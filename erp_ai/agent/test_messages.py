from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.agent.messages import add_message, history, thread, typed_by_people
from erp_ai.constants import AGENT_USER, MESSAGE_DOCTYPE
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
		name = add_message(self.ticket, "xin chào", trusted=True)
		self.assertEqual(frappe.db.get_value(MESSAGE_DOCTYPE, name, "owner"), NO_ROLE_USER)

	def test_untrusted_insert_needs_create_permission(self):
		frappe.set_user(NO_ROLE_USER)
		with self.assertRaises(frappe.PermissionError):
			add_message(self.ticket, "xin chào")
		frappe.set_user("Administrator")
		self.assertEqual(self.count(), 0)

	def test_agent_account_inserts_untrusted(self):
		pin_agent_roles(self)
		frappe.set_user(AGENT_USER)
		name = add_message(self.ticket, "trả lời")
		self.assertTrue(frappe.db.exists(MESSAGE_DOCTYPE, name))

	def test_run_id_and_source_comment_are_stored(self):
		name = add_message(self.ticket, "x", run_id="run-1", source_comment="comment-1", trusted=True)
		row = frappe.db.get_value(MESSAGE_DOCTYPE, name, ["run_id", "source_comment"], as_dict=True)
		self.assertEqual((row.run_id, row.source_comment), ("run-1", "comment-1"))

	def test_content_with_markup_stored_verbatim(self):
		text = "<b>x</b> & y < z"
		name = add_message(self.ticket, text, trusted=True)
		self.assertEqual(frappe.db.get_value(MESSAGE_DOCTYPE, name, "content"), text)
		self.assertEqual(thread(self.ticket)[-1]["text"], text)

	def test_rejects_blank_content(self):
		for content in ("  ", "", None, 7):
			with self.subTest(content=content), self.assertRaises(ValueError):
				add_message(self.ticket, content, trusted=True)
		self.assertEqual(self.count(), 0)

	def test_history_newest_first_with_limit(self):
		names = [add_message(self.ticket, f"tin {i}", trusted=True) for i in range(3)]
		for i, name in enumerate(names):
			frappe.db.set_value(MESSAGE_DOCTYPE, name, "creation", f"2001-01-0{i + 1} 10:00:00")
		rows = history(self.ticket, limit=2)
		self.assertEqual([row["name"] for row in rows], [names[2], names[1]])
		self.assertEqual(set(rows[0]), {"name", "author", "creation", "content"})
		self.assertEqual(rows[0]["author"], "Administrator")
		self.assertEqual(rows[0]["content"], "tin 2")

	def test_thread_oldest_first_marks_the_bot(self):
		frappe.set_user(HUMAN_USER)
		human = add_message(self.ticket, "hỏi", trusted=True)
		frappe.set_user(AGENT_USER)
		bot = add_message(self.ticket, "trả lời", trusted=True)
		for i, name in enumerate((human, bot)):
			frappe.db.set_value(MESSAGE_DOCTYPE, name, "creation", f"2001-01-0{i + 1} 10:00:00")
		frappe.set_user("Administrator")
		rows = thread(self.ticket)
		self.assertEqual([row["name"] for row in rows], [human, bot])
		self.assertEqual([row["is_bot"] for row in rows], [False, True])
		self.assertEqual(set(rows[0]), {"name", "author", "is_bot", "created_at", "text", "kind"})
		self.assertEqual([row["kind"] for row in rows], ["", ""])
		self.assertEqual(rows[0]["text"], "hỏi")
		self.assertEqual(rows[0]["author"], frappe.utils.get_fullname(HUMAN_USER))

	def test_typed_by_people_leaves_out_the_bot_and_comment_copies(self):
		add_message(self.ticket, "người gõ", trusted=True)
		add_message(self.ticket, "bản chép của comment", source_comment="comment-1", trusted=True)
		frappe.set_user(AGENT_USER)
		add_message(self.ticket, "bot đáp", trusted=True)
		frappe.set_user("Administrator")

		rows = typed_by_people(self.ticket)

		self.assertEqual([row["content"] for row in rows], ["người gõ"])
		self.assertEqual(set(rows[0]), {"creation", "content"})

	def test_typed_by_people_after_a_time_newest_first_with_limit(self):
		names = [add_message(self.ticket, f"tin {i}", trusted=True) for i in range(4)]
		for i, name in enumerate(names):
			frappe.db.set_value(MESSAGE_DOCTYPE, name, "creation", f"2001-01-0{i + 1} 10:00:00")

		rows = typed_by_people(self.ticket, after="2001-01-01 10:00:00", limit=2)

		self.assertEqual([row["content"] for row in rows], ["tin 3", "tin 2"])
		self.assertEqual(len(typed_by_people(self.ticket)), 4)

	def test_add_message_never_commits(self):
		with patch.object(frappe.db, "commit", side_effect=AssertionError("commit")):
			add_message(self.ticket, "xin chào", trusted=True)
