"""The result line of a change proposal on its ticket (AC-28, CHG-001 design 3).

One core `Comment` of type `Info` under the session user (the approver or undoer): it starts no agent
run, is never read as an instruction and publishes no realtime event (design "Quyết định").
"""

import json

import frappe

from erp_ai.constants import (
	CHANGE_KIND_CODE,
	CHANGE_STATUS_APPLIED,
	CHANGE_STATUS_FAILED,
	CHANGE_STATUS_STALE,
	CHANGE_STATUS_UNDONE,
	PROPOSAL_DOCTYPE,
)

COMMENT_TYPE_INFO = "Info"
TITLE_RESULT_COMMENT_FAILED = "erp_ai: ghi kết quả đề xuất lên phiếu lỗi"
TICKET_DOCTYPE = "HD Ticket"
LINE_SEPARATOR = "; "
REASON_MAX_CHARS = 300
MASKED_WORD = "[đã ẩn]"
SHORT_SHA_CHARS = 12
# Design 2: the only fields read; never `command_output`, `diff` or file content.
RESULT_FIELDS = (
	"name",
	"ticket",
	"change_status",
	"change_kind",
	"is_new_file",
	"file_path",
	"command_args",
	"failure_reason",
	"apply_commit_sha",
	"undo_commit_sha",
	"exit_code",
	"undo_by",
)


def _masked_reason(reason: str | None) -> str:
	"""Whitespace folded, every word holding `://` or `@` masked, then cut to 300 characters.

	Masking comes before the cut so a secret on the cut boundary is never half kept (NFR-8).
	"""
	words = [MASKED_WORD if "://" in word or "@" in word else word for word in (reason or "").split()]
	return " ".join(words)[:REASON_MAX_CHARS]


def _target(fields: dict) -> str:
	if fields.get("change_kind") == CHANGE_KIND_CODE:
		verb = "tạo" if fields.get("is_new_file") else "sửa"
		return f"{verb} {fields.get('file_path')}"
	args = " ".join(json.loads(fields.get("command_args") or "[]"))
	return f"lệnh bench {args}"


def _outcome_line(fields: dict) -> str:
	status = fields.get("change_status")
	if status == CHANGE_STATUS_APPLIED:
		if fields.get("change_kind") == CHANGE_KIND_CODE:
			return f"commit {(fields.get('apply_commit_sha') or '')[:SHORT_SHA_CHARS]}"
		return f"mã thoát {fields.get('exit_code') or 0}"
	if status == CHANGE_STATUS_FAILED:
		line = f"lý do: {_masked_reason(fields.get('failure_reason'))}"
		if fields.get("exit_code"):
			line += f", mã thoát {fields.get('exit_code')}"
		if fields.get("undo_by"):
			line = f"khi hoàn tác, {line}"
		return line
	if status == CHANGE_STATUS_STALE:
		return f"lý do: {_masked_reason(fields.get('failure_reason'))}"
	if status == CHANGE_STATUS_UNDONE:
		return f"commit hoàn tác {(fields.get('undo_commit_sha') or '')[:SHORT_SHA_CHARS]}"
	raise ValueError(f"not a final change status: {status!r}")


def result_lines(fields: dict) -> list[str]:
	"""The result lines of a proposal in a final status (pure, no I/O); other statuses → ValueError."""
	outcome = _outcome_line(fields)
	return [
		f"kết quả đề xuất {fields.get('name')} ({_target(fields)}): {fields.get('change_status')}",
		outcome,
	]


def post_result(proposal_name: str) -> str | None:
	"""Write one `Info` line on the proposal's ticket as the session user and return the Comment name.

	No proposal, no ticket or a deleted ticket → None, nothing written. Never commits and never catches:
	the caller (the change job) commits, or rolls back and logs.
	"""
	fields = frappe.db.get_value(PROPOSAL_DOCTYPE, proposal_name, list(RESULT_FIELDS), as_dict=True)
	if not fields or not fields.ticket or not frappe.db.exists(TICKET_DOCTYPE, fields.ticket):
		return None
	text = frappe.utils.escape_html(LINE_SEPARATOR.join(result_lines(fields)))
	return frappe.get_doc(TICKET_DOCTYPE, fields.ticket).add_comment(COMMENT_TYPE_INFO, text).name


# CHG-002 design 3.7: the only fields the restart notice reads; never `upstream_ref` (a remote URL).
NOTICE_FIELDS = (
	"name",
	"ticket",
	"app",
	"target_branch",
	"applied_branch",
	"apply_commit_sha",
	"undo_commit_sha",
)
NOTICE_ACTIONS = {"apply": ("áp dụng", "apply_commit_sha"), "undo": ("hoàn tác", "undo_commit_sha")}


def restart_notice_text(fields: dict, action: str) -> str:
	"""The comment written before a restart (CHG-002 design 3.7, AC-46 b); pure, unknown action → KeyError.

	The action's sha set → the commit template: commit, branch, app and the `git revert` recovery.
	The sha empty (`None` or "") → the no-commit template of addendum-5 P-2: only `bench restart`, and
	neither `app` nor a branch is read.
	"""
	verb, sha_field = NOTICE_ACTIONS[action]
	sha = fields.get(sha_field) or ""
	if not sha:
		return (
			f"Đề xuất {fields.get('name')} đã {verb}. Hệ thống sắp restart bench. "
			"Nếu site không lên sau vài phút: trên máy chủ chạy `bench restart`."
		)
	app = fields.get("app")
	branch = fields.get("applied_branch") or fields.get("target_branch")
	return (
		f"Đề xuất {fields.get('name')} đã {verb}: commit {sha[:SHORT_SHA_CHARS]} trên nhánh {branch} của app {app}. "
		"Hệ thống sắp restart bench. Nếu site không lên sau vài phút: trên máy chủ chạy "
		f"`git -C apps/{app} revert --no-edit {sha}` rồi `bench restart`."
	)


def post_restart_notice(name: str, action: str) -> str | None:
	"""Write one `Info` notice on the proposal's ticket as the session user and return the Comment name.

	Same `add_comment` call as `post_result` (addendum-3 RQ-4). No proposal or no ticket → None. A failed
	write is logged like the job logs `post_result` and returns None: the restart still goes ahead (STD-ERR-1).
	Never commits: the caller does.
	"""
	try:
		fields = frappe.db.get_value(PROPOSAL_DOCTYPE, name, list(NOTICE_FIELDS), as_dict=True)
		if not fields or not fields.ticket or not frappe.db.exists(TICKET_DOCTYPE, fields.ticket):
			return None
		text = frappe.utils.escape_html(restart_notice_text(fields, action))
		return frappe.get_doc(TICKET_DOCTYPE, fields.ticket).add_comment(COMMENT_TYPE_INFO, text).name
	except Exception as exc:
		frappe.log_error(
			TITLE_RESULT_COMMENT_FAILED, f"proposal={name} action={action} error={type(exc).__name__}"
		)
		return None
