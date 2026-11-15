import dataclasses
import json

import frappe
from frappe.utils import escape_html, now_datetime

from erp_ai.agent import policy, site_facts
from erp_ai.agent.classification import Classification
from erp_ai.agent.routing import RouteDecision, decide_route
from erp_ai.agent.tools.registry import ToolContext, ToolSpec
from erp_ai.constants import (
	CATEGORIES,
	CLASSIFICATION_FIELDS,
	CLASSIFIED_BY_AI,
	CLASSIFIED_BY_HUMAN,
	CONFIDENCE_VALUES,
	LOGGER_NAME,
)

TICKET_DOCTYPE = "HD Ticket"
TASK_DOCTYPE = "Task"
HINT_FIELD = "ai_resolution_hint"
# Written by handlers.ticket_validate at creation; erp_ai.agent may not import erp_ai.handlers (LAYER_RULES).
CREATED_LABELS_FIELD = "ai_created_labels"
REASON_HUMAN_FILLED = "người đã điền lúc tạo phiếu"
# A broken record reads fail-closed: every classification field counts as filled by the person.
_EVERY_FIELD_HUMAN = dict.fromkeys(CLASSIFICATION_FIELDS, True)
# Target field -> DocType holding its allowed values (design 3.5).
LINKED_DOCTYPES = {
	"ticket_type": "HD Ticket Type",
	"agent_group": "HD Team",
	"priority": "HD Ticket Priority",
}
REASON_MAX = 200


def _fail(reason: str) -> dict:
	return {"ok": False, "reason": reason[:REASON_MAX]}


def _existing_values(wanted: dict, reasons: dict | None = None) -> tuple[dict, list]:
	"""Values to write (only those that exist on the site) and the skipped fields with a reason.

	`reasons` holds the routing reason for fields the route left empty on purpose.
	"""
	reasons = reasons or {}
	values, skipped = {}, []
	for field, value in wanted.items():
		if not value:
			skipped.append({"field": field, "reason": reasons.get(field, "ánh xạ không có giá trị")})
		elif not frappe.db.exists(LINKED_DOCTYPES[field], value):
			skipped.append({"field": field, "reason": "giá trị không tồn tại trên hệ thống"})
		else:
			values[field] = value
	return values, skipped


def created_labels(raw: str | None) -> dict:
	"""The classification fields a person typed at creation, read from `ai_created_labels`; empty → {}.

	Broken JSON, a value that is not a dict or a key outside CLASSIFICATION_FIELDS → all three (fail-closed);
	the caller logs the warning, it knows the ticket.
	"""
	if not raw:
		return {}
	try:
		labels = json.loads(raw)
	except (TypeError, ValueError):
		return dict(_EVERY_FIELD_HUMAN)
	if not isinstance(labels, dict) or not set(labels) <= set(CLASSIFICATION_FIELDS):
		return dict(_EVERY_FIELD_HUMAN)
	return labels


def keep_human_fields(decision: RouteDecision, labels: dict) -> RouteDecision:
	"""`decision` with every field of `labels` emptied and noted REASON_HUMAN_FILLED; the rest unchanged."""
	filled = [field for field in CLASSIFICATION_FIELDS if field in labels]
	if not filled:
		return decision
	notes = (*decision.notes, *({"field": field, "reason": REASON_HUMAN_FILLED} for field in filled))
	return dataclasses.replace(decision, **dict.fromkeys(filled), notes=notes)


def _mapped_values(doc, args: dict, ctx: ToolContext) -> tuple[dict, list]:
	classification = Classification(
		category=args["category"],
		confidence=args["confidence"],
		complexity=doc.ai_complexity or 0,
		importance=doc.ai_importance or 0,
	)
	labels = created_labels(doc.get(CREATED_LABELS_FIELD))
	if labels == _EVERY_FIELD_HUMAN:
		frappe.logger(LOGGER_NAME).warning(f"erp_ai created_labels invalid ticket={doc.name}")
	decision = keep_human_fields(
		decide_route(
			classification,
			doc.subject,
			ctx.category_mapping,
			ctx.routing_config or {},
			team_exists=site_facts.team_exists,
			is_excluded_team=policy.is_excluded_team,
			is_active_agent=site_facts.is_active_agent,
		),
		labels,
	)
	wanted = {
		"ticket_type": decision.ticket_type,
		"agent_group": decision.agent_group,
		"priority": decision.priority,
	}
	reasons = {note["field"]: note["reason"] for note in decision.notes if note["field"] in wanted}
	return _existing_values(wanted, reasons)


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
	# Frappe sanitizes Text Editor values on save: report what was stored, not the raw input.
	return {"ok": True, "before": before, "after": doc.get(HINT_FIELD)}


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


def _ticket_link_html(name: str) -> str:
	"""The clickable ticket paragraph that opens a Task description (Text Editor, HTML)."""
	path = f"/helpdesk/tickets/{name}"
	return f'<p>Phiếu {escape_html(name)}: <a href="{escape_html(path)}">{escape_html(path)}</a></p>'


def _task_refusal(ctx: ToolContext) -> dict | None:
	"""`ok=false` result when a Task cannot be created for the ticket, else None."""
	if not frappe.db.exists("DocType", TASK_DOCTYPE):
		return _fail("hệ thống không có DocType Task")
	if not frappe.get_doc(TICKET_DOCTYPE, ctx.ticket_name).has_permission("read"):
		return _fail("thiếu quyền đọc phiếu")
	if not frappe.has_permission(TASK_DOCTYPE, "create"):
		return _fail("thiếu quyền tạo Task")
	return None


def create_task(args: dict, ctx: ToolContext) -> dict:
	if not ctx.instructor:
		return _fail("không có người ra lệnh")
	if refusal := _task_refusal(ctx):
		return refusal
	link = _ticket_link_html(ctx.ticket_name)
	text = escape_html(args["description"]).replace("\r\n", "\n").replace("\n", "<br>")
	task = frappe.get_doc(
		{
			"doctype": TASK_DOCTYPE,
			"subject": args["subject"],
			"ai_ticket": ctx.ticket_name,
			"description": f"{link}\n<p>{text}</p>",
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
