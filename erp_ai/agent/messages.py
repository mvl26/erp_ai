import frappe
from frappe.utils import format_datetime, get_fullname

from erp_ai.agent.prompts import MAX_COMMENTS
from erp_ai.constants import AGENT_USER, MESSAGE_DOCTYPE

THREAD_LIMIT = 200


def add_message(
	ticket: str,
	content: str,
	*,
	run_id: str | None = None,
	source_comment: str | None = None,
	trusted: bool = False,
) -> str:
	"""The one writer of ERP AI Message: one thing a person or the bot said in the ticket's conversation.
	Returns the row name; never commits.

	`trusted=True` inserts with `ignore_permissions=True`: only code that has already checked who may speak
	(the panel method, the @ai comment hook) passes it, never a bot tool. The owner is always the session user.
	"""
	if not isinstance(content, str) or not content.strip():
		raise ValueError("content must be a non-empty string")
	doc = frappe.get_doc(
		{
			"doctype": MESSAGE_DOCTYPE,
			"ticket": ticket,
			"content": content,
			"run_id": run_id,
			"source_comment": source_comment,
		}
	)
	doc.insert(ignore_permissions=trusted)
	return doc.name


def _rows(ticket: str, limit: int) -> list:
	# The callers have checked read access on the ticket; the DocType itself is read-restricted.
	return frappe.get_all(
		MESSAGE_DOCTYPE,
		filters={"ticket": ticket},
		fields=["name", "owner", "creation", "content"],
		order_by="creation desc, name desc",
		limit_page_length=limit,
	)


def history(ticket: str, limit: int = MAX_COMMENTS) -> list[dict]:
	"""Newest first. The author is `owner` (set by the server); client-set fields are never read."""
	return [
		{"name": row.name, "author": row.owner, "creation": row.creation, "content": row.content}
		for row in _rows(ticket, limit)
	]


def typed_by_people(ticket: str, after=None, limit: int = MAX_COMMENTS) -> list[dict]:
	"""What people typed in the conversation after `after` (None: from the start), newest first, each with its
	`creation` and `content`. Not the bot's messages, and not the copy of an @ai comment: that comment is on the
	ticket and is read there."""
	filters = {"ticket": ticket, "owner": ("!=", AGENT_USER), "source_comment": ("is", "not set")}
	if after:
		filters["creation"] = (">", after)
	return frappe.get_all(
		MESSAGE_DOCTYPE,
		filters=filters,
		fields=["creation", "content"],
		order_by="creation desc, name desc",
		limit_page_length=limit,
	)


def forget_ticket(ticket: str) -> None:
	"""Delete the whole conversation of a ticket that was deleted: it goes with its ticket, as the comments do."""
	frappe.db.delete(MESSAGE_DOCTYPE, {"ticket": ticket})


def thread(ticket: str) -> list[dict]:
	"""The newest THREAD_LIMIT messages, oldest first, shaped for the panel."""
	return [
		{
			"name": row.name,
			"author": get_fullname(row.owner),
			"is_bot": row.owner == AGENT_USER,
			"created_at": format_datetime(row.creation),
			"text": row.content,
		}
		for row in reversed(_rows(ticket, THREAD_LIMIT))
	]
