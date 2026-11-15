"""Ticket-page panel (ADR-009, ADR-010): what the bot filled in on a ticket, and the conversation with it.

Everything is read under the caller's own permissions.
"""

import frappe
from frappe import _
from frappe.core.utils import html_to_plain_text
from frappe.utils import cstr, format_datetime
from helpdesk.utils import is_agent

from erp_ai.agent import messages
from erp_ai.constants import AGENT_USER, LOGGER_NAME, MESSAGE_KIND_CHAT, PANEL_MAX_MESSAGE_CHARS

TICKET_DOCTYPE = "HD Ticket"
# The three fields the bot classifies, with the wording its own "Đã làm" line uses for them.
CLASSIFICATION_LABELS = {"ticket_type": "Loại", "agent_group": "Nhóm", "priority": "Ưu tiên"}
# Display order: why it was classified so and how it was scored, what the run concluded and did, who and when.
AI_FIELDS = (
	"ai_classification_reason",
	"ai_confidence",
	"ai_confidence_pct",
	"ai_complexity",
	"ai_importance",
	"ai_score_reason",
	"ai_resolution_hint",
	"ai_analysis",
	"ai_done",
	"ai_pending",
	"ai_manual",
	"ai_classified_by",
	"ai_updated_at",
)


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
	"""The ticket's own record: the classification the bot filled in, then the AI fields."""
	meta = frappe.get_meta(TICKET_DOCTYPE)
	doc = frappe.get_doc(TICKET_DOCTYPE, ticket)
	doc.apply_fieldlevel_read_permissions()
	labels = {**CLASSIFICATION_LABELS, **{name: meta.get_label(name) for name in AI_FIELDS}}
	return [
		{"fieldname": name, "label": label, "text": _field_text(meta, doc, name)}
		for name, label in labels.items()
	]


@frappe.whitelist(methods=["POST"])
def get_panel_data(ticket: str) -> dict:
	if not isinstance(ticket, str) or not ticket.strip():
		frappe.throw(_("Thiếu mã phiếu."), frappe.ValidationError)
	ticket = ticket.strip()
	_require_panel_access(ticket)
	thread = messages.thread(ticket)
	frappe.logger(LOGGER_NAME).debug(f"erp_ai panel read ticket={ticket} messages={len(thread)}")
	return {"ticket": ticket, "ai_fields": _ai_fields(ticket), "messages": thread}


@frappe.whitelist(methods=["POST"])
def send_message(ticket: str, text: str) -> dict:
	"""Post the typed text as a chat message on the ticket, owned by the caller (B-6).

	Input: ticket name; text, 1-PANEL_MAX_MESSAGE_CHARS characters after strip().
	Output: {"message": <ERP AI Message name>}. The text is stored as typed, with no keyword and no markup.
	The message handler decides whether the agent runs; the panel only writes the message.
	Errors: PermissionError (not an active agent, no read on the ticket, or the agent account);
	ValidationError (missing ticket, empty or too long text); FrappeTypeError (text not a string).
	"""
	if not isinstance(ticket, str) or not ticket.strip():
		frappe.throw(_("Thiếu mã phiếu."), frappe.ValidationError)
	ticket = ticket.strip()
	_require_panel_access(ticket, forbid_agent_user=True)
	if not isinstance(text, str) or not text.strip():
		frappe.throw(_("Nội dung tin trống."), frappe.ValidationError)
	text = text.strip()
	if len(text) > PANEL_MAX_MESSAGE_CHARS:
		frappe.throw(_("Tin dài quá {0} ký tự.").format(PANEL_MAX_MESSAGE_CHARS), frappe.ValidationError)
	name = messages.add_message(ticket, text, MESSAGE_KIND_CHAT, trusted=True)
	frappe.logger(LOGGER_NAME).info(f"erp_ai panel send ticket={ticket} message={name}")
	return {"message": name}
