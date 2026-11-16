import json
from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import MagicMock, patch

import frappe
from frappe.core.utils import html_to_plain_text
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import create_agent, make_ticket, make_todo
from helpdesk.utils import is_agent

from erp_ai import ticket_panel
from erp_ai.agent import answer_delay, policy, runner
from erp_ai.agent.policy import contains_keyword
from erp_ai.agent.queue import PENDING_JOB_IDS_FLAG
from erp_ai.agent.run_log import write_entry
from erp_ai.agent.tools import propose_change, write_ticket
from erp_ai.constants import (
	AGENT_USER,
	CHANGE_STATUS_APPLIED,
	CHANGE_STATUS_APPROVED,
	CHANGE_STATUS_FAILED,
	CHANGE_STATUS_PENDING,
	CHANGE_STATUS_REJECTED,
	CHANGE_STATUS_STALE,
	CHANGE_STATUS_UNDOING,
	CHANGE_STATUS_UNDONE,
	CLASSIFICATION_FIELDS,
	LOG_DOCTYPE,
	LOGGER_NAME,
	MESSAGE_DOCTYPE,
	PANEL_MAX_PROPOSALS,
	PANEL_METHODS,
	PROPOSAL_DOCTYPE,
	RESTART_STATUS_CONFIRMED,
	RESTART_STATUS_LAUNCH_FAILED,
	RESTART_STATUS_SENT,
	RESTART_STATUS_UNCONFIRMED,
	ROLE_INSTRUCTOR,
	TITLE_RUN_FAILED,
)
from erp_ai.erp_ai_agent.doctype.erp_ai_change_proposal import erp_ai_change_proposal as proposal_form
from erp_ai.test_utils import (
	FakeGateway,
	keep_agent_settings,
	make_block_proposal,
	make_change_proposal,
	make_model_result,
	record_status_signals,
	set_agent_settings,
)

# What the panel lists about the ticket, in display order: what the bot classified and why, how it scored
# the ticket, what it concluded and did, then who classified and when.
INFO_FIELD_LABELS = (
	("ticket_type", "Loại"),
	("agent_group", "Nhóm"),
	("priority", "Ưu tiên"),
	("ai_classification_reason", "Lý do phân loại (AI)"),
	("ai_confidence", "Độ tin cậy (AI)"),
	("ai_confidence_pct", "Độ tin cậy % (AI)"),
	("ai_complexity", "Độ phức tạp (AI)"),
	("ai_importance", "Độ quan trọng (AI)"),
	("ai_score_reason", "Lý do chấm điểm (AI)"),
	("ai_resolution_hint", "Hướng giải quyết (AI)"),
	("ai_analysis", "Nhận định (AI)"),
	("ai_done", "Đã làm (AI)"),
	("ai_pending", "Chờ duyệt (AI)"),
	("ai_manual", "Cần người xử lý (AI)"),
	("ai_classified_by", "Phân loại bởi"),
	("ai_updated_at", "AI cập nhật lúc"),
)
AGENT_EMAIL = "panel.agent@example.com"
NO_READ_EMAIL = "panel.noread@example.com"
INACTIVE_EMAIL = "panel.inactive@example.com"
WEBSITE_EMAIL = "panel.website@example.com"
CUSTOMER_EMAIL = "panel.customer@example.com"
KEYWORD = "@ai"
RUN_ROUTE = "erp_ai.agent.runner.run_for_ticket"
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


