import frappe
from frappe.utils import format_datetime, get_fullname

from erp_ai.agent.prompts import MAX_COMMENTS
from erp_ai.constants import AGENT_USER, MESSAGE_DOCTYPE, MESSAGE_KIND_CHAT, MESSAGE_KINDS

THREAD_LIMIT = 200


def add_message(
	ticket: str,
	content: str,
	kind: str,
	*,
	run_id: str | None = None,
	proposal: str | None = None,
	source_comment: str | None = None,
	trusted: bool = False,
) -> str:
	"""The one writer of ERP AI Message. Returns the row name; never commits.

	`trusted=True` inserts with `ignore_permissions=True`: only code that has already checked who may speak
	(the panel method, the @ai comment hook) passes it, never a bot tool. The owner is always the session user.
	"""
	if kind not in MESSAGE_KINDS:
		raise ValueError(f"kind must be one of {MESSAGE_KINDS}, got {kind!r}")
	if not isinstance(content, str) or not content.strip():
		raise ValueError("content must be a non-empty string")
	doc = frappe.get_doc(
		{
			"doctype": MESSAGE_DOCTYPE,
			"ticket": ticket,
			"kind": kind,
			"content": content,
			"run_id": run_id,
			"proposal": proposal,
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
		fields=["name", "owner", "creation", "content", "kind"],
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
			"kind": row.kind,
		}
		for row in _rows(ticket, limit)
	]


def thread(ticket: str) -> list[dict]:
	"""The newest THREAD_LIMIT messages, oldest first, shaped for the panel."""
	return [
		{
			"name": row.name,
			"author": get_fullname(row.owner),
			"is_bot": row.owner == AGENT_USER or row.kind != MESSAGE_KIND_CHAT,
			"kind": row.kind,
			"created_at": format_datetime(row.creation),
			"text": row.content,
		}
		for row in reversed(_rows(ticket, THREAD_LIMIT))
	]
