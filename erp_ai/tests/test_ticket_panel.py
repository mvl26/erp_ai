import contextlib
import hashlib
import inspect
import json
from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs

import frappe
import frappe.handler
from frappe.core.utils import html_to_plain_text
from frappe.tests.utils import FrappeTestCase
from frappe.utils import background_jobs
from helpdesk.test_utils import create_agent, make_ticket, make_todo
from helpdesk.utils import is_agent
from rq.job import JobStatus

from erp_ai import change_decision, ticket_panel
from erp_ai.agent import (
	answer_delay,
	bot_status,
	change_link,
	change_text,
	kpi,
	messages,
	policy,
	run_log,
	runner,
)
from erp_ai.agent.changes import apply_job, transitions
from erp_ai.agent.policy import contains_keyword
from erp_ai.agent.queue import PENDING_JOB_IDS_FLAG
from erp_ai.agent.run_log import write_entry
from erp_ai.agent.tools import propose_change, write_ticket
from erp_ai.constants import (
	AGENT_USER,
	CHANGE_KIND_COMMAND,
	CHANGE_STATUS_APPLIED,
	CHANGE_STATUS_APPROVED,
	CHANGE_STATUS_FAILED,
	CHANGE_STATUS_PENDING,
	CHANGE_STATUS_REJECTED,
	CHANGE_STATUS_STALE,
	CHANGE_STATUS_UNDOING,
	CHANGE_STATUS_UNDONE,
	CLASSIFICATION_FIELDS,
	EVENT_CALL_BUSY,
	EVENT_CALL_MERGED,
	EVENT_RUN_DONE,
	EVENT_RUN_FAILED,
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
	SKIP_AGENT_DISABLED,
	TITLE_RUN_FAILED,
	TRIGGER_COMMENT_MENTION,
)
from erp_ai.erp_ai_agent.doctype.erp_ai_change_proposal import erp_ai_change_proposal as proposal_form
from erp_ai.gateway import GatewayError
from erp_ai.test_utils import (
	FakeGateway,
	GitSandbox,
	keep_agent_settings,
	make_block_proposal,
	make_change_proposal,
	make_model_result,
	record_status_signals,
	set_agent_settings,
	stub_job_states,
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
# CHG-010: thread rows carry the raw creation time as `created`
# ADR-050: "kind" marks the bot's guidance message ("guidance"), "" for any other
THREAD_KEYS = {"name", "author", "is_bot", "created_at", "created", "text", "kind"}


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
		# ADR-044 QĐ 1 (CHG-008): the panel gains its one decision method, a third POST-only method
		self.assertEqual(
			PANEL_METHODS,
			(
				"erp_ai.ticket_panel.get_panel_data",
				"erp_ai.ticket_panel.send_message",
				"erp_ai.ticket_panel.decide_proposal",
			),
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
		# ADR-044 (CHG-008): the read result gains `proposals`, the cards of the ticket's change proposals; ADR-044
		# Amendment 1 (CHG-009, ADR-048): and `bot_status`, the bot's status line and system lines
		self.assertEqual(
			set(json.loads(result)), {"ticket", "ai_fields", "messages", "proposals", "bot_status"}
		)

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
		# CHG-009 (STD-TEST-6): a send with the bot on reads the RQ job state from this stub, never the shared Redis
		stub_job_states(self, {})
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
		# CHG-009 (STD-TEST-6): every branch queues with the bot on; the RQ job state comes from this stub
		stub_job_states(self, {})
		month_spend_patch = patch.object(policy, "month_spend_usd", return_value=0.0)
		self.month_spend = month_spend_patch.start()
		self.addCleanup(month_spend_patch.stop)

		if not frappe.db.exists("Role", ROLE_INSTRUCTOR):
			frappe.get_doc({"doctype": "Role", "role_name": ROLE_INSTRUCTOR}).insert(ignore_permissions=True)
		create_agent(AGENT_EMAIL)
		create_agent(self.INSTRUCTOR_EMAIL)
		frappe.get_doc("User", self.INSTRUCTOR_EMAIL).add_roles(ROLE_INSTRUCTOR)
		# learning off: no lesson of the shared site reaches the runs of this test (NFR-7, FEAT-008 ruling R7)
		set_agent_settings(lessons_enabled=0)

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
				# CHG-010: time of the proposal, and the console script and masked output for readers
				"created",
				"is_console",
				"script",
				"output",
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
				# CHG-010: the proposal time, so cards sort among thread rows
				"creation",
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
		# ADR-044 Amendment 1 (CHG-009, ADR-048): the closed key set gains `bot_status`
		self.assertEqual(set(result), {"ticket", "ai_fields", "messages", "proposals", "bot_status"})
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

	def test_console_card_can_decide_follows_the_console_switch(self):
		# CHG-010: a console card reads the console switch, not the one-click switch
		name = make_change_proposal(
			CHANGE_KIND_COMMAND,
			ticket=self.ticket,
			command_args=None,
			app=None,
			command_list=json.dumps([["--site", frappe.local.site, "console"]]),
			content_after="print(1)\n",
		).name
		for one_click, console, expected in ((0, 1, True), (1, 0, False), (0, 0, False), (1, 1, True)):
			with self.subTest(one_click=one_click, console=console):
				set_agent_settings(one_click_approval_enabled=one_click, console_enabled=console)
				cards = {card["name"]: card for card in self._cards(CARD_INSTRUCTOR)}
				self.assertIs(cards[name]["can_decide"], expected)

	def _console(self):
		return make_change_proposal(
			CHANGE_KIND_COMMAND,
			ticket=self.ticket,
			command_args=None,
			app=None,
			command_list=json.dumps([["--site", frappe.local.site, "console"]]),
			content_after="print(1)\n",
		).name

	def _console_with_output(self, output):
		name = self._console()
		self._set(name, command_output=output)
		return name

	def test_console_card_gives_readers_the_script_and_masked_output(self):
		# CHG-010: Task 6
		secret = "zq-secret-token-value-123456"
		lines = [f"line {i}" for i in range(30)] + [f"password={secret}"]
		name = self._console_with_output("\n".join(lines))
		self._set(name, content_after="print('hello')\n")
		card = {c["name"]: c for c in self._cards(CARD_INSTRUCTOR)}[name]
		self.assertIs(card["is_console"], True)
		self.assertEqual(card["script"], "print('hello')\n")
		self.assertNotIn(secret, card["output"])
		self.assertIn("[đã che]", card["output"])
		self.assertLessEqual(len(card["output"].splitlines()), 20)
		self.assertIn("line 29", card["output"])
		self.assertNotIn("line 5\n", card["output"])

	def test_console_card_hides_script_and_output_from_a_viewer_who_cannot_open(self):
		# CHG-010: Task 6
		name = self._console_with_output("done")
		card = {c["name"]: c for c in self._cards(AGENT_EMAIL)}[name]
		self.assertIs(card["can_open"], False)
		self.assertIs(card["is_console"], True)
		self.assertIsNone(card["script"])
		self.assertIsNone(card["output"])

	def test_console_card_without_output_or_script_carries_none(self):
		# CHG-010 final review F-5: a pending console card has no output yet; an empty block is None, never ""
		name = self._console()
		card = {c["name"]: c for c in self._cards(CARD_INSTRUCTOR)}[name]
		self.assertEqual(card["script"], "print(1)\n")
		self.assertIsNone(card["output"])
		self._set(name, content_after="", command_output="\n\n")
		card = {c["name"]: c for c in self._cards(CARD_INSTRUCTOR)}[name]
		self.assertIsNone(card["script"])
		self.assertIsNone(card["output"])

	def test_console_card_offers_no_decision_to_a_viewer_who_cannot_open_it(self):
		# CHG-010 final review F-7: the role and the switch are not enough for a console card; Duyệt never shows
		# without the script, so the viewer must also read the proposal. Other kinds keep their rule.
		set_agent_settings(one_click_approval_enabled=1, console_enabled=1)
		console = self._console()
		other = make_change_proposal(ticket=self.ticket).name
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": CARD_INSTRUCTOR,
				"allow": PROPOSAL_DOCTYPE,
				"for_value": other,
			}
		).insert(ignore_permissions=True)
		frappe.clear_cache(user=CARD_INSTRUCTOR)
		cards = {c["name"]: c for c in self._cards(CARD_INSTRUCTOR)}
		self.assertIs(cards[console]["can_open"], False)
		self.assertIs(cards[console]["can_decide"], False)
		self.assertIsNone(cards[console]["script"])
		self.assertIs(cards[other]["can_open"], True)
		self.assertIs(cards[other]["can_decide"], True)

	def test_code_proposal_content_never_reaches_the_panel(self):
		# CHG-010: Task 6; spec rule since CHG-008, the card reads no content of a code proposal
		proposal = make_change_proposal(ticket=self.ticket)
		self._set(
			proposal.name,
			content_after="zq-seed-after-text",
			command_output="zq-seed-output-text",
		)
		for user in (AGENT_EMAIL, CARD_INSTRUCTOR):
			with self.subTest(user=user):
				frappe.set_user(user)
				try:
					text = json.dumps(ticket_panel.get_panel_data(self.ticket), ensure_ascii=False)
				finally:
					frappe.set_user("Administrator")
				self.assertNotIn("zq-seed-after", text)
				self.assertNotIn("zq-seed-output", text)
				card = self._cards(user)[0]
				self.assertIs(card["is_console"], False)
				self.assertIsNone(card["script"])
				self.assertIsNone(card["output"])

	def test_card_created_is_the_proposal_creation(self):
		# CHG-010: Task 6
		first = make_change_proposal(ticket=self.ticket)
		second = self._console()
		for name, stamp in (
			(first.name, "2001-01-01 10:00:00.123456"),
			(second, "2001-01-02 10:00:00.654321"),
		):
			self._set(name, creation=stamp)
		for card in self._cards(CARD_INSTRUCTOR):
			self.assertEqual(
				card["created"], str(frappe.db.get_value(PROPOSAL_DOCTYPE, card["name"], "creation"))
			)

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

	def test_unreadable_commands_reduce_only_that_card(self):
		# Final review F-1: one proposal with unreadable stored commands never breaks the panel (AC-11, ADR-009 QĐ 4)
		good = make_change_proposal(ticket=self.ticket)
		for bad_commands in ("{", "5"):
			with self.subTest(command_list=bad_commands):
				bad = make_change_proposal(ticket=self.ticket)
				self._set(bad.name, command_list=bad_commands)
				frappe.set_user(CARD_INSTRUCTOR)
				try:
					result = ticket_panel.get_panel_data(self.ticket)
				finally:
					frappe.set_user("Administrator")
				self.assertIn("messages", result)
				cards = {card["name"]: card for card in result["proposals"]}
				self.assertEqual(set(cards[bad.name]), set(proposal_form.CARD_KEYS))
				self.assertEqual(cards[bad.name]["notes"], [proposal_form.UNREADABLE_NOTES])
				self.assertEqual(cards[bad.name]["target"], "")
				self.assertEqual(cards[bad.name]["status"], CHANGE_STATUS_PENDING)
				self.assertIs(cards[bad.name]["can_decide"], False)
				self.assertIs(cards[bad.name]["can_open"], True)
				self.assertEqual(set(cards[good.name]), set(proposal_form.CARD_KEYS))
				self.assertNotEqual(cards[good.name]["notes"], [proposal_form.UNREADABLE_NOTES])
				self.assertTrue(cards[good.name]["target"])
				self.assertIs(cards[good.name]["can_decide"], True)

	def test_can_open_loads_no_proposal_document(self):
		# CHG-008 ruling: the card never reads the forbidden fields, so no proposal document is loaded for can_open
		for _ in range(3):
			make_change_proposal(ticket=self.ticket)
		real_get_doc = frappe.get_doc
		loads = []

		def counting(*args, **kwargs):
			if args and (
				args[0] == PROPOSAL_DOCTYPE
				or (isinstance(args[0], dict) and args[0].get("doctype") == PROPOSAL_DOCTYPE)
			):
				loads.append(args)
			return real_get_doc(*args, **kwargs)

		with patch.object(frappe, "get_doc", side_effect=counting):
			cards = self._cards(CARD_INSTRUCTOR)
		self.assertEqual(len(cards), 3)
		self.assertTrue(all(card["can_open"] for card in cards))
		self.assertEqual(loads, [])

	def test_can_open_follows_a_share_per_proposal(self):
		shared = make_change_proposal(ticket=self.ticket)
		other = make_change_proposal(ticket=self.ticket)
		frappe.share.add(
			PROPOSAL_DOCTYPE, shared.name, AGENT_EMAIL, read=1, flags={"ignore_share_permission": True}
		)
		cards = {card["name"]: card for card in self._cards(AGENT_EMAIL)}
		self.assertIs(cards[shared.name]["can_open"], True)
		self.assertIs(cards[other.name]["can_open"], False)

	def test_decided_by_without_user_row_or_with_at_sign_is_anonymous(self):
		# D-5: get_fullname falls back to the email for a missing User, which must never reach the panel
		proposal = make_change_proposal(ticket=self.ticket)
		self._set(proposal.name, decided_by="zq.ghost.user@example.com")
		for name in (None, "zq.at@example.com"):
			with self.subTest(fullname=name):
				if name is None:
					result = json.dumps(self._cards(), ensure_ascii=False)
				else:
					with patch.object(frappe.utils, "get_fullname", return_value=name):
						result = json.dumps(self._cards(), ensure_ascii=False)
				self.assertEqual(json.loads(result)[0]["decided_by"], change_text.ANONYMOUS_PERSON)
				self.assertNotIn("@", result)


