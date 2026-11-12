import frappe
from frappe.desk.form import assign_to
from frappe.utils import now_datetime

from erp_ai.agent.classification import Classification
from erp_ai.agent.routing import RouteDecision
from erp_ai.agent.tools.registry import ToolContext
from erp_ai.agent.tools.write_ticket import LINKED_DOCTYPES, REASON_MAX, TICKET_DOCTYPE, post_comment
from erp_ai.constants import CLASSIFIED_BY_AI, CLASSIFIED_BY_HUMAN

# Fixed sentences for the routing comment (design 3.6). They never carry ticket content or raw configuration.
ASSIGN_REQUEST = "Bot chưa gán được người phụ trách cho phiếu này: {reason}. Nhờ trưởng nhóm phân công."
REASON_NO_VALID_ASSIGNEE = "cấu hình không có người hợp lệ"
REASON_ASSIGN_FAILED = "gán người không thành công"
REASON_TASK_NOT_ASSIGNED = "không giao được Task cho người phụ trách (chia sẻ tài liệu đang tắt)"
NO_SLA = "Chưa có SLA áp vào phiếu, cần System Manager cấu hình."


def _fail(reason: str) -> dict:
	return {"ok": False, "reason": reason[:REASON_MAX]}


def apply_route(decision: RouteDecision, classification: Classification, ctx: ToolContext) -> dict:
	"""Write the route and the scores with one `doc.save()` of the ticket (ADR-019). Not a model tool."""
	doc = frappe.get_doc(TICKET_DOCTYPE, ctx.ticket_name)
	if not doc.has_permission("write"):
		return _fail("thiếu quyền ghi phiếu")
	if doc.get("ai_classified_by") == CLASSIFIED_BY_HUMAN:
		return _fail("người đã phân loại, không ghi đè")
	values, skipped = {}, []
	for field in LINKED_DOCTYPES:
		value = getattr(decision, field)
		if not value:
			skipped.append({"field": field, "reason": "ánh xạ không có giá trị"})
		elif not frappe.db.exists(LINKED_DOCTYPES[field], value):
			skipped.append({"field": field, "reason": "giá trị không tồn tại trên hệ thống"})
		else:
			values[field] = value
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
