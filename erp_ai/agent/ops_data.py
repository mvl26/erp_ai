"""Calendar cycle keys, category lookups, the processing deadline and the milestone sets shared by the scheduled
jobs (design 3.6.2, ADR-033 QĐ 6; design-addendum-2-U5b 3.1: the 08:00 report and the reminders read the same
helpers, so they cannot drift apart).

A cycle key comes from the calendar, not from the moment the job runs: every cycle starts at 08:00,
so a run at 02:00 still belongs to the previous cycle.
"""

from datetime import date, datetime, time, timedelta

import frappe
from frappe.utils import get_datetime

from erp_ai.agent.routing import processing_deadline
from erp_ai.constants import AGENT_USER, CATEGORIES, LOGGER_NAME

BA_NOTE_MARKER = "**BA note**"
CYCLE_START = time(8, 0)
TICKET = "HD Ticket"
# Same rule as the setting's E-2 check; the agent core may not import the controller (ADR-001).
DUE_FIELD_TYPES = ("Date", "Datetime")


def daily_cycle(now: datetime) -> date:
	"""The day of the latest 08:00 at or before `now`."""
	if now.time() < CYCLE_START:
		return now.date() - timedelta(days=1)
	return now.date()


def weekly_cycle(now: datetime) -> date:
	"""The Monday of the latest "Monday 08:00" at or before `now`; the week to compute is the one before it."""
	monday = now.date() - timedelta(days=now.weekday())
	if now.weekday() == 0 and now.time() < CYCLE_START:
		return monday - timedelta(days=7)
	return monday


def monthly_cycle(now: datetime) -> str:
	"""`YYYY-MM` of the latest "day 1 08:00" at or before `now`; the month to review is the one before it."""
	if now.day == 1 and now.time() < CYCLE_START:
		return f"{now.date() - timedelta(days=1):%Y-%m}"
	return f"{now:%Y-%m}"


def category_by_ticket_type(mapping: dict) -> dict[str, str]:
	"""Invert a loaded `category_mapping`: ticket type -> category.

	Categories are read in `CATEGORIES` order (A -> F), not in the JSON key order; a key outside
	`CATEGORIES` and a category with an empty `ticket_type` are left out. When several categories share
	one ticket type, the one met first in `CATEGORIES` order wins, the same rule as
	`run_eval._expected_category`. Consequence: the tickets of a losing category are counted under the
	winning category in the accuracy report, the KPI (U5a) and the 08:00 report (`c_missing_ba_note`
	included).
	"""
	reverse_map: dict[str, str] = {}
	for category in CATEGORIES:
		ticket_type = (mapping.get(category) or {}).get("ticket_type")
		if ticket_type:
			reverse_map.setdefault(ticket_type, category)
	return reverse_map


def ticket_category(ticket_row: dict, reverse_map: dict[str, str]) -> str | None:
	"""The category of a ticket row from its `ticket_type`; None when the type is empty, missing or not mapped."""
	ticket_type = ticket_row.get("ticket_type")
	if not ticket_type:
		return None
	return reverse_map.get(ticket_type)


def ticket_deadline(category: str | None, resolution_by, due_value) -> datetime | None:
	"""The processing deadline of a ticket (D-18): `routing.processing_deadline` with `resolution_by` read as a
	datetime (a string goes through `get_datetime`); a Date due value is the end of that day, done there (A-U5b-3)."""
	return processing_deadline(category, get_datetime(resolution_by) if resolution_by else None, due_value)


def due_field(fieldname: str | None) -> str | None:
	"""The configured due field, or None when it is unset or no longer a Date/Datetime field of HD Ticket."""
	if not fieldname:
		return None
	field = frappe.get_meta(TICKET).get_field(fieldname)
	if field is None or field.fieldtype not in DUE_FIELD_TYPES:
		frappe.logger(LOGGER_NAME).warning(
			"erp_ai daily_report: due field %s is not a Date/Datetime field of HD Ticket, using resolution_by",
			fieldname,
		)
		return None
	return fieldname


def tickets_with_ba_note(names: list[str]) -> set[str]:
	"""Tickets with a comment by the bot that starts with BA_NOTE_MARKER."""
	if not names:
		return set()
	comments = frappe.get_all(
		"Comment",
		filters={
			"reference_doctype": TICKET,
			"reference_name": ["in", names],
			"comment_type": "Comment",
			"owner": AGENT_USER,
		},
		fields=["reference_name", "content"],
	)
	return {row.reference_name for row in comments if (row.content or "").startswith(BA_NOTE_MARKER)}


def tickets_with_task(names: list[str]) -> set[str]:
	"""Tickets with at least one Task whose `ai_ticket` is the ticket."""
	if not names:
		return set()
	return {
		row.ai_ticket
		for row in frappe.get_all("Task", filters={"ai_ticket": ["in", names]}, fields=["ai_ticket"])
	}
