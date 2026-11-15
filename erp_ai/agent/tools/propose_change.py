"""Change-proposal tools: the model proposes one block of file items and bench commands; nothing is written
to disk and no command runs here. A person approves on the proposal form, then the change job applies it."""

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
	CHANGE_OP_CREATE,
	CHANGE_OP_DELETE,
	CHANGE_OP_EDIT,
	CHANGE_OP_RENAME,
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
COMMENT_DOCTYPE = "Comment"
NO_INSTRUCTOR = "không có người ra lệnh"
# Design table 3.1: these sentences are the contract with the model and the tests.
NO_PERMISSION = "thiếu quyền tạo đề xuất"
NO_COMMENT_PERMISSION = "thiếu quyền tạo comment"
NOT_FOUND = "file không tồn tại"
NOT_UTF8 = source.TEXT_NOT_UTF8
EDIT_SHAPE = f"find và replace phải cùng số phần tử, từ 1 đến {REPLACE_MAX_ITEMS}"
EDIT_NOT_FOUND = "đoạn find[{index}] không có trong file"
EDIT_AMBIGUOUS = "đoạn find[{index}] xuất hiện nhiều hơn một lần"
EDIT_OVERLAP = "các đoạn find chồng nhau"
NO_CHANGE = "nội dung sau trùng nội dung trước"
EXISTS = "file đã tồn tại"
BLOCK_SHAPE = change_guard.BLOCK_SHAPE
# CHG-002 design 3.1: the fields of each kind of item of `changes`.
ITEM_FIELDS = {
	"edit": {"action", "path", "find", "replace"},
	"create": {"action", "path", "content"},
	"delete": {"action", "path"},
	"rename": {"action", "path", "new_path"},
}
EXECUTABLE_BITS = 0o111
LEGACY_EDIT_KEYS = ("path", "find", "replace")
# CHG-002 design 3.1: the fields of one item of `commands`.
COMMAND_FIELDS = {"command", "app"}


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


def _diff(rel_path: str, before: str, after: str, tofile: str | None = None) -> str:
	lines = difflib.unified_diff(
		before.splitlines(keepends=True),
		after.splitlines(keepends=True),
		fromfile=f"a/{rel_path}",
		tofile=tofile or f"b/{rel_path}",
		n=DIFF_CONTEXT_LINES,
	)
	return "".join(line if line.endswith("\n") else line + "\n" for line in lines)


def _comment(ctx: ToolContext, proposal) -> str:
	"""One ticket comment (design 3.8): the escaped first sentence, the notes of design 3.9 and the
	Duyệt / Từ chối links; returns the Comment name. A block (CHG-002 T1) names its first item's path."""
	escape = frappe.utils.escape_html
	if proposal.change_kind == CHANGE_KIND_CODE:
		first = proposal.operations[0] if proposal.get("operations") else None
		is_new = first.operation == CHANGE_OP_CREATE if first else proposal.is_new_file
		verb = "tạo" if is_new else "sửa"
		path = first.file_path if first else proposal.file_path
		target = f"{verb} <code>{escape(path)}</code>"
	else:
		args = "; ".join(" ".join(argv) for argv in json.loads(proposal.command_list or "[]"))
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


def _is_text_list(value) -> bool:
	return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _item_shape(change) -> str | None:
	"""Design 3.1: the fields of an item of `changes` for its `action`, or the refusal reason."""
	action = change.get("action") if isinstance(change, dict) else None
	if action not in ITEM_FIELDS:
		return change_guard.OP_UNKNOWN
	fields_ok = set(change) == ITEM_FIELDS[action] and isinstance(change["path"], str)
	if action == "edit":
		fields_ok = fields_ok and _is_text_list(change["find"]) and _is_text_list(change["replace"])
	elif action == "create":
		fields_ok = fields_ok and isinstance(change["content"], str)
	elif action == "rename":
		fields_ok = fields_ok and isinstance(change["new_path"], str)
	return None if fields_ok else change_guard.OP_FIELDS.format(action=action)


