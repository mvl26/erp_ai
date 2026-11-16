"""Deadline reminders for D/E tickets and milestone reminders for C/D tickets (design-addendum-2-U5b 3.2, AC-57, AC-58).

The cycle key of a reminder is an ok entry of its tool in the ticket's `bot_action` rows (ADR-033 QĐ 6): a
deadline reminder is keyed by (ticket, kind, deadline), so a moved deadline is a new cycle (A-U5b-2); a milestone
reminder by (ticket, kind), once in the ticket's life. Nothing here calls the model.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta

import frappe
from frappe.utils import escape_html, get_datetime, get_fullname, now_datetime
from frappe.utils.file_lock import LockTimeoutError
from frappe.utils.synchronization import filelock

from erp_ai.agent import authority, ops_data, policy, run_log
from erp_ai.agent.classification import load_mapping
from erp_ai.constants import AGENT_USER, LEVELS, LOG_DOCTYPE, LOGGER_NAME, SETTING_DOCTYPE

DUE_REMINDER_TOOL = "due_reminder"
MILESTONE_REMINDER_TOOL = "milestone_reminder"
KIND_DUE_SOON, KIND_OVERDUE = "due_soon", "overdue"
KIND_BA_NOTE_MISSING, KIND_TASK_MISSING = "ba_note_missing", "task_missing"
CANDIDATE_LIMIT = 200  # per kind of candidate and run; the rest waits for the next run
LOCK_NAME = "erp_ai_due_checks"
DUE_SOON_TEXT = "Nhắc hạn: phiếu còn dưới {hours} giờ tới hạn {deadline}. Người phụ trách: {people}."
OVERDUE_TEXT = "Nhắc hạn: phiếu đã quá hạn {deadline}. Người phụ trách: {people}."
BA_NOTE_TEXT = "Nhắc mốc: phiếu đầu mục C đã quá {hours} giờ mà chưa có BA note. Người phụ trách: {people}."
TASK_TEXT = "Nhắc mốc: phiếu đã quá {days} ngày mà chưa có Task liên kết. Người phụ trách: {people}."
NO_ASSIGNEE_TEXT = "chưa có người phụ trách"
# excluded-team tickets: the ticket number and the deadline only (A-12)
CODE_SUBJECT = {
	KIND_DUE_SOON: "Phiếu #{name}: còn dưới {hours} giờ tới hạn {deadline}",
	KIND_OVERDUE: "Phiếu #{name}: đã quá hạn {deadline}",
	KIND_TASK_MISSING: "Phiếu #{name}: quá {days} ngày chưa có Task liên kết",
}
REMINDER_TOOLS = (DUE_REMINDER_TOOL, MILESTONE_REMINDER_TOOL)

TICKET = ops_data.TICKET
COMMENT_DOCTYPE = "Comment"  # the record HD Ticket.new_comment makes (Document.add_comment), U5b.md:356
NOTIFICATION_DOCTYPE = "Notification Log"
LOCK_TIMEOUT_S = 5
DUE_CATEGORIES = ("D", "E")
DUE_KINDS = (KIND_DUE_SOON, KIND_OVERDUE)
TEXT_BY_KIND = {
	KIND_DUE_SOON: DUE_SOON_TEXT,
	KIND_OVERDUE: OVERDUE_TEXT,
	KIND_BA_NOTE_MISSING: BA_NOTE_TEXT,
	KIND_TASK_MISSING: TASK_TEXT,
}
TOOL_BY_KIND = {
	KIND_DUE_SOON: DUE_REMINDER_TOOL,
	KIND_OVERDUE: DUE_REMINDER_TOOL,
	KIND_BA_NOTE_MISSING: MILESTONE_REMINDER_TOOL,
	KIND_TASK_MISSING: MILESTONE_REMINDER_TOOL,
}
# Structural columns only: never the subject, the description or a comment of a ticket (A-12, NFR-1).
CANDIDATE_FIELDS = ("name", "creation", "ticket_type", "resolution_by")
DEADLINE_FORMAT = "%d/%m/%Y %H:%M"
DEADLINE_KEY_FORMAT = "%Y-%m-%d %H:%M:%S"
# The mention tag of the Helpdesk editor; Frappe notifies every `data-id` of a `mention` span in a comment.
MENTION = '<span class="mention" data-type="mention" data-id="{user}" data-label="{label}">@{label}</span>'
ERRORS, NO_ASSIGNEE = "errors", "no_assignee"
SUMMARY_COUNTS = (KIND_DUE_SOON, KIND_OVERDUE, KIND_BA_NOTE_MISSING, KIND_TASK_MISSING, ERRORS, NO_ASSIGNEE)
SUMMARY = "due_checks: due_soon=%d overdue=%d ba_note=%d task=%d errors=%d no_assignee=%d capped=%s"


def due_kind(deadline: datetime | None, now: datetime, hours: int) -> str | None:
	"""`overdue` at or past the deadline, `due_soon` when it is at most `hours` away (exactly `hours` counts)."""
	if deadline is None:
		return None
	if deadline <= now:
		return KIND_OVERDUE
	if deadline <= now + timedelta(hours=hours):
		return KIND_DUE_SOON
	return None


def milestone_due(created: datetime, now: datetime, hours: float) -> bool:
	"""The milestone `hours` after `created` is reached (exactly `hours` counts)."""
	return now - created >= timedelta(hours=hours)


def sent_keys(names: list[str]) -> set[tuple[str, str, str]]:
	"""The (ticket, kind, deadline_iso) keys already sent for `names`, from the ok reminder entries of their
	scheduled `bot_action` rows; a milestone key has deadline_iso "". A row whose `actions` cannot be read is
	skipped with one warning."""
	if not names:
		return set()
	rows = frappe.get_all(
		LOG_DOCTYPE,
		filters={
			"entry_type": run_log.ENTRY_TYPE_BOT_ACTION,
			"trigger": run_log.TRIGGER_SCHEDULED_JOB,
			"ticket": ["in", names],
		},
		fields=["ticket", "actions"],
	)
	keys = set()
	for row in rows:
		try:
			actions = json.loads(row.actions or "[]")
		except ValueError:
			actions = None
		if not isinstance(actions, list):
			frappe.logger(LOGGER_NAME).warning(
				"due_checks: unreadable actions on a log row of ticket %s, row skipped", row.ticket
			)
			continue
		for entry in actions:
			key = _entry_key(row.ticket, entry)
			if key:
				keys.add(key)
	return keys


def _entry_key(ticket: str, entry) -> tuple[str, str, str] | None:
	"""The cycle key an action entry holds, or None when it is not an ok reminder entry."""
	if not isinstance(entry, dict) or entry.get("ok") is not True or entry.get("tool") not in REMINDER_TOOLS:
		return None
	after = entry.get("value_after")
	if not isinstance(after, dict) or not after.get("kind"):
		return None
	deadline = (after.get("deadline") or "") if entry["tool"] == DUE_REMINDER_TOOL else ""
	return (ticket, after["kind"], deadline)


@dataclass(frozen=True)
class _Reminder:
	"""One (ticket, kind) to remind; `deadline` is the deadline a due reminder is keyed by, None for a milestone."""

	ticket: str
	created: datetime
	kind: str
	deadline: datetime | None = None

	@property
	def key(self) -> tuple[str, str, str]:
		return (self.ticket, self.kind, _deadline_key(self.deadline))


def run_due_checks(now: datetime | None = None) -> None:
	"""The reminder job (design-addendum-2-U5b 4.1, AC-57, AC-58): under the agent account, one reminder for each
	(ticket, kind) whose cycle key is not sent yet, oldest ticket first, then one logger line.

	A busy lock, the agent off and the effective level L0 (after the budget cap, AC-23) send nothing and log one line.
	"""
	logger = frappe.logger(LOGGER_NAME)
	try:
		with filelock(LOCK_NAME, timeout=LOCK_TIMEOUT_S):
			_run_locked(get_datetime(now) if now else now_datetime(), logger)
	except LockTimeoutError:
		logger.info("due_checks: lock busy")


def _run_locked(now: datetime, logger) -> None:
	settings = frappe.get_single(SETTING_DOCTYPE)
	if not policy.is_enabled():
		logger.info("due_checks: agent off, nothing sent")
		return
	if policy.effective_level(settings, over_budget=policy.is_over_budget(settings, now)) == LEVELS[0]:
		logger.info("due_checks: level L0, nothing sent")
		return
	if not authority.enter_agent_session():
		return
	reverse_map = ops_data.category_by_ticket_type(load_mapping(settings.category_mapping))
	due_field = ops_data.due_field(settings.field_due_date)
	if not settings.field_due_date:
		logger.info("due_checks: no due field configured, the deadline is resolution_by")
	due_rows, capped = _candidates(DUE_CATEGORIES, reverse_map, due_field)
	sent = sent_keys([row.name for row in due_rows])
	reminders = [
		reminder
		for reminder in _due_reminders(due_rows, due_field, now, settings.due_reminder_hours)
		if reminder.key not in sent
	]
	people = _people_in_charge(sorted({reminder.ticket for reminder in reminders}))
	counts = dict.fromkeys(SUMMARY_COUNTS, 0)
	for reminder in sorted(reminders, key=lambda reminder: (reminder.created, reminder.ticket)):
		if counted := _remind(reminder, people.get(reminder.ticket, []), settings):
			counts[counted] += 1
	logger.info(SUMMARY, *(counts[name] for name in SUMMARY_COUNTS), capped)


def _candidates(
	categories: tuple[str, ...], reverse_map: dict[str, str], due_field: str | None = None
) -> tuple[list, bool]:
	"""Open tickets of `categories`, oldest first, at most CANDIDATE_LIMIT, each with its `category`; and whether
	the limit was reached (the rest waits for the next run)."""
	ticket_types = [ticket_type for ticket_type, category in reverse_map.items() if category in categories]
	if not ticket_types:
		return [], False
	rows = frappe.get_all(
		TICKET,
		filters=[["status_category", "!=", "Resolved"], ["ticket_type", "in", ticket_types]],
		fields=[*CANDIDATE_FIELDS, *([due_field] if due_field else [])],
		order_by="creation asc, name asc",
		limit=CANDIDATE_LIMIT,
	)
	for row in rows:
		row.category = ops_data.ticket_category(row, reverse_map)
	return rows, len(rows) == CANDIDATE_LIMIT


def _due_reminders(rows: list, due_field: str | None, now: datetime, hours: int) -> list[_Reminder]:
	"""The due reminder each row needs by its processing deadline (D-18); a row first seen past it is overdue only."""
	reminders = []
	for row in rows:
		deadline = ops_data.ticket_deadline(
			row.category, row.resolution_by, row.get(due_field) if due_field else None
		)
		if kind := due_kind(deadline, now, hours):
			reminders.append(_Reminder(row.name, row.creation, kind, deadline))
	return reminders


# Controller ruling R28: the people in charge are the users of the ticket's open ToDo rows (ADR-019 QĐ 5 keeps the
# ticket's denormalised assignee column out of agent/); site_facts.ticket_assignments also returns closed ToDos.
def _people_in_charge(names: list[str]) -> dict[str, list[str]]:
	"""The users of each ticket's open ToDo rows, oldest assignment first, in one query for the batch."""
	people: dict[str, list[str]] = {}
	if not names:
		return people
	rows = frappe.get_all(
		"ToDo",
		filters={"reference_type": TICKET, "reference_name": ["in", names], "status": "Open"},
		fields=["reference_name", "allocated_to"],
		order_by="creation asc, name asc",
	)
	for row in rows:
		users = people.setdefault(row.reference_name, [])
		if row.allocated_to and row.allocated_to not in users:
			users.append(row.allocated_to)
	return people


