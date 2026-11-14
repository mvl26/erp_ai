"""Change-proposal tools: the model proposes one file change or one bench command; nothing is written to
disk and no command runs here. A person approves on the proposal form, then the change job applies it."""

import difflib
import hashlib
import itertools
import json
import os

import frappe

from erp_ai.agent import change_link, change_text
from erp_ai.agent.agent_write_guard import allow_agent_write
from erp_ai.agent.tools import change_guard, source
from erp_ai.agent.tools.registry import ToolContext, ToolSpec
from erp_ai.agent.tools.registry import _invalid as registry_invalid  # design-addendum-2 A2-2
from erp_ai.constants import (
	CHANGE_KIND_CODE,
	CHANGE_KIND_COMMAND,
	CHANGE_MAX_FILE_OPS,
	CHANGE_OP_EDIT,
	PROPOSAL_DOCTYPE,
	PROPOSAL_TEXT_MAX_CHARS,
	REPLACE_MAX_ITEMS,
)

GROUP = "change_propose"
PROPOSE_TOOL_NAMES = ("propose_file_change", "propose_new_file", "propose_bench_command")
TICKET_DOCTYPE = "HD Ticket"
REASON_MAX_CHARS = 1000
PATH_MAX_CHARS = 300
APP_MAX_CHARS = 100
DIFF_CONTEXT_LINES = 3
PROPOSAL_FILE_MAX_BYTES = source.SEARCH_FILE_MAX_BYTES
COMMENT_DOCTYPE = "Comment"
NO_INSTRUCTOR = "không có người ra lệnh"
# Design table 3.1: these sentences are the contract with the model and the tests.
NO_PERMISSION = "thiếu quyền tạo đề xuất"
NO_COMMENT_PERMISSION = "thiếu quyền tạo comment"
NOT_FOUND = "file không tồn tại"
TOO_LARGE = "file lớn hơn 1 MiB"
NOT_UTF8 = "file không phải UTF-8"
EDIT_SHAPE = f"find và replace phải cùng số phần tử, từ 1 đến {REPLACE_MAX_ITEMS}"
EDIT_NOT_FOUND = "đoạn find[{index}] không có trong file"
EDIT_AMBIGUOUS = "đoạn find[{index}] xuất hiện nhiều hơn một lần"
EDIT_OVERLAP = "các đoạn find chồng nhau"
NO_CHANGE = "nội dung sau trùng nội dung trước"
EXISTS = "file đã tồn tại"
NO_PARENT = "thư mục cha chưa có"
# CHG-002 design 3.1: the fields of an `edit` item of `changes`.
EDIT_FIELDS = {"action", "path", "find", "replace"}
LEGACY_EDIT_KEYS = ("path", "find", "replace")


def _fail(reason: str) -> dict:
	return {"ok": False, "reason": reason}


def _sha256(data: bytes) -> str:
	return hashlib.sha256(data).hexdigest()


def _entry_refusal(ctx: ToolContext) -> dict | None:
	if not ctx.instructor:
		return _fail(NO_INSTRUCTOR)
	if not frappe.has_permission(PROPOSAL_DOCTYPE, "create"):
		return _fail(NO_PERMISSION)
	if not frappe.has_permission(COMMENT_DOCTYPE, "create"):
		return _fail(NO_COMMENT_PERMISSION)
	return None


def _apply_edits(text: str, find: list, replace: list) -> tuple[str | None, str | None]:
	"""Replace each find[i] (exactly once in `text`, spans not overlapping) by replace[i], by position
	on the original text (design 3.1); (new text, None) or (None, refusal reason)."""
	if len(find) != len(replace) or not 1 <= len(find) <= REPLACE_MAX_ITEMS:
		return None, EDIT_SHAPE
	spans = []
	for index, needle in enumerate(find):
		start = text.find(needle)
		if start < 0:
			return None, EDIT_NOT_FOUND.format(index=index)
		if text.find(needle, start + 1) >= 0:
			return None, EDIT_AMBIGUOUS.format(index=index)
		spans.append((start, start + len(needle), replace[index]))
	spans.sort()
	if any(end > next_start for (_, end, _), (next_start, _, _) in itertools.pairwise(spans)):
		return None, EDIT_OVERLAP
	pieces, cursor = [], 0
	for start, end, new in spans:
		pieces += [text[cursor:start], new]
		cursor = end
	pieces.append(text[cursor:])
	return "".join(pieces), None


def _diff(rel_path: str, before: str, after: str) -> str:
	lines = difflib.unified_diff(
		before.splitlines(keepends=True),
		after.splitlines(keepends=True),
		fromfile=f"a/{rel_path}",
		tofile=f"b/{rel_path}",
		n=DIFF_CONTEXT_LINES,
	)
	return "".join(line if line.endswith("\n") else line + "\n" for line in lines)


