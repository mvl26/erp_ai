"""Weekly KPI (design 3.6.4, D-11, A-14).

Every value is computed from the data as of the week's boundaries, never from the moment the job runs.
A KPI whose sample is 0 is `None` ("no data yet"); its sample field is 0.
"""

import json
from datetime import date, datetime, timedelta
from statistics import median

import frappe
from frappe.utils import get_datetime, now_datetime
from frappe.utils.file_lock import LockTimeoutError
from frappe.utils.synchronization import filelock

from erp_ai.agent.classification import load_mapping
from erp_ai.agent.ops_data import category_by_ticket_type, ticket_category, weekly_cycle
from erp_ai.constants import AGENT_USER, LOG_DOCTYPE, LOGGER_NAME, MESSAGE_DOCTYPE, SETTING_DOCTYPE

TICKET = "HD Ticket"
CLOSED_STATUSES = ("Resolved", "Closed")
COMPLETE_FIELDS = ("ticket_type", "agent_group", "priority")
FAST_RESPONSE_MINUTES = 15
FASTEST_RESPONSE_MINUTES = 5
TASK_DUE = timedelta(hours=72)
STALE_DAYS = (5, 7)
KPI_WEEK_DOCTYPE = "ERP AI KPI Week"
LOCK_NAME = "erp_ai_weekly_kpi"
LOCK_TIMEOUT_S = 5
MAX_BACKFILL_WEEKS = 8
WEEK = timedelta(days=7)
TITLE_KPI_FAILED = "erp_ai: KPI tuần lỗi"


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


def run_weekly_kpi(now: datetime | None = None) -> None:
	"""Write one `ERP AI KPI Week` row for every week that has none, up to 8 weeks back (D-10, NFR-3).

	The target week is the one before the cycle `now` belongs to. A week that fails is rolled back, logged and
	ends the run: the rows stay contiguous, so the next run starts at that week.
	"""
	logger = frappe.logger(LOGGER_NAME)
	try:
		with filelock(LOCK_NAME, timeout=LOCK_TIMEOUT_S):
			_run_locked(get_datetime(now) if now else now_datetime(), logger)
	except LockTimeoutError:
		logger.info("weekly_kpi: lock busy")


def _weeks_to_compute(now: datetime) -> list[date]:
	target = weekly_cycle(now) - WEEK
	first = target - (MAX_BACKFILL_WEEKS - 1) * WEEK
	newest = frappe.get_all(
		KPI_WEEK_DOCTYPE, fields=["week_start"], order_by="week_start desc", limit_page_length=1
	)
	if newest:
		first = max(first, frappe.utils.getdate(newest[0].week_start) + WEEK)
	return [first + n * WEEK for n in range((target - first) // WEEK + 1)] if first <= target else []


def _run_locked(now: datetime, logger) -> None:
	weeks = _weeks_to_compute(now)
	settings = frappe.get_single(SETTING_DOCTYPE)
	written = 0
	for week_start in weeks:
		frappe.db.savepoint(LOCK_NAME)
		try:
			values = compute_week(week_start, settings)
			frappe.get_doc({"doctype": KPI_WEEK_DOCTYPE, **values, "computed_at": now}).insert(
				ignore_permissions=True
			)
			written += 1
		except frappe.DuplicateEntryError:
			frappe.db.rollback(save_point=LOCK_NAME)
		except Exception as exc:
			frappe.db.rollback(save_point=LOCK_NAME)
			frappe.log_error(TITLE_KPI_FAILED, f"week={week_start} error={type(exc).__name__}")
			break
	logger.info("erp_ai weekly_kpi: %s of %s weeks written", written, len(weeks))


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
	sample = len(minutes)  # R21a: the sample of a median is the values it is computed from
	return {
		"first_response_median_min": median(minutes) if minutes else None,
		"first_response_within_15_pct": _pct(sum(m <= FAST_RESPONSE_MINUTES for m in minutes), len(tickets)),
		"first_response_within_5_pct": _pct(
			sum(m <= FASTEST_RESPONSE_MINUTES for m in minutes), len(tickets)
		),
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
	"""Tickets with an agent-side comment, message to the bot, sent email or assignment by anyone other than the bot."""
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
	# a person who spoke to the bot in the ticket's conversation worked on the ticket, as with a comment
	touched.update(
		row.ticket
		for row in frappe.get_all(
			MESSAGE_DOCTYPE, filters={"ticket": ["in", names]}, fields=["ticket", "owner"]
		)
		if row.owner not in (AGENT_USER, raised_by[row.ticket])
	)
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
		if any(is_bot_close(action, row.ticket) for action in log_actions(row.actions)):
			closed.add(row.ticket)
	return closed


def is_bot_close(action: dict, ticket: str | None) -> bool:
	"""True when an action entry is ok and set `ticket`'s status to Resolved/Closed (ADR-024)."""
	return bool(
		ticket
		and action.get("ok") is True
		and action.get("doctype") == TICKET
		and action.get("name") == ticket
		and (action.get("value_after") or {}).get("status") in CLOSED_STATUSES
	)


def log_actions(raw) -> list[dict]:
	"""The `actions` list of a log row; an unreadable value counts as no action."""
	try:
		actions = json.loads(raw or "[]")
	except ValueError:
		return []
	if not isinstance(actions, list):
		return []
	return [action for action in actions if isinstance(action, dict)]
