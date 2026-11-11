import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.constants import LOG_DOCTYPE


class TestTicketDeleteKeepsLog(FrappeTestCase):
	def setUp(self):
		# FrappeTestCase rolls back only after the whole class: undo each test.
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")

	def _ticket_with_log(self):
		ticket = make_ticket(subject="T11b delete ticket")
		log = frappe.get_doc(
			{
				"doctype": LOG_DOCTYPE,
				"ticket": ticket.name,
				"run_id": "t11b",
				"entry_type": "classify",
				"turn": 0,
			}
		).insert(ignore_permissions=True)
		return ticket, log

	def test_ticket_with_log_can_be_deleted_and_log_survives(self):
		ticket, log = self._ticket_with_log()

		frappe.delete_doc("HD Ticket", ticket.name, force=False)

		self.assertFalse(frappe.db.exists("HD Ticket", ticket.name))
		self.assertTrue(frappe.db.exists(LOG_DOCTYPE, log.name))
		self.assertEqual(frappe.db.get_value(LOG_DOCTYPE, log.name, "ticket"), ticket.name)

	def test_log_doctype_still_has_no_delete_permission(self):
		for perm in frappe.get_meta(LOG_DOCTYPE).permissions:
			with self.subTest(role=perm.role):
				self.assertFalse(perm.get("delete"))
