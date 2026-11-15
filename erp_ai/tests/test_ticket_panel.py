import json
from typing import ClassVar
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import create_agent, make_ticket, make_todo
from helpdesk.utils import is_agent

from erp_ai import ticket_panel
from erp_ai.agent import answer_delay, policy, runner
from erp_ai.agent.policy import contains_keyword
from erp_ai.agent.queue import PENDING_JOB_IDS_FLAG
from erp_ai.agent.run_log import write_entry
from erp_ai.constants import (
	AGENT_USER,
	LOG_DOCTYPE,
	LOGGER_NAME,
	PANEL_METHODS,
	ROLE_INSTRUCTOR,
	TITLE_RUN_FAILED,
)
from erp_ai.test_utils import FakeGateway, make_model_result, record_status_signals, set_agent_settings

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
KEYWORD = "@ai"
THREAD_KEYS = {"name", "author", "is_bot", "created_at", "text"}


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


def _add_comment(ticket, content, owner="Administrator", creation=None, comment_type="Comment"):
	"""A Comment as the timeline stores it; owner and creation are set directly, like the DB would hold them."""
	with patch.object(frappe, "enqueue"):
		doc = frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": comment_type,
				"reference_doctype": "HD Ticket",
				"reference_name": ticket,
				"content": "placeholder",
			}
		).insert(ignore_permissions=True)
	values = {"content": content, "owner": owner}
	if creation:
		values["creation"] = creation
	frappe.db.set_value("Comment", doc.name, values, update_modified=False)
	return doc.name


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
		self.assertEqual(
			PANEL_METHODS, ("erp_ai.ticket_panel.get_panel_data", "erp_ai.ticket_panel.send_message")
		)
		for method in PANEL_METHODS:
			with self.subTest(method=method):
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


