"""The change job: applies an approved proposal (one file + one local commit, or one bench command) and
undoes an applied code change. Runs in the `long` queue, one job at a time across the bench."""

import hashlib
import json
import os
import time

import frappe
from frappe.utils import get_fullname
from frappe.utils.file_lock import LockTimeoutError
from frappe.utils.synchronization import filelock

from erp_ai.agent import change_text, policy
from erp_ai.agent.authority import NEVER_AUTHORITY
from erp_ai.agent.changes import file_writer, process_runner, transitions
from erp_ai.agent.tools import change_guard, source
from erp_ai.constants import (
	BOT_GIT_EMAIL,
	CHANGE_KIND_CODE,
	CHANGE_STATUS_APPLIED,
	CHANGE_STATUS_APPLYING,
	CHANGE_STATUS_APPROVED,
	CHANGE_STATUS_FAILED,
	CHANGE_STATUS_STALE,
	CHANGE_STATUS_UNDOING,
	CHANGE_STATUS_UNDONE,
	COMMAND_TIMEOUT_S,
	LOGGER_NAME,
	PROPOSAL_DOCTYPE,
	ROLE_INSTRUCTOR,
	TITLE_CHANGE_FAILED,
)

LOCK_NAME = "erp_ai_change"
LOCK_TIMEOUT_S = 30
ACTION_APPLY = "apply"
ACTION_UNDO = "undo"
OUTCOME_SKIPPED = "skipped"

# Design 4.3 steps 3 and 4.2 (exact wording of the design table).
LOCK_BUSY = "đang có thay đổi khác chạy, không lấy được khóa"
WRONG_RUNNER = "sai người chạy job"
APPROVER_LOST_ROLE = "người duyệt không còn quyền"
SWITCH_OFF = "công tắc đang tắt"
DIGEST_CHANGED = "nội dung đề xuất đã bị sửa sau khi duyệt"
STORED_HASH_MISMATCH = "nội dung lưu không khớp dấu"
TARGET_CHANGED = "file đích đã đổi kể từ lúc đề xuất"
FILE_CHANGED_AFTER_APPLY = "file đã đổi sau khi áp dụng, không hoàn tác tự động được"
WRITE_MISMATCH = "đọc lại sau khi ghi không khớp"
COMMIT_UNEXPECTED = "commit vừa tạo không đúng một file của đề xuất"
# Design table 3.2 (exact wording).
GIT_COMMIT_FAILED = "commit git lỗi, đã trả file về như trước"
GIT_COMMIT_TIMED_OUT_SUFFIX = " (quá thời gian)"
GIT_RESTORE_FAILED = "commit git lỗi và không trả lại được trạng thái kho, cần người kiểm"
GIT_COMMIT_MISMATCH = "commit không đúng nội dung đã duyệt, cần người kiểm"
# Design 3.5: the short reason taken from the git output after `GIT_COMMIT_FAILED`.
GIT_SHORT_REASON_MAX_CHARS = 120
GIT_BRANCH_CHANGED = "nhánh đang checkout đã đổi kể từ lúc đề xuất"
COMMAND_FAILED = "lệnh thoát với mã {0}"
COMMAND_TIMED_OUT = "lệnh chạy quá giờ và đã bị dừng"
COMMAND_NOT_FOUND = "không tìm thấy lệnh bench"


class _Stop(Exception):
	"""Ends a job with a final status and reason, and the git `fields` and log `before`/`after` to record."""

	def __init__(self, status: str, reason: str, result=None, *, fields=None, before=None, after=None):
		super().__init__(reason)
		self.status = status
		self.reason = reason
		self.result = result
		self.fields = fields
		self.before = before
		self.after = after


def run_change(proposal_name: str, action: str) -> None:
	"""Job entry (queued by `queue.enqueue_change_job`): `action` is `apply` or `undo` (design 4.3, 4.4).

	Ends with the proposal in a final state or untouched (a repeated job); writes one `erp_ai` log line.
	"""
	if action not in (ACTION_APPLY, ACTION_UNDO):
		raise ValueError(f"Unknown action: {action!r}")
	started = time.monotonic()
	deadline = started + COMMAND_TIMEOUT_S
	outcome = _locked_run(proposal_name, action, deadline)
	commit = "-"
	if outcome != OUTCOME_SKIPPED:
		commit_field = "apply_commit_sha" if action == ACTION_APPLY else "undo_commit_sha"
		commit = frappe.db.get_value(PROPOSAL_DOCTYPE, proposal_name, commit_field) or "-"
	frappe.logger(LOGGER_NAME).info(
		"erp_ai change proposal=%s action=%s outcome=%s duration_ms=%d commit=%s",
		proposal_name,
		action,
		outcome,
		int((time.monotonic() - started) * 1000),
		commit,
	)


