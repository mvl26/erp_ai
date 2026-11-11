import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from erp_ai.constants import (
	AGENT_USER,
	HELPDESK_AGENT_ROLE,
	LOGGER_NAME,
	ROLE_AGENT,
	ROLE_INSTRUCTOR,
	SETTING_DOCTYPE,
)

TICKET_DOCTYPE = "HD Ticket"
TEMPLATE_NAME = "Default"
AI_MODULE = "ERP AI agent"
AI_SECTION_FIELD = "ai_section"
OPT_OUT_FIELD = "ai_opt_out"
AI_PERMLEVEL = 8


def after_install():
	ensure_setup()


def after_migrate():
	ensure_setup()


def ensure_setup() -> None:
	"""Create what is missing; never overwrite or remove anything a human set."""
	_ensure_roles()
	_ensure_agent_user()
	_ensure_default_settings()
	_ensure_ticket_custom_fields()
	_ensure_template_rows()


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
			"select value from `tabSingles` where doctype=%s and field=%s",
			(SETTING_DOCTYPE, field.fieldname),
		)
		if not stored or stored[0][0] is None:
			frappe.db.set_single_value(SETTING_DOCTYPE, field.fieldname, field.default)


def _ensure_ticket_custom_fields() -> None:
	# Keep the section where it was first placed; the last field of the meta changes once ours exist.
	insert_after = frappe.db.get_value(
		"Custom Field", {"dt": TICKET_DOCTYPE, "fieldname": AI_SECTION_FIELD}, "insert_after"
	) or (frappe.get_meta(TICKET_DOCTYPE).fields[-1].fieldname)
	common = {"permlevel": AI_PERMLEVEL, "module": AI_MODULE}
	fields = [
		{
			"fieldname": AI_SECTION_FIELD,
			"label": "ERP AI",
			"fieldtype": "Section Break",
			"insert_after": insert_after,
		},
		{
			"fieldname": "ai_resolution_hint",
			"label": "Hướng giải quyết (AI)",
			"fieldtype": "Text Editor",
			"read_only": 1,
		},
		{
			"fieldname": "ai_confidence",
			"label": "Độ tin cậy (AI)",
			"fieldtype": "Select",
			"options": "\nCao\nTrung bình\nThấp",
			"read_only": 1,
		},
		{
			"fieldname": "ai_classified_by",
			"label": "Phân loại bởi",
			"fieldtype": "Select",
			"options": "\nAI\nNgười",
			"read_only": 1,
		},
		{
			"fieldname": "ai_updated_at",
			"label": "AI cập nhật lúc",
			"fieldtype": "Datetime",
			"read_only": 1,
		},
		{
			"fieldname": OPT_OUT_FIELD,
			"label": "Không dùng AI cho phiếu này",
			"fieldtype": "Check",
		},
	]
	previous = None
	for field in fields:
		field.update(common)
		field.setdefault("insert_after", previous)
		previous = field["fieldname"]
	create_custom_fields({TICKET_DOCTYPE: fields}, update=True)


def _ensure_template_rows() -> None:
	if not frappe.db.exists("HD Ticket Template", TEMPLATE_NAME):
		frappe.logger(LOGGER_NAME).warning(
			"HD Ticket Template %s not found; AI rows not added", TEMPLATE_NAME
		)
		return
	template = frappe.get_doc("HD Ticket Template", TEMPLATE_NAME)
	present = {row.fieldname for row in template.fields}
	missing = [
		name
		for name in (
			"ai_resolution_hint",
			"ai_confidence",
			"ai_classified_by",
			"ai_updated_at",
			OPT_OUT_FIELD,
		)
		if name not in present
	]
	for name in missing:
		template.append(
			"fields",
			{
				"fieldname": name,
				"required": 0,
				"visible_to": "Agents",
				"editable_after_creation": 1 if name == OPT_OUT_FIELD else 0,
			},
		)
	if missing:
		template.flags.ignore_permissions = True
		template.save()
