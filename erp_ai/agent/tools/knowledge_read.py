"""Knowledge read tools of the `read` group (FEAT-007 U6b, AC-46, AC-47, AC-50; ADR-034 QĐ 2, 4).

Every string a tool returns goes through `redact_secrets`; the runner cuts the JSON of each tool result at
`read.TOOL_RESULT_MAX_CHARS`. `_limits` is the one place this module reads ERP AI Setting. No tool here passes
`ignore_permissions` (ADR-034 Ràng buộc): the Error Log is read by `system_read`, the one permission-free path.
"""

import frappe
from frappe.utils import cint, get_datetime

from erp_ai.agent import knowledge, policy, system_read
from erp_ai.agent.redact import redact_secrets
from erp_ai.agent.tools import read, source
from erp_ai.agent.tools.read import _schema
from erp_ai.agent.tools.registry import ToolContext, ToolSpec
from erp_ai.constants import SETTING_DOCTYPE

KNOWLEDGE_TOOL_NAMES = frozenset({"search_knowledge_base", "search_manuals", "read_error_logs", "run_report"})
MANUALS_NOT_CONFIGURED = "chưa có kho HDSD"
INVALID_TIME = "thời điểm không hợp lệ: {key}"
ARTICLE_DOCTYPE = "HD Article"
# ERP AI Setting Int fields (A-13 defaults, the controller's bounds); a value outside them reads the default.
KNOWLEDGE_SEARCH_LIMIT_DEFAULT, KNOWLEDGE_SEARCH_LIMIT_MAX = 5, 20
REPORT_ROW_LIMIT_DEFAULT, REPORT_ROW_LIMIT_MAX = 20, 100


def _refuse(reason: str) -> dict:
	return {"ok": False, "reason": reason}


def _masked(row: dict) -> dict:
	return {key: redact_secrets(value) if isinstance(value, str) else value for key, value in row.items()}


def _bounded(value, default: int, maximum: int) -> int:
	number = cint(value)
	return number if 1 <= number <= maximum else default


def _limits() -> tuple[int, tuple[str, ...], int]:
	"""(knowledge_search_limit, the non-blank stripped lines of allowed_reports, report_row_limit)."""
	get = frappe.db.get_single_value
	reports = tuple(
		line.strip() for line in (get(SETTING_DOCTYPE, "allowed_reports") or "").splitlines() if line.strip()
	)
	return (
		_bounded(
			get(SETTING_DOCTYPE, "knowledge_search_limit"),
			KNOWLEDGE_SEARCH_LIMIT_DEFAULT,
			KNOWLEDGE_SEARCH_LIMIT_MAX,
		),
		reports,
		_bounded(get(SETTING_DOCTYPE, "report_row_limit"), REPORT_ROW_LIMIT_DEFAULT, REPORT_ROW_LIMIT_MAX),
	)


def search_knowledge_base(args: dict, ctx: ToolContext) -> dict:
	"""AC-46: published articles the session user may read (`knowledge.search_kb_articles`); an article whose
	source ticket the agent may not take is left out (NFR-1)."""
	args = args if isinstance(args, dict) else {}
	try:
		rows = knowledge.search_kb_articles(args.get("query"), _limits()[0])
	except frappe.ValidationError as exc:
		return _refuse(str(exc))
	articles = [
		_masked(row) for row in rows if not policy.is_ticket_record_excluded(ARTICLE_DOCTYPE, row["name"])
	]
	return {"ok": True, "articles": articles}


def search_manuals(args: dict, ctx: ToolContext) -> dict:
	"""AC-47: sections of the manuals directory; none set (or not a safe directory) → MANUALS_NOT_CONFIGURED.

	`source.manuals_root` is the one reader of `manuals_dir`; its real path joins to itself under the source root.
	A file that cannot be read is skipped inside `knowledge.search_manuals`.
	"""
	args = args if isinstance(args, dict) else {}
	try:
		sections = knowledge.search_manuals(args.get("query"), _limits()[0], source.manuals_root())
	except frappe.ValidationError as exc:
		return _refuse(str(exc))
	if sections is None:
		return _refuse(MANUALS_NOT_CONFIGURED)
	return {"ok": True, "sections": [_masked(row) for row in sections]}


def _time(value):
	"""The naive datetime `value` names, else None (blank, unparsable or with a time zone)."""
	try:
		when = get_datetime(value)
	except (TypeError, ValueError, OverflowError):
		return None
	return when if when is not None and when.tzinfo is None else None


def read_error_logs(args: dict, ctx: ToolContext) -> dict:
	"""AC-50: Error Log rows by `system_read.read_error_logs` (window, keyword, limit and masking are its own)."""
	args = args if isinstance(args, dict) else {}
	call = {"keyword": args.get("keyword")}
	if "limit" in args:
		call["limit"] = args["limit"]
	for key in ("since", "until"):
		if args.get(key) is not None:
			call[key] = _time(args[key])
			if call[key] is None:
				return _refuse(INVALID_TIME.format(key=key))
	try:
		errors = system_read.read_error_logs(**call)
	except frappe.ValidationError as exc:
		return _refuse(str(exc))
	return {"ok": True, "errors": [_masked(row) for row in errors]}


def _query_property() -> dict:
	return {"type": "string", "minLength": read.QUERY_MIN_CHARS, "maxLength": read.QUERY_MAX_CHARS}


TOOLS: list[ToolSpec] = [
	ToolSpec(
		"search_knowledge_base",
		"read",
		_schema(
			"search_knowledge_base",
			"Tìm bài CSKT (HD Article) đã xuất bản theo nội dung; trả tên, tiêu đề và đoạn trích, bài khớp "
			"nhiều từ đứng trước.",
			{"query": _query_property()},
			["query"],
		),
		search_knowledge_base,
	),
	ToolSpec(
		"search_manuals",
		"read",
		_schema(
			"search_manuals",
			"Tìm trong kho HDSD (tài liệu .md); trả tên tài liệu, tiêu đề mục, dòng và đoạn trích. "
			"Trả 'chưa có kho HDSD' khi chưa cấu hình kho.",
			{"query": _query_property()},
			["query"],
		),
		search_manuals,
	),
	ToolSpec(
		"read_error_logs",
		"read",
		_schema(
			"read_error_logs",
			"Đọc Error Log của site, mới nhất trước, đã che khóa và mật khẩu. since/until dạng "
			"'YYYY-MM-DD HH:MM:SS' (mặc định 24 giờ gần nhất, tối đa 7 ngày); keyword lọc theo method hoặc nội dung.",
			{
				"since": {"type": "string", "minLength": 1},
				"until": {"type": "string", "minLength": 1},
				"keyword": {
					"type": "string",
					"minLength": system_read.MIN_KEYWORD_LENGTH,
					"maxLength": system_read.MAX_KEYWORD_LENGTH,
				},
				"limit": {
					"type": "integer",
					"minimum": system_read.MIN_LIMIT,
					"maximum": system_read.MAX_LIMIT,
				},
			},
			[],
		),
		read_error_logs,
	),
]
