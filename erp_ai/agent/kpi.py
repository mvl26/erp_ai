"""Weekly KPI (design 3.6.4, D-11, A-14).

Every value is computed from the data as of the week's boundaries, never from the moment the job runs.
A KPI whose sample is 0 is `None` ("no data yet"); its sample field is 0.
"""

import json
from datetime import date, datetime, timedelta
from statistics import median

import frappe

from erp_ai.agent.classification import load_mapping
from erp_ai.agent.ops_data import category_by_ticket_type, ticket_category
from erp_ai.constants import AGENT_USER, LOG_DOCTYPE

TICKET = "HD Ticket"
CLOSED_STATUSES = ("Resolved", "Closed")
COMPLETE_FIELDS = ("ticket_type", "agent_group", "priority")
FAST_RESPONSE_MINUTES = 15
FASTEST_RESPONSE_MINUTES = 5
TASK_DUE = timedelta(hours=72)
STALE_DAYS = (5, 7)


def compute_week(week_start: date, settings) -> dict:
	"""KPI 1-6 of the week starting Monday `week_start`; keys are fields of `ERP AI KPI Week`."""
	ws = datetime.combine(week_start, datetime.min.time())
	we = ws + timedelta(days=7)
	reverse_map = category_by_ticket_type(load_mapping(settings.category_mapping))
	return {
		"week_start": week_start,
		"week_end": week_start + timedelta(days=6),
		**_first_response(ws, we),
		**_complete_fields(we),
		**_closed_without_human(ws, we),
		**_b_resolution(ws, we, reverse_map),
		**_c_task_in_3_days(ws, we, reverse_map),
		**_stale(we),
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


def _open_at(we: datetime, fields: list[str]) -> list:
	"""Tickets open at `we` (A-D2): created before it, not resolved before it."""
	return frappe.get_all(
		TICKET,
		filters=[["creation", "<", we]],
		or_filters=[["resolution_date", "is", "not set"], ["resolution_date", ">=", we]],
		fields=fields,
	)


def _complete_fields(we: datetime) -> dict:
	"""KPI 2: tickets open at `we` with all three fields."""
	tickets = _open_at(we, list(COMPLETE_FIELDS))
	complete = sum(all(row.get(field) for field in COMPLETE_FIELDS) for row in tickets)
	return {"complete_fields_pct": _pct(complete, len(tickets)), "complete_fields_sample": len(tickets)}


def _b_resolution(ws: datetime, we: datetime, reverse_map: dict[str, str]) -> dict:
	"""KPI 4: mean calendar hours from creation to resolution of category B tickets resolved in [ws, we)."""
	tickets = frappe.get_all(
		TICKET,
		filters=[["resolution_date", ">=", ws], ["resolution_date", "<", we]],
		fields=["ticket_type", "creation", "resolution_date"],
	)
	hours = [
		(row.resolution_date - row.creation).total_seconds() / 3600
		for row in tickets
		if ticket_category(row, reverse_map) == "B"
	]
	return {
		"b_resolution_avg_hours": sum(hours) / len(hours) if hours else None,
		"b_resolution_sample": len(hours),
	}


def _c_task_in_3_days(ws: datetime, we: datetime, reverse_map: dict[str, str]) -> dict:
	"""KPI 5 (A-D4): category C tickets created in [ws - 3 days, we - 3 days) with a linked Task created
	at most 72 h after the ticket (exactly 72 h counts)."""
	tickets = [
		row
		for row in frappe.get_all(
			TICKET,
			filters=[["creation", ">=", ws - TASK_DUE], ["creation", "<", we - TASK_DUE]],
			fields=["name", "ticket_type", "creation"],
		)
		if ticket_category(row, reverse_map) == "C"
	]
	created = {row.name: row.creation for row in tickets}
	in_time = (
		{
			task.ai_ticket
			for task in frappe.get_all(
				"Task", filters={"ai_ticket": ["in", list(created)]}, fields=["ai_ticket", "creation"]
			)
			if task.creation <= created[task.ai_ticket] + TASK_DUE
		}
		if created
		else set()
	)
	return {"c_task_in_3_days_pct": _pct(len(in_time), len(tickets)), "c_task_sample": len(tickets)}


def _stale(we: datetime) -> dict:
	"""KPI 6: tickets open at `we` older than 5 and than 7 days (exactly 5 days is not counted)."""
	tickets = _open_at(we, ["creation"])
	return {
		f"stale_over_{days}_days": sum(we - row.creation > timedelta(days=days) for row in tickets)
		for days in STALE_DAYS
	}


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
