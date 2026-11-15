from datetime import datetime, timedelta

import frappe
from frappe.utils import get_datetime

from erp_ai.agent import policy
from erp_ai.constants import AGENT_USER, CLASSIFICATION_FIELDS, LOG_DOCTYPE, SETTING_DOCTYPE

SCAN_BATCH = 50
SCAN_GRACE_MIN = 5

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
	order by t.creation asc, t.name asc
"""


def _agent_enabled_at():
	"""The raw stored value: get_single_value would turn an unset Datetime into year 1."""
	stored = frappe.db.sql(
		"select value from `tabSingles` where doctype=%s and field='agent_enabled_at'", SETTING_DOCTYPE
	)
	return get_datetime(stored[0][0]) if stored and stored[0][0] else None


def find_missed_tickets(now: datetime) -> list[str]:
	"""Tickets whose classification run was missed (AC-16, D-16, A-D3), oldest first, at most SCAN_BATCH."""
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
		},
		pluck=True,
	)
	found = []
	for name in candidates:
		name = str(name)
		if policy.can_send_ticket(name) and policy.runs_today(name, now) < max_runs:
			found.append(name)
			if len(found) == SCAN_BATCH:
				break
	return found
