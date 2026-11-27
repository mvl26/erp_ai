"""Read-only Server Script tools (group `script_read`, 2026-11-27): find and read a Server Script to diagnose an
automation fault.

Granted above L0 while `server_script_read_enabled` is on (registry.GRANT_TABLE); each handler also checks the switch
of its context. The reads are those of `agent.server_script_read`, which skips role permissions on purpose (the switch
is the grant; see there). A script body arrives with its secrets masked and is cut here so the whole result fits
`read.TOOL_RESULT_MAX_CHARS`, the cap the runner puts on the JSON of every tool result. Every call is in ERP AI Log:
the `reason` row of its turn lists it in `tools_called`.
"""

import json

from erp_ai.agent import server_script_read
from erp_ai.agent.redact import MASK
from erp_ai.agent.tools.read import TOOL_RESULT_MAX_CHARS, _is_int, _refuse, _schema
from erp_ai.agent.tools.registry import ToolContext, ToolSpec

DEFAULT_LIST_LIMIT = 20
MAX_LIST_LIMIT = 50
TEXT_MAX_CHARS = 140
SWITCH_OFF_REASON = "công tắc cho bot đọc Server Script đang tắt"
MISSING_NAME_REASON = "thiếu name"
NOT_FOUND_REASON = "không tìm thấy Server Script"


def _text(args: dict, key: str) -> str | None:
	value = args.get(key)
	return value if isinstance(value, str) and value else None


def list_server_scripts(args: dict, ctx: ToolContext) -> dict:
	if not ctx.server_script_read:
		return _refuse(SWITCH_OFF_REASON)
	args = args if isinstance(args, dict) else {}
	limit = args.get("limit", DEFAULT_LIST_LIMIT)
	if not _is_int(limit) or not 1 <= limit <= MAX_LIST_LIMIT:
		return _refuse(f"limit phải từ 1 đến {MAX_LIST_LIMIT}")
	# one row more than asked says whether the filters left some out
	rows = server_script_read.list_scripts(
		reference_doctype=_text(args, "reference_doctype"),
		name_contains=_text(args, "name_contains"),
		script_type=_text(args, "script_type"),
		limit=limit + 1,
	)
	return {"ok": True, "server_scripts": rows[:limit], "more": len(rows) > limit}


def _result(record: dict, script: str, cut: bool) -> dict:
	return {"ok": True, "server_script": {**record, "script": script, "script_cut": cut}}


def _size(result: dict) -> int:
	# the runner's own dump of a tool result (runner._run_tool)
	return len(json.dumps(result, ensure_ascii=False, default=str))


def _fitted(record: dict) -> dict:
	"""The result with `script` cut to the longest head that keeps its JSON within TOOL_RESULT_MAX_CHARS."""
	script = record.pop("script")
	if _size(_result(record, script, False)) <= TOOL_RESULT_MAX_CHARS:
		return _result(record, script, False)
	# the JSON size grows with the head, and each character takes at least one: binary search on the head length
	low, high = 0, min(len(script), TOOL_RESULT_MAX_CHARS)
	while low < high:
		middle = (low + high + 1) // 2
		if _size(_result(record, script[:middle], True)) <= TOOL_RESULT_MAX_CHARS:
			low = middle
		else:
			high = middle - 1
	return _result(record, script[:low], True)


def get_server_script(args: dict, ctx: ToolContext) -> dict:
	if not ctx.server_script_read:
		return _refuse(SWITCH_OFF_REASON)
	args = args if isinstance(args, dict) else {}
	name = _text(args, "name")
	if name is None:
		return _refuse(MISSING_NAME_REASON)
	record = server_script_read.get_script(name)
	if record is None:
		return _refuse(NOT_FOUND_REASON)
	return _fitted(record)


TOOLS: list[ToolSpec] = [
	ToolSpec(
		"list_server_scripts",
		"script_read",
		_schema(
			"list_server_scripts",
			"Tìm Server Script theo DocType, loại hoặc một phần tên, kể cả script đang tắt; mới sửa trước. Trả loại, "
			"DocType, sự kiện, hàm API, tần suất, trạng thái tắt; không trả nội dung (đọc bằng get_server_script). "
			"Server Script nằm trong cơ sở dữ liệu, search_source không thấy. Script chạy theo lịch (Scheduler Event) "
			"không có DocType: tìm theo loại hoặc tên.",
			{
				"reference_doctype": {"type": "string", "minLength": 1, "maxLength": TEXT_MAX_CHARS},
				"name_contains": {"type": "string", "minLength": 1, "maxLength": TEXT_MAX_CHARS},
				"script_type": {"type": "string", "enum": list(server_script_read.SCRIPT_TYPES)},
				"limit": {"type": "integer", "minimum": 1, "maximum": MAX_LIST_LIMIT},
			},
			[],
		),
		list_server_scripts,
	),
	ToolSpec(
		"get_server_script",
		"script_read",
		_schema(
			"get_server_script",
			"Đọc một Server Script theo tên (loại, DocType, sự kiện, trạng thái tắt, nội dung script) để chẩn đoán lỗi "
			f"tự động hóa. Chỉ đọc. Token, khóa API, mật khẩu trong script đã được che thành {MASK}: đó không phải giá "
			"trị thật, đừng kết luận lỗi từ đó. script_cut = true là script dài đã bị cắt phần cuối.",
			{"name": {"type": "string", "minLength": 1, "maxLength": TEXT_MAX_CHARS}},
			["name"],
		),
		get_server_script,
	),
]
