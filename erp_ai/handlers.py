import json

import frappe
from frappe.core.utils import html_to_plain_text

from erp_ai.agent import lessons, lifecycle, messages, policy
from erp_ai.agent.queue import enqueue_agent_run, enqueue_lifecycle_job, requester_reply_key
from erp_ai.agent.run_log import EVENT_CODES, record_event
from erp_ai.constants import (
	AGENT_USER,
	CATEGORIES,
	CLASSIFICATION_FIELDS,
	CLASSIFIED_BY_HUMAN,
	LOG_DOCTYPE,
	LOG_ENTRY_RUN_EVENT,
	LOGGER_NAME,
	SKIP_AGENT_DISABLED,
	SKIP_CREATED_BY_AGENT,
	SKIP_NOT_SENDABLE,
	SKIP_PREFILLED,
	TRIGGER_COMMENT_MENTION,
	TRIGGER_KB_DRAFT,
	TRIGGER_REQUESTER_REPLY,
	TRIGGER_TICKET_INSERT,
)
from erp_ai.install import ARTICLE_DOCTYPE, ARTICLE_SOURCE_FIELD, TASK_TICKET_FIELD

TICKET_DOCTYPE = "HD Ticket"
HUMAN_COMMENT_TYPE = "Comment"
COMMUNICATION_DOCTYPE = "Communication"
MESSAGE_COMMUNICATION_TYPE = "Communication"
RECEIVED = "Received"
TRIGGER_HUMAN_CORRECTION = "human_correction"
# Log label of the Task handler (not a run trigger: the lifecycle job calls no model).
TRIGGER_TASK_STATUS = "task_status"
CREATED_LABELS_FIELD = "ai_created_labels"
CREATED_LABELS_FLAG = "erp_ai_created_labels"


def _log_decision(ticket, trigger, outcome, reason):
	"""One line per decision; ids and reasons only, never ticket or comment content."""
	frappe.logger(LOGGER_NAME).info(f"erp_ai handler ticket={ticket} trigger={trigger} {outcome}: {reason}")


def _record_refusal(ticket, trigger, skip_reason):
	"""A refused call leaves one run_event row with its reason code, in the person's transaction (ADR-048 QĐ 2, 3).

	Only a call's refusal has an event code; a skip that refuses no call (the bot's own text, no keyword, no
	text, a missing ticket) leaves no row. `record_event` never commits and never raises.
	"""
	if skip_reason in EVENT_CODES:
		record_event(ticket=ticket, trigger=trigger, code=skip_reason)


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
		skip_reason = SKIP_AGENT_DISABLED
	elif doc.owner == AGENT_USER:
		skip_reason = SKIP_CREATED_BY_AGENT
	elif refusal := policy.send_refusal(doc):
		skip_reason = f"{SKIP_NOT_SENDABLE}:{refusal}"
	elif doc.flags.erp_ai_prefilled:
		skip_reason = SKIP_PREFILLED

	if skip_reason:
		_log_decision(doc.name, TRIGGER_TICKET_INSERT, "skipped", skip_reason)
		_record_refusal(doc.name, TRIGGER_TICKET_INSERT, skip_reason)
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
	# The flags carry the name of the classify log row to update and the fields this save changed; stale on a
	# re-used doc object.
	doc.flags.erp_ai_human_corrected = None
	doc.flags.erp_ai_corrected_fields = None
	# Runs for every ticket save: leave before any DB read unless a classification field changed.
	if doc.is_new():
		return
	changed = [field for field in CLASSIFICATION_FIELDS if doc.has_value_changed(field)]
	if not changed:
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
	# R9: a lesson only for what the person changed in this save, never for the fields they left as they were.
	doc.flags.erp_ai_corrected_fields = changed


def _record_human_correction(doc):
	log_name = doc.flags.erp_ai_human_corrected
	if doc.flags.in_insert or not log_name:
		return
	changed = doc.flags.erp_ai_corrected_fields or []
	doc.flags.erp_ai_human_corrected = None
	doc.flags.erp_ai_corrected_fields = None

	values = {
		"human_corrected_to": json.dumps({field: doc.get(field) for field in CLASSIFICATION_FIELDS}),
		"human_corrected_by": frappe.session.user,
	}
	if not frappe.db.get_value(LOG_DOCTYPE, log_name, "human_corrected_at"):
		values["human_corrected_at"] = frappe.utils.now_datetime()
	frappe.db.set_value(LOG_DOCTYPE, log_name, values, update_modified=False)
	_log_decision(doc.name, TRIGGER_HUMAN_CORRECTION, "recorded", "human_changed_classification")
	lessons.safely(lessons.record_correction, doc.name, log_name, changed)


