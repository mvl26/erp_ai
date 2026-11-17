import frappe
from frappe.utils import format_datetime, get_fullname

from erp_ai.agent.prompts import MAX_COMMENTS
from erp_ai.constants import AGENT_USER, MESSAGE_DOCTYPE

THREAD_LIMIT = 200
# ADR-050: the kind of the bot's guidance message in the panel's thread (the script holds the same value); any other
# message has kind "".
KIND_GUIDANCE = "guidance"


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
	# imported on call: authority reads the conversation through this module's callers
	from erp_ai.agent import authority

	doc = frappe.get_doc(
		{
			"doctype": MESSAGE_DOCTYPE,
			"ticket": ticket,
			"content": content,
			"run_id": run_id,
			"source_comment": source_comment,
			# BUG-009: the role the author (the session user) holds as the message is sent
			"author_role": authority.role_label(frappe.session.user, ticket),
		}
	)
	doc.insert(ignore_permissions=trusted)
	return doc.name


def _rows(ticket: str, limit: int) -> list:
	# The callers have checked read access on the ticket; the DocType itself is read-restricted.
	return frappe.get_all(
		MESSAGE_DOCTYPE,
		filters={"ticket": ticket},
		fields=["name", "owner", "creation", "content", "author_role"],
		order_by="creation desc, name desc",
		limit_page_length=limit,
	)


def history(ticket: str, limit: int = MAX_COMMENTS) -> list[dict]:
	"""Newest first. The author is `owner` (set by the server); client-set fields are never read."""
	return [
		{
			"name": row.name,
			"author": row.owner,
			"creation": row.creation,
			"content": row.content,
			"role_at_send": row.author_role,
		}
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


def _shown(row) -> tuple[str, str]:
	"""(kind, text) of a message for the panel: the bot's guidance is plain text of kind KIND_GUIDANCE (ADR-050); any
	other message is shown as stored, kind ""."""
	# Imported on call: write_ticket imports add_message from this module.
	from erp_ai.agent.tools.write_ticket import guidance_text

	if row.owner == AGENT_USER and (text := guidance_text(row.content)) is not None:
		return KIND_GUIDANCE, text
	return "", row.content


def thread(ticket: str) -> list[dict]:
	"""The newest THREAD_LIMIT messages, oldest first, shaped for the panel."""
	shaped = []
	for row in reversed(_rows(ticket, THREAD_LIMIT)):
		kind, text = _shown(row)
		shaped.append(
			{
				"name": row.name,
				"author": get_fullname(row.owner),
				"is_bot": row.owner == AGENT_USER,
				"created_at": format_datetime(row.creation),
				"created": str(row.creation),
				"text": text,
				"kind": kind,
			}
		)
	return shaped