class TestTicketPanelThread(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		create_agent(AGENT_EMAIL)
		set_agent_settings(trigger_keyword=KEYWORD)
		self.ticket = make_ticket(subject="Panel thread ticket").name

	def _messages(self):
		frappe.set_user(AGENT_EMAIL)
		return ticket_panel.get_panel_data(self.ticket)["messages"]

	def test_thread_selects_b5_comments_in_creation_order(self):
		# AC-8 data: 3 human keyword (1 other case), 2 human plain, 2 agent, 1 keyword on ANOTHER ticket.
		# Inserted out of order on purpose: the result must follow `creation`, not insertion.
		other_ticket = make_ticket(subject="Another ticket").name
		late = _add_comment(self.ticket, f"{KEYWORD} late human", creation="2026-11-12 10:05:00")
		_add_comment(self.ticket, "plain human chat", creation="2026-11-12 10:01:00")
		bot_plain = _add_comment(self.ticket, "bot says hi", AGENT_USER, "2026-11-12 10:03:00")
		early = _add_comment(self.ticket, f"early {KEYWORD.upper()} human", creation="2026-11-12 10:02:00")
		_add_comment(self.ticket, "another plain human", creation="2026-11-12 10:04:00")
		bot_kw = _add_comment(self.ticket, f"bot {KEYWORD}", AGENT_USER, "2026-11-12 10:06:00")
		last = _add_comment(self.ticket, f"last {KEYWORD} human", creation="2026-11-12 10:07:00")
		_add_comment(other_ticket, f"{KEYWORD} on another ticket", creation="2026-11-12 10:04:30")

		messages = self._messages()

		self.assertEqual([m["name"] for m in messages], [early, bot_plain, late, bot_kw, last])
		for message in messages:
			self.assertEqual(set(message), THREAD_KEYS)
			self.assertNotIn("@", message["author"])
		self.assertEqual(messages[0]["text"], f"early {KEYWORD.upper()} human")
		self.assertEqual(messages[0]["created_at"], frappe.utils.format_datetime("2026-11-12 10:02:00"))
		self.assertRegex(messages[0]["created_at"], r"^\d{2}-\d{2}-\d{4} 10:02:00$")
		self.assertEqual(messages[0]["author"], frappe.utils.get_fullname("Administrator"))

	def test_thread_selects_nothing_for_humans_when_keyword_is_empty(self):
		set_agent_settings(trigger_keyword="")
		_add_comment(self.ticket, f"{KEYWORD} human")
		bot = _add_comment(self.ticket, "bot reply", AGENT_USER)
		self.assertEqual([m["name"] for m in self._messages()], [bot])

	def test_thread_ignores_non_comment_types(self):
		for comment_type in ("Info", "Assignment Completed", "Like", "Label"):
			_add_comment(self.ticket, f"{KEYWORD} {comment_type}", comment_type=comment_type)
		_add_comment(self.ticket, "bot info", AGENT_USER, comment_type="Info")
		kept = _add_comment(self.ticket, f"{KEYWORD} real comment")
		self.assertEqual([m["name"] for m in self._messages()], [kept])

	def test_thread_marks_bot_messages(self):
		_add_comment(self.ticket, f"{KEYWORD} human", creation="2026-11-12 10:00:00")
		_add_comment(self.ticket, "bot answer", AGENT_USER, "2026-11-12 10:01:00")
		messages = self._messages()
		self.assertEqual([m["is_bot"] for m in messages], [False, True])
		self.assertEqual(messages[1]["author"], frappe.utils.get_fullname(AGENT_USER))

	def test_read_strips_xss_payloads_to_text(self):
		payload = (
			f'<script>alert(1)</script><img src=x onerror="alert(2)">'
			f'<a href="javascript:alert(3)">link</a> <b>{KEYWORD}</b> bold'
		)
		_add_comment(self.ticket, payload)
		_add_comment(self.ticket, f"<p>one</p><p>two</p>{payload}", AGENT_USER)
		xss, bot = self._messages()
		# Markup that can run (img/a handlers, javascript: urls) is gone; whatever text is left (an escaped
		# <script> literal) is inert because the page renders it with textContent only.
		for message in (xss, bot):
			with self.subTest(is_bot=message["is_bot"]):
				for tag in ("<img", "<a ", "</a", "<b>"):
					self.assertNotIn(tag, message["text"])
				self.assertNotIn("onerror", message["text"])
				self.assertNotIn("javascript:", message["text"])
				self.assertIn("link", message["text"])
				self.assertEqual(message["text"].split()[-3:], ["link", KEYWORD, "bold"])
		self.assertEqual(bot["text"].split()[:2], ["one", "two"])


class TestTicketPanelReadOnly(FrappeTestCase):
	"""AC-14, NFR-4, STD-OPS-5: the read changes nothing, calls no model, and logs ids only."""

	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		create_agent(AGENT_EMAIL)
		set_agent_settings(trigger_keyword=KEYWORD)
		self.ticket = make_ticket(subject="Panel read-only ticket").name

	def _logger(self):
		logger = MagicMock()
		patcher = patch.object(ticket_panel.frappe, "logger", return_value=logger)
		get_logger = patcher.start()
		self.addCleanup(patcher.stop)
		return logger, get_logger

	def _counts(self):
		return {
			"comments": frappe.db.count("Comment"),
			"logs": frappe.db.count("ERP AI Log"),
			"todos": frappe.db.count("ToDo"),
			"tasks": frappe.db.count("Task"),
			"modified": frappe.db.get_value("HD Ticket", self.ticket, "modified"),
		}

	def test_read_writes_nothing_and_calls_no_gateway(self):
		_add_comment(self.ticket, f"{KEYWORD} human")
		_add_comment(self.ticket, "bot reply", AGENT_USER)
		gateway = FakeGateway()
		frappe.set_user(AGENT_EMAIL)
		self.assertNotEqual(frappe.session.user, "Administrator")
		before = self._counts()
		with patch("erp_ai.gateway.call_model", gateway), patch("frappe.enqueue") as enqueue:
			for _ in range(3):
				writes = frappe.db.transaction_writes
				ticket_panel.get_panel_data(self.ticket)
				self.assertEqual(frappe.db.transaction_writes, writes)
		self.assertEqual(self._counts(), before)
		self.assertEqual(gateway.call_count, 0)
		enqueue.assert_not_called()

	def test_read_never_returns_keyword_or_settings(self):
		set_agent_settings(
			trigger_keyword="zq-unique-keyword",
			alert_recipients="zq-unique-recipient@example.com",
			thinking_text="zq-unique-thinking",
		)
		frappe.db.set_value("HD Ticket", self.ticket, "ai_confidence", "Cao")
		_add_comment(self.ticket, "bot reply", AGENT_USER)
		frappe.set_user(AGENT_EMAIL)
		result = json.dumps(ticket_panel.get_panel_data(self.ticket), ensure_ascii=False)
		for secret in ("zq-unique-keyword", "zq-unique-recipient", "zq-unique-thinking"):
			with self.subTest(secret=secret):
				self.assertNotIn(secret, result)
		self.assertEqual(set(json.loads(result)), {"ticket", "ai_fields", "messages"})

	def test_read_logs_ids_only_at_debug(self):
		_add_comment(self.ticket, f"{KEYWORD} secret body text")
		_add_comment(self.ticket, "bot secret reply", AGENT_USER)
		_add_comment(self.ticket, "plain human note without the trigger")
		logger, get_logger = self._logger()
		frappe.set_user(AGENT_EMAIL)
		ticket_panel.get_panel_data(self.ticket)
		get_logger.assert_called_with(LOGGER_NAME)
		logger.debug.assert_called_once_with(f"erp_ai panel read ticket={self.ticket} messages=2")
		logger.info.assert_not_called()
		logged = str(logger.mock_calls)
		bot_name = frappe.utils.get_fullname(AGENT_USER)
		for leak in ("secret", KEYWORD, bot_name, AGENT_EMAIL, AGENT_USER, "Administrator"):
			self.assertNotIn(leak, logged)

	def test_denied_read_logs_reason_without_content_or_email(self):
		_make_user(WEBSITE_EMAIL)
		_add_comment(self.ticket, f"{KEYWORD} secret body text")
		logger, _ = self._logger()
		frappe.set_user(WEBSITE_EMAIL)
		with self.assertRaises(frappe.PermissionError):
			ticket_panel.get_panel_data(self.ticket)
		logger.info.assert_called_once_with(
			f"erp_ai panel denied method=get ticket={self.ticket} reason=not_agent"
		)
		logger.debug.assert_not_called()

		frappe.set_user("Administrator")
		create_agent(NO_READ_EMAIL)
		frappe.get_doc("User", NO_READ_EMAIL).remove_roles("Agent", "Agent Manager")
		frappe.set_user(NO_READ_EMAIL)
		logger.reset_mock()
		with self.assertRaises(frappe.PermissionError):
			ticket_panel.get_panel_data(self.ticket)
		logger.info.assert_called_once_with(
			f"erp_ai panel denied method=get ticket={self.ticket} reason=no_read"
		)
		logger.debug.assert_not_called()
		logged = str(logger.mock_calls)
		for leak in ("secret", KEYWORD, WEBSITE_EMAIL, NO_READ_EMAIL):
			self.assertNotIn(leak, logged)


class TestTicketPanelSend(FrappeTestCase):
	"""AC-9, AC-13 (send): input checks, content building, one Comment owned by the sender."""

	KEYWORD = "!hoibot"

	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		create_agent(AGENT_EMAIL)
		set_agent_settings(trigger_keyword=self.KEYWORD)
		self.ticket = make_ticket(subject="Panel send ticket").name
		# The Comment handler (FEAT-001) is not under test here: keep it from queueing a job.
		enqueue = patch.object(frappe, "enqueue")
		enqueue.start()
		self.addCleanup(enqueue.stop)

	def _send(self, text, user=AGENT_EMAIL, ticket=None):
		frappe.set_user(user)
		return ticket_panel.send_message(ticket or self.ticket, text)

	def _content(self, result):
		return frappe.db.get_value("Comment", result["comment"], "content")

	def _comment_count(self):
		return frappe.db.count("Comment", {"reference_doctype": "HD Ticket", "reference_name": self.ticket})

	def test_send_empty_or_whitespace_is_rejected(self):
		for text in ("", "   ", "\n\t \n"):
			with self.subTest(text=text), self.assertRaises(frappe.ValidationError):
				self._send(text)
		# Frappe's own annotation check turns a wrong type away before the function body runs.
		for text in (None, 5):
			with self.subTest(text=text), self.assertRaises(frappe.FrappeTypeError):
				self._send(text)
		self.assertEqual(self._comment_count(), 0)

	def test_send_length_boundary(self):
		self.assertIn("comment", self._send("a" * 2000))
		# The limit counts the text after strip().
		self.assertIn("comment", self._send("  " + "a" * 2000 + "  "))
		with self.assertRaises(frappe.ValidationError):
			self._send("a" * 2001)
		self.assertEqual(self._comment_count(), 2)

	def test_send_appends_configured_keyword_when_missing(self):
		self.assertEqual(self._content(self._send("Hello there")), f"<p>Hello there {self.KEYWORD}</p>")

	def test_send_keeps_text_when_keyword_present_other_case(self):
		self.assertEqual(
			self._content(self._send(f"Hi {self.KEYWORD.upper()} please")),
			f"<p>Hi {self.KEYWORD.upper()} please</p>",
		)

	def test_send_escapes_html(self):
		# <b> is an allowed tag: only our own escaping keeps it from being stored as markup.
		result = self._send("<b>x</b> & y")
		self.assertEqual(self._content(result), f"<p>&lt;b&gt;x&lt;/b&gt; &amp; y {self.KEYWORD}</p>")
		frappe.set_user(AGENT_EMAIL)
		texts = [m["text"] for m in ticket_panel.get_panel_data(self.ticket)["messages"]]
		self.assertEqual(texts, [f"<b>x</b> & y {self.KEYWORD}"])

	def test_send_multiline_keeps_line_breaks(self):
		content = self._content(self._send("one\ntwo\r\nthree"))
		self.assertEqual(content, f"<p>one<br>two<br>three {self.KEYWORD}</p>")

	def test_send_creates_one_comment_owned_by_sender(self):
		result = self._send("Question")
		self.assertEqual(list(result), ["comment"])
		self.assertEqual(self._comment_count(), 1)
		values = frappe.db.get_value(
			"Comment", result["comment"], ["owner", "comment_type", "comment_email"], as_dict=True
		)
		self.assertEqual(values.owner, AGENT_EMAIL)
		self.assertNotEqual(values.owner, AGENT_USER)
		self.assertEqual(values.comment_type, "Comment")
		self.assertEqual(values.comment_email, AGENT_EMAIL)

	def test_send_with_empty_keyword_creates_comment_without_keyword(self):
		set_agent_settings(trigger_keyword="")
		self.assertEqual(self._content(self._send("No keyword")), "<p>No keyword</p>")
		self.assertEqual(self._comment_count(), 1)

	def test_send_calls_new_comment_once_with_built_content(self):
		with patch("helpdesk.helpdesk.doctype.hd_ticket.hd_ticket.HDTicket.new_comment") as new_comment:
			new_comment.return_value = "COMMENT-1"
			self.assertEqual(self._send("Hi"), {"comment": "COMMENT-1"})
		new_comment.assert_called_once_with(f"<p>Hi {self.KEYWORD}</p>")

	def test_send_denied_for_same_accounts_creates_nothing(self):
		_make_user(WEBSITE_EMAIL)
		frappe.set_user("Administrator")
		create_agent(NO_READ_EMAIL)
		frappe.get_doc("User", NO_READ_EMAIL).remove_roles("Agent", "Agent Manager")
		create_agent(INACTIVE_EMAIL)
		frappe.db.set_value("HD Agent", INACTIVE_EMAIL, "is_active", 0)
		_make_user(CUSTOMER_EMAIL)
		frappe.get_doc("User", CUSTOMER_EMAIL).add_roles("HD Customer")
		own = make_ticket(subject="Customer own ticket", raised_by=CUSTOMER_EMAIL).name
		frappe.set_user(NO_READ_EMAIL)
		self.assertTrue(is_agent())
		self.assertFalse(frappe.has_permission("HD Ticket", "read", doc=self.ticket))
		frappe.set_user(CUSTOMER_EMAIL)
		self.assertFalse(is_agent())
		self.assertTrue(frappe.has_permission("HD Ticket", "read", doc=own))
		with self.assertRaises(frappe.PermissionError):
			ticket_panel.send_message(own, "Hi")
		for user in (WEBSITE_EMAIL, "Guest", NO_READ_EMAIL, INACTIVE_EMAIL):
			with self.subTest(user=user), self.assertRaises(frappe.PermissionError):
				self._send("Hi", user=user)
		with self.assertRaises(frappe.PermissionError):
			self._send("Hi", ticket="999999999")
		self.assertEqual(self._comment_count(), 0)
		self.assertEqual(frappe.db.count("Comment", {"reference_name": own}), 0)

	def test_send_denied_for_agent_user(self):
		frappe.set_user("Administrator")
		create_agent(AGENT_USER)
		with self.assertRaises(frappe.PermissionError):
			self._send("Hi", user=AGENT_USER)
		self.assertEqual(self._comment_count(), 0)

	def _logger(self):
		logger = MagicMock()
		patcher = patch.object(ticket_panel.frappe, "logger", return_value=logger)
		patcher.start()
		self.addCleanup(patcher.stop)
		return logger

	def test_send_stored_content_passes_contains_keyword(self):
		for text in ("Hello", "<b>x</b> & y", f"Hi {self.KEYWORD.upper()} there", "one\ntwo"):
			with self.subTest(text=text):
				stored = self._content(self._send(text))
				self.assertTrue(contains_keyword(stored), stored)

	def test_send_checks_keyword_on_sanitized_form(self):
		# The check must run on what sanitize_html(always_sanitize=True) returns, not on our own escaping.
		with (
			patch.object(ticket_panel, "sanitize_html", return_value="<p>stripped</p>") as sanitize,
			patch("helpdesk.helpdesk.doctype.hd_ticket.hd_ticket.HDTicket.new_comment") as new_comment,
		):
			with self.assertRaises(frappe.ValidationError):
				self._send("Hello")
		sanitize.assert_called_once_with(f"<p>Hello {self.KEYWORD}</p>", always_sanitize=True)
		new_comment.assert_not_called()

	def test_send_keyword_with_special_chars_rejected(self):
		for keyword in ("a&b", "a<b"):
			with self.subTest(keyword=keyword):
				set_agent_settings(trigger_keyword=keyword)
				with (
					patch(
						"helpdesk.helpdesk.doctype.hd_ticket.hd_ticket.HDTicket.new_comment"
					) as new_comment,
					self.assertRaises(frappe.ValidationError) as caught,
				):
					self._send("Hello")
				new_comment.assert_not_called()
				self.assertNotIn(keyword, str(caught.exception))
				self.assertNotIn(keyword.casefold(), str(caught.exception).casefold())
				self.assertEqual(self._comment_count(), 0)

	def test_send_logs_without_content_or_email(self):
		logger = self._logger()
		added = self._send("Secret body")["comment"]
		kept = self._send(f"Other {self.KEYWORD}")["comment"]
		set_agent_settings(trigger_keyword="a&b")
		with self.assertRaises(frappe.ValidationError):
			self._send("Secret body")
		set_agent_settings(trigger_keyword=self.KEYWORD)
		with self.assertRaises(frappe.PermissionError):
			self._send("Secret body", user="Guest")
		frappe.set_user("Administrator")
		create_agent(AGENT_USER)
		with self.assertRaises(frappe.PermissionError):
			self._send("Secret body", user=AGENT_USER)
		# The FEAT-001 handler logs through the same logger name: keep only the panel's lines.
		lines = [
			call.args[0] for call in logger.info.call_args_list if call.args[0].startswith("erp_ai panel")
		]
		self.assertEqual(
			lines,
			[
				f"erp_ai panel send ticket={self.ticket} comment={added} keyword_added=true",
				f"erp_ai panel send ticket={self.ticket} comment={kept} keyword_added=false",
				f"erp_ai panel send rejected ticket={self.ticket} reason=keyword_not_storable",
				f"erp_ai panel denied method=send ticket={self.ticket} reason=not_agent",
				f"erp_ai panel denied method=send ticket={self.ticket} reason=agent_user",
			],
		)
		logged = str(logger.mock_calls)
		for leak in ("Secret", "Other", "a&b", self.KEYWORD, AGENT_EMAIL, AGENT_USER):
			self.assertNotIn(leak, logged)


class TestTicketPanelGateParity(FrappeTestCase):
	"""AC-10, NFR-4: the panel and the Comments box reach the same agent decision in every gate branch."""

	KEYWORD = "xin-bot"
	TEXT = "Please look at this"
	EXCLUDED_TEAM = "ERPAI-TEST-Parity-Excluded"
	INSTRUCTOR_EMAIL = "panel.instructor@example.com"
	SAVEPOINT = "erp_ai_gate_parity"
	RUN_ROUTE = "erp_ai.agent.runner.run_for_ticket"
	SPEND_BY_BRANCH: ClassVar[dict] = {"over_budget": 2.0}
	LEVEL_BY_BRANCH: ClassVar[dict] = {"over_budget": "L1", "instructor_role": "L2", "assignee": "L2"}

	def setUp(self):
		# Cleanups run LIFO: set_user, rollback, then the roles cache that the rollback leaves stale.
		self.addCleanup(frappe.clear_cache, user=self.INSTRUCTOR_EMAIL)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("test must not commit"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		log_error = patch.object(frappe, "log_error")
		self.log_error = log_error.start()
		self.addCleanup(log_error.stop)
		record_status_signals(self)
		sleep_patch = patch.object(answer_delay, "_sleep")
		sleep_patch.start()
		self.addCleanup(sleep_patch.stop)
		self.gateway = FakeGateway()
		gateway_patch = patch("erp_ai.gateway.call_model", self.gateway)
		gateway_patch.start()
		self.addCleanup(gateway_patch.stop)
		enqueue_patch = patch.object(frappe, "enqueue")
		self.enqueue = enqueue_patch.start()
		self.addCleanup(enqueue_patch.stop)
		month_spend_patch = patch.object(policy, "month_spend_usd", return_value=0.0)
		self.month_spend = month_spend_patch.start()
		self.addCleanup(month_spend_patch.stop)

		if not frappe.db.exists("Role", ROLE_INSTRUCTOR):
			frappe.get_doc({"doctype": "Role", "role_name": ROLE_INSTRUCTOR}).insert(ignore_permissions=True)
		create_agent(AGENT_EMAIL)
		create_agent(self.INSTRUCTOR_EMAIL)
		frappe.get_doc("User", self.INSTRUCTOR_EMAIL).add_roles(ROLE_INSTRUCTOR)

	def _tool_turn(self):
		block = {"type": "tool_use", "id": "toolu_1", "name": "get_ticket", "input": {}}
		return make_model_result(content=[block], stop_reason="tool_use")

	def _branches(self):
		"""name -> (settings, ticket values, seeded runs, assigned agent, commenter, gateway results, expected jobs, expected gateway calls, expected instructor)."""
		l1 = {
			"permission_level": "L1",
			"max_runs_per_ticket_per_day": 5,
			"max_turns_per_run": 4,
			"monthly_budget_usd": 1,
			"spent_this_month_usd": 0,
			"excluded_teams": "",
		}
		return {
			"agent_off": (
				{**l1, "enabled": 0},
				{},
				0,
				False,
				AGENT_EMAIL,
				[],
				0,
				0,
				None,
			),
			"level_L0": (
				{**l1, "permission_level": "L0"},
				{},
				0,
				False,
				AGENT_EMAIL,
				[],
				1,
				0,
				None,
			),
			"excluded_group": (
				{**l1, "excluded_teams": self.EXCLUDED_TEAM},
				{"agent_group": self.EXCLUDED_TEAM},
				0,
				False,
				AGENT_EMAIL,
				[],
				0,
				0,
				None,
			),
			"ai_opt_out": (l1, {"ai_opt_out": 1}, 0, False, AGENT_EMAIL, [], 0, 0, None),
			"daily_limit": (
				{**l1, "max_runs_per_ticket_per_day": 1},
				{},
				1,
				False,
				AGENT_EMAIL,
				[],
				1,
				0,
				None,
			),
			"turn_limit": (
				{**l1, "max_turns_per_run": 1},
				{},
				0,
				False,
				AGENT_EMAIL,
				[self._tool_turn()],
				1,
				1,
				None,
			),
			"over_budget": (
				{**l1, "permission_level": "L2"},
				{},
				0,
				False,
				AGENT_EMAIL,
				[],
				1,
				1,
				None,
			),
			"instructor_role": (
				{**l1, "permission_level": "L2"},
				{},
				0,
				False,
				self.INSTRUCTOR_EMAIL,
				[],
				1,
				1,
				self.INSTRUCTOR_EMAIL,
			),
			"assignee": ({**l1, "permission_level": "L2"}, {}, 0, True, AGENT_EMAIL, [], 1, 1, AGENT_EMAIL),
			"other_person": (l1, {}, 0, False, AGENT_EMAIL, [], 1, 1, None),
		}

	def _decision(self, ticket, user, act, results):
		"""Run `act` as `user`, then every agent job it queued; return what the decision looks like, then undo it all."""
		frappe.db.savepoint(self.SAVEPOINT)
		known = set(frappe.get_all(LOG_DOCTYPE, filters={"ticket": ticket}, pluck="name"))
		self.enqueue.reset_mock()
		self.gateway.calls.clear()
		self.gateway.results = list(results)
		frappe.flags.pop(PENDING_JOB_IDS_FLAG, None)
		frappe.set_user(user)
		decisions = []
		logger = MagicMock()
		logger.info.side_effect = lambda message, *args, **kwargs: decisions.append(str(message))
		try:
			with patch.object(frappe, "logger", return_value=logger):
				content_of = act()
			jobs = [
				call.kwargs
				for call in self.enqueue.call_args_list
				if call.args and call.args[0] == self.RUN_ROUTE
			]
		finally:
			frappe.set_user("Administrator")
		real_effective_level = policy.effective_level
		levels = []

		def record_level(*args, **kwargs):
			level = real_effective_level(*args, **kwargs)
			levels.append(level)
			return level

		with patch.object(policy, "effective_level", side_effect=record_level):
			for job in jobs:
				runner.run_for_ticket(job["ticket_name"], job["trigger"])
		frappe.set_user("Administrator")
		entries = [
			row
			for row in frappe.get_all(
				LOG_DOCTYPE,
				filters={"ticket": ticket},
				fields=["name", "entry_type", "trigger", "turn", "stop_reason", "instructor"],
				order_by="creation asc, name asc",
			)
			if row.name not in known
		]
		outcome = {
			"jobs": [(job["ticket_name"], job["trigger"], job["job_id"]) for job in jobs],
			"gateway": [
				(call["task"], [tool["name"] for tool in call.get("tools") or []])
				for call in self.gateway.calls
			],
			"log": [(e.entry_type, e.trigger, e.turn, e.stop_reason, e.instructor) for e in entries],
			"decisions": [line for line in decisions if line.startswith("erp_ai handler ")],
			"comment": frappe.db.get_value("Comment", content_of, ["owner", "comment_type", "content"]),
			"levels": levels,
		}
		frappe.flags.pop(PENDING_JOB_IDS_FLAG, None)
		frappe.db.rollback(save_point=self.SAVEPOINT)
		return outcome

	def test_send_matches_comments_box_in_every_gate_branch(self):
		for name, branch in self._branches().items():
			settings, ticket_values, seeded, assigned, user, results, want_jobs, want_calls, want_who = branch
			with self.subTest(branch=name):
				set_agent_settings(enabled=1, trigger_keyword=self.KEYWORD)
				ticket = make_ticket(subject=f"Parity {name}").name
				if ticket_values:
					frappe.db.set_value("HD Ticket", ticket, ticket_values)
				if assigned:
					todo = make_todo(ticket, AGENT_EMAIL)
					frappe.db.set_value("ToDo", todo, "assigned_by", "Administrator")
				for index in range(seeded):
					write_entry(
						ticket=ticket,
						run_id=f"ERPAI-TEST-parity-{index}",
						entry_type="classify",
						trigger="ticket_insert",
						turn=0,
					)
				set_agent_settings(**settings)

				def comments_box():
					return frappe.get_doc("HD Ticket", ticket).new_comment(
						f"<p>{self.TEXT} {self.KEYWORD}</p>"
					)

				def panel():
					return ticket_panel.send_message(ticket, self.TEXT)["comment"]

				self.month_spend.return_value = self.SPEND_BY_BRANCH.get(name, 0.0)
				via_box = self._decision(ticket, user, comments_box, results)
				via_panel = self._decision(ticket, user, panel, results)

				self.assertEqual(via_panel, via_box)
				self.assertEqual(len(via_panel["jobs"]), want_jobs)
				self.assertEqual(len(via_panel["gateway"]), want_calls)
				if want_jobs:
					self.assertTrue(via_panel["log"])
				self.assertEqual(
					{entry[4] for entry in via_panel["log"] if entry[0] == "reason"} or {None},
					{want_who},
				)
				if name in ("excluded_group", "ai_opt_out"):
					self.assertEqual(self.gateway.call_count, 0)
				if name in self.LEVEL_BY_BRANCH:
					self.assertEqual(set(via_panel["levels"]), {self.LEVEL_BY_BRANCH[name]})