def _locked_run(proposal_name: str, action: str, deadline: float) -> str:
	"""Steps 2 to 5 of design 4.3 (4.4 for undo); returns the final status, or `OUTCOME_SKIPPED`."""
	waiting = CHANGE_STATUS_APPROVED if action == ACTION_APPLY else CHANGE_STATUS_UNDOING
	row = frappe.db.get_value(
		PROPOSAL_DOCTYPE, proposal_name, ["change_status", "decided_by", "undo_by"], as_dict=True
	)
	if row is None or row.change_status != waiting:
		return OUTCOME_SKIPPED
	actor = row.decided_by if action == ACTION_APPLY else row.undo_by
	try:
		with filelock(LOCK_NAME, timeout=LOCK_TIMEOUT_S, is_global=True):
			return _run_in_lock(proposal_name, action, actor, deadline)
	except LockTimeoutError:
		if not transitions.finish(
			proposal_name, waiting, CHANGE_STATUS_FAILED, step="fail", actor=actor, reason=LOCK_BUSY
		):
			return OUTCOME_SKIPPED
		frappe.db.commit()
		return CHANGE_STATUS_FAILED


def _run_in_lock(proposal_name: str, action: str, actor: str, deadline: float) -> str:
	if action == ACTION_APPLY:
		if not transitions.begin_apply(proposal_name):
			return OUTCOME_SKIPPED
		expected = CHANGE_STATUS_APPLYING
	else:
		status = frappe.db.get_value(PROPOSAL_DOCTYPE, proposal_name, "change_status")
		if status != CHANGE_STATUS_UNDOING:
			return OUTCOME_SKIPPED
		expected = CHANGE_STATUS_UNDOING
	# The running state is durable before any check, file or process (ADR-013 decision 5).
	frappe.db.commit()
	proposal = frappe.get_doc(PROPOSAL_DOCTYPE, proposal_name)
	outcome = CHANGE_STATUS_FAILED
	try:
		outcome = _run(proposal, action, actor, deadline)
	except _Stop as stop:
		transitions.finish(
			proposal_name,
			expected,
			stop.status,
			step="stale" if stop.status == CHANGE_STATUS_STALE else "fail",
			actor=actor,
			reason=stop.reason,
			result=stop.result,
			fields=stop.fields,
			before=stop.before,
			after=stop.after,
		)
		outcome = stop.status
	except Exception as exc:
		frappe.db.rollback()
		frappe.log_error(
			TITLE_CHANGE_FAILED, f"proposal={proposal_name} action={action} error={type(exc).__name__}"
		)
		transitions.finish(
			proposal_name,
			expected,
			CHANGE_STATUS_FAILED,
			step="fail",
			actor=actor,
			reason=type(exc).__name__,
		)
	frappe.db.commit()
	return outcome


def _run(proposal, action: str, actor: str, deadline: float) -> str:
	if action == ACTION_UNDO:
		_undo_code(proposal, actor)
		return CHANGE_STATUS_UNDONE
	settings = _recheck(proposal)
	if proposal.change_kind == CHANGE_KIND_CODE:
		_apply_code(proposal, actor, settings.allowed_apps, deadline)
	else:
		_apply_command(proposal, actor, deadline)
	return CHANGE_STATUS_APPLIED


def _has_authority(user) -> bool:
	return bool(user) and user not in NEVER_AUTHORITY and ROLE_INSTRUCTOR in frappe.get_roles(user)


