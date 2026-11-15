import json

import frappe

from erp_ai.agent import policy
from erp_ai.agent.queue import enqueue_agent_run
from erp_ai.constants import (
	AGENT_USER,
	CLASSIFICATION_FIELDS,
	CLASSIFIED_BY_HUMAN,
	LOG_DOCTYPE,
	LOGGER_NAME,
	TRIGGER_COMMENT_MENTION,
	TRIGGER_TICKET_INSERT,
)

TICKET_DOCTYPE = "HD Ticket"
HUMAN_COMMENT_TYPE = "Comment"
TRIGGER_HUMAN_CORRECTION = "human_correction"


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


def _latest_classify_log(ticket):
	"""The newest `classify` log row of the ticket (name, predicted_category, human_corrected_at), or None."""
	rows = frappe.get_all(
		LOG_DOCTYPE,
		filters={"ticket": ticket, "entry_type": "classify"},
		fields=["name", "predicted_category", "human_corrected_at"],
		order_by="creation desc",
		limit=1,
	)
	return rows[0] if rows else None


def ticket_validate(doc, method=None):
	# The flag carries the name of the classify log row to update; stale on a re-used doc object.
	doc.flags.erp_ai_human_corrected = None
	# Runs for every ticket save: leave before any DB read unless a classification field changed.
	if doc.is_new() or not any(doc.has_value_changed(field) for field in CLASSIFICATION_FIELDS):
		return

	skip_reason = None
	if frappe.session.user == AGENT_USER:
		skip_reason = "changed_by_agent"
	else:
		latest = _latest_classify_log(doc.name)
		if not latest or not latest.predicted_category:
			skip_reason = "no_prediction"

	if skip_reason:
		_log_decision(doc.name, TRIGGER_HUMAN_CORRECTION, "skipped", skip_reason)
		return
	doc.ai_classified_by = CLASSIFIED_BY_HUMAN
	doc.flags.erp_ai_human_corrected = latest.name


def ticket_on_update(doc, method=None):
	log_name = doc.flags.erp_ai_human_corrected
	if doc.flags.in_insert or not log_name:
		return
	doc.flags.erp_ai_human_corrected = None

	values = {
		"human_corrected_to": json.dumps({field: doc.get(field) for field in CLASSIFICATION_FIELDS}),
		"human_corrected_by": frappe.session.user,
	}
	if not frappe.db.get_value(LOG_DOCTYPE, log_name, "human_corrected_at"):
		values["human_corrected_at"] = frappe.utils.now_datetime()
	frappe.db.set_value(LOG_DOCTYPE, log_name, values, update_modified=False)
	_log_decision(doc.name, TRIGGER_HUMAN_CORRECTION, "recorded", "human_changed_classification")


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
	enqueue_agent_run(ticket, TRIGGER_COMMENT_MENTION, comment_name=doc.name)
	_log_decision(ticket, TRIGGER_COMMENT_MENTION, "enqueued", "conditions_met")
