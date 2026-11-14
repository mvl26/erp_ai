import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.permissions import setup_custom_perms

from erp_ai.agent.policy import OPT_OUT_FIELD
from erp_ai.agent.routing import DEFAULT_ROUTING_RULES
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
AI_PERMLEVEL = 8
TASK_DOCTYPE = "Task"
TASK_TICKET_FIELD = "ai_ticket"
ARTICLE_DOCTYPE = "HD Article"
ARTICLE_SOURCE_FIELD = "ai_source_ticket"
FORM_SCRIPT_DOCTYPE = "HD Form Script"
AGENT_STATUS_SCRIPT = "ERP AI Agent Status"
AGENT_STATUS_SCRIPT_FILE = ("public", "js", "agent_status_indicator.js")
AGENT_STATUS_SCRIPT_FLAGS = {
	"dt": "HD Ticket",
	"apply_to": "Form",
	"enabled": 1,
	"apply_to_customer_portal": 0,
	"apply_on_new_page": 0,
	"is_standard": 0,
}


def after_install():
	ensure_setup()


def after_migrate():
	ensure_setup()


def ensure_setup() -> None:
	"""Create what is missing, never overwrite what a human set; except the app-owned form script (ADR-007)."""
	_ensure_roles()
	_ensure_agent_user()
	_ensure_default_settings()
	_ensure_ticket_custom_fields()
	_ensure_template_rows()
	_ensure_task_ticket_field()
	_ensure_article_source_field()
	_ensure_task_permission()
	_ensure_article_instructor_permission()
	_ensure_agent_status_script()


def before_uninstall() -> None:
	"""Remove the app-owned form script; the only delete in the app (ADR-007)."""
	if not frappe.db.exists("DocType", FORM_SCRIPT_DOCTYPE):
		return
	if frappe.db.exists(FORM_SCRIPT_DOCTYPE, AGENT_STATUS_SCRIPT):
		frappe.delete_doc(FORM_SCRIPT_DOCTYPE, AGENT_STATUS_SCRIPT, ignore_permissions=True)


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
	defaults = {
		field.fieldname: field.default
		for field in frappe.get_meta(SETTING_DOCTYPE).fields
		if field.default is not None and field.default != ""
	}
	# Too long for a DocType JSON default, so it lives in code (design 2.4/3.3).
	defaults["routing_rules"] = DEFAULT_ROUTING_RULES
	for fieldname, default in defaults.items():
		stored = frappe.db.sql(
			"select value from `tabSingles` where doctype=%s and field=%s",
			(SETTING_DOCTYPE, fieldname),
		)
		if not stored or stored[0][0] is None:
			frappe.db.set_single_value(SETTING_DOCTYPE, fieldname, default)
	# A site enabled before the upgrade gets its enable mark once (AC-16, ADR-006); absent, NULL or "" is missing.
	enabled_at = frappe.db.sql(
		"select value from `tabSingles` where doctype=%s and field='agent_enabled_at'", SETTING_DOCTYPE
	)
	if frappe.db.get_single_value(SETTING_DOCTYPE, "enabled", cache=False) and not (
		enabled_at and enabled_at[0][0]
	):
		frappe.db.set_single_value(SETTING_DOCTYPE, "agent_enabled_at", frappe.utils.now_datetime())


def _ensure_ticket_custom_fields() -> None:
	# Keep the section where it was first placed; the last field of the meta changes once ours exist.
	insert_after = frappe.db.get_value(
		"Custom Field", {"dt": TICKET_DOCTYPE, "fieldname": AI_SECTION_FIELD}, "insert_after"
	) or (frappe.get_meta(TICKET_DOCTYPE).fields[-1].fieldname)
	common = {"permlevel": AI_PERMLEVEL, "module": AI_MODULE}
	fields = _ai_field_specs()
	fields[0]["insert_after"] = insert_after
	previous = None
	for field in fields:
		field.update(common)
		field.setdefault("insert_after", previous)
		previous = field["fieldname"]
	create_custom_fields({TICKET_DOCTYPE: fields}, update=True)


