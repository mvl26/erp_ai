from datetime import datetime
from decimal import Decimal

import frappe
from frappe import _
from frappe.query_builder.functions import Count, IfNull, Max, Min, Sum
from frappe.utils import add_days, add_months, flt, get_datetime, getdate, now_datetime

from erp_ai.constants import LOG_DOCTYPE, SETTING_DOCTYPE
from erp_ai.erp_ai_agent.report.erp_ai_accuracy.erp_ai_accuracy import _validate_dates

BY_TICKET = "Phiếu"
BY_RUN = "Lần chạy"
GROUP_BY_OPTIONS = (BY_TICKET, BY_RUN)
NO_TICKET_LABEL = "(không gắn phiếu)"
COST_PRECISION = 6
COST_STEP = Decimal(1).scaleb(-COST_PRECISION)
RANGE_TOTAL_LABEL = "Tổng trong khoảng"
MONTH_TOTAL_LABEL = "Tổng tháng này (ERP AI Log)"
SPENT_LABEL = "Đã chi tháng này (Setting)"


def execute(filters=None, now: datetime | None = None):
	"""Script Report: AI cost (USD) per ticket or per run from ERP AI Log (AC-60, AC-20).

	Filters: `from_date`, `to_date` (both required, inclusive, by the log row's `creation`) and `group_by`
	in `GROUP_BY_OPTIONS`. Per ticket: `ticket` (empty or NULL → `NO_TICKET_LABEL`), `runs` (distinct
	`run_id`), `cost_usd`; ordered by ticket, the rows without a ticket last. Per run: `run_id`, `ticket`,
	`started_at` (first `creation` in the range), `cost_usd`; ordered by `started_at`, then `run_id`.
	Only the ticket name is shown, never its subject.

	The summary has the range total, this month's total from ERP AI Log (the calendar month of `now`,
	whatever the range) and `ERP AI Setting.spent_this_month_usd`, each at `COST_PRECISION` places.

	Raises:
		frappe.PermissionError: the user may not run reports on ERP AI Log.
		frappe.ValidationError: a date is missing, `from_date` is after `to_date`, or `group_by` is not
			in `GROUP_BY_OPTIONS`.
	"""
	frappe.has_permission(LOG_DOCTYPE, "report", throw=True)
	filters = filters or {}
	from_date, to_date = _validate_dates(filters)
	group_by = filters.get("group_by")
	if group_by not in GROUP_BY_OPTIONS:
		frappe.throw(_("Group By must be one of: {0}").format(", ".join(GROUP_BY_OPTIONS)))
	start = datetime.combine(from_date, datetime.min.time())
	# The end is the start of the day after `to_date`, so the whole last day counts.
	end = datetime.combine(getdate(add_days(to_date, 1)), datetime.min.time())

	if group_by == BY_TICKET:
		columns, data = _ticket_columns(), _rows_by_ticket(start, end)
	else:
		columns, data = _run_columns(), _rows_by_run(start, end)
	range_total = sum((_exact(row["cost_usd"]) for row in data), Decimal(0))
	for row in data:
		row["cost_usd"] = flt(row["cost_usd"], COST_PRECISION)
	summary = _summary(range_total, _month_total(get_datetime(now) if now else now_datetime()))
	return columns, data, None, None, summary


def _rows_by_ticket(start: datetime, end: datetime) -> list[dict]:
	log = frappe.qb.DocType(LOG_DOCTYPE)
	ticket = IfNull(log.ticket, "")
	rows = (
		frappe.qb.from_(log)
		.select(
			ticket.as_("ticket"),
			Count(log.run_id).distinct().as_("runs"),
			Sum(log.cost_usd).as_("cost_usd"),
		)
		.where((log.creation >= start) & (log.creation < end))
		.groupby(ticket)
		.run(as_dict=True)
	)
	rows.sort(key=lambda row: (not row.ticket, row.ticket))
	return [
		{"ticket": row.ticket or NO_TICKET_LABEL, "runs": row.runs, "cost_usd": row.cost_usd} for row in rows
	]


def _rows_by_run(start: datetime, end: datetime) -> list[dict]:
	log = frappe.qb.DocType(LOG_DOCTYPE)
	started_at = Min(log.creation)
	rows = (
		frappe.qb.from_(log)
		.select(
			log.run_id,
			Max(log.ticket).as_("ticket"),
			started_at.as_("started_at"),
			Sum(log.cost_usd).as_("cost_usd"),
		)
		.where((log.creation >= start) & (log.creation < end))
		.groupby(log.run_id)
		.orderby(started_at)
		.orderby(log.run_id)
		.run(as_dict=True)
	)
	return [
		{
			"run_id": row.run_id,
			"ticket": row.ticket or NO_TICKET_LABEL,
			"started_at": row.started_at,
			"cost_usd": row.cost_usd,
		}
		for row in rows
	]


def _month_total(now: datetime) -> Decimal:
	"""Sum of `cost_usd` over the rows created in the calendar month of `now` (the bounds of
	`tasks.recompute_monthly_spend`)."""
	month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
	log = frappe.qb.DocType(LOG_DOCTYPE)
	rows = (
		frappe.qb.from_(log)
		.select(Sum(log.cost_usd).as_("spent"))
		.where((log.creation >= month_start) & (log.creation < add_months(month_start, 1)))
		.run(as_dict=True)
	)
	return _exact(rows[0].spent)


def _exact(value) -> Decimal:
	"""A `cost_usd` sum as an exact Decimal: the column is DECIMAL with `COST_PRECISION` places, but the
	query result comes back as float."""
	return Decimal(str(value or 0)).quantize(COST_STEP)


def _summary(range_total: Decimal, month_total: Decimal) -> list[dict]:
	spent = frappe.db.get_single_value(SETTING_DOCTYPE, "spent_this_month_usd", cache=False)
	return [
		{"label": label, "value": str(_exact(value)), "datatype": "Data"}
		for label, value in (
			(RANGE_TOTAL_LABEL, range_total),
			(MONTH_TOTAL_LABEL, month_total),
			(SPENT_LABEL, spent),
		)
	]


def _cost_column() -> dict:
	return {
		"fieldname": "cost_usd",
		"label": _("Cost (USD)"),
		"fieldtype": "Float",
		"precision": COST_PRECISION,
		"width": 130,
	}


def _ticket_columns() -> list[dict]:
	return [
		{"fieldname": "ticket", "label": _("Ticket"), "fieldtype": "Data", "width": 160},
		{"fieldname": "runs", "label": _("Runs"), "fieldtype": "Int", "width": 100},
		_cost_column(),
	]


def _run_columns() -> list[dict]:
	return [
		{"fieldname": "run_id", "label": _("Run ID"), "fieldtype": "Data", "width": 200},
		{"fieldname": "ticket", "label": _("Ticket"), "fieldtype": "Data", "width": 160},
		{"fieldname": "started_at", "label": _("Started At"), "fieldtype": "Datetime", "width": 170},
		_cost_column(),
	]
