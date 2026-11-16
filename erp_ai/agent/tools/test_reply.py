import ast
import inspect
import textwrap
from datetime import timedelta
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.helpdesk.doctype.hd_ticket import api as ticket_api
from helpdesk.helpdesk.doctype.hd_ticket.hd_ticket import HDTicket
from helpdesk.test_utils import make_ticket

from erp_ai.agent import lifecycle
from erp_ai.agent.redact import MASK
from erp_ai.agent.tools import reply, write_ticket
from erp_ai.agent.tools.registry import ToolContext, _first_invalid_key
from erp_ai.constants import AGENT_USER, LOGGER_NAME, SETTING_DOCTYPE, TRIGGER_TICKET_INSERT
from erp_ai.test_utils import keep_agent_settings, make_log_entry, pin_agent_roles, set_agent_settings

EXCLUDED_TEAM = "T151 Nhóm loại trừ"
# Helpdesk sends an agent reply as an email (Email Queue, delayed) only with these settings; a Sent message
# leaves the ticket status as it is.
EMAIL_REPLY_SETTINGS = {
	"enable_reply_email_via_agent": 1,
	"skip_email_workflow": 0,
	"instantly_send_email": 0,
	"auto_update_status": 0,
}
COMMENT_CALLS = ("new_comment", "add_comment")
REFUSED_TICKET = "phiếu không được phép đưa cho AI"
REASON_NO_REQUESTER = "phiếu không có người tạo để trả lời"
REASON_BELOW_THRESHOLD = "độ tin cậy dưới ngưỡng: chỉ được hỏi lại"
REASON_QUESTION_MARK = "câu hỏi lại phải có dấu ?"
REASON_F_SOURCE = (
	"đầu mục F: trả lời phải nêu ít nhất một nguồn (bài CSKT, mục HDSD hoặc số phiếu cũ); "
	"không có nguồn thì hỏi lại"
)
REASON_NOT_SENT = "chưa gửi được: site chưa có tài khoản email gửi đi"


def _unique(label: str) -> str:
	return f"erpai-test-{label}-{frappe.generate_hash(length=10).lower()}"


def _comment_calls(source: str) -> list[str]:
	"""Every name or attribute of `source` that is one of COMMENT_CALLS."""
	found = []
	for node in ast.walk(ast.parse(textwrap.dedent(source))):
		name = node.attr if isinstance(node, ast.Attribute) else getattr(node, "id", None)
		if name in COMMENT_CALLS:
			found.append(name)
	return sorted(found)


