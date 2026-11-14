from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.helpdesk.doctype.hd_form_script.hd_form_script import get_form_script
from helpdesk.test_utils import make_ticket

from erp_ai import install
from erp_ai.agent.routing import DEFAULT_ROUTING_RULES
from erp_ai.constants import (
	AGENT_USER,
	HELPDESK_AGENT_ROLE,
	LOG_DOCTYPE,
	LOGGER_NAME,
	ROLE_AGENT,
	ROLE_INSTRUCTOR,
	SETTING_DOCTYPE,
)
from erp_ai.test_utils import keep_agent_settings

INSTRUCTOR_LOG_RIGHTS = ("read", "report")

AI_FIELDS = (
	"ai_section",
	"ai_resolution_hint",
	"ai_confidence",
	"ai_complexity",
	"ai_importance",
	"ai_score_reason",
	"ai_classified_by",
	"ai_updated_at",
	"ai_opt_out",
)
TEMPLATE = "Default"

AUTOMATIC_ROLES = {"Guest", "All", "Administrator", "Desk User"}

# FEAT-007 AC-1: switches (1) and (4) existed before FEAT-007; (2), (3), (5) are new.
OLD_SWITCHES = ("unrestricted_enabled", "code_change_enabled")
NEW_SWITCHES = ("record_tools_enabled", "act_now_enabled", "one_click_approval_enabled")
FIVE_SWITCHES = (
	"unrestricted_enabled",
	"record_tools_enabled",
	"act_now_enabled",
	"code_change_enabled",
	"one_click_approval_enabled",
)


def _agent_roles():
	return set(frappe.get_all("Has Role", filters={"parent": AGENT_USER, "parenttype": "User"}, pluck="role"))


def _counts():
	return {
		"roles": frappe.db.count("Role", {"name": ("in", [ROLE_AGENT, ROLE_INSTRUCTOR])}),
		"users": frappe.db.count("User", {"name": AGENT_USER}),
		"agent_roles": len(_agent_roles()),
		"tickets": frappe.db.count("HD Ticket"),
		"comments": frappe.db.count("HD Ticket Comment"),
		"ai_fields": frappe.db.count("Custom Field", {"dt": "HD Ticket", "fieldname": ("like", "ai\\_%")}),
		"template_rows": frappe.db.count("HD Ticket Template Field", {"parent": TEMPLATE}),
		"status_scripts": frappe.db.count(install.FORM_SCRIPT_DOCTYPE, {"name": install.AGENT_STATUS_SCRIPT}),
	}


def _ticket_rows():
	return (
		frappe.db.sql("select name, modified from `tabHD Ticket` order by name"),
		frappe.db.sql("select name, modified from `tabHD Ticket Comment` order by name"),
	)


