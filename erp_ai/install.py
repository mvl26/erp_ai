import frappe

from erp_ai.constants import AGENT_USER, HELPDESK_AGENT_ROLE, ROLE_AGENT, ROLE_INSTRUCTOR, SETTING_DOCTYPE


def after_install():
	ensure_setup()


def after_migrate():
	ensure_setup()


def ensure_setup() -> None:
	"""Create what is missing; never overwrite or remove anything a human set."""
	_ensure_roles()
	_ensure_agent_user()
	_ensure_default_settings()


def _ensure_roles() -> None:
	for role in (ROLE_AGENT, ROLE_INSTRUCTOR):
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
				ignore_permissions=True
			)


def _ensure_agent_user() -> None:
	wanted = (ROLE_AGENT, HELPDESK_AGENT_ROLE)
	if not frappe.db.exists("User", AGENT_USER):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": AGENT_USER,
				"first_name": "ERP AI",
				"user_type": "System User",
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
	user = frappe.get_doc("User", AGENT_USER)
	missing = [role for role in wanted if role not in {row.role for row in user.roles}]
	if missing:
		user.add_roles(*missing)


def _ensure_default_settings() -> None:
	for field in frappe.get_meta(SETTING_DOCTYPE).fields:
		if field.default is None or field.default == "":
			continue
		stored = frappe.db.sql(
			"select 1 from `tabSingles` where doctype=%s and field=%s",
			(SETTING_DOCTYPE, field.fieldname),
		)
		if not stored:
			frappe.db.set_single_value(SETTING_DOCTYPE, field.fieldname, field.default)