DECIDE_INSTRUCTOR = "panel.decide.instructor@example.com"
DECIDE_METHOD = "erp_ai.ticket_panel.decide_proposal"
RUN_CHANGE = "erp_ai.agent.changes.apply_job.run_change"
APPROVE = change_link.ACTION_APPROVE
REJECT = change_link.ACTION_REJECT
# Design 3.2 error sentences, copied by hand (not a contract, D-2; pinned so a refusal is the expected one).
GATE_TEXT = "Bạn không có quyền xem khu vực này của phiếu."
AGENT_DECIDE_TEXT = "Tài khoản agent không được duyệt hoặc từ chối đề xuất."
BAD_ACTION_TEXT = "Hành động không hợp lệ."
APPLY_APP = "custom_app"
APPLY_REL = "pkg/mod.py"
APPLY_BEFORE = "x = 1\n"
APPLY_AFTER = "x = 2\n"


def _sha(text: str) -> str:
	return hashlib.sha256(text.encode("utf-8")).hexdigest()


class TestPanelDecision(FrappeTestCase):
	"""CHG-008 design 3.2, 4.2 (AC-5..AC-8, AC-10): the panel's Duyệt / Từ chối buttons are one POST that passes
	the panel gate on the proposal's own ticket and the panel predicate, then the form's own approve / reject."""

	def setUp(self):
		# Cleanups run LIFO: settings restore, set_user, rollback, then the roles cache the rollback leaves stale.
		for user in (DECIDE_INSTRUCTOR, AGENT_USER, NO_READ_EMAIL):
			self.addCleanup(frappe.clear_cache, user=user)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		keep_agent_settings(self)
		# The apply job commits its state; inside a test nothing may reach the database for good.
		for target, attribute in ((frappe.db, "commit"), (frappe, "log_error")):
			patcher = patch.object(target, attribute)
			patcher.start()
			self.addCleanup(patcher.stop)
		enqueue = patch.object(frappe, "enqueue")
		self.enqueue = enqueue.start()
		self.addCleanup(enqueue.stop)
		if not frappe.db.exists("Role", ROLE_INSTRUCTOR):
			frappe.get_doc({"doctype": "Role", "role_name": ROLE_INSTRUCTOR}).insert(ignore_permissions=True)
		create_agent(AGENT_EMAIL)
		create_agent(DECIDE_INSTRUCTOR)
		frappe.get_doc("User", DECIDE_INSTRUCTOR).add_roles(ROLE_INSTRUCTOR)
		set_agent_settings(one_click_approval_enabled=1)
		self.ticket = make_ticket(subject="Panel decide ticket").name
		self.proposal = make_change_proposal(ticket=self.ticket).name

	def _decide(self, name, action, user=DECIDE_INSTRUCTOR):
		frappe.set_user(user)
		try:
			return ticket_panel.decide_proposal(name, action)
		finally:
			frappe.set_user("Administrator")

	def _request(self, http_method, form, user=DECIDE_INSTRUCTOR):
		"""Run the method the way a request does: `frappe.handler.execute_cmd` under `user` and `http_method`."""
		frappe.set_user(user)
		try:
			with (
				patch.object(frappe.local, "request", SimpleNamespace(method=http_method), create=True),
				patch.object(frappe.local, "form_dict", frappe._dict(cmd=DECIDE_METHOD, **form)),
			):
				return frappe.handler.execute_cmd(DECIDE_METHOD)
		finally:
			frappe.set_user("Administrator")

	def _jobs(self):
		return [
			call.kwargs for call in self.enqueue.call_args_list if call.args and call.args[0] == RUN_CHANGE
		]

	def _state(self, name):
		return frappe.db.get_value(
			PROPOSAL_DOCTYPE,
			name,
			["change_status", "decided_by", "decided_at", "approved_digest", "modified"],
			as_dict=True,
		)

	def _log_rows(self, name):
		rows = frappe.get_all(
			LOG_DOCTYPE,
			filters={"change_proposal": name},
			fields=["change_step", "actor"],
			order_by="creation asc",
		)
		return [(row.change_step, row.actor) for row in rows]

	def _snapshot(self, name):
		"""What a refused call leaves unchanged: the proposal, the log, the change jobs, comments, notifications."""
		return (
			self._state(name),
			frappe.db.count(LOG_DOCTYPE),
			len(self._jobs()),
			frappe.db.count("Comment"),
			frappe.db.count("Notification Log"),
		)

	def assertRefused(self, name, action, error, user=DECIDE_INSTRUCTOR, text=None, proposal=None):
		"""`decide_proposal(name, action)` as `user` raises exactly `error` (with `text`) and writes nothing."""
		proposal = name if proposal is None else proposal
		before = self._snapshot(proposal)
		writes = frappe.db.transaction_writes
		with self.assertRaises(error) as caught:
			self._decide(name, action, user)
		self.assertEqual(frappe.db.transaction_writes, writes)
		self.assertIs(type(caught.exception), error)
		if text is not None:
			self.assertEqual(str(caught.exception), text)
		frappe.clear_messages()
		self.assertEqual(self._snapshot(proposal), before)

	def _bot_account_holds_everything(self):
		"""The agent account as an active Helpdesk agent holding the decider role: only its name can refuse it."""
		create_agent(AGENT_USER)
		frappe.get_doc("User", AGENT_USER).add_roles(ROLE_INSTRUCTOR)
		self.assertIn(ROLE_INSTRUCTOR, frappe.get_roles(AGENT_USER))

	def _console(self):
		return make_change_proposal(
			CHANGE_KIND_COMMAND,
			ticket=self.ticket,
			command_args=None,
			app=None,
			command_list=json.dumps([["--site", frappe.local.site, "console"]]),
			content_after="print(1)\n",
		).name

	def test_console_approve_needs_only_the_console_switch(self):
		# CHG-010: the panel is the one place a console proposal is approved; one-click approval is not its switch
		set_agent_settings(one_click_approval_enabled=0, console_enabled=1)
		name = self._console()
		result = self._decide(name, APPROVE)
		self.assertEqual(result, {"name": name, "status": CHANGE_STATUS_APPROVED})
		self.assertEqual(self._state(name).change_status, CHANGE_STATUS_APPROVED)
		self.assertEqual(len(self._jobs()), 1)

	def test_console_approve_refused_when_the_console_switch_is_off(self):
		set_agent_settings(one_click_approval_enabled=1, console_enabled=0)
		name = self._console()
		self.assertRefused(name, APPROVE, frappe.PermissionError, text="Chạy bench console đang tắt.")
		self.assertEqual(self._state(name).change_status, CHANGE_STATUS_PENDING)

	def test_console_approve_refused_when_the_clicker_cannot_read_the_proposal(self):
		# CHG-010 final review F-7: approving a script needs the right to read it, so nobody approves unseen code
		set_agent_settings(console_enabled=1)
		name = self._console()
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": DECIDE_INSTRUCTOR,
				"allow": PROPOSAL_DOCTYPE,
				"for_value": self.proposal,
			}
		).insert(ignore_permissions=True)
		frappe.clear_cache(user=DECIDE_INSTRUCTOR)
		frappe.set_user(DECIDE_INSTRUCTOR)
		try:
			self.assertFalse(frappe.has_permission(PROPOSAL_DOCTYPE, "read", doc=name))
		finally:
			frappe.set_user("Administrator")
		self.assertRefused(
			name,
			APPROVE,
			frappe.PermissionError,
			text="Bạn cần quyền xem đề xuất để duyệt script console.",
		)
		self.assertEqual(self._state(name).change_status, CHANGE_STATUS_PENDING)
		# the same user still approves a non-console proposal they read
		self.assertEqual(self._decide(self.proposal, APPROVE)["status"], CHANGE_STATUS_APPROVED)

	def test_console_reject_from_the_panel_with_console_on(self):
		set_agent_settings(console_enabled=1)
		name = self._console()
		self.assertEqual(self._decide(name, REJECT)["status"], CHANGE_STATUS_REJECTED)

	def test_signed_link_cannot_approve_a_console_proposal(self):
		# CHG-010: the signed one-click link refuses a console proposal and writes nothing
		set_agent_settings(one_click_approval_enabled=1, console_enabled=1)
		name = self._console()
		signature = parse_qs(change_link._signed_query(name, APPROVE))["_signature"][0]
		before = self._snapshot(name)
		frappe.set_user(DECIDE_INSTRUCTOR)
		try:
			with self.assertRaises(frappe.PermissionError):
				change_decision.decide(name, APPROVE, signature)
		finally:
			frappe.set_user("Administrator")
		frappe.clear_messages()
		self.assertEqual(self._snapshot(name), before)

	def test_form_reject_still_works_on_a_console_proposal(self):
		name = self._console()
		frappe.set_user(DECIDE_INSTRUCTOR)
		try:
			self.assertEqual(proposal_form.reject(name)["status"], CHANGE_STATUS_REJECTED)
		finally:
			frappe.set_user("Administrator")

	def test_approve_one_post_one_job(self):
		result = self._decide(self.proposal, APPROVE)
		self.assertEqual(result, {"name": self.proposal, "status": CHANGE_STATUS_APPROVED})
		self.assertEqual(self._state(self.proposal).change_status, CHANGE_STATUS_APPROVED)
		jobs = self._jobs()
		self.assertEqual(len(jobs), 1)
		self.assertEqual((jobs[0]["proposal_name"], jobs[0]["action"]), (self.proposal, "apply"))
		self.assertEqual(self._log_rows(self.proposal), [("approve", DECIDE_INSTRUCTOR)])

	def test_reject_no_job(self):
		result = self._decide(self.proposal, REJECT)
		self.assertEqual(result, {"name": self.proposal, "status": CHANGE_STATUS_REJECTED})
		self.assertEqual(self._state(self.proposal).change_status, CHANGE_STATUS_REJECTED)
		self.assertEqual(self._jobs(), [])
		self.assertEqual(self._log_rows(self.proposal), [("reject", DECIDE_INSTRUCTOR)])

	def test_second_post_refused_not_pending(self):
		self._decide(self.proposal, APPROVE)
		for action in (APPROVE, REJECT):
			with self.subTest(action=action):
				self.assertRefused(
					self.proposal,
					action,
					frappe.PermissionError,
					text=proposal_form.PANEL_REFUSALS["not_pending"],
				)
		self.assertEqual(self._state(self.proposal).change_status, CHANGE_STATUS_APPROVED)
		self.assertEqual(len(self._jobs()), 1)
		self.assertEqual(self._log_rows(self.proposal), [("approve", DECIDE_INSTRUCTOR)])

	def test_second_call_past_the_predicate_meets_the_row_lock(self):
		# Design 3.2 row 7 (plan Review focus 2): a second call read the head while the proposal was still pending,
		# the first call then decided it; the state machine's row lock refuses the second, and 1 job stays 1.
		frappe.set_user(DECIDE_INSTRUCTOR)
		stale = proposal_form.proposal_head(self.proposal)
		frappe.set_user("Administrator")
		self.assertEqual(stale.change_status, CHANGE_STATUS_PENDING)
		self._decide(self.proposal, APPROVE)
		with patch.object(proposal_form, "proposal_head", return_value=stale):
			for action in (APPROVE, REJECT):
				with self.subTest(action=action):
					self.assertRefused(
						self.proposal, action, transitions.InvalidTransition, proposal=self.proposal
					)
		self.assertEqual(self._state(self.proposal).change_status, CHANGE_STATUS_APPROVED)
		self.assertEqual(len(self._jobs()), 1)

	def test_get_refused(self):
		fn = frappe.get_attr(DECIDE_METHOD)
		self.assertIn(fn, frappe.whitelisted)
		self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[fn], ["POST"])
		self.assertNotIn(fn, frappe.guest_methods)
		form = {"name": self.proposal, "action": APPROVE}
		for action in (APPROVE, REJECT):
			with self.subTest(action=action):
				before = self._snapshot(self.proposal)
				with self.assertRaises(frappe.PermissionError):
					self._request("GET", {**form, "action": action})
				frappe.clear_messages()
				self.assertEqual(self._snapshot(self.proposal), before)
		# The same request as a POST is the one click: decided, one job.
		self.assertEqual(
			self._request("POST", form), {"name": self.proposal, "status": CHANGE_STATUS_APPROVED}
		)
		self.assertEqual(len(self._jobs()), 1)

	def test_refused_callers_change_nothing(self):
		self._bot_account_holds_everything()
		cases = (
			(AGENT_EMAIL, proposal_form.PANEL_REFUSALS["role"]),  # an agent without the decider role
			(AGENT_USER, AGENT_DECIDE_TEXT),
			("Administrator", proposal_form.PANEL_REFUSALS["role"]),
			("Guest", GATE_TEXT),
		)
		for user, text in cases:
			for action in (APPROVE, REJECT):
				with self.subTest(user=user, action=action):
					self.assertRefused(self.proposal, action, frappe.PermissionError, user=user, text=text)
		# Switch (5) is read again on every call: on for one call, off for the next.
		other = make_change_proposal(ticket=self.ticket).name
		self.assertEqual(self._decide(other, REJECT)["status"], CHANGE_STATUS_REJECTED)
		set_agent_settings(one_click_approval_enabled=0)
		for action in (APPROVE, REJECT):
			with self.subTest(switch="off", action=action):
				self.assertRefused(
					self.proposal,
					action,
					frappe.PermissionError,
					text=proposal_form.PANEL_REFUSALS["switch_off"],
				)
		self.assertEqual(self._state(self.proposal).change_status, CHANGE_STATUS_PENDING)
		self.assertEqual(self._jobs(), [])

	def test_gate_uses_ticket_of_proposal(self):
		other = make_ticket(subject="Panel decide other ticket").name
		theirs = make_change_proposal(ticket=other).name
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": DECIDE_INSTRUCTOR,
				"allow": "HD Ticket",
				"for_value": self.ticket,
			}
		).insert(ignore_permissions=True)
		frappe.clear_cache(user=DECIDE_INSTRUCTOR)
		frappe.set_user(DECIDE_INSTRUCTOR)
		try:
			self.assertTrue(frappe.has_permission("HD Ticket", "read", doc=self.ticket))
			self.assertFalse(frappe.has_permission("HD Ticket", "read", doc=other))
		finally:
			frappe.set_user("Administrator")
		for action in (APPROVE, REJECT):
			with self.subTest(action=action):
				self.assertRefused(theirs, action, frappe.PermissionError, text=GATE_TEXT)
		# The browser cannot point the gate at a ticket it reads: `ticket` is not a parameter of the method.
		before = self._snapshot(theirs)
		with self.assertRaises(frappe.PermissionError):
			self._request("POST", {"name": theirs, "action": APPROVE, "ticket": self.ticket})
		frappe.clear_messages()
		self.assertEqual(self._snapshot(theirs), before)
		# The same user decides a proposal of the ticket they read.
		self.assertEqual(self._decide(self.proposal, APPROVE)["status"], CHANGE_STATUS_APPROVED)

	def test_proposal_without_ticket_refused(self):
		# Plan Review focus 1: a proposal attached to no ticket has no panel, so no panel decides it.
		frappe.db.set_value(PROPOSAL_DOCTYPE, self.proposal, "ticket", None, update_modified=False)
		for user in (DECIDE_INSTRUCTOR, "Administrator"):
			for action in (APPROVE, REJECT):
				with self.subTest(user=user, action=action):
					self.assertRefused(
						self.proposal, action, frappe.PermissionError, user=user, text=GATE_TEXT
					)
		self.assertEqual(self._state(self.proposal).change_status, CHANGE_STATUS_PENDING)

	def test_bad_name_or_action(self):
		for action in ("undo", "confirm_restart", "APPROVE", "", None, 5, [APPROVE]):
			with self.subTest(action=action):
				self.assertRefused(self.proposal, action, frappe.ValidationError, text=BAD_ACTION_TEXT)
		for name in ("AICHG-zq-missing", "", "   ", None, 5, ["x"]):
			with self.subTest(name=name):
				self.assertRefused(name, APPROVE, frappe.DoesNotExistError, proposal=self.proposal)
		self.assertEqual(self._state(self.proposal).change_status, CHANGE_STATUS_PENDING)

	def test_checks_run_in_design_order(self):
		# D-3: action, then the proposal, then the gate on its ticket, then the predicate (role, pending, switch).
		self.assertRefused(
			"AICHG-zq-missing", "undo", frappe.ValidationError, user="Guest", proposal=self.proposal
		)
		self.assertRefused(
			"AICHG-zq-missing", APPROVE, frappe.DoesNotExistError, user="Guest", proposal=self.proposal
		)
		self.assertRefused(self.proposal, APPROVE, frappe.PermissionError, user="Guest", text=GATE_TEXT)
		create_agent(NO_READ_EMAIL)
		user = frappe.get_doc("User", NO_READ_EMAIL)
		user.remove_roles("Agent", "Agent Manager")
		user.add_roles(ROLE_INSTRUCTOR)
		frappe.set_user(NO_READ_EMAIL)
		try:
			self.assertTrue(is_agent())
			self.assertFalse(frappe.has_permission("HD Ticket", "read", doc=self.ticket))
		finally:
			frappe.set_user("Administrator")
		self.assertRefused(self.proposal, APPROVE, frappe.PermissionError, user=NO_READ_EMAIL, text=GATE_TEXT)
		frappe.db.set_value(
			PROPOSAL_DOCTYPE, self.proposal, "change_status", CHANGE_STATUS_APPROVED, update_modified=False
		)
		set_agent_settings(one_click_approval_enabled=0)
		self.assertRefused(
			self.proposal,
			APPROVE,
			frappe.PermissionError,
			user=AGENT_EMAIL,
			text=proposal_form.PANEL_REFUSALS["role"],
		)
		self.assertRefused(
			self.proposal, APPROVE, frappe.PermissionError, text=proposal_form.PANEL_REFUSALS["not_pending"]
		)

	def test_panel_approval_records_clicker(self):
		other = make_change_proposal(ticket=self.ticket).name
		self._decide(self.proposal, APPROVE)
		self._decide(other, REJECT)
		for name, step in ((self.proposal, "approve"), (other, "reject")):
			with self.subTest(step=step):
				state = self._state(name)
				self.assertEqual(state.decided_by, DECIDE_INSTRUCTOR)
				self.assertIsNotNone(state.decided_at)
				self.assertEqual(self._log_rows(name), [(step, DECIDE_INSTRUCTOR)])

	def test_panel_approval_rechecked_at_apply(self):
		# ADR-023 QĐ 2: the apply job checks the approver again; a role taken away after the click stops it.
		sandbox = GitSandbox(self)
		sandbox.commit_file(APPLY_APP, APPLY_REL, APPLY_BEFORE)
		set_agent_settings(code_change_enabled=1, code_change_apps=APPLY_APP)
		name = make_change_proposal(
			ticket=self.ticket,
			app=APPLY_APP,
			file_path=f"{APPLY_APP}/{APPLY_REL}",
			content_before=APPLY_BEFORE,
			content_after=APPLY_AFTER,
			base_hash=_sha(APPLY_BEFORE),
			after_hash=_sha(APPLY_AFTER),
			target_branch="main",
			upstream_ref="",
		).name

		def commits():
			return int(sandbox.git(APPLY_APP, "rev-list", "--count", "HEAD").strip())

		before = commits()
		self.assertEqual(self._decide(name, APPROVE)["status"], CHANGE_STATUS_APPROVED)
		frappe.get_doc("User", DECIDE_INSTRUCTOR).remove_roles(ROLE_INSTRUCTOR)
		frappe.set_user(DECIDE_INSTRUCTOR)
		try:
			apply_job.run_change(name, "apply")
		finally:
			frappe.set_user("Administrator")
		state = frappe.db.get_value(PROPOSAL_DOCTYPE, name, ["change_status", "failure_reason"], as_dict=True)
		self.assertEqual(
			(state.change_status, state.failure_reason), (CHANGE_STATUS_FAILED, apply_job.APPROVER_LOST_ROLE)
		)
		self.assertEqual(commits(), before)
		with open(f"{sandbox.repo(APPLY_APP)}/{APPLY_REL}", encoding="utf-8") as handle:
			self.assertEqual(handle.read(), APPLY_BEFORE)

	def test_agent_session_refused(self):
		# AC-8 (a): the bot's own session, holding every right a decider has, is refused by name and writes nothing.
		self._bot_account_holds_everything()
		frappe.set_user(AGENT_USER)
		try:
			self.assertTrue(is_agent())
			self.assertTrue(frappe.has_permission("HD Ticket", "read", doc=self.ticket))
		finally:
			frappe.set_user("Administrator")
		for action in (APPROVE, REJECT):
			with self.subTest(action=action):
				self.assertRefused(
					self.proposal, action, frappe.PermissionError, user=AGENT_USER, text=AGENT_DECIDE_TEXT
				)
		self.assertEqual(self._state(self.proposal).change_status, CHANGE_STATUS_PENDING)
		self.assertEqual(self._log_rows(self.proposal), [])

	def test_typed_ok_is_only_a_message(self):
		# AC-8 (c): typing an approval word is a chat message; a bot run that answers "ok" decides nothing either.
		record_status_signals(self)
		set_agent_settings(
			enabled=1,
			trigger_keyword=KEYWORD,
			permission_level="L2",
			max_runs_per_ticket_per_day=10,
			max_turns_per_run=4,
			monthly_budget_usd=1,
			spent_this_month_usd=0,
			excluded_teams="",
		)
		write_entry(
			ticket=self.ticket,
			run_id="ERPAI-TEST-decide-classified",
			entry_type="classify",
			trigger="ticket_insert",
			turn=0,
			predicted_category="A",
			predicted_confidence_pct=100,
		)
		before = self._state(self.proposal)
		for text in ("ok", "duyệt", "approve"):
			with self.subTest(text=text):
				count = frappe.db.count(MESSAGE_DOCTYPE, {"ticket": self.ticket})
				frappe.set_user(DECIDE_INSTRUCTOR)
				try:
					sent = ticket_panel.send_message(self.ticket, text)["message"]
				finally:
					frappe.set_user("Administrator")
				self.assertEqual(frappe.db.count(MESSAGE_DOCTYPE, {"ticket": self.ticket}), count + 1)
				self.assertEqual(
					tuple(frappe.db.get_value(MESSAGE_DOCTYPE, sent, ["content", "owner"])),
					(text, DECIDE_INSTRUCTOR),
				)
		runs = [
			call.kwargs for call in self.enqueue.call_args_list if call.args and call.args[0] == RUN_ROUTE
		]
		self.assertTrue(runs)
		gateway = FakeGateway(*(make_model_result(text="ok") for _ in runs))
		with (
			patch("erp_ai.gateway.call_model", gateway),
			patch.object(answer_delay, "_sleep"),
			patch.object(policy, "month_spend_usd", return_value=0.0),
		):
			for job in runs:
				runner.run_for_ticket(job["ticket_name"], job["trigger"], job.get("message_name"))
		self.assertGreater(gateway.call_count, 0)
		self.assertEqual(self._state(self.proposal), before)
		self.assertEqual(self._jobs(), [])

	def test_decision_adds_no_comment_or_notification(self):
		other = make_change_proposal(ticket=self.ticket).name
		before = (frappe.db.count("Comment"), frappe.db.count("Notification Log"))
		self._decide(self.proposal, APPROVE)
		self._decide(other, REJECT)
		self.assertEqual((frappe.db.count("Comment"), frappe.db.count("Notification Log")), before)

	def test_decide_logs_ids_only(self):
		# Design 6 (Observation): the decision, the refusal and the gate denial, by ids and reason keys only.
		self._bot_account_holds_everything()
		logger = MagicMock()
		with patch.object(ticket_panel.frappe, "logger", return_value=logger):
			self._decide(self.proposal, APPROVE)
			with self.assertRaises(frappe.PermissionError):
				self._decide(self.proposal, REJECT)
			with self.assertRaises(frappe.PermissionError):
				self._decide(self.proposal, APPROVE, user=AGENT_USER)
		lines = [
			call.args[0]
			for call in logger.info.call_args_list
			if call.args and str(call.args[0]).startswith("erp_ai panel")
		]
		self.assertEqual(
			lines,
			[
				f"erp_ai panel decide proposal={self.proposal} action=approve status={CHANGE_STATUS_APPROVED}",
				f"erp_ai panel decide refused proposal={self.proposal} reason=not_pending",
				f"erp_ai panel denied method=decide ticket={self.ticket} reason=agent_user",
			],
		)
		for leak in (
			DECIDE_INSTRUCTOR,
			AGENT_USER,
			"Đề xuất mẫu",
			proposal_form.PANEL_REFUSALS["not_pending"],
		):
			with self.subTest(leak=leak):
				self.assertNotIn(leak, "\n".join(lines))


