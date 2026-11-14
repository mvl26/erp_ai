import os
import re
from dataclasses import dataclass

import frappe
from frappe import _
from frappe.utils import add_months, get_datetime, now_datetime

from erp_ai.constants import LEVELS, LOG_DOCTYPE, SETTING_DOCTYPE, TICKET_CONTENT_DOCTYPES

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
	return not is_excluded_team(values.get(TEAM_FIELD))


def is_excluded_team(team) -> bool:
	"""True when the team is listed in excluded_teams (same normalization as can_send_ticket)."""
	team = _normalize(team)
	if not team:
		return False
	excluded = frappe.db.get_single_value(SETTING_DOCTYPE, EXCLUDED_TEAMS_FIELD) or ""
	return team in {_normalize(line) for line in excluded.splitlines()}


def auto_assign_enabled(settings) -> bool:
	"""The only reader of the auto-assign switch; missing or 0 means off."""
	return bool(getattr(settings, "auto_assign_enabled", 0))


UNRESTRICTED_FIELD = "unrestricted_enabled"


def unrestricted_enabled(settings) -> bool:
	"""The only reader of the unrestricted switch; missing or 0 means off."""
	return bool(getattr(settings, UNRESTRICTED_FIELD, 0))


def contains_keyword(content) -> bool:
	keyword = frappe.db.get_single_value(SETTING_DOCTYPE, "trigger_keyword") or ""
	if not keyword:
		return False
	return keyword.casefold() in (content or "").casefold()


def get_trigger_keyword() -> str:
	return frappe.db.get_single_value(SETTING_DOCTYPE, "trigger_keyword") or ""


def month_spend_usd(now=None) -> float:
	"""Sum of cost_usd over every ERP AI Log row created in the month containing `now` (AC-61)."""
	start = get_datetime(now or now_datetime()).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
	end = add_months(start, 1)
	rows = frappe.db.sql(
		f"SELECT COALESCE(SUM(cost_usd), 0) FROM `tab{LOG_DOCTYPE}` WHERE creation >= %s AND creation < %s",
		(start, end),
	)
	return float(rows[0][0])


def is_over_budget(settings, now=None) -> bool:
	"""The month's live log spend is above monthly_budget_usd; spent_this_month_usd is not read."""
	return month_spend_usd(now) > (settings.monthly_budget_usd or 0)


def effective_level(settings, *, over_budget: bool) -> str:
	"""The only reader of permission_level; over budget caps at L1 but never raises L0."""
	level = settings.permission_level
	if over_budget:
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


CODE_CHANGE_ENABLED_FIELD = "code_change_enabled"
CODE_CHANGE_APPS_FIELD = "code_change_apps"
APP_NAME_PATTERN = re.compile(r"[A-Za-z0-9_-]+")
OWN_APP = "erp_ai"


@dataclass(frozen=True)
class ChangeSettings:
	enabled: bool
	allowed_apps: tuple[str, ...]


def _change_app_lines(raw) -> tuple[str, ...]:
	"""Stripped, non-blank lines of code_change_apps, first occurrence kept."""
	return tuple(dict.fromkeys(line.strip() for line in (raw or "").splitlines() if line.strip()))


def _app_name_error(name) -> str | None:
	if not APP_NAME_PATTERN.fullmatch(name):
		return _("Tên app '{0}' không hợp lệ").format(name)
	if name == OWN_APP:
		return _("Không được thêm erp_ai vào danh sách app được sửa")
	return None


def change_settings(settings) -> ChangeSettings:
	"""The only reader of the code-change switch and app list; names are kept as given (the tools refuse bad ones)."""
	return ChangeSettings(
		enabled=bool(getattr(settings, CODE_CHANGE_ENABLED_FIELD, 0)),
		allowed_apps=_change_app_lines(getattr(settings, CODE_CHANGE_APPS_FIELD, None)),
	)


def current_change_settings() -> ChangeSettings:
	"""Fresh read from the DB (no cache), for the change job."""
	fields = (CODE_CHANGE_ENABLED_FIELD, CODE_CHANGE_APPS_FIELD)
	return change_settings(
		frappe._dict(
			{field: frappe.db.get_single_value(SETTING_DOCTYPE, field, cache=False) for field in fields}
		)
	)


RECORD_TOOLS_FIELD = "record_tools_enabled"
ACT_NOW_FIELD = "act_now_enabled"
ONE_CLICK_APPROVAL_FIELD = "one_click_approval_enabled"
# The five permission switches in the spec's order (1)..(5).
PERMISSION_SWITCH_FIELDS = (
	UNRESTRICTED_FIELD,
	RECORD_TOOLS_FIELD,
	ACT_NOW_FIELD,
	CODE_CHANGE_ENABLED_FIELD,
	ONE_CLICK_APPROVAL_FIELD,
)


@dataclass(frozen=True)
class PermissionSwitches:
	unrestricted: bool = False  # (1)
	record_tools: bool = False  # (2)
	act_now: bool = False  # (3)
	code_change: bool = False  # (4)
	one_click_approval: bool = False  # (5)


def permission_switches(settings) -> PermissionSwitches:
	"""The only reader of the five permission switches; a missing field (before migrate) means off."""
	return PermissionSwitches(
		unrestricted=unrestricted_enabled(settings),
		record_tools=bool(getattr(settings, RECORD_TOOLS_FIELD, 0)),
		act_now=bool(getattr(settings, ACT_NOW_FIELD, 0)),
		code_change=change_settings(settings).enabled,
		one_click_approval=bool(getattr(settings, ONE_CLICK_APPROVAL_FIELD, 0)),
	)


def validate_change_apps(settings, apps_root: str) -> None:
	"""Raise frappe.ValidationError for a bad name or erp_ai (every line), then for a missing `apps_root`/<x> directory."""
	apps = _change_app_lines(getattr(settings, CODE_CHANGE_APPS_FIELD, None))
	for name in apps:
		error = _app_name_error(name)
		if error:
			frappe.throw(error)
	for name in apps:
		if not os.path.isdir(os.path.join(apps_root, name)):
			frappe.throw(_("Không có thư mục apps/{0}").format(name))


TICKET_DOCTYPE = "HD Ticket"


def _stored_doctype_name(doctype) -> str | None:
	"""The DocType's stored name (the collation matches "comment" to Comment), or None when there is none."""
	return frappe.db.get_value("DocType", doctype, "name")


def ticket_link_fieldnames(doctype: str) -> tuple[str, ...]:
	"""Fields of this DocType (Custom Fields included, meta order) that Link to HD Ticket; () for HD Ticket itself
	and for a missing DocType."""
	name = _stored_doctype_name(doctype)
	if not name or name == TICKET_DOCTYPE:
		return ()
	return tuple(
		field.fieldname
		for field in frappe.get_meta(name).fields
		if field.fieldtype == "Link" and field.options == TICKET_DOCTYPE
	)


def is_ticket_content_doctype(doctype: str) -> bool:
	"""ADR-034: a DocType of TICKET_CONTENT_DOCTYPES or one with a Link to HD Ticket carries ticket content."""
	name = _stored_doctype_name(doctype)
	return bool(name) and (name in TICKET_CONTENT_DOCTYPES or bool(ticket_link_fieldnames(name)))