def _deadline_key(deadline: datetime | None) -> str:
	return f"{deadline:{DEADLINE_KEY_FORMAT}}" if deadline else ""


def _people_text(users: list[str]) -> str:
	"""Helpdesk mention tags of `users` joined by ", "; NO_ASSIGNEE_TEXT when nobody is in charge."""
	if not users:
		return NO_ASSIGNEE_TEXT
	return ", ".join(
		MENTION.format(user=escape_html(user), label=escape_html(get_fullname(user))) for user in users
	)


def _text_values(reminder: _Reminder, settings) -> dict:
	"""The placeholders of the reminder texts and subjects: the ticket number, numbers and the deadline only."""
	hours = (
		settings.ba_note_due_hours if reminder.kind == KIND_BA_NOTE_MISSING else settings.due_reminder_hours
	)
	return {
		"name": reminder.ticket,
		"hours": hours,
		"days": settings.task_due_days,
		"deadline": f"{reminder.deadline:{DEADLINE_FORMAT}}" if reminder.deadline else "",
	}


def _value_after(reminder: _Reminder, users: list[str]) -> dict:
	if reminder.kind in DUE_KINDS:
		return {"kind": reminder.kind, "deadline": _deadline_key(reminder.deadline), "assignees": users}
	return {"kind": reminder.kind, "assignees": users}