def _recheck(proposal):
	"""Design 4.3 step 4.2, in table order: the first failing row ends the job as `Lỗi` with its reason."""
	if frappe.session.user != proposal.decided_by:
		raise _Stop(CHANGE_STATUS_FAILED, WRONG_RUNNER)
	if not _has_authority(proposal.decided_by):
		raise _Stop(CHANGE_STATUS_FAILED, APPROVER_LOST_ROLE)
	settings = policy.current_change_settings()
	if not settings.enabled:
		raise _Stop(CHANGE_STATUS_FAILED, SWITCH_OFF)
	if transitions.content_digest(proposal) != proposal.approved_digest:
		raise _Stop(CHANGE_STATUS_FAILED, DIGEST_CHANGED)
	if proposal.change_kind == CHANGE_KIND_CODE:
		guard = change_guard.check_write_path(
			proposal.file_path, settings.allowed_apps, new_file=bool(proposal.is_new_file), read_git=False
		)
		refusal = guard.reason
	else:
		args = json.loads(proposal.command_args or "null")
		refusal = change_guard.check_bench_args(args, settings.allowed_apps, frappe.local.site)
	if refusal:
		raise _Stop(CHANGE_STATUS_FAILED, refusal)
	if proposal.change_kind == CHANGE_KIND_CODE:
		content_after = (proposal.content_after or "").encode("utf-8")
		if hashlib.sha256(content_after).hexdigest() != proposal.after_hash:
			raise _Stop(CHANGE_STATUS_FAILED, STORED_HASH_MISMATCH)
		# The real message with the approver put back as the placeholder is the stored preview (design 3.9);
		# `apply_message` only places the approver in its own line, so building it with the placeholder is that.
		preview = change_text.message_text(
			*change_text.apply_message(
				proposal.name,
				str(proposal.ticket or ""),
				proposal.file_path,
				change_text.APPROVER_PLACEHOLDER,
			)
		)
		if preview != proposal.commit_message:
			raise _Stop(CHANGE_STATUS_FAILED, DIGEST_CHANGED)
	return settings


def _guard(proposal, allowed_apps, *, new_file: bool):
	"""Path and git checks of the undo job; any refusal ends it as `Lỗi`."""
	guard = change_guard.check_write_path(proposal.file_path, allowed_apps, new_file=new_file)
	if guard.reason:
		raise _Stop(CHANGE_STATUS_FAILED, guard.reason)
	return guard


def _failed(result) -> bool:
	return result.timed_out or result.exit_code != 0


def _commit_failed_reason(result) -> str:
	"""`GIT_COMMIT_FAILED`, ` (quá thời gian)` on a timeout, then the last git output line cut short (design 3.5)."""
	reason = GIT_COMMIT_FAILED + (GIT_COMMIT_TIMED_OUT_SUFFIX if result.timed_out else "")
	lines = [line.strip() for line in (result.output or "").splitlines() if line.strip()]
	return f"{reason}: {lines[-1][:GIT_SHORT_REASON_MAX_CHARS]}" if lines else reason


def _git_commit(repo_root: str, rel_in_repo: str, subject: str, body: str, give_back, limit_s: int) -> None:
	"""One `commit --only` of the target; on any failure `give_back()` restores the file, then the job fails."""
	result = process_runner.git_commit_only(repo_root, rel_in_repo, subject, body, limit_s)
	if _failed(result):
		give_back()
		raise _Stop(CHANGE_STATUS_FAILED, _commit_failed_reason(result), result)


def _commit(guard, subject: str, body: str, give_back) -> str:
	"""The undo commit and its check; returns the new HEAD commit."""
	git = guard.git
	_git_commit(git.repo_root, git.rel_in_repo, subject, body, give_back, source.GIT_TIMEOUT_S)
	summary = source.git_commit_summary(git.repo_root)
	if summary.parents != (git.head,) or summary.paths != (git.rel_in_repo,):
		raise _Stop(CHANGE_STATUS_FAILED, COMMIT_UNEXPECTED)
	return summary.commit


def _git_limit(deadline: float) -> int:
	"""`limit_s` of a git write: at most `GIT_TIMEOUT_S`, cut by the job deadline, never below 1 (design 3.5)."""
	return min(source.GIT_TIMEOUT_S, max(1, int(deadline - time.monotonic())))


def _person(user: str) -> str:
	return change_text.safe_person_name(get_fullname(user))


def _apply_record(proposal, full_path: str, old_head: str, commit: str | None, branch: str | None) -> dict:
	"""`fields`, `before` and `after` of a `finish` after the commit ran (design-addendum-3 QĐ-B5).

	Without a commit sha, neither `fields` nor `after` carries one.
	"""
	after = {"sha256": file_writer.sha256_of(full_path)}
	fields = {}
	if commit:
		fields["apply_commit_sha"] = commit
		after["commit"] = commit
	after["branch"] = branch
	return {"fields": fields, "before": {"sha256": proposal.base_hash, "head": old_head}, "after": after}


