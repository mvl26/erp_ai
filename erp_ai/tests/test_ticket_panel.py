import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import create_agent, make_ticket
from helpdesk.utils import is_agent

from erp_ai import ticket_panel
from erp_ai.constants import PANEL_METHODS

AI_FIELD_LABELS = (
	("ai_resolution_hint", "Hướng giải quyết (AI)"),
	("ai_confidence", "Độ tin cậy (AI)"),
	("ai_classified_by", "Phân loại bởi"),
	("ai_updated_at", "AI cập nhật lúc"),
)
AGENT_EMAIL = "panel.agent@example.com"
NO_READ_EMAIL = "panel.noread@example.com"
INACTIVE_EMAIL = "panel.inactive@example.com"
WEBSITE_EMAIL = "panel.website@example.com"
CUSTOMER_EMAIL = "panel.customer@example.com"


def _make_user(email, user_type="Website User"):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0],
				"user_type": user_type,
				"send_welcome_email": 0,
			}
		).insert(ignore_permissions=True)
	return email


class TestTicketPanelRead(FrappeTestCase):
	def setUp(self):
		# FrappeTestCase rolls back only after the whole class: undo each test.
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		create_agent(AGENT_EMAIL)
		self.ticket = make_ticket(subject="Panel read ticket")

	def _read(self, user=AGENT_EMAIL, ticket=None):
		frappe.set_user(user)
		return ticket_panel.get_panel_data(ticket or self.ticket.name)

	def test_methods_whitelisted_post_without_guest(self):
		method = PANEL_METHODS[0]
		self.assertEqual(method, "erp_ai.ticket_panel.get_panel_data")
		self.assertIn("erp_ai.ticket_panel.send_message", PANEL_METHODS)
		fn = frappe.get_attr(method)
		self.assertIn(fn, frappe.whitelisted)
		self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[fn], ["POST"])
		self.assertNotIn(fn, frappe.guest_methods)

	def test_read_returns_ai_fields_as_stored_text(self):
		frappe.db.set_value(
			"HD Ticket",
			self.ticket.name,
			{
				"ai_resolution_hint": "<p>Dòng 1</p><p>Dòng 2</p>",
				"ai_confidence": "Cao",
				"ai_classified_by": "AI",
				"ai_updated_at": "2026-11-12 10:05:00",
			},
		)
		data = self._read()
		self.assertEqual(data["ticket"], self.ticket.name)
		self.assertEqual(data["messages"], [])
		by_name = {item["fieldname"]: item["text"] for item in data["ai_fields"]}
		self.assertEqual(by_name["ai_resolution_hint"].split(), ["Dòng", "1", "Dòng", "2"])
		self.assertIn("\n", by_name["ai_resolution_hint"].strip())
		self.assertEqual(by_name["ai_confidence"], "Cao")
		self.assertEqual(by_name["ai_classified_by"], "AI")
		self.assertEqual(by_name["ai_updated_at"], "12-11-2026 10:05:00")

	def test_read_empty_ai_fields_are_null(self):
		data = self._read()
		self.assertEqual(len(data["ai_fields"]), 4)
		for item in data["ai_fields"]:
			with self.subTest(field=item["fieldname"]):
				self.assertIsNone(item["text"])

	def test_read_ai_fields_use_hd_ticket_labels(self):
		data = self._read()
		self.assertEqual(
			[(item["fieldname"], item["label"]) for item in data["ai_fields"]], list(AI_FIELD_LABELS)
		)

	def test_read_denied_for_non_agents_and_guest(self):
		_make_user(WEBSITE_EMAIL)
		for user in (WEBSITE_EMAIL, "Guest"):
			with self.subTest(user=user), self.assertRaises(frappe.PermissionError):
				self._read(user)

	def test_read_denied_for_customer_who_can_read_the_ticket(self):
		# Only a non-agent that HD Ticket's permission hook lets in shows that the is_agent() gate is needed.
		_make_user(CUSTOMER_EMAIL)
		frappe.get_doc("User", CUSTOMER_EMAIL).add_roles("HD Customer")
		ticket = make_ticket(subject="Customer own ticket", raised_by=CUSTOMER_EMAIL)
		frappe.set_user(CUSTOMER_EMAIL)
		self.assertFalse(is_agent())
		self.assertTrue(frappe.has_permission("HD Ticket", "read", doc=ticket.name))
		with self.assertRaises(frappe.PermissionError):
			ticket_panel.get_panel_data(ticket.name)

	def test_read_rejects_empty_or_wrong_type_ticket(self):
		frappe.set_user(AGENT_EMAIL)
		for value in ("", "   "):
			with self.subTest(ticket=value), self.assertRaises(frappe.ValidationError):
				ticket_panel.get_panel_data(value)

	def test_read_hides_fields_above_the_callers_permlevel(self):
		frappe.db.set_value("HD Ticket", self.ticket.name, "ai_updated_at", "2026-11-12 10:05:00")
		self.assertEqual(self._read()["ai_fields"][3]["text"], "12-11-2026 10:05:00")
		self.addCleanup(frappe.clear_cache, doctype="HD Ticket")
		permlevel = frappe.get_meta("HD Ticket").get_field("ai_updated_at").permlevel
		frappe.permissions.update_permission_property("HD Ticket", "Agent", permlevel, "read", 0)
		frappe.clear_cache(doctype="HD Ticket")
		self.assertIsNone(self._read()["ai_fields"][3]["text"])

	def test_read_denied_for_agent_without_ticket_read(self):
		frappe.set_user("Administrator")
		create_agent(NO_READ_EMAIL)
		frappe.get_doc("User", NO_READ_EMAIL).remove_roles("Agent", "Agent Manager")
		frappe.set_user(NO_READ_EMAIL)
		self.assertTrue(is_agent())
		self.assertFalse(frappe.has_permission("HD Ticket", "read", doc=self.ticket.name))
		with self.assertRaises(frappe.PermissionError):
			ticket_panel.get_panel_data(self.ticket.name)

	def test_inactive_hd_agent_denied(self):
		create_agent(INACTIVE_EMAIL)
		frappe.db.set_value("HD Agent", INACTIVE_EMAIL, "is_active", 0)
		with self.assertRaises(frappe.PermissionError):
			self._read(INACTIVE_EMAIL)

	def test_read_denied_for_missing_ticket(self):
		with self.assertRaises(frappe.PermissionError):
			self._read(ticket="999999999")
