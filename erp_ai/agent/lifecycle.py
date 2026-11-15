"""Ticket lifecycle (FEAT-007 U6b, ADR-033): the N-2 status changes that need no model.

Agent core: never imports the model gateway, the tools or the runner (ADR-033 QĐ 3, Ràng buộc 4); it reads
the lifecycle switches and the origin field itself (`lifecycle_settings`) and never writes ERP AI Setting.
"""

from dataclasses import dataclass
from datetime import datetime

import frappe
from frappe.utils import extract_email_id

from erp_ai.agent import policy
from erp_ai.constants import AGENT_USER, SETTING_DOCTYPE

STATUS_RESOLVED = "Resolved"
STATUS_CLOSED = "Closed"
RESOLVED_CATEGORY = "Resolved"
TASK_COMPLETED = "Completed"
TASK_CANCELLED = "Cancelled"
CATEGORY_E = "E"
CATEGORY_F = "F"
TOOL_RESOLVE_ON_TASKS_DONE = "resolve_on_tasks_done"
TOOL_CLOSE_SILENT_F = "close_silent_f"
TOOL_LIFECYCLE_COMMENT = "lifecycle_comment"
TOOL_REQUESTER_NOTICE = "requester_notice"
TOOL_LIFECYCLE_CONFIG = "ticket_lifecycle"
REASON_ORIGIN_NOT_CONFIGURED = "chưa cấu hình trường Nguồn phát sinh (field_origin, origin_board_value)"
TITLE_LIFECYCLE_FAILED = "ERP AI lifecycle failed"
COMMENT_RESOLVED = "ERP AI: mọi Task liên kết đã xong ({completed} Completed), phiếu chuyển Resolved."
COMMENT_SILENT_CLOSED = "ERP AI: người tạo chưa phản hồi {days} ngày sau tin của bot, phiếu chuyển Closed."
NOTICE_SILENT_CLOSE = (
	"Phiếu #{ticket} được đóng vì chưa nhận được phản hồi sau {days} ngày. "
	"Nếu vấn đề còn, anh/chị trả lời tin này để mở lại."
)

TICKET_DOCTYPE = "HD Ticket"
# Refusal codes of status_change_refusal, in the order they are checked (AC-42 (b), (c); A-U6b-5).
REFUSAL_ORIGIN_NOT_CONFIGURED = "origin_not_configured"
REFUSAL_NOT_SENDABLE = "not_sendable"
REFUSAL_BOARD_DIRECTED = "board_directed"
REFUSAL_CATEGORY_E = "category_e"
# ERP AI Setting `close_silent_f_days` (Int 3, 1..30); anything else reads the default.
CLOSE_SILENT_F_DAYS_DEFAULT = 3
CLOSE_SILENT_F_DAYS_MIN = 1
CLOSE_SILENT_F_DAYS_MAX = 30


@dataclass(frozen=True)
class LifecycleSettings:
	reply: bool
	resolve_on_tasks_done: bool
	close_silent_f: bool
	close_silent_f_days: int
	kb_draft: bool
	field_origin: str
	origin_board_value: str


def _days(value) -> int:
	try:
		days = int(value)
	except (TypeError, ValueError):
		return CLOSE_SILENT_F_DAYS_DEFAULT
	return days if CLOSE_SILENT_F_DAYS_MIN <= days <= CLOSE_SILENT_F_DAYS_MAX else CLOSE_SILENT_F_DAYS_DEFAULT


def _text(value) -> str:
	return (value or "").strip()


def lifecycle_settings(settings) -> LifecycleSettings:
	"""The only reader of the seven lifecycle fields of ERP AI Setting; a missing field reads off / blank."""
	return LifecycleSettings(
		reply=bool(getattr(settings, "reply_enabled", 0)),
		resolve_on_tasks_done=bool(getattr(settings, "resolve_on_tasks_done_enabled", 0)),
		close_silent_f=bool(getattr(settings, "close_silent_f_enabled", 0)),
		close_silent_f_days=_days(getattr(settings, "close_silent_f_days", None)),
		kb_draft=bool(getattr(settings, "kb_draft_enabled", 0)),
		field_origin=_text(getattr(settings, "field_origin", None)),
		origin_board_value=_text(getattr(settings, "origin_board_value", None)),
	)


def kb_draft_enabled() -> bool:
	"""The knowledge-draft switch in one read, for the handler."""
	return bool(frappe.db.get_single_value(SETTING_DOCTYPE, "kb_draft_enabled"))