def _apply_postcheck(proposal, state, full_path: str, summary=None):
	"""Design 4.3 step 3.5 (ADR-022 decision 1 step 5); returns the `CommitSummary` of the bot commit.

	The bot commit exists (the commit command exited 0, or HEAD moved to a bot commit whose `summary` is
	given), so the file is never given back and history is never rewritten (design-addendum-3 QĐ-B2 item 1):
	a check that fails or cannot be read ends the job as `Lỗi` `GIT_COMMIT_MISMATCH`, keeping the commit sha
	when it is known.
	"""
	repo, rel, old_head = state.repo_root, state.rel_in_repo, state.head
	try:
		if summary is None:
			summary = source.git_commit_summary(repo)
		matches = (
			len(summary.parents) == 1
			and source.git_is_ancestor(repo, old_head, summary.parents[0]) is True
			and summary.paths == (rel,)
			and summary.branch == proposal.target_branch
			and source.git_blob(repo, summary.commit, rel) == (proposal.content_after or "").encode("utf-8")
		)
	except RuntimeError:
		# git could not be read: the check is not passed (QĐ-B2 item 1), the reason below says so.
		matches = False
	if matches:
		return summary
	if summary is not None:
		commit, branch = summary.commit, summary.branch
	else:
		head = source.git_head(repo)
		commit, branch = (head if head not in (None, old_head) else None), None
	raise _Stop(
		CHANGE_STATUS_FAILED,
		GIT_COMMIT_MISMATCH,
		**_apply_record(proposal, full_path, old_head, commit, branch),
	)


def _apply_code(proposal, actor: str, allowed_apps, deadline: float) -> None:
	"""Design 4.3 step 4.3: file hash, git pre-read, write, commit, post-check, done."""
	new_file = bool(proposal.is_new_file)
	guard = change_guard.check_write_path(proposal.file_path, allowed_apps, new_file=new_file, read_git=False)
	if guard.reason:
		raise _Stop(CHANGE_STATUS_FAILED, guard.reason)
	full = guard.full_path
	# D-19: the file hash first, git after; a stale target never reaches git.
	on_disk = file_writer.sha256_of(full)
	if new_file and (on_disk is not None or os.path.lexists(full)):
		raise _Stop(CHANGE_STATUS_STALE, TARGET_CHANGED)
	if not new_file and on_disk != proposal.base_hash:
		raise _Stop(CHANGE_STATUS_STALE, TARGET_CHANGED)
	# Git pre-check (design 4.3 step 4.3 item 2): a git refusal is `Lỗi` (AC-18, ADR-022 decision 7); only
	# a changed branch is `Hết hiệu lực` (spec D-1, ADR-022 decision 6). A held `index.lock` is refused at
	# once and never removed; `limit_s` bounds every git read by the job deadline (NFR-3).
	state = source.read_git_state(full, new_file=new_file, limit_s=_git_limit(deadline))
	if state.refusal:
		raise _Stop(CHANGE_STATUS_FAILED, state.refusal)
	if state.branch != proposal.target_branch:
		raise _Stop(CHANGE_STATUS_STALE, GIT_BRANCH_CHANGED)
	repo, rel, old_head = state.repo_root, state.rel_in_repo, state.head
	added = committed = False
	summary = None

	def give_back(reason: str, expected_head: str):
		"""Design 4.3 step 3.6, then `Lỗi` with `reason`, or `GIT_RESTORE_FAILED` when the repo is not as before."""
		if not _give_back(
			proposal, full, repo, rel, new_file=new_file, added=added, expected_head=expected_head
		):
			reason = GIT_RESTORE_FAILED
		raise _Stop(CHANGE_STATUS_FAILED, reason)

	written = file_writer.write_atomic(full, proposal.content_after, new_file=new_file)
	try:
		if written != proposal.after_hash:
			give_back(WRITE_MISMATCH, old_head)
		if new_file:
			result = process_runner.git_add_new(repo, rel, source.GIT_TIMEOUT_S)
			if _failed(result):
				give_back(_commit_failed_reason(result), old_head)
			added = True
		subject, body = change_text.apply_message(
			proposal.name, str(proposal.ticket or ""), proposal.file_path, _person(actor)
		)
		result = process_runner.git_commit_only(repo, rel, subject, body, _git_limit(deadline))
		if _failed(result):
			summary = _commit_landed(
				repo, old_head, lambda head: give_back(_commit_failed_reason(result), head)
			)
		committed = True
		summary = _apply_postcheck(proposal, state, full, summary)
		record = _apply_record(proposal, full, old_head, summary.commit, summary.branch)
		transitions.finish(
			proposal.name,
			CHANGE_STATUS_APPLYING,
			CHANGE_STATUS_APPLIED,
			step="apply",
			actor=actor,
			fields={
				**record["fields"],
				"applied_branch": summary.branch,
				"applied_ahead_count": state.ahead_count + 1 if state.upstream_ref else 0,
			},
			before=record["before"],
			after=record["after"],
		)
	except _Stop:
		raise
	except Exception as exc:
		# Design-addendum-3 QĐ-B2 item 4: an unexpected error gives the file back only while no bot commit is
		# known, and only once HEAD is proven unchanged (D-17).
		if committed:
			_fail_after_commit(proposal, full, repo, old_head, summary, exc)
		_give_back_after_crash(proposal, full, repo, rel, new_file=new_file, added=added, old_head=old_head)
		raise


