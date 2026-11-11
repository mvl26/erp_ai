import frappe
from frappe.utils import get_datetime, now_datetime

from erp_ai.constants import LEVELS, LOG_DOCTYPE, SETTING_DOCTYPE

OPT_OUT_FIELD = "ai_opt_out"
EXCLUDED_TEAMS_FIELD = "excluded_teams"
TEAM_FIELD = "agent_group"
SEND_POLICY_FIELDS = (OPT_OUT_FIELD, TEAM_FIELD)

OVER_BUDGET_LEVEL = "L1"


def is_enabled() -> bool:
	return bool(frappe.db.get_single_value(SETTING_DOCTYPE, "enabled"))


def _normalize(name) -> str:
	return " ".join((name or "").split()).casefold()


def can_send_ticket(ticket) -> bool:
	"""The only send condition: not opted out and not in an excluded team."""
	if not ticket:
		return False
	if isinstance(ticket, str):
		values = frappe.db.get_value("HD Ticket", ticket, list(SEND_POLICY_FIELDS), as_dict=True)
		if not values:
			return False
	else:
		values = {field: ticket.get(field) for field in SEND_POLICY_FIELDS}
	if values.get(OPT_OUT_FIELD):
		return False
	team = _normalize(values.get(TEAM_FIELD))
	if not team:
		return True
	excluded = frappe.db.get_single_value(SETTING_DOCTYPE, EXCLUDED_TEAMS_FIELD) or ""
	return team not in {_normalize(line) for line in excluded.splitlines()}


def contains_keyword(content) -> bool:
	keyword = frappe.db.get_single_value(SETTING_DOCTYPE, "trigger_keyword") or ""
	if not keyword:
		return False
	return keyword.casefold() in (content or "").casefold()


def effective_level(settings) -> str:
	"""The only reader of permission_level; over budget caps at L1 but never raises L0."""
	level = settings.permission_level
	if (settings.spent_this_month_usd or 0) > (settings.monthly_budget_usd or 0):
		return min(level, OVER_BUDGET_LEVEL, key=LEVELS.index)
	return level


def runs_today(ticket_name, now=None) -> int:
	"""Distinct run_id of classify/reason log entries since 00:00 today (system time)."""
	start = get_datetime(now or now_datetime()).replace(hour=0, minute=0, second=0, microsecond=0)
	rows = frappe.get_all(
		LOG_DOCTYPE,
		filters={
			"ticket": ticket_name,
			"entry_type": ("in", ("classify", "reason")),
			"creation": (">=", start),
		},
		pluck="run_id",
	)
	return len(set(rows))