def _add_message(ticket, content, owner="Administrator", creation=None):
	"""An ERP AI Message as the DB would hold it; owner and creation are set directly."""
	with patch.object(frappe, "enqueue"):
		doc = frappe.get_doc({"doctype": MESSAGE_DOCTYPE, "ticket": ticket, "content": "placeholder"}).insert(
			ignore_permissions=True
		)
	values = {"content": content, "owner": owner}
	if creation:
		values["creation"] = creation
	frappe.db.set_value(MESSAGE_DOCTYPE, doc.name, values, update_modified=False)
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
		ai_items = [item for item in self._read()["ai_fields"] if item["fieldname"].startswith("ai_")]
		self.assertEqual(len(ai_items), 13)
		for item in ai_items:
			with self.subTest(field=item["fieldname"]):
				self.assertIsNone(item["text"])

	def test_read_lists_classification_then_ai_fields_with_labels(self):
		data = self._read()
		self.assertEqual(
			[(item["fieldname"], item["label"]) for item in data["ai_fields"]], list(INFO_FIELD_LABELS)
		)
		meta = frappe.get_meta("HD Ticket")
		for name in ticket_panel.AI_FIELDS:
			with self.subTest(field=name):
				self.assertEqual(dict(INFO_FIELD_LABELS)[name], meta.get_label(name))
		# One wording for the three fields: the bot's own "Đã làm" line uses the same labels.
		self.assertEqual(ticket_panel.CLASSIFICATION_LABELS, write_ticket.FIELD_LABELS)
		self.assertEqual(tuple(ticket_panel.CLASSIFICATION_LABELS), CLASSIFICATION_FIELDS)

	def test_read_returns_classification_and_scores_stored_on_the_ticket(self):
		# What the bot filled in is the ticket's own information: the panel reads it from the record.
		frappe.db.set_value(
			"HD Ticket",
			self.ticket.name,
			{
				"ticket_type": "Câu hỏi, phiếu nhiễu",
				"priority": "Low",
				"ai_confidence_pct": 88,
				"ai_complexity": 1,
				"ai_importance": 2,
				"ai_score_reason": "Chỉ cần hướng dẫn thao tác có sẵn.",
			},
		)
		by_name = {item["fieldname"]: item["text"] for item in self._read()["ai_fields"]}
		self.assertEqual(by_name["ticket_type"], "Câu hỏi, phiếu nhiễu")
		self.assertEqual(by_name["priority"], "Low")
		self.assertEqual(by_name["ai_confidence_pct"], "88")
		self.assertEqual(by_name["ai_complexity"], "1")
		self.assertEqual(by_name["ai_importance"], "2")
		self.assertEqual(by_name["ai_score_reason"], "Chỉ cần hướng dẫn thao tác có sẵn.")

	def test_read_returns_what_the_run_concluded_and_did(self):
		frappe.db.set_value(
			"HD Ticket",
			self.ticket.name,
			{
				"ai_classification_reason": "Người dùng hỏi cách dùng.",
				"ai_analysis": "**Nhận định:** hỏi cách dùng.\n\n**Hướng xử lý:**\n1. Gửi hướng dẫn.",
				"ai_done": "Bot đã phân loại phiếu: Loại Câu hỏi.\nĐã tạo Task TASK-1 (2 giờ).",
				"ai_pending": "Đề xuất CP-1",
				"ai_manual": "Nhờ trưởng nhóm phân công.",
			},
		)
		by_name = {item["fieldname"]: item["text"] for item in self._read()["ai_fields"]}
		self.assertEqual(by_name["ai_classification_reason"], "Người dùng hỏi cách dùng.")
		# The analysis is the model's own text: its line breaks are kept, the page shows it as plain text.
		self.assertEqual(
			by_name["ai_analysis"], "**Nhận định:** hỏi cách dùng.\n\n**Hướng xử lý:**\n1. Gửi hướng dẫn."
		)
		self.assertEqual(
			by_name["ai_done"].splitlines(),
			["Bot đã phân loại phiếu: Loại Câu hỏi.", "Đã tạo Task TASK-1 (2 giờ)."],
		)
		self.assertEqual(by_name["ai_pending"], "Đề xuất CP-1")
		self.assertEqual(by_name["ai_manual"], "Nhờ trưởng nhóm phân công.")

	def test_read_returns_the_team_stored_on_the_ticket(self):
		# Read as Administrator: a team the test agent is not in must not make this a permission test.
		frappe.db.set_value("HD Ticket", self.ticket.name, "agent_group", "Panel Test Team")
		by_name = {item["fieldname"]: item["text"] for item in self._read("Administrator")["ai_fields"]}
		self.assertEqual(by_name["agent_group"], "Panel Test Team")

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
		self.assertEqual(self._read()["ai_fields"][-1]["text"], "12-11-2026 10:05:00")
		self.addCleanup(frappe.clear_cache, doctype="HD Ticket")
		permlevel = frappe.get_meta("HD Ticket").get_field("ai_updated_at").permlevel
		frappe.permissions.update_permission_property("HD Ticket", "Agent", permlevel, "read", 0)
		frappe.clear_cache(doctype="HD Ticket")
		self.assertIsNone(self._read()["ai_fields"][-1]["text"])

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

	def test_thread_reads_messages_in_creation_order(self):
		# Inserted out of order on purpose: the result must follow `creation`, not insertion.
		late = _add_message(self.ticket, "late human", creation="2026-11-12 10:05:00")
		first = _add_message(self.ticket, "first human", creation="2026-11-12 10:01:00")
		bot = _add_message(self.ticket, "bot says hi", AGENT_USER, "2026-11-12 10:03:00")

		messages = self._messages()

		self.assertEqual([m["name"] for m in messages], [first, bot, late])
		for message in messages:
			self.assertEqual(set(message), THREAD_KEYS)
			self.assertNotIn("@", message["author"])
		self.assertEqual(messages[0]["text"], "first human")
		self.assertEqual(messages[0]["created_at"], frappe.utils.format_datetime("2026-11-12 10:01:00"))
		self.assertRegex(messages[0]["created_at"], r"^\d{2}-\d{2}-\d{4} 10:01:00$")
		self.assertEqual(messages[0]["author"], frappe.utils.get_fullname("Administrator"))

	def test_thread_ignores_other_tickets_and_plain_comments(self):
		other_ticket = make_ticket(subject="Another ticket").name
		_add_comment(self.ticket, "plain human comment")
		_add_comment(self.ticket, f"{KEYWORD} comment without a message")
		_add_comment(self.ticket, "bot comment", AGENT_USER)
		_add_message(other_ticket, "on another ticket")
		kept = _add_message(self.ticket, "mine")
		self.assertEqual([m["name"] for m in self._messages()], [kept])

	def test_thread_marks_bot_messages(self):
		_add_message(self.ticket, "human", creation="2026-11-12 10:00:00")
		_add_message(self.ticket, "bot answer", AGENT_USER, "2026-11-12 10:01:00")
		messages = self._messages()
		self.assertEqual([m["is_bot"] for m in messages], [False, True])
		self.assertEqual(messages[1]["author"], frappe.utils.get_fullname(AGENT_USER))

	def test_thread_returns_markup_as_literal_text(self):
		payload = '<img src=x onerror="alert(1)"> <script>alert(2)</script>'
		_add_message(self.ticket, payload)
		_add_message(self.ticket, payload, AGENT_USER)
		for message in self._messages():
			self.assertEqual(message["text"], payload)


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
			"messages": frappe.db.count(MESSAGE_DOCTYPE),
			"logs": frappe.db.count("ERP AI Log"),
			"todos": frappe.db.count("ToDo"),
			"tasks": frappe.db.count("Task"),
			"modified": frappe.db.get_value("HD Ticket", self.ticket, "modified"),
		}

	def test_read_writes_nothing_and_calls_no_gateway(self):
		_add_message(self.ticket, "human")
		_add_message(self.ticket, "bot reply", AGENT_USER)
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
		_add_message(self.ticket, "bot reply", AGENT_USER)
		frappe.set_user(AGENT_EMAIL)
		result = json.dumps(ticket_panel.get_panel_data(self.ticket), ensure_ascii=False)
		for secret in ("zq-unique-keyword", "zq-unique-recipient", "zq-unique-thinking"):
			with self.subTest(secret=secret):
				self.assertNotIn(secret, result)
		# ADR-044 (CHG-008): the read result gains `proposals`, the cards of the ticket's change proposals
		self.assertEqual(set(json.loads(result)), {"ticket", "ai_fields", "messages", "proposals"})

	def test_read_logs_ids_only_at_debug(self):
		_add_message(self.ticket, f"{KEYWORD} secret body text")
		_add_message(self.ticket, "bot secret reply", AGENT_USER)
		_add_comment(self.ticket, "plain human note without the trigger")
		logger, get_logger = self._logger()
		frappe.set_user(AGENT_EMAIL)
		ticket_panel.get_panel_data(self.ticket)
		get_logger.assert_called_with(LOGGER_NAME)
		# ADR-044 (CHG-008 design 4.1 step 4): the debug line also counts the proposal cards
		logger.debug.assert_called_once_with(f"erp_ai panel read ticket={self.ticket} messages=2 proposals=0")
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
	"""AC-9, AC-13 (send): input checks, one chat message owned by the sender, no Comment, no keyword."""

	KEYWORD = "!hoibot"

	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		create_agent(AGENT_EMAIL)
		set_agent_settings(trigger_keyword=self.KEYWORD)
		self.ticket = make_ticket(subject="Panel send ticket").name
		# The message handler (FEAT-007) is not under test here: keep it from queueing a job.
		enqueue = patch.object(frappe, "enqueue")
		enqueue.start()
		self.addCleanup(enqueue.stop)

	def _send(self, text, user=AGENT_EMAIL, ticket=None):
		frappe.set_user(user)
		return ticket_panel.send_message(ticket or self.ticket, text)

	def _content(self, result):
		return frappe.db.get_value(MESSAGE_DOCTYPE, result["message"], "content")

	def _message_count(self):
		return frappe.db.count(MESSAGE_DOCTYPE, {"ticket": self.ticket})

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
		self.assertEqual(self._message_count(), 0)

	def test_send_length_boundary(self):
		self.assertIn("message", self._send("a" * 2000))
		# The limit counts the text after strip().
		self.assertIn("message", self._send("  " + "a" * 2000 + "  "))
		with self.assertRaises(frappe.ValidationError):
			self._send("a" * 2001)
		self.assertEqual(self._message_count(), 2)

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
		self.assertEqual(self._message_count(), 0)
		self.assertEqual(frappe.db.count(MESSAGE_DOCTYPE, {"ticket": own}), 0)

	def test_send_denied_for_agent_user(self):
		frappe.set_user("Administrator")
		create_agent(AGENT_USER)
		with self.assertRaises(frappe.PermissionError):
			self._send("Hi", user=AGENT_USER)
		self.assertEqual(self._message_count(), 0)

	def _logger(self):
		logger = MagicMock()
		patcher = patch.object(ticket_panel.frappe, "logger", return_value=logger)
		patcher.start()
		self.addCleanup(patcher.stop)
		return logger

	def test_send_creates_one_chat_message_owned_by_sender(self):
		text = "  <b>Question</b> & more < x\nsecond line  "
		before = frappe.db.count("Comment")
		result = self._send(text)
		self.assertEqual(list(result), ["message"])
		self.assertEqual(self._message_count(), 1)
		values = frappe.db.get_value(
			MESSAGE_DOCTYPE, result["message"], ["owner", "content", "ticket"], as_dict=True
		)
		self.assertEqual(values.owner, AGENT_EMAIL)
		self.assertNotEqual(values.owner, AGENT_USER)
		self.assertEqual(values.content, text.strip())
		self.assertEqual(values.ticket, self.ticket)
		self.assertEqual(frappe.db.count("Comment"), before)

	def test_send_does_not_add_keyword(self):
		for keyword in (self.KEYWORD, ""):
			with self.subTest(keyword=keyword):
				set_agent_settings(trigger_keyword=keyword)
				content = self._content(self._send("Hello there"))
				self.assertEqual(content, "Hello there")

	def test_send_enqueues_one_run(self):
		set_agent_settings(enabled=1)
		with patch.object(frappe, "enqueue") as enqueue:
			result = self._send("Please look")
		jobs = [c.kwargs for c in enqueue.call_args_list if c.args and c.args[0] == RUN_ROUTE]
		self.assertEqual(len(jobs), 1)
		self.assertEqual(jobs[0]["message_name"], result["message"])
		self.assertEqual(jobs[0]["ticket_name"], self.ticket)

	def test_send_logs_without_content_or_email(self):
		logger = self._logger()
		first = self._send("Secret body")["message"]
		second = self._send("Other body")["message"]
		with self.assertRaises(frappe.PermissionError):
			self._send("Secret body", user="Guest")
		frappe.set_user("Administrator")
		create_agent(AGENT_USER)
		with self.assertRaises(frappe.PermissionError):
			self._send("Secret body", user=AGENT_USER)
		lines = [
			call.args[0] for call in logger.info.call_args_list if call.args[0].startswith("erp_ai panel")
		]
		self.assertEqual(
			lines,
			[
				f"erp_ai panel send ticket={self.ticket} message={first}",
				f"erp_ai panel send ticket={self.ticket} message={second}",
				f"erp_ai panel denied method=send ticket={self.ticket} reason=not_agent",
				f"erp_ai panel denied method=send ticket={self.ticket} reason=agent_user",
			],
		)
		logged = str(logger.mock_calls)
		for leak in ("Secret", "Other", self.KEYWORD, AGENT_EMAIL, AGENT_USER):
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
	# The branches about the reasoning path start from a ticket already classified at/above the threshold, so a
	# later run reasons without classifying first (CHG-005 AC-1): one gateway call stays one.
	CLASSIFIED_BRANCHES: ClassVar[set] = {
		"turn_limit",
		"over_budget",
		"instructor_role",
		"assignee",
		"other_person",
	}

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

	panel_messages: ClassVar[dict] = {}

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
		"""Run `act` as `user`, then every agent job it queued; return what the decision looks like, then undo it all.

		A gated @ai comment leaves no message (nothing is copied) while the panel always keeps the one it
		wrote, so stored messages are not part of the decision."""
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
				act()
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
			levels.append((kwargs.get("over_budget"), level))
			return level

		with patch.object(policy, "effective_level", side_effect=record_level):
			for job in jobs:
				runner.run_for_ticket(job["ticket_name"], job["trigger"], job.get("message_name"))
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
			# The comment handler adds a "copied" line for its copy; the decision is every other handler line.
			"decisions": [
				line for line in decisions if line.startswith("erp_ai handler ") and " copied: " not in line
			],
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
				if name in self.CLASSIFIED_BRANCHES:
					write_entry(
						ticket=ticket,
						run_id="ERPAI-TEST-parity-classified",
						entry_type="classify",
						trigger="ticket_insert",
						turn=0,
						predicted_category="A",
						predicted_confidence_pct=100,
					)
				set_agent_settings(**settings)

				def comments_box():
					return frappe.get_doc("HD Ticket", ticket).new_comment(
						f"<p>{self.TEXT} {self.KEYWORD}</p>"
					)

				def panel():
					sent = ticket_panel.send_message(ticket, self.TEXT)["message"]
					self.panel_messages[name] = [sent]

				self.month_spend.return_value = self.SPEND_BY_BRANCH.get(name, 0.0)
				via_box = self._decision(ticket, user, comments_box, results)
				via_panel = self._decision(ticket, user, panel, results)

				self.assertEqual(via_panel, via_box)
				self.assertEqual(len(self.panel_messages[name]), 1)
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
					over_budget = name in self.SPEND_BY_BRANCH
					self.assertEqual(
						{lvl for ob, lvl in via_panel["levels"] if ob == over_budget},
						{self.LEVEL_BY_BRANCH[name]},
					)
					if over_budget:
						# the over_budget=False probe of the run reads the base level
						self.assertEqual(
							{lvl for ob, lvl in via_panel["levels"] if ob is False},
							{settings["permission_level"]},
						)


