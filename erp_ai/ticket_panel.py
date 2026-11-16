"""Ticket-page panel (ADR-009, ADR-010): what the bot filled in on a ticket, and the conversation with it.

Everything is read under the caller's own permissions.
"""

import html

import frappe
from frappe import _
from frappe.core.utils import html_to_plain_text
from frappe.desk.form.activity import get_activity_timeline
from frappe.utils import cstr, format_datetime
from frappe.utils.html_utils import sanitize_html
from helpdesk.utils import is_agent

from erp_ai.agent.policy import contains_keyword, get_trigger_keyword
from erp_ai.constants import AGENT_USER, LOGGER_NAME, PANEL_MAX_MESSAGE_CHARS

TICKET_DOCTYPE = "HD Ticket"
# The three fields the bot classifies, with the wording its own "Đã làm" line uses for them.
CLASSIFICATION_LABELS = {"ticket_type": "Loại", "agent_group": "Nhóm", "priority": "Ưu tiên"}
AI_FIELDS = (
	"ai_resolution_hint",
	"ai_confidence",
	"ai_confidence_pct",
	"ai_complexity",
	"ai_importance",
	"ai_score_reason",
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


def _thread(ticket: str) -> list[dict]:
	"""Conversation with the bot, old to new: keyword comments, and agent comments after the first of them.

	What the agent wrote before anyone spoke to it (classification, guidance at ticket creation) is ticket
	information, shown from the ticket's fields, not a message here. This narrows B-5 of ADR-010.
	"""
	items = get_activity_timeline(TICKET_DOCTYPE, ticket, ["comment"])["activities"]
	messages = []
	for item in items:
		if item["type"] != "comment":
			continue
		content = item["data"]["content"]
		is_bot = item["author"]["email"] == AGENT_USER
		if is_bot and not messages:
			continue
		if not is_bot and not contains_keyword(content):
			continue
		messages.append(
			{
				"name": item["data"]["name"],
				"author": item["author"]["fullname"],
				"is_bot": is_bot,
				"created_at": format_datetime(item["timestamp"]),
				"text": html_to_plain_text(content),
			}
		)
	return messages


@frappe.whitelist(methods=["POST"])
def get_panel_data(ticket: str) -> dict:
	if not isinstance(ticket, str) or not ticket.strip():
		frappe.throw(_("Thiếu mã phiếu."), frappe.ValidationError)
	ticket = ticket.strip()
	_require_panel_access(ticket)
	messages = _thread(ticket)
	frappe.logger(LOGGER_NAME).debug(f"erp_ai panel read ticket={ticket} messages={len(messages)}")
	return {"ticket": ticket, "ai_fields": _ai_fields(ticket), "messages": messages}


def _message_content(text) -> tuple[str, bool]:
	"""B-6: the typed text escaped, line breaks kept, the trigger keyword appended when missing.

	Returns the content and whether the keyword was appended."""
	if not isinstance(text, str) or not text.strip():
		frappe.throw(_("Nội dung tin trống."), frappe.ValidationError)
	text = text.strip()
	if len(text) > PANEL_MAX_MESSAGE_CHARS:
		frappe.throw(_("Tin dài quá {0} ký tự.").format(PANEL_MAX_MESSAGE_CHARS), frappe.ValidationError)
	body = "<br>".join(html.escape(line, quote=False) for line in text.splitlines())
	keyword = get_trigger_keyword()
	keyword_added = bool(keyword) and not contains_keyword(body)
	if keyword_added:
		body = f"{body} {html.escape(keyword, quote=False)}"
	return f"<p>{body}</p>", keyword_added


@frappe.whitelist(methods=["POST"])
def send_message(ticket: str, text: str) -> dict:
	"""Post the typed text as a Comment on the ticket, owned by the caller (B-6).

	Input: ticket name; text, 1-PANEL_MAX_MESSAGE_CHARS characters after strip().
	Output: {"comment": <Comment name>}.
	Errors: PermissionError (not an active agent, no read on the ticket, or the agent account);
	ValidationError (missing ticket, empty or too long text, or a trigger keyword that does not survive
	storage as a Comment); FrappeTypeError (text not a string).
	"""
	if not isinstance(ticket, str) or not ticket.strip():
		frappe.throw(_("Thiếu mã phiếu."), frappe.ValidationError)
	ticket = ticket.strip()
	_require_panel_access(ticket, forbid_agent_user=True)
	content, keyword_added = _message_content(text)
	# Same call as Comment.validate: the stored form must still trigger the agent handler (ADR-010 Amendment 1).
	if get_trigger_keyword() and not contains_keyword(sanitize_html(content, always_sanitize=True)):
		frappe.logger(LOGGER_NAME).info(
			f"erp_ai panel send rejected ticket={ticket} reason=keyword_not_storable"
		)
		frappe.throw(
			_(
				"Từ khóa kích hoạt trong ERP AI Setting có ký tự không dùng được. Quản trị viên cần đổi từ khóa này."
			),
			frappe.ValidationError,
		)
	comment = frappe.get_doc(TICKET_DOCTYPE, ticket).new_comment(content)
	frappe.logger(LOGGER_NAME).info(
		f"erp_ai panel send ticket={ticket} comment={comment} keyword_added={str(keyword_added).lower()}"
	)
	return {"comment": comment}
