import ast
import inspect
from datetime import datetime, timedelta
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.agent import authority, lifecycle, policy
from erp_ai.constants import AGENT_USER, SETTING_DOCTYPE, TRIGGER_TICKET_INSERT
from erp_ai.test_utils import keep_agent_settings, make_log_entry, pin_agent_roles, set_agent_settings

# A real HD Ticket field erp_ai installs (Small Text), so no test creates a Custom Field (its ALTER TABLE commits).
ORIGIN_FIELD = "ai_score_reason"
BOARD_VALUE = "Chỉ đạo BGĐ"
OTHER_ORIGIN = "Phòng ban"
LIFECYCLE_MODULE = "erp_ai.agent.lifecycle"
GATEWAY_MODULES = ("erp_ai.gateway",)
TOOLS_OR_RUNNER_MODULES = ("erp_ai.agent.tools", "erp_ai.agent.runner")
# Every test message is dated in 2001: no live Communication of the shared site falls in a test's window.
DAY0 = datetime(2001, 1, 1, 8, 0, 0)
# Helpdesk sends an agent reply as an email (Email Queue, delayed) only with these settings.
EMAIL_REPLY_SETTINGS = {
	"enable_reply_email_via_agent": 1,
	"skip_email_workflow": 0,
	"instantly_send_email": 0,
}


def _forbidden_imports(source: str, forbidden: tuple[str, ...]) -> list[str]:
	"""Every module that `source` (read as erp_ai/agent/lifecycle.py) imports, or names in a string, and that is
	one of `forbidden` or under one; `from a import b` yields both `a` and `a.b` (b may be a submodule)."""
	found = []
	for node in ast.walk(ast.parse(source)):
		if isinstance(node, ast.Import):
			names = [alias.name for alias in node.names]
		elif isinstance(node, ast.ImportFrom):
			base = node.module or ""
			if node.level:
				package = LIFECYCLE_MODULE.split(".")[: -node.level]
				base = ".".join([*package, base] if base else package)
			names = [base, *(f"{base}.{alias.name}" for alias in node.names)]
		elif isinstance(node, ast.Constant) and isinstance(node.value, str):
			names = [node.value]
		else:
			continue
		found.extend(
			name
			for name in names
			if any(name == module or name.startswith(module + ".") for module in forbidden)
		)
	return found


class LifecycleTestCase(FrappeTestCase):
	"""Own data, rolled back after each test; the agent account pinned to its production roles."""

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
		self._settings(
			enabled=0,
			excluded_teams="",
			excluded_title_prefixes="",
			reply_enabled=0,
			resolve_on_tasks_done_enabled=0,
			close_silent_f_enabled=0,
			close_silent_f_days=3,
			kb_draft_enabled=0,
			field_origin=ORIGIN_FIELD,
			origin_board_value=BOARD_VALUE,
		)

	def _settings(self, **fields) -> None:
		set_agent_settings(**fields)
		frappe.db.value_cache.pop(SETTING_DOCTYPE, None)

	def _ls(self):
		return lifecycle.lifecycle_settings(frappe.get_single(SETTING_DOCTYPE))

	def _ticket(self, category=None, origin=OTHER_ORIGIN, **values) -> str:
		"""A ticket of a fresh requester with `origin` in ORIGIN_FIELD, classified `category` when given."""
		frappe.set_user("Administrator")
		raised_by = f"erpai-test-{frappe.generate_hash(length=10).lower()}@example.com"
		ticket = make_ticket(subject="ERPAI-TEST lifecycle", raised_by=raised_by)
		frappe.db.set_value("HD Ticket", ticket.name, {ORIGIN_FIELD: origin, **values}, update_modified=False)
		if category:
			make_log_entry(
				ticket=ticket.name,
				entry_type="classify",
				run_id=f"ERPAI-TEST-classify-{ticket.name}",
				trigger=TRIGGER_TICKET_INSERT,
				predicted_category=category,
			)
		return str(ticket.name)

	def _requester(self, ticket) -> str:
		return frappe.db.get_value("HD Ticket", ticket, "raised_by")

	def _message(self, ticket, sent_or_received, creation, sender, owner="Administrator", name=None) -> str:
		"""A Communication of `ticket` stored as is (no Helpdesk hook runs, so the ticket is left as it was)."""
		doc = frappe.get_doc(
			{
				"doctype": "Communication",
				"name": name,
				"communication_type": "Communication",
				"communication_medium": "Email",
				"sent_or_received": sent_or_received,
				"reference_doctype": "HD Ticket",
				"reference_name": ticket,
				"sender": sender,
				"subject": "ERPAI-TEST lifecycle",
				"content": "ERPAI-TEST lifecycle message",
				"owner": owner,
				"modified_by": owner,
				"creation": creation,
				"modified": creation,
			}
		)
		doc.db_insert()
		return doc.name

	def _bot_message(self, ticket, creation) -> str:
		return self._message(ticket, "Sent", creation, sender=AGENT_USER, owner=AGENT_USER)

	def _requester_message(self, ticket, creation, name=None) -> str:
		return self._message(ticket, "Received", creation, sender=self._requester(ticket), name=name)

	def _email_settings(self) -> None:
		"""Helpdesk queues an email for an agent reply; the cached HD Settings doc is dropped after the test."""
		self.addCleanup(frappe.clear_document_cache, "HD Settings", "HD Settings")
		frappe.db.set_single_value("HD Settings", EMAIL_REPLY_SETTINGS)
		self.assertTrue(
			frappe.db.exists("Email Account", {"enable_outgoing": 1, "default_outgoing": 1}),
			"the site needs a default outgoing Email Account",
		)


