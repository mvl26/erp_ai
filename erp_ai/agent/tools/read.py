import frappe
from frappe.utils import get_fullname

from erp_ai.agent import authority, policy, prompts
from erp_ai.agent.tools.registry import ToolContext, ToolSpec

AI_MODULE = "ERP AI agent"
DENIED_DOCTYPES = frozenset(
	{
		"ERP AI Setting",
		"ERP AI Credential",
		"ERP AI Log",
		"Salary Slip",
		"Employee",
		"Purchase Invoice",
		"Payment Entry",
		"GL Entry",
		"User",
		"Role Permission",
		"Custom DocPerm",
	}
)
ALLOWED_READ_DOCTYPES = frozenset(
	{"HD Ticket", "Comment", "HD Team", "HD Ticket Type", "HD Ticket Priority", "HD Article"}
)
COMMENT_HIDDEN_FIELDS = ("comment_email", "comment_by")
TOOL_RESULT_MAX_CHARS = 20000
COMMENT_MAX_CHARS = prompts.COMMENT_MAX_CHARS
RESOLUTION_MAX_CHARS = 1500
DEFAULT_COMMENT_LIMIT = 20
MAX_COMMENT_LIMIT = authority.MAX_COMMENT_LIMIT
DEFAULT_SEARCH_LIMIT = 5
MAX_SEARCH_LIMIT = 10
QUERY_MIN_CHARS = 2
QUERY_MAX_CHARS = 100
SEARCH_SCAN_MAX = 50
EMPTY_QUERY_REASON = "câu tìm cần ít nhất một từ dài 2 ký tự"
SEARCH_FIELDS = ("subject", "description", "resolution_details")
SEARCH_RESULT_FIELDS = (
	"name",
	"subject",
	"ticket_type",
	"agent_group",
	"resolution_date",
	"resolution_details",
)
MAX_DOCTYPE_ECHO = 80


def _refuse(reason: str) -> dict:
	return {"ok": False, "reason": reason}


def _is_int(value) -> bool:
	return isinstance(value, int) and not isinstance(value, bool)


_clean = prompts._clean


def _check_ticket(name) -> dict | None:
	"""Refusal for a ticket the agent may not read or send, else None."""
	if not isinstance(name, str) or not name or not frappe.db.exists("HD Ticket", name):
		return _refuse("không tìm thấy phiếu")
	if not frappe.has_permission("HD Ticket", "read", doc=name):
		return _refuse("không có quyền đọc phiếu")
	if not policy.can_send_ticket(name):
		return _refuse("phiếu không được phép đưa cho AI")
	return None


def get_ticket(args: dict, ctx: ToolContext) -> dict:
	args = args if isinstance(args, dict) else {}
	name = args.get("name", ctx.ticket_name)
	refusal = _check_ticket(name)
	if refusal:
		return refusal
	doc = frappe.get_doc("HD Ticket", name)
	doc.apply_fieldlevel_read_permissions()
	fields = ("name", "subject", "status", "priority", "ticket_type", "agent_group", "creation")
	ticket = {field: doc.get(field) for field in fields}
	ticket["description"] = _clean(doc.get("description"), prompts.DESCRIPTION_MAX_CHARS)
	return {"ok": True, "ticket": ticket}


def list_comments(args: dict, ctx: ToolContext) -> dict:
	args = args if isinstance(args, dict) else {}
	name = args.get("ticket", ctx.ticket_name)
	limit = args.get("limit", DEFAULT_COMMENT_LIMIT)
	if not _is_int(limit) or not 1 <= limit <= MAX_COMMENT_LIMIT:
		return _refuse(f"limit phải từ 1 đến {MAX_COMMENT_LIMIT}")
	refusal = _check_ticket(name)
	if refusal:
		return refusal
	labelled = authority.label_comments(name, authority.fetch_ticket_comments(name, limit))
	comments = [
		{
			"author": get_fullname(row["author"]),
			"role": row["role"],
			"creation": row["creation"],
			"content": _clean(row["content"], COMMENT_MAX_CHARS),
		}
		for row in labelled
	]
	return {"ok": True, "comments": comments}


def _like_pattern(word: str) -> str:
	# Frappe escapes `\\` and `%` of a like value itself; a `_` left as a wildcard only widens the scan.
	return f"%{word}%"


def search_resolved_tickets(args: dict, ctx: ToolContext) -> dict:
	# Imported on call: knowledge imports tools.source, which imports `_schema` from this module as it loads.
	from erp_ai.agent import knowledge

	args = args if isinstance(args, dict) else {}
	query = args.get("query")
	limit = args.get("limit", DEFAULT_SEARCH_LIMIT)
	if not isinstance(query, str) or not QUERY_MIN_CHARS <= len(query) <= QUERY_MAX_CHARS:
		return _refuse(f"query phải dài {QUERY_MIN_CHARS}..{QUERY_MAX_CHARS} ký tự")
	if not _is_int(limit) or not 1 <= limit <= MAX_SEARCH_LIMIT:
		return _refuse(f"limit phải từ 1 đến {MAX_SEARCH_LIMIT}")
	words = set(knowledge.tokenize(query))
	if not words:
		return _refuse(EMPTY_QUERY_REASON)
	# ADR-034: excluded tickets are left out by the query itself, before the scan limit and the ranking.
	excluded, ticket_or = policy.ticket_content_filters("HD Ticket")
	if ticket_or:
		raise ValueError("policy.ticket_content_filters gave an OR group for HD Ticket")
	try:
		rows = frappe.get_list(
			"HD Ticket",
			filters=[["status_category", "=", "Resolved"], *excluded],
			or_filters=[
				[field, "like", _like_pattern(word)] for word in sorted(words) for field in SEARCH_FIELDS
			],
			fields=[*SEARCH_RESULT_FIELDS, "description", "modified"],
			order_by="modified desc",
			limit_page_length=SEARCH_SCAN_MAX,
		)
	except frappe.PermissionError:
		return _refuse("không có quyền đọc phiếu")
	ranked = []
	for row in rows:
		# Score: distinct query words found whole; one space between the fields keeps their words apart.
		description, details = (
			knowledge.plain_text(row.description),
			knowledge.plain_text(row.resolution_details),
		)
		if score := len(words & knowledge.text_words(f"{row.subject or ''} {description} {details}")):
			ranked.append((score, row.modified, row))
	ranked.sort(key=lambda item: item[:2], reverse=True)
	tickets = []
	for _score, _modified, row in ranked[:limit]:
		ticket = {field: row.get(field) for field in SEARCH_RESULT_FIELDS}
		ticket["resolution_details"] = _clean(row.resolution_details, RESOLUTION_MAX_CHARS)
		tickets.append(ticket)
	return {"ok": True, "tickets": tickets}


