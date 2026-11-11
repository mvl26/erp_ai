import frappe

from erp_ai.agent import policy
from erp_ai.agent.queue import enqueue_agent_run
from erp_ai.constants import (
	AGENT_USER,
	CLASSIFICATION_FIELDS,
	LOGGER_NAME,
	TRIGGER_COMMENT_MENTION,
	TRIGGER_TICKET_INSERT,
)

TICKET_DOCTYPE = "HD Ticket"
HUMAN_COMMENT_TYPE = "Comment"


def _log_decision(ticket, trigger, outcome, reason):
	"""One line per decision; ids and reasons only, never ticket or comment content."""
	frappe.logger(LOGGER_NAME).info(f"erp_ai handler ticket={ticket} trigger={trigger} {outcome}: {reason}")


def ticket_before_insert(doc, method=None):
	# Runs before Helpdesk fills defaults, so it sees only what the person typed.
	doc.flags.erp_ai_prefilled = all(doc.get(field) for field in CLASSIFICATION_FIELDS)


def ticket_after_insert(doc, method=None):
	skip_reason = None
	if not policy.is_enabled():
		skip_reason = "agent_disabled"
	elif doc.owner == AGENT_USER:
		skip_reason = "created_by_agent"
	elif not policy.can_send_ticket(doc):
		skip_reason = "not_sendable"
	elif doc.flags.erp_ai_prefilled:
		skip_reason = "prefilled"

	if skip_reason:
		_log_decision(doc.name, TRIGGER_TICKET_INSERT, "skipped", skip_reason)
		return
	enqueue_agent_run(doc.name, TRIGGER_TICKET_INSERT)
	_log_decision(doc.name, TRIGGER_TICKET_INSERT, "enqueued", "conditions_met")


def comment_after_insert(doc, method=None):
	# Step 0: this hook fires for every Comment on the site; return before any DB read.
	if doc.reference_doctype != TICKET_DOCTYPE or doc.comment_type != HUMAN_COMMENT_TYPE:
		return

	ticket = doc.reference_name
	skip_reason = None
	if not policy.is_enabled():
		skip_reason = "agent_disabled"
	elif doc.owner == AGENT_USER:
		skip_reason = "written_by_agent"
	elif not policy.contains_keyword(doc.content):
		skip_reason = "no_keyword"
	elif not policy.can_send_ticket(ticket):
		skip_reason = "not_sendable"

	if skip_reason:
		_log_decision(ticket, TRIGGER_COMMENT_MENTION, "skipped", skip_reason)
		return
	enqueue_agent_run(ticket, TRIGGER_COMMENT_MENTION)
	_log_decision(ticket, TRIGGER_COMMENT_MENTION, "enqueued", "conditions_met")