class TestLifecycleSettings(LifecycleTestCase):
	def test_reads_the_seven_fields(self):
		self._settings(
			reply_enabled=1,
			resolve_on_tasks_done_enabled=1,
			close_silent_f_enabled=0,
			close_silent_f_days=5,
			kb_draft_enabled=1,
			field_origin=f"  {ORIGIN_FIELD} ",
			origin_board_value=f" {BOARD_VALUE}  ",
		)
		self.assertEqual(
			self._ls(),
			lifecycle.LifecycleSettings(
				reply=True,
				resolve_on_tasks_done=True,
				close_silent_f=False,
				close_silent_f_days=5,
				kb_draft=True,
				field_origin=ORIGIN_FIELD,
				origin_board_value=BOARD_VALUE,
			),
		)
		self.assertTrue(lifecycle.kb_draft_enabled())
		self._settings(kb_draft_enabled=0)
		self.assertFalse(lifecycle.kb_draft_enabled())

	def test_missing_fields_read_off_and_days_default(self):
		self.assertEqual(
			lifecycle.lifecycle_settings(frappe._dict()),
			lifecycle.LifecycleSettings(False, False, False, 3, False, "", ""),
		)
		for days in (0, 31, "x", None):
			with self.subTest(days=days):
				settings = frappe._dict(close_silent_f_days=days)
				self.assertEqual(lifecycle.lifecycle_settings(settings).close_silent_f_days, 3)


