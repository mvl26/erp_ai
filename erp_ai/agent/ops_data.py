"""Calendar cycle keys and category lookups shared by the scheduled jobs (design 3.6.2, ADR-033 QĐ 6).

A cycle key comes from the calendar, not from the moment the job runs: every cycle starts at 08:00,
so a run at 02:00 still belongs to the previous cycle.
"""

from datetime import date, datetime, time, timedelta

BA_NOTE_MARKER = "**BA note**"
CYCLE_START = time(8, 0)


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
	"""Invert a loaded `category_mapping`: ticket type -> category; entries without a ticket type are left out."""
	return {entry["ticket_type"]: category for category, entry in mapping.items() if entry.get("ticket_type")}


def ticket_category(ticket_row, reverse_map: dict[str, str]) -> str | None:
	"""The category of a ticket row from its `ticket_type`; None when the type is empty or not mapped."""
	return reverse_map.get(ticket_row.get("ticket_type"))