def _edited_op(change: dict, ctx: ToolContext) -> change_guard.FileOp | str:
	"""Design 4.1 step 2 for an `edit` item: read at most `TEXT_MAX_BYTES + 1` bytes, `text_refusal`, then
	the edits; the `FileOp` or the refusal reason."""
	guard = change_guard.check_write_path(change["path"], ctx.allowed_apps, new_file=False, read_git=False)
	if guard.reason:
		return guard.reason
	if not os.path.isfile(guard.full_path):
		return NOT_FOUND
	with open(guard.full_path, "rb") as handle:
		data = handle.read(source.TEXT_MAX_BYTES + 1)
	refusal = source.text_refusal(guard.rel_path, data)
	if refusal:
		return refusal
	before = data.decode("utf-8")
	after, refusal = _apply_edits(before, change["find"], change["replace"])
	if refusal:
		return refusal
	if after == before:
		return NO_CHANGE
	return change_guard.FileOp(
		kind=CHANGE_OP_EDIT,
		path=change["path"],
		new_path=None,
		before=before,
		after=after,
		base_hash=_sha256(before.encode("utf-8")),
		after_hash=_sha256(after.encode("utf-8")),
	)


def _under_a_folder(full: str) -> bool:
	"""A new file's nearest existing parent is a folder, not a file (`app/README.md/x.txt` is refused)."""
	parent = os.path.dirname(full)
	while not os.path.lexists(parent):
		parent = os.path.dirname(parent)
	return os.path.isdir(parent)


def _created_op(change: dict, ctx: ToolContext) -> change_guard.FileOp | str:
	"""Design 4.1 step 2 for a `create` item: an existing path (`lexists`) is `EXISTS`; folders may be new."""
	guard = change_guard.check_write_path(change["path"], ctx.allowed_apps, new_file=True, read_git=False)
	if guard.reason:
		return guard.reason
	if os.path.lexists(guard.full_path):
		return EXISTS
	if not _under_a_folder(guard.full_path):
		return change_guard.PATH_INVALID
	content = change["content"]
	return change_guard.FileOp(
		kind=CHANGE_OP_CREATE,
		path=change["path"],
		new_path=None,
		before=None,
		after=content,
		base_hash=None,
		after_hash=_sha256(content.encode("utf-8", errors="surrogatepass")),
	)


def _removed_text(path: str, ctx: ToolContext) -> tuple[str, str | None]:
	"""Design 4.1 step 2 for the file a `delete` or `rename` item takes away (R-7, R-8): a regular file and
	not a symlink (`NOT_REGULAR_FILE`), no execute bit (`EXECUTABLE_FILE`), then at most
	`TEXT_MAX_BYTES + 1` bytes through `text_refusal`; (text, None) or ("", refusal reason)."""
	guard = change_guard.check_write_path(path, ctx.allowed_apps, new_file=False, read_git=False)
	if guard.reason:
		return "", guard.reason
	full = guard.full_path
	if not os.path.isfile(full) or os.path.islink(full):
		return "", change_guard.NOT_REGULAR_FILE
	if os.stat(full).st_mode & EXECUTABLE_BITS:
		return "", change_guard.EXECUTABLE_FILE
	with open(full, "rb") as handle:
		data = handle.read(source.TEXT_MAX_BYTES + 1)
	refusal = source.text_refusal(guard.rel_path, data)
	if refusal:
		return "", refusal
	return data.decode("utf-8"), None


def _deleted_op(change: dict, ctx: ToolContext) -> change_guard.FileOp | str:
	"""Design 4.1 step 2 for a `delete` item: the file's text is kept as the content before."""
	before, refusal = _removed_text(change["path"], ctx)
	if refusal:
		return refusal
	return change_guard.FileOp(
		kind=CHANGE_OP_DELETE,
		path=change["path"],
		new_path=None,
		before=before,
		after=None,
		base_hash=_sha256(before.encode("utf-8")),
		after_hash=None,
	)


