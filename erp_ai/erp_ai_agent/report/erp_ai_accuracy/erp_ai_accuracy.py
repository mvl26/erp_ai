import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from fractions import Fraction

import frappe
from frappe import _
from frappe.utils import add_days, get_datetime, getdate, now_datetime

from erp_ai.agent import policy
from erp_ai.constants import AGENT_USER, CATEGORIES, CLASSIFICATION_FIELDS, LOG_DOCTYPE

TOTAL_LABEL = "Tổng"
LATENCY_LABELS = ("Phân loại ≤ 5 phút", "Phân loại > 5 phút", "Chưa phân loại")
GATE_LABEL = "Cửa L0 → L1"
LATENCY_LIMIT = timedelta(minutes=5)
COUNT_KEYS = ("predictions", "labeled", "correct")
GATE_WINDOW_DAYS = 14
GATE_MIN_SAMPLE = 30
GATE_MIN_ACCURACY = 0.85


@dataclass(frozen=True)
class GateResult:
	verdict: str
	labeled: int
	correct: int


def l0_l1_gate(now: datetime | None = None) -> GateResult:
	"""Verdict of the L0 → L1 gate (AC-18), independent of the report's filters.

	The sample is every ticket whose first successful `classify` row was created in
	`(now - GATE_WINDOW_DAYS, now]`, labeled/correct by `label_outcome`. Fewer than `GATE_MIN_SAMPLE`
	labeled → "Chưa đủ mẫu"; `correct / labeled >= GATE_MIN_ACCURACY` (exact, no float rounding) →
	"Đạt"; otherwise "Chưa đạt".
	"""
	now = now or now_datetime()
	return _gate_result(_fetch_classify_rows(_through(now)), now)


def _through(moment: datetime) -> datetime:
	"""The end for `_fetch_classify_rows` that keeps rows created at `moment` itself (it keeps rows before
	its end)."""
	return moment + timedelta(microseconds=1)


def _gate_result(rows: list, now: datetime) -> GateResult:
	"""`l0_l1_gate` over `rows`: the `classify` rows created up to `now`, oldest first."""
	start = now - timedelta(days=GATE_WINDOW_DAYS)
	labeled = correct = 0
	for row in _first_successes(rows):
		if get_datetime(row.creation) > start:
			row_labeled, row_correct = label_outcome(row)
			labeled += row_labeled
			correct += row_correct
	if labeled < GATE_MIN_SAMPLE:
		verdict = "Chưa đủ mẫu"
	elif Fraction(correct, labeled) >= Fraction(str(GATE_MIN_ACCURACY)):
		verdict = "Đạt"
	else:
		verdict = "Chưa đạt"
	return GateResult(verdict, labeled, correct)


def execute(filters=None):
	"""Script Report: accuracy of the AI classification against the human's labels, per category A-F and in
	total (AC-12, AC-19, D-9, NFR-8).

	Filters: `from_date`, `to_date` (both required, inclusive, by the log row's `creation`).
	Each ticket counts once, by its first `classify` row with a predicted category (`_first_predictions`);
	`labeled`/`correct` follow `label_outcome`. `failed_runs` (total row only) counts the tickets with a
	`classify` row without a predicted category in the range and no successful `classify` row up to its end.
	Returns no data when the range holds neither a prediction nor a failed run.

	The summary (AC-17, AC-18, D-8) always has the latency numbers of `_latency_counts` and the
	`l0_l1_gate` verdict at the current time with `correct/labeled`.

	Raises:
		frappe.PermissionError: the user may not run reports on ERP AI Log.
		frappe.ValidationError: a date is missing or `from_date` is after `to_date`.
	"""
	frappe.has_permission(LOG_DOCTYPE, "report", throw=True)
	from_date, to_date = _validate_dates(filters or {})
	start = datetime.combine(from_date, datetime.min.time())
	# The end is the start of the day after `to_date`, so the whole last day counts.
	end = datetime.combine(getdate(add_days(to_date, 1)), datetime.min.time())
	now = now_datetime()
	# One read serves the gate (rows up to `now`), the range (rows before `end`) and the latency of the
	# tickets created in the range (every row read, so a result after the range end still counts).
	all_rows = _fetch_classify_rows(max(end, _through(now)))
	gate = _gate_result([row for row in all_rows if get_datetime(row.creation) <= now], now)
	rows = [row for row in all_rows if get_datetime(row.creation) < end]
	summary = _summary(_latency_counts(all_rows, start, end), gate)
	predictions = _first_predictions(rows, start)
	failed_runs = _failed_runs(rows, start)
	if not predictions and not failed_runs:
		return _columns(), [], None, None, summary

	counts = {category: dict.fromkeys(COUNT_KEYS, 0) for category in CATEGORIES}
	for row in predictions:
		labeled, correct = label_outcome(row)
		bucket = counts[row.predicted_category]
		bucket["predictions"] += 1
		bucket["labeled"] += labeled
		bucket["correct"] += correct

	data = [{"category": category, **counts[category], "failed_runs": None} for category in CATEGORIES]
	data.append(
		{
			"category": TOTAL_LABEL,
			**{key: sum(bucket[key] for bucket in counts.values()) for key in COUNT_KEYS},
			"failed_runs": failed_runs,
		}
	)
	for row in data:
		row["accuracy_pct"] = _accuracy_pct(row)
	return _columns(), data, None, None, summary


