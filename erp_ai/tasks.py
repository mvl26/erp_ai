import json
from collections import Counter
from datetime import datetime, timedelta

import frappe
from frappe.permissions import AUTOMATIC_ROLES
from frappe.query_builder.functions import Sum
from frappe.utils import add_months, get_datetime, now_datetime

from erp_ai import alerts, gateway
from erp_ai.agent.runner import GENERIC_WRITE_TOOLS
from erp_ai.agent.tools.site_api import FORBIDDEN_ROLES
from erp_ai.constants import (
	AGENT_USER,
	CREDENTIAL_DOCTYPE,
	HELPDESK_AGENT_ROLE,
	LOG_DOCTYPE,
	ROLE_AGENT,
	SETTING_DOCTYPE,
	TITLE_RUN_FAILED,
)
from erp_ai.erp_ai_agent.doctype.erp_ai_setting.erp_ai_setting import read_privilege_watermark

PERMISSION_DOCTYPES = ("Custom DocPerm", "DocPerm", "Role", "Has Role", "User Permission", "Role Profile")
HAS_ROLE_DOCTYPE = "Has Role"
DOCTYPE_DOCTYPE = "DocType"
USER_DOCTYPE = "User"
MAX_LISTED_NAMES = 5
# Rows newer than now minus this are left for the next run: covers write_entry's insert-to-commit gap and clock skew.
PRIVILEGE_ALERT_SETTLE_S = 300
UNKNOWN_INSTRUCTOR = "không rõ"
# Marks a role entry whose role the tools refuse without the unrestricted switch; such entries are listed first.
ADMIN_ROLE_MARK = "[QUẢN TRỊ] "
# Verb of each generic write tool, keyed by the action word of its name (`api_<word>_record`), so the tool names
# come only from runner.GENERIC_WRITE_TOOLS; a new generic tool with another word fails at import, never mislabelled.
CHANGE_VERBS = {"create": "tạo", "update": "sửa", "delete": "xóa", "submit": "submit/hủy"}
PRIVILEGE_CHANGE_VERBS = {tool: CHANGE_VERBS[tool.split("_")[1]] for tool in GENERIC_WRITE_TOOLS}


def recompute_monthly_spend(now: datetime | None = None) -> None:
	"""Daily job (AC-16, D-19): set this month's spend from the ERP AI Log cost sums.

	Sums `cost_usd` of rows created in the calendar month of `now` into
	`ERP AI Setting.spent_this_month_usd` and, per `credential_label`, into each key row's
	`spent_month_usd` (a key with no log row gets 0). On the 1st the new month starts at ~0.
	Writes directly (no `.save()`); a log label with no key row only counts in the total.
	On any error it rolls back, logs a constant title with an explicit message and returns (D-20).
	"""
	now = get_datetime(now) if now else now_datetime()
	month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
	next_month_start = add_months(month_start, 1)

	try:
		log = frappe.qb.DocType(LOG_DOCTYPE)
		rows = (
			frappe.qb.from_(log)
			.select(log.credential_label, Sum(log.cost_usd).as_("spent"))
			.where((log.creation >= month_start) & (log.creation < next_month_start))
			.groupby(log.credential_label)
			.run(as_dict=True)
		)
		spent_by_label = {row.credential_label: row.spent or 0 for row in rows}

		frappe.db.set_single_value(SETTING_DOCTYPE, "spent_this_month_usd", sum(spent_by_label.values()))
		for key in frappe.get_all(
			CREDENTIAL_DOCTYPE, fields=["name", "label"], parent_doctype=SETTING_DOCTYPE
		):
			frappe.db.set_value(
				CREDENTIAL_DOCTYPE,
				key.name,
				"spent_month_usd",
				spent_by_label.get(key.label, 0),
				update_modified=False,
			)
		if not frappe.flags.in_test:
			frappe.db.commit()
	except Exception as exc:
		frappe.db.rollback()
		frappe.log_error(
			TITLE_RUN_FAILED,
			f"recompute_monthly_spend month={month_start:%Y-%m} error={type(exc).__name__}",
		)


