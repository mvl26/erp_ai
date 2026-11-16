"""Knowledge read tools of the `read` group (FEAT-007 U6b, AC-46, AC-47, AC-49, AC-50; ADR-034 QĐ 2-4).

Every string a tool returns goes through `redact_secrets`; the runner cuts the JSON of each tool result at
`read.TOOL_RESULT_MAX_CHARS`. `_limits` is the one place this module reads ERP AI Setting. No tool here passes
`ignore_permissions` (ADR-034 Ràng buộc): the Error Log is read by `system_read`, the one permission-free path,
and a report runs under the session user (the agent account).
"""

import frappe
from frappe.desk import query_report
from frappe.utils import cint, get_datetime

from erp_ai.agent import knowledge, policy, system_read
from erp_ai.agent.redact import redact_secrets
from erp_ai.agent.tools import read, source
from erp_ai.agent.tools.read import _schema
from erp_ai.agent.tools.registry import ToolContext, ToolSpec, _invalid
from erp_ai.constants import SETTING_DOCTYPE

KNOWLEDGE_TOOL_NAMES = frozenset({"search_knowledge_base", "search_manuals", "read_error_logs", "run_report"})
MANUALS_NOT_CONFIGURED = "chưa có kho HDSD"
INVALID_TIME = "thời điểm không hợp lệ: {key}"
REPORT_FILTER_MAX_KEYS = 10
REPORT_TYPES = ("Script Report", "Query Report")
REPORT_NAME_MAX_CHARS = 140
REASON_NO_REPORTS = "chưa cho phép báo cáo nào"
REASON_REPORT_NOT_ALLOWED = "báo cáo không nằm trong danh sách cho phép"
REASON_REPORT_NOT_RUNNABLE = "báo cáo không chạy được"
REASON_REPORT_ON_TICKET_DATA = "báo cáo dựa trên dữ liệu phiếu hoặc dữ liệu của app: bot không được chạy"
REASON_REPORT_PERMISSION = "tài khoản agent không có quyền chạy báo cáo này"
FILTER_VALUE_TYPES = (str, int, float, bool)
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


def _allowed_articles(rows: list) -> list:
	"""The rows, in their order, without the articles of excluded tickets (NFR-1): one get_list over
	`policy.ticket_content_filters`, none when no ticket is excluded."""
	filters, or_filters = policy.ticket_content_filters(ARTICLE_DOCTYPE)
	if not rows or not (filters or or_filters):
		return rows
	names = [row["name"] for row in rows]
	kept = set(
		frappe.get_list(
			ARTICLE_DOCTYPE,
			filters=[["name", "in", names], *filters],
			or_filters=or_filters,
			pluck="name",
			limit_page_length=len(names),
		)
	)
	return [row for row in rows if row["name"] in kept]


def search_knowledge_base(args: dict, ctx: ToolContext) -> dict:
	"""AC-46: published articles the session user may read (`knowledge.search_kb_articles`, every ranked match up
	to its scan cap); the articles of excluded tickets are dropped before the cut to the limit (R17d), so a short
	list never reveals an excluded match."""
	args = args if isinstance(args, dict) else {}
	try:
		rows = knowledge.search_kb_articles(args.get("query"), knowledge.KB_SCAN_MAX)
	except frappe.ValidationError as exc:
		return _refuse(str(exc))
	return {"ok": True, "articles": [_masked(row) for row in _allowed_articles(rows)[: _limits()[0]]]}


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


def _filters_ok(filters) -> bool:
	"""At most REPORT_FILTER_MAX_KEYS keys, each value a string, a number or a boolean (the registry checks only
	that `filters` is an object)."""
	return (
		isinstance(filters, dict)
		and len(filters) <= REPORT_FILTER_MAX_KEYS
		and all(isinstance(value, FILTER_VALUE_TYPES) for value in filters.values())
	)


def _cell(value):
	return redact_secrets(value) if isinstance(value, str) else value


def _row(row, fieldnames: list) -> list:
	"""The cells of one result row in column order (a dict row by fieldname, a list row as it is), masked."""
	cells = [row.get(fieldname) for fieldname in fieldnames] if isinstance(row, dict) else list(row)
	return [_cell(value) for value in cells]


def _on_ticket_or_app_data(ref_doctype) -> bool:
	"""ADR-034 QĐ 3: the report's DocType carries ticket content (TICKET_CONTENT_DOCTYPES, a Link to HD Ticket),
	points at tickets through a column of `policy.ticket_link_columns` (R17b: the listed and the live-meta
	(DocType, Dynamic Link) pairs), or is denied to the read tools."""
	return (
		policy.is_ticket_content_doctype(ref_doctype)
		or bool(policy.ticket_link_columns(ref_doctype))
		or ref_doctype in read.denied_doctypes()
	)


def run_report(args: dict, ctx: ToolContext) -> dict:
	"""AC-49: a report of `allowed_reports`, checked again here (the list can be written past the form, ADR-034
	QĐ 3), run under the session user without a prepared report, cut to `report_row_limit` rows."""
	args = args if isinstance(args, dict) else {}
	filters = args.get("filters", {})
	if not _filters_ok(filters):
		return _invalid("filters")
	report_name = args.get("report_name")
	_search_limit, allowed, row_limit = _limits()
	if not allowed:
		return _refuse(REASON_NO_REPORTS)
	if report_name not in allowed:
		return _refuse(REASON_REPORT_NOT_ALLOWED)
	report = frappe.db.get_value(
		"Report", report_name, ["report_type", "disabled", "ref_doctype"], as_dict=True
	)
	if not report or report.disabled or report.report_type not in REPORT_TYPES:
		return _refuse(REASON_REPORT_NOT_RUNNABLE)
	if _on_ticket_or_app_data(report.ref_doctype):
		return _refuse(REASON_REPORT_ON_TICKET_DATA)
	try:
		# R17f: Frappe's check that the session user may read the record of each Link filter, run here so that its
		# error, and no other validation error of the run, gives the permission reason.
		query_report.validate_filters_permissions(report_name, filters, frappe.session.user)
	except frappe.ValidationError:
		return _refuse(REASON_REPORT_PERMISSION)
	try:
		result = query_report.run(report_name, filters=filters, ignore_prepared_report=True)
	except frappe.PermissionError:
		return _refuse(REASON_REPORT_PERMISSION)
	columns = result.get("columns") or []
	rows = result.get("result") or []
	fieldnames = [column.get("fieldname") for column in columns]
	return {
		"ok": True,
		"columns": [_cell(column.get("label") or column.get("fieldname")) for column in columns],
		"rows": [_row(row, fieldnames) for row in rows[:row_limit]],
		"truncated": len(rows) > row_limit,
	}


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
	ToolSpec(
		"run_report",
		"read",
		_schema(
			"run_report",
			"Chạy một báo cáo (Script Report hoặc Query Report) có trong danh sách cho phép của cấu hình, theo "
			"quyền của tài khoản agent; trả nhãn cột và tối đa số dòng cấu hình.",
			{
				"report_name": {"type": "string", "minLength": 1, "maxLength": REPORT_NAME_MAX_CHARS},
				"filters": {
					"type": "object",
					"maxProperties": REPORT_FILTER_MAX_KEYS,
					"additionalProperties": {"type": ["string", "number", "boolean"]},
				},
			},
			["report_name"],
		),
		run_report,
	),
]
