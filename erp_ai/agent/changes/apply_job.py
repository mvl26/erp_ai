"""The change job: applies an approved proposal (one file + one local commit, or one bench command) and
undoes an applied code change. Runs in the `long` queue, one job at a time across the bench."""

import json
import os

import frappe
from frappe.utils import get_fullname
from frappe.utils.synchronization import filelock

from erp_ai.agent import change_text, policy
from erp_ai.agent.changes import file_writer, process_runner, transitions
from erp_ai.agent.tools import change_guard, source
from erp_ai.constants import (
	CHANGE_KIND_CODE,
	CHANGE_STATUS_APPLIED,
	CHANGE_STATUS_APPLYING,
	CHANGE_STATUS_FAILED,
	CHANGE_STATUS_STALE,
	CHANGE_STATUS_UNDOING,
	CHANGE_STATUS_UNDONE,
	COMMAND_TIMEOUT_S,
	PROPOSAL_DOCTYPE,
	TITLE_CHANGE_FAILED,
)

LOCK_NAME = "erp_ai_change"
LOCK_TIMEOUT_S = 30
ACTION_APPLY = "apply"
ACTION_UNDO = "undo"

SWITCH_OFF = "công tắc sửa code đã tắt"
DIGEST_CHANGED = "nội dung đề xuất đã đổi sau khi duyệt"
BRANCH_CHANGED = "nhánh đang checkout đã đổi từ lúc đề xuất"
FILE_CHANGED = "file đã đổi từ lúc đề xuất"
FILE_NOW_EXISTS = "file đã tồn tại từ lúc đề xuất"
FILE_CHANGED_AFTER_APPLY = "file đã đổi sau khi áp dụng, không hoàn tác tự động được"
WRITE_MISMATCH = "nội dung ghi xuống đĩa không khớp đề xuất"
COMMIT_FAILED = "git commit lỗi, file đã được trả lại như cũ"
COMMIT_TIMED_OUT = "git commit quá giờ, file đã được trả lại như cũ"
COMMIT_UNEXPECTED = "commit vừa tạo không đúng một file của đề xuất"
COMMAND_FAILED = "lệnh thoát với mã {0}"
COMMAND_TIMED_OUT = "lệnh chạy quá giờ và đã bị dừng"
COMMAND_NOT_FOUND = "không tìm thấy lệnh bench"
CRASHED = "job lỗi: {0}"
# Git states that mean the repo moved since the proposal was made: the proposal is stale, not broken.
GIT_MOVED_REASONS = (
	source.GIT_NOT_REPO,
	source.GIT_NO_COMMIT,
	source.GIT_DETACHED,
	source.GIT_LOCKED,
	source.GIT_IN_PROGRESS,
	source.GIT_IGNORED,
	source.GIT_DIRTY,
)


class _Stop(Exception):
	"""Ends a job with a final status and reason; nothing on disk is left half-done when it is raised."""

	def __init__(self, status: str, reason: str, result=None):
		super().__init__(reason)
		self.status = status
		self.reason = reason
		self.result = result


def run_change(proposal_name: str, action: str) -> None:
	"""Job entry (queued by `queue.enqueue_change_job`): `action` is `apply` or `undo`."""
	if action not in (ACTION_APPLY, ACTION_UNDO):
		raise ValueError(f"Unknown action: {action!r}")
	with filelock(LOCK_NAME, timeout=LOCK_TIMEOUT_S, is_global=True):
		if action == ACTION_APPLY:
			if not transitions.begin_apply(proposal_name):
				return
			expected = CHANGE_STATUS_APPLYING
		else:
			status = frappe.db.get_value(PROPOSAL_DOCTYPE, proposal_name, "change_status")
			if status != CHANGE_STATUS_UNDOING:
				return
			expected = CHANGE_STATUS_UNDOING
		# The running state is durable before any file or process is touched.
		frappe.db.commit()
		proposal = frappe.get_doc(PROPOSAL_DOCTYPE, proposal_name)
		actor = proposal.decided_by if action == ACTION_APPLY else proposal.undo_by
		try:
			_run(proposal, action, actor)
		except _Stop as stop:
			transitions.finish(
				proposal_name,
				expected,
				stop.status,
				step="stale" if stop.status == CHANGE_STATUS_STALE else "fail",
				actor=actor,
				reason=stop.reason,
				result=stop.result,
			)
		except Exception as exc:
			frappe.db.rollback()
			frappe.log_error(TITLE_CHANGE_FAILED, f"{proposal_name} {action}: {type(exc).__name__}")
			transitions.finish(
				proposal_name,
				expected,
				CHANGE_STATUS_FAILED,
				step="fail",
				actor=actor,
				reason=CRASHED.format(type(exc).__name__),
			)
		frappe.db.commit()


