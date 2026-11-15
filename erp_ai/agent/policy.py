import os
import re
import unicodedata
from dataclasses import dataclass

import frappe
from frappe import _
from frappe.utils import add_months, get_datetime, now_datetime

from erp_ai.constants import (
	CATEGORIES,
	LEVELS,
	LOG_DOCTYPE,
	SETTING_DOCTYPE,
	TICKET_CONTENT_DOCTYPES,
	TRIGGER_COMMENT_MENTION,
	TRIGGER_TICKET_INSERT,
)

OPT_OUT_FIELD = "ai_opt_out"
EXCLUDED_TEAMS_FIELD = "excluded_teams"
TEAM_FIELD = "agent_group"
SUBJECT_FIELD = "subject"
SEND_POLICY_FIELDS = (OPT_OUT_FIELD, TEAM_FIELD, SUBJECT_FIELD)
EXCLUDED_BY_CLASSIFICATION = "excluded_by_classification"  # stop_reason of the classify row of such a ticket
# Refusal codes of send_refusal: codes only, never ticket content.
REFUSAL_OPTED_OUT = "opted_out"
REFUSAL_EXCLUDED_TEAM = "excluded_team"
REFUSAL_EXCLUDED_TITLE = "excluded_title"
REFUSAL_EXCLUDED_BY_CLASSIFICATION = "excluded_by_classification"
REFUSAL_MISSING = "missing"

OVER_BUDGET_LEVEL = "L1"


def is_enabled() -> bool:
	return bool(frappe.db.get_single_value(SETTING_DOCTYPE, "enabled"))


def _normalize(name) -> str:
	return " ".join((name or "").split()).casefold()


def is_excluded_by_classification(ticket_name: str) -> bool:
	"""The ticket has a classify row of ERP AI Log that stopped as EXCLUDED_BY_CLASSIFICATION."""
	return bool(
		ticket_name
		and frappe.db.exists(
			LOG_DOCTYPE,
			{"ticket": ticket_name, "entry_type": "classify", "stop_reason": EXCLUDED_BY_CLASSIFICATION},
		)
	)


def send_refusal(ticket) -> str | None:
	"""The only send predicate (ADR-034 QĐ 1): why the agent must not take this ticket, or None when it may.

	`ticket` is a name or a doc. First match wins: missing, opted out, excluded team, excluded title (with or
	without a team: the prefix is the creator's intent), excluded by classification (only while no team is
	set, so a person's team choice ends it).
	"""
	if not ticket:
		return REFUSAL_MISSING
	if isinstance(ticket, str):
		values = frappe.db.get_value(TICKET_DOCTYPE, ticket, ["name", *SEND_POLICY_FIELDS], as_dict=True)
		if not values:
			return REFUSAL_MISSING
	else:
		values = {field: ticket.get(field) for field in ("name", *SEND_POLICY_FIELDS)}
		is_new = getattr(ticket, "is_new", None)
		if callable(is_new) and is_new():
			values["name"] = None  # not saved yet: there is no log row to look up
	if values.get(OPT_OUT_FIELD):
		return REFUSAL_OPTED_OUT
	team = values.get(TEAM_FIELD)
	if is_excluded_team(team):
		return REFUSAL_EXCLUDED_TEAM
	if has_excluded_title(values.get(SUBJECT_FIELD)):
		return REFUSAL_EXCLUDED_TITLE
	if not (team or "").strip() and is_excluded_by_classification(values.get("name")):
		return REFUSAL_EXCLUDED_BY_CLASSIFICATION
	return None


def can_send_ticket(ticket) -> bool:
	"""The only send condition: send_refusal(ticket) is None."""
	return send_refusal(ticket) is None


def is_excluded_team(team) -> bool:
	"""True when the team is listed in excluded_teams (same normalization as can_send_ticket)."""
	team = _normalize(team)
	if not team:
		return False
	excluded = frappe.db.get_single_value(SETTING_DOCTYPE, EXCLUDED_TEAMS_FIELD) or ""
	return team in {_normalize(line) for line in excluded.splitlines()}


EXCLUDED_TITLE_PREFIXES_FIELD = "excluded_title_prefixes"


def _title_key(text) -> str:
	"""NFC, then the same spaces + casefold key as the team names."""
	return _normalize(unicodedata.normalize("NFC", text or ""))


def excluded_title_prefixes() -> tuple[str, ...]:
	"""Keys of the non-empty lines of excluded_title_prefixes; () when the field is missing (before migrate)."""
	# Checked on the meta: get_single_value would throw and leave its message in message_log (a red dialog).
	if not frappe.get_meta(SETTING_DOCTYPE).has_field(EXCLUDED_TITLE_PREFIXES_FIELD):
		return ()
	raw = frappe.db.get_single_value(SETTING_DOCTYPE, EXCLUDED_TITLE_PREFIXES_FIELD)
	return tuple(key for key in map(_title_key, (raw or "").splitlines()) if key)