def _renamed_op(change: dict, ctx: ToolContext) -> change_guard.FileOp | str:
	"""Design 4.1 step 2 for a `rename` item: the source as for `delete`, a target that exists
	(`lexists`) is `EXISTS`; the content moves unchanged."""
	text, refusal = _removed_text(change["path"], ctx)
	if refusal:
		return refusal
	guard = change_guard.check_write_path(change["new_path"], ctx.allowed_apps, new_file=True, read_git=False)
	if guard.reason:
		return guard.reason
	if os.path.lexists(guard.full_path):
		return EXISTS
	if not _under_a_folder(guard.full_path):
		return change_guard.PATH_INVALID
	digest = _sha256(text.encode("utf-8"))
	return change_guard.FileOp(
		kind=CHANGE_OP_RENAME,
		path=change["path"],
		new_path=change["new_path"],
		before=text,
		after=text,
		base_hash=digest,
		after_hash=digest,
	)


def _built_commands(commands, ctx: ToolContext) -> list | dict:
	"""Design 3.1: each `{command, app?}` of `commands` as its argv from `build_bench_args`, in order, or the
	refusal: a malformed list or item is refused like the schema, a command reason gets `lệnh {n}: `."""
	if not isinstance(commands, list):
		return registry_invalid("commands")
	built = []
	for number, command in enumerate(commands, start=1):
		if not isinstance(command, dict) or "command" not in command or not set(command) <= COMMAND_FIELDS:
			return registry_invalid("commands")
		args = change_guard.build_bench_args(
			command["command"], command.get("app"), ctx.allowed_apps, frappe.local.site
		)
		if isinstance(args, str):
			return _fail(change_guard.COMMAND_PREFIX.format(number=number) + args)
		built.append(args)
	return built


_BUILDERS = {"edit": _edited_op, "create": _created_op, "delete": _deleted_op, "rename": _renamed_op}


def _op_diff(op: change_guard.FileOp) -> str:
	"""One item's part of `diff_text`: a unified diff (a deletion against `/dev/null`), or for a rename
	the two lines `rename from` / `rename to`."""
	path = os.path.normpath(op.path)
	if op.kind == CHANGE_OP_RENAME:
		return f"rename from {path}\nrename to {os.path.normpath(op.new_path)}\n"
	tofile = "/dev/null" if op.kind == CHANGE_OP_DELETE else None
	return _diff(path, op.before or "", op.after or "", tofile)


def _row(target: change_guard.OpTarget) -> dict:
	op = target.op
	row = {"operation": op.kind, "file_path": target.guard.rel_path, "content_after": op.after}
	if op.new_path is not None:
		row["new_path"] = os.path.normpath(op.new_path)
	if op.before is not None:
		row.update(content_before=op.before, base_hash=op.base_hash)
	row["after_hash"] = op.after_hash
	return row


def _propose_block(changes: list, commands: list, reason: str, ctx: ToolContext) -> dict:
	"""CHG-002 design 4.1: one block proposal of `edit`, `create`, `delete` and `rename` items (design 3.1).

	Step 2 turns each item into a `FileOp`; step 2b builds the joined `diff_text` once (design-addendum-1
	A-1.5); step 3 is `check_block` at proposal time, whose paths and git state are the ones stored; step 4
	inserts one parent with one child row per item and exactly that `diff_text`. Every refusal comes before
	the insert: 0 proposals, 0 comments. `commands` are argv lists passed on to `check_block` and stored in
	`command_list` in order; a block with only commands carries no git field and no `branch`.
	"""
	if not isinstance(changes, list):
		return _fail(change_guard.OP_UNKNOWN)
	ops = []
	for number, change in enumerate(changes, start=1):
		refusal = _item_shape(change)
		if refusal is None:
			built = _BUILDERS[change["action"]](change, ctx)
			refusal = built if isinstance(built, str) else None
		if refusal:
			path = change.get("path") if isinstance(change, dict) else None
			return _fail(change_guard.OP_PREFIX.format(number=number, path=path) + refusal)
		ops.append(built)
	diff_text = "".join(_op_diff(op) for op in ops)
	check = change_guard.check_block(
		ops, commands, ctx.allowed_apps, frappe.local.site, at_apply=False, diff_text=diff_text
	)
	if check.reason:
		return _fail(check.reason)
	values = {"command_list": json.dumps(commands, ensure_ascii=False), "reason": reason}
	if check.targets:
		guard = check.targets[0].guard
		values.update(
			change_kind=CHANGE_KIND_CODE,
			app=check.app,
			reversible=1,
			operations=[_row(target) for target in check.targets],
			diff=diff_text,
			target_branch=guard.git.branch,
			upstream_ref=guard.git.upstream_ref,
			ahead_count=guard.git.ahead_count,
			is_core_app=int(guard.is_core_app),
		)
		return {**_insert(ctx, values), "branch": guard.git.branch}
	# design 2.2: a block with only commands takes the app of `build --app`, if any, and no git field
	built_apps = [args[-1] for args in commands if args[0] == change_guard.BUILD_COMMAND]
	values.update(
		change_kind=CHANGE_KIND_COMMAND,
		app=built_apps[0] if built_apps else None,
		reversible=0,
		target_branch="",
		upstream_ref="",
		ahead_count=0,
		is_core_app=0,
	)
	return _insert(ctx, values)


