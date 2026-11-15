"""The result line of a change proposal on its ticket (AC-28, CHG-001 design 3).

One core `Comment` of type `Info` under the session user (the approver or undoer): it starts no agent
run, is never read as an instruction and publishes no realtime event (design "Quyết định").

A block proposal (CHG-002 design 3.7, addendum-7 P7-1..P7-8) adds one element per item, its commits, the
commands that ran, the restart and what a person still has to do; it reads the stored doc for them, and of
`command_results` only `COMMAND_RESULT_KEYS` (never `output`). The old shape keeps its CHG-001 text.
"""

import json
import re
from pathlib import PurePosixPath

import frappe

from erp_ai.agent import change_text
from erp_ai.agent.changes import block
from erp_ai.constants import (
	CHANGE_KIND_CODE,
	CHANGE_OP_RENAME,
	CHANGE_STATUS_APPLIED,
	CHANGE_STATUS_FAILED,
	CHANGE_STATUS_STALE,
	CHANGE_STATUS_UNDONE,
	PROPOSAL_DOCTYPE,
	RESTART_STATUS_CONFIRMED,
	RESTART_STATUS_LAUNCH_FAILED,
	RESTART_STATUS_SENT,
	RESTART_STATUS_UNCONFIRMED,
	RESTART_TIMEOUT_S,
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
# Addendum-7 P7-1: the only keys of a `command_results` item the block comment reads; never `output`.
COMMAND_RESULT_KEYS = ("args", "exit_code", "timed_out")
# P7-4: a reason naming item n (`mục n (…` or `ghi mục n (…`) is attached to that item's element.
ITEM_REASON = re.compile(r"^(?:ghi )?mục (\d+) \(")
BUILD_SUFFIXES = (".js", ".ts", ".vue", ".css", ".scss", ".less")
MIGRATE_SUFFIX = ".json"
ITEM_UNDONE = "đã hoàn tác"
ITEM_APPLIED = "đã áp dụng"
ITEM_NOT_APPLIED = "chưa áp dụng"
# P7-7: the restart word once the job got past the restart step, by `restart_status`.
RESTART_WORDS = {
	RESTART_STATUS_SENT: "đã gửi",
	RESTART_STATUS_LAUNCH_FAILED: "lỗi khởi chạy",
	RESTART_STATUS_CONFIRMED: "đã xác nhận",
	RESTART_STATUS_UNCONFIRMED: "chưa xác nhận",
}
RESTART_NOT_RUN = "không chạy"
RESTART_NOT_NEEDED = "không cần"
# P7-8: what a person still has to do, in this order; no hint holds a comma.
TODO_PREFIX = "việc người còn phải làm: "
TODO_NONE = "không"
TODO_SEPARATOR = ", "
TODO_RESTART = "restart bench"
TODO_SENT = (
	f"nếu sau {RESTART_TIMEOUT_S // 60} phút form đề xuất chưa ghi "
	'"Đã xác nhận" thì restart bench (có thể chưa được cấp quyền restart)'
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


def result_lines(fields: dict, *, doc=None) -> list[str]:
	"""The result lines of a proposal in a final status (no I/O); other statuses → ValueError.

	`doc` is the stored proposal. A block (`doc is not None and block.is_block(doc)`) gets the block
	elements of addendum-7 P7-1..P7-8, reading `doc` and `frappe.local.site`; otherwise the old text, byte
	for byte. Raises ValueError too for an unreadable `command_results` or an unknown `restart_status`.
	"""
	outcome = _outcome_line(fields)
	if doc is None or not block.is_block(doc):
		return [
			f"kết quả đề xuất {fields.get('name')} ({_target(fields)}): {fields.get('change_status')}",
			outcome,
		]
	return _block_lines(fields, doc)


def _block_lines(fields: dict, doc) -> list[str]:
	"""P7-1 order: line 1, the unattached reason, items, commits, commands, restart, what is left to do."""
	operations = block.operations_of(doc)
	commands = block.commands_of(doc)
	status = fields.get("change_status")
	undoing = bool(fields.get("undo_by"))
	apply_sha = fields.get("apply_commit_sha") or ""
	undo_sha = fields.get("undo_commit_sha") or ""
	files_changed = bool(undo_sha) if undoing else bool(apply_sha)
	# P7-6: an undo that stopped before its commit ran no command; the stored results are the apply's.
	results = [] if undoing and not undo_sha else _command_results(doc.get("command_results"))
	restart = _restart_word(status, doc.get("restart_status"), commands)

	label = (
		_masked_reason(change_text.block_label(operations)) if operations else f"{len(commands)} lệnh bench"
	)
	lines = [f"kết quả đề xuất {fields.get('name')} ({label}): {status}"]
	items = [_item_element(operation, undo_sha, apply_sha) for operation in operations]
	reason, item_number = _block_reason(fields, len(operations))
	if item_number:
		items[item_number - 1] += f", {reason}"
	elif reason:
		lines.append(reason)
	lines += items
	if apply_sha:
		lines.append(f"commit {apply_sha[:SHORT_SHA_CHARS]}")
	if undo_sha:
		lines.append(f"commit hoàn tác {undo_sha[:SHORT_SHA_CHARS]}")
	lines += [_command_element(result) for result in results]
	lines.append(f"restart: {restart}")
	hints = _todo_hints(restart, files_changed, operations, results, doc.get("app"))
	lines.append(TODO_PREFIX + (TODO_SEPARATOR.join(hints) or TODO_NONE))
	return lines


def _item_element(operation, undo_sha: str, apply_sha: str) -> str:
	"""P7-3: the commit body's verb, the path(s) and the item's state from the two shas."""
	if undo_sha:
		state = ITEM_UNDONE
	elif apply_sha:
		state = ITEM_APPLIED
	else:
		state = ITEM_NOT_APPLIED
	target = _masked_reason(operation.path)
	if operation.kind == CHANGE_OP_RENAME:
		target += f" → {_masked_reason(operation.new_path)}"
	return f"{change_text._ITEM_VERBS[operation.kind]} {target}: {state}"


def _block_reason(fields: dict, item_count: int) -> tuple[str, int]:
	"""P7-4: the reason text ("" when none) and the item number it is attached to (0 when none)."""
	raw = (fields.get("failure_reason") or "").strip()
	status = fields.get("change_status")
	if status not in (CHANGE_STATUS_FAILED, CHANGE_STATUS_STALE) or not raw:
		return "", 0
	reason = f"lý do: {_masked_reason(raw)}"
	if status == CHANGE_STATUS_FAILED and fields.get("undo_by"):
		reason = f"khi hoàn tác, {reason}"
	match = ITEM_REASON.match(raw)
	number = int(match.group(1)) if match else 0
	return reason, number if 1 <= number <= item_count else 0


def _command_results(stored) -> list[dict]:
	"""P7-6: the stored results, read strictly; only `COMMAND_RESULT_KEYS` of each item are kept.

	Raises ValueError unless it is a JSON list of objects whose `args` is a list of strings and whose
	`exit_code` is an int when the command did not time out.
	"""
	try:
		results = json.loads(stored or "[]")
	except ValueError as exc:
		raise ValueError(f"command_results không đọc được: {exc}") from exc
	if not isinstance(results, list) or not all(isinstance(result, dict) for result in results):
		raise ValueError(f"command_results không đọc được: {stored!r}")
	kept = [{key: result.get(key) for key in COMMAND_RESULT_KEYS} for result in results]
	for result in kept:
		args, exit_code = result["args"], result["exit_code"]
		if not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
			raise ValueError(f"command_results không đọc được: args {args!r}")
		if not result["timed_out"] and (not isinstance(exit_code, int) or isinstance(exit_code, bool)):
			raise ValueError(f"command_results không đọc được: exit_code {exit_code!r}")
	return kept


def _command_element(result: dict) -> str:
	argv = _masked_reason(" ".join(result["args"]))
	if result["timed_out"]:
		return f"bench {argv}: quá thời gian"
	return f"bench {argv}: mã thoát {result['exit_code']}"


def _restart_word(status: str, restart_status: str | None, commands: list) -> str:
	"""P7-7: `restart_status` is read only past the restart step (Đã áp dụng, Đã hoàn tác)."""
	if status in (CHANGE_STATUS_APPLIED, CHANGE_STATUS_UNDONE) and restart_status:
		if restart_status not in RESTART_WORDS:
			raise ValueError(f"restart_status không hỗ trợ: {restart_status!r}")
		return RESTART_WORDS[restart_status]
	if change_text._RESTART_ARGV in commands:
		return RESTART_NOT_RUN
	return RESTART_NOT_NEEDED


def _todo_hints(restart: str, files_changed: bool, operations, results: list[dict], app) -> list[str]:
	"""P7-8: the four hints, in order, each at most once."""
	hints = []
	if restart in (
		RESTART_WORDS[RESTART_STATUS_LAUNCH_FAILED],
		RESTART_WORDS[RESTART_STATUS_UNCONFIRMED],
	) or (restart == RESTART_NOT_RUN and files_changed):
		hints.append(TODO_RESTART)
	if restart == RESTART_WORDS[RESTART_STATUS_SENT]:
		hints.append(TODO_SENT)
	if not files_changed:
		return hints
	suffixes = {
		PurePosixPath(path).suffix.lower()
		for operation in operations
		for path in (operation.path, operation.new_path)
		if path
	}
	if suffixes.intersection(BUILD_SUFFIXES) and not any(_built(result, app) for result in results):
		hints.append(f"chạy bench build --app {_masked_reason(app)}")
	if MIGRATE_SUFFIX in suffixes and not any(
		_done(result) and "migrate" in result["args"] for result in results
	):
		hints.append(f"chạy bench --site {frappe.local.site} migrate")
	return hints


def _done(result: dict) -> bool:
	return result["exit_code"] == 0 and not result["timed_out"]


def _built(result: dict, app) -> bool:
	"""A `build` that finished with 0 and covers `app` (no `--app`, or `--app {app}`)."""
	args = result["args"]
	if args[:1] != ["build"] or not _done(result):
		return False
	if "--app" not in args:
		return True
	position = args.index("--app") + 1
	return position < len(args) and args[position] == app


def post_result(proposal_name: str) -> str | None:
	"""Write one `Info` line on the proposal's ticket as the session user and return the Comment name.

	The stored doc is passed to `result_lines`, so a block gets its own elements (addendum-3 RQ-3).
	No proposal, no ticket or a deleted ticket → None, nothing written. Never commits and never catches:
	the caller (the change job) commits, or rolls back and logs.
	"""
	fields = frappe.db.get_value(PROPOSAL_DOCTYPE, proposal_name, list(RESULT_FIELDS), as_dict=True)
	if not fields or not fields.ticket or not frappe.db.exists(TICKET_DOCTYPE, fields.ticket):
		return None
	doc = frappe.get_doc(PROPOSAL_DOCTYPE, proposal_name)
	text = frappe.utils.escape_html(LINE_SEPARATOR.join(result_lines(fields, doc=doc)))
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
