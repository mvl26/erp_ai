import json
from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import add_days, get_datetime, getdate, now_datetime

from erp_ai.constants import CATEGORIES, CLASSIFICATION_FIELDS, LOG_DOCTYPE

TOTAL_LABEL = "Tổng"
CORRECTION_WINDOW = timedelta(days=7)


def execute(filters=None):
	"""Script Report: accuracy of the AI classification, per category A-F and in total (AC-12, A-12, D-17).

	Filters: `from_date`, `to_date` (both required, inclusive, by the log row's `creation`).
	A prediction is `corrected` when a person changed ticket type, agent group or priority to a value
	different from the prediction within 7 days; `pending` while it is younger than 7 days and not corrected.
	Returns no data when the range holds no prediction.

	Raises:
		frappe.PermissionError: the user may not run reports on ERP AI Log.
		frappe.ValidationError: a date is missing or `from_date` is after `to_date`.
	"""
	frappe.has_permission(LOG_DOCTYPE, "report", throw=True)
	from_date, to_date = _validate_dates(filters or {})
	predictions = _fetch_predictions(from_date, to_date)
	if not predictions:
		return _columns(), []

	now = now_datetime()
	counts = {category: {"predictions": 0, "corrected": 0, "pending": 0} for category in CATEGORIES}
	for row in predictions:
		bucket = counts[row.predicted_category]
		bucket["predictions"] += 1
		if _is_corrected(row):
			bucket["corrected"] += 1
		elif get_datetime(row.creation) > now - CORRECTION_WINDOW:
			bucket["pending"] += 1

	data = [{"category": category, **counts[category]} for category in CATEGORIES]
	data.append(
		{
			"category": TOTAL_LABEL,
			**{
				key: sum(bucket[key] for bucket in counts.values())
				for key in ("predictions", "corrected", "pending")
			},
		}
	)
	for row in data:
		row["accuracy_pct"] = _accuracy_pct(row)
	return _columns(), data


def _columns() -> list[dict]:
	return [
		{"fieldname": "category", "label": _("Category"), "fieldtype": "Data", "width": 120},
		{"fieldname": "predictions", "label": _("Predictions"), "fieldtype": "Int", "width": 110},
		{"fieldname": "corrected", "label": _("Corrected"), "fieldtype": "Int", "width": 110},
		{"fieldname": "pending", "label": _("Pending"), "fieldtype": "Int", "width": 110},
		{"fieldname": "accuracy_pct", "label": _("Accuracy (%)"), "fieldtype": "Percent", "width": 120},
	]


def _validate_dates(filters: dict):
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required"))
	from_date, to_date = getdate(filters["from_date"]), getdate(filters["to_date"])
	if from_date > to_date:
		frappe.throw(_("From Date must not be after To Date"))
	return from_date, to_date


def _fetch_predictions(from_date, to_date) -> list:
	log = frappe.qb.DocType(LOG_DOCTYPE)
	# Upper bound is the start of the day after `to_date`, so the whole last day counts.
	return (
		frappe.qb.from_(log)
		.select(
			log.predicted_category,
			log.creation,
			log.human_corrected_at,
			log.human_corrected_to,
			log.predicted_ticket_type,
			log.predicted_agent_group,
			log.predicted_priority,
		)
		.where(log.entry_type == "classify")
		.where(log.predicted_category.isin(CATEGORIES))
		.where(log.creation >= datetime.combine(from_date, datetime.min.time()))
		.where(log.creation < datetime.combine(getdate(add_days(to_date, 1)), datetime.min.time()))
		.run(as_dict=True)
	)


def _is_corrected(row) -> bool:
	if not row.human_corrected_at:
		return False
	if get_datetime(row.human_corrected_at) > get_datetime(row.creation) + CORRECTION_WINDOW:
		return False
	corrected_to = _parse_corrected_to(row.human_corrected_to)
	return any(
		(corrected_to.get(field) or "") != (row.get(f"predicted_{field}") or "")
		for field in CLASSIFICATION_FIELDS
	)


def _parse_corrected_to(raw) -> dict:
	try:
		parsed = json.loads(raw or "")
	except ValueError:
		return {}
	return parsed if isinstance(parsed, dict) else {}


def _accuracy_pct(row: dict) -> float | None:
	sample = row["predictions"] - row["pending"]
	if sample <= 0:
		return None
	return round((sample - row["corrected"]) / sample * 100, 2)
