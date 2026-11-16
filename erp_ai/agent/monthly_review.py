"""The monthly random review of tickets (design 3.6.5, AC-59, D-10, ADR-033 QĐ 6).

On the 1st at 08:00 the job fixes a sample of the tickets the bot wrote on in the month before, as one
`ERP AI Review Month` row named `REV-<YYYY-MM>`; the same month always gives the same sample. A month that
already has its row, or an older month that has none, is left alone.
"""

import random
from datetime import date, datetime

import frappe
from frappe.utils import add_months, get_datetime, get_first_day, get_last_day, get_url, now_datetime
from frappe.utils.file_lock import LockTimeoutError
from frappe.utils.synchronization import filelock

from erp_ai.agent import policy
from erp_ai.agent.kpi import log_actions
from erp_ai.agent.ops_data import monthly_cycle
from erp_ai.agent.text_lines import filled_lines
from erp_ai.constants import LOG_DOCTYPE, LOGGER_NAME, SETTING_DOCTYPE

REVIEW_MONTH_DOCTYPE = "ERP AI Review Month"
LOCK_NAME = "erp_ai_monthly_review"
LOCK_TIMEOUT_S = 5
TITLE_REVIEW_FAILED = "erp_ai: rà soát tháng lỗi"
SUBJECT_FORMAT = "[erp_ai] Danh sách rà soát {month}"


def _month_start(month: str) -> date:
	return get_first_day(date(int(month[:4]), int(month[5:7]), 1))


def review_candidates(month: str) -> list[str]:
	"""Names of the tickets with at least one bot write in `month` (`YYYY-MM`), sorted by name.

	A bot write is a `classify` row with `applied` set, or a row whose `actions` has an `ok` entry. A ticket
	the send predicate refuses (excluded, opted out, gone) is left out.
	"""
	start = _month_start(month)
	rows = frappe.get_all(
		LOG_DOCTYPE,
		filters=[
			["creation", ">=", datetime.combine(start, datetime.min.time())],
			["creation", "<", datetime.combine(add_months(start, 1), datetime.min.time())],
			["ticket", "is", "set"],
		],
		fields=["ticket", "entry_type", "applied", "actions"],
	)
	touched = {
		row.ticket
		for row in rows
		if (row.entry_type == "classify" and row.applied)
		or any(action.get("ok") is True for action in log_actions(row.actions))
	}
	return sorted(name for name in touched if policy.can_send_ticket(name))


def pick_sample(candidates: list[str], month: str, size: int) -> list[str]:
	"""`min(size, len(candidates))` names, fixed by `month` alone (same month, same set, any run time)."""
	return random.Random(month).sample(candidates, min(size, len(candidates)))


def run_monthly_review(now: datetime | None = None) -> None:
	"""Create the review row of the month before the cycle `now` belongs to, once; mail the reviewers.

	The row and the email are one transaction: a failure rolls the row back, is logged, and the next run
	starts again. Nothing leaves this function as an error.
	"""
	logger = frappe.logger(LOGGER_NAME)
	try:
		with filelock(LOCK_NAME, timeout=LOCK_TIMEOUT_S):
			_run_locked(get_datetime(now) if now else now_datetime(), logger)
	except LockTimeoutError:
		logger.info("monthly_review: lock busy")


def _run_locked(now: datetime, logger) -> None:
	cycle = _month_start(monthly_cycle(now))
	start = add_months(cycle, -1)
	month = f"{start:%Y-%m}"
	if frappe.db.exists(REVIEW_MONTH_DOCTYPE, f"REV-{month}"):
		logger.info("monthly_review: %s already has its row", month)
		return
	frappe.db.savepoint(LOCK_NAME)
	try:
		candidates = review_candidates(month)
		size = frappe.db.get_single_value(SETTING_DOCTYPE, "review_sample_size")
		picked = pick_sample(candidates, month, size)
		doc = frappe.get_doc(
			{
				"doctype": REVIEW_MONTH_DOCTYPE,
				"month": month,
				"period_start": start,
				"period_end": get_last_day(start),
				"candidate_count": len(candidates),
				"items": [{"ticket": name} for name in picked],
			}
		).insert(ignore_permissions=True)
		reviewers = list(
			dict.fromkeys(filled_lines(frappe.db.get_single_value(SETTING_DOCTYPE, "monthly_reviewers")))
		)
		if reviewers:
			frappe.sendmail(
				recipients=reviewers,
				subject=SUBJECT_FORMAT.format(month=month),
				message=_message(month, len(picked), doc.name),
				delayed=True,
			)
	except frappe.DuplicateEntryError:
		frappe.db.rollback(save_point=LOCK_NAME)
		logger.info("monthly_review: %s already has its row", month)
		return
	except Exception as exc:
		frappe.db.rollback(save_point=LOCK_NAME)
		frappe.log_error(TITLE_REVIEW_FAILED, f"month={month} error={type(exc).__name__}")
		return
	logger.info(
		"erp_ai monthly_review: %s, %s of %s tickets picked, %s reviewers",
		month,
		len(picked),
		len(candidates),
		len(reviewers),
	)


def _message(month: str, count: int, name: str) -> str:
	link = get_url(f"/app/erp-ai-review-month/{name}")
	return f'<p>Kỳ rà soát {month}: {count} phiếu cần rà.</p><p><a href="{link}">{link}</a></p>'
