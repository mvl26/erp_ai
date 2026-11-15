"""The change job: applies an approved proposal (one file + one local commit, or one bench command) and
undoes an applied code change. Runs in the `long` queue, one job at a time across the bench."""

import hashlib
import json
import os
import re
import time
import unicodedata

import frappe
from frappe.utils import get_fullname
from frappe.utils.file_lock import LockTimeoutError
from frappe.utils.synchronization import filelock

from erp_ai.agent import change_text, policy
from erp_ai.agent.authority import NEVER_AUTHORITY
from erp_ai.agent.changes import block, file_writer, process_runner, result_comment, transitions
from erp_ai.agent.tools import change_guard, source
from erp_ai.constants import (
	BOT_GIT_EMAIL,
	CHANGE_KIND_CODE,
	CHANGE_OP_EDIT,
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
FILE_CHANGED_AFTER_APPLY = "file đã đổi sau khi áp dụng, không hoàn tác"
WRITE_MISMATCH = "đọc lại sau khi ghi không khớp"
# Design table 3.2 (exact wording).
GIT_COMMIT_FAILED = "commit git lỗi, đã trả file về như trước"
GIT_COMMIT_TIMED_OUT_SUFFIX = " (quá thời gian)"
GIT_RESTORE_FAILED = "commit git lỗi và không trả lại được trạng thái kho, cần người kiểm"
GIT_COMMIT_MISMATCH = "commit không đúng nội dung đã duyệt, cần người kiểm"
# Design 3.5: the short reason taken from the git output after `GIT_COMMIT_FAILED`.
GIT_SHORT_REASON_MAX_CHARS = 120
# Design addendum 4 QĐ-D1, QĐ-D2: a word of the short reason that may hold a path, URL, email or key is masked.
GIT_MASKED_WORD = "…"
GIT_KEY_LIKE = re.compile(r"[A-Za-z0-9_+\-]{20,}")
GIT_BRANCH_CHANGED = "nhánh đang checkout đã đổi kể từ lúc đề xuất"
GIT_NOT_ANCESTOR = "commit áp dụng không còn nằm trong lịch sử nhánh đang checkout"
# Design 4.3 step 4 (exact wording); "quá thời gian" is AC-10's reason (design addendum 2 QĐ-A3).
COMMAND_FAILED = "lệnh trả mã {0}"
COMMAND_OUT_OF_TIME = "quá thời gian"
COMMAND_NOT_FOUND = "không tìm thấy bench trên máy chủ"


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
	comment = "-"
	if outcome != OUTCOME_SKIPPED:
		commit_field = "apply_commit_sha" if action == ACTION_APPLY else "undo_commit_sha"
		commit = frappe.db.get_value(PROPOSAL_DOCTYPE, proposal_name, commit_field) or "-"
		comment = _post_result(proposal_name, action)
	frappe.logger(LOGGER_NAME).info(
		"erp_ai change proposal=%s action=%s outcome=%s duration_ms=%d commit=%s comment=%s",
		proposal_name,
		action,
		outcome,
		int((time.monotonic() - started) * 1000),
		commit,
		comment,
	)


def _post_result(proposal_name: str, action: str) -> str:
	"""Write the result line on the ticket after the final status was committed (AC-28, CHG-001 design 4).

	Returns the Comment name, `-` when nothing was written, or `error`.
	"""
	try:
		name = result_comment.post_result(proposal_name)
		frappe.db.commit()
	except Exception as exc:
		# STD-ERR-1: the final status is already committed and is the job's real result; a failed result line
		# only loses that line (rolled back), so it is logged and the job ends normally instead of re-raising.
		frappe.db.rollback()
		frappe.log_error(
			result_comment.TITLE_RESULT_COMMENT_FAILED,
			f"proposal={proposal_name} action={action} error={type(exc).__name__}",
		)
		return "error"
	return name or "-"


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
		_undo_code(proposal, actor, _recheck(proposal, action), deadline)
		return CHANGE_STATUS_UNDONE
	allowed_apps = _recheck(proposal, action)
	if block.is_block(proposal):
		_apply_block(proposal, actor, allowed_apps, deadline)
	elif proposal.change_kind == CHANGE_KIND_CODE:
		_apply_code(proposal, actor, allowed_apps, deadline)
	else:
		_apply_command(proposal, actor, deadline)
	return CHANGE_STATUS_APPLIED


def _has_authority(user) -> bool:
	return bool(user) and user not in NEVER_AUTHORITY and ROLE_INSTRUCTOR in frappe.get_roles(user)


def _recheck(proposal, action: str) -> tuple[str, ...]:
	"""Design 4.3 step 4.2, in table order: the first failing row ends the job as `Lỗi` with its reason.

	Undo (design 4.4 step 2) runs only the runner, role, digest and guard rows against `undo_by`: not the
	switch (G-1), not the stored-hash and commit-message preview rows (apply-only). Its guard allows the
	proposal's own app, so undo stays possible after the app left the list. Returns the apps the guard
	allowed.
	"""
	runner = proposal.decided_by if action == ACTION_APPLY else proposal.undo_by
	if frappe.session.user != runner:
		raise _Stop(CHANGE_STATUS_FAILED, WRONG_RUNNER)
	if not _has_authority(runner):
		raise _Stop(CHANGE_STATUS_FAILED, APPROVER_LOST_ROLE)
	if action == ACTION_APPLY:
		settings = policy.current_change_settings()
		if not settings.enabled:
			raise _Stop(CHANGE_STATUS_FAILED, SWITCH_OFF)
		allowed_apps = settings.allowed_apps
	else:
		allowed_apps = (proposal.app,)
	if transitions.content_digest(proposal) != proposal.approved_digest:
		raise _Stop(CHANGE_STATUS_FAILED, DIGEST_CHANGED)
	if block.is_block(proposal):
		# CHG-002 T1 walking skeleton: runner, role, switch and digest only; `_apply_block` guards its item.
		return allowed_apps
	if proposal.change_kind == CHANGE_KIND_CODE:
		# The applied file exists at undo time, so the guard sees it as a changed file then.
		new_file = action == ACTION_APPLY and bool(proposal.is_new_file)
		guard = change_guard.check_write_path(
			proposal.file_path, allowed_apps, new_file=new_file, read_git=False
		)
		refusal = guard.reason
	else:
		args = json.loads(proposal.command_args or "null")
		refusal = change_guard.check_bench_args(args, settings.allowed_apps, frappe.local.site)
	if refusal:
		raise _Stop(CHANGE_STATUS_FAILED, refusal)
	if action == ACTION_APPLY and proposal.change_kind == CHANGE_KIND_CODE:
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
	return allowed_apps


def _failed(result) -> bool:
	return result.timed_out or result.exit_code != 0


def _git_short_line(output: str) -> str:
	"""The last non-empty line of `output`, cleaned then cut to `GIT_SHORT_REASON_MAX_CHARS` (addendum 4 QĐ-D1).

	Control characters become spaces and whitespace collapses; a word holding `/` `\\` `@` `=` `~` or a
	key-like run becomes `GIT_MASKED_WORD`; the cut comes after the masking. Nothing left → "".
	"""
	# Lines end at `\n` only: a `\r` (git progress) is a control character, made a space below.
	lines = [line for line in (output or "").split("\n") if line.strip()]
	if not lines:
		return ""
	text = "".join(" " if unicodedata.category(char) == "Cc" else char for char in lines[-1])
	words = [
		GIT_MASKED_WORD if any(char in word for char in "/\\@=~") or GIT_KEY_LIKE.search(word) else word
		for word in text.split()
	]
	return " ".join(words)[:GIT_SHORT_REASON_MAX_CHARS]


def _commit_failed_reason(result) -> str:
	"""`GIT_COMMIT_FAILED`, ` (quá thời gian)` on a timeout, then the cleaned last git output line (design 3.5)."""
	reason = GIT_COMMIT_FAILED + (GIT_COMMIT_TIMED_OUT_SUFFIX if result.timed_out else "")
	short = _git_short_line(result.output)
	return f"{reason}: {short}" if short else reason


def _git_limit(deadline: float) -> int:
	"""`limit_s` of a git write: at most `GIT_TIMEOUT_S`, cut by the job deadline, never below 1 (design 3.5)."""
	return min(source.GIT_TIMEOUT_S, max(1, int(deadline - time.monotonic())))


def _person(user: str) -> str:
	return change_text.safe_person_name(get_fullname(user))


def _commit_record(
	field: str, full_path: str, sha_before: str, old_head: str, commit: str | None, branch: str | None
) -> dict:
	"""`fields`, `before` and `after` of a `finish` after the commit ran (design-addendum-3 QĐ-B5).

	`field` is `apply_commit_sha` or `undo_commit_sha`; without a commit sha, neither `fields` nor `after`
	carries one.
	"""
	after = {"sha256": file_writer.sha256_of(full_path)}
	fields = {}
	if commit:
		fields[field] = commit
		after["commit"] = commit
	after["branch"] = branch
	return {"fields": fields, "before": {"sha256": sha_before, "head": old_head}, "after": after}


def _apply_record(proposal, full_path: str, old_head: str, commit: str | None, branch: str | None) -> dict:
	return _commit_record("apply_commit_sha", full_path, proposal.base_hash, old_head, commit, branch)


def _undo_record(proposal, full_path: str, old_head: str, commit: str | None, branch: str | None) -> dict:
	return _commit_record("undo_commit_sha", full_path, proposal.after_hash, old_head, commit, branch)


def _apply_postcheck(proposal, state, full_path: str, summary=None):
	"""Design 4.3 step 3.5 (ADR-022 decision 1 step 5); returns the `CommitSummary` of the bot commit."""
	content_after = (proposal.content_after or "").encode("utf-8")
	return _postcheck(
		state,
		proposal.target_branch,
		content_after,
		summary,
		lambda commit, branch: _apply_record(proposal, full_path, state.head, commit, branch),
	)


def _postcheck(state, branch: str, blob: bytes | None, summary, record):
	"""The post-check of design 4.3 step 3.5 and 4.4 step 6; returns the `CommitSummary` of the bot commit.

	The commit must have one parent with `state.head` as its ancestor, only the target path, `branch`, and
	`blob` as the target's bytes (`None`: not in the tree). The bot commit exists (the commit command exited
	0, or HEAD moved to a bot commit whose `summary` is given), so the file is never given back and history
	is never rewritten (design-addendum-3 QĐ-B2 item 1): a check that fails or cannot be read ends the job as
	`Lỗi` `GIT_COMMIT_MISMATCH` with `record(commit, branch)`, keeping the commit sha when it is known.
	"""
	repo, rel, old_head = state.repo_root, state.rel_in_repo, state.head
	try:
		if summary is None:
			summary = source.git_commit_summary(repo)
		matches = (
			len(summary.parents) == 1
			and source.git_is_ancestor(repo, old_head, summary.parents[0]) is True
			and summary.paths == (rel,)
			and summary.branch == branch
			and source.git_blob(repo, summary.commit, rel) == blob
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
	raise _Stop(CHANGE_STATUS_FAILED, GIT_COMMIT_MISMATCH, **record(commit, branch))


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

	def restore() -> bool:
		"""Design 4.3 step 3.6: `content_before` back (read-back hash = `base_hash`), or the new file removed
		and unstaged when `git add` went through."""
		if new_file:
			file_writer.remove_file(full)
			return not added or not _failed(process_runner.git_unstage_new(repo, rel, source.GIT_TIMEOUT_S))
		return file_writer.write_atomic(full, proposal.content_before, new_file=False) == proposal.base_hash

	def give_back(reason: str, expected_head: str):
		"""Design 4.3 step 3.6, then `Lỗi` with `reason`, or `GIT_RESTORE_FAILED` when the repo is not as before."""
		if not _give_back(proposal, full, repo, restore, new_file=new_file, expected_head=expected_head):
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
			_fail_after_commit(
				proposal,
				ACTION_APPLY,
				repo,
				old_head,
				summary,
				exc,
				lambda commit, branch: _apply_record(proposal, full, old_head, commit, branch),
			)
		_give_back_after_crash(
			proposal,
			repo,
			old_head,
			lambda: _give_back(proposal, full, repo, restore, new_file=new_file, expected_head=old_head),
		)
		raise


def _apply_block(proposal, actor: str, allowed_apps, deadline: float) -> None:
	"""CHG-002 T1 walking skeleton: a block of exactly one `Sửa` item takes the one-file apply path.

	The item is seen through the fields `_apply_code` reads, so the guard, stale check, write, one commit
	of that one path, post-check and `Đã áp dụng` are those of the old shape. Later tasks replace this.
	"""
	operations = block.operations_of(proposal)
	if len(operations) != 1 or operations[0].kind != CHANGE_OP_EDIT or block.commands_of(proposal):
		raise _Stop(CHANGE_STATUS_FAILED, change_guard.OP_UNKNOWN)
	(operation,) = operations
	if hashlib.sha256(operation.after.encode("utf-8")).hexdigest() != operation.after_hash:
		raise _Stop(CHANGE_STATUS_FAILED, STORED_HASH_MISMATCH)
	item = frappe._dict(
		name=proposal.name,
		ticket=proposal.ticket,
		target_branch=proposal.target_branch,
		file_path=operation.path,
		is_new_file=0,
		content_before=operation.before,
		content_after=operation.after,
		base_hash=operation.base_hash,
		after_hash=operation.after_hash,
	)
	_apply_code(item, actor, allowed_apps, deadline)


def _give_back(proposal, full: str, repo: str, restore, *, new_file: bool, expected_head: str) -> bool:
	"""Design 4.3 step 3.6 (4.4 step 6 for undo); True when the file, the index entry of the target and HEAD
	are as before.

	`restore()` puts the file back and is True when its read-back hash (or the removal) holds; HEAD must
	still be `expected_head` and git must accept the target (`new_file`: as git sees the target then).
	"""
	try:
		return (
			restore()
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


def _fail_after_commit(proposal, action: str, repo: str, old_head: str, summary, exc: Exception, record):
	"""QĐ-B2 items 1 and 4: the bot commit exists, so the file stays; `Lỗi` with the class name, keeping the
	commit sha when known (`summary`, else a HEAD that moved off `old_head`) with its QĐ-B5 log values from
	`record(commit, branch)`."""
	frappe.db.rollback()
	frappe.log_error(
		TITLE_CHANGE_FAILED, f"proposal={proposal.name} action={action} error={type(exc).__name__}"
	)
	if summary is not None:
		commit, branch = summary.commit, summary.branch
	else:
		head = source.git_head(repo)
		commit, branch = (head if head not in (None, old_head) else None), None
	raise _Stop(CHANGE_STATUS_FAILED, type(exc).__name__, **record(commit, branch)) from exc


def _give_back_after_crash(proposal, repo: str, old_head: str, give_back):
	"""QĐ-B2 item 4 with no bot commit known: `give_back()` only when HEAD is still `old_head` (D-17).

	The caller re-raises the original error, which ends the job as `Lỗi` with its class name; a give-back
	that was skipped or did not hold is recorded in the error log so a person checks the repo.
	"""
	try:
		restored = source.git_head(repo) == old_head and give_back()
	except Exception as exc:
		# Never hide the first error behind one from giving back; record this one and go on.
		frappe.log_error(
			TITLE_CHANGE_FAILED, f"proposal={proposal.name} action=give_back error={type(exc).__name__}"
		)
		return
	if not restored:
		frappe.log_error(TITLE_CHANGE_FAILED, f"proposal={proposal.name} action=give_back restored=False")


def _undo_code(proposal, actor: str, allowed_apps, deadline: float) -> None:
	"""Design 4.4 steps 3 to 7: file hash, git pre-read, write back, one undo commit, post-check, done."""
	new_file = bool(proposal.is_new_file)
	guard = change_guard.check_write_path(proposal.file_path, allowed_apps, new_file=False, read_git=False)
	if guard.reason:
		raise _Stop(CHANGE_STATUS_FAILED, guard.reason)
	full = guard.full_path
	if file_writer.sha256_of(full) != proposal.after_hash:
		raise _Stop(CHANGE_STATUS_FAILED, FILE_CHANGED_AFTER_APPLY)
	# Git pre-check (design 4.4 step 4): a git refusal is `Lỗi`. No "same branch" check: the undo commits on
	# the branch checked out now, only when the apply commit is in its history (ADR-022 decision 6).
	state = source.read_git_state(full, new_file=False, limit_s=_git_limit(deadline))
	if state.refusal:
		raise _Stop(CHANGE_STATUS_FAILED, state.refusal)
	repo, rel, old_head = state.repo_root, state.rel_in_repo, state.head
	in_history = source.git_is_ancestor(repo, str(proposal.apply_commit_sha or ""), old_head)
	if in_history is None:
		raise _Stop(CHANGE_STATUS_FAILED, source.GIT_ERROR)
	if not in_history:
		raise _Stop(CHANGE_STATUS_FAILED, GIT_NOT_ANCESTOR)
	committed = False
	summary = None

	def restore() -> bool:
		"""Design 4.4 step 6: the applied bytes back (a new file is created again), read-back hash = `after_hash`."""
		return (
			file_writer.write_atomic(full, proposal.content_after, new_file=new_file) == proposal.after_hash
		)

	def give_back(reason: str, expected_head: str):
		"""Design 4.4 step 6, then `Lỗi` with `reason`, or `GIT_RESTORE_FAILED` when the repo is not as before.

		The target is back in the tree of HEAD (the apply commit), so git checks it as a changed file."""
		if not _give_back(proposal, full, repo, restore, new_file=False, expected_head=expected_head):
			reason = GIT_RESTORE_FAILED
		raise _Stop(CHANGE_STATUS_FAILED, reason)

	if new_file:
		file_writer.remove_file(full)
		if os.path.lexists(full):
			raise _Stop(CHANGE_STATUS_FAILED, WRITE_MISMATCH)
	elif file_writer.write_atomic(full, proposal.content_before, new_file=False) != proposal.base_hash:
		give_back(WRITE_MISMATCH, old_head)
	try:
		subject, body = change_text.undo_message(
			proposal.name,
			str(proposal.ticket or ""),
			proposal.file_path,
			str(proposal.apply_commit_sha or ""),
			_person(actor),
		)
		result = process_runner.git_commit_only(repo, rel, subject, body, _git_limit(deadline))
		if _failed(result):
			# Design 4.4 step 6 follows 4.3 step 3.4 (D-17, design-addendum-3 QĐ-B2 items 2 and 3).
			summary = _commit_landed(
				repo, old_head, lambda head: give_back(_commit_failed_reason(result), head)
			)
		committed = True
		# D-18: the undo commit of a new file has the path deleted from the tree.
		restored = None if new_file else (proposal.content_before or "").encode("utf-8")
		summary = _postcheck(
			state,
			state.branch,
			restored,
			summary,
			lambda commit, branch: _undo_record(proposal, full, old_head, commit, branch),
		)
		record = _undo_record(proposal, full, old_head, summary.commit, summary.branch)
		transitions.finish(
			proposal.name,
			CHANGE_STATUS_UNDOING,
			CHANGE_STATUS_UNDONE,
			step="undo",
			actor=actor,
			fields=record["fields"],
			before=record["before"],
			after=record["after"],
		)
	except _Stop:
		raise
	except Exception as exc:
		# Design-addendum-3 QĐ-B2 item 4 on the undo side, as in `_apply_code`.
		if committed:
			_fail_after_commit(
				proposal,
				ACTION_UNDO,
				repo,
				old_head,
				summary,
				exc,
				lambda commit, branch: _undo_record(proposal, full, old_head, commit, branch),
			)
		_give_back_after_crash(
			proposal,
			repo,
			old_head,
			lambda: _give_back(proposal, full, repo, restore, new_file=False, expected_head=old_head),
		)
		raise


def _apply_command(proposal, actor: str, deadline: float) -> None:
	"""Design 4.3 step 4: one bench run with the job's remaining budget; no git call (ADR-022 QĐ 1)."""
	args = json.loads(proposal.command_args)
	limit = int(deadline - time.monotonic())
	if limit < 1:
		# Design addendum 2 QĐ-A3: no process when under 1 s is left; no exit code (addendum 3 QĐ-B4).
		no_run = process_runner.CommandResult(
			exit_code=None, output="", duration_ms=0, timed_out=True, not_found=False
		)
		raise _Stop(CHANGE_STATUS_FAILED, COMMAND_OUT_OF_TIME, no_run)
	result = process_runner.run_bench(args, limit)
	# Design 4.3 step 4, in its order: timed out, bench not found, non-zero exit, done.
	if result.timed_out:
		raise _Stop(CHANGE_STATUS_FAILED, COMMAND_OUT_OF_TIME, result)
	if result.not_found:
		raise _Stop(CHANGE_STATUS_FAILED, COMMAND_NOT_FOUND, result)
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