def _ai_field_specs() -> list[dict]:
	"""Single source of the AI fields; the first one is the section break."""
	return [
		{
			"fieldname": AI_SECTION_FIELD,
			"label": "ERP AI",
			"fieldtype": "Section Break",
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
			"fieldname": "ai_confidence_pct",
			"label": "Độ tin cậy % (AI)",
			"fieldtype": "Int",
			"read_only": 1,
		},
		{
			"fieldname": "ai_complexity",
			"label": "Độ phức tạp (AI)",
			"fieldtype": "Int",
			"default": "0",
			"read_only": 1,
		},
		{
			"fieldname": "ai_importance",
			"label": "Độ quan trọng (AI)",
			"fieldtype": "Int",
			"default": "0",
			"read_only": 1,
		},
		{
			"fieldname": "ai_score_reason",
			"label": "Lý do chấm điểm (AI)",
			"fieldtype": "Small Text",
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
		{
			# Server-only: labels the requester filled at creation; no template row (hidden).
			"fieldname": "ai_created_labels",
			"label": "Nhãn người tạo điền (AI)",
			"fieldtype": "Small Text",
			"hidden": 1,
			"read_only": 1,
			"no_copy": 1,
		},
	]


def _ensure_template_rows() -> None:
	if not frappe.db.exists("HD Ticket Template", TEMPLATE_NAME):
		frappe.logger(LOGGER_NAME).warning(
			"HD Ticket Template %s not found; AI rows not added", TEMPLATE_NAME
		)
		return
	template = frappe.get_doc("HD Ticket Template", TEMPLATE_NAME)
	present = {row.fieldname for row in template.fields}
	# A hidden field is server-only, so it gets no row; a row already there is a human decision and stays.
	missing = [
		name
		for name in (
			spec["fieldname"]
			for spec in _ai_field_specs()
			if spec["fieldname"] != AI_SECTION_FIELD and not spec.get("hidden")
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


def _ensure_task_ticket_field() -> None:
	if not frappe.db.exists("DocType", TASK_DOCTYPE):
		return  # _ensure_task_permission logs the missing DocType once
	# update=False: a field that exists is left as the human set it.
	create_custom_fields(
		{
			TASK_DOCTYPE: [
				{
					"fieldname": TASK_TICKET_FIELD,
					"label": "Phiếu Helpdesk",
					"fieldtype": "Link",
					"options": TICKET_DOCTYPE,
					"permlevel": 0,
					"search_index": 1,
					"module": AI_MODULE,
					"insert_after": "description",
				}
			]
		},
		update=False,
	)


def _ensure_article_source_field() -> None:
	if not frappe.db.exists("DocType", ARTICLE_DOCTYPE):
		frappe.logger(LOGGER_NAME).warning("DocType HD Article not found; source ticket field not added")
		return
	# update=False: a field that exists is left as the human set it.
	create_custom_fields(
		{
			ARTICLE_DOCTYPE: [
				{
					"fieldname": ARTICLE_SOURCE_FIELD,
					"label": "Phiếu nguồn (AI)",
					"fieldtype": "Link",
					"options": TICKET_DOCTYPE,
					"read_only": 1,
					"search_index": 1,
					"module": AI_MODULE,
					"insert_after": "category",
				}
			]
		},
		update=False,
	)


def _ensure_task_permission() -> None:
	if not frappe.db.exists("DocType", TASK_DOCTYPE):
		frappe.logger(LOGGER_NAME).warning("DocType Task not found; agent permission not added")
		return
	setup_custom_perms(TASK_DOCTYPE)
	row = {"parent": TASK_DOCTYPE, "role": ROLE_AGENT, "permlevel": 0, "if_owner": 1}
	if frappe.db.exists("Custom DocPerm", {"parent": TASK_DOCTYPE, "role": ROLE_AGENT}):
		# Only the share flag is ours to turn on; every other flag stays as found.
		if frappe.db.exists("Custom DocPerm", {**row, "share": 0}):
			frappe.db.set_value("Custom DocPerm", {**row, "share": 0}, "share", 1)
			frappe.clear_cache(doctype=TASK_DOCTYPE)
		return
	frappe.get_doc(
		{
			"doctype": "Custom DocPerm",
			"parent": TASK_DOCTYPE,
			"parenttype": "DocType",
			"parentfield": "permissions",
			"role": ROLE_AGENT,
			"permlevel": 0,
			"read": 1,
			"write": 1,
			"create": 1,
			"share": 1,
			"if_owner": 1,
		}
	).insert(ignore_permissions=True)
	frappe.clear_cache(doctype=TASK_DOCTYPE)


def _ensure_article_instructor_permission() -> None:
	if not frappe.db.exists("DocType", ARTICLE_DOCTYPE):
		frappe.logger(LOGGER_NAME).warning("DocType HD Article not found; instructor permission not added")
		return
	# Copy the standard DocPerm first: once a Custom DocPerm exists, the standard rows are ignored (ADR-015).
	setup_custom_perms(ARTICLE_DOCTYPE)
	if frappe.db.exists("Custom DocPerm", {"parent": ARTICLE_DOCTYPE, "role": ROLE_INSTRUCTOR}):
		return
	frappe.get_doc(
		{
			"doctype": "Custom DocPerm",
			"parent": ARTICLE_DOCTYPE,
			"parenttype": "DocType",
			"parentfield": "permissions",
			"role": ROLE_INSTRUCTOR,
			"permlevel": 0,
			"read": 1,
			"report": 1,
			"export": 0,  # the Custom DocPerm default is 1; the Instructor only reads and reports
		}
	).insert(ignore_permissions=True)
	frappe.clear_cache(doctype=ARTICLE_DOCTYPE)


def _ensure_agent_status_script() -> None:
	if not frappe.db.exists("DocType", FORM_SCRIPT_DOCTYPE):
		frappe.logger(LOGGER_NAME).warning(
			"DocType %s not found; status script not installed", FORM_SCRIPT_DOCTYPE
		)
		return
	with open(frappe.get_app_path("erp_ai", *AGENT_STATUS_SCRIPT_FILE), encoding="utf-8") as handle:
		wanted = {**AGENT_STATUS_SCRIPT_FLAGS, "script": handle.read()}
	if not frappe.db.exists(FORM_SCRIPT_DOCTYPE, AGENT_STATUS_SCRIPT):
		frappe.get_doc({"doctype": FORM_SCRIPT_DOCTYPE, "name": AGENT_STATUS_SCRIPT, **wanted}).insert(
			ignore_permissions=True
		)
		return
	doc = frappe.get_doc(FORM_SCRIPT_DOCTYPE, AGENT_STATUS_SCRIPT)
	if all(doc.get(key) == value for key, value in wanted.items()):
		return
	doc.update(wanted)
	doc.save(ignore_permissions=True)