def _remind(reminder: _Reminder, users: list[str], settings) -> str | None:
	"""One (ticket, kind): a comment on a ticket the agent may take (policy.can_send_ticket); else a coded notice to
	each person in charge, or nothing and no key when there is none (A-U5b-6: tried again next run). Returns the
	summary count to add one to."""
	if policy.can_send_ticket(reminder.ticket):
		_remind_on_ticket(reminder, users, settings)
		return reminder.kind
	if not users:
		return NO_ASSIGNEE
	_notify_by_code(reminder, users, settings)
	return reminder.kind


def _remind_on_ticket(reminder: _Reminder, users: list[str], settings) -> None:
	"""A comment of the agent account on the ticket, then its cycle key."""
	text = TEXT_BY_KIND[reminder.kind].format(**_text_values(reminder, settings), people=_people_text(users))
	comment = frappe.get_doc(TICKET, reminder.ticket).new_comment(text)
	_write_key(reminder, COMMENT_DOCTYPE, comment, _value_after(reminder, users))


def _notify_by_code(reminder: _Reminder, users: list[str], settings) -> None:
	"""A Notification Log from the agent account to each person in charge of a ticket the agent may not take, with
	the ticket number and the deadline only (A-12, NFR-1), then its cycle key; nothing is written on the ticket."""
	subject = CODE_SUBJECT[reminder.kind].format(**_text_values(reminder, settings))
	notices = [
		frappe.get_doc(
			{
				"doctype": NOTIFICATION_DOCTYPE,
				"for_user": user,
				"from_user": AGENT_USER,
				"type": "Alert",
				"document_type": TICKET,
				"document_name": reminder.ticket,
				"subject": subject,
			}
		)
		.insert(ignore_permissions=True)
		.name
		for user in users
	]
	_write_key(reminder, NOTIFICATION_DOCTYPE, notices[0], {**_value_after(reminder, users), "by_code": True})


def _write_key(reminder: _Reminder, doctype: str, name: str, value_after: dict) -> None:
	"""The reminder's bot_action row, written last: outside tests its commit covers the reminder and its key."""
	entry = run_log.action_entry(TOOL_BY_KIND[reminder.kind], doctype, name, True, value_after=value_after)
	run_log.write_bot_action(trigger=run_log.TRIGGER_SCHEDULED_JOB, ticket=reminder.ticket, actions=[entry])