class ReplyCase(FrappeTestCase):
	"""Own data, rolled back after each test; the tool runs under the agent account, pinned to its roles."""

	def setUp(self):
		commit_guard = patch.object(
			frappe.db, "commit", side_effect=AssertionError("test must not commit the transaction")
		)
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		keep_agent_settings(self)
		pin_agent_roles(self)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		set_agent_settings(excluded_teams=EXCLUDED_TEAM, excluded_title_prefixes="")
		frappe.db.value_cache.pop(SETTING_DOCTYPE, None)
		# The cached HD Settings doc is dropped after the test (the values themselves roll back).
		self.addCleanup(frappe.clear_document_cache, "HD Settings", "HD Settings")
		frappe.db.set_single_value("HD Settings", EMAIL_REPLY_SETTINGS)
		self.assertTrue(
			frappe.db.exists("Email Account", {"enable_outgoing": 1, "default_outgoing": 1}),
			"the site needs a default outgoing Email Account",
		)

	def _ticket(self, category=None, raised_by=None, **values) -> str:
		"""A ticket of a fresh requester, classified `category` when given."""
		ticket = make_ticket(subject="ERPAI-TEST reply", raised_by=raised_by or f"{_unique('r')}@example.com")
		if values:
			# db.set_value skips the link check: the send predicate compares team names only.
			frappe.db.set_value("HD Ticket", ticket.name, values, update_modified=False)
		if category:
			make_log_entry(
				ticket=ticket.name,
				entry_type="classify",
				run_id=f"ERPAI-TEST-classify-{ticket.name}",
				trigger=TRIGGER_TICKET_INSERT,
				predicted_category=category,
			)
		return str(ticket.name)

	def _ctx(self, ticket, below_threshold=False) -> ToolContext:
		# A fresh run id per context: the one-ask mark of a run lives in the process flags.
		return ToolContext(
			ticket_name=ticket,
			effective_level="L2",
			instructor=None,
			run_id=_unique("run"),
			category_mapping={},
			agent_user=AGENT_USER,
			below_threshold=below_threshold,
		)

	def _reply(self, ticket, message="ERPAI-TEST câu trả lời", kind="answer", ctx=None, **args):
		frappe.set_user(AGENT_USER)
		try:
			return reply.reply_to_requester(
				{"message": message, "kind": kind, **args}, ctx or self._ctx(ticket)
			)
		finally:
			frappe.set_user("Administrator")

	def _sent(self, ticket) -> list[str]:
		"""The agent's Sent Communications of the ticket."""
		return frappe.get_all(
			"Communication",
			filters={
				"reference_doctype": "HD Ticket",
				"reference_name": ticket,
				"sent_or_received": "Sent",
				"owner": AGENT_USER,
			},
			pluck="name",
		)

	def _comments(self, ticket) -> int:
		return frappe.db.count(
			"Comment", {"reference_doctype": "HD Ticket", "reference_name": ticket, "comment_type": "Comment"}
		)

	def _content(self, result) -> str:
		self.assertTrue(result["ok"], result)
		return frappe.db.get_value("Communication", result["communication"], "content")

	def _assert_refused(self, ticket, result, reason) -> None:
		self.assertEqual(result, {"ok": False, "reason": reason})
		self.assertEqual(self._sent(ticket), [])


