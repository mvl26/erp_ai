import ast
import inspect
import json
from datetime import datetime, timedelta
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.helpdesk.doctype.hd_ticket.hd_ticket import HDTicket
from helpdesk.test_utils import make_ticket

from erp_ai.agent import authority, lifecycle, policy
from erp_ai.constants import AGENT_USER, LOG_DOCTYPE, SETTING_DOCTYPE, TRIGGER_TICKET_INSERT
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
# Helpdesk sends an agent reply as an email (Email Queue, delayed) only with these settings; a Sent message
# leaves the ticket status as it is.
EMAIL_REPLY_SETTINGS = {
	"enable_reply_email_via_agent": 1,
	"skip_email_workflow": 0,
	"instantly_send_email": 0,
	"auto_update_status": 0,
}
DAYS = 3


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
		# Error Log rows outlive the test transaction and ticket names are reused: count only the new ones.
		self.old_error_logs = frappe.get_all(
			"Error Log", filters={"method": lifecycle.TITLE_LIFECYCLE_FAILED}, pluck="name"
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

	def _task(self, ticket, status, linked=True) -> str:
		frappe.set_user("Administrator")
		values = {
			"doctype": "Task",
			"subject": f"ERPAI-TEST lifecycle task of {ticket}",
			"description": "ERPAI-TEST lifecycle",
			"status": status,
		}
		if linked:
			values["ai_ticket"] = ticket
		if status == "Completed":
			values.update(completed_by="Administrator", completed_on=DAY0.date())
		return frappe.get_doc(values).insert(ignore_permissions=True).name

	def _comments(self, ticket) -> list:
		return frappe.get_all(
			"Comment",
			filters={"reference_doctype": "HD Ticket", "reference_name": ticket, "comment_type": "Comment"},
			fields=["name", "owner", "content"],
		)

	def _rows(self, ticket) -> list:
		"""The ticket's bot_action rows of ERP AI Log, `actions` decoded."""
		rows = frappe.get_all(
			LOG_DOCTYPE,
			filters={"ticket": ticket, "entry_type": "bot_action"},
			fields=["name", "trigger", "run_id", "cost_usd", "actions"],
			order_by="creation",
		)
		return [frappe._dict(row, actions=json.loads(row.actions)) for row in rows]

	def _error_logs(self, ticket) -> int:
		"""TITLE_LIFECYCLE_FAILED Error Logs of `ticket` written since setUp."""
		filters = {"method": lifecycle.TITLE_LIFECYCLE_FAILED, "error": ("like", f"ticket={ticket} %")}
		if self.old_error_logs:
			filters["name"] = ("not in", self.old_error_logs)
		return frappe.db.count("Error Log", filters)

	def _status(self, ticket) -> str:
		return frappe.db.get_value("HD Ticket", ticket, "status")

	def _assert_unchanged(self, ticket, status="Open") -> None:
		self.assertEqual(self._status(ticket), status)
		self.assertEqual(self._comments(ticket), [])
		self.assertEqual(self._rows(ticket), [])

	def _fail_once(self, method_name: str, when=lambda doc: True):
		"""Patch HDTicket.<method_name> to raise once, on the first call where `when(doc)` holds; real otherwise."""
		real = getattr(HDTicket, method_name)
		failed = []

		def method(doc, *args, **kwargs):
			if not failed and when(doc):
				failed.append(doc.name)
				raise frappe.ValidationError("ERPAI-TEST injected failure")
			return real(doc, *args, **kwargs)

		return patch.object(HDTicket, method_name, method)


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


class TestResolveOnTasksDone(LifecycleTestCase):
	"""AC-43: the 7 cases of the spec plus A-11, under the agent account."""

	def setUp(self):
		super().setUp()
		self._settings(resolve_on_tasks_done_enabled=1)

	def _run(self, ticket) -> None:
		lifecycle.run_task_lifecycle(ticket)
		frappe.set_user("Administrator")

	def _assert_resolved_once(self, ticket, completed: int) -> None:
		values = frappe.db.get_value(
			"HD Ticket", ticket, ["status", "status_category", "modified_by"], as_dict=True
		)
		self.assertEqual(
			(values.status, values.status_category, values.modified_by), ("Resolved", "Resolved", AGENT_USER)
		)
		content = lifecycle.COMMENT_RESOLVED.format(completed=completed)
		comments = self._comments(ticket)
		self.assertEqual([(c.owner, c.content) for c in comments], [(AGENT_USER, content)])
		rows = self._rows(ticket)
		self.assertEqual(len(rows), 1)
		self.assertEqual((rows[0].trigger, rows[0].cost_usd), ("scheduled_job", 0))
		self.assertEqual(
			rows[0].actions,
			[
				{
					"tool": "resolve_on_tasks_done",
					"doctype": "HD Ticket",
					"name": ticket,
					"ok": True,
					"value_before": {"status": "Open"},
					"value_after": {"status": "Resolved"},
					"instructor": None,
				},
				{
					"tool": "lifecycle_comment",
					"doctype": "Comment",
					"name": comments[0].name,
					"ok": True,
					"value_before": None,
					"value_after": {"content": content},
					"instructor": None,
				},
			],
		)

	def test_two_of_two_completed_resolved(self):
		ticket = self._ticket(category="C")
		self._task(ticket, "Completed")
		self._task(ticket, "Completed")
		self.assertEqual(lifecycle.tasks_done(ticket), (True, 2))

		self._run(ticket)

		self._assert_resolved_once(ticket, completed=2)

	def test_one_of_two_not_changed(self):
		ticket = self._ticket(category="C")
		self._task(ticket, "Completed")
		self._task(ticket, "Working")
		self.assertEqual(lifecycle.tasks_done(ticket), (False, 1))

		self._run(ticket)

		self._assert_unchanged(ticket)

	def test_no_task_not_changed(self):
		ticket = self._ticket(category="C")
		self.assertEqual(lifecycle.tasks_done(ticket), (False, 0))

		self._run(ticket)

		self._assert_unchanged(ticket)

	def test_cancelled_plus_completed_resolved(self):
		ticket = self._ticket(category="C")
		self._task(ticket, "Cancelled")
		self._task(ticket, "Completed")
		self.assertEqual(lifecycle.tasks_done(ticket), (True, 1))

		self._run(ticket)

		self._assert_resolved_once(ticket, completed=1)

	def test_all_cancelled_not_changed(self):
		ticket = self._ticket(category="C")
		self._task(ticket, "Cancelled")
		self._task(ticket, "Cancelled")
		self.assertEqual(lifecycle.tasks_done(ticket), (False, 0))

		self._run(ticket)

		self._assert_unchanged(ticket)

	def test_closed_ticket_not_changed(self):
		ticket = self._ticket(category="C")
		frappe.db.set_value(
			"HD Ticket", ticket, {"status": "Closed", "status_category": "Resolved"}, update_modified=False
		)
		self._task(ticket, "Completed")
		self._task(ticket, "Completed")

		self._run(ticket)

		self._assert_unchanged(ticket, status="Closed")

	def test_repeated_event_changes_once(self):
		ticket = self._ticket(category="C")
		self._task(ticket, "Completed")

		for _ in range(3):
			self._run(ticket)

		self._assert_resolved_once(ticket, completed=1)

	def test_task_without_ticket_link_not_counted(self):
		"""A-11: a Task with no ai_ticket never counts, whether open or done."""
		resolved = self._ticket(category="C")
		self._task(resolved, "Completed")
		self._task(resolved, "Open", linked=False)
		unlinked_only = self._ticket(category="C")
		self._task(unlinked_only, "Completed", linked=False)
		self.assertEqual(lifecycle.tasks_done(resolved), (True, 1))
		self.assertEqual(lifecycle.tasks_done(unlinked_only), (False, 0))

		self._run(resolved)
		self._run(unlinked_only)

		self._assert_resolved_once(resolved, completed=1)
		self._assert_unchanged(unlinked_only)

	def test_failure_midway_rolls_back_then_once(self):
		"""ADR-033 Ràng buộc, U6b-fixes Sửa 2: a failure after the status save undoes it; the next run does it once."""
		ticket = self._ticket(category="C")
		self._task(ticket, "Completed")

		with self._fail_once("new_comment"):
			self._run(ticket)
			self._assert_unchanged(ticket)
			self.assertEqual(self._error_logs(ticket), 1)
			self._run(ticket)

		self._assert_resolved_once(ticket, completed=1)
		self.assertEqual(self._error_logs(ticket), 1)


class TestSilentClose(LifecycleTestCase):
	"""AC-44, AC-41 (clock reset), ADR-033 QĐ 6: a silent F ticket is closed, with one notice, exactly once."""

	def setUp(self):
		super().setUp()
		self._settings(close_silent_f_enabled=1, close_silent_f_days=DAYS)
		self._email_settings()

	def _silent_f(self, category="F", **values) -> str:
		"""A ticket of `category` whose only message is the bot's, at DAY0."""
		ticket = self._ticket(category=category, **values)
		self._bot_message(ticket, DAY0)
		return ticket

	def _scan(self, now) -> None:
		lifecycle.scan_silent_f_tickets(now)
		frappe.set_user("Administrator")

	def _bot_messages(self, ticket) -> list:
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

	def _counts(self, ticket) -> dict:
		sent = self._bot_messages(ticket)
		return {
			"bot messages": len(sent),
			"emails": frappe.db.count("Email Queue", {"communication": ("in", sent)}) if sent else 0,
			"comments": len(self._comments(ticket)),
			"rows": len(self._rows(ticket)),
			"status": self._status(ticket),
		}

	def _closed(self) -> dict:
		"""The counts of a ticket of `_silent_f` once closed: its old message plus one notice and its email."""
		return {"bot messages": 2, "emails": 1, "comments": 1, "rows": 1, "status": "Closed"}

	def _untouched(self, status="Open", bot_messages=1) -> dict:
		return {"bot messages": bot_messages, "emails": 0, "comments": 0, "rows": 0, "status": status}

	def test_2d23h_not_closed(self):
		ticket = self._silent_f()

		self._scan(DAY0 + timedelta(hours=DAYS * 24 - 1))

		self.assertEqual(self._counts(ticket), self._untouched())

	def test_3d_closed_with_comment_and_notice(self):
		ticket = self._silent_f()
		requester = self._requester(ticket)
		old_message = self._bot_messages(ticket)

		self._scan(DAY0 + timedelta(hours=DAYS * 24))

		self.assertEqual(self._counts(ticket), self._closed())
		values = frappe.db.get_value("HD Ticket", ticket, ["status_category", "modified_by"], as_dict=True)
		self.assertEqual((values.status_category, values.modified_by), ("Resolved", AGENT_USER))
		(notice_name,) = set(self._bot_messages(ticket)) - set(old_message)
		notice = frappe.get_doc("Communication", notice_name)
		notice_text = lifecycle.NOTICE_SILENT_CLOSE.format(ticket=ticket, days=DAYS)
		self.assertEqual((notice.recipients, notice.owner), (requester, AGENT_USER))
		self.assertIn(notice_text, notice.content)
		content = lifecycle.COMMENT_SILENT_CLOSED.format(days=DAYS)
		(comment,) = self._comments(ticket)
		self.assertEqual((comment.owner, comment.content), (AGENT_USER, content))
		(row,) = self._rows(ticket)
		self.assertEqual((row.trigger, row.cost_usd), ("scheduled_job", 0))
		self.assertEqual(
			row.actions,
			[
				{
					"tool": "requester_notice",
					"doctype": "Communication",
					"name": notice_name,
					"ok": True,
					"value_before": None,
					"value_after": {"content": notice_text},
					"instructor": None,
				},
				{
					"tool": "close_silent_f",
					"doctype": "HD Ticket",
					"name": ticket,
					"ok": True,
					"value_before": {"status": "Open"},
					"value_after": {"status": "Closed"},
					"instructor": None,
				},
				{
					"tool": "lifecycle_comment",
					"doctype": "Comment",
					"name": comment.name,
					"ok": True,
					"value_before": None,
					"value_after": {"content": content},
					"instructor": None,
				},
			],
		)

	def test_reply_on_day2_not_closed(self):
		ticket = self._silent_f()
		self._requester_message(ticket, DAY0 + timedelta(days=2))

		self._scan(DAY0 + timedelta(days=DAYS, hours=1))

		self.assertEqual(self._counts(ticket), self._untouched())

	def test_board_f_not_closed(self):
		ticket = self._silent_f(origin=BOARD_VALUE)

		self._scan(DAY0 + timedelta(days=DAYS, hours=1))

		self.assertEqual(self._counts(ticket), self._untouched())

	def test_category_e_not_closed(self):
		ticket = self._silent_f(category="E")

		self._scan(DAY0 + timedelta(days=DAYS, hours=1))

		self.assertEqual(self._counts(ticket), self._untouched())

	def test_category_c_not_closed(self):
		ticket = self._silent_f(category="C")

		self._scan(DAY0 + timedelta(days=DAYS, hours=1))

		self.assertEqual(self._counts(ticket), self._untouched())

	def test_f_never_replied_not_closed(self):
		"""The clock starts only at a bot message: the requester's own opening email never starts it."""
		ticket = self._ticket(category="F")
		self._requester_message(ticket, DAY0)

		self._scan(DAY0 + timedelta(days=DAYS * 3))

		self.assertEqual(self._counts(ticket), self._untouched(bot_messages=0))

	def test_notice_failure_not_closed(self):
		"""A-U6b-7: no notice, no close; one requester_notice entry ok=False; the next scan tries again."""
		ticket = self._silent_f()
		now = DAY0 + timedelta(days=DAYS, hours=1)

		with patch.object(
			HDTicket, "reply_via_agent", side_effect=frappe.OutgoingEmailError("ERPAI-TEST no account")
		):
			self._scan(now)

		self.assertEqual(self._counts(ticket), {**self._untouched(), "rows": 1})
		(row,) = self._rows(ticket)
		(entry,) = row.actions
		self.assertEqual(
			(entry["tool"], entry["doctype"], entry["name"], entry["ok"]),
			("requester_notice", "Communication", None, False),
		)
		self.assertIn("OutgoingEmailError", entry["reason"])
		self.assertEqual(self._error_logs(ticket), 0)

		self._scan(now)

		self.assertEqual(self._counts(ticket), {**self._closed(), "rows": 2})

	def test_requester_reply_resets_clock(self):
		"""Design 8: bot day 0, requester day 2, scan day 4: open; bot again day 4, scan day 7: closed."""
		ticket = self._silent_f()
		self._requester_message(ticket, DAY0 + timedelta(days=2))

		self._scan(DAY0 + timedelta(days=4))
		self.assertEqual(self._counts(ticket), self._untouched())

		self._bot_message(ticket, DAY0 + timedelta(days=4))
		self._scan(DAY0 + timedelta(days=7))
		self.assertEqual(self._counts(ticket), {**self._closed(), "bot messages": 3})

	def test_two_runs_same_now_one_close(self):
		"""ADR-033 Ràng buộc (X-3): two scans at the same simulated time: 0 email, comment or row more."""
		ticket = self._silent_f()
		now = DAY0 + timedelta(days=DAYS, hours=1)

		self._scan(now)
		self.assertEqual(self._counts(ticket), self._closed())
		self._scan(now)
		self.assertEqual(self._counts(ticket), self._closed())

	def test_failure_after_notice_rolls_back_then_once(self):
		"""ADR-033 Ràng buộc (X-3): a failure at the Closed save undoes the notice too; the next scan does it once.

		It also shows Helpdesk's reply_via_agent does not commit: the savepoint rollback undoes its Communication.
		"""
		ticket = self._silent_f()
		now = DAY0 + timedelta(days=DAYS, hours=1)

		with self._fail_once("save", when=lambda doc: doc.status == "Closed"):
			self._scan(now)

		self.assertEqual(self._counts(ticket), self._untouched())
		self.assertEqual(self._error_logs(ticket), 1)

		self._scan(now)

		self.assertEqual(self._counts(ticket), self._closed())
		self.assertEqual(self._error_logs(ticket), 1)

	def test_failure_on_one_ticket_others_closed(self):
		tickets = [self._silent_f(), self._silent_f()]

		with self._fail_once("save", when=lambda doc: doc.status == "Closed" and doc.name in tickets):
			self._scan(DAY0 + timedelta(days=DAYS, hours=1))

		counts = {ticket: self._counts(ticket) for ticket in tickets}
		failed = [ticket for ticket in tickets if self._error_logs(ticket)]
		self.assertEqual(len(failed), 1, counts)
		(closed,) = set(tickets) - set(failed)
		self.assertEqual(counts[failed[0]], self._untouched())
		self.assertEqual(counts[closed], self._closed())

	def test_resolved_tickets_not_candidates(self):
		"""U6b-fixes Sửa 15: the candidate query keeps only tickets not in the Resolved category."""
		closed = self._silent_f()
		frappe.db.set_value(
			"HD Ticket", closed, {"status": "Closed", "status_category": "Resolved"}, update_modified=False
		)
		open_ticket = self._silent_f()
		now = DAY0 + timedelta(days=DAYS, hours=1)
		mine = {closed, open_ticket}

		candidates = lifecycle._silent_f_candidates(now - timedelta(days=DAYS))
		self.assertEqual([name for name in candidates if name in mine], [open_ticket])

		with patch.object(lifecycle, "send_to_requester", wraps=lifecycle.send_to_requester) as send:
			self._scan(now)

		self.assertEqual(
			[call.args[0] for call in send.call_args_list if call.args[0] in mine], [open_ticket]
		)
		self.assertEqual(self._counts(closed), self._untouched(status="Closed"))
		self.assertEqual(self._counts(open_ticket), self._closed())


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