def origin_configured(ls: LifecycleSettings) -> bool:
	"""Both origin settings set and `field_origin` a field of HD Ticket; anything else is False (fail-closed, AC-42 (c))."""
	return bool(
		ls.field_origin
		and ls.origin_board_value
		and frappe.get_meta(TICKET_DOCTYPE).has_field(ls.field_origin)
	)


def _normalize(value) -> str:
	return str(value or "").strip().casefold()


def status_change_refusal(ticket_name: str, ls: LifecycleSettings) -> str | None:
	"""The one guard of both N-2 status changes (AC-42 (b)): why the bot must not change this ticket's status, or None.

	First match wins: origin not configured, not sendable (excluded ticket, A-U6b-5), board-directed origin
	(compared after strip and casefold), latest category E.
	"""
	if not origin_configured(ls):
		return REFUSAL_ORIGIN_NOT_CONFIGURED
	if not policy.can_send_ticket(ticket_name):
		return REFUSAL_NOT_SENDABLE
	origin = frappe.db.get_value(TICKET_DOCTYPE, ticket_name, ls.field_origin)
	if _normalize(origin) == _normalize(ls.origin_board_value):
		return REFUSAL_BOARD_DIRECTED
	if policy.latest_classification(ticket_name)[0] == CATEGORY_E:
		return REFUSAL_CATEGORY_E
	return None


def _ticket_messages(ticket_name: str, sent_or_received: str) -> dict:
	return {
		"reference_doctype": TICKET_DOCTYPE,
		"reference_name": ticket_name,
		"sent_or_received": sent_or_received,
	}


def _bot_messages(ticket_name: str) -> dict:
	"""The filter of the bot's own messages to the requester on a ticket."""
	return {**_ticket_messages(ticket_name, "Sent"), "owner": AGENT_USER}


def is_requester_sender(sender, raised_by) -> bool:
	"""Same email address (display name dropped, casefold; A-U6b-9); a blank side never matches."""
	requester = extract_email_id(raised_by or "").casefold()
	return bool(requester) and extract_email_id(sender or "").casefold() == requester


def send_to_requester(ticket_name: str, html: str) -> str:
	"""Reply to the ticket's requester only, through Helpdesk (a Communication Sent, its email queued; never a
	comment), under the session user. Returns the newest Sent Communication of the agent on the ticket.

	Errors are not caught: the caller decides.
	"""
	doc = frappe.get_doc(TICKET_DOCTYPE, ticket_name)
	doc.reply_via_agent(message=html, to=doc.raised_by)
	return frappe.db.get_value(
		"Communication", _bot_messages(ticket_name), "name", order_by="creation desc, name desc"
	)


def newer_requester_message_exists(ticket_name: str, communication_name: str) -> bool:
	"""Another Communication of the requester on the ticket (Received, type Communication) with a larger
	(creation, name) than `communication_name`."""
	given = frappe.db.get_value("Communication", communication_name, ["name", "creation"], as_dict=True)
	if not given:
		return False
	raised_by = frappe.db.get_value(TICKET_DOCTYPE, ticket_name, "raised_by")
	rows = frappe.get_all(
		"Communication",
		filters={
			**_ticket_messages(ticket_name, "Received"),
			"communication_type": "Communication",
			"name": ("!=", given.name),
			"creation": (">=", given.creation),
		},
		fields=["name", "creation", "sender"],
	)
	return any(
		is_requester_sender(row.sender, raised_by) and (row.creation, row.name) > (given.creation, given.name)
		for row in rows
	)


def silent_since(ticket_name: str) -> datetime | None:
	"""When the requester's silence began: the bot's last message, unless the requester wrote after it (then
	None until the bot's next message; AC-41, AC-44). None when the bot never wrote."""
	last_bot = frappe.db.get_value(
		"Communication", _bot_messages(ticket_name), "creation", order_by="creation desc"
	)
	if not last_bot:
		return None
	raised_by = frappe.db.get_value(TICKET_DOCTYPE, ticket_name, "raised_by")
	senders = frappe.get_all(
		"Communication",
		filters={**_ticket_messages(ticket_name, "Received"), "creation": (">", last_bot)},
		pluck="sender",
	)
	if any(is_requester_sender(sender, raised_by) for sender in senders):
		return None
	return last_bot