class TestInstall(FrappeTestCase):
	def setUp(self):
		frappe.db.rollback()
		self.addCleanup(frappe.db.rollback)
		# Empty state inside the rolled-back transaction so "create if missing" runs for real.
		frappe.db.delete("Singles", {"doctype": SETTING_DOCTYPE})
		frappe.db.delete("Has Role", {"parent": AGENT_USER, "parenttype": "User"})
		frappe.db.delete("User", {"name": AGENT_USER})
		frappe.db.delete("Role", {"name": ("in", [ROLE_AGENT, ROLE_INSTRUCTOR])})
		# Creating a Custom Field runs ALTER TABLE, an implicit commit that would leak the deletes below.
		# The columns already exist (migrate), so skip the DDL and keep everything in the transaction.
		patcher = patch.object(frappe.db, "updatedb")
		patcher.start()
		self.addCleanup(patcher.stop)
		# Committed by migrate; remove so the create path runs inside the rolled-back transaction.
		frappe.db.delete("Custom Field", {"dt": "HD Ticket", "fieldname": ("like", "ai\\_%")})
		frappe.db.delete("HD Ticket Template Field", {"parent": TEMPLATE, "fieldname": ("like", "ai\\_%")})
		frappe.clear_cache(doctype="HD Ticket")
		# Same for the agent's Task permission (Custom DocPerm insert has no DDL, so it stays in the transaction).
		frappe.db.delete("Custom DocPerm", {"parent": "Task", "role": ROLE_AGENT})
		frappe.clear_cache(doctype="Task")
		# Same for the Task link field (DDL skipped above).
		frappe.db.delete("Custom Field", {"dt": "Task", "fieldname": "ai_ticket"})
		# The app-owned form script, removed so the create path runs inside the rolled-back transaction.
		frappe.db.delete(install.FORM_SCRIPT_DOCTYPE, {"name": install.AGENT_STATUS_SCRIPT})
		install.ensure_setup()

	def test_setup_twice_is_idempotent(self):
		before = _counts()
		install.ensure_setup()
		install.after_migrate()
		self.assertEqual(_counts(), before)
		self.assertEqual(before["roles"], 2)
		self.assertEqual(before["users"], 1)
		self.assertEqual(before["ai_fields"], 9)

	def test_ai_fields_permlevel_8_and_template_rows_agents_only(self):
		for name in AI_FIELDS:
			field = frappe.db.get_value(
				"Custom Field",
				{"dt": "HD Ticket", "fieldname": name},
				["permlevel", "module"],
				as_dict=True,
			)
			self.assertIsNotNone(field, name)
			self.assertEqual(field.permlevel, 8, name)
			self.assertEqual(field.module, "ERP AI agent", name)
		self.assertEqual(
			frappe.db.get_value("Custom Field", "HD Ticket-ai_confidence", "options"),
			"\nCao\nTrung bình\nThấp",
		)
		rows = frappe.get_all(
			"HD Ticket Template Field",
			filters={"parent": TEMPLATE, "fieldname": ("in", AI_FIELDS)},
			fields=["fieldname", "visible_to", "required", "editable_after_creation"],
		)
		self.assertEqual({r.fieldname for r in rows}, set(AI_FIELDS) - {"ai_section"})
		self.assertEqual(len(rows), 8)
		for row in rows:
			self.assertEqual(row.visible_to, "Agents")
			self.assertEqual(row.required, 0)
			self.assertEqual(row.editable_after_creation, 1 if row.fieldname == "ai_opt_out" else 0)
		frappe.clear_cache(doctype="HD Ticket")
		meta = frappe.get_meta("HD Ticket")
		for name in AI_FIELDS:
			self.assertEqual(meta.get_field(name).permlevel, 8, name)
		self.assertNotIn(
			8, {perm.permlevel for perm in meta.permissions if perm.role == "HD Customer" and perm.read}
		)

	def test_existing_template_row_preserved(self):
		frappe.db.delete("HD Ticket Template Field", {"parent": TEMPLATE})
		frappe.db.sql(
			"insert into `tabHD Ticket Template Field` (name, parent, parenttype, parentfield, idx, fieldname, "
			"required, visible_to, editable_after_creation) values ('erp-ai-t12-keep', %s, 'HD Ticket Template', "
			"'fields', 1, 'priority', 1, 'Everyone', 1)",
			TEMPLATE,
		)
		install.ensure_setup()
		rows = frappe.get_all(
			"HD Ticket Template Field",
			filters={"parent": TEMPLATE},
			fields=["name", "idx", "fieldname", "required", "visible_to", "editable_after_creation"],
			order_by="idx",
		)
		self.assertEqual(len(rows), 9)
		first = rows[0]
		self.assertEqual(
			(
				first.name,
				first.idx,
				first.fieldname,
				first.required,
				first.visible_to,
				first.editable_after_creation,
			),
			("erp-ai-t12-keep", 1, "priority", 1, "Everyone", 1),
		)
		self.assertEqual([r.idx for r in rows], [1, 2, 3, 4, 5, 6, 7, 8, 9])
		self.assertEqual(
			[r.fieldname for r in rows[1:]],
			[
				"ai_resolution_hint",
				"ai_confidence",
				"ai_complexity",
				"ai_importance",
				"ai_score_reason",
				"ai_classified_by",
				"ai_updated_at",
				"ai_opt_out",
			],
		)
		for row in rows[1:]:
			self.assertEqual(row.visible_to, "Agents", row.fieldname)
			self.assertEqual(row.required, 0, row.fieldname)
			self.assertEqual(
				row.editable_after_creation, 1 if row.fieldname == "ai_opt_out" else 0, row.fieldname
			)

	def test_missing_template_is_skipped_with_warning(self):
		frappe.db.delete("HD Ticket Template", {"name": TEMPLATE})
		with patch.object(install.frappe, "logger") as logger:
			install.ensure_setup()
		logger.assert_called_with(LOGGER_NAME)
		logger.return_value.warning.assert_called_once()
		self.assertIn("not found", logger.return_value.warning.call_args.args[0])
		self.assertEqual(logger.return_value.warning.call_args.args[1], TEMPLATE)
		self.assertFalse(frappe.db.exists("HD Ticket Template", TEMPLATE))

	def _agent_task_perms(self):
		return frappe.get_all(
			"Custom DocPerm",
			filters={"parent": "Task", "role": ROLE_AGENT},
			fields=["permlevel", "read", "write", "create", "if_owner", "delete", "submit"],
		)

	def _other_task_perms(self):
		return frappe.db.sql(
			"select name, role, permlevel, `read`, `write`, `create`, `delete`, `share`, if_owner, modified "
			"from `tabCustom DocPerm` where parent='Task' and role != %s order by name",
			ROLE_AGENT,
		)

	def _agent_task_perm_row(self):
		return frappe.db.get_value(
			"Custom DocPerm",
			{"parent": "Task", "role": ROLE_AGENT, "permlevel": 0, "if_owner": 1},
			["name", "share", "read", "write", "create", "delete", "submit", "cancel", "amend", "modified"],
			as_dict=True,
		)

	def test_task_permission_share_and_role_set(self):
		other = self._other_task_perms()
		install.ensure_setup()
		install.ensure_setup()
		self.assertEqual(len(self._agent_task_perms()), 1)
		perm = self._agent_task_perm_row()
		self.assertEqual((perm.read, perm.write, perm.create, perm.share), (1, 1, 1, 1))
		self.assertEqual((perm.delete, perm.submit, perm.cancel, perm.amend), (0, 0, 0, 0))
		self.assertEqual(self._other_task_perms(), other)
		self.assertEqual(_agent_roles() - AUTOMATIC_ROLES, {ROLE_AGENT, HELPDESK_AGENT_ROLE})

	def test_task_permission_missing_row_is_created_with_share(self):
		frappe.db.delete("Custom DocPerm", {"parent": "Task", "role": ROLE_AGENT})
		install.ensure_setup()
		perm = self._agent_task_perm_row()
		self.assertIsNotNone(perm)
		self.assertEqual(perm.share, 1)

	def test_task_permission_share_off_is_turned_on_only_that_flag(self):
		perm = self._agent_task_perm_row()
		frappe.db.set_value("Custom DocPerm", perm.name, {"share": 0, "write": 0})
		# get_meta below caches the in-transaction state (write=0) in redis; rollback does not clear it.
		self.addCleanup(frappe.clear_cache, doctype="Task")
		frappe.clear_cache(doctype="Task")
		decoys = [
			{"role": ROLE_AGENT, "permlevel": 0, "if_owner": 0},
			{"role": ROLE_AGENT, "permlevel": 1, "if_owner": 1},
			{"role": "Blogger", "permlevel": 0, "if_owner": 1},
		]
		for decoy in decoys:
			frappe.get_doc(
				{
					"doctype": "Custom DocPerm",
					"parent": "Task",
					"parenttype": "DocType",
					"parentfield": "permissions",
					"read": 1,
					"share": 0,
					**decoy,
				}
			).insert(ignore_permissions=True)
		other = self._other_task_perms()
		with patch.object(install.frappe, "clear_cache", wraps=frappe.clear_cache) as clear_cache:
			install.ensure_setup()
		clear_cache.assert_any_call(doctype="Task")
		now = self._agent_task_perm_row()
		self.assertEqual((now.share, now.write, now.read, now.create), (1, 0, 1, 1))
		self.assertEqual(self._other_task_perms(), other)
		decoy_shares = frappe.get_all(
			"Custom DocPerm",
			filters={"parent": "Task", "share": 0, "role": ("in", [ROLE_AGENT, "Blogger"])},
			fields=["role", "permlevel", "if_owner"],
		)
		self.assertCountEqual(
			[(d.role, d.permlevel, d.if_owner) for d in decoy_shares],
			[(d["role"], d["permlevel"], d["if_owner"]) for d in decoys],
		)
		shared = [
			p.share
			for p in frappe.get_meta("Task").permissions
			if p.role == ROLE_AGENT and p.if_owner and not p.permlevel
		]
		self.assertEqual(shared, [1])

	def test_task_permission_share_already_on_is_not_saved_again(self):
		perm = self._agent_task_perm_row()
		old = "2020-01-01 00:00:00"
		frappe.db.set_value("Custom DocPerm", perm.name, "modified", old, update_modified=False)
		install.ensure_setup()
		self.assertEqual(str(self._agent_task_perm_row().modified), old)

	def test_score_fields_int_default_zero_permlevel_8(self):
		for name in ("ai_complexity", "ai_importance"):
			field = frappe.db.get_value(
				"Custom Field",
				{"dt": "HD Ticket", "fieldname": name},
				["fieldtype", "default", "permlevel", "read_only"],
				as_dict=True,
			)
			self.assertEqual(
				(field.fieldtype, field.default, field.permlevel, field.read_only), ("Int", "0", 8, 1)
			)
		reason = frappe.db.get_value(
			"Custom Field",
			{"dt": "HD Ticket", "fieldname": "ai_score_reason"},
			["fieldtype", "permlevel", "read_only"],
			as_dict=True,
		)
		self.assertEqual((reason.fieldtype, reason.permlevel, reason.read_only), ("Small Text", 8, 1))
		rows = frappe.get_all(
			"HD Ticket Template Field",
			filters={
				"parent": TEMPLATE,
				"fieldname": ("in", ("ai_complexity", "ai_importance", "ai_score_reason")),
			},
			fields=["fieldname", "visible_to", "required"],
		)
		self.assertEqual(len(rows), 3)
		self.assertEqual({r.fieldname for r in rows}, {"ai_complexity", "ai_importance", "ai_score_reason"})
		self.assertEqual({(r.visible_to, r.required) for r in rows}, {("Agents", 0)})

	def _task_ticket_field(self):
		return frappe.db.get_value(
			"Custom Field",
			{"dt": "Task", "fieldname": "ai_ticket"},
			[
				"name",
				"fieldtype",
				"options",
				"permlevel",
				"search_index",
				"label",
				"module",
				"insert_after",
				"read_only",
			],
			as_dict=True,
		)

	def test_task_ticket_field(self):
		field = self._task_ticket_field()
		self.assertIsNotNone(field)
		self.assertEqual(
			(field.fieldtype, field.options, field.permlevel, field.search_index, field.read_only),
			("Link", "HD Ticket", 0, 1, 0),
		)
		self.assertEqual(
			(field.label, field.module, field.insert_after),
			("Phiếu Helpdesk", "ERP AI agent", "description"),
		)
		install.ensure_setup()
		self.assertEqual(frappe.db.count("Custom Field", {"dt": "Task", "fieldname": "ai_ticket"}), 1)

	def test_task_ticket_field_existing_is_not_changed(self):
		name = self._task_ticket_field().name
		frappe.db.set_value("Custom Field", name, {"label": "Do người sửa", "search_index": 0})
		install.ensure_setup()
		field = self._task_ticket_field()
		self.assertEqual((field.label, field.search_index), ("Do người sửa", 0))
		self.assertEqual(frappe.db.count("Custom Field", {"dt": "Task", "fieldname": "ai_ticket"}), 1)

	def test_agent_task_perm_created_once_if_owner(self):
		other = self._other_task_perms()
		self.assertTrue(other)
		install.ensure_setup()
		install.after_migrate()
		perms = self._agent_task_perms()
		self.assertEqual(len(perms), 1)
		perm = perms[0]
		self.assertEqual((perm.permlevel, perm.read, perm.write, perm.create, perm.if_owner), (0, 1, 1, 1, 1))
		self.assertEqual((perm.delete, perm.submit), (0, 0))
		self.assertEqual(self._other_task_perms(), other)

	def test_task_perm_copies_standard_perms_when_no_custom_yet(self):
		frappe.db.delete("Custom DocPerm", {"parent": "Task"})
		standard = frappe.db.count("DocPerm", {"parent": "Task"})
		install.ensure_setup()
		self.assertEqual(len(self._agent_task_perms()), 1)
		self.assertEqual(frappe.db.count("Custom DocPerm", {"parent": "Task"}), standard + 1)

	def test_missing_task_doctype_is_skipped_with_warning(self):
		frappe.db.delete("Custom DocPerm", {"parent": "Task", "role": ROLE_AGENT})
		frappe.db.delete("Custom Field", {"dt": "Task", "fieldname": "ai_ticket"})
		real = frappe.db.exists
		with (
			patch.object(
				install.frappe.db,
				"exists",
				side_effect=lambda *a, **k: None if a[:2] == ("DocType", "Task") else real(*a, **k),
			),
			patch.object(install.frappe, "logger") as logger,
		):
			install.ensure_setup()
		warnings = [c.args for c in logger.return_value.warning.call_args_list if "Task" in c.args[0]]
		self.assertEqual(len(warnings), 1)
		self.assertIn("not found", warnings[0][0])
		self.assertEqual(self._agent_task_perms(), [])
		self.assertIsNone(self._task_ticket_field())

	def test_agent_user_has_exact_roles_without_system_manager(self):
		user = frappe.get_doc("User", AGENT_USER)
		self.assertEqual(user.user_type, "System User")
		self.assertEqual(user.first_name, "ERP AI")
		self.assertTrue(frappe.db.get_value("Role", ROLE_AGENT, "desk_access"))
		self.assertTrue(frappe.db.get_value("Role", ROLE_INSTRUCTOR, "desk_access"))
		self.assertEqual(_agent_roles() - AUTOMATIC_ROLES, {ROLE_AGENT, HELPDESK_AGENT_ROLE})
		self.assertNotIn("System Manager", _agent_roles())
		self.assertFalse(frappe.db.get_value("User", AGENT_USER, "api_key"))

	def _new_user(self, email, roles):
		user = frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "erp_ai T33", "send_welcome_email": 0}
		)
		for role in roles:
			user.append("roles", {"role": role})
		return user.insert(ignore_permissions=True)

	def test_instructor_role_has_desk_access_and_makes_system_user(self):
		# AC-5, D-11: the approver reaches Desk only through the role's desk_access (no extra code).
		self.addCleanup(frappe.db.rollback)
		install.ensure_setup()
		self.assertEqual(frappe.db.get_value("Role", ROLE_INSTRUCTOR, "desk_access"), 1)
		instructor = self._new_user("erp-ai-t33-instructor@example.com", [ROLE_INSTRUCTOR])
		self.assertEqual([row.role for row in instructor.roles], [ROLE_INSTRUCTOR])
		self.assertEqual(instructor.user_type, "System User")
		no_desk_role = frappe.get_doc(
			{"doctype": "Role", "role_name": "erp_ai T33 no desk", "desk_access": 0}
		).insert(ignore_permissions=True)
		outsider = self._new_user("erp-ai-t33-outsider@example.com", [no_desk_role.name])
		self.assertEqual(outsider.user_type, "Website User")

	def test_user_missing_agent_role_gets_it_back(self):
		frappe.db.delete("Has Role", {"parent": AGENT_USER, "parenttype": "User", "role": ROLE_AGENT})
		self.assertNotIn(ROLE_AGENT, _agent_roles())
		install.ensure_setup()
		self.assertEqual(_agent_roles() - AUTOMATIC_ROLES, {ROLE_AGENT, HELPDESK_AGENT_ROLE})

	def test_setup_does_not_remove_extra_agent_role(self):
		frappe.get_doc("User", AGENT_USER).add_roles("Blogger")
		install.ensure_setup()
		self.assertIn("Blogger", _agent_roles())

	def test_default_settings_disabled_level_l0(self):
		self.assertEqual(int(frappe.db.get_single_value(SETTING_DOCTYPE, "enabled") or 0), 0)
		self.assertEqual(frappe.db.get_single_value(SETTING_DOCTYPE, "permission_level"), "L0")
		frappe.db.set_single_value(SETTING_DOCTYPE, "permission_level", "L2")
		frappe.db.set_single_value(SETTING_DOCTYPE, "max_turns_per_run", 3)
		install.ensure_setup()
		self.assertEqual(frappe.db.get_single_value(SETTING_DOCTYPE, "permission_level"), "L2")
		self.assertEqual(int(frappe.db.get_single_value(SETTING_DOCTYPE, "max_turns_per_run")), 3)

	def test_default_routing_rules_written_when_null(self):
		self.assertEqual(self._stored("routing_rules"), DEFAULT_ROUTING_RULES)
		self.assertEqual(self._stored("auto_assign_enabled"), "0")

	def test_default_routing_rules_not_overwritten(self):
		for kept in ('{"assignees": {}}', ""):
			with self.subTest(kept=kept):
				frappe.db.set_single_value(SETTING_DOCTYPE, "routing_rules", kept)
				frappe.db.set_single_value(SETTING_DOCTYPE, "auto_assign_enabled", 1)
				install.ensure_setup()
				install.after_migrate()
				self.assertEqual(self._stored("routing_rules"), kept)
				self.assertEqual(self._stored("auto_assign_enabled"), "1")

	def test_null_routing_rules_refilled(self):
		frappe.db.sql(
			"update `tabSingles` set value=NULL where doctype=%s "
			"and field in ('routing_rules', 'auto_assign_enabled')",
			SETTING_DOCTYPE,
		)
		install.ensure_setup()
		self.assertEqual(self._stored("routing_rules"), DEFAULT_ROUTING_RULES)
		self.assertEqual(self._stored("auto_assign_enabled"), "0")

	def test_cleared_default_is_refilled(self):
		frappe.db.sql(
			"update `tabSingles` set value=NULL where doctype=%s and field='permission_level'",
			SETTING_DOCTYPE,
		)
		install.ensure_setup()
		self.assertEqual(frappe.db.get_single_value(SETTING_DOCTYPE, "permission_level"), "L0")

	def _stored(self, fieldname):
		rows = frappe.db.sql(
			"select value from `tabSingles` where doctype=%s and field=%s", (SETTING_DOCTYPE, fieldname)
		)
		return rows[0][0] if rows else "<missing>"

	def test_status_defaults_filled_only_when_missing(self):
		self.assertEqual(self._stored("thinking_text"), "Đang suy nghĩ…")
		self.assertEqual(self._stored("answer_delay_min_s"), "3")
		self.assertEqual(self._stored("answer_delay_max_s"), "5")
		frappe.db.set_single_value(SETTING_DOCTYPE, "thinking_text", "Chờ chút")
		frappe.db.set_single_value(SETTING_DOCTYPE, "answer_delay_min_s", 0)
		frappe.db.set_single_value(SETTING_DOCTYPE, "answer_delay_max_s", 0)
		frappe.db.delete("Singles", {"doctype": SETTING_DOCTYPE, "field": "trigger_keyword"})
		install.ensure_setup()
		self.assertEqual(self._stored("thinking_text"), "Chờ chút")
		self.assertEqual(self._stored("answer_delay_min_s"), "0")
		self.assertEqual(self._stored("answer_delay_max_s"), "0")
		self.assertEqual(self._stored("trigger_keyword"), "@ai")

	def test_emptied_thinking_text_survives_setup(self):
		frappe.db.set_single_value(SETTING_DOCTYPE, "thinking_text", "")
		install.ensure_setup()
		install.after_migrate()
		self.assertEqual(self._stored("thinking_text"), "")

	def test_setup_never_writes_existing_tickets(self):
		ticket = make_ticket(subject="erp_ai T11 existing")
		frappe.get_doc(
			{
				"doctype": "HD Ticket Comment",
				"reference_ticket": ticket.name,
				"commented_by": "Administrator",
				"content": "existing comment",
			}
		).insert(ignore_permissions=True)
		before = _ticket_rows()
		self.assertTrue(before[0])
		self.assertTrue(before[1])
		install.ensure_setup()
		self.assertEqual(_ticket_rows(), before)

	def _script_file(self):
		path = frappe.get_app_path("erp_ai", *install.AGENT_STATUS_SCRIPT_FILE)
		with open(path, encoding="utf-8") as handle:
			return handle.read()

	def _status_script(self):
		return frappe.get_doc(install.FORM_SCRIPT_DOCTYPE, install.AGENT_STATUS_SCRIPT)

	def test_status_script_installed_once_matching_repo_file(self):
		install.ensure_setup()
		install.after_migrate()
		self.assertEqual(_counts()["status_scripts"], 1)
		doc = self._status_script()
		expected = {
			"dt": "HD Ticket",
			"apply_to": "Form",
			"enabled": 1,
			"apply_to_customer_portal": 0,
			"apply_on_new_page": 0,
			"is_standard": 0,
		}
		self.assertEqual(install.AGENT_STATUS_SCRIPT_FLAGS, expected)
		for key, value in expected.items():
			self.assertEqual(doc.get(key), value, key)
		self.assertEqual(doc.script, self._script_file())
		self.assertTrue(doc.script.strip())

	def test_status_script_reset_when_changed_on_site(self):
		for field, changed in (
			("script", "// edited by hand"),
			("enabled", 0),
			("apply_to_customer_portal", 1),
		):
			with self.subTest(field=field):
				frappe.db.set_value(install.FORM_SCRIPT_DOCTYPE, install.AGENT_STATUS_SCRIPT, field, changed)
				install.ensure_setup()
				self.assertEqual(_counts()["status_scripts"], 1)
				doc = self._status_script()
				self.assertEqual(doc.script, self._script_file())
				self.assertEqual(doc.enabled, 1)
				self.assertEqual(doc.apply_to_customer_portal, 0)

	def test_status_script_served_to_agent_page_only(self):
		self.assertIn(self._script_file(), get_form_script("HD Ticket") or [])
		self.assertNotIn(self._script_file(), get_form_script("HD Ticket", is_customer_portal=True) or [])

	def test_unchanged_status_script_is_not_saved_again(self):
		old = "2020-01-01 00:00:00"
		frappe.db.set_value(
			install.FORM_SCRIPT_DOCTYPE, install.AGENT_STATUS_SCRIPT, "modified", old, update_modified=False
		)
		install.ensure_setup()
		self.assertEqual(
			str(frappe.db.get_value(install.FORM_SCRIPT_DOCTYPE, install.AGENT_STATUS_SCRIPT, "modified")),
			old,
		)

	def test_uninstall_removes_only_status_script(self):
		# Same flags as the app's record, only the name differs: a human's identical script must survive.
		other = frappe.get_doc(
			{
				"doctype": install.FORM_SCRIPT_DOCTYPE,
				"name": "erp_ai test other script",
				**install.AGENT_STATUS_SCRIPT_FLAGS,
				"script": "function setupForm() { return {actions: []} }",
			}
		).insert(ignore_permissions=True)
		before = _counts()
		total_before = frappe.db.count(install.FORM_SCRIPT_DOCTYPE)
		install.before_uninstall()
		self.assertEqual(frappe.db.count(install.FORM_SCRIPT_DOCTYPE), total_before - 1)
		self.assertEqual(
			frappe.db.count(install.FORM_SCRIPT_DOCTYPE, {"name": install.AGENT_STATUS_SCRIPT}), 0
		)
		self.assertTrue(frappe.db.exists(install.FORM_SCRIPT_DOCTYPE, other.name))
		after = _counts()
		self.assertEqual(after.pop("status_scripts"), 0)
		before.pop("status_scripts")
		self.assertEqual(after, before)

	def test_missing_form_script_doctype_is_skipped_with_warning(self):
		real = frappe.db.exists

		def exists(*args, **kwargs):
			if args[:2] == ("DocType", install.FORM_SCRIPT_DOCTYPE):
				return None
			return real(*args, **kwargs)

		frappe.db.delete(install.FORM_SCRIPT_DOCTYPE, {"name": install.AGENT_STATUS_SCRIPT})
		with (
			patch.object(install.frappe.db, "exists", side_effect=exists),
			patch.object(install.frappe, "logger") as logger,
		):
			install.ensure_setup()
		warnings = [
			c.args
			for c in logger.return_value.warning.call_args_list
			if "not found" in c.args[0] and c.args[1] == install.FORM_SCRIPT_DOCTYPE
		]
		self.assertEqual(len(warnings), 1)
		self.assertEqual(_counts()["status_scripts"], 0)
		# Uninstall does nothing while the doctype is missing.
		install.ensure_setup()
		self.assertEqual(_counts()["status_scripts"], 1)
		with patch.object(install.frappe.db, "exists", side_effect=exists):
			install.before_uninstall()
		self.assertEqual(_counts()["status_scripts"], 1)

	def test_uninstall_without_record_is_noop(self):
		frappe.db.delete(install.FORM_SCRIPT_DOCTYPE, {"name": install.AGENT_STATUS_SCRIPT})
		install.before_uninstall()
		install.before_uninstall()
		self.assertEqual(_counts()["status_scripts"], 0)


