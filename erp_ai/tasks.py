import json
from collections import Counter
from datetime import datetime, timedelta

import frappe
from frappe.permissions import AUTOMATIC_ROLES
from frappe.query_builder.functions import Sum
from frappe.utils import add_months, get_datetime, now_datetime
from frappe.utils.file_lock import LockTimeoutError
from frappe.utils.synchronization import filelock

from erp_ai import alerts, gateway
from erp_ai.agent import policy
from erp_ai.agent.runner import GENERIC_WRITE_TOOLS
from erp_ai.agent.tools.site_api import FORBIDDEN_ROLES
from erp_ai.constants import (
	AGENT_USER,
	CREDENTIAL_DOCTYPE,
	HELPDESK_AGENT_ROLE,
	LOG_DOCTYPE,
	LOGGER_NAME,
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
# Per-site file lock around the whole alarm job, commit included, so two runs never overlap (ADR-024 QĐ 3.7).
PRIVILEGE_ALERT_LOCK = "erp_ai_privilege_alert"
PRIVILEGE_ALERT_LOCK_TIMEOUT_S = 60
PRIVILEGE_CHANGES_SUBJECT = "Agent đã sửa bản ghi phân quyền"
PERMISSION_SWITCHES_ON_SUBJECT = "Quyền mở rộng đang bật"
UNKNOWN_INSTRUCTOR = "không rõ"
# Marks a role entry whose role the tools refuse without the unrestricted switch; such entries are listed first.
ADMIN_ROLE_MARK = "[QUẢN TRỊ] "
# Ends an entry whose snapshots cannot be used, so the change is listed without its before/after (ADR-024 QĐ 1).
NO_BEFORE_AFTER = ", không có trước/sau"
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
	try:
		snapshots = json.loads(raw) if raw else {}
	except (ValueError, TypeError):
		# Fail-closed (ADR-024 QĐ 1): a broken column must not stop the job (it would roll back every day and
		# silence all four conditions); its actions are listed "không có trước/sau" instead.
		return {}
	return snapshots if isinstance(snapshots, dict) else {}


def _load_actions(raw) -> list[dict] | None:
	"""The action entries of a `reason` row, or None when the column cannot be read (listed by row name)."""
	try:
		actions = json.loads(raw)
	except (ValueError, TypeError):
		# Fail-closed (ADR-024 QĐ 1): same reason as `_load_snapshots`.
		return None
	if isinstance(actions, list) and all(isinstance(action, dict) for action in actions):
		return actions
	return None


def _is_privilege_target(doctype) -> bool:
	return doctype in (USER_DOCTYPE, DOCTYPE_DOCTYPE) or (
		doctype in PERMISSION_DOCTYPES and doctype != HAS_ROLE_DOCTYPE
	)


def _has_role_rows(snapshot: dict) -> bool:
	roles = snapshot.get("roles")
	return isinstance(roles, list) and all(
		isinstance(row, dict) and isinstance(row.get("role"), str) and row["role"] for row in roles
	)


def _usable_snapshots(doctype, key: str, before: dict, after: dict) -> tuple | None:
	"""The (before, after) snapshots of one call, or None when they cannot be compared: a key is missing (an old
	row), a side is neither a dict nor None (None = a create's before or a delete's after), both sides are None,
	or a User side has no list of role rows that each name a role."""
	if key not in before or key not in after:
		return None
	pair = (before[key], after[key])
	if pair == (None, None) or not all(side is None or isinstance(side, dict) for side in pair):
		return None
	if doctype == USER_DOCTYPE and not all(side is None or _has_role_rows(side) for side in pair):
		return None
	return pair


def _is_permission_change(doctype, before: dict | None, after: dict | None) -> bool:
	if doctype == DOCTYPE_DOCTYPE:
		return (before or {}).get("permissions") != (after or {}).get("permissions")
	return True


def _role_counts(snapshot: dict | None) -> Counter:
	return Counter(row.get("role") for row in (snapshot or {}).get("roles") or [])


def _role_changes(user: str, before: dict | None, after: dict | None, by: str) -> list[str]:
	"""One entry per role added to or removed from a User, by role name (D-4: kept roles get new rows on save)."""
	old, new = _role_counts(before), _role_counts(after)
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
	Fail-closed: a User or permission write whose snapshots cannot be used gives one entry ending
	NO_BEFORE_AFTER, and a row whose `actions` cannot be read gives `ERP AI Log <row>` + NO_BEFORE_AFTER.
	"""
	log = frappe.qb.DocType(LOG_DOCTYPE)
	query = (
		frappe.qb.from_(log)
		.select(log.name, log.creation, log.instructor, log.actions, log.value_before, log.value_after)
		.where((log.entry_type == "reason") & (log.creation <= upper) & log.actions.like("%api_%"))
		.orderby(log.creation)
	)
	if lower is not None:
		query = query.where(log.creation > lower)
	changes = []
	for row in query.run(as_dict=True):
		actions = _load_actions(row.actions)
		if actions is None:
			changes.append(f"{LOG_DOCTYPE} {row.name}{NO_BEFORE_AFTER}")
			continue
		before, after = _load_snapshots(row.value_before), _load_snapshots(row.value_after)
		by = f"người ra lệnh {row.instructor or UNKNOWN_INSTRUCTOR}, {row.creation:%Y-%m-%d %H:%M}"
		for position, action in enumerate(actions, start=1):
			tool, doctype = action.get("tool"), action.get("doctype")
			if tool not in GENERIC_WRITE_TOOLS or not action.get("ok") or not _is_privilege_target(doctype):
				continue
			record = f"{PRIVILEGE_CHANGE_VERBS[tool]} {doctype} {action.get('name')} ({by})"
			snapshots = _usable_snapshots(doctype, f"{tool}#{position}", before, after)
			if snapshots is None:
				changes.append(f"{record}{NO_BEFORE_AFTER}")
			elif doctype == USER_DOCTYPE:
				changes.extend(_role_changes(action.get("name"), *snapshots, by))
			elif _is_permission_change(doctype, *snapshots):
				changes.append(record)
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


def _enabled_permission_switches() -> list[str]:
	"""Labels of the permission switches that are on, in section order; each field is read by its own flag name."""
	switches = policy.permission_switches(frappe.get_single(SETTING_DOCTYPE))
	meta = frappe.get_meta(SETTING_DOCTYPE)
	return [
		meta.get_label(field)
		for field in policy.PERMISSION_SWITCH_FIELDS
		if getattr(switches, policy.SWITCH_FLAGS[field])
	]


def _raise_alarm(subject: str, names: list[str]) -> None:
	"""Record and mail one alarm; an email failure is logged and must not stop later conditions."""
	try:
		alerts.send_alarm(subject, f"{subject}: {_list_names(names)}")
	except Exception as exc:
		# `send_alarm` writes the Error Log before mailing, so the alarm record is already kept.
		frappe.log_error(TITLE_RUN_FAILED, f"check_privilege_escalation email error={type(exc).__name__}")


def _advance_privilege_watermark(upper: datetime) -> None:
	"""The only writer of the watermark: a direct Single write in the job's transaction, never a Setting save."""
	frappe.db.set_single_value(SETTING_DOCTYPE, "privilege_alert_checked_until", upper)


def check_privilege_escalation(now: datetime | None = None) -> None:
	"""Daily job (AC-18): one alarm per escalation condition that holds.

	Conditions: the agent account's roles (minus automatic ones) differ from {ERP AI Agent, Agent}
	(extra or missing, or the account is gone); permission records the agent wrote, read from the ERP AI Log
	rows created in (watermark, now - PRIVILEGE_ALERT_SETTLE_S]; enabled Server Script/Webhook owned by the
	agent; an enabled key with an empty `api_key`; any permission switch on (by label, ADR-030 QĐ 7).
	Messages list at most 5 names and never any key text.
	A failing alarm email is logged under TITLE_RUN_FAILED and the alarm Error Log is kept; the remaining
	conditions still run. After every condition it advances the watermark to the upper bound (never back)
	in the same transaction as the alarms, before the job's commit (ADR-024 QĐ 3.3, 3.5). On any error it
	rolls back, logs a constant title with an explicit message and returns (D-20).
	The whole run, commit included, holds the per-site PRIVILEGE_ALERT_LOCK; when another run holds it past
	PRIVILEGE_ALERT_LOCK_TIMEOUT_S the job logs "lock busy" and returns without running any condition
	(ADR-024 QĐ 3.7). A finished run logs its window and permission-change count, never a user or role name.
	"""
	try:
		with filelock(PRIVILEGE_ALERT_LOCK, timeout=PRIVILEGE_ALERT_LOCK_TIMEOUT_S):
			_check_privilege_escalation_locked(now)
	except LockTimeoutError:
		frappe.log_error(TITLE_RUN_FAILED, "check_privilege_escalation lock busy")


def _check_privilege_escalation_locked(now: datetime | None) -> None:
	upper = (get_datetime(now) if now else now_datetime()) - timedelta(seconds=PRIVILEGE_ALERT_SETTLE_S)
	try:
		lower = read_privilege_watermark()
		checks = (
			("Tài khoản agent có role ngoài danh sách cho phép", _agent_role_drift),
			(PRIVILEGE_CHANGES_SUBJECT, lambda: _privilege_changes_by_agent(lower, upper)),
			("Server Script/Webhook do agent tạo đang bật", _enabled_scripts_by_agent),
			("Khóa đang bật nhưng không có giá trị", _enabled_keys_without_value),
			# Daily, read-only: never reads or moves the watermark and writes no ERP AI Log row (ADR-030 QĐ 7).
			(PERMISSION_SWITCHES_ON_SUBJECT, _enabled_permission_switches),
		)
		found = {}
		for subject, find in checks:
			found[subject] = names = find()
			if names:
				_raise_alarm(subject, names)
		# Never moves back: an upper bound not after the watermark read nothing new (ADR-024 QĐ 3.3).
		if lower is None or upper > lower:
			_advance_privilege_watermark(upper)
		if not frappe.flags.in_test:
			frappe.db.commit()
	except Exception as exc:
		frappe.db.rollback()
		frappe.log_error(TITLE_RUN_FAILED, f"check_privilege_escalation error={type(exc).__name__}")
		return
	frappe.logger(LOGGER_NAME).info(
		"check_privilege_escalation window=%s..%s changes=%d",
		lower,
		upper,
		len(found[PRIVILEGE_CHANGES_SUBJECT]),
	)


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