def _run(proposal, action: str, actor: str) -> None:
	if action == ACTION_UNDO:
		_undo_code(proposal, actor)
		return
	settings = policy.current_change_settings()
	if not settings.enabled:
		raise _Stop(CHANGE_STATUS_FAILED, SWITCH_OFF)
	if transitions.content_digest(proposal) != proposal.approved_digest:
		raise _Stop(CHANGE_STATUS_FAILED, DIGEST_CHANGED)
	if proposal.change_kind == CHANGE_KIND_CODE:
		_apply_code(proposal, actor, settings.allowed_apps)
	else:
		_apply_command(proposal, actor, settings.allowed_apps)


def _guard(proposal, allowed_apps, *, new_file: bool, stale_on_git: bool):
	"""Path and git checks at run time; a git refusal is stale on apply (the repo moved) and a failure on undo."""
	guard = change_guard.check_write_path(proposal.file_path, allowed_apps, new_file=new_file)
	if guard.reason:
		git_refusal = guard.reason in GIT_MOVED_REASONS
		status = CHANGE_STATUS_STALE if stale_on_git and git_refusal else CHANGE_STATUS_FAILED
		raise _Stop(status, guard.reason)
	return guard


def _commit(guard, subject: str, body: str, give_back) -> str:
	"""One `commit --only` of the target; on any failure `give_back()` restores the file, then the job fails.

	Returns the new HEAD commit.
	"""
	git = guard.git
	result = process_runner.git_commit_only(
		git.repo_root, git.rel_in_repo, subject, body, source.GIT_TIMEOUT_S
	)
	if result.timed_out or result.exit_code != 0:
		give_back()
		reason = COMMIT_TIMED_OUT if result.timed_out else COMMIT_FAILED
		raise _Stop(CHANGE_STATUS_FAILED, reason, result)
	summary = source.git_commit_summary(git.repo_root)
	if summary.parents != (git.head,) or summary.paths != (git.rel_in_repo,):
		raise _Stop(CHANGE_STATUS_FAILED, COMMIT_UNEXPECTED)
	return summary.commit


def _person(user: str) -> str:
	return change_text.safe_person_name(get_fullname(user))


