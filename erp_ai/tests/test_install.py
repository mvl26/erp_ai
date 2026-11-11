import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai import install
from erp_ai.constants import AGENT_USER, HELPDESK_AGENT_ROLE, ROLE_AGENT, ROLE_INSTRUCTOR, SETTING_DOCTYPE

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
		install.ensure_setup()

	def test_setup_twice_is_idempotent(self):
		before = _counts()
		install.ensure_setup()
		install.after_migrate()
		self.assertEqual(_counts(), before)
		self.assertEqual(before["roles"], 2)
		self.assertEqual(before["users"], 1)

	def test_agent_user_has_exact_roles_without_system_manager(self):
		user = frappe.get_doc("User", AGENT_USER)
		self.assertEqual(user.user_type, "System User")
		self.assertEqual(user.first_name, "ERP AI")
		self.assertTrue(frappe.db.get_value("Role", ROLE_AGENT, "desk_access"))
		self.assertTrue(frappe.db.get_value("Role", ROLE_INSTRUCTOR, "desk_access"))
		self.assertEqual(_agent_roles() - AUTOMATIC_ROLES, {ROLE_AGENT, HELPDESK_AGENT_ROLE})
		self.assertNotIn("System Manager", _agent_roles())

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

	def test_setup_never_writes_existing_tickets(self):
		before = _ticket_rows()
		install.ensure_setup()
		self.assertEqual(_ticket_rows(), before)
