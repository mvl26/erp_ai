import frappe
from frappe.desk.form import assign_to
from frappe.utils import escape_html, now_datetime

from erp_ai.agent.classification import Classification
from erp_ai.agent.routing import RouteDecision
from erp_ai.agent.tools.registry import ToolContext
from erp_ai.agent.tools.write_ticket import (
	LINKED_DOCTYPES,
	REASON_MAX,
	TASK_DOCTYPE,
	TICKET_DOCTYPE,
	_existing_values,
	_task_refusal,
	_ticket_link_html,
	post_comment,
)
from erp_ai.constants import CLASSIFIED_BY_AI, CLASSIFIED_BY_HUMAN

# Fixed sentences for the routing comment (design 3.6). They never carry ticket content or raw configuration.
ASSIGN_REQUEST = "Bot chưa gán được người phụ trách cho phiếu này: {reason}. Nhờ trưởng nhóm phân công."
TASK_REQUEST = (
	"Bot đã gán người phụ trách cho phiếu nhưng không giao được Task: {reason}. Nhờ trưởng nhóm giao Task."
)
REASON_NO_VALID_ASSIGNEE = "cấu hình không có người hợp lệ"
REASON_ASSIGN_FAILED = "gán người không thành công"
REASON_TASK_NOT_ASSIGNED = "chia sẻ tài liệu đang tắt"
NO_SLA = "Chưa có SLA áp vào phiếu, cần System Manager cấu hình."
SCORE_LINE = "Độ phức tạp {complexity}/3, độ quan trọng {importance}/3: {reason}"
TASK_SUBJECT_MAX = 140


def _fail(reason: str) -> dict:
	return {"ok": False, "reason": reason[:REASON_MAX]}


def apply_route(decision: RouteDecision, classification: Classification, ctx: ToolContext) -> dict:
	"""Write the route and the scores with one `doc.save()` of the ticket (ADR-019). Not a model tool."""
	doc = frappe.get_doc(TICKET_DOCTYPE, ctx.ticket_name)
	if not doc.has_permission("write"):
		return _fail("thiếu quyền ghi phiếu")
	if doc.get("ai_classified_by") == CLASSIFIED_BY_HUMAN:
		return _fail("người đã phân loại, không ghi đè")
	values, skipped = _existing_values({field: getattr(decision, field) for field in LINKED_DOCTYPES})
	values.update(
		ai_confidence=classification.confidence,
		ai_complexity=classification.complexity,
		ai_importance=classification.importance,
		ai_score_reason=classification.score_reason,
	)
	for field in ("ai_classified_by", "ai_updated_at"):
		if not doc.has_permlevel_access_to(field, permission_type="write"):
			return _fail(f"thiếu quyền ghi trường {field}")
	for field in list(values):
		if not doc.has_permlevel_access_to(field, permission_type="write"):
			del values[field]
			skipped.append({"field": field, "reason": "thiếu quyền ghi trường"})
	changed = [field for field, value in values.items() if doc.get(field) != value]
	before = {field: doc.get(field) for field in changed}
	doc.update(values)
	doc.ai_classified_by = CLASSIFIED_BY_AI
	doc.ai_updated_at = now_datetime()
	doc.save()
	return {
		"ok": True,
		"before": before,
		"after": {field: values[field] for field in changed},
		"skipped": skipped,
	}


def assign_owner(user: str, ctx: ToolContext) -> dict:
	"""Assign the ticket to `user` through Frappe's own `assign_to.add` (ADR-021 QĐ 3). Not a model tool."""
	doc = frappe.get_doc(TICKET_DOCTYPE, ctx.ticket_name)
	if not doc.has_permission("read"):
		return _fail("thiếu quyền đọc phiếu")
	assign_to.add({"assign_to": [user], "doctype": TICKET_DOCTYPE, "name": ctx.ticket_name})
	return {"ok": True, "assignee": user}


def post_routing_comment(lines: list[str], ctx: ToolContext) -> dict:
	"""Post the fixed sentences as ONE comment, reusing `post_comment`."""
	return post_comment({"content": "\n".join(lines)}, ctx)


def create_routed_task(
	user: str, ticket_subject: str, classification: Classification, ctx: ToolContext
) -> dict:
	"""Create the Task for a C/D ticket and give it to `user` (ADR-021 QĐ 2, 5). Not a model tool.

	A sharing failure from `assign_to.add` is not caught: it reaches the runner's savepoint.
	"""
	if refusal := _task_refusal(ctx):
		return refusal
	score = SCORE_LINE.format(
		complexity=classification.complexity,
		importance=classification.importance,
		reason=classification.score_reason,
	)
	task = frappe.get_doc(
		{
			"doctype": TASK_DOCTYPE,
			"subject": ticket_subject[:TASK_SUBJECT_MAX],
			"ai_ticket": ctx.ticket_name,
			"description": f"{_ticket_link_html(ctx.ticket_name)}\n<p>{escape_html(score)}</p>",
		}
	)
	task.insert()
	assign_to.add({"assign_to": [user], "doctype": TASK_DOCTYPE, "name": task.name})
	return {"ok": True, "task": task.name}
