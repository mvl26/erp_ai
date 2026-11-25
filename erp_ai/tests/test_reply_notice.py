from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import create_agent, make_ticket, make_todo

from erp_ai import install
from erp_ai.agent import messages
from erp_ai.constants import AGENT_USER, BOT_REPLY_NOTIFICATION_TYPE
from erp_ai.test_utils import keep_agent_settings, set_agent_settings

NOTIFICATION_LOG = "Notification Log"
ASSIGNEE = "reply-notice-assignee@example.com"
TALKER = "reply-notice-talker@example.com"
BYSTANDER = "reply-notice-bystander@example.com"
# ensure_setup's other steps, stubbed when only checking that it registers the notification type.
_OTHER_SETUP_STEPS = (
	"_ensure_roles",
	"_ensure_agent_user",
	"_ensure_ticket_custom_fields",
	"_ensure_template_rows",
	"_ensure_task_ticket_field",
	"_ensure_article_source_field",
	"_ensure_task_permission",
	"_ensure_article_instructor_permission",
	"_ensure_agent_status_script",
)


class TestReplyNotice(FrappeTestCase):
	"""Each bot message in a ticket's chat is one unread notice for the ticket's assignees and the people
	who wrote in that chat; helpdesk's Miyano bot counts them on its badge."""

	def setUp(self):
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("test must not commit"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		keep_agent_settings(self)
		# A person's message must not start a real bot run here.
		set_agent_settings(enabled=0)
		install._ensure_bot_reply_notification_type()
		for user in (ASSIGNEE, TALKER, BYSTANDER):
			create_agent(user)
		self.ticket = make_ticket(subject="reply notice").name
		make_todo(self.ticket, ASSIGNEE)

	def _say(self, user, text, ticket=None):
		frappe.set_user(user)
		try:
			return messages.add_message(ticket or self.ticket, text, trusted=True)
		finally:
			frappe.set_user("Administrator")

	def _notices(self, user, ticket=None):
		return frappe.get_all(
			NOTIFICATION_LOG,
			filters={
				"for_user": user,
				"type": BOT_REPLY_NOTIFICATION_TYPE,
				"document_name": ticket or self.ticket,
			},
			fields=["read", "source_name", "from_user", "document_type"],
			order_by="creation asc",
		)

	def test_setup_registers_the_notification_type(self):
		self.assertTrue(frappe.db.exists("Notification Type", BOT_REPLY_NOTIFICATION_TYPE))
		with patch.object(install, "_ensure_bot_reply_notification_type") as ensure_type:
			with patch.multiple(install, **{name: lambda: None for name in _OTHER_SETUP_STEPS}):
				install.ensure_setup()
		ensure_type.assert_called_once_with()

	def test_bot_message_notifies_assignees_and_people_of_the_chat(self):
		self._say(TALKER, "Bot ơi, kiểm tra giúp")
		reply = self._say(AGENT_USER, "Đã nhận, đang kiểm tra.")
		expected = [{"read": 0, "source_name": reply, "from_user": AGENT_USER, "document_type": "HD Ticket"}]
		self.assertEqual(self._notices(ASSIGNEE), expected)
		self.assertEqual(self._notices(TALKER), expected)
		self.assertEqual(self._notices(BYSTANDER), [])
		self.assertEqual(self._notices(AGENT_USER), [])

	def test_each_bot_message_is_one_notice(self):
		self._say(AGENT_USER, "Tin 1")
		self._say(AGENT_USER, "Tin 2")
		self._say(AGENT_USER, "Tin 3")
		self.assertEqual(len(self._notices(ASSIGNEE)), 3)

	def test_a_notice_sends_no_email(self):
		self.assertIn(BOT_REPLY_NOTIFICATION_TYPE, frappe.get_hooks("notification_skip_email_types"))
		with patch.object(frappe, "sendmail") as sendmail:
			self._say(AGENT_USER, "Đã nhận.")
		self.assertEqual(len(self._notices(ASSIGNEE)), 1)
		sendmail.assert_not_called()

	def test_a_persons_message_notifies_nobody(self):
		self._say(TALKER, "Bot ơi")
		self.assertFalse(
			frappe.db.exists(
				NOTIFICATION_LOG, {"type": BOT_REPLY_NOTIFICATION_TYPE, "document_name": self.ticket}
			)
		)
