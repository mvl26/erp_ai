from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai import install
from erp_ai.constants import (
	AGENT_USER,
	HELPDESK_AGENT_ROLE,
	LOGGER_NAME,
	ROLE_AGENT,
	ROLE_INSTRUCTOR,
	SETTING_DOCTYPE,
)

AI_FIELDS = (
	"ai_section",
	"ai_resolution_hint",
	"ai_confidence",
	"ai_classified_by",
	"ai_updated_at",
	"ai_opt_out",
)
TEMPLATE = "Default"

AUTOMATIC_ROLES = {"Guest", "All", "Administrator", "Desk User"}


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
		install.ensure_setup()

	def test_setup_twice_is_idempotent(self):
		before = _counts()
		install.ensure_setup()
		install.after_migrate()
		self.assertEqual(_counts(), before)
		self.assertEqual(before["roles"], 2)
		self.assertEqual(before["users"], 1)
		self.assertEqual(before["ai_fields"], 6)

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
		self.assertEqual(len(rows), 5)
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
		self.assertEqual(len(rows), 6)
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
		self.assertEqual([r.idx for r in rows], [1, 2, 3, 4, 5, 6])
		self.assertEqual(
			[r.fieldname for r in rows[1:]],
			["ai_resolution_hint", "ai_confidence", "ai_classified_by", "ai_updated_at", "ai_opt_out"],
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

	def test_agent_user_has_exact_roles_without_system_manager(self):
		user = frappe.get_doc("User", AGENT_USER)
		self.assertEqual(user.user_type, "System User")
		self.assertEqual(user.first_name, "ERP AI")
		self.assertTrue(frappe.db.get_value("Role", ROLE_AGENT, "desk_access"))
		self.assertTrue(frappe.db.get_value("Role", ROLE_INSTRUCTOR, "desk_access"))
		self.assertEqual(_agent_roles() - AUTOMATIC_ROLES, {ROLE_AGENT, HELPDESK_AGENT_ROLE})
		self.assertNotIn("System Manager", _agent_roles())
		self.assertFalse(frappe.db.get_value("User", AGENT_USER, "api_key"))

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

	def test_cleared_default_is_refilled(self):
		frappe.db.sql(
			"update `tabSingles` set value=NULL where doctype=%s and field='permission_level'",
			SETTING_DOCTYPE,
		)
		install.ensure_setup()
		self.assertEqual(frappe.db.get_single_value(SETTING_DOCTYPE, "permission_level"), "L0")

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