class TestReplyToRequester(ReplyCase):
	def test_spec_and_constants(self):
		(spec,) = reply.TOOLS
		self.assertEqual(
			(spec.name, spec.group, spec.handler),
			("reply_to_requester", "requester_reply", reply.reply_to_requester),
		)
		self.assertEqual(
			(reply.REPLY_KINDS, reply.REPLY_MAX_CHARS, reply.SOURCES_MAX), (("answer", "question"), 4000, 5)
		)
		schema = spec.schema["input_schema"]
		self.assertEqual(schema["required"], ["message", "kind"])
		self.assertIsNone(
			_first_invalid_key({"message": "x" * 4000, "kind": "question", "sources": ["a"] * 5}, schema)
		)
		for bad in (
			{"message": "", "kind": "answer"},
			{"message": "x" * 4001, "kind": "answer"},
			{"message": "x", "kind": "note"},
			{"message": "x", "kind": "answer", "sources": ["a"] * 6},
			{"message": "x", "kind": "answer", "sources": ["x" * 201]},
		):
			with self.subTest(bad):
				self.assertIsNotNone(_first_invalid_key(bad, schema))

	def test_customer_without_agent_role_reads_reply(self):
		customer = f"{_unique('customer')}@example.com"
		frappe.get_doc(
			{"doctype": "User", "email": customer, "first_name": "T151", "send_welcome_email": 0}
		).insert()
		frappe.get_doc("User", customer).add_roles("HD Customer")
		ticket = self._ticket(raised_by=customer)

		self.assertTrue(self._reply(ticket, message="ERPAI-TEST hướng dẫn cho khách")["ok"])

		self.assertNotIn("Agent", frappe.get_roles(customer))
		frappe.set_user(customer)
		contents = [row.content or "" for row in ticket_api.get_one(ticket)["communications"]]
		self.assertTrue(any("ERPAI-TEST hướng dẫn cho khách" in content for content in contents), contents)

	def test_sends_only_to_raised_by(self):
		ticket, other = self._ticket(), self._ticket()
		requester = frappe.db.get_value("HD Ticket", ticket, "raised_by")

		result = self._reply(ticket)

		self.assertEqual(set(result), {"ok", "communication"})
		communication = frappe.get_doc("Communication", result["communication"])
		self.assertEqual(
			(communication.recipients, communication.reference_name, communication.owner),
			(requester, ticket, AGENT_USER),
		)
		self.assertFalse(communication.cc or communication.bcc)
		(queue,) = frappe.get_all("Email Queue", filters={"communication": communication.name}, pluck="name")
		self.assertEqual(
			frappe.get_all("Email Queue Recipient", filters={"parent": queue}, pluck="recipient"), [requester]
		)
		self.assertEqual(self._sent(ticket), [communication.name])
		self.assertEqual(self._sent(other), [])
		# The tool takes no recipient and no ticket: the one recipient is raised_by of ctx.ticket_name.
		schema = reply.TOOLS[0].schema["input_schema"]
		self.assertEqual(set(schema["properties"]), {"message", "kind", "sources"})
		for extra in ("to", "recipients", "cc", "ticket"):
			self.assertEqual(
				_first_invalid_key({"message": "x", "kind": "answer", extra: "a@b.c"}, schema), extra
			)

	def test_excluded_team_refused(self):
		ticket = self._ticket(agent_group=EXCLUDED_TEAM)

		self._assert_refused(ticket, self._reply(ticket), REFUSED_TICKET)

	def test_ai_opt_out_refused(self):
		ticket = self._ticket(ai_opt_out=1)

		self._assert_refused(ticket, self._reply(ticket), REFUSED_TICKET)

	def test_no_requester_refused(self):
		ticket = self._ticket(raised_by=f"{_unique('r')}@example.com")
		frappe.db.set_value("HD Ticket", ticket, "raised_by", "", update_modified=False)

		self._assert_refused(ticket, self._reply(ticket), REASON_NO_REQUESTER)

	def test_category_f_answer_without_source_refused(self):
		ticket = self._ticket(category="F")
		for args in ({}, {"sources": []}):
			with self.subTest(args):
				self._assert_refused(ticket, self._reply(ticket, **args), REASON_F_SOURCE)

	def test_category_f_answer_with_source_sent(self):
		ticket = self._ticket(category="F")

		content = self._content(self._reply(ticket, sources=["KB-0001 In lại hóa đơn", "#123"]))

		self.assertIn("ERPAI-TEST câu trả lời", content)
		self.assertIn("Nguồn: KB-0001 In lại hóa đơn, #123", content)

	def test_category_f_question_without_source_sent(self):
		ticket = self._ticket(category="F")

		content = self._content(self._reply(ticket, message="ERPAI-TEST lỗi từ khi nào?", kind="question"))

		self.assertIn("ERPAI-TEST lỗi từ khi nào?", content)
		self.assertNotIn("Nguồn:", content)

	def test_below_threshold_answer_refused_question_allowed(self):
		ticket = self._ticket(category="C")
		ctx = self._ctx(ticket, below_threshold=True)

		self._assert_refused(ticket, self._reply(ticket, ctx=ctx), REASON_BELOW_THRESHOLD)
		self._assert_refused(
			ticket,
			self._reply(ticket, message="ERPAI-TEST không có dấu hỏi", kind="question", ctx=ctx),
			REASON_QUESTION_MARK,
		)
		self.assertTrue(
			self._reply(ticket, message="ERPAI-TEST màn hình nào?", kind="question", ctx=ctx)["ok"]
		)
		self.assertEqual(len(self._sent(ticket)), 1)

	def test_first_responded_on_set_after_first_reply(self):
		ticket = self._ticket()
		self.assertIsNone(frappe.db.get_value("HD Ticket", ticket, "first_responded_on"))

		self.assertTrue(self._reply(ticket)["ok"])
		first = frappe.db.get_value("HD Ticket", ticket, "first_responded_on")
		self.assertIsNotNone(first)
		with patch("frappe.utils.now_datetime", return_value=first + timedelta(days=1)):
			self.assertTrue(self._reply(ticket, message="ERPAI-TEST lần hai")["ok"])

		self.assertEqual(frappe.db.get_value("HD Ticket", ticket, "first_responded_on"), first)
		self.assertEqual(len(self._sent(ticket)), 2)

	def test_missing_outgoing_account_refused_no_comment(self):
		"""ADR-034 QĐ 7, R-1 (c): a reply that cannot be sent leaves no Communication and no stand-in comment."""
		ticket = self._ticket()

		with self.subTest("no outgoing account, as Helpdesk raises it"):
			with patch.object(HDTicket, "sender_email", return_value=None):
				self._assert_refused(ticket, self._reply(ticket), REASON_NOT_SENT)
		with self.subTest("the email fails after the Communication is written"):
			with patch("frappe.sendmail", side_effect=Exception("ERPAI-TEST smtp down")):
				self._assert_refused(ticket, self._reply(ticket), REASON_NOT_SENT)
			self.assertIsNone(frappe.db.get_value("HD Ticket", ticket, "first_responded_on"))
		with self.subTest("OutgoingEmailError, logged with the ticket and the error class"):
			with (
				patch.object(
					HDTicket, "reply_via_agent", side_effect=frappe.OutgoingEmailError("ERPAI-TEST")
				),
				patch.object(reply.frappe, "logger") as get_logger,
			):
				self._assert_refused(ticket, self._reply(ticket), REASON_NOT_SENT)
			get_logger.assert_any_call(LOGGER_NAME)
			lines = [call.args[0] % call.args[1:] for call in get_logger.return_value.warning.call_args_list]
			self.assertTrue(
				any(f"ticket={ticket}" in line and "OutgoingEmailError" in line for line in lines), lines
			)
		self.assertEqual(self._comments(ticket), 0)

	def test_never_calls_comment_api(self):
		self.assertEqual(_comment_calls(inspect.getsource(reply)), [])
		self.assertEqual(_comment_calls(inspect.getsource(lifecycle.send_to_requester)), [])
		# the scan itself sees both forms
		self.assertEqual(
			_comment_calls("doc.new_comment('x')\nadd_comment(1)\n"), ["add_comment", "new_comment"]
		)

	def test_question_marks_run_and_second_question_refused(self):
		"""E-1 (`w1b-r2.md:75`): one ask per run, the emailed question included."""
		ticket = self._ticket()
		ctx = self._ctx(ticket)
		self.assertFalse(write_ticket.asked_in_run(ctx.run_id))

		self.assertTrue(
			self._reply(ticket, message="ERPAI-TEST lỗi từ khi nào?", kind="question", ctx=ctx)["ok"]
		)
		self.assertTrue(write_ticket.asked_in_run(ctx.run_id))
		sent = self._sent(ticket)

		second = self._reply(ticket, message="ERPAI-TEST còn lỗi không?", kind="question", ctx=ctx)

		self.assertEqual(second, {"ok": False, "reason": write_ticket.REASON_ONE_ASK})
		self.assertEqual(self._sent(ticket), sent)
		answer_ctx = self._ctx(ticket)
		self.assertTrue(self._reply(ticket, ctx=answer_ctx)["ok"])
		self.assertFalse(write_ticket.asked_in_run(answer_ctx.run_id))

	def test_message_escaped_and_masked(self):
		ticket = self._ticket()

		content = self._content(
			self._reply(
				ticket,
				message="<b>ERPAI-TEST</b>\npassword: fake-reply-secret\ndòng ba",
				sources=["token=fake-src"],
			)
		)

		self.assertIn("&lt;b&gt;ERPAI-TEST&lt;/b&gt;", content)
		self.assertNotIn("<b>", content)
		self.assertIn("<br>", content)
		self.assertNotIn("fake-reply-secret", content)
		self.assertNotIn("fake-src", content)
		self.assertIn(MASK, content)

	def test_value_starting_with_angle_bracket_masked(self):
		"""R17a (NFR-6): the text is masked before it is escaped, so a value that starts with `<` is still caught
		(escaped first, it would start with `&lt;`, which no masking rule reads as a value)."""
		ticket = self._ticket()

		content = self._content(
			self._reply(
				ticket,
				message="ERPAI-TEST\npassword: <fake-reply-angle>\napi_key=<fake-reply-key>",
				sources=["token: <fake-src-angle>"],
			)
		)

		for secret in ("fake-reply-angle", "fake-reply-key", "fake-src-angle"):
			with self.subTest(secret=secret):
				self.assertNotIn(secret, content)
		self.assertEqual(content.count(MASK), 3, content)
