"""Ticket-page panel (ADR-009, ADR-010): the AI fields of a ticket, read under the caller's own permissions."""

import frappe
from frappe import _
from frappe.core.utils import html_to_plain_text
from frappe.utils import cstr, format_datetime
from helpdesk.utils import is_agent

from erp_ai.constants import AGENT_USER, LOGGER_NAME

TICKET_DOCTYPE = "HD Ticket"
AI_FIELDS = ("ai_resolution_hint", "ai_confidence", "ai_classified_by", "ai_updated_at")


def _log_denied(method, ticket, reason):
	"""Ids and reasons only, never ticket content."""
	frappe.logger(LOGGER_NAME).info(f"erp_ai panel denied method={method} ticket={ticket} reason={reason}")


def _require_panel_access(ticket: str, *, forbid_agent_user: bool = False) -> None:
	"""Shared gate of both panel methods: an active agent who can read the ticket."""
	method = "send" if forbid_agent_user else "get"
	if not is_agent():
		_log_denied(method, ticket, "not_agent")
		frappe.throw(_("Bạn không có quyền xem khu vực này của phiếu."), frappe.PermissionError)
	if not frappe.db.exists(TICKET_DOCTYPE, ticket) or not frappe.has_permission(
		TICKET_DOCTYPE, "read", doc=ticket
	):
		_log_denied(method, ticket, "no_read")
		frappe.throw(_("Bạn không có quyền xem khu vực này của phiếu."), frappe.PermissionError)
	if forbid_agent_user and frappe.session.user == AGENT_USER:
		_log_denied(method, ticket, "agent_user")
		frappe.throw(_("Tài khoản agent không được gửi tin từ khu vực này."), frappe.PermissionError)


def _field_text(meta, doc, fieldname):
	value = doc.get(fieldname)
	if not value:
		return None
	fieldtype = meta.get_field(fieldname).fieldtype
	if fieldtype == "Text Editor":
		return html_to_plain_text(value) or None
	if fieldtype == "Datetime":
		return format_datetime(value)
	return cstr(value)


def _ai_fields(ticket: str) -> list[dict]:
	meta = frappe.get_meta(TICKET_DOCTYPE)
	doc = frappe.get_doc(TICKET_DOCTYPE, ticket)
	doc.apply_fieldlevel_read_permissions()
	return [
		{"fieldname": name, "label": meta.get_label(name), "text": _field_text(meta, doc, name)}
		for name in AI_FIELDS
	]


@frappe.whitelist(methods=["POST"])
def get_panel_data(ticket: str) -> dict:
	if not isinstance(ticket, str) or not ticket.strip():
		frappe.throw(_("Thiếu mã phiếu."), frappe.ValidationError)
	ticket = ticket.strip()
	_require_panel_access(ticket)
	return {"ticket": ticket, "ai_fields": _ai_fields(ticket), "messages": []}
