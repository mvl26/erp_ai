"""CHG-017: the Duyệt / Không duyệt buttons under the bot's finished work."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import create_agent, make_ticket

from erp_ai import ticket_panel
from erp_ai.agent import lifecycle, messages, prompts, run_log
from erp_ai.constants import (
	AGENT_USER,
	LOG_DOCTYPE,
	MESSAGE_DOCTYPE,
	ROLE_INSTRUCTOR,
	SETTING_DOCTYPE,
	TRIGGER_COMMENT_MENTION,
)
from erp_ai.test_utils import (
	keep_agent_settings,
	post_bot_guidance,
	set_agent_settings,
	set_result_confirm_ready,
	stub_job_states,
)

INSTRUCTOR = "result.instructor@example.com"
PLAIN_AGENT = "result.plain@example.com"
CREATOR = "result.creator@example.com"


def _say(ticket, text, user):
	frappe.set_user(user)
	try:
		return messages.add_message(ticket, text, trusted=True)
	finally:
		frappe.set_user("Administrator")


class ResultCase(FrappeTestCase):
	def setUp(self):
		for user in (INSTRUCTOR, PLAIN_AGENT, CREATOR, AGENT_USER):
			self.addCleanup(frappe.clear_cache, user=user)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		keep_agent_settings(self)
		stub_job_states(self, {})
		set_result_confirm_ready()
		if not frappe.db.exists("Role", ROLE_INSTRUCTOR):
			frappe.get_doc({"doctype": "Role", "role_name": ROLE_INSTRUCTOR}).insert(ignore_permissions=True)
		for email in (INSTRUCTOR, PLAIN_AGENT, CREATOR):
			create_agent(email)
		frappe.get_doc("User", INSTRUCTOR).add_roles(ROLE_INSTRUCTOR)
		self.ticket = make_ticket(subject="ERPAI-TEST result", raised_by="result.requester@example.com").name
		frappe.db.set_value("HD Ticket", self.ticket, "owner", CREATOR, update_modified=False)
		enqueue = patch("erp_ai.handlers.enqueue_agent_run")
		self.enqueue = enqueue.start()
		self.addCleanup(enqueue.stop)

	def _flags(self):
		return [m["result_confirmable"] for m in messages.thread(self.ticket)]

	def _decide(self, action, user=INSTRUCTOR):
		frappe.set_user(user)
		try:
			return ticket_panel.decide_result(self.ticket, action)
		finally:
			frappe.set_user("Administrator")

	def _status(self):
		return frappe.db.get_value("HD Ticket", self.ticket, "status")


class TestResultButtonsShown(ResultCase):
	def test_shown_under_a_guidance_with_done_work_and_nothing_pending(self):
		post_bot_guidance(self.ticket)

		self.assertEqual(self._flags(), [True])

	def test_not_shown_when_a_step_is_pending_or_offered_or_nothing_was_done(self):
		for kwargs in ({"pending": ["Đề xuất CP-1"]}, {"offer": True}, {"done": ()}):
			with self.subTest(kwargs=kwargs):
				frappe.db.delete(MESSAGE_DOCTYPE, {"ticket": self.ticket})
				post_bot_guidance(self.ticket, **({"done": ["Đã sửa A"]} | kwargs))
				self.assertNotIn(True, self._flags())

	def test_not_shown_once_the_ticket_is_resolved_or_closed(self):
		post_bot_guidance(self.ticket)
		for status in (lifecycle.STATUS_RESOLVED, lifecycle.STATUS_CLOSED):
			with self.subTest(status=status):
				frappe.db.set_value("HD Ticket", self.ticket, "status", status, update_modified=False)
				self.assertEqual(self._flags(), [False])

	def test_not_shown_where_the_bot_must_not_change_the_status(self):
		post_bot_guidance(self.ticket)
		frappe.db.set_value("HD Ticket", self.ticket, "ai_score_reason", "Chỉ đạo BGĐ", update_modified=False)

		self.assertEqual(self._flags(), [False])

	def test_shown_when_the_origin_field_is_not_configured_but_not_on_a_category_e_ticket(self):
		post_bot_guidance(self.ticket)
		set_agent_settings(field_origin="", origin_board_value="")
		frappe.db.value_cache.pop(SETTING_DOCTYPE, None)
		self.assertEqual(self._flags(), [True])

		with patch("erp_ai.agent.policy.latest_classification", return_value=("E", 0)):
			self.assertEqual(self._flags(), [False])

	def test_hidden_while_the_bot_is_to_answer_and_after_a_reject_until_the_person_answers(self):
		post_bot_guidance(self.ticket)
		_say(self.ticket, "Thêm việc B", INSTRUCTOR)
		self.assertEqual(self._flags(), [False, False])
		_say(self.ticket, "Đã làm B", AGENT_USER)
		self.assertEqual(self._flags(), [True, False, False])
		_say(self.ticket, prompts.RESULT_REJECTED_TEXT, INSTRUCTOR)
		_say(self.ticket, "Kết quả chưa đạt ở điểm nào?", AGENT_USER)
		self.assertNotIn(True, self._flags())
		_say(self.ticket, "Thiếu mục C", INSTRUCTOR)
		_say(self.ticket, "Đã làm C", AGENT_USER)
		self.assertTrue(self._flags()[0])


class TestApproveResult(ResultCase):
	def test_instructor_approve_resolves_the_ticket_and_closes_the_conversation_quietly(self):
		post_bot_guidance(self.ticket)

		result = self._decide("approve")

		self.assertEqual(result["status"], lifecycle.STATUS_RESOLVED)
		self.assertEqual(self._status(), lifecycle.STATUS_RESOLVED)
		last = messages.thread(self.ticket)[-1]
		self.assertEqual((last["text"], last["is_bot"]), (prompts.RESULT_APPROVED_TEXT, False))
		self.enqueue.assert_not_called()
		row = frappe.get_all(
			LOG_DOCTYPE,
			filters={"ticket": self.ticket, "entry_type": run_log.ENTRY_TYPE_BOT_ACTION},
			fields=["instructor", "actions"],
		)[0]
		self.assertEqual(row.instructor, INSTRUCTOR)
		self.assertIn(lifecycle.TOOL_RESOLVE_ON_RESULT_APPROVED, row.actions)
		self.assertNotIn(True, self._flags())

	def test_the_creator_may_approve_without_the_instructor_role(self):
		post_bot_guidance(self.ticket)

		self._decide("approve", user=CREATOR)

		self.assertEqual(self._status(), lifecycle.STATUS_RESOLVED)

	def test_nobody_else_may_decide_and_nothing_is_written(self):
		post_bot_guidance(self.ticket)
		before = self._status()
		for user in (PLAIN_AGENT, AGENT_USER, "Guest"):
			for action in ("approve", "reject"):
				with self.subTest(user=user, action=action), self.assertRaises(frappe.PermissionError):
					self._decide(action, user=user)
		self.assertEqual(self._status(), before)
		self.assertEqual(len(messages.thread(self.ticket)), 1)

	def test_refused_without_finished_work_or_with_an_unknown_action(self):
		with self.assertRaises(frappe.ValidationError):
			self._decide("approve")
		post_bot_guidance(self.ticket, done=(), pending=["Đề xuất CP-1"])
		with self.assertRaises(frappe.ValidationError):
			self._decide("approve")
		with self.assertRaises(frappe.ValidationError):
			self._decide("resolve")
		self.assertNotEqual(self._status(), lifecycle.STATUS_RESOLVED)


class TestRejectResult(ResultCase):
	def test_reject_sends_the_fixed_message_and_calls_the_bot_without_changing_the_status(self):
		post_bot_guidance(self.ticket)
		before = self._status()

		result = self._decide("reject")

		self.assertEqual(self._status(), before)
		row = frappe.db.get_value(MESSAGE_DOCTYPE, result["message"], ["owner", "content"], as_dict=True)
		self.assertEqual((row.owner, row.content), (INSTRUCTOR, prompts.RESULT_REJECTED_TEXT))
		self.enqueue.assert_called_once()
		self.assertEqual(self.enqueue.call_args.args[:2], (self.ticket, TRIGGER_COMMENT_MENTION))

	def test_the_reject_message_gets_the_ask_one_question_task(self):
		def task(content):
			conversation = [{"author": "A", "role": "chỉ thị", "content": content}]
			return prompts.build_initial_message(
				{"subject": "s"}, [], TRIGGER_COMMENT_MENTION, None, conversation=conversation
			)

		rejected, other = task(prompts.RESULT_REJECTED_TEXT), task("Thêm việc B")

		self.assertIn(prompts.TASK_RESULT_REJECTED, rejected)
		self.assertNotIn(prompts.TASK_COMMENT, rejected)
		self.assertIn(prompts.TASK_COMMENT, other)
		self.assertNotIn(prompts.TASK_RESULT_REJECTED, other)


class TestResultLinks(ResultCase):
	def _log(self, *entries):
		run_log.write_bot_action(
			trigger=run_log.TRIGGER_SCHEDULED_JOB,
			ticket=self.ticket,
			actions=[run_log.action_entry(tool, doctype, name, ok) for tool, doctype, name, ok in entries],
		)

	def test_links_to_what_the_bot_wrote_above_the_buttons_and_nothing_else(self):
		post_bot_guidance(self.ticket)
		self._log(
			("api_update_record", "Role", ROLE_INSTRUCTOR, True),
			("api_update_record", "Role", "No such role", True),
			("api_delete_record", "Role", "Desk User", True),
			("api_update_record", "Role", "Guest", False),
			("api_update_record", "HD Ticket", self.ticket, True),
		)

		(guidance,) = messages.thread(self.ticket)

		self.assertTrue(guidance["result_confirmable"])
		self.assertEqual(
			guidance["result_links"],
			[{"label": f"Role {ROLE_INSTRUCTOR}", "url": "/app/role/ERP%20AI%20Instructor"}],
		)

	def test_a_record_the_reader_may_not_open_is_not_linked(self):
		post_bot_guidance(self.ticket)
		self._log(("api_update_record", "Role", ROLE_INSTRUCTOR, True))

		with patch("frappe.has_permission", side_effect=lambda doctype, *a, **k: doctype != "Role"):
			(guidance,) = messages.thread(self.ticket)

		self.assertEqual(guidance["result_links"], [])