def _apply_code(proposal, actor: str, allowed_apps) -> None:
	new_file = bool(proposal.is_new_file)
	guard = _guard(proposal, allowed_apps, new_file=new_file, stale_on_git=True)
	git = guard.git
	if git.branch != proposal.target_branch:
		raise _Stop(CHANGE_STATUS_STALE, BRANCH_CHANGED)
	on_disk = file_writer.sha256_of(guard.full_path)
	if new_file and (on_disk is not None or os.path.lexists(guard.full_path)):
		raise _Stop(CHANGE_STATUS_STALE, FILE_NOW_EXISTS)
	if not new_file and on_disk != proposal.base_hash:
		raise _Stop(CHANGE_STATUS_STALE, FILE_CHANGED)

	def give_back():
		if new_file:
			process_runner.git_unstage_new(git.repo_root, git.rel_in_repo, source.GIT_TIMEOUT_S)
			file_writer.remove_created(guard.full_path)
		else:
			file_writer.write_atomic(guard.full_path, proposal.content_before, new_file=False)

	written = file_writer.write_atomic(guard.full_path, proposal.content_after, new_file=new_file)
	if written != proposal.after_hash:
		if new_file:
			file_writer.remove_created(guard.full_path)
		else:
			file_writer.write_atomic(guard.full_path, proposal.content_before, new_file=False)
		raise _Stop(CHANGE_STATUS_FAILED, WRITE_MISMATCH)
	if new_file:
		added = process_runner.git_add_new(git.repo_root, git.rel_in_repo, source.GIT_TIMEOUT_S)
		if added.timed_out or added.exit_code != 0:
			file_writer.remove_created(guard.full_path)
			raise _Stop(CHANGE_STATUS_FAILED, COMMIT_FAILED, added)
	subject, body = change_text.apply_message(
		proposal.name, str(proposal.ticket or ""), proposal.file_path, _person(actor)
	)
	commit = _commit(guard, subject, body, give_back)
	transitions.finish(
		proposal.name,
		CHANGE_STATUS_APPLYING,
		CHANGE_STATUS_APPLIED,
		step="apply",
		actor=actor,
		fields={
			"applied_branch": git.branch,
			"applied_ahead_count": git.ahead_count + 1 if git.upstream_ref else 0,
			"apply_commit_sha": commit,
		},
		before={"hash": proposal.base_hash},
		after={"hash": proposal.after_hash, "commit": commit},
	)


def _undo_code(proposal, actor: str) -> None:
	new_file = bool(proposal.is_new_file)
	# Undo stays possible after the app left the allowed list; the guard still refuses erp_ai and bad paths.
	guard = _guard(proposal, (proposal.app,), new_file=False, stale_on_git=False)
	if file_writer.sha256_of(guard.full_path) != proposal.after_hash:
		raise _Stop(CHANGE_STATUS_FAILED, FILE_CHANGED_AFTER_APPLY)

	def give_back():
		file_writer.write_atomic(guard.full_path, proposal.content_after, new_file=new_file)

	if new_file:
		file_writer.remove_created(guard.full_path)
	else:
		restored = file_writer.write_atomic(guard.full_path, proposal.content_before, new_file=False)
		if restored != proposal.base_hash:
			give_back()
			raise _Stop(CHANGE_STATUS_FAILED, WRITE_MISMATCH)
	subject, body = change_text.undo_message(
		proposal.name,
		str(proposal.ticket or ""),
		proposal.file_path,
		str(proposal.apply_commit_sha or ""),
		_person(actor),
	)
	commit = _commit(guard, subject, body, give_back)
	transitions.finish(
		proposal.name,
		CHANGE_STATUS_UNDOING,
		CHANGE_STATUS_UNDONE,
		step="undo",
		actor=actor,
		fields={"undo_commit_sha": commit},
		before={"hash": proposal.after_hash},
		after={"hash": proposal.base_hash, "commit": commit},
	)


def _apply_command(proposal, actor: str, allowed_apps) -> None:
	args = json.loads(proposal.command_args or "null")
	refusal = change_guard.check_bench_args(args, allowed_apps, frappe.local.site)
	if refusal:
		raise _Stop(CHANGE_STATUS_FAILED, refusal)
	result = process_runner.run_bench(args, COMMAND_TIMEOUT_S)
	if result.not_found:
		raise _Stop(CHANGE_STATUS_FAILED, COMMAND_NOT_FOUND, result)
	if result.timed_out:
		raise _Stop(CHANGE_STATUS_FAILED, COMMAND_TIMED_OUT, result)
	if result.exit_code != 0:
		raise _Stop(CHANGE_STATUS_FAILED, COMMAND_FAILED.format(result.exit_code), result)
	transitions.finish(
		proposal.name,
		CHANGE_STATUS_APPLYING,
		CHANGE_STATUS_APPLIED,
		step="apply",
		actor=actor,
		result=result,
	)