# CHG-009 design 3.1: the keys of `bot_status` and of each of its system lines.
STATUS_KEYS = {"state", "text", "expires_in_s", "expired_text", "lines"}
LINE_KEYS = {"kind", "text", "after_message"}
# AC-1: the open call's form of the status line, as the spec quotes it.
TEXT_RUNNING = "Đang xử lý…"
# Frappe runs a job as `method(**kwargs)` with the arguments `frappe.enqueue` does not keep for itself.
ENQUEUE_OWN_PARAMETERS = frozenset(inspect.signature(background_jobs.enqueue).parameters)
# The reader's clock: a case pins it to the time of the row it reads, so no assertion reads the wall clock.
STATUS_CLOCK = "erp_ai.agent.bot_status.now_datetime"


class ZqSeedFaultError(Exception):
	"""An error no step of a run expects, named so that its name is a seed (AC-8)."""


class TestPanelBotStatus(FrappeTestCase):
	"""CHG-009 AC-2, AC-6, AC-8, AC-9, AC-10, NFR-1, NFR-2 (design 3.1, 4, 5; ADR-010 Amendment 4, ADR-044
	Amendment 1, ADR-048 QĐ 6, 7): the panel's read carries the bot's status line and system lines in `bot_status`,
	built after the panel gate from codes only, writing nothing; a system line is never a message.

	The ticket is created with the bot off (one refusal line, as ticket 43229), then the bot is on. Each message is
	sent through the panel and each job it queued runs with the kwargs the queue gave it; the RQ job state is the
	stub `job_states` (STD-TEST-6)."""

	SAVEPOINT = "erp_ai_panel_bot_status"
	TEXT = "Kiểm tra giúp mã nhân viên"

	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("test must not commit"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		log_error = patch.object(frappe, "log_error")
		self.log_error = log_error.start()
		self.addCleanup(log_error.stop)
		self.job_states = stub_job_states(self, {})
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
		month_spend_patch.start()
		self.addCleanup(month_spend_patch.stop)
		self.addCleanup(frappe.flags.pop, PENDING_JOB_IDS_FLAG, None)
		create_agent(AGENT_EMAIL)
		# every value a run depends on is set here, never read from the shared site (STD-TEST-6, STD-TEST-8)
		set_agent_settings(
			enabled=0,
			trigger_keyword=KEYWORD,
			permission_level="L1",
			max_runs_per_ticket_per_day=5,
			max_turns_per_run=4,
			monthly_budget_usd=1,
			spent_this_month_usd=0,
			excluded_teams="",
			excluded_title_prefixes="",
			answer_delay_min_s=0,
			answer_delay_max_s=0,
			reply_enabled=0,
			kb_draft_enabled=0,
			auto_assign_enabled=0,
		)
		# learning off: no lesson of the shared site reaches the runs of this test (NFR-7, FEAT-008 ruling R7)
		set_agent_settings(lessons_enabled=0)
		self.ticket = make_ticket(subject="Panel bot status ticket").name
		# classified at full confidence: a message run reasons at once, one model call
		write_entry(
			ticket=self.ticket,
			run_id="ERPAI-TEST-panel-status-classified",
			entry_type="classify",
			trigger="ticket_insert",
			turn=0,
			predicted_category="A",
			predicted_confidence_pct=100,
		)
		set_agent_settings(enabled=1)

	def _read(self, user=AGENT_EMAIL, ticket=None):
		"""The panel's read as `user` (its own request); the session goes back to the one before."""
		previous = frappe.session.user
		frappe.set_user(user)
		try:
			return ticket_panel.get_panel_data(ticket or self.ticket)
		finally:
			frappe.set_user(previous)

	def _read_at(self, now, user=AGENT_EMAIL):
		with patch(STATUS_CLOCK, return_value=now):
			return self._read(user)

	def _send(self, text=TEXT):
		"""One send from the panel, its own request: no job claimed by an earlier request is left."""
		frappe.flags.pop(PENDING_JOB_IDS_FLAG, None)
		frappe.set_user(AGENT_EMAIL)
		try:
			return ticket_panel.send_message(self.ticket, text)["message"]
		finally:
			frappe.set_user("Administrator")

	def _jobs(self):
		"""The agent jobs queued so far, each as the kwargs Frappe runs it with."""
		return [
			{key: value for key, value in call.kwargs.items() if key not in ENQUEUE_OWN_PARAMETERS}
			for call in self.enqueue.call_args_list
			if call.args and call.args[0] == RUN_ROUTE
		]

	def _run_jobs(self):
		"""Run every queued agent job as the worker would, then forget them."""
		jobs = self._jobs()
		self.enqueue.reset_mock()
		for kwargs in jobs:
			runner.run_for_ticket(**kwargs)
		frappe.set_user("Administrator")
		return jobs

	def _event_at(self, code):
		"""When the ticket's one run_event row with `code` was written."""
		(creation,) = frappe.get_all(
			LOG_DOCTYPE,
			filters={"ticket": self.ticket, "entry_type": "run_event", "stop_reason": code},
			pluck="creation",
		)
		return creation

	def _events(self, code):
		return frappe.db.count(
			LOG_DOCTYPE, {"ticket": self.ticket, "entry_type": "run_event", "stop_reason": code}
		)

	def _status_texts(self, status):
		"""Every sentence of `bot_status` (not the message names its lines are anchored to)."""
		return "\n".join(
			[status["text"], str(status["expired_text"]), *(line["text"] for line in status["lines"])]
		)

	def _seed_every_reason(self):
		"""One row for each reason the panel names, written as its writer writes it: a refused call by the handlers
		(`record_event`), a stopped run by the runner (a skip row)."""
		for code in bot_status.REASONS:
			if code in run_log.EVENT_CODES:
				run_log.record_event(ticket=self.ticket, trigger=TRIGGER_COMMENT_MENTION, code=code)
			else:
				write_entry(
					ticket=self.ticket,
					run_id=f"ERPAI-TEST-panel-stop-{code}",
					entry_type="skip",
					trigger=TRIGGER_COMMENT_MENTION,
					turn=0,
					stop_reason=code,
				)

	def test_status_mid_run_and_after(self):
		# AC-2: a reload while the run works shows the open call; after the run, the time of its end row
		seen = []
		self.gateway.on_call = lambda task, kwargs: seen.append(self._read()["bot_status"]["text"])
		self._send()
		queued = self._read()["bot_status"]
		self.assertEqual((queued["state"], queued["text"]), ("running", TEXT_RUNNING))
		self.assertGreaterEqual(queued["expires_in_s"], 1)

		self._run_jobs()

		self.assertTrue(seen)
		self.assertEqual(set(seen), {TEXT_RUNNING})
		done_at = self._event_at(EVENT_RUN_DONE)
		result = self._read_at(done_at)
		status = result["bot_status"]
		done = f"Đã xong lúc {done_at:%H:%M}"
		self.assertEqual(
			(status["state"], status["text"], status["expires_in_s"], status["expired_text"]),
			("done", done, None, None),
		)
		self.assertEqual(
			status["lines"][-1],
			{"kind": "done", "text": done, "after_message": result["messages"][-1]["name"]},
		)

	def test_message_while_job_queued_or_started(self):
		# AC-6: a message sent while the ticket's message job waits or runs gets one line right under it and no run
		# of its own; the status line stays on the open call
		self._send()
		(job,) = self._jobs()
		job_id = self.enqueue.call_args.kwargs["job_id"]
		for job_state, kind in ((JobStatus.QUEUED, "merged"), (JobStatus.STARTED, "busy")):
			with self.subTest(job_state=job_state):
				self.job_states[job_id] = job_state
				self.enqueue.reset_mock()

				message = self._send()

				(merged_job,) = self._jobs()
				self.assertEqual(self.enqueue.call_args.kwargs["job_id"], job_id)
				self.assertIsNone(merged_job["run_id"])
				self.assertEqual(self._events("call_received"), 1)
				status = self._read()["bot_status"]
				self.assertEqual((status["state"], status["text"]), ("running", TEXT_RUNNING))
				under = [line for line in status["lines"] if line["after_message"] == message]
				self.assertEqual(
					under, [{"kind": kind, "text": bot_status.LINE_TEXTS[kind], "after_message": message}]
				)
		self.assertIsNotNone(job["run_id"])

	def test_failure_shows_no_detail(self):
		# AC-8, NFR-2: a failed run reads "Lỗi lúc HH:MM" with one failed line; no error class, key, HTTP status or
		# request id reaches the panel
		cases = {
			"gateway": (
				GatewayError(
					"server_error", status=529, credential_label="zq-seed-key", request_id="zq-seed-req"
				),
				contextlib.nullcontext,
				("GatewayError", "server_error", "529"),
			),
			"unexpected": (
				make_model_result(),
				lambda: patch.object(
					runner, "build_initial_message", side_effect=ZqSeedFaultError("zq-seed-detail")
				),
				("ZqSeedFaultError",),
			),
		}
		for case, (result, failure, names) in cases.items():
			with self.subTest(case=case):
				frappe.db.savepoint(self.SAVEPOINT)
				try:
					self.gateway.results = [result]
					self._send()
					with failure():
						self._run_jobs()

					failed_at = self._event_at(EVENT_RUN_FAILED)
					result = self._read_at(failed_at)
					status = result["bot_status"]
					failed = f"Lỗi lúc {failed_at:%H:%M}"
					self.assertEqual((status["state"], status["text"]), ("failed", failed))
					self.assertEqual(
						[line["text"] for line in status["lines"] if line["kind"] == "failed"], [failed]
					)
					dumped = json.dumps(result, ensure_ascii=False)
					texts = self._status_texts(status)
					for leak in ("zq-seed", *names):
						with self.subTest(leak=leak):
							self.assertNotIn(leak, texts)
							if leak != "529":
								# a ticket or message name may hold these digits; only the sentences may not
								self.assertNotIn(leak, dumped)
				finally:
					frappe.db.rollback(save_point=self.SAVEPOINT)

	def test_denied_callers_get_no_status(self):
		# AC-9: the status is built only after the panel gate: an HD contact who reads the ticket, Guest and an agent
		# who cannot read it get PermissionError, and the reader is never called for them
		_make_user(CUSTOMER_EMAIL)
		frappe.get_doc("User", CUSTOMER_EMAIL).add_roles("HD Customer")
		frappe.flags.pop(PENDING_JOB_IDS_FLAG, None)
		own = make_ticket(subject="Customer own ticket", raised_by=CUSTOMER_EMAIL).name
		self.addCleanup(frappe.clear_cache, user=NO_READ_EMAIL)
		create_agent(NO_READ_EMAIL)
		frappe.get_doc("User", NO_READ_EMAIL).remove_roles("Agent", "Agent Manager")
		self._send()
		with patch.object(bot_status, "panel_status", wraps=bot_status.panel_status) as reader:
			for user, ticket in ((CUSTOMER_EMAIL, own), ("Guest", self.ticket), (NO_READ_EMAIL, self.ticket)):
				with self.subTest(user=user), self.assertRaises(frappe.PermissionError):
					self._read(user, ticket)
			reader.assert_not_called()
			# the same tickets have a status for an agent who may read them: there was something to leak
			for ticket in (own, self.ticket):
				with self.subTest(ticket=ticket):
					self.assertEqual(self._read(ticket=ticket)["bot_status"]["text"], TEXT_RUNNING)
		self.assertEqual(reader.call_count, 2)

	def test_status_never_shows_settings_or_content(self):
		# AC-9, NFR-2, ADR-010 Amendment 4: a reason names its kind only; no setting, odd stop reason, ticket text,
		# message or model text reaches the status; the keys are exactly those of design 3.1
		set_agent_settings(
			trigger_keyword="zq-cfg-keyword",
			excluded_title_prefixes="zq-cfg-prefix",
			excluded_teams="zq-cfg-team",
			max_runs_per_ticket_per_day=9173,
			monthly_budget_usd=8642,
			thinking_text="zq-cfg-thinking",
		)
		frappe.db.set_value(
			"HD Ticket",
			self.ticket,
			{"subject": "zq-txt-subject", "description": "zq-txt-content"},
			update_modified=False,
		)
		self.gateway.results = [make_model_result(text="zq-txt-model")]
		self._send("zq-txt-message")
		self._run_jobs()
		self._seed_every_reason()
		write_entry(
			ticket=self.ticket,
			run_id="ERPAI-TEST-panel-odd-stop",
			entry_type="skip",
			trigger=TRIGGER_COMMENT_MENTION,
			turn=0,
			stop_reason="zq-stop-odd",
		)

		result = self._read()

		status = result["bot_status"]
		self.assertEqual(set(result), {"ticket", "ai_fields", "messages", "proposals", "bot_status"})
		self.assertEqual(set(status), STATUS_KEYS)
		self.assertEqual([set(line) for line in status["lines"]], [LINE_KEYS] * len(status["lines"]))
		# every reason is on the panel (the creation refusal too), so each was checked below
		reasons = [line for line in status["lines"] if line["kind"] == "not_run"]
		self.assertEqual(len(reasons), len(bot_status.REASONS) + 1)
		# the run took the seeded model text
		self.assertEqual(self.gateway.results, [])
		dumped = json.dumps(result, ensure_ascii=False)
		texts = self._status_texts(status)
		for leak in ("zq-cfg", "zq-stop"):
			with self.subTest(leak=leak):
				self.assertNotIn(leak, dumped)
		for leak in ("zq-txt", "zq-cfg", "zq-stop", "9173", "8642"):
			with self.subTest(leak=leak):
				self.assertNotIn(leak, texts)

	def test_system_lines_are_not_messages(self):
		# AC-10, ADR-048 QĐ 7: a system line comes from the log only: it is no message, starts no job, adds no
		# Comment, and changes neither the next run's model input nor what counts people's or the bot's words
		self.gateway.results = [make_model_result(text="Bot đã xem phiếu")]
		self._send("Tin đầu của người")
		self._run_jobs()
		raised_by = frappe.db.get_value("HD Ticket", self.ticket, "raised_by")

		def counts():
			return {
				"history": messages.history(self.ticket),
				"typed": messages.typed_by_people(self.ticket),
				"kpi3_touched": kpi._human_touched([frappe._dict(name=self.ticket, raised_by=raised_by)]),
				"guidance": write_ticket.count_guidance(self.ticket),
				"comments": frappe.db.count("Comment"),
				"thread": self._read()["messages"],
			}

		before = counts()
		for code in (EVENT_CALL_MERGED, EVENT_CALL_BUSY, SKIP_AGENT_DISABLED):
			run_log.record_event(ticket=self.ticket, trigger=TRIGGER_COMMENT_MENTION, code=code)
		for code in (EVENT_RUN_DONE, EVENT_RUN_FAILED):
			run_log.record_event(
				ticket=self.ticket, trigger=TRIGGER_COMMENT_MENTION, code=code, run_id=f"ERPAI-TEST-{code}"
			)
		lines = self._read()["bot_status"]["lines"]

		self.assertEqual({line["kind"] for line in lines}, {"merged", "busy", "not_run", "done", "failed"})
		self.assertEqual(counts(), before)
		self.assertEqual(
			[message["name"] for message in before["thread"]],
			frappe.get_all(
				MESSAGE_DOCTYPE,
				filters={"ticket": self.ticket},
				pluck="name",
				order_by="creation asc, name asc",
			),
		)
		self.enqueue.assert_not_called()
		# the next run reads the conversation: no system line is in what it sends the model
		self.gateway.calls.clear()
		self._send("Tin thứ hai của người")
		self._run_jobs()
		self.assertGreater(self.gateway.call_count, 0)
		model_input = json.dumps(self.gateway.calls, ensure_ascii=False, default=str)
		self.assertIn("Tin thứ hai của người", model_input)
		for line in lines:
			with self.subTest(line=line["text"]):
				self.assertNotIn(line["text"], model_input)

	def test_read_with_events_writes_nothing(self):
		# NFR-1, ADR-010 QĐ 5 (Amendment 4): a read that builds the status line, its deadline and system lines of
		# every kind writes no SQL, changes no count, calls no model and queues nothing
		self._send()
		self._run_jobs()
		self._send()
		self.job_states[self.enqueue.call_args.kwargs["job_id"]] = JobStatus.QUEUED
		self._send()
		self._seed_every_reason()
		self.enqueue.reset_mock()
		calls = self.gateway.call_count

		def counts():
			return {
				doctype: frappe.db.count(doctype)
				for doctype in ("Comment", MESSAGE_DOCTYPE, LOG_DOCTYPE, "ToDo", "Task", "Error Log")
			} | {"modified": frappe.db.get_value("HD Ticket", self.ticket, "modified")}

		before = counts()
		frappe.set_user(AGENT_EMAIL)
		for _ in range(3):
			writes = frappe.db.transaction_writes
			status = ticket_panel.get_panel_data(self.ticket)["bot_status"]
			self.assertEqual(frappe.db.transaction_writes, writes)
		frappe.set_user("Administrator")

		self.assertEqual((status["state"], status["text"]), ("running", TEXT_RUNNING))
		self.assertGreaterEqual(status["expires_in_s"], 1)
		self.assertEqual({line["kind"] for line in status["lines"]}, {"not_run", "done", "merged"})
		self.assertEqual(counts(), before)
		self.assertEqual(self.gateway.call_count, calls)
		self.enqueue.assert_not_called()
