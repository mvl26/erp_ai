import frappe
from frappe.utils import now_datetime

from erp_ai.agent.classification import Classification
from erp_ai.agent.routing import RouteDecision
from erp_ai.agent.tools.registry import ToolContext
from erp_ai.agent.tools.write_ticket import LINKED_DOCTYPES, REASON_MAX, TICKET_DOCTYPE
from erp_ai.constants import CLASSIFIED_BY_AI, CLASSIFIED_BY_HUMAN


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
	for field in (*values, "ai_classified_by", "ai_updated_at"):
		if not doc.has_permlevel_access_to(field, permission_type="write"):
			return _fail(f"thiếu quyền ghi trường {field}")
	before = {field: doc.get(field) for field in values}
	doc.update(values)
	doc.ai_classified_by = CLASSIFIED_BY_AI
	doc.ai_updated_at = now_datetime()
	doc.save()
	return {"ok": True, "before": before, "after": dict(values), "skipped": skipped}