def _comment(ctx: ToolContext, proposal) -> str:
	"""One ticket comment (design 3.8): the escaped first sentence, the notes of design 3.9 and the
	Duyệt / Từ chối links; returns the Comment name. A block (CHG-002 T1) names its first item's path."""
	escape = frappe.utils.escape_html
	if proposal.change_kind == CHANGE_KIND_CODE:
		verb = "tạo" if proposal.is_new_file else "sửa"
		path = proposal.operations[0].file_path if proposal.get("operations") else proposal.file_path
		target = f"{verb} <code>{escape(path)}</code>"
	else:
		args = " ".join(json.loads(proposal.command_args or "[]"))
		target = f"lệnh <code>bench {escape(args)}</code>"
	form = f"/app/erp-ai-change-proposal/{proposal.name}"
	html = f'<p>Đề xuất <a href="{escape(form)}">{escape(proposal.name)}</a> đang chờ duyệt: {target}.</p>'
	html += "".join(f"<p>{escape(line)}</p>" for line in change_text.proposal_notes(proposal))
	approve = change_link.decision_path(proposal.name, change_link.ACTION_APPROVE)
	reject = change_link.decision_path(proposal.name, change_link.ACTION_REJECT)
	html += (
		f'<p><a href="{escape(approve)}"><strong>Duyệt</strong></a> · '
		f'<a href="{escape(reject)}"><strong>Từ chối</strong></a> · '
		f'<a href="{escape(form)}">Xem nội dung thay đổi</a></p>'
	)
	return frappe.get_doc(TICKET_DOCTYPE, ctx.ticket_name).new_comment(html)


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
	# ADR-023 QĐ 5 valid path 2: the only opening of the proposal guard for the agent account.
	with allow_agent_write():
		proposal.insert()
	comment = _comment(ctx, proposal)
	return {"ok": True, "proposal": proposal.name, "status": proposal.change_status, "comment": comment}


def _code_values(guard, *, before: str | None, after: str, reason: str) -> dict:
	new_file = before is None
	return {
		"change_kind": CHANGE_KIND_CODE,
		"app": guard.app,
		"file_path": guard.rel_path,
		"is_new_file": int(new_file),
		"reversible": 1,
		"base_hash": "" if new_file else _sha256(before.encode("utf-8")),
		"content_before": "" if new_file else before,
		"content_after": after,
		"after_hash": _sha256(after.encode("utf-8")),
		"diff": _diff(guard.rel_path, before or "", after),
		"reason": reason,
		"target_branch": guard.git.branch,
		"upstream_ref": guard.git.upstream_ref,
		"ahead_count": guard.git.ahead_count,
		"is_core_app": int(guard.is_core_app),
	}


def _edited(path: str, find: list, replace: list, ctx: ToolContext):
	"""Guard `path` as a changed file, read it and apply the edits; (guard, before, after, None) or a refusal
	reason as the last item."""
	guard = change_guard.check_write_path(path, ctx.allowed_apps, new_file=False)
	if guard.reason:
		return None, None, None, guard.reason
	if not os.path.isfile(guard.full_path):
		return None, None, None, NOT_FOUND
	with open(guard.full_path, "rb") as handle:
		data = handle.read(PROPOSAL_FILE_MAX_BYTES + 1)
	if len(data) > PROPOSAL_FILE_MAX_BYTES:
		return None, None, None, TOO_LARGE
	try:
		before = data.decode("utf-8")
	except UnicodeDecodeError:
		return None, None, None, NOT_UTF8
	after, reason = _apply_edits(before, find, replace)
	if reason:
		return None, None, None, reason
	if after == before:
		return None, None, None, NO_CHANGE
	return guard, before, after, None


def _is_text_list(value) -> bool:
	return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _propose_block(changes: list, commands: list | None, reason: str, ctx: ToolContext) -> dict:
	"""CHG-002 T1 walking skeleton of the block path (design 3.1): only `edit` items, no command.

	Every item goes through `check_write_path`; one parent proposal is inserted with one child row per item
	and the scalar file fields left empty. `commands` is not in the schema yet, so it is always `None`.
	The block checks of design 3.2 (`check_block`) replace this skeleton in later tasks.
	"""
	if not changes:
		return _fail(change_guard.BLOCK_EMPTY)
	rows, diffs, first = [], [], None
	for change in changes:
		if change.get("action") != "edit":
			return _fail(change_guard.OP_UNKNOWN)
		find, replace = change.get("find"), change.get("replace")
		if set(change) != EDIT_FIELDS or not _is_text_list(find) or not _is_text_list(replace):
			return _fail(change_guard.OP_FIELDS.format(action="edit"))
		guard, before, after, refusal = _edited(change["path"], find, replace, ctx)
		if refusal:
			return _fail(refusal)
		first = first or guard
		rows.append(
			{
				"operation": CHANGE_OP_EDIT,
				"file_path": guard.rel_path,
				"content_before": before,
				"content_after": after,
				"base_hash": _sha256(before.encode("utf-8")),
				"after_hash": _sha256(after.encode("utf-8")),
			}
		)
		diffs.append(_diff(guard.rel_path, before, after))
	values = {
		"change_kind": CHANGE_KIND_CODE,
		"app": first.app,
		"reversible": 1,
		"operations": rows,
		"diff": "".join(diffs),
		"reason": reason,
		"target_branch": first.git.branch,
		"upstream_ref": first.git.upstream_ref,
		"ahead_count": first.git.ahead_count,
		"is_core_app": int(first.is_core_app),
	}
	return {**_insert(ctx, values), "branch": first.git.branch}


