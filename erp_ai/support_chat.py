"""Entry of the user-support chat in helpdesk's Miyano bot: checks who asks and what, then hands over to
agent/support.py. Like the panel, it never calls the model itself (ADR-001)."""

import json
from html import unescape

import frappe
from frappe import _
from frappe.utils import strip_html
from helpdesk.utils import is_agent

from erp_ai.agent import support
from erp_ai.constants import BOT_REPLY_NOTIFICATION_TYPE


@frappe.whitelist(methods=["POST"])
def ask(question: str, history: str | list | None = None) -> dict:
	"""The bot's answer to `question`, after the earlier `history` turns (a list, or its JSON).

	Output: `{"answer", "articles": [{"name", "title"}], "answered"}`.
	Errors: PermissionError (not an active agent); ValidationError (blank question or over the length limit).
	"""
	if not is_agent():
		frappe.throw(_("Chỉ nhân viên hỗ trợ mới dùng được bot này."), frappe.PermissionError)
	question = question.strip() if isinstance(question, str) else ""
	if not question:
		frappe.throw(_("Hãy nhập câu hỏi."), frappe.ValidationError)
	if len(question) > support.MAX_QUESTION_CHARS:
		frappe.throw(
			_("Câu hỏi dài quá {0} ký tự.").format(support.MAX_QUESTION_CHARS), frappe.ValidationError
		)
	return support.answer(question, _turns(history))


def _turns(history) -> list:
	if isinstance(history, str):
		try:
			history = json.loads(history)
		except ValueError:
			return []
	return history if isinstance(history, list) else []


NOTIFICATION_LOG = "Notification Log"
ASSIGNMENT_NOTICE = "Assignment"
NOTICE_TYPES = (ASSIGNMENT_NOTICE, BOT_REPLY_NOTIFICATION_TYPE)
MAX_NOTICE_TICKETS = 10
MAX_NOTICE_ROWS = 50
# The list shows only what was made from the day the notices shipped; older ones stay in the bell.
NOTICES_SINCE = "2026-11-27 00:00:00"


def plain_text(html: str | None) -> str:
	"""A notice's subject as plain text: Helpdesk writes the assignment subject as HTML."""
	return " ".join(unescape(strip_html(html or "")).split())


def _require_agent() -> None:
	if not is_agent():
		frappe.throw(_("Chỉ nhân viên hỗ trợ mới dùng được bot này."), frappe.PermissionError)


def _own_notice_filters(**extra) -> dict:
	return {
		"for_user": frappe.session.user,
		"type": ("in", list(NOTICE_TYPES)),
		"document_type": "HD Ticket",
		**extra,
	}


@frappe.whitelist(methods=["POST"])
def get_notices() -> dict:
	"""The caller's unread assignment and bot-reply notices of tickets, one row per ticket, newest first.

	Output: `{"unread": int, "tickets": [{"ticket", "unread", "type", "subject", "creation"}]}`.
	Errors: PermissionError (not an active agent).
	"""
	_require_agent()
	rows = frappe.get_all(
		NOTIFICATION_LOG,
		filters=_own_notice_filters(read=0, creation=(">=", NOTICES_SINCE)),
		fields=["type", "subject", "document_name", "creation"],
		order_by="creation desc",
		limit_page_length=MAX_NOTICE_ROWS,
	)
	by_ticket: dict = {}
	for row in rows:
		entry = by_ticket.get(row.document_name)
		if entry is None:
			entry = by_ticket[row.document_name] = {
				"ticket": row.document_name,
				"unread": 0,
				"type": row.type,
				"subject": plain_text(row.subject),
				"creation": str(row.creation),
			}
		entry["unread"] += 1
	return {"unread": len(rows), "tickets": list(by_ticket.values())[:MAX_NOTICE_TICKETS]}


@frappe.whitelist(methods=["POST"])
def mark_notices_read(
	ticket: str | None = None,
	with_bot_replies: bool | int | str = False,
	only_bot_replies: bool | int | str = False,
) -> None:
	"""Mark the caller's unread notices of `ticket` read: its assignments, and its bot replies only when
	`with_bot_replies` is true (the person has the bot's chat of that ticket in front of them). Without a
	ticket it marks every notice the list shows (those made since NOTICES_SINCE). With `only_bot_replies`
	only bot replies are marked (the person opened the bot, so its replies are seen; assignments are not).

	Errors: PermissionError (not an active agent).
	"""
	_require_agent()
	types = [ASSIGNMENT_NOTICE]
	if _truthy(with_bot_replies):
		types.append(BOT_REPLY_NOTIFICATION_TYPE)
	if _truthy(only_bot_replies):
		types = [BOT_REPLY_NOTIFICATION_TYPE]
	extra = {"document_name": str(ticket)} if ticket else {"creation": (">=", NOTICES_SINCE)}
	names = frappe.get_all(
		NOTIFICATION_LOG,
		filters={**_own_notice_filters(read=0, **extra), "type": ("in", types)},
		pluck="name",
	)
	for name in names:
		frappe.db.set_value(NOTIFICATION_LOG, name, "read", 1, update_modified=False)


def _truthy(value) -> bool:
	return bool(frappe.parse_json(value) if isinstance(value, str) else value)
