import json
from functools import partial
from urllib.parse import quote

import frappe
from frappe.utils import format_datetime, get_fullname

from erp_ai.agent import lifecycle
from erp_ai.agent.prompts import APPROVE_GUIDANCE_OFFER, MAX_COMMENTS, RESULT_REJECTED_TEXT
from erp_ai.agent.run_status import announce_message
from erp_ai.constants import AGENT_USER, LOG_DOCTYPE, MESSAGE_DOCTYPE

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
	# CHG-018: whoever has the ticket open is told once the row is committed, or its reload would not see it.
	frappe.db.after_commit.add(partial(announce_message, ticket))
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


def add_result_line(ticket: str, text: str) -> str:
	"""CHG-017: the fixed line of a person's verdict on the bot's result (the panel method has checked who may)."""
	return add_message(ticket, text, trusted=True)


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


def _has_done_and_nothing_pending(text: str) -> bool:
	"""The guidance holds a real 'Đã làm' list, no 'Chờ duyệt' list and no approve offer (CHG-017)."""
	# Imported on call: write_ticket imports add_message from this module.
	from erp_ai.agent.tools.write_ticket import guidance_work_done

	return guidance_work_done(text) and APPROVE_GUIDANCE_OFFER not in text


def result_confirmable(ticket: str, shaped: list[dict]) -> int:
	"""CHG-017: the index in `shaped` of the guidance that gets the Duyệt / Không duyệt buttons, or -1.

	The newest guidance whose work is done, while the ticket may still be resolved by a person and the bot has the
	last word: not while the bot is yet to answer, nor after a Không duyệt that no person has answered.
	"""
	guidance = [i for i, m in enumerate(shaped) if m["kind"] == KIND_GUIDANCE]
	if not guidance or not _has_done_and_nothing_pending(shaped[guidance[-1]]["text"]):
		return -1
	tail = shaped[guidance[-1] + 1 :]
	if tail and not tail[-1]["is_bot"]:
		return -1
	rejected = [
		i for i, m in enumerate(tail) if not m["is_bot"] and m["text"].strip() == RESULT_REJECTED_TEXT
	]
	if rejected and all(m["is_bot"] for m in tail[rejected[-1] + 1 :]):
		return -1
	return -1 if lifecycle.result_refusal(ticket) else guidance[-1]


# CHG-017: the tools whose successful call leaves a record the person can open (runner.WRITE_TOOL_TARGETS).
LINKED_WRITE_TOOLS = (
	"api_create_record",
	"api_update_record",
	"api_submit_record",
	"create_task",
	"create_kb_draft",
)
RESULT_LINKS_MAX = 10
# The ticket itself and the conversation are where the person already is.
LINK_SKIP_DOCTYPES = ("HD Ticket", MESSAGE_DOCTYPE, "Comment", "Communication")


def result_links(ticket: str) -> list[dict]:
	"""CHG-017: the records the bot created or changed on this ticket, oldest first, each `{label, url}` of the
	desk form; only those the caller may read and that still exist, at most RESULT_LINKS_MAX."""
	rows = frappe.get_all(
		LOG_DOCTYPE,
		filters={"ticket": ticket, "actions": ("like", '%"ok": true%')},
		fields=["actions"],
		order_by="creation asc, name asc",
	)
	found = {}
	for row in rows:
		try:
			entries = json.loads(row.actions or "[]")
		except ValueError:
			continue
		for entry in entries if isinstance(entries, list) else []:
			doctype, name = entry.get("doctype"), entry.get("name")
			if entry.get("tool") in LINKED_WRITE_TOOLS and entry.get("ok") and doctype and name:
				found[(doctype, str(name))] = None
	links = []
	for doctype, name in found:
		if (
			doctype in LINK_SKIP_DOCTYPES
			or not frappe.db.exists(doctype, name)
			or not frappe.has_permission(doctype, "read", doc=name)
		):
			continue
		slug = frappe.scrub(doctype).replace("_", "-")
		links.append({"label": f"{doctype} {name}", "url": f"/app/{slug}/{quote(name)}"})
	return links[:RESULT_LINKS_MAX]


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
				# CHG-010: only a plan with steps left for the bot can be approved.
				"approvable": kind == KIND_GUIDANCE and APPROVE_GUIDANCE_OFFER in text,
				"result_confirmable": False,
				"result_links": [],
			}
		)
	if (index := result_confirmable(ticket, shaped)) >= 0:
		shaped[index]["result_confirmable"] = True
		shaped[index]["result_links"] = result_links(ticket)
	return shaped
