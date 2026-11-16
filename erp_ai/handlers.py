import json

import frappe

from erp_ai.agent import policy
from erp_ai.agent.queue import enqueue_agent_run
from erp_ai.constants import (
	AGENT_USER,
	CATEGORIES,
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
CREATED_LABELS_FIELD = "ai_created_labels"
CREATED_LABELS_FLAG = "erp_ai_created_labels"


def _log_decision(ticket, trigger, outcome, reason):
	"""One line per decision; ids and reasons only, never ticket or comment content."""
	frappe.logger(LOGGER_NAME).info(f"erp_ai handler ticket={ticket} trigger={trigger} {outcome}: {reason}")


def ticket_before_insert(doc, method=None):
	# Runs before Helpdesk fills defaults, so it sees only what the person typed.
	doc.flags.erp_ai_prefilled = all(doc.get(field) for field in CLASSIFICATION_FIELDS)
	# Kept in a flag, not the field: Frappe resets permlevel 8 fields of a creator without that level.
	doc.flags[CREATED_LABELS_FLAG] = {
		field: doc.get(field) for field in CLASSIFICATION_FIELDS if doc.get(field)
	}


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


def reference_classify_row(ticket_name: str) -> str | None:
	"""The ticket's reference `classify` row (ADR-037 QĐ 5): its first row with a result, a category A-F, oldest by
	creation then name as the ERP AI Accuracy report reads it; None when it has none. A person's correction goes here.
	"""
	rows = frappe.get_all(
		LOG_DOCTYPE,
		filters={"ticket": ticket_name, "entry_type": "classify", "predicted_category": ("in", CATEGORIES)},
		pluck="name",
		order_by="creation asc, name asc",
		limit=1,
	)
	return rows[0] if rows else None


def _record_created_labels(doc):
	"""Server-computed at creation, overwriting any client value; only typed values the ticket still holds."""
	typed = doc.flags.get(CREATED_LABELS_FLAG) or {}
	kept = {field: value for field, value in typed.items() if doc.get(field) == value}
	doc.set(CREATED_LABELS_FIELD, json.dumps(kept, ensure_ascii=False, sort_keys=True) if kept else "")


def _freeze_created_labels(doc):
	"""No later save may change the record, in any session."""
	before = doc.get_doc_before_save()
	if before and doc.has_value_changed(CREATED_LABELS_FIELD):
		doc.set(CREATED_LABELS_FIELD, before.get(CREATED_LABELS_FIELD))


def ticket_validate(doc, method=None):
	# Before any early return; the field is absent until migrate has installed it.
	if doc.meta.has_field(CREATED_LABELS_FIELD):
		if doc.is_new():
			_record_created_labels(doc)
		else:
			_freeze_created_labels(doc)
	# The flag carries the name of the classify log row to update; stale on a re-used doc object.
	doc.flags.erp_ai_human_corrected = None
	# Runs for every ticket save: leave before any DB read unless a classification field changed.
	if doc.is_new() or not any(doc.has_value_changed(field) for field in CLASSIFICATION_FIELDS):
		return

	# The session alone tells the bot's write from a person's (AC-21).
	if frappe.session.user == AGENT_USER:
		_log_decision(doc.name, TRIGGER_HUMAN_CORRECTION, "skipped", "changed_by_agent")
		return
	doc.ai_classified_by = CLASSIFIED_BY_HUMAN
	reference = reference_classify_row(doc.name)
	if not reference:
		# No prediction row to correct yet: the person is still the one who classified the ticket.
		_log_decision(doc.name, TRIGGER_HUMAN_CORRECTION, "recorded", "human_changed_before_prediction")
		return
	doc.flags.erp_ai_human_corrected = reference


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


def ticket_series_name() -> str | None:
	"""The `tabSeries` row HD Ticket numbers come from: the text before `.####` of its autoname ("" for ".####").

	None when the autoname is not a plain "<prefix>.####" (date parts, naming series): no counter to keep.
	"""
	prefix, dot, hashes = (frappe.get_meta(TICKET_DOCTYPE).autoname or "").rpartition(".")
	if not dot or not hashes or hashes.strip("#") or "." in prefix:
		return None
	return prefix


def ticket_number(name: str) -> int | None:
	"""The counter value a ticket name was made from, or None for a name the counter did not make."""
	prefix = ticket_series_name()
	if prefix is None or not name or not name.startswith(prefix):
		return None
	digits = name[len(prefix) :]
	return int(digits) if digits.isdigit() else None


def raise_ticket_series(number: int) -> None:
	"""Move the HD Ticket counter up to `number` when it is lower; never move it down."""
	series = ticket_series_name()
	if series is None:
		return
	rows = frappe.db.sql("select current from `tabSeries` where name = %s for update", (series,))
	if not rows:
		frappe.db.sql("insert into `tabSeries` (name, current) values (%s, %s)", (series, number))
	elif (rows[0][0] or 0) < number:
		frappe.db.sql("update `tabSeries` set current = %s where name = %s", (number, series))


def ticket_after_delete(doc, method=None):
	# Frappe's delete_doc moves the counter back when the newest ticket goes (revert_series_if_last).
	# The ERP AI Log rows of a deleted ticket stay (D7), so a reused name would inherit them: put it back.
	number = ticket_number(doc.name)
	if number is not None:
		raise_ticket_series(number)


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
