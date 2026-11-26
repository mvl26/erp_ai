"""Bot reply notices: each bot message in a ticket's chat is one unread Notification Log for the ticket's
assignees and the people who wrote in that chat. Helpdesk's Miyano bot counts them on its badge and marks them
read when the person opens that ticket's chat.
"""

import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

from erp_ai.constants import AGENT_USER, BOT_REPLY_NOTIFICATION_TYPE, MESSAGE_DOCTYPE

TICKET_DOCTYPE = "HD Ticket"
PREVIEW_CHARS = 120


def recipients(ticket: str) -> list[str]:
	"""The open assignees of `ticket` and every person who wrote in its chat, never the bot."""
	assignees = frappe.get_all(
		"ToDo",
		filters={"reference_type": TICKET_DOCTYPE, "reference_name": ticket, "status": "Open"},
		pluck="allocated_to",
	)
	talkers = frappe.get_all(
		MESSAGE_DOCTYPE,
		filters={"ticket": ticket, "owner": ("!=", AGENT_USER)},
		pluck="owner",
		distinct=True,
	)
	return sorted({user for user in (*assignees, *talkers) if user and user != AGENT_USER})


def preview(content: str | None) -> str:
	text = " ".join((content or "").split())
	return text if len(text) <= PREVIEW_CHARS else text[: PREVIEW_CHARS - 1] + "…"


def notify(message) -> None:
	"""One unread notice per recipient for the bot `message` (an ERP AI Message the bot owns)."""
	users = recipients(message.ticket)
	if not users:
		return
	enqueue_create_notification(
		users,
		{
			"type": BOT_REPLY_NOTIFICATION_TYPE,
			"document_type": TICKET_DOCTYPE,
			"document_name": message.ticket,
			"source_doctype": MESSAGE_DOCTYPE,
			"source_name": message.name,
			"from_user": AGENT_USER,
			"subject": _("Bot Miyano trả lời trong phiếu #{0}: {1}").format(
				message.ticket, preview(message.content)
			),
		},
	)
