"""The 08:00 daily report (design 3.6.3, AC-51, AC-26, D-18, A-D5).

Windows come from `anchor` (the cycle's 08:00): "new" means created in `[anchor - 24 h, anchor)`, "done" means
resolved in that window. Every state is read when the job runs: "open" means created before `anchor` and
`status_category` not "Resolved"; first response, BA notes and Tasks are read as they are at run time.
"""

from datetime import datetime, timedelta

import frappe

from erp_ai.agent import policy
from erp_ai.agent.classification import load_mapping
from erp_ai.agent.ops_data import BA_NOTE_MARKER, category_by_ticket_type, ticket_category
from erp_ai.agent.routing import load_routing_config, processing_deadline, response_overdue
from erp_ai.constants import AGENT_USER, LOGGER_NAME, SETTING_DOCTYPE

TICKET = "HD Ticket"
WINDOW = timedelta(hours=24)
UNKNOWN_CATEGORY = "?"
PROGRESS_CATEGORIES = ("D", "E")
# Same rule as the setting's E-2 check; the agent core may not import the controller (ADR-001).
DUE_FIELD_TYPES = ("Date", "Datetime")


def build_daily_report(anchor: datetime) -> dict:
	"""The ticket figures of the report for the window ending at `anchor`."""
	settings = frappe.get_single(SETTING_DOCTYPE)
	reverse_map = category_by_ticket_type(load_mapping(settings.category_mapping))
	routing = load_routing_config(settings.routing_rules)
	due_field = _due_field(settings.field_due_date)
	start = anchor - WINDOW

	new = _tickets([["creation", ">=", start], ["creation", "<", anchor]], reverse_map)
	open_rows = _tickets(
		[["creation", "<", anchor], ["status_category", "!=", "Resolved"]], reverse_map, due_field
	)
	for row in open_rows:
		row.deadline = processing_deadline(
			row.category, row.resolution_by, row.get(due_field) if due_field else None
		)
	due_until = anchor + timedelta(hours=settings.due_reminder_hours)
	overdue = [row for row in open_rows if row.deadline and row.deadline <= anchor]

	c_old = [
		row
		for row in open_rows
		if row.category == "C" and row.creation <= anchor - timedelta(hours=settings.ba_note_due_hours)
	]
	ba_noted = _ba_noted([row.name for row in c_old])
	cd_old = [
		row
		for row in open_rows
		if row.category in ("C", "D") and row.creation <= anchor - timedelta(days=settings.task_due_days)
	]
	with_task = _with_task([row.name for row in cd_old])

	return {
		"new_by_category_priority": _count_by_category_priority(new),
		"new_list": _items(new),
		"due_soon": _items(
			(row for row in open_rows if row.deadline and anchor < row.deadline <= due_until),
			with_deadline=True,
		),
		"overdue": _items(overdue, with_deadline=True),
		"response_overdue": _items(
			row
			for row in open_rows
			if response_overdue(row.creation, row.first_responded_on, row.category, routing, anchor)
		),
		"c_missing_ba_note": _items(row for row in c_old if row.name not in ba_noted),
		"cd_missing_task": _items(row for row in cd_old if row.name not in with_task),
		"de_progress": _de_progress(start, anchor, open_rows, overdue, reverse_map),
	}


def _due_field(due_field: str | None) -> str | None:
	"""The configured due field, or None when it is unset or no longer a Date/Datetime field of HD Ticket."""
	if not due_field:
		return None
	field = frappe.get_meta(TICKET).get_field(due_field)
	if field is None or field.fieldtype not in DUE_FIELD_TYPES:
		frappe.logger(LOGGER_NAME).warning(
			"erp_ai daily_report: due field %s is not a Date/Datetime field of HD Ticket, using resolution_by",
			due_field,
		)
		return None
	return due_field


def _tickets(filters: list, reverse_map: dict[str, str], due_field: str | None = None) -> list:
	"""Ticket rows oldest first, each with its `category` (None when unknown)."""
	rows = frappe.get_all(
		TICKET,
		filters=filters,
		fields=[
			"name",
			"subject",
			"ticket_type",
			"priority",
			"creation",
			"first_responded_on",
			"resolution_by",
			*([due_field] if due_field else []),
		],
		order_by="creation asc, name asc",
	)
	for row in rows:
		row.category = ticket_category(row, reverse_map)
	return rows


def _items(rows, with_deadline: bool = False) -> list[dict]:
	"""List entries; an excluded ticket (A-D5) carries only its number, category and priority.

	With `with_deadline`, a sendable ticket's entry also carries the processing deadline it was listed by.
	"""
	items = []
	for row in rows:
		item = {"name": row.name, "category": row.category or UNKNOWN_CATEGORY, "priority": _priority(row)}
		if policy.can_send_ticket(row.name):
			item.update(subject=row.subject, excluded=False)
			if with_deadline:
				item["deadline"] = row.deadline
		else:
			item["excluded"] = True
		items.append(item)
	return items


def _count_by_category_priority(rows: list) -> dict[str, dict[str, int]]:
	counts: dict[str, dict[str, int]] = {}
	for row in rows:
		by_priority = counts.setdefault(row.category or UNKNOWN_CATEGORY, {})
		priority = _priority(row)
		by_priority[priority] = by_priority.get(priority, 0) + 1
	return counts


def _priority(row) -> str:
	"""HD Ticket does not require a priority; an empty one counts as UNKNOWN_CATEGORY."""
	return row.priority or UNKNOWN_CATEGORY


def _ba_noted(names: list[str]) -> set[str]:
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


def _with_task(names: list[str]) -> set[str]:
	"""Tickets with at least one Task whose `ai_ticket` is the ticket."""
	if not names:
		return set()
	return {
		row.ai_ticket
		for row in frappe.get_all("Task", filters={"ai_ticket": ["in", names]}, fields=["ai_ticket"])
	}


def _de_progress(
	start: datetime, anchor: datetime, open_rows: list, overdue: list, reverse_map: dict
) -> dict:
	"""For D and E: resolved in the window and still Resolved, open, open past the processing deadline."""
	resolved = frappe.get_all(
		TICKET,
		filters=[
			["resolution_date", ">=", start],
			["resolution_date", "<", anchor],
			["status_category", "=", "Resolved"],
		],
		fields=["ticket_type"],
	)
	resolved_categories = [ticket_category(row, reverse_map) for row in resolved]
	return {
		category: {
			"done": resolved_categories.count(category),
			"in_progress": sum(row.category == category for row in open_rows),
			"overdue": sum(row.category == category for row in overdue),
		}
		for category in PROGRESS_CATEGORIES
	}
