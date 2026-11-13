"""Change-proposal tools: the model proposes one file change or one bench command; nothing is written to
disk and no command runs here. A person approves on the proposal form, then the change job applies it."""

import difflib
import hashlib
import json
import os

import frappe

from erp_ai.agent import change_link, change_text
from erp_ai.agent.tools import change_guard
from erp_ai.agent.tools.registry import ToolContext, ToolSpec
from erp_ai.constants import (
	CHANGE_KIND_CODE,
	CHANGE_KIND_COMMAND,
	CHANGE_STATUS_PENDING,
	PROPOSAL_DOCTYPE,
	PROPOSAL_TEXT_MAX_CHARS,
	REPLACE_MAX_ITEMS,
)

GROUP = "change_propose"
TICKET_DOCTYPE = "HD Ticket"
REASON_MAX_CHARS = 1000
PATH_MAX_CHARS = 300
DIFF_CONTEXT_LINES = 3
NO_INSTRUCTOR = "không có người ra lệnh"
NO_CREATE_PERMISSION = "thiếu quyền tạo đề xuất"
FILE_MISSING = "file không tồn tại; dùng propose_new_file để tạo file mới"
FILE_EXISTS = "file đã tồn tại; dùng propose_file_change để sửa"
FOLDER_MISSING = "thư mục chứa file chưa tồn tại"
NOT_TEXT = "file không phải văn bản UTF-8"
TOO_LONG = f"nội dung file vượt {PROPOSAL_TEXT_MAX_CHARS} ký tự"
NO_CHANGE = "nội dung sau khi sửa giống hệt nội dung hiện tại"
BAD_EDIT = "mỗi phần tử của edits phải là object có old và new là chuỗi, old không rỗng"


def _fail(reason: str) -> dict:
	return {"ok": False, "reason": reason}


def _sha256(data: bytes) -> str:
	return hashlib.sha256(data).hexdigest()


def _entry_refusal(ctx: ToolContext) -> dict | None:
	if not ctx.instructor:
		return _fail(NO_INSTRUCTOR)
	if not frappe.has_permission(PROPOSAL_DOCTYPE, "create"):
		return _fail(NO_CREATE_PERMISSION)
	return None


def _apply_edits(text: str, edits: list) -> tuple[str | None, str | None]:
	"""Apply each {old, new} once, in order; (new text, None) or (None, refusal reason)."""
	for index, edit in enumerate(edits, start=1):
		if (
			not isinstance(edit, dict)
			or set(edit) != {"old", "new"}
			or not isinstance(edit["old"], str)
			or not isinstance(edit["new"], str)
			or not edit["old"]
		):
			return None, BAD_EDIT
		count = text.count(edit["old"])
		if count != 1:
			return None, f"edits[{index}].old xuất hiện {count} lần trong file, cần đúng 1 lần"
		text = text.replace(edit["old"], edit["new"])
	return text, None


def _diff(rel_path: str, before: str, after: str) -> str:
	lines = difflib.unified_diff(
		before.splitlines(keepends=True),
		after.splitlines(keepends=True),
		fromfile=f"a/{rel_path}",
		tofile=f"b/{rel_path}",
		n=DIFF_CONTEXT_LINES,
	)
	return "".join(line if line.endswith("\n") else line + "\n" for line in lines)


def _comment(ctx: ToolContext, proposal) -> None:
	"""One ticket comment with the notes the reviewer needs (design 3.9) and the Duyệt / Từ chối links."""
	escape = frappe.utils.escape_html
	target = proposal.file_path or " ".join(json.loads(proposal.command_args or "[]"))
	lines = [
		f"Đã tạo đề xuất {proposal.name} ({proposal.change_kind}: {target}), đang {CHANGE_STATUS_PENDING}.",
		*change_text.proposal_notes(proposal),
	]
	approve = change_link.decision_path(proposal.name, change_link.ACTION_APPROVE)
	reject = change_link.decision_path(proposal.name, change_link.ACTION_REJECT)
	form = f"/app/erp-ai-change-proposal/{proposal.name}"
	html = "".join(f"<p>{escape(line)}</p>" for line in lines)
	html += (
		f'<p><a href="{escape(approve)}"><strong>Duyệt</strong></a> · '
		f'<a href="{escape(reject)}"><strong>Từ chối</strong></a> · '
		f'<a href="{escape(form)}">Xem nội dung thay đổi</a></p>'
	)
	frappe.get_doc(TICKET_DOCTYPE, ctx.ticket_name).new_comment(html)


def _insert(ctx: ToolContext, values: dict) -> dict:
	proposal = frappe.get_doc(
		{
			"doctype": PROPOSAL_DOCTYPE,
			"ticket": ctx.ticket_name,
			"run_id": ctx.run_id,
			"instructor": ctx.instructor,
			**values,
		}
	)
	proposal.insert()
	_comment(ctx, proposal)
	return {"ok": True, "proposal": proposal.name, "status": proposal.change_status}