def _stored_settings():
	return dict(frappe.db.sql("select field, value from `tabSingles` where doctype=%s", SETTING_DOCTYPE))


class TestFeat007Migrate(FrappeTestCase):
	def setUp(self):
		frappe.db.rollback()
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)
		# Custom fields already exist (migrate); never let a create path run DDL (implicit commit).
		patcher = patch.object(frappe.db, "updatedb")
		patcher.start()
		self.addCleanup(patcher.stop)

	def test_fresh_install_five_switches_off(self):
		frappe.db.delete("Singles", {"doctype": SETTING_DOCTYPE})
		install.ensure_setup()
		stored = _stored_settings()
		self.assertEqual(
			{name: stored.get(name, "<missing>") for name in FIVE_SWITCHES}, dict.fromkeys(FIVE_SWITCHES, "0")
		)

	def test_migrate_keeps_old_switches_new_switches_off(self):
		frappe.db.delete("Singles", {"doctype": SETTING_DOCTYPE, "field": ("in", FIVE_SWITCHES)})
		for name in OLD_SWITCHES:
			frappe.db.set_single_value(SETTING_DOCTYPE, name, 1)
		install.after_migrate()
		stored = _stored_settings()
		self.assertEqual(
			{name: stored.get(name, "<missing>") for name in FIVE_SWITCHES},
			{**dict.fromkeys(OLD_SWITCHES, "1"), **dict.fromkeys(NEW_SWITCHES, "0")},
		)

	def test_second_migrate_changes_nothing(self):
		frappe.db.delete("Singles", {"doctype": SETTING_DOCTYPE, "field": ("in", FIVE_SWITCHES)})
		frappe.db.set_single_value(SETTING_DOCTYPE, "code_change_enabled", 1)
		install.after_migrate()
		first = _stored_settings()
		self.assertLessEqual(set(FIVE_SWITCHES), set(first))
		install.after_migrate()
		self.assertEqual(_stored_settings(), first)

	def test_instructor_can_report_on_log(self):
		"""AC-20, D-5: ERP AI Instructor reads ERP AI Log through reports, nothing else (append-only kept)."""
		rows = [p for p in frappe.get_meta(LOG_DOCTYPE).permissions if p.role == ROLE_INSTRUCTOR]
		self.assertEqual(len(rows), 1)
		row = rows[0]
		self.assertEqual((row.permlevel, row.if_owner), (0, 0))
		checked = [right for right in frappe.permissions.rights if right != "select"]
		expected = {right: int(right in INSTRUCTOR_LOG_RIGHTS) for right in checked}
		self.assertEqual(
			{right: row.get(right) or 0 for right in checked},
			expected,
		)

		instructor = "feat007-instructor@example.com"
		frappe.local.role_permissions.clear()
		self.addCleanup(frappe.local.role_permissions.clear)
		with patch.object(frappe, "get_roles", return_value=[ROLE_INSTRUCTOR, "All", "Guest"]):
			effective = frappe.permissions.get_role_permissions(LOG_DOCTYPE, user=instructor)
		self.assertEqual(
			{right: effective[right] for right in checked},
			expected,
		)
