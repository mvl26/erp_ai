"""Weekly KPI (design 3.6.4, D-11, A-14).

Every value is computed from the data as of the week's boundaries, never from the moment the job runs.
A KPI whose sample is 0 is `None` ("no data yet"); its sample field is 0.
"""

import json
from datetime import date, datetime, timedelta
from statistics import median

import frappe

from erp_ai.constants import AGENT_USER, LOG_DOCTYPE

TICKET = "HD Ticket"
CLOSED_STATUSES = ("Resolved", "Closed")
COMPLETE_FIELDS = ("ticket_type", "agent_group", "priority")
FAST_RESPONSE_MINUTES = 15
FASTEST_RESPONSE_MINUTES = 5


def compute_week(week_start: date, settings) -> dict:
	"""KPI 1-3 of the week starting Monday `week_start`; keys are fields of `ERP AI KPI Week`."""
	ws = datetime.combine(week_start, datetime.min.time())
	we = ws + timedelta(days=7)
	return {
		"week_start": week_start,
		"week_end": week_start + timedelta(days=6),
		**_first_response(ws, we),
		**_complete_fields(we),
		**_closed_without_human(ws, we),
	}


def _pct(part: int, whole: int) -> float | None:
	return part * 100 / whole if whole else None


def _first_response(ws: datetime, we: datetime) -> dict:
	"""KPI 1: tickets created in [ws, we); median over answered ones, rates over all (unanswered = missed)."""
	tickets = frappe.get_all(
		TICKET,
		filters=[["creation", ">=", ws], ["creation", "<", we]],
		fields=["creation", "first_responded_on"],
	)
	minutes = [
		(row.first_responded_on - row.creation).total_seconds() / 60
		for row in tickets
		if row.first_responded_on
	]
	sample = len(tickets)
	return {
		"first_response_median_min": median(minutes) if minutes else None,
		"first_response_within_15_pct": _pct(sum(m <= FAST_RESPONSE_MINUTES for m in minutes), sample),
		"first_response_within_5_pct": _pct(sum(m <= FASTEST_RESPONSE_MINUTES for m in minutes), sample),
		"first_response_sample": sample,
	}


def _complete_fields(we: datetime) -> dict:
	"""KPI 2: tickets open at `we` (A-D2: created before it, not resolved before it) with all three fields."""
	tickets = frappe.get_all(
		TICKET,
		filters=[["creation", "<", we]],
		or_filters=[["resolution_date", "is", "not set"], ["resolution_date", ">=", we]],
		fields=list(COMPLETE_FIELDS),
	)
	complete = sum(all(row.get(field) for field in COMPLETE_FIELDS) for row in tickets)
	return {"complete_fields_pct": _pct(complete, len(tickets)), "complete_fields_sample": len(tickets)}


def _closed_without_human(ws: datetime, we: datetime) -> dict:
	"""KPI 3: tickets resolved in [ws, we) whose every agent-side action is the bot's and that the bot closed."""
	tickets = frappe.get_all(
		TICKET,
		filters=[["resolution_date", ">=", ws], ["resolution_date", "<", we]],
		fields=["name", "raised_by"],
	)
	names = [row.name for row in tickets]
	human_touched = _human_touched(tickets) if names else set()
	bot_closed = _bot_closed(names) if names else set()
	without_human = sum(name in bot_closed and name not in human_touched for name in names)
	return {"closed_without_human_pct": _pct(without_human, len(names)), "closed_sample": len(names)}


def _human_touched(tickets: list) -> set[str]:
	"""Tickets with an agent-side comment, sent email or assignment by anyone other than the bot."""
	names = [row.name for row in tickets]
	raised_by = {row.name: row.raised_by for row in tickets}
	reference = {"reference_doctype": TICKET, "reference_name": ["in", names]}
	touched = {
		row.reference_name
		for row in frappe.get_all(
			"Comment",
			filters={**reference, "comment_type": "Comment"},
			fields=["reference_name", "owner"],
		)
		if row.owner not in (AGENT_USER, raised_by[row.reference_name])
	}
	touched.update(
		row.reference_name
		for row in frappe.get_all(
			"Communication",
			filters={**reference, "sent_or_received": "Sent"},
			fields=["reference_name", "owner"],
		)
		if row.owner != AGENT_USER
	)
	touched.update(
		row.reference_name
		for row in frappe.get_all(
			"ToDo",
			filters={"reference_type": TICKET, "reference_name": ["in", names]},
			fields=["reference_name", "assigned_by"],
		)
		if row.assigned_by != AGENT_USER
	)
	return touched


def _bot_closed(names: list[str]) -> set[str]:
	"""Tickets with an ERP AI Log action that is ok and set the ticket's status to Resolved/Closed (ADR-024)."""
	closed = set()
	for row in frappe.get_all(LOG_DOCTYPE, filters={"ticket": ["in", names]}, fields=["ticket", "actions"]):
		for action in _actions(row.actions):
			if (
				action.get("ok") is True
				and action.get("doctype") == TICKET
				and action.get("name") == row.ticket
				and (action.get("value_after") or {}).get("status") in CLOSED_STATUSES
			):
				closed.add(row.ticket)
	return closed


def _actions(raw) -> list[dict]:
	"""The `actions` list of a log row; an unreadable value counts as no action."""
	try:
		actions = json.loads(raw or "[]")
	except ValueError:
		return []
	if not isinstance(actions, list):
		return []
	return [action for action in actions if isinstance(action, dict)]
