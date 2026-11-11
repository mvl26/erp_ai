from datetime import datetime

import frappe
from frappe.query_builder.functions import Sum
from frappe.utils import add_months, get_datetime, now_datetime

from erp_ai.constants import CREDENTIAL_DOCTYPE, LOG_DOCTYPE, SETTING_DOCTYPE, TITLE_RUN_FAILED


def recompute_monthly_spend(now: datetime | None = None) -> None:
	"""Daily job (AC-16, D-19): set this month's spend from the ERP AI Log cost sums.

	Sums `cost_usd` of rows created in the calendar month of `now` into
	`ERP AI Setting.spent_this_month_usd` and, per `credential_label`, into each key row's
	`spent_month_usd` (a key with no log row gets 0). On the 1st the new month starts at ~0.
	Writes directly (no `.save()`); a log label with no key row only counts in the total.
	On any error it rolls back, logs a constant title with an explicit message and returns (D-20).
	"""
	now = get_datetime(now) if now else now_datetime()
	month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
	next_month_start = add_months(month_start, 1)

	try:
		log = frappe.qb.DocType(LOG_DOCTYPE)
		rows = (
			frappe.qb.from_(log)
			.select(log.credential_label, Sum(log.cost_usd).as_("spent"))
			.where((log.creation >= month_start) & (log.creation < next_month_start))
			.groupby(log.credential_label)
			.run(as_dict=True)
		)
		spent_by_label = {row.credential_label: row.spent or 0 for row in rows}

		frappe.db.set_single_value(SETTING_DOCTYPE, "spent_this_month_usd", sum(spent_by_label.values()))
		for key in frappe.get_all(
			CREDENTIAL_DOCTYPE, fields=["name", "label"], parent_doctype=SETTING_DOCTYPE
		):
			frappe.db.set_value(
				CREDENTIAL_DOCTYPE,
				key.name,
				"spent_month_usd",
				spent_by_label.get(key.label, 0),
				update_modified=False,
			)
		if not frappe.flags.in_test:
			frappe.db.commit()
	except Exception as exc:
		frappe.db.rollback()
		frappe.log_error(
			TITLE_RUN_FAILED,
			f"recompute_monthly_spend month={month_start:%Y-%m} error={type(exc).__name__}",
		)
