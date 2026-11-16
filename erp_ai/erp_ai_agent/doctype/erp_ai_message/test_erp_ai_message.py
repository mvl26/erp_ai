import json
from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import create_agent, make_ticket

from erp_ai.agent.messages import add_message
from erp_ai.constants import MESSAGE_DOCTYPE, ROLE_AGENT, ROLE_INSTRUCTOR

JSON_PATH = Path(__file__).resolve().parent / "erp_ai_message.json"
# A message is one thing said in the conversation with the bot: no kind, no link to anything but its ticket.
FIELD_TYPES = {
	"ticket": "Link",
	"content": "Code",
	"run_id": "Data",
	"source_comment": "Data",
}
LAYOUT_TYPES = ("Section Break", "Column Break", "Tab Break")
GRANTED = (
	{"read": 1, "report": 1, "role": "System Manager"},
	{"create": 1, "read": 1, "role": ROLE_AGENT},
	{"read": 1, "report": 1, "role": ROLE_INSTRUCTOR},
)


def _load() -> dict:
	return json.loads(JSON_PATH.read_text(encoding="utf-8"))


class TestERPAIMessage(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, frappe.session.user)
		frappe.set_user("Administrator")

	def test_doctype_json_fields_and_module(self):
		doctype = _load()
		self.assertEqual(doctype["name"], MESSAGE_DOCTYPE)
		self.assertEqual(doctype["module"], "ERP AI agent")
		self.assertEqual(doctype["autoname"], "hash")
		fields = {f["fieldname"]: f for f in doctype["fields"] if f["fieldtype"] not in LAYOUT_TYPES}
		self.assertEqual({name: f["fieldtype"] for name, f in fields.items()}, FIELD_TYPES)
		self.assertEqual(
			doctype["field_order"],
			["section_message", "ticket", "content", "section_source", "run_id", "source_comment"],
		)
		self.assertEqual(fields["ticket"]["options"], "HD Ticket")
		# every read is by ticket: the panel, each run, the weekly KPI
		self.assertEqual(fields["ticket"].get("search_index"), 1)
		for name, field in fields.items():
			self.assertEqual(field.get("read_only"), 1, name)
		for name in ("ticket", "content"):
			self.assertEqual(fields[name].get("reqd"), 1, name)

	def test_permissions_exact(self):
		permissions = _load()["permissions"]
		self.assertCountEqual(permissions, GRANTED)
		for row in permissions:
			self.assertNotIn("write", row)
			self.assertNotIn("delete", row)
			self.assertNotEqual(row["role"], "Agent")

	def test_helpdesk_agent_cannot_read_messages(self):
		email = "plain.agent@example.com"
		create_agent(email)
		frappe.set_user(email)
		self.assertFalse(frappe.has_permission(MESSAGE_DOCTYPE, "read"))
		with self.assertRaises(frappe.PermissionError):
			frappe.get_list(MESSAGE_DOCTYPE)

	def test_saved_message_cannot_be_changed(self):
		ticket = make_ticket()
		doc = frappe.get_doc(MESSAGE_DOCTYPE, add_message(ticket.name, "xin chào", trusted=True))
		doc.content = "đã sửa"
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)

	def test_deleting_a_ticket_deletes_its_conversation(self):
		# The conversation goes with its ticket, as the ticket's comments do; another ticket's stays.
		ticket = make_ticket()
		other = make_ticket()
		add_message(ticket.name, "xin chào", trusted=True)
		kept = add_message(other.name, "phiếu khác", trusted=True)

		frappe.delete_doc("HD Ticket", ticket.name, ignore_permissions=True)

		self.assertFalse(frappe.db.exists("HD Ticket", ticket.name))
		self.assertEqual(frappe.db.count(MESSAGE_DOCTYPE, {"ticket": ticket.name}), 0)
		self.assertTrue(frappe.db.exists(MESSAGE_DOCTYPE, kept))