def _code_values(guard, *, before: str | None, after: str, reason: str) -> dict:
	new_file = before is None
	return {
		"change_kind": CHANGE_KIND_CODE,
		"app": guard.app,
		"file_path": guard.rel_path,
		"is_new_file": int(new_file),
		"reversible": 1,
		"base_hash": None if new_file else _sha256(before.encode("utf-8")),
		"content_before": before,
		"content_after": after,
		"after_hash": _sha256(after.encode("utf-8")),
		"diff": _diff(guard.rel_path, before or "", after),
		"reason": reason,
		"target_branch": guard.git.branch,
		"upstream_ref": guard.git.upstream_ref,
		"ahead_count": guard.git.ahead_count,
		"is_core_app": int(guard.is_core_app),
	}


def propose_file_change(args: dict, ctx: ToolContext) -> dict:
	if refusal := _entry_refusal(ctx):
		return refusal
	guard = change_guard.check_write_path(args["path"], ctx.allowed_apps, new_file=False)
	if guard.reason:
		return _fail(guard.reason)
	if not os.path.isfile(guard.full_path):
		return _fail(FILE_MISSING)
	with open(guard.full_path, "rb") as handle:
		data = handle.read(PROPOSAL_TEXT_MAX_CHARS * 4 + 1)
	try:
		before = data.decode("utf-8")
	except UnicodeDecodeError:
		return _fail(NOT_TEXT)
	if len(before) > PROPOSAL_TEXT_MAX_CHARS:
		return _fail(TOO_LONG)
	after, reason = _apply_edits(before, args["edits"])
	if reason:
		return _fail(reason)
	if after == before:
		return _fail(NO_CHANGE)
	if len(after) > PROPOSAL_TEXT_MAX_CHARS:
		return _fail(TOO_LONG)
	return _insert(ctx, _code_values(guard, before=before, after=after, reason=args["reason"]))


def propose_new_file(args: dict, ctx: ToolContext) -> dict:
	if refusal := _entry_refusal(ctx):
		return refusal
	guard = change_guard.check_write_path(args["path"], ctx.allowed_apps, new_file=True)
	if guard.reason:
		return _fail(guard.reason)
	if os.path.lexists(guard.full_path):
		return _fail(FILE_EXISTS)
	if not os.path.isdir(os.path.dirname(guard.full_path)):
		return _fail(FOLDER_MISSING)
	return _insert(ctx, _code_values(guard, before=None, after=args["content"], reason=args["reason"]))


def propose_bench_command(args: dict, ctx: ToolContext) -> dict:
	if refusal := _entry_refusal(ctx):
		return refusal
	built = change_guard.build_bench_args(
		args["command"], args.get("app"), ctx.allowed_apps, frappe.local.site
	)
	if isinstance(built, str):
		return _fail(built)
	values = {
		"change_kind": CHANGE_KIND_COMMAND,
		"app": args.get("app"),
		"command_args": json.dumps(built, ensure_ascii=False),
		"reversible": 0,
		"reason": args["reason"],
	}
	return _insert(ctx, values)


_PATH = {"type": "string", "minLength": 3, "maxLength": PATH_MAX_CHARS}
_REASON = {"type": "string", "minLength": 1, "maxLength": REASON_MAX_CHARS}

TOOLS: list[ToolSpec] = [
	ToolSpec(
		name="propose_file_change",
		group=GROUP,
		schema={
			"name": "propose_file_change",
			"description": (
				"Tạo đề xuất sửa một file đã có trong apps/ (đường dẫn tính từ apps/, ví dụ "
				"helpdesk/helpdesk/api/ticket.py). edits là danh sách {old, new}: mỗi old phải xuất hiện "
				"đúng 1 lần trong file. Chỉ tạo đề xuất Chờ duyệt, chưa ghi gì xuống đĩa."
			),
			"input_schema": {
				"type": "object",
				"properties": {
					"path": _PATH,
					"edits": {"type": "array", "maxItems": REPLACE_MAX_ITEMS, "items": {"type": "object"}},
					"reason": _REASON,
				},
				"required": ["path", "edits", "reason"],
			},
		},
		handler=propose_file_change,
	),
	ToolSpec(
		name="propose_new_file",
		group=GROUP,
		schema={
			"name": "propose_new_file",
			"description": (
				"Tạo đề xuất thêm một file mới trong apps/ (thư mục chứa phải có sẵn). "
				"Chỉ tạo đề xuất Chờ duyệt, chưa ghi gì xuống đĩa."
			),
			"input_schema": {
				"type": "object",
				"properties": {
					"path": _PATH,
					"content": {"type": "string", "minLength": 1, "maxLength": PROPOSAL_TEXT_MAX_CHARS},
					"reason": _REASON,
				},
				"required": ["path", "content", "reason"],
			},
		},
		handler=propose_new_file,
	),
	ToolSpec(
		name="propose_bench_command",
		group=GROUP,
		schema={
			"name": "propose_bench_command",
			"description": (
				"Tạo đề xuất chạy một lệnh bench cho site đang chạy. build cần app; các lệnh khác không nhận "
				"app. Lệnh không hoàn tác được. Chỉ tạo đề xuất Chờ duyệt, chưa chạy gì."
			),
			"input_schema": {
				"type": "object",
				"properties": {
					"command": {"type": "string", "enum": list(change_guard.BENCH_COMMANDS)},
					"app": {"type": "string", "minLength": 1, "maxLength": 80},
					"reason": _REASON,
				},
				"required": ["command", "reason"],
			},
		},
		handler=propose_bench_command,
	),
]
