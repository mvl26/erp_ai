from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.agent.messages import add_message, history, thread
from erp_ai.constants import (
	AGENT_USER,
	MESSAGE_DOCTYPE,
	MESSAGE_KIND_CHAT,
	MESSAGE_KIND_RESULT,
)
from erp_ai.test_utils import pin_agent_roles

NO_ROLE_USER = "messages.norole@example.com"
HUMAN_USER = "messages.human@example.com"


def _make_user(email):
	if frappe.db.exists("User", email):
		return
	user = frappe.new_doc("User")
	user.update({"email": email, "first_name": email.split("@")[0], "send_welcome_email": 0})
	user.insert(ignore_permissions=True)


class TestMessages(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, frappe.session.user)
		frappe.set_user("Administrator")
		_make_user(NO_ROLE_USER)
		_make_user(HUMAN_USER)
		self.ticket = make_ticket().name

	def count(self):
		return frappe.db.count(MESSAGE_DOCTYPE, {"ticket": self.ticket})

	def test_trusted_insert_owned_by_session_user(self):
		frappe.set_user(NO_ROLE_USER)
		name = add_message(self.ticket, "xin chào", MESSAGE_KIND_CHAT, trusted=True)
		row = frappe.db.get_value(MESSAGE_DOCTYPE, name, ["owner", "kind"], as_dict=True)
		self.assertEqual((row.owner, row.kind), (NO_ROLE_USER, "chat"))

	def test_untrusted_insert_needs_create_permission(self):
		frappe.set_user(NO_ROLE_USER)
		with self.assertRaises(frappe.PermissionError):
			add_message(self.ticket, "xin chào", MESSAGE_KIND_CHAT)
		frappe.set_user("Administrator")
		self.assertEqual(self.count(), 0)

	def test_agent_account_inserts_untrusted(self):
		pin_agent_roles(self)
		frappe.set_user(AGENT_USER)
		name = add_message(self.ticket, "trả lời", MESSAGE_KIND_CHAT)
		self.assertTrue(frappe.db.exists(MESSAGE_DOCTYPE, name))

	def test_content_with_markup_stored_verbatim(self):
		text = "<b>x</b> & y < z"
		name = add_message(self.ticket, text, MESSAGE_KIND_CHAT, trusted=True)
		self.assertEqual(frappe.db.get_value(MESSAGE_DOCTYPE, name, "content"), text)
		self.assertEqual(thread(self.ticket)[-1]["text"], text)

	def test_rejects_unknown_kind_and_blank_content(self):
		for kind, content in (("note", "x"), (MESSAGE_KIND_CHAT, "  "), (MESSAGE_KIND_CHAT, None)):
			with self.subTest(kind=kind, content=content), self.assertRaises(ValueError):
				add_message(self.ticket, content, kind, trusted=True)
		self.assertEqual(self.count(), 0)

	def test_history_newest_first_with_limit(self):
		names = [add_message(self.ticket, f"tin {i}", MESSAGE_KIND_CHAT, trusted=True) for i in range(3)]
		for i, name in enumerate(names):
			frappe.db.set_value(MESSAGE_DOCTYPE, name, "creation", f"2001-01-0{i + 1} 10:00:00")
		rows = history(self.ticket, limit=2)
		self.assertEqual([row["name"] for row in rows], [names[2], names[1]])
		self.assertEqual(set(rows[0]), {"name", "author", "creation", "content", "kind"})
		self.assertEqual(rows[0]["author"], "Administrator")
		self.assertEqual(rows[0]["content"], "tin 2")

	def test_thread_oldest_first_marks_bot_and_system_kinds(self):
		frappe.set_user(HUMAN_USER)
		human = add_message(self.ticket, "hỏi", MESSAGE_KIND_CHAT, trusted=True)
		result = add_message(self.ticket, "đã duyệt", MESSAGE_KIND_RESULT, trusted=True)
		frappe.set_user(AGENT_USER)
		bot = add_message(self.ticket, "trả lời", MESSAGE_KIND_CHAT, trusted=True)
		for i, name in enumerate((human, result, bot)):
			frappe.db.set_value(MESSAGE_DOCTYPE, name, "creation", f"2001-01-0{i + 1} 10:00:00")
		frappe.set_user("Administrator")
		rows = thread(self.ticket)
		self.assertEqual([row["name"] for row in rows], [human, result, bot])
		self.assertEqual([row["is_bot"] for row in rows], [False, True, True])
		self.assertEqual(set(rows[0]), {"name", "author", "is_bot", "kind", "created_at", "text"})
		self.assertEqual(rows[0]["text"], "hỏi")
		self.assertEqual(rows[0]["author"], frappe.utils.get_fullname(HUMAN_USER))

	def test_add_message_never_commits(self):
		with patch.object(frappe.db, "commit", side_effect=AssertionError("commit")):
			add_message(self.ticket, "xin chào", MESSAGE_KIND_CHAT, trusted=True)
