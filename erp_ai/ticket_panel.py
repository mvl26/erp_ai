"""Ticket-page panel (ADR-009, ADR-010, ADR-044): what the bot filled in on a ticket, the conversation with it,
the bot's status on the ticket, and the Duyệt / Từ chối buttons of the ticket's change proposals.

The ticket's fields are read under the caller's own permissions; the conversation and the bot's status are read
by ticket once the caller has passed the panel gate (ADR-010 Amendments 2 and 4). A decision passes the gate on
the proposal's own ticket, then the panel predicate, then the form's own method (ADR-044 QĐ 5).
"""

import frappe
from frappe import _
from frappe.core.utils import html_to_plain_text
from frappe.utils import cstr, format_datetime
from helpdesk.utils import is_agent

from erp_ai.agent import bot_status, change_link, messages
from erp_ai.constants import AGENT_USER, LOGGER_NAME, PANEL_MAX_MESSAGE_CHARS
from erp_ai.erp_ai_agent.doctype.erp_ai_change_proposal import erp_ai_change_proposal as proposal_form

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


# ADR-044 QĐ 1 (CHG-008 design 3.2): what the panel's Duyệt / Từ chối buttons may do, each the form's own method.
# FEAT-007 W2 adds its action here, not a method.
PANEL_DECISIONS = {
	# CHG-010: the panel approves through `panel_approve`, the only path that may approve a console script.
	change_link.ACTION_APPROVE: proposal_form.panel_approve,
	change_link.ACTION_REJECT: proposal_form.reject,
}


def _log_denied(method, ticket, reason):
	"""Ids and reasons only, never ticket content."""
	frappe.logger(LOGGER_NAME).info(f"erp_ai panel denied method={method} ticket={ticket} reason={reason}")


def _require_panel_access(ticket: str | None, *, method: str) -> None:
	"""Shared gate of the panel methods: an active agent who can read the ticket.

	`method` is the label of the caller ("get", "send" or "decide"): it names the log line, and every method but
	"get" also refuses the agent account. A missing ticket is a ticket nobody can read.
	"""
	if not is_agent():
		_log_denied(method, ticket, "not_agent")
		frappe.throw(_("Bạn không có quyền xem khu vực này của phiếu."), frappe.PermissionError)
	if (
		not ticket
		or not frappe.db.exists(TICKET_DOCTYPE, ticket)
		or not frappe.has_permission(TICKET_DOCTYPE, "read", doc=ticket)
	):
		_log_denied(method, ticket, "no_read")
		frappe.throw(_("Bạn không có quyền xem khu vực này của phiếu."), frappe.PermissionError)
	if method != "get" and frappe.session.user == AGENT_USER:
		_log_denied(method, ticket, "agent_user")
		if method == "send":
			frappe.throw(_("Tài khoản agent không được gửi tin từ khu vực này."), frappe.PermissionError)
		frappe.throw(_("Tài khoản agent không được duyệt hoặc từ chối đề xuất."), frappe.PermissionError)


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
	"""Everything the panel shows for `ticket`, read after the panel gate; writes nothing (ADR-010 QĐ 5).

	Output: exactly {"ticket", "ai_fields", "messages", "proposals", "bot_status"} (ADR-044 Amendment 1);
	`bot_status` is `bot_status.panel_status` for the ticket and its messages: the status line and the system
	lines anchored under the messages (CHG-009 design 3.1), never a message itself.
	Errors: ValidationError (missing ticket); PermissionError (not an active agent, or no read on the ticket).
	"""
	if not isinstance(ticket, str) or not ticket.strip():
		frappe.throw(_("Thiếu mã phiếu."), frappe.ValidationError)
	ticket = ticket.strip()
	_require_panel_access(ticket, method="get")
	thread = messages.thread(ticket)
	proposals = proposal_form.panel_cards(ticket)
	status = bot_status.panel_status(ticket, [message["name"] for message in thread])
	frappe.logger(LOGGER_NAME).debug(
		f"erp_ai panel read ticket={ticket} messages={len(thread)} proposals={len(proposals)}"
	)
	return {
		"ticket": ticket,
		"ai_fields": _ai_fields(ticket),
		"messages": thread,
		"proposals": proposals,
		"bot_status": status,
	}


@frappe.whitelist(methods=["POST"])
def send_message(ticket: str, text: str) -> dict:
	"""Add the typed text to the ticket's conversation with the bot, owned by the caller (B-6).

	Input: ticket name; text, 1-PANEL_MAX_MESSAGE_CHARS characters after strip().
	Output: {"message": <ERP AI Message name>}. The text is stored as typed, with no keyword and no markup.
	The message handler decides whether the agent runs; the panel only writes the message.
	Errors: PermissionError (not an active agent, no read on the ticket, or the agent account);
	ValidationError (missing ticket, empty or too long text); FrappeTypeError (text not a string).
	"""
	if not isinstance(ticket, str) or not ticket.strip():
		frappe.throw(_("Thiếu mã phiếu."), frappe.ValidationError)
	ticket = ticket.strip()
	_require_panel_access(ticket, method="send")
	if not isinstance(text, str) or not text.strip():
		frappe.throw(_("Nội dung tin trống."), frappe.ValidationError)
	text = text.strip()
	if len(text) > PANEL_MAX_MESSAGE_CHARS:
		frappe.throw(_("Tin dài quá {0} ký tự.").format(PANEL_MAX_MESSAGE_CHARS), frappe.ValidationError)
	name = messages.add_message(ticket, text, trusted=True)
	frappe.logger(LOGGER_NAME).info(f"erp_ai panel send ticket={ticket} message={name}")
	return {"message": name}


@frappe.whitelist(methods=["POST"])
def decide_proposal(name=None, action=None) -> dict:
	"""Approve or reject change proposal `name` from the ticket panel, as the session user (ADR-044 QĐ 5).

	Input: `name` of the proposal; `action`, a key of `PANEL_DECISIONS`. No ticket: the gate reads the proposal's
	own ticket from its record. Neither has a type annotation on purpose: Frappe would refuse a wrong type with its
	own error before the checks below, which answer it as design 3.2 says.
	Output: {"name", "status"}, the result of the form's own `approve` / `reject`.
	Errors, checked in this order, each writing nothing: ValidationError (`action` not a key of
	`PANEL_DECISIONS`); DoesNotExistError (no such proposal); PermissionError (the panel gate on the proposal's
	ticket, which also refuses the agent account; then the panel predicate: role, not pending, one-click switch
	off, or for a console proposal the console switch off). InvalidTransition: a second call that passed the predicate before the first one wrote.
	"""
	if not isinstance(action, str) or action not in PANEL_DECISIONS:
		frappe.throw(_("Hành động không hợp lệ."), frappe.ValidationError)
	head = proposal_form.proposal_head(name)
	_require_panel_access(head.ticket, method="decide")
	refusal = proposal_form.panel_decision_refusal(head.change_status, console=head.is_console)
	if refusal is not None:
		frappe.logger(LOGGER_NAME).info(f"erp_ai panel decide refused proposal={name} reason={refusal}")
		frappe.throw(_(proposal_form.PANEL_REFUSALS[refusal]), frappe.PermissionError)
	result = PANEL_DECISIONS[action](name)
	frappe.logger(LOGGER_NAME).info(
		f"erp_ai panel decide proposal={name} action={action} status={result['status']}"
	)
	return result
