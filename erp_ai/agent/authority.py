import json

import frappe

from erp_ai.agent.prompts import MAX_COMMENTS
from erp_ai.constants import (
	AGENT_USER,
	MESSAGE_DOCTYPE,
	ROLE_INSTRUCTOR,
	TITLE_WRONG_USER,
	TRIGGER_COMMENT_MENTION,
)

ROLE_LABEL_INSTRUCTION = "chỉ thị"
ROLE_LABEL_DATA = "dữ liệu"

# D-16: these accounts never carry authority (Administrator holds every role).
NEVER_AUTHORITY = frozenset({"Administrator", "Guest", AGENT_USER})

MIN_COMMENT_LIMIT = 1
MAX_COMMENT_LIMIT = 50


def enter_agent_session() -> bool:
	"""ADR-033 QĐ 1: the only place a job switches its session to the agent account.

	The previous user is not restored (the caller is a job). False (logged) means the caller must stop.
	"""
	if not frappe.db.get_value("User", AGENT_USER, "enabled"):
		frappe.log_error(TITLE_WRONG_USER, "Không có tài khoản agent")
		return False
	frappe.set_user(AGENT_USER)
	if frappe.session.user != AGENT_USER:
		frappe.log_error(TITLE_WRONG_USER, f"Sai tài khoản: {frappe.session.user}")
		return False
	return True


def ticket_comment_filters(ticket_name: str) -> dict:
	"""The one filter for a ticket's human comments (core `Comment`, design 2.7)."""
	return {
		"reference_doctype": "HD Ticket",
		"reference_name": ticket_name,
		"comment_type": "Comment",
	}


def fetch_ticket_comments(ticket_name: str, limit: int = MAX_COMMENTS) -> list[dict]:
	"""Newest first. The author is `owner` (set by the server); client-set fields are never read."""
	if not MIN_COMMENT_LIMIT <= limit <= MAX_COMMENT_LIMIT:
		raise ValueError(f"limit must be between {MIN_COMMENT_LIMIT} and {MAX_COMMENT_LIMIT}")
	rows = frappe.get_list(
		"Comment",
		filters=ticket_comment_filters(ticket_name),
		fields=["name", "owner", "creation", "content"],
		order_by="creation desc",
		limit_page_length=limit,
	)
	return [
		{"name": row.name, "author": row.owner, "creation": row.creation, "content": row.content}
		for row in rows
	]


def is_instruction(author: str, ticket_name: str) -> bool:
	if not author or author in NEVER_AUTHORITY:
		return False
	if ROLE_INSTRUCTOR in frappe.get_roles(author):
		return True
	return _assigned_by_other(author, ticket_name)


def _assigned_by_other(author: str, ticket_name: str) -> bool:
	assign = frappe.db.get_value("HD Ticket", ticket_name, "_assign")
	if author not in json.loads(assign or "[]"):
		return False
	todo = frappe.db.get_value(
		"ToDo",
		{
			"reference_type": "HD Ticket",
			"reference_name": ticket_name,
			"allocated_to": author,
		},
		["status", "assigned_by"],
		order_by="creation desc",
		as_dict=True,
	)
	if not todo or todo.status != "Open":
		return False
	# ADR-030 QĐ 6: an assignment made by the bot itself never creates authority.
	return bool(todo.assigned_by) and todo.assigned_by not in (author, AGENT_USER)


def run_instructor(ticket_name: str, trigger: str, message_name: str | None = None) -> str | None:
	"""ADR-030 QĐ 6: the instructor comes only from the event that queued the run (fail-closed, never raises).

	A comment run reads the author (`owner`, set by the server) of exactly that message of the conversation; no
	other message is scanned. Any other trigger falls back to the ticket owner.
	"""
	if trigger == TRIGGER_COMMENT_MENTION:
		author = _trigger_message_author(ticket_name, message_name)
	else:
		author = frappe.db.get_value("HD Ticket", ticket_name, "owner")
	return author if is_instruction(author, ticket_name) else None


def _trigger_message_author(ticket_name: str, message_name: str | None) -> str | None:
	if not message_name:
		return None
	message = frappe.db.get_value(
		MESSAGE_DOCTYPE,
		{"name": message_name, "ticket": ticket_name},
		["owner", "source_comment"],
		as_dict=True,
	)
	if not message:
		return None
	# The copy of an @ai comment speaks for whoever wrote that comment, read now: Helpdesk's ticket merge re-inserts
	# old comments in the merger's session and restores their owner afterwards, so a copy can be owned by someone
	# who did not write it. Then, or when the comment is gone, the run has no instructor.
	if message.source_comment and (
		frappe.db.get_value("Comment", message.source_comment, "owner") != message.owner
	):
		return None
	return message.owner


def label_comments(ticket_name: str, comments: list[dict]) -> list[dict]:
	verdicts: dict[str, bool] = {}
	labelled = []
	for comment in comments:
		author = comment["author"]
		if author not in verdicts:
			verdicts[author] = is_instruction(author, ticket_name)
		role = ROLE_LABEL_INSTRUCTION if verdicts[author] else ROLE_LABEL_DATA
		labelled.append({**comment, "role": role})
	return labelled