def propose_file_change(args: dict, ctx: ToolContext) -> dict:
	if refusal := _entry_refusal(ctx):
		return refusal
	if "changes" in args:
		if "path" in args:
			return _fail(change_guard.BLOCK_SHAPE)
		return _propose_block(args["changes"], args.get("commands"), args["reason"], ctx)
	# The old shape: the schema no longer requires these keys, so a missing one is refused as before.
	for key in LEGACY_EDIT_KEYS:
		if key not in args:
			return registry_invalid(key)
	guard, before, after, reason = _edited(args["path"], args["find"], args["replace"], ctx)
	if reason:
		return _fail(reason)
	result = _insert(ctx, _code_values(guard, before=before, after=after, reason=args["reason"]))
	return {**result, "branch": guard.git.branch}


def propose_new_file(args: dict, ctx: ToolContext) -> dict:
	if refusal := _entry_refusal(ctx):
		return refusal
	guard = change_guard.check_write_path(args["path"], ctx.allowed_apps, new_file=True)
	if guard.reason:
		return _fail(guard.reason)
	if os.path.lexists(guard.full_path):
		return _fail(EXISTS)
	if not os.path.isdir(os.path.dirname(guard.full_path)):
		return _fail(NO_PARENT)
	result = _insert(ctx, _code_values(guard, before=None, after=args["content"], reason=args["reason"]))
	return {**result, "branch": guard.git.branch}


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
		# design 2.1: a bench command carries no git field
		"target_branch": "",
		"upstream_ref": "",
		"ahead_count": 0,
		"is_core_app": 0,
	}
	return _insert(ctx, values)


_PATH = {"type": "string", "minLength": 1, "maxLength": PATH_MAX_CHARS}
_REASON = {"type": "string", "minLength": 1, "maxLength": REASON_MAX_CHARS}
_FIND_ITEM = {"type": "string", "minLength": 1, "maxLength": PROPOSAL_TEXT_MAX_CHARS}
_REPLACE_ITEM = {"type": "string", "maxLength": PROPOSAL_TEXT_MAX_CHARS}
# CHG-002 design 3.1: one item of `changes`.
_CHANGE_ITEM = {
	"type": "object",
	"properties": {
		"action": {"type": "string", "enum": ["edit", "create", "delete", "rename"]},
		"path": _PATH,
		"new_path": _PATH,
		"find": {"type": "array", "items": {"type": "string", "minLength": 1}},
		"replace": {"type": "array", "items": {"type": "string"}},
		"content": {"type": "string"},
	},
	"required": ["action", "path"],
}

TOOLS: list[ToolSpec] = [
	ToolSpec(
		name="propose_file_change",
		group=GROUP,
		schema={
			"name": "propose_file_change",
			"description": (
				"Tạo đề xuất sửa một file đã có trong apps/ (đường dẫn tính từ apps/, ví dụ "
				"helpdesk/helpdesk/api/ticket.py). find và replace là hai mảng cùng số phần tử: mỗi find[i] "
				"phải xuất hiện đúng 1 lần trong file, các đoạn find không chồng nhau, và được thay bằng "
				"replace[i]. Chỉ tạo đề xuất Chờ duyệt, chưa ghi gì xuống đĩa."
			),
			"input_schema": {
				"type": "object",
				"properties": {
					"changes": {"type": "array", "maxItems": CHANGE_MAX_FILE_OPS, "items": _CHANGE_ITEM},
					"path": _PATH,
					"find": {"type": "array", "maxItems": REPLACE_MAX_ITEMS, "items": _FIND_ITEM},
					"replace": {"type": "array", "maxItems": REPLACE_MAX_ITEMS, "items": _REPLACE_ITEM},
					"reason": _REASON,
				},
				"required": ["reason"],
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
					"app": {"type": "string", "minLength": 1, "maxLength": APP_MAX_CHARS},
					"reason": _REASON,
				},
				"required": ["command", "reason"],
			},
		},
		handler=propose_bench_command,
	),
]
