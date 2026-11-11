import frappe
from frappe.utils import now_datetime

from erp_ai.agent.classification import Classification, resolve_ticket_values
from erp_ai.agent.tools.registry import ToolContext, ToolSpec
from erp_ai.constants import CATEGORIES, CLASSIFIED_BY_AI, CLASSIFIED_BY_HUMAN, CONFIDENCE_VALUES

TICKET_DOCTYPE = "HD Ticket"
TASK_DOCTYPE = "Task"
HINT_FIELD = "ai_resolution_hint"
# Target field -> DocType holding its allowed values (design 3.5).
LINKED_DOCTYPES = {
	"ticket_type": "HD Ticket Type",
	"agent_group": "HD Team",
	"priority": "HD Ticket Priority",
}
REASON_MAX = 200


def _fail(reason: str) -> dict:
	return {"ok": False, "reason": reason[:REASON_MAX]}


def _mapped_values(doc, args: dict, ctx: ToolContext) -> tuple[dict, list]:
	"""Values to write (only those that exist on the site) and the skipped fields with a reason."""
	classification = Classification(category=args["category"], confidence=args["confidence"])
	wanted = resolve_ticket_values(classification, doc.subject, ctx.category_mapping)
	values, skipped = {}, []
	for field, value in wanted.items():
		if not value:
			skipped.append({"field": field, "reason": "ánh xạ không có giá trị"})
		elif not frappe.db.exists(LINKED_DOCTYPES[field], value):
			skipped.append({"field": field, "reason": "giá trị không tồn tại trên hệ thống"})
		else:
			values[field] = value
	return values, skipped


def set_classification(args: dict, ctx: ToolContext) -> dict:
	doc = frappe.get_doc(TICKET_DOCTYPE, ctx.ticket_name)
	if not doc.has_permission("write"):
		return _fail("thiếu quyền ghi phiếu")
	if doc.get("ai_classified_by") == CLASSIFIED_BY_HUMAN:
		return _fail("người đã phân loại, không ghi đè")
	values, skipped = _mapped_values(doc, args, ctx)
	if not values:
		return {"ok": True, "before": {}, "after": {}, "skipped": skipped}
	values["ai_confidence"] = args["confidence"]
	for field in (*values, "ai_classified_by", "ai_updated_at"):
		if not doc.has_permlevel_access_to(field, permission_type="write"):
			return _fail(f"thiếu quyền ghi trường {field}")
	before = {field: doc.get(field) for field in values}
	doc.update(values)
	doc.ai_classified_by = CLASSIFIED_BY_AI
	doc.ai_updated_at = now_datetime()
	doc.save()
	return {"ok": True, "before": before, "after": dict(values), "skipped": skipped}


def set_resolution_hint(args: dict, ctx: ToolContext) -> dict:
	doc = frappe.get_doc(TICKET_DOCTYPE, ctx.ticket_name)
	if not doc.has_permission("write"):
		return _fail("thiếu quyền ghi phiếu")
	if not doc.has_permlevel_access_to(HINT_FIELD, permission_type="write"):
		return _fail(f"thiếu quyền ghi trường {HINT_FIELD}")
	before = doc.get(HINT_FIELD)
	doc.set(HINT_FIELD, args["text"])
	doc.save()
	return {"ok": True, "before": before, "after": args["text"]}


def post_comment(args: dict, ctx: ToolContext) -> dict:
	doc = frappe.get_doc(TICKET_DOCTYPE, ctx.ticket_name)
	if not doc.has_permission("read"):
		return _fail("thiếu quyền đọc phiếu")
	if not frappe.has_permission("Comment", "create"):
		return _fail("thiếu quyền tạo comment")
	try:
		name = doc.new_comment(args["content"])
	except frappe.PermissionError:
		return _fail("không được phép thêm comment vào phiếu")
	return {"ok": True, "comment": name}


def create_task(args: dict, ctx: ToolContext) -> dict:
	if not ctx.instructor:
		return _fail("không có người ra lệnh")
	if not frappe.db.exists("DocType", TASK_DOCTYPE):
		return _fail("hệ thống không có DocType Task")
	doc = frappe.get_doc(TICKET_DOCTYPE, ctx.ticket_name)
	if not doc.has_permission("read"):
		return _fail("thiếu quyền đọc phiếu")
	if not frappe.has_permission(TASK_DOCTYPE, "create"):
		return _fail("thiếu quyền tạo Task")
	link = f"Phiếu {doc.name}: /helpdesk/tickets/{doc.name}"
	task = frappe.get_doc(
		{
			"doctype": TASK_DOCTYPE,
			"subject": args["subject"],
			"description": f"{link}\n\n{args['description']}",
		}
	)
	task.insert()
	return {"ok": True, "task": task.name}


TOOLS: list[ToolSpec] = [
	ToolSpec(
		name="set_classification",
		group="ticket_write",
		schema={
			"name": "set_classification",
			"description": (
				"Ghi phân loại của phiếu hiện tại theo đầu mục A-F và độ tin cậy. "
				"Loại, nhóm và mức ưu tiên lấy từ ánh xạ đầu mục, không nhận tên trường."
			),
			"input_schema": {
				"type": "object",
				"properties": {
					"category": {"type": "string", "enum": list(CATEGORIES)},
					"confidence": {"type": "string", "enum": list(CONFIDENCE_VALUES)},
				},
				"required": ["category", "confidence"],
			},
		},
		handler=set_classification,
	),
	ToolSpec(
		name="set_resolution_hint",
		group="ticket_write",
		schema={
			"name": "set_resolution_hint",
			"description": "Ghi hướng giải quyết gợi ý cho phiếu hiện tại.",
			"input_schema": {
				"type": "object",
				"properties": {"text": {"type": "string", "minLength": 1, "maxLength": 5000}},
				"required": ["text"],
			},
		},
		handler=set_resolution_hint,
	),
	ToolSpec(
		name="post_comment",
		group="ticket_write",
		schema={
			"name": "post_comment",
			"description": "Đăng một comment lên phiếu hiện tại.",
			"input_schema": {
				"type": "object",
				"properties": {"content": {"type": "string", "minLength": 1, "maxLength": 5000}},
				"required": ["content"],
			},
		},
		handler=post_comment,
	),
	ToolSpec(
		name="create_task",
		group="task_write",
		schema={
			"name": "create_task",
			"description": "Tạo một Task cho phiếu hiện tại; chỉ dùng khi có người ra lệnh.",
			"input_schema": {
				"type": "object",
				"properties": {
					"subject": {"type": "string", "minLength": 1, "maxLength": 140},
					"description": {"type": "string", "minLength": 1, "maxLength": 5000},
				},
				"required": ["subject", "description"],
			},
		},
		handler=create_task,
	),
]