def denied_doctypes() -> set:
	return set(DENIED_DOCTYPES) | set(frappe.get_all("DocType", {"module": AI_MODULE}, pluck="name"))


def _password_fieldnames(doctype: str) -> set:
	return {df.fieldname for df in frappe.get_meta(doctype).fields if df.fieldtype == "Password"}


def get_record(args: dict, ctx: ToolContext) -> dict:
	args = args if isinstance(args, dict) else {}
	doctype, name = args.get("doctype"), args.get("name")
	if not isinstance(doctype, str) or not isinstance(name, str) or not doctype or not name:
		return _refuse("thiếu doctype hoặc name")
	if doctype in denied_doctypes():
		return _refuse(f"DocType {doctype[:MAX_DOCTYPE_ECHO]} bị cấm")
	if doctype not in ALLOWED_READ_DOCTYPES:
		return _refuse(f"DocType {doctype[:MAX_DOCTYPE_ECHO]} chưa được mở")
	if not frappe.db.exists(doctype, name):
		return _refuse("không tìm thấy bản ghi")
	if not frappe.has_permission(doctype, "read", doc=name):
		return _refuse("không có quyền đọc bản ghi")
	ticket_name = _owning_ticket(doctype, name)
	if ticket_name is False:
		return _refuse(f"DocType {doctype[:MAX_DOCTYPE_ECHO]} chưa được mở")
	if ticket_name and not policy.can_send_ticket(ticket_name):
		return _refuse("bản ghi thuộc phiếu không được phép đưa cho AI")
	doc = frappe.get_doc(doctype, name)
	doc.apply_fieldlevel_read_permissions()
	hidden = _password_fieldnames(doctype)
	if doctype == "Comment":
		hidden |= set(COMMENT_HIDDEN_FIELDS)
	record = {key: value for key, value in doc.as_dict().items() if key not in hidden}
	return {"ok": True, "record": record}


def _owning_ticket(doctype: str, name: str):
	"""The HD Ticket a record belongs to; None when it has none; False for a Comment that is not a ticket's."""
	if doctype == "HD Ticket":
		return name
	if doctype != "Comment":
		return None
	values = frappe.db.get_value(
		"Comment", name, ["reference_doctype", "reference_name", "comment_type"], as_dict=True
	)
	expected = authority.ticket_comment_filters(values.reference_name)
	if (values.reference_doctype, values.comment_type) != (
		expected["reference_doctype"],
		expected["comment_type"],
	):
		return False
	return values.reference_name


def _schema(name: str, description: str, properties: dict, required: list) -> dict:
	return {
		"name": name,
		"description": description,
		"input_schema": {"type": "object", "properties": properties, "required": required},
	}


TOOLS: list[ToolSpec] = [
	ToolSpec(
		"get_ticket",
		"read",
		_schema(
			"get_ticket",
			"Đọc các trường của phiếu (mặc định là phiếu đang xử lý).",
			{"name": {"type": "string", "minLength": 1}},
			[],
		),
		get_ticket,
	),
	ToolSpec(
		"list_comments",
		"read",
		_schema(
			"list_comments",
			"Liệt kê comment của phiếu, mới nhất trước, kèm nhãn role (chỉ thị/dữ liệu).",
			{
				"ticket": {"type": "string", "minLength": 1},
				"limit": {"type": "integer", "minimum": 1, "maximum": MAX_COMMENT_LIMIT},
			},
			[],
		),
		list_comments,
	),
	ToolSpec(
		"search_resolved_tickets",
		"read",
		_schema(
			"search_resolved_tickets",
			"Tìm phiếu đã giải quyết có tiêu đề hoặc nội dung chứa chuỗi cho trước.",
			{
				"query": {"type": "string", "minLength": QUERY_MIN_CHARS, "maxLength": QUERY_MAX_CHARS},
				"limit": {"type": "integer", "minimum": 1, "maximum": MAX_SEARCH_LIMIT},
			},
			["query"],
		),
		search_resolved_tickets,
	),
	ToolSpec(
		"get_record",
		"read",
		_schema(
			"get_record",
			"Đọc một bản ghi của DocType được phép (phiếu, comment của phiếu, nhóm, loại, ưu tiên, bài viết).",
			{
				"doctype": {"type": "string", "minLength": 1, "maxLength": 140},
				"name": {"type": "string", "minLength": 1},
			},
			["doctype", "name"],
		),
		get_record,
	),
]