def propose_file_change(args: dict, ctx: ToolContext) -> dict:
	if refusal := _entry_refusal(ctx):
		return refusal
	if "changes" in args:
		if "path" in args:
			return _fail(BLOCK_SHAPE)
		changes = args["changes"]
	else:
		# The old shape: the schema no longer requires these keys, so a missing one is refused as before.
		for key in LEGACY_EDIT_KEYS:
			if key not in args:
				return registry_invalid(key)
		changes = [{"action": "edit", **{key: args[key] for key in LEGACY_EDIT_KEYS}}]
	commands = _built_commands(args.get("commands", []), ctx)
	if isinstance(commands, dict):
		return commands
	return _propose_block(changes, commands, args["reason"], ctx)


def propose_new_file(args: dict, ctx: ToolContext) -> dict:
	if refusal := _entry_refusal(ctx):
		return refusal
	change = {"action": "create", "path": args["path"], "content": args["content"]}
	commands = _built_commands(args.get("commands", []), ctx)
	if isinstance(commands, dict):
		return commands
	return _propose_block([change], commands, args["reason"], ctx)


def propose_bench_command(args: dict, ctx: ToolContext) -> dict:
	if refusal := _entry_refusal(ctx):
		return refusal
	built = change_guard.build_bench_args(
		args["command"], args.get("app"), ctx.allowed_apps, frappe.local.site
	)
	if isinstance(built, str):
		return _fail(built)
	return _propose_block([], [built], args["reason"], ctx)


_PATH = {"type": "string", "minLength": 1, "maxLength": PATH_MAX_CHARS}
_REASON = {"type": "string", "minLength": 1, "maxLength": REASON_MAX_CHARS}
_FIND_ITEM = {"type": "string", "minLength": 1, "maxLength": PROPOSAL_TEXT_MAX_CHARS}
_REPLACE_ITEM = {"type": "string", "maxLength": PROPOSAL_TEXT_MAX_CHARS}
_APP = {"type": "string", "minLength": 1, "maxLength": APP_MAX_CHARS}
_COMMAND = {"type": "string", "enum": list(change_guard.BENCH_COMMANDS)}
# CHG-002 design 3.1: the bench commands run after the files, in order.
_COMMANDS = {
	"type": "array",
	"items": {"type": "object", "properties": {"command": _COMMAND, "app": _APP}, "required": ["command"]},
}
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
				"replace[i]. commands là các lệnh bench chạy sau khi ghi file, đúng thứ tự; có file .py thì "
				"kết thúc bằng migrate rồi restart. Chỉ tạo đề xuất Chờ duyệt, chưa ghi gì xuống đĩa."
			),
			"input_schema": {
				"type": "object",
				"properties": {
					"changes": {"type": "array", "maxItems": CHANGE_MAX_FILE_OPS, "items": _CHANGE_ITEM},
					"path": _PATH,
					"find": {"type": "array", "maxItems": REPLACE_MAX_ITEMS, "items": _FIND_ITEM},
					"replace": {"type": "array", "maxItems": REPLACE_MAX_ITEMS, "items": _REPLACE_ITEM},
					"commands": _COMMANDS,
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
					"commands": _COMMANDS,
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
					"command": _COMMAND,
					"app": _APP,
					"reason": _REASON,
				},
				"required": ["command", "reason"],
			},
		},
		handler=propose_bench_command,
	),
]