def _give_back(
	proposal, full: str, repo: str, rel: str, *, new_file: bool, added: bool, expected_head: str
) -> bool:
	"""Design 4.3 step 3.6; True when the file, the index entry of the target and HEAD are as before.

	A changed file gets `content_before` back (read-back hash = `base_hash`); a new file is removed, then
	unstaged when `git add` went through. HEAD must still be `expected_head` and git must accept the target.
	"""
	try:
		if new_file:
			file_writer.remove_created(full)
			restored = True
			if added:
				restored = not _failed(process_runner.git_unstage_new(repo, rel, source.GIT_TIMEOUT_S))
		else:
			restored = (
				file_writer.write_atomic(full, proposal.content_before, new_file=False) == proposal.base_hash
			)
		return (
			restored
			and source.git_head(repo) == expected_head
			and source.read_git_state(full, new_file=new_file).refusal is None
		)
	except Exception as exc:
		# The give-back itself broke: the repo state is unknown, which is what `GIT_RESTORE_FAILED` says.
		frappe.log_error(
			TITLE_CHANGE_FAILED, f"proposal={proposal.name} action=give_back error={type(exc).__name__}"
		)
		return False


def _commit_landed(repo: str, old_head: str, give_back):
	"""Design 4.3 step 3.4 after a failed or timed-out commit; returns the `CommitSummary` of a bot commit.

	HEAD unchanged → `give_back(old_head)`; HEAD moved to a person's commit → `give_back(head_now)`; HEAD
	unreadable, or moved and its summary unreadable → `Lỗi` `GIT_ERROR` without giving back (QĐ-B2 item 2).
	"""
	head_now = source.git_head(repo)
	if head_now is None:
		raise _Stop(CHANGE_STATUS_FAILED, source.GIT_ERROR)
	if head_now == old_head:
		give_back(old_head)
	try:
		summary = source.git_commit_summary(repo)
	except RuntimeError:
		raise _Stop(CHANGE_STATUS_FAILED, source.GIT_ERROR) from None
	if summary.author_email != BOT_GIT_EMAIL:
		give_back(head_now)
	return summary


def _fail_after_commit(proposal, full: str, repo: str, old_head: str, summary, exc: Exception):
	"""QĐ-B2 items 1 and 4: the bot commit exists, so the file stays; `Lỗi` with the class name, keeping the
	commit sha when known (`summary`, else a HEAD that moved off `old_head`) with its QĐ-B5 log values."""
	frappe.db.rollback()
	frappe.log_error(TITLE_CHANGE_FAILED, f"proposal={proposal.name} action=apply error={type(exc).__name__}")
	if summary is not None:
		commit, branch = summary.commit, summary.branch
	else:
		head = source.git_head(repo)
		commit, branch = (head if head not in (None, old_head) else None), None
	raise _Stop(
		CHANGE_STATUS_FAILED, type(exc).__name__, **_apply_record(proposal, full, old_head, commit, branch)
	) from exc


def _give_back_after_crash(
	proposal, full: str, repo: str, rel: str, *, new_file: bool, added: bool, old_head
):
	"""QĐ-B2 item 4 with no bot commit known: give the file back only when HEAD is still `old_head` (D-17).

	The caller re-raises the original error, which ends the job as `Lỗi` with its class name; a give-back
	that was skipped or did not hold is recorded in the error log so a person checks the repo.
	"""
	try:
		restored = source.git_head(repo) == old_head and _give_back(
			proposal, full, repo, rel, new_file=new_file, added=added, expected_head=old_head
		)
	except Exception as exc:
		# Never hide the first error behind one from giving back; record this one and go on.
		frappe.log_error(
			TITLE_CHANGE_FAILED, f"proposal={proposal.name} action=give_back error={type(exc).__name__}"
		)
		return
	if not restored:
		frappe.log_error(TITLE_CHANGE_FAILED, f"proposal={proposal.name} action=give_back restored=False")


def _undo_code(proposal, actor: str) -> None:
	new_file = bool(proposal.is_new_file)
	# Undo stays possible after the app left the allowed list; the guard still refuses erp_ai and bad paths.
	guard = _guard(proposal, (proposal.app,), new_file=False)
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


def _apply_command(proposal, actor: str, deadline: float) -> None:
	args = json.loads(proposal.command_args)
	result = process_runner.run_bench(args, int(deadline - time.monotonic()))
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
