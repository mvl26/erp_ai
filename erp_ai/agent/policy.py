import os
import re
import unicodedata
from dataclasses import dataclass

import frappe
from frappe import _
from frappe.utils import add_months, cint, get_datetime, now_datetime

from erp_ai.agent.authority import NEVER_AUTHORITY
from erp_ai.agent.text_lines import filled_lines
from erp_ai.constants import (
	CATEGORIES,
	LEVELS,
	LOG_DOCTYPE,
	ROLE_INSTRUCTOR,
	SETTING_DOCTYPE,
	TICKET_CONTENT_DOCTYPES,
	TRIGGER_COMMENT_MENTION,
	TRIGGER_REQUESTER_REPLY,
	TRIGGER_SUPPORT_CHAT,
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


def _like_core(key: str) -> str:
	"""A LIKE pattern that matches every subject whose normalized start is `key`, and a few more.

	Words are joined with `%` so a subject with other spaces still matches. `%`, `_` and `\\` in the key are
	left as they are: frappe's `like` filter treats a backslash literally and gives no way to escape `%` or
	`_` (checked on this site), so they only widen the candidates; send_refusal then drops the extras.
	"""
	return "%" + "%".join(key.split()) + "%"


def excluded_team_names() -> list[str]:
	"""Names of the real HD Teams listed in excluded_teams (same comparison as is_excluded_team)."""
	excluded = frappe.db.get_single_value(SETTING_DOCTYPE, EXCLUDED_TEAMS_FIELD) or ""
	keys = {_normalize(line) for line in excluded.splitlines()} - {""}
	if not keys:
		return []
	return [name for name in frappe.get_all("HD Team", pluck="name") if _normalize(name) in keys]


def excluded_ticket_names() -> list:
	"""Names of the HD Tickets that send_refusal refuses: the query form of the send predicate.

	Step 1 selects a superset with one frappe.get_all (an OR of the rules; the optional arms only when their
	set is not empty); step 2 keeps the rows the predicate itself refuses, so the two forms cannot differ.
	A database error is raised to the caller.
	"""
	or_filters = [[OPT_OUT_FIELD, "=", 1]]
	if teams := excluded_team_names():
		or_filters.append([TEAM_FIELD, "in", teams])
	or_filters.extend([SUBJECT_FIELD, "like", _like_core(prefix)] for prefix in excluded_title_prefixes())
	classified = frappe.get_all(
		LOG_DOCTYPE,
		filters={"entry_type": "classify", "stop_reason": EXCLUDED_BY_CLASSIFICATION},
		pluck="ticket",
		distinct=True,
	)
	if classified := [name for name in classified if name]:
		or_filters.append(["name", "in", classified])
	rows = frappe.get_all(TICKET_DOCTYPE, or_filters=or_filters, fields=["name", *SEND_POLICY_FIELDS])
	return [row.name for row in rows if send_refusal(row) is not None]


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
RUN_LIMIT_TRIGGERS = (
	TRIGGER_TICKET_INSERT,
	TRIGGER_COMMENT_MENTION,
	TRIGGER_REQUESTER_REPLY,
	TRIGGER_SUPPORT_CHAT,
)


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
CONSOLE_FIELD = "console_enabled"
# The permission switches in the order of the settings section (section_permissions).
# BUG-008: console is one of them: its change is logged and it is listed in the daily privilege alarm.
PERMISSION_SWITCH_FIELDS = (
	UNRESTRICTED_FIELD,
	RECORD_TOOLS_FIELD,
	ACT_NOW_FIELD,
	CODE_CHANGE_ENABLED_FIELD,
	CONSOLE_FIELD,
	ONE_CLICK_APPROVAL_FIELD,
)
# Field -> the PermissionSwitches attribute that reads it; consumers pair by this name, never by position.
SWITCH_FLAGS = {
	UNRESTRICTED_FIELD: "unrestricted",
	RECORD_TOOLS_FIELD: "record_tools",
	ACT_NOW_FIELD: "act_now",
	CODE_CHANGE_ENABLED_FIELD: "code_change",
	CONSOLE_FIELD: "console",
	ONE_CLICK_APPROVAL_FIELD: "one_click_approval",
}


@dataclass(frozen=True)
class PermissionSwitches:
	unrestricted: bool = False  # (1)
	record_tools: bool = False  # (2)
	act_now: bool = False  # (3)
	code_change: bool = False  # (4)
	one_click_approval: bool = False  # (5)
	console: bool = False  # CHG-010: bench console proposals, independent of code_change


def permission_switches(settings) -> PermissionSwitches:
	"""The only reader of the permission switches; a missing field (before migrate) means off."""
	return PermissionSwitches(
		unrestricted=unrestricted_enabled(settings),
		record_tools=bool(getattr(settings, RECORD_TOOLS_FIELD, 0)),
		act_now=bool(getattr(settings, ACT_NOW_FIELD, 0)),
		code_change=change_settings(settings).enabled,
		one_click_approval=bool(getattr(settings, ONE_CLICK_APPROVAL_FIELD, 0)),
		console=bool(cint(getattr(settings, CONSOLE_FIELD, 0))),  # a Single without meta gives "0"
	)


def console_enabled_now() -> bool:
	"""Fresh read of the console switch from the DB (no cache), for the apply job.

	Reads `tabSingles` directly: the DocType meta of a site not yet migrated does not know the field, and
	`get_single_value` checks the meta. A missing row reads off."""
	value = frappe.db.sql(
		"select value from `tabSingles` where doctype=%s and field=%s", (SETTING_DOCTYPE, CONSOLE_FIELD)
	)
	return permission_switches(frappe._dict({CONSOLE_FIELD: value[0][0] if value else 0})).console


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


EXCLUDED_TICKET_REASON = "bản ghi thuộc phiếu không được phép đưa cho AI"
# DocType that names its ticket by (type column, name column) pairs -> the pairs, each enough alone. R11d:
# ticket_link_columns adds every (Link to DocType, Dynamic Link) pair of the live meta, so only a pair whose name
# column is not a Dynamic Link has to be listed here (File, Email Queue, Notification Log's document pair); the
# other entries are derived too and stay as pins that hold whatever the meta says.
TICKET_LINK_FIELDS = {
	"Comment": (("reference_doctype", "reference_name"),),
	"Communication": (("reference_doctype", "reference_name"),),
	"File": (("attached_to_doctype", "attached_to_name"),),
	# R10b, R10g, R11a: column names of the installed DocType JSON, every pair of the DocType. Version is refused by
	# the record tool instead (R10e).
	"ToDo": (("reference_type", "reference_name"),),
	"Notification Log": (("document_type", "document_name"), ("source_doctype", "source_name")),
	"Activity Log": (
		("reference_doctype", "reference_name"),
		("timeline_doctype", "timeline_name"),
		("link_doctype", "link_name"),
	),
	"Email Queue": (("reference_doctype", "reference_name"),),
	# R11a: Frappe's add_tag, which Helpdesk tags tickets with, stores the ticket subject in the Tag Link title.
	"Tag Link": (("document_type", "document_name"),),
	"Document Follow": (("ref_doctype", "ref_docname"),),
	"Workflow Action": (("reference_doctype", "reference_name"),),
	"Reminder": (("reminder_doctype", "reminder_docname"),),
}
# Records of a ticket that hold records of their own (R10a): Helpdesk keeps comment attachments on the Comment and
# email attachments on the Communication, and Frappe points an "Attachment" Comment at its Comment. A record whose
# dynamic pair or Link (R10g: Email Queue's `communication`) names one of them belongs to that record's tickets (one
# hop, no deeper). Helpdesk's legacy note DocType is a known gap (R10f): D8 bars naming it.
TICKET_PARENT_DOCTYPES = ("Comment", "Communication")
# Column values that name no record.
EMPTY_LINK_VALUES = (None, "", [])


def ticket_link_columns(doctype: str) -> tuple[tuple[str | None, str], ...]:
	"""Every column that points a record of this DocType at a ticket: its dynamic pairs, each once, plus
	`(None, fieldname)` for each Link to HD Ticket; () for HD Ticket and for a missing DocType. The dynamic pairs are
	its entries of TICKET_LINK_FIELDS, then (R11d) each `(Link to DocType, Dynamic Link whose options name that
	Link)` of the live meta, Custom Fields included, meta order. The one reader of TICKET_LINK_FIELDS (C-U2-1)."""
	name = _stored_doctype_name(doctype)
	if not name or name == TICKET_DOCTYPE:
		return ()
	fields = frappe.get_meta(name).fields
	type_columns = {
		field.fieldname for field in fields if field.fieldtype == "Link" and field.options == "DocType"
	}
	derived = (
		(field.options, field.fieldname)
		for field in fields
		if field.fieldtype == "Dynamic Link" and field.options in type_columns
	)
	pairs = dict.fromkeys((*TICKET_LINK_FIELDS.get(name, ()), *derived))
	return (*pairs, *((None, field) for field in ticket_link_fieldnames(name)))


def parent_link_fields(doctype: str) -> tuple[tuple[str, str], ...]:
	"""`(fieldname, DocType)` of each field of this DocType (Custom Fields included, meta order) that Links to a
	DocType of TICKET_PARENT_DOCTYPES (R10g); () for a missing DocType."""
	name = _stored_doctype_name(doctype)
	if not name:
		return ()
	return tuple(
		(field.fieldname, field.options)
		for field in frappe.get_meta(name).fields
		if field.fieldtype == "Link" and field.options in TICKET_PARENT_DOCTYPES
	)


def link_column_names(doctype: str) -> list[str]:
	"""Every column of ticket_link_columns and parent_link_fields of this DocType, each once, in that order."""
	columns = [column for pair in ticket_link_columns(doctype) for column in pair if column]
	return list(dict.fromkeys([*columns, *(field for field, _parent in parent_link_fields(doctype))]))


def _excluded_parent_names(names: list) -> list:
	"""Names of the records of TICKET_PARENT_DOCTYPES that point at one of the tickets `names` (one hop)."""
	found = []
	for parent in TICKET_PARENT_DOCTYPES:
		for type_column, name_column in ticket_link_columns(parent):
			filters = {name_column: ["in", names]}
			if type_column:
				filters[type_column] = TICKET_DOCTYPE
			found.extend(frappe.get_all(parent, filters=filters, pluck="name"))
	return list(dict.fromkeys(found))


def _rows_naming(doctype: str, pairs, owners: list) -> list:
	"""Names of the rows of this DocType whose type column, for one of the dynamic `pairs`, is HD Ticket or a DocType
	of TICKET_PARENT_DOCTYPES and whose name column is one of `owners`."""
	rows = []
	for type_column, name_column in pairs:
		filters = {
			type_column: ["in", [TICKET_DOCTYPE, *TICKET_PARENT_DOCTYPES]],
			name_column: ["in", owners],
		}
		rows.extend(frappe.get_all(doctype, filters=filters, pluck="name"))
	return list(dict.fromkeys(rows))


def ticket_content_filters(doctype: str) -> tuple[list, list]:
	"""`(filters, or_filters)` for frappe.get_list that hide the records of excluded tickets; ([], []) when no
	column of the DocType points at a ticket (ticket_link_columns, parent_link_fields) or no ticket is excluded.
	The OR group keeps a row whose first dynamic pair names neither a ticket nor a record of TICKET_PARENT_DOCTYPES,
	or names one that is neither an excluded ticket nor a record of one (R10a). get_list takes one OR group, so the
	rows another pair points at one of those are left out by name, and a Link to a DocType of
	TICKET_PARENT_DOCTYPES must name none of those records (R10g)."""
	name = _stored_doctype_name(doctype)
	columns = ticket_link_columns(name) if name else ()
	parents = parent_link_fields(name) if name else ()
	if not (name == TICKET_DOCTYPE or columns or parents) or not (names := excluded_ticket_names()):
		return [], []
	if name == TICKET_DOCTYPE:
		return [["name", "not in", names]], []
	filters = [[name_column, "not in", names] for type_column, name_column in columns if not type_column]
	pairs = [pair for pair in columns if pair[0]]
	if not (pairs or parents):
		return filters, []
	parent_names = _excluded_parent_names(names)
	owners = [*names, *parent_names]
	or_filters = []
	if pairs:
		(type_column, name_column), *others = pairs
		or_filters = [
			[type_column, "not in", [TICKET_DOCTYPE, *TICKET_PARENT_DOCTYPES]],
			[name_column, "not in", owners],
		]
		if rows := _rows_naming(name, others, owners):
			filters.append(["name", "not in", rows])
	# An empty `not in` list would hide every empty Link (frappe compares ifnull(column, '') with '').
	if parent_names:
		filters.extend([field, "not in", parent_names] for field, _parent in parents)
	return filters, or_filters


def _doctype_of(value) -> str | None:
	"""The stored name of the DocType a type column holds (the collation matches "comment" to Comment), or None."""
	if value == TICKET_DOCTYPE or value in TICKET_PARENT_DOCTYPES:
		return value
	return _stored_doctype_name(value) if isinstance(value, str) and value else None


def _records_named(doctype: str, values) -> list[tuple[str, str]]:
	"""`(DocType, name)` of each record that `values` (columns of a record of this DocType, stored or about to be
	written) name over link_column_names: HD Ticket for a static Link of ticket_link_columns, the type column's
	DocType for a dynamic pair, the Link's DocType for one of parent_link_fields. Names as text."""
	named = [
		(_doctype_of(values.get(type_column)) if type_column else TICKET_DOCTYPE, values.get(name_column))
		for type_column, name_column in ticket_link_columns(doctype)
	]
	named += [(parent, values.get(field)) for field, parent in parent_link_fields(doctype)]
	return [(kind, str(linked)) for kind, linked in named if kind and linked not in EMPTY_LINK_VALUES]


def _linked_records(doctype: str, name) -> list[tuple[str, str]]:
	"""_records_named of the stored record."""
	fields = link_column_names(doctype)
	if not fields:
		return []
	values = frappe.db.get_value(doctype, name, fields, as_dict=True)
	return _records_named(doctype, values) if values else []


def _tickets_of(kind: str, linked) -> list:
	"""The tickets a linked record stands for: the ticket itself, or the tickets a record of TICKET_PARENT_DOCTYPES
	points at (R10a: one hop, no deeper); [] for a record of any other DocType."""
	if kind == TICKET_DOCTYPE:
		return [linked]
	if kind in TICKET_PARENT_DOCTYPES:
		return [ticket for owner, ticket in _linked_records(kind, linked) if owner == TICKET_DOCTYPE]
	return []


def _tickets_named(records) -> list[str]:
	"""The tickets the `(DocType, name)` records stand for (_tickets_of), first seen first."""
	return list(dict.fromkeys(ticket for kind, record in records for ticket in _tickets_of(kind, record)))


def linked_tickets(doctype: str, values) -> list[str]:
	"""Names of the tickets `values` (columns of a record of this DocType about to be written) point at, the same
	way as a stored record (R10h)."""
	return _tickets_named(_records_named(doctype, values))


def _owning_tickets(doctype: str, name: str) -> list[str]:
	"""Names of the tickets this record points at, over every column of link_column_names, first seen first."""
	stored = _stored_doctype_name(doctype)
	if not stored or not name:
		return []
	if stored == TICKET_DOCTYPE:
		return [name] if frappe.db.exists(TICKET_DOCTYPE, name) else []
	return _tickets_named(_linked_records(stored, name))


def owning_ticket(doctype: str, name: str) -> str | None:
	"""The ticket a record belongs to (the first column that names one), None when there is none."""
	tickets = _owning_tickets(doctype, name)
	return tickets[0] if tickets else None


def is_ticket_record_excluded(doctype: str, name: str) -> bool:
	"""True when any ticket the record points at fails can_send_ticket."""
	return any(not can_send_ticket(ticket) for ticket in _owning_tickets(doctype, name))


# FEAT-008: the lesson store. The only readers of the lesson switches, caps and who may decide on a lesson.
LESSON_SCAN_MAX = 500
LESSONS_MAX_RANGE = (1, 20)
# R13: the smallest cap still holds one lesson of the largest size (situation 300 + text 1000 characters).
LESSONS_CHARS_RANGE = (1300, 20000)
DEFAULT_LESSONS_MAX = 5
DEFAULT_LESSONS_CHARS = 2000
LESSONS_ENABLED_FIELD = "lessons_enabled"
LESSONS_MAX_FIELD = "lessons_max_per_request"
LESSONS_CHARS_FIELD = "lessons_max_chars"
LESSON_TEACH_MARKER_FIELD = "lesson_teach_marker"
APPROVER_ROLE = "System Manager"


@dataclass(frozen=True)
class LessonSettings:
	enabled: bool
	max_lessons: int
	max_chars: int
	scan_max: int


def _in_range(value, bounds: tuple[int, int], default: int) -> int:
	"""`value` as an int inside `bounds`; missing, garbage or out of range reads `default`."""
	if isinstance(value, bool):
		return default
	try:
		number = int(value)
	except (TypeError, ValueError):
		return default
	return number if bounds[0] <= number <= bounds[1] else default


def lesson_settings(settings) -> LessonSettings:
	"""The lesson switch and caps of a Setting doc; a cap that is missing or out of range reads its default."""
	return LessonSettings(
		enabled=bool(getattr(settings, LESSONS_ENABLED_FIELD, 0)),
		max_lessons=_in_range(
			getattr(settings, LESSONS_MAX_FIELD, None), LESSONS_MAX_RANGE, DEFAULT_LESSONS_MAX
		),
		max_chars=_in_range(
			getattr(settings, LESSONS_CHARS_FIELD, None), LESSONS_CHARS_RANGE, DEFAULT_LESSONS_CHARS
		),
		scan_max=LESSON_SCAN_MAX,
	)


def lessons_enabled() -> bool:
	"""One value read of the lesson switch, for the sources that write lessons; missing means off."""
	return bool(frappe.db.get_single_value(SETTING_DOCTYPE, LESSONS_ENABLED_FIELD))


def lesson_teach_marker() -> str:
	"""The stripped teaching marker; blank means teaching by message is off."""
	return (frappe.db.get_single_value(SETTING_DOCTYPE, LESSON_TEACH_MARKER_FIELD) or "").strip()


def is_lesson_approver(user: str | None) -> bool:
	"""A-2: a listed monthly reviewer or a System Manager may approve a lesson; never the system accounts."""
	if not user or user in NEVER_AUTHORITY:
		return False
	if user in filled_lines(frappe.db.get_single_value(SETTING_DOCTYPE, "monthly_reviewers")):
		return True
	return APPROVER_ROLE in frappe.get_roles(user)


def can_manage_lessons(user: str | None) -> bool:
	"""D-3: only an ERP AI Instructor may turn a lesson off or on; never the system accounts."""
	if not user or user in NEVER_AUTHORITY:
		return False
	return ROLE_INSTRUCTOR in frappe.get_roles(user)


def lesson_limit_errors(settings) -> list[str]:
	"""One Vietnamese message per lesson cap that is set but does not read as an int inside its range.

	A cap that is not set (None or "") gives no message, and the reader uses the default. A cap gives one when
	`int()` of it fails (text), when it is a bool, or when its int is out of range, 0 included: 0 is what Frappe
	stores for an Int field emptied on the form, so the next save of the form is refused until the cap is filled.
	"""
	errors = []
	for fieldname, label, bounds in (
		(LESSONS_MAX_FIELD, "Số bài tối đa mỗi lần gọi", LESSONS_MAX_RANGE),
		(LESSONS_CHARS_FIELD, "Số ký tự bài học tối đa mỗi lần gọi", LESSONS_CHARS_RANGE),
	):
		value = getattr(settings, fieldname, None)
		if value in (None, ""):
			continue
		if _in_range(value, bounds, bounds[0] - 1) == bounds[0] - 1:
			errors.append(f"{label} phải từ {bounds[0]} đến {bounds[1]}")
	return errors
