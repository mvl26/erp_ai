from datetime import datetime, timedelta

import frappe
from frappe.utils import get_datetime, now_datetime

from erp_ai.agent import policy, queue
from erp_ai.constants import (
	AGENT_USER,
	CLASSIFICATION_FIELDS,
	LOG_DOCTYPE,
	LOGGER_NAME,
	SETTING_DOCTYPE,
	TITLE_RUN_FAILED,
	TRIGGER_TICKET_INSERT,
)

SCAN_BATCH = 50
SCAN_GRACE_MIN = 5
SCAN_CANDIDATE_LIMIT = 1000

_ANY_FIELD_EMPTY = " or ".join(f"ifnull(t.`{field}`, '') = ''" for field in CLASSIFICATION_FIELDS)
CANDIDATES_SQL = f"""
	select t.name
	from `tabHD Ticket` t
	where t.creation > %(enabled_at)s
		and t.creation <= %(cutoff)s
		and ifnull(t.status_category, '') != 'Resolved'
		and t.owner != %(agent_user)s
		and ({_ANY_FIELD_EMPTY})
		and not exists (
			select 1 from `tab{LOG_DOCTYPE}` l
			where l.ticket = t.name and l.entry_type = 'classify' and ifnull(l.predicted_category, '') != ''
		)
	order by t.creation desc, t.name desc
	limit %(limit)s
"""


def _agent_enabled_at():
	"""The raw stored value: get_single_value would turn an unset Datetime into year 1."""
	stored = frappe.db.sql(
		"select value from `tabSingles` where doctype=%s and field='agent_enabled_at'", SETTING_DOCTYPE
	)
	return get_datetime(stored[0][0]) if stored and stored[0][0] else None


def find_missed_tickets(now: datetime) -> list[str]:
	"""Tickets whose classification run was missed (AC-16, D-16, A-D3), oldest first, at most SCAN_BATCH.

	Only the SCAN_CANDIDATE_LIMIT newest candidates are considered (design-w1-fixes-6 Điểm 2).
	"""
	enabled_at = _agent_enabled_at()
	if not enabled_at:
		return []
	max_runs = frappe.db.get_single_value(SETTING_DOCTYPE, "max_runs_per_ticket_per_day", cache=False)
	candidates = frappe.db.sql(
		CANDIDATES_SQL,
		{
			"enabled_at": enabled_at,
			"cutoff": get_datetime(now) - timedelta(minutes=SCAN_GRACE_MIN),
			"agent_user": AGENT_USER,
			"limit": SCAN_CANDIDATE_LIMIT,
		},
		pluck=True,
	)
	if len(candidates) == SCAN_CANDIDATE_LIMIT:
		frappe.logger(LOGGER_NAME).warning(
			"missed_scan: chạm trần %s ứng viên, phiếu cũ hơn không được xét", SCAN_CANDIDATE_LIMIT
		)
	found = []
	for name in reversed(candidates):
		name = str(name)
		if policy.can_send_ticket(name) and policy.runs_today(name, now) < max_runs:
			found.append(name)
			if len(found) == SCAN_BATCH:
				break
	return found


def scan_missed_tickets(now: datetime | None = None) -> None:
	"""The 15-minute cron (AC-16, ADR-033 QĐ 2): re-queue missed tickets as a ticket_insert run.

	One logger line per run; an error ends the run with one constant-title log_error (D-17).
	"""
	logger = frappe.logger(LOGGER_NAME)
	queued = 0
	try:
		if not policy.is_enabled():
			logger.info("missed_scan: agent tắt, bỏ qua")
			return
		for name in find_missed_tickets(now or now_datetime()):
			if queue.enqueue_agent_run(name, TRIGGER_TICKET_INSERT):
				queued += 1
	except Exception as exc:
		frappe.log_error(TITLE_RUN_FAILED, f"missed_scan error={type(exc).__name__}")
		logger.error("missed_scan: lỗi %s, đã xếp %s phiếu", type(exc).__name__, queued)
		return
	logger.info(f"missed_scan: xếp {queued} phiếu")