def _latency_counts(rows: list, start: datetime, end: datetime) -> list[int]:
	"""[≤ 5 min, > 5 min, not classified] over the tickets created in `[start, end)` (AC-17, D-8).

	The latency is the `creation` of the ticket's first successful `classify` row in `rows` minus the
	ticket's `creation`; exactly `LATENCY_LIMIT` is "≤ 5". Tickets skipped on purpose are not counted
	(`_skipped_on_purpose`); the rest without a successful row are not classified.
	"""
	successes = {row.ticket: row for row in _first_successes(rows)}
	counts = [0, 0, 0]
	tickets = frappe.get_all(
		"HD Ticket",
		filters=[["creation", ">=", start], ["creation", "<", end]],
		fields=["name", "creation", "owner", *policy.SEND_POLICY_FIELDS, *CLASSIFICATION_FIELDS],
	)
	for ticket in tickets:
		success = successes.get(ticket.name)
		if _skipped_on_purpose(ticket, success):
			continue
		if not success:
			counts[2] += 1
		elif get_datetime(success.creation) - get_datetime(ticket.creation) <= LATENCY_LIMIT:
			counts[0] += 1
		else:
			counts[1] += 1
	return counts


def _skipped_on_purpose(ticket, success) -> bool:
	"""Created by the agent, not sendable, or full at creation: every classification field has a label at
	creation on the first successful row or, with no successful row, a value on the ticket."""
	if ticket.owner == AGENT_USER or not policy.can_send_ticket(ticket):
		return True
	values = _parse_labels(success.created_labels) if success else ticket
	return all(values.get(field) for field in CLASSIFICATION_FIELDS)


def _summary(latency_counts: list[int], gate: GateResult) -> list[dict]:
	items = [
		{"label": label, "value": count, "datatype": "Int"}
		for label, count in zip(LATENCY_LABELS, latency_counts, strict=True)
	]
	items.append(
		{"label": GATE_LABEL, "value": f"{gate.verdict} ({gate.correct}/{gate.labeled})", "datatype": "Data"}
	)
	return items


def label_outcome(prediction) -> tuple[bool, bool]:
	"""(labeled, correct) of one ticket's first successful `classify` row (AC-19, D-9).

	The label of each field in `CLASSIFICATION_FIELDS` is `created_labels[field]` when set, else
	`human_corrected_to[field]` when set, else there is none. Only fields with a label and a non-empty
	`predicted_<field>` are compared (a D/E ticket whose group the bot left empty is not wrong for it).
	No field to compare → not labeled; otherwise correct when every compared field is equal.
	"""
	created = _parse_labels(prediction.created_labels)
	corrected = _parse_labels(prediction.human_corrected_to)
	compared = []
	for field in CLASSIFICATION_FIELDS:
		predicted = prediction.get(f"predicted_{field}")
		label = created.get(field) or corrected.get(field)
		if predicted and label:
			compared.append(predicted == label)
	return bool(compared), bool(compared) and all(compared)


def _columns() -> list[dict]:
	return [
		{"fieldname": "category", "label": _("Category"), "fieldtype": "Data", "width": 120},
		{"fieldname": "predictions", "label": _("Predictions"), "fieldtype": "Int", "width": 110},
		{"fieldname": "labeled", "label": _("Labeled"), "fieldtype": "Int", "width": 110},
		{"fieldname": "correct", "label": _("Correct"), "fieldtype": "Int", "width": 110},
		{"fieldname": "accuracy_pct", "label": _("Accuracy (%)"), "fieldtype": "Percent", "width": 120},
		{"fieldname": "failed_runs", "label": _("Failed Runs"), "fieldtype": "Int", "width": 110},
	]


def _validate_dates(filters: dict):
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("From Date and To Date are required"))
	from_date, to_date = getdate(filters["from_date"]), getdate(filters["to_date"])
	if from_date > to_date:
		frappe.throw(_("From Date must not be after To Date"))
	return from_date, to_date


def _fetch_classify_rows(end: datetime) -> list:
	"""Every `classify` row with a ticket created before `end`, oldest first."""
	log = frappe.qb.DocType(LOG_DOCTYPE)
	return (
		frappe.qb.from_(log)
		.select(
			log.ticket,
			log.predicted_category,
			log.creation,
			log.created_labels,
			log.human_corrected_to,
			log.predicted_ticket_type,
			log.predicted_agent_group,
			log.predicted_priority,
		)
		.where(log.entry_type == "classify")
		# NULL != "" is not true, so this also drops rows whose ticket is NULL.
		.where(log.ticket != "")
		.where(log.creation < end)
		.orderby(log.creation)
		.orderby(log.name)
		.run(as_dict=True)
	)


def _first_predictions(rows: list, start: datetime) -> list:
	"""The first row with a predicted category of each ticket, when it was created at or after `start`."""
	return [row for row in _first_successes(rows) if get_datetime(row.creation) >= start]


def _first_successes(rows: list) -> list:
	"""The first row with a predicted category A-F of each ticket (`rows` oldest first)."""
	first = {}
	for row in rows:
		if row.predicted_category in CATEGORIES:
			first.setdefault(row.ticket, row)
	return list(first.values())


def _failed_runs(rows: list, start: datetime) -> int:
	succeeded = {row.ticket for row in rows if row.predicted_category}
	return len(
		{
			row.ticket
			for row in rows
			if not row.predicted_category
			and get_datetime(row.creation) >= start
			and row.ticket not in succeeded
		}
	)


def _parse_labels(raw) -> dict:
	try:
		parsed = json.loads(raw or "")
	except ValueError:
		return {}
	return parsed if isinstance(parsed, dict) else {}


def _accuracy_pct(row: dict) -> float | None:
	if not row["labeled"]:
		return None
	return round(row["correct"] / row["labeled"] * 100, 2)