def has_excluded_title(subject) -> bool:
	"""The title starts with an excluded prefix (only the start of the title counts)."""
	title = _title_key(subject)
	return any(title.startswith(prefix) for prefix in excluded_title_prefixes())


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


LEVEL_CAP_FIELD_PREFIX = "level_cap_"
UNKNOWN_CATEGORY_LEVEL = "L1"


def category_level_cap(settings, category: str | None) -> str:
	"""The only reader of level_cap_<x>; an unknown category, a missing field or a value outside LEVELS reads L1."""
	if category not in CATEGORIES:
		return UNKNOWN_CATEGORY_LEVEL
	cap = getattr(settings, LEVEL_CAP_FIELD_PREFIX + category.lower(), None)
	return cap if cap in LEVELS else UNKNOWN_CATEGORY_LEVEL


def main_path_level(settings, permission_level: str, category: str | None) -> str:
	"""The main-path level (AC-31): the smaller of the permission level and the category cap."""
	return min(permission_level, category_level_cap(settings, category), key=LEVELS.index)


CONFIDENCE_THRESHOLD_FIELD = "confidence_threshold"
DEFAULT_CONFIDENCE_THRESHOLD = 70


def _known_pct(value) -> int | None:
	"""An int 0..100 (not a bool) as is; anything else (-1, None, outside 0..100) is unknown: None."""
	if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 100:
		return value
	return None


def confidence_threshold(settings) -> int:
	"""The only reader of confidence_threshold; missing, empty, garbage or outside 0..100 reads the default."""
	value = getattr(settings, CONFIDENCE_THRESHOLD_FIELD, None)
	if isinstance(value, bool):
		return DEFAULT_CONFIDENCE_THRESHOLD
	try:
		threshold = _known_pct(int(value))
	except (TypeError, ValueError):
		threshold = None  # missing or not a number: behave like a fresh install
	return DEFAULT_CONFIDENCE_THRESHOLD if threshold is None else threshold


def is_below_confidence(
	confidence_pct: int | None, threshold: int, *, has_instructor: bool, act_now: bool
) -> bool:
	"""The single below-threshold predicate (ADR-030 QĐ 4): unknown is below, unless instructor AND act_now."""
	if has_instructor and act_now:
		return False
	pct = _known_pct(confidence_pct)
	return pct is None or pct < threshold


def latest_classification(ticket_name: str) -> tuple[str | None, int | None]:
	"""(predicted_category, pct) of the ticket's newest classify row with a category; (None, None) without one."""
	rows = frappe.get_all(
		LOG_DOCTYPE,
		filters={"ticket": ticket_name, "entry_type": "classify", "predicted_category": ("is", "set")},
		fields=["predicted_category", "predicted_confidence_pct"],
		order_by="creation desc",
		limit=1,
	)
	if not rows:
		return None, None
	return rows[0].predicted_category, _known_pct(rows[0].predicted_confidence_pct)


# The triggers whose runs count toward the daily limit (ADR-033 QĐ 4).
RUN_LIMIT_TRIGGERS = (TRIGGER_TICKET_INSERT, TRIGGER_COMMENT_MENTION)


def runs_today(ticket_name, now=None) -> int:
	"""Distinct run_id of classify/reason log entries of a RUN_LIMIT_TRIGGERS trigger since 00:00 today (system time)."""
	start = get_datetime(now or now_datetime()).replace(hour=0, minute=0, second=0, microsecond=0)
	rows = frappe.get_all(
		LOG_DOCTYPE,
		filters={
			"ticket": ticket_name,
			"entry_type": ("in", ("classify", "reason")),
			"trigger": ("in", RUN_LIMIT_TRIGGERS),
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


SITE_ENVIRONMENT_FIELD = "site_environment"
SITE_ENVIRONMENTS = ("production", "test")
DEFAULT_SITE_ENVIRONMENT = "production"


def site_environment(settings=None) -> str:
	"""The only reader of site_environment (ADR-031 QĐ 7); `settings` None reads the stored ERP AI Setting.
	Anything but an exact value of SITE_ENVIRONMENTS (missing, empty, unknown, other case) reads production."""
	if settings is None:
		settings = frappe.get_single(SETTING_DOCTYPE)
	value = getattr(settings, SITE_ENVIRONMENT_FIELD, None)
	return value if isinstance(value, str) and value in SITE_ENVIRONMENTS else DEFAULT_SITE_ENVIRONMENT


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