CARD_INSTRUCTOR = "panel.card.instructor@example.com"
CARD_ALL_STATUSES = (
	CHANGE_STATUS_PENDING,
	CHANGE_STATUS_REJECTED,
	CHANGE_STATUS_APPROVED,
	"Đang áp dụng",
	CHANGE_STATUS_APPLIED,
	CHANGE_STATUS_FAILED,
	CHANGE_STATUS_STALE,
	CHANGE_STATUS_UNDOING,
	CHANGE_STATUS_UNDONE,
)
CARD_ALL_RESTARTS = (
	RESTART_STATUS_SENT,
	RESTART_STATUS_CONFIRMED,
	RESTART_STATUS_UNCONFIRMED,
	RESTART_STATUS_LAUNCH_FAILED,
)
RESTART_SENT_AT = "2026-01-05 10:00:00"


class TestPanelProposalCards(FrappeTestCase):
	"""CHG-008 design 3.1, 4.1 (AC-1..AC-4, AC-9): `get_panel_data` returns one card per proposal of the ticket."""

	def setUp(self):
		# Cleanups run LIFO: settings restore, roles cache, rollback, set_user.
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		keep_agent_settings(self)
		self.addCleanup(frappe.clear_cache, user=CARD_INSTRUCTOR)
		if not frappe.db.exists("Role", ROLE_INSTRUCTOR):
			frappe.get_doc({"doctype": "Role", "role_name": ROLE_INSTRUCTOR}).insert(ignore_permissions=True)
		create_agent(AGENT_EMAIL)
		create_agent(CARD_INSTRUCTOR)
		frappe.get_doc("User", CARD_INSTRUCTOR).add_roles(ROLE_INSTRUCTOR)
		frappe.clear_cache(user=CARD_INSTRUCTOR)
		set_agent_settings(one_click_approval_enabled=1)
		self.ticket = make_ticket(subject="Panel cards ticket").name

	def _cards(self, user=AGENT_EMAIL, ticket=None):
		frappe.set_user(user)
		try:
			return ticket_panel.get_panel_data(ticket or self.ticket)["proposals"]
		finally:
			frappe.set_user("Administrator")

	def _set(self, name, **values):
		frappe.db.set_value(PROPOSAL_DOCTYPE, name, values, update_modified=False)

	def _comment_text(self, proposal):
		"""The comment `propose_change._comment` posts for `proposal`, as (target, notes) in plain text."""
		ctx = SimpleNamespace(ticket_name=proposal.ticket, one_click_approval=False)
		comment = propose_change._comment(ctx, proposal)
		content = frappe.db.get_value("Comment", comment, "content")
		lines = [line.strip() for line in html_to_plain_text(content).splitlines() if line.strip()]
		head, *rest = lines
		prefix = "đang chờ duyệt: "
		target = head.split(prefix, 1)[1].removesuffix(".")
		return target, rest[:-1]

	def _counts(self):
		return {
			doctype: frappe.db.count(doctype)
			for doctype in ("Comment", MESSAGE_DOCTYPE, PROPOSAL_DOCTYPE, LOG_DOCTYPE)
		}

	def test_card_keys_and_constants(self):
		self.assertEqual(
			proposal_form.CARD_KEYS,
			(
				"name",
				"target",
				"notes",
				"status",
				"restart_status",
				"decided_by",
				"failure_reason",
				"can_decide",
				"can_open",
			),
		)
		self.assertEqual(PANEL_MAX_PROPOSALS, 200)
		self.assertEqual(
			proposal_form.CARD_FIELDS,
			(
				"name",
				"change_kind",
				"is_new_file",
				"file_path",
				"app",
				"command_list",
				"change_status",
				"restart_status",
				"restart_sent_at",
				"decided_by",
				"failure_reason",
				"target_branch",
				"upstream_ref",
				"ahead_count",
				"is_core_app",
				"apply_commit_sha",
				"undo_commit_sha",
			),
		)
		self.assertEqual(
			proposal_form.CARD_OPERATION_FIELDS, ("parent", "idx", "operation", "file_path", "new_path")
		)
		self.assertNotIn(proposal_form.panel_cards, frappe.whitelisted)

	def test_card_text_matches_proposal_comment(self):
		code = make_change_proposal(ticket=self.ticket)
		command = make_change_proposal(kind="Lệnh bench", ticket=self.ticket)
		block = make_block_proposal(
			[{"kind": "Sửa", "path": "erp_ai/a.py", "before": "x = 1\n", "after": "x = 2\n"}],
			[["clear-cache"]],
			ticket=self.ticket,
		)
		cards = {card["name"]: card for card in self._cards()}
		self.assertEqual(len(cards), 3)
		for proposal in (code, command, block):
			with self.subTest(name=proposal.name):
				fresh = frappe.get_doc(PROPOSAL_DOCTYPE, proposal.name)
				target, notes = self._comment_text(fresh)
				# html_to_plain_text pads `<code>` with spaces; the words are the same
				self.assertEqual(" ".join(cards[proposal.name]["target"].split()), " ".join(target.split()))
				self.assertEqual(cards[proposal.name]["notes"], notes)

	def test_read_with_proposals_writes_nothing(self):
		for status in CARD_ALL_STATUSES:
			proposal = make_change_proposal(ticket=self.ticket)
			self._set(proposal.name, change_status=status)
		before = self._counts()
		for user in (AGENT_EMAIL, CARD_INSTRUCTOR):
			frappe.set_user(user)
			writes = frappe.db.transaction_writes
			ticket_panel.get_panel_data(self.ticket)
			self.assertEqual(frappe.db.transaction_writes, writes)
			frappe.set_user("Administrator")
		self.assertEqual(self._counts(), before)

	def test_cards_by_ticket_whatever_run(self):
		other = make_ticket(subject="Panel cards other ticket").name
		runs = ("run-from-panel", "run-from-mention", "run-from-creation")
		names = {make_change_proposal(ticket=self.ticket, run_id=run).name for run in runs}
		make_change_proposal(ticket=other)
		orphan = make_change_proposal(ticket=self.ticket)
		self._set(orphan.name, ticket=None)
		self.assertEqual({card["name"] for card in self._cards()}, names)
		self.assertEqual(len(self._cards(ticket=other)), 1)

	def test_proposal_without_ticket_has_no_card_anywhere(self):
		orphan = make_change_proposal(ticket=self.ticket)
		self._set(orphan.name, ticket=None)
		self.assertEqual(proposal_form.panel_cards(self.ticket), [])
		self.assertEqual(proposal_form.panel_cards(""), [])
		self.assertEqual(self._cards(), [])

	def test_cards_newest_first_capped(self):
		names = []
		for index in range(PANEL_MAX_PROPOSALS + 1):
			proposal = make_change_proposal(ticket=self.ticket)
			creation = f"2026-01-01 00:{index // 60:02d}:{index % 60:02d}.000000"
			frappe.db.set_value(PROPOSAL_DOCTYPE, proposal.name, "creation", creation, update_modified=False)
			names.append(proposal.name)
		cards = self._cards()
		self.assertEqual(len(cards), PANEL_MAX_PROPOSALS)
		self.assertEqual([card["name"] for card in cards], list(reversed(names))[:PANEL_MAX_PROPOSALS])

	def test_cards_same_creation_ordered_by_name_desc(self):
		names = [make_change_proposal(ticket=self.ticket).name for _ in range(3)]
		for name in names:
			frappe.db.set_value(
				PROPOSAL_DOCTYPE, name, "creation", "2026-01-01 00:00:00", update_modified=False
			)
		self.assertEqual([card["name"] for card in self._cards()], sorted(names, reverse=True))

	def test_every_status_has_card_only_pending_decidable(self):
		by_status = {}
		for status in CARD_ALL_STATUSES:
			proposal = make_change_proposal(ticket=self.ticket)
			self._set(proposal.name, change_status=status)
			by_status[status] = proposal.name
		restart_by_name = {}
		for restart in CARD_ALL_RESTARTS:
			proposal = make_change_proposal(ticket=self.ticket)
			self._set(
				proposal.name,
				change_status=CHANGE_STATUS_APPLIED,
				restart_status=restart,
				restart_sent_at=RESTART_SENT_AT,
			)
			restart_by_name[proposal.name] = restart
		cards = {card["name"]: card for card in self._cards(CARD_INSTRUCTOR)}
		self.assertEqual(len(cards), len(by_status) + len(restart_by_name))
		for status, name in by_status.items():
			with self.subTest(status=status):
				self.assertEqual(cards[name]["status"], status)
				self.assertIsNone(cards[name]["restart_status"])
				self.assertIs(cards[name]["can_decide"], status == CHANGE_STATUS_PENDING)
		for name, restart in restart_by_name.items():
			with self.subTest(restart=restart):
				self.assertEqual(cards[name]["status"], CHANGE_STATUS_APPLIED)
				self.assertEqual(cards[name]["restart_status"], restart)
				self.assertIs(cards[name]["can_decide"], False)

	def test_denied_read_returns_no_card(self):
		make_change_proposal(ticket=self.ticket)
		_make_user(NO_READ_EMAIL, user_type="System User")
		for user in ("Guest", WEBSITE_EMAIL, NO_READ_EMAIL):
			with self.subTest(user=user):
				if user == WEBSITE_EMAIL:
					_make_user(user)
				with self.assertRaises(frappe.PermissionError):
					self._cards(user)

	def test_card_never_carries_content_fields(self):
		seeds = {
			"diff": "zq-seed-diff",
			"content_before": "zq-seed-before",
			"content_after": "zq-seed-after",
			"command_args": '["zq-seed-args"]',
			"commit_message": "zq-seed-commit",
			"reason": "zq-seed-reason",
		}
		proposal = make_block_proposal(
			[{"kind": "Sửa", "path": "erp_ai/a.py", "before": "zq-row-before", "after": "zq-row-after"}],
			[],
			ticket=self.ticket,
			**seeds,
		)
		self._set(
			proposal.name,
			command_output="zq-seed-output",
			command_results='[{"zq-seed-results": 1}]',
			approved_digest="zq-seed-digest",
			created_dirs='["zq-seed-dirs"]',
			change_status=CHANGE_STATUS_FAILED,
			failure_reason="that bai tai https://zq-seed-url.example/x xong",
		)
		frappe.db.set_value(
			"ERP AI Change Operation",
			{"parent": proposal.name},
			{"base_hash": "zq-row-hash", "after_hash": "zq-row-hash2"},
			update_modified=False,
		)
		frappe.set_user(CARD_INSTRUCTOR)
		result = ticket_panel.get_panel_data(self.ticket)
		self.assertEqual(set(result), {"ticket", "ai_fields", "messages", "proposals"})
		self.assertEqual(len(result["proposals"]), 1)
		self.assertEqual(set(result["proposals"][0]), set(proposal_form.CARD_KEYS))
		text = json.dumps(result["proposals"], ensure_ascii=False)
		for needle in ("zq-seed", "zq-row"):
			with self.subTest(needle=needle):
				self.assertNotIn(needle, text)

	def test_decide_flag_matrix(self):
		proposal = make_change_proposal(ticket=self.ticket)
		cells = []
		for user, role in ((CARD_INSTRUCTOR, True), (AGENT_EMAIL, False)):
			for status in (CHANGE_STATUS_PENDING, CHANGE_STATUS_APPROVED):
				for switch in (1, 0):
					self._set(proposal.name, change_status=status)
					set_agent_settings(one_click_approval_enabled=switch)
					card = self._cards(user)[0]
					cells.append((role, status == CHANGE_STATUS_PENDING, switch, card))
		self.assertEqual(len(cells), 8)
		self.assertEqual([cell[:3] for cell in cells if cell[3]["can_decide"]], [(True, True, 1)])
		for role, pending, switch, card in cells:
			with self.subTest(role=role, pending=pending, switch=switch):
				self.assertIs(card["can_decide"], role and pending and bool(switch))
				self.assertIs(card["can_open"], role)

	def test_switch_flip_between_reads_changes_can_decide_without_cache(self):
		make_change_proposal(ticket=self.ticket)
		self.assertIs(self._cards(CARD_INSTRUCTOR)[0]["can_decide"], True)
		set_agent_settings(one_click_approval_enabled=0)
		card = self._cards(CARD_INSTRUCTOR)[0]
		self.assertIs(card["can_decide"], False)
		self.assertIs(card["can_open"], True)
		set_agent_settings(one_click_approval_enabled=1)
		self.assertIs(self._cards(CARD_INSTRUCTOR)[0]["can_decide"], True)

	def test_failed_card_masks_reason(self):
		proposal = make_change_proposal(ticket=self.ticket)
		reason = (
			"<script>alert(1)</script> loi tai https://secret.example/x?k=1 va ai@example.com " + "x" * 400
		)
		self._set(proposal.name, change_status=CHANGE_STATUS_FAILED, failure_reason=reason)
		card = self._cards()[0]
		self.assertNotIn("https://", card["failure_reason"])
		self.assertNotIn("@", card["failure_reason"])
		self.assertNotIn("secret.example", card["failure_reason"])
		self.assertIn("[đã ẩn]", card["failure_reason"])
		self.assertIn(
			"<script>alert(1)</script>", card["failure_reason"]
		)  # plain text; the panel shows it by textContent
		self.assertLessEqual(len(card["failure_reason"]), 300)
		self._set(proposal.name, failure_reason=None)
		self.assertIsNone(self._cards()[0]["failure_reason"])

	def test_decided_by_is_a_safe_person_name_not_an_email(self):
		proposal = make_change_proposal(ticket=self.ticket)
		self.assertIsNone(self._cards()[0]["decided_by"])
		self._set(proposal.name, decided_by=CARD_INSTRUCTOR)
		decided_by = self._cards()[0]["decided_by"]
		self.assertEqual(decided_by, frappe.utils.get_fullname(CARD_INSTRUCTOR))
		self.assertNotIn("@", decided_by)

	def test_unreadable_notes_card_shows_the_warning_line(self):
		proposal = make_change_proposal(ticket=self.ticket)
		self._set(proposal.name, restart_status="Không có trạng thái này")
		self.assertEqual(self._cards()[0]["notes"], [proposal_form.UNREADABLE_NOTES])