def _kb_draft_skip(doc) -> str | None:
	"""Why a ticket entering the Resolved group must not queue the knowledge-draft run, or None; reads only."""
	if not policy.is_enabled():
		return "agent_disabled"
	if not lifecycle.kb_draft_enabled():
		return "kb_draft_off"
	# The lifecycle job's own close of a silent F ticket makes no article.
	if doc.flags.erp_ai_silent_close:
		return "silent_close"
	if refusal := policy.send_refusal(doc):
		return f"not_sendable:{refusal}"
	if frappe.db.exists(ARTICLE_DOCTYPE, {ARTICLE_SOURCE_FIELD: doc.name}):
		return "kb_exists"
	return None


def _maybe_enqueue_kb_draft(doc):
	"""AC-45: a ticket entering the Resolved group queues the knowledge-draft run (ADR-033 QĐ 2: read and queue)."""
	# Runs for every ticket save: leave before any DB read unless the status moved into the Resolved group.
	if (
		doc.flags.in_insert
		or not doc.has_value_changed("status")
		or doc.status_category != lifecycle.RESOLVED_CATEGORY
	):
		return

	skip_reason = _kb_draft_skip(doc)
	if skip_reason:
		_log_decision(doc.name, TRIGGER_KB_DRAFT, "skipped", skip_reason)
		return
	enqueue_agent_run(doc.name, TRIGGER_KB_DRAFT)
	_log_decision(doc.name, TRIGGER_KB_DRAFT, "enqueued", "conditions_met")


def ticket_on_update(doc, method=None):
	_record_human_correction(doc)
	_maybe_enqueue_kb_draft(doc)


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
	# The conversation with the bot goes with its ticket; the ERP AI Log rows stay (D7).
	messages.forget_ticket(doc.name)
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
	# D-6: what is no call is told first, so only a call the bot refuses leaves a row (ADR-048 QĐ 2).
	skip_reason = None
	if doc.owner == AGENT_USER:
		skip_reason = "written_by_agent"
	elif not policy.contains_keyword(doc.content):
		skip_reason = "no_keyword"
	elif not (text := html_to_plain_text(doc.content)).strip():
		# the keyword sat only inside markup: nothing was said, and the comment itself must still be saved
		skip_reason = "no_text"
	elif not policy.is_enabled():
		skip_reason = SKIP_AGENT_DISABLED
	elif refusal := policy.send_refusal(ticket):
		skip_reason = f"{SKIP_NOT_SENDABLE}:{refusal}"

	if skip_reason:
		_log_decision(ticket, TRIGGER_COMMENT_MENTION, "skipped", skip_reason)
		_record_refusal(ticket, TRIGGER_COMMENT_MENTION, skip_reason)
		return
	# The copy is the one trigger: its after_insert (message_after_insert) queues the run.
	messages.add_message(ticket, text, source_comment=doc.name, trusted=True)
	_log_decision(ticket, TRIGGER_COMMENT_MENTION, "copied", "conditions_met")


def message_after_insert(doc, method=None):
	# Only a person's message starts a run; the bot's own reply is told by its owner, before any DB read.
	ticket = doc.ticket
	if doc.owner != AGENT_USER and (rule := lessons.teaching_rule(doc.content)):
		lessons.safely(lessons.record_teaching_message, ticket, doc.name, rule)
	skip_reason = None
	if doc.owner == AGENT_USER:
		skip_reason = "written_by_agent"
	elif not policy.is_enabled():
		skip_reason = SKIP_AGENT_DISABLED
	elif refusal := policy.send_refusal(ticket):
		skip_reason = f"{SKIP_NOT_SENDABLE}:{refusal}"

	if skip_reason:
		_log_decision(ticket, TRIGGER_COMMENT_MENTION, "skipped", skip_reason)
		_record_refusal(ticket, TRIGGER_COMMENT_MENTION, skip_reason)
		return
	enqueue_agent_run(ticket, TRIGGER_COMMENT_MENTION, message_name=doc.name)
	_log_decision(ticket, TRIGGER_COMMENT_MENTION, "enqueued", "conditions_met")


