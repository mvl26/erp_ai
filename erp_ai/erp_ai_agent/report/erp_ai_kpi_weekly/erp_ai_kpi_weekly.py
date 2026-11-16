import json
from datetime import timedelta

import frappe
from frappe.utils import flt, getdate

from erp_ai.constants import KPI_IDS, SETTING_DOCTYPE

KPI_WEEK_DOCTYPE = "ERP AI KPI Week"
NO_DATA_LABEL = "chưa có dữ liệu"
# KPI id -> (label, field of ERP AI KPI Week, its sample field, unit); the rows come in `KPI_IDS` order.
# Frappe stores an empty Float/Percent as 0, so "no data" is read from the sample: 0 means no data.
# KPI 6 has no sample: a count of 0 is a real value.
KPI_ROWS = {
	"first_response_minutes": (
		"Phản hồi đầu tiên: trung vị",
		"first_response_median_min",
		"first_response_sample",
		"phút",
	),
	"complete_fields_pct": (
		"Đủ đầu mục, nhóm, ưu tiên",
		"complete_fields_pct",
		"complete_fields_sample",
		"%",
	),
	"closed_without_human_pct": (
		"Đóng không cần người",
		"closed_without_human_pct",
		"closed_sample",
		"%",
	),
	"b_resolution_hours": (
		"Xử lý đầu mục B: trung bình",
		"b_resolution_avg_hours",
		"b_resolution_sample",
		"giờ",
	),
	"c_task_in_3_days_pct": (
		"Đầu mục C có Task trong 3 ngày",
		"c_task_in_3_days_pct",
		"c_task_sample",
		"%",
	),
	"stale_over_5_days": ("Tồn quá 5 ngày", "stale_over_5_days", None, "phiếu"),
}
COLUMNS = (
	("kpi", "KPI"),
	("this_week", "Tuần này"),
	("last_week", "Tuần trước"),
	("target_gd2", "Mục tiêu GĐ2"),
	("target_gd4", "Mục tiêu GĐ4"),
	("unit", "Đơn vị"),
)


def execute(filters=None):
	"""Script Report: the six KPI of a week against the week before and the targets (AC-56, AC-20).

	Filter `week_start` is optional; empty means the newest week that has a row. A week without a row, and a
	KPI whose sample was 0 (stored empty), show `NO_DATA_LABEL`. Targets come from `ERP AI Setting.kpi_targets`.

	Raises:
		frappe.PermissionError: the user may not run reports on ERP AI KPI Week.
	"""
	frappe.has_permission(KPI_WEEK_DOCTYPE, "report", throw=True)
	week_start = (filters or {}).get("week_start")
	week_start = getdate(week_start) if week_start else _newest_week()
	this_week = _week_values(week_start)
	last_week = _week_values(week_start - timedelta(days=7) if week_start else None)
	targets = _targets()

	data = []
	for kpi in KPI_IDS:
		label, field, sample, unit = KPI_ROWS[kpi]
		data.append(
			{
				"kpi": label,
				"this_week": _week_value(this_week, field, sample),
				"last_week": _week_value(last_week, field, sample),
				"target_gd2": _format((targets.get(kpi) or {}).get("gd2")),
				"target_gd4": _format((targets.get(kpi) or {}).get("gd4")),
				"unit": unit,
			}
		)
	columns = [
		{"fieldname": fieldname, "label": label, "fieldtype": "Data", "width": 160}
		for fieldname, label in COLUMNS
	]
	return columns, data


def _newest_week():
	rows = frappe.get_all(
		KPI_WEEK_DOCTYPE, fields=["week_start"], order_by="week_start desc", limit_page_length=1
	)
	return getdate(rows[0].week_start) if rows else None


def _week_values(week_start) -> dict:
	if not week_start:
		return {}
	return frappe.db.get_value(KPI_WEEK_DOCTYPE, {"week_start": week_start}, "*", as_dict=True) or {}


def _week_value(week: dict, field: str, sample: str | None) -> str:
	if not week or (sample and not week.get(sample)):
		return NO_DATA_LABEL
	return _format(week.get(field))


def _targets() -> dict:
	try:
		targets = json.loads(frappe.db.get_single_value(SETTING_DOCTYPE, "kpi_targets") or "{}")
	except ValueError:
		return {}
	return targets if isinstance(targets, dict) else {}


def _format(value) -> str:
	"""A number at one decimal without a trailing zero; empty or missing is `NO_DATA_LABEL`."""
	if value is None or value == "":
		return NO_DATA_LABEL
	rounded = flt(value, 1)
	return str(int(rounded)) if rounded == int(rounded) else str(rounded)