class TestStatusGuard(LifecycleTestCase):
	def test_refusal_reasons_in_order(self):
		"""AC-42 (b), (c), A-U6b-5: each ticket also meets every later condition, so only the order picks its reason."""
		all_bad = self._ticket(category="E", origin=BOARD_VALUE, **{policy.OPT_OUT_FIELD: 1})
		board_e = self._ticket(category="E", origin=f"  {BOARD_VALUE.casefold()} ")
		category_e = self._ticket(category="E")
		category_f = self._ticket(category="F")
		unclassified = self._ticket()

		for case, fields in (
			("field_origin empty", {"field_origin": ""}),
			("field_origin not a field of HD Ticket", {"field_origin": "erpai_test_no_such_field"}),
			("origin_board_value empty", {"origin_board_value": ""}),
		):
			with self.subTest(case=case):
				self._settings(**{"field_origin": ORIGIN_FIELD, "origin_board_value": BOARD_VALUE, **fields})
				ls = self._ls()
				self.assertFalse(lifecycle.origin_configured(ls))
				for ticket in (all_bad, category_f):
					self.assertEqual(lifecycle.status_change_refusal(ticket, ls), "origin_not_configured")

		self._settings(field_origin=ORIGIN_FIELD, origin_board_value=BOARD_VALUE)
		ls = self._ls()
		self.assertTrue(lifecycle.origin_configured(ls))
		for case, ticket, expected in (
			("opted out, board, E", all_bad, "not_sendable"),
			("board (other case, blanks), E", board_e, "board_directed"),
			("E", category_e, "category_e"),
			("F", category_f, None),
			("not classified", unclassified, None),
		):
			with self.subTest(case=case):
				self.assertEqual(lifecycle.status_change_refusal(ticket, ls), expected)

	def test_constants(self):
		self.assertEqual(lifecycle.TOOL_RESOLVE_ON_TASKS_DONE, "resolve_on_tasks_done")
		self.assertEqual(lifecycle.TOOL_CLOSE_SILENT_F, "close_silent_f")
		self.assertEqual(lifecycle.TOOL_LIFECYCLE_COMMENT, "lifecycle_comment")
		self.assertEqual(lifecycle.TOOL_REQUESTER_NOTICE, "requester_notice")
		self.assertEqual(lifecycle.TOOL_LIFECYCLE_CONFIG, "ticket_lifecycle")
		self.assertEqual(
			lifecycle.REASON_ORIGIN_NOT_CONFIGURED,
			"chưa cấu hình trường Nguồn phát sinh (field_origin, origin_board_value)",
		)
		self.assertEqual(lifecycle.TITLE_LIFECYCLE_FAILED, "ERP AI lifecycle failed")


class TestRequesterMessages(LifecycleTestCase):
	def test_sender_match_ignores_display_name_and_case(self):
		"""A-U6b-9: senders compare by their email address only, after casefold."""
		requester = "nguyen.a@example.com"
		for sender, expected in (
			("nguyen.a@example.com", True),
			("Nguyễn Văn A <Nguyen.A@Example.COM>", True),
			("NGUYEN.A@EXAMPLE.COM", True),
			("nguyen.b@example.com", False),
			("Nguyen A <nguyen.a@example.org>", False),
			("", False),
			(None, False),
		):
			with self.subTest(sender=sender):
				self.assertIs(lifecycle.is_requester_sender(sender, requester), expected)
		self.assertTrue(lifecycle.is_requester_sender(requester, "Người tạo <Nguyen.A@example.com>"))
		self.assertFalse(lifecycle.is_requester_sender("", ""))
		self.assertFalse(lifecycle.is_requester_sender(None, None))

	def test_newer_message_detected_by_creation_then_name(self):
		"""U6b-fixes :64: another Received message of the requester with a larger (creation, name)."""
		ticket = self._ticket()
		base = f"ERPAI-TEST-{frappe.generate_hash(length=8)}"
		given = self._requester_message(ticket, DAY0, name=f"{base}-b")
		self.assertFalse(lifecycle.newer_requester_message_exists(ticket, given))

		self._message(ticket, "Received", DAY0 + timedelta(hours=1), sender="other@example.com")
		self._bot_message(ticket, DAY0 + timedelta(hours=1))
		self._requester_message(ticket, DAY0, name=f"{base}-a")  # same creation, smaller name: not newer
		self.assertFalse(lifecycle.newer_requester_message_exists(ticket, given))

		self._requester_message(ticket, DAY0, name=f"{base}-c")  # same creation, larger name: newer
		self.assertTrue(lifecycle.newer_requester_message_exists(ticket, given))

		later = self._ticket()
		first = self._requester_message(later, DAY0, name=f"{base}-z")
		self._requester_message(later, DAY0 + timedelta(seconds=1), name=f"{base}-y")  # later creation wins
		self.assertTrue(lifecycle.newer_requester_message_exists(later, first))

	def test_silent_since_stops_on_requester_reply_and_restarts_on_next_bot_message(self):
		"""AC-41 last sentence, AC-44: the clock runs from the bot's last message until the requester replies."""
		ticket = self._ticket()
		requester = self._requester(ticket)
		self.assertIsNone(lifecycle.silent_since(ticket))
		self._requester_message(ticket, DAY0)  # the opening email: no bot message yet
		self.assertIsNone(lifecycle.silent_since(ticket))

		first_bot = DAY0 + timedelta(hours=1)
		self._bot_message(ticket, first_bot)
		self.assertEqual(lifecycle.silent_since(ticket), first_bot)
		self._message(ticket, "Sent", DAY0 + timedelta(hours=2), sender="Administrator")  # a person's reply
		self._message(ticket, "Received", DAY0 + timedelta(hours=3), sender="other@example.com")
		self._bot_message(self._ticket(), DAY0 + timedelta(hours=4))  # another ticket's bot message
		self.assertEqual(lifecycle.silent_since(ticket), first_bot)

		self._message(ticket, "Received", DAY0 + timedelta(days=1), sender=f"Người tạo <{requester.upper()}>")
		self.assertIsNone(lifecycle.silent_since(ticket))

		next_bot = DAY0 + timedelta(days=2)
		self._bot_message(ticket, next_bot)
		self.assertEqual(lifecycle.silent_since(ticket), next_bot)

	def test_send_goes_only_to_raised_by(self):
		"""AC-40, ADR-034 QĐ 7: one Communication Sent by the agent to raised_by, one queued email, no comment."""
		self._email_settings()
		ticket = self._ticket()
		requester = self._requester(ticket)
		self._bot_message(ticket, DAY0)  # an older bot message: the name returned is the new one
		self.assertTrue(authority.enter_agent_session())

		name = lifecycle.send_to_requester(ticket, "<p>ERPAI-TEST trả lời người tạo</p>")

		communication = frappe.get_doc("Communication", name)
		self.assertEqual(communication.recipients, requester)
		self.assertEqual(communication.sent_or_received, "Sent")
		self.assertEqual(communication.owner, AGENT_USER)
		self.assertEqual(
			(communication.reference_doctype, communication.reference_name), ("HD Ticket", ticket)
		)
		self.assertIn("ERPAI-TEST trả lời người tạo", communication.content)
		queues = frappe.get_all("Email Queue", filters={"communication": name}, fields=["name", "status"])
		self.assertEqual(len(queues), 1)
		self.assertEqual(queues[0].status, "Not Sent")
		self.assertEqual(
			frappe.get_all("Email Queue Recipient", filters={"parent": queues[0].name}, pluck="recipient"),
			[requester],
		)
		self.assertEqual(
			frappe.db.count(
				"Comment",
				{"reference_doctype": "HD Ticket", "reference_name": ticket, "comment_type": "Comment"},
			),
			0,
		)