def _requester_reply_skip(doc, ticket) -> str | None:
	"""Why a received message must not queue a requester-reply run, or None; reads only (ADR-033 QĐ 2)."""
	if not policy.is_enabled():
		return "agent_disabled"
	if doc.owner == AGENT_USER:
		return "written_by_agent"
	if not lifecycle.is_requester_sender(
		doc.sender, frappe.db.get_value(TICKET_DOCTYPE, ticket, "raised_by")
	):
		return "not_requester"
	# B-1: the message that opened the ticket (portal or email) has no message of the bot before it.
	if not frappe.db.exists(
		COMMUNICATION_DOCTYPE, {**lifecycle._bot_messages(ticket), "creation": ("<", doc.creation)}
	):
		return "no_bot_message_before"
	# B-2: the run of this message already wrote its rows under the event key; the call_received row the queue
	# wrote under it is not the run's (ADR-033 QĐ 6, ADR-048 QĐ 4).
	if frappe.db.exists(
		LOG_DOCTYPE,
		{"run_id": requester_reply_key(ticket, doc.name), "entry_type": ("!=", LOG_ENTRY_RUN_EVENT)},
	):
		return "already_handled"
	if refusal := policy.send_refusal(ticket):
		return f"not_sendable:{refusal}"
	return None


def communication_on_update(doc, method=None):
	"""AC-41: the requester's reply after the bot's message queues one run of its own (one job per message, X-1)."""
	# Fires for every Communication on the site; return before any DB read.
	if (
		doc.reference_doctype != TICKET_DOCTYPE
		or not doc.reference_name
		or doc.sent_or_received != RECEIVED
		or doc.communication_type != MESSAGE_COMMUNICATION_TYPE
	):
		return

	# B-3: read at on_update, after Helpdesk moved a reply to a merged ticket onto its merge target.
	ticket = doc.reference_name
	skip_reason = _requester_reply_skip(doc, ticket)
	if skip_reason:
		_log_decision(ticket, TRIGGER_REQUESTER_REPLY, "skipped", skip_reason)
		return
	enqueue_agent_run(ticket, TRIGGER_REQUESTER_REPLY, communication_name=doc.name)
	_log_decision(ticket, TRIGGER_REQUESTER_REPLY, "enqueued", "conditions_met")


def task_on_update(doc, method=None):
	"""AC-43 (A-11): a status change of a Task linked to a ticket queues that ticket's lifecycle job."""
	# Fires for every Task save; return before any DB read.
	ticket = doc.get(TASK_TICKET_FIELD)
	if not ticket or not doc.has_value_changed("status"):
		return

	if not policy.is_enabled():
		_log_decision(ticket, TRIGGER_TASK_STATUS, "skipped", "agent_disabled")
		return
	enqueue_lifecycle_job(ticket)
	_log_decision(ticket, TRIGGER_TASK_STATUS, "enqueued", "conditions_met")


def todo_after_insert(doc, method=None):
	"""AC-6: a person assigns a ticket the bot had already assigned to someone else, so that is a lesson; giving
	it back to the bot's pick retires that lesson (I5)."""
	# Fires for every ToDo on the site; return before any DB read.
	ticket, new_user = doc.reference_name, doc.allocated_to
	if doc.reference_type != policy.TICKET_DOCTYPE or not ticket or not new_user:
		return
	# I2: an Assignment Rule (round robin of the team) made this ToDo inside the person's request, not their choice.
	if doc.assignment_rule:
		return
	if frappe.session.user == AGENT_USER:
		return
	bot_user = frappe.db.get_value(
		"ToDo",
		{
			"reference_type": policy.TICKET_DOCTYPE,
			"reference_name": ticket,
			"assigned_by": AGENT_USER,
			"name": ("!=", doc.name),
		},
		"allocated_to",
		order_by="creation desc",
	)
	if not bot_user:
		return
	lessons.safely(lessons.record_assignee_change, ticket, bot_user, new_user)
