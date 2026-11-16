import json
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.constants import LESSON_DOCTYPE, LESSON_SOURCE_TEACHING, LESSON_STATUS_PENDING, ROLE_INSTRUCTOR

DOCTYPE_JSON = Path(__file__).with_name("erp_ai_lesson.json")


class TestERPAILesson(FrappeTestCase):
	def setUp(self):
		frappe.db.rollback()
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("test must not commit"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")

	def test_no_role_can_create_or_write(self):
		permissions = json.loads(DOCTYPE_JSON.read_text(encoding="utf-8"))["permissions"]
		self.assertEqual({row["role"] for row in permissions}, {"System Manager", ROLE_INSTRUCTOR})
		for row in permissions:
			granted = {key for key, value in row.items() if key != "role" and value}
			self.assertEqual(granted, {"read"}, row["role"])

	def test_ticket_with_lesson_can_be_deleted(self):
		ticket = make_ticket(subject="erp_ai lesson ticket delete")
		doc = frappe.get_doc(
			{
				"doctype": LESSON_DOCTYPE,
				"lesson_status": LESSON_STATUS_PENDING,
				"lesson_source": LESSON_SOURCE_TEACHING,
				"situation": "tình huống thử",
				"lesson_text": "bài học thử",
				"ticket": ticket.name,
			}
		)
		doc.flags.erp_ai_lesson_store = True
		doc.insert(ignore_permissions=True)
		frappe.delete_doc("HD Ticket", ticket.name, force=False)
		self.assertFalse(frappe.db.exists("HD Ticket", ticket.name))
		self.assertTrue(frappe.db.exists(LESSON_DOCTYPE, doc.name))