class TestArchitecture(FrappeTestCase):
	def test_no_model_gateway_import(self):
		"""ADR-033 QĐ 3, Ràng buộc: the lifecycle jobs never reach the model gateway."""
		self.assertEqual(_forbidden_imports(inspect.getsource(lifecycle), GATEWAY_MODULES), [])
		for sample in (
			"import erp_ai.gateway\n",
			"from erp_ai.gateway import call_model\n",
			"from erp_ai import gateway\n",
			"from .. import gateway\n",
		):
			with self.subTest(sample=sample):
				self.assertIn("erp_ai.gateway", _forbidden_imports(sample, GATEWAY_MODULES))

	def test_lifecycle_imports_no_tools_or_runner(self):
		"""U6b-fixes Sửa 13: tools/reply.py, handlers and runner import lifecycle, never the other way."""
		self.assertEqual(_forbidden_imports(inspect.getsource(lifecycle), TOOLS_OR_RUNNER_MODULES), [])
		for sample, caught in (
			("from erp_ai.agent import runner\n", "erp_ai.agent.runner"),
			("from erp_ai.agent.tools import registry\n", "erp_ai.agent.tools"),
			("import erp_ai.agent.tools.write_ticket\n", "erp_ai.agent.tools.write_ticket"),
			("from .tools.reply import reply_to_requester\n", "erp_ai.agent.tools.reply"),
			('frappe.get_attr("erp_ai.agent.runner.run_for_ticket")\n', "erp_ai.agent.runner.run_for_ticket"),
		):
			with self.subTest(sample=sample):
				self.assertIn(caught, _forbidden_imports(sample, TOOLS_OR_RUNNER_MODULES))
