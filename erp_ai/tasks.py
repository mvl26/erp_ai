from datetime import datetime

import frappe
from frappe.permissions import AUTOMATIC_ROLES
from frappe.query_builder.functions import Sum
from frappe.utils import add_months, get_datetime, now_datetime

from erp_ai import alerts
from erp_ai.constants import (
	AGENT_USER,
	CREDENTIAL_DOCTYPE,
	HELPDESK_AGENT_ROLE,
	LOG_DOCTYPE,
	ROLE_AGENT,
	SETTING_DOCTYPE,
	TITLE_RUN_FAILED,
)

PERMISSION_DOCTYPES = ("Custom DocPerm", "DocPerm", "Role", "Has Role", "User Permission", "Role Profile")
MAX_LISTED_NAMES = 5


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
	allowed = {ROLE_AGENT, HELPDESK_AGENT_ROLE, *AUTOMATIC_ROLES}
	return sorted(set(roles) - allowed)


def _permission_records_by_agent() -> list[str]:
	names = []
	for doctype in PERMISSION_DOCTYPES:
		if frappe.db.exists("DocType", doctype):
			rows = frappe.get_all(doctype, filters={"modified_by": AGENT_USER}, pluck="name")
			names.extend(f"{doctype} {name}" for name in rows)
	return names


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


def check_privilege_escalation() -> None:
	"""Daily job (AC-18): one alarm per escalation condition that holds.

	Conditions: the agent account holds a role outside {ERP AI Agent, Agent}; permission records
	modified by the agent; enabled Server Script/Webhook owned by the agent; an enabled key with an
	empty `api_key`. Messages list at most 5 names and never any key text.
	On any error it rolls back, logs a constant title with an explicit message and returns (D-20).
	"""
	checks = (
		("Tài khoản agent có role ngoài danh sách cho phép", _agent_role_drift),
		("Agent đã sửa bản ghi phân quyền", _permission_records_by_agent),
		("Server Script/Webhook do agent tạo đang bật", _enabled_scripts_by_agent),
		("Khóa đang bật nhưng không có giá trị", _enabled_keys_without_value),
	)
	try:
		for subject, find in checks:
			names = find()
			if names:
				alerts.send_alarm(subject, f"{subject}: {_list_names(names)}")
		if not frappe.flags.in_test:
			frappe.db.commit()
	except Exception as exc:
		frappe.db.rollback()
		frappe.log_error(TITLE_RUN_FAILED, f"check_privilege_escalation error={type(exc).__name__}")
