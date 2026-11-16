"""Deadline reminders for D/E tickets and milestone reminders for C/D tickets (design-addendum-2-U5b 3.2, AC-57, AC-58).

The cycle key of a reminder is an ok entry of its tool in the ticket's `bot_action` rows (ADR-033 QĐ 6): a
deadline reminder is keyed by (ticket, kind, deadline), so a moved deadline is a new cycle (A-U5b-2); a milestone
reminder by (ticket, kind), once in the ticket's life. Nothing here calls the model.
"""

import json
from datetime import datetime, timedelta

import frappe

from erp_ai.agent import run_log
from erp_ai.constants import LOG_DOCTYPE, LOGGER_NAME

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