def _list_names(names: list[str]) -> str:
	shown = ", ".join(names[:MAX_LISTED_NAMES])
	extra = len(names) - MAX_LISTED_NAMES
	return f"{shown} …và {extra} mục khác" if extra > 0 else shown


def _agent_role_drift() -> list[str]:
	if not frappe.db.exists("User", AGENT_USER):
		return [f"tài khoản {AGENT_USER} không tồn tại"]
	roles = frappe.get_all("Has Role", filters={"parent": AGENT_USER, "parenttype": "User"}, pluck="role")
	expected = {ROLE_AGENT, HELPDESK_AGENT_ROLE}
	actual = set(roles) - set(AUTOMATIC_ROLES)
	extra, missing = sorted(actual - expected), sorted(expected - actual)
	return [f"thừa role {role}" for role in extra] + [f"thiếu role {role}" for role in missing]


def _load_snapshots(raw) -> dict:
	"""The `"<tool>#<n>"` snapshots of a `reason` row's `value_before`/`value_after` column (design-amd2 §2)."""
	return json.loads(raw) if raw else {}


def _is_permission_change(doctype, key: str, before: dict, after: dict) -> bool:
	if doctype == DOCTYPE_DOCTYPE:
		return (before.get(key) or {}).get("permissions") != (after.get(key) or {}).get("permissions")
	return doctype in PERMISSION_DOCTYPES and doctype != HAS_ROLE_DOCTYPE


def _role_counts(snapshot) -> Counter:
	return Counter(row.get("role") for row in (snapshot or {}).get("roles") or [])


def _role_changes(user: str, key: str, before: dict, after: dict, by: str) -> list[str]:
	"""One entry per role added to or removed from a User, by role name (D-4: kept roles get new rows on save)."""
	old, new = _role_counts(before.get(key)), _role_counts(after.get(key))
	added = [f"{_admin_mark(role)}thêm role {role} cho {user} ({by})" for role in (new - old).elements()]
	removed = [f"{_admin_mark(role)}gỡ role {role} của {user} ({by})" for role in (old - new).elements()]
	return added + removed


def _admin_mark(role) -> str:
	return ADMIN_ROLE_MARK if role in FORBIDDEN_ROLES else ""


def _privilege_changes_by_agent(lower: datetime | None, upper: datetime) -> list[str]:
	"""Entries for successful generic writes on permission records logged in (lower, upper] (ADR-024 QĐ 1, 3.3).

	Reads `reason` rows of ERP AI Log by `creation`, oldest first; no lower bound when `lower` is None.
	A DocType write gives one entry when its `permissions` snapshot changed. `Has Role` rows are User changes: a
	User write gives one entry per role added or removed (0..n). Entries marked `[QUẢN TRỊ]` come first, so the
	5-entry limit of the mail never cuts them before an ordinary one; each group keeps `creation` order.
	"""
	log = frappe.qb.DocType(LOG_DOCTYPE)
	query = (
		frappe.qb.from_(log)
		.select(log.creation, log.instructor, log.actions, log.value_before, log.value_after)
		.where((log.entry_type == "reason") & (log.creation <= upper) & log.actions.like("%api_%"))
		.orderby(log.creation)
	)
	if lower is not None:
		query = query.where(log.creation > lower)
	changes = []
	for row in query.run(as_dict=True):
		before, after = _load_snapshots(row.value_before), _load_snapshots(row.value_after)
		by = f"người ra lệnh {row.instructor or UNKNOWN_INSTRUCTOR}, {row.creation:%Y-%m-%d %H:%M}"
		for position, action in enumerate(json.loads(row.actions), start=1):
			tool, doctype = action.get("tool"), action.get("doctype")
			if tool not in GENERIC_WRITE_TOOLS or not action.get("ok"):
				continue
			if doctype == USER_DOCTYPE:
				changes.extend(_role_changes(action.get("name"), f"{tool}#{position}", before, after, by))
			elif _is_permission_change(doctype, f"{tool}#{position}", before, after):
				changes.append(f"{PRIVILEGE_CHANGE_VERBS[tool]} {doctype} {action.get('name')} ({by})")
	# Stable sort: each group keeps the `creation` order of the rows, then the order of actions and roles.
	return sorted(changes, key=lambda change: not change.startswith(ADMIN_ROLE_MARK))


def _enabled_scripts_by_agent() -> list[str]:
	names = []
	for doctype, flag in (("Server Script", {"disabled": 0}), ("Webhook", {"enabled": 1})):
		if frappe.db.exists("DocType", doctype):
			rows = frappe.get_all(doctype, filters={"owner": AGENT_USER, **flag}, pluck="name")
			names.extend(f"{doctype} {name}" for name in rows)
	return names


def _enabled_keys_without_value() -> list[str]:
	# `api_key` is a Password column: the table holds a mask or nothing; only emptiness is read.
	rows = frappe.get_all(
		CREDENTIAL_DOCTYPE,
		filters={"enabled": 1},
		fields=["label", "api_key"],
		parent_doctype=SETTING_DOCTYPE,
	)
	return [row.label for row in rows if not row.api_key]


def _raise_alarm(subject: str, names: list[str]) -> None:
	"""Record and mail one alarm; an email failure is logged and must not stop later conditions."""
	try:
		alerts.send_alarm(subject, f"{subject}: {_list_names(names)}")
	except Exception as exc:
		# `send_alarm` writes the Error Log before mailing, so the alarm record is already kept.
		frappe.log_error(TITLE_RUN_FAILED, f"check_privilege_escalation email error={type(exc).__name__}")


def check_privilege_escalation(now: datetime | None = None) -> None:
	"""Daily job (AC-18): one alarm per escalation condition that holds.

	Conditions: the agent account's roles (minus automatic ones) differ from {ERP AI Agent, Agent}
	(extra or missing, or the account is gone); permission records the agent wrote, read from the ERP AI Log
	rows created in (watermark, now - PRIVILEGE_ALERT_SETTLE_S]; enabled Server Script/Webhook owned by the
	agent; an enabled key with an empty `api_key`. Messages list at most 5 names and never any key text.
	A failing alarm email is logged under TITLE_RUN_FAILED and the alarm Error Log is kept; the remaining
	conditions still run. On any error it rolls back, logs a constant title with an explicit message and
	returns (D-20).
	"""
	upper = (get_datetime(now) if now else now_datetime()) - timedelta(seconds=PRIVILEGE_ALERT_SETTLE_S)
	try:
		lower = read_privilege_watermark()
		checks = (
			("Tài khoản agent có role ngoài danh sách cho phép", _agent_role_drift),
			("Agent đã sửa bản ghi phân quyền", lambda: _privilege_changes_by_agent(lower, upper)),
			("Server Script/Webhook do agent tạo đang bật", _enabled_scripts_by_agent),
			("Khóa đang bật nhưng không có giá trị", _enabled_keys_without_value),
		)
		for subject, find in checks:
			names = find()
			if names:
				_raise_alarm(subject, names)
		if not frappe.flags.in_test:
			frappe.db.commit()
	except Exception as exc:
		frappe.db.rollback()
		frappe.log_error(TITLE_RUN_FAILED, f"check_privilege_escalation error={type(exc).__name__}")


def reprobe_exhausted_keys() -> None:
	"""Hourly job (AC-18): re-probe keys in status 'Hết hạn mức'.

	The gateway probes only those keys, sets a recovered key back to 'Hoạt động' and sends the one
	notice itself, so this job sends nothing. On any error it rolls back, logs a constant title with
	an explicit message and returns (D-20).
	"""
	try:
		gateway.reprobe_exhausted_keys()
		if not frappe.flags.in_test:
			frappe.db.commit()
	except Exception as exc:
		frappe.db.rollback()
		frappe.log_error(TITLE_RUN_FAILED, f"reprobe_exhausted_keys error={type(exc).__name__}")
