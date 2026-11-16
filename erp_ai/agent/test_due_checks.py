import json
from datetime import datetime, timedelta
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.agent import due_checks, run_log
from erp_ai.constants import LOG_DOCTYPE, LOGGER_NAME
from erp_ai.test_utils import keep_agent_settings

NOW = datetime(2026, 11, 18, 10, 0)


def _fake_ticket() -> str:
	"""A ticket name no real ticket has: `sent_keys` only matches it against the `ticket` column of ERP AI Log."""
	return f"ERPAI-TEST-due-{frappe.generate_hash(length=10)}"


def _log_row(ticket: str, actions, *, entry_type: str = "bot_action", trigger: str = "scheduled_job") -> None:
	"""An ERP AI Log row inserted straight into the database; `actions` is stored as given (a list as JSON)."""
	frappe.get_doc(
		{
			"doctype": LOG_DOCTYPE,
			"run_id": "ERPAI-TEST-due",
			"entry_type": entry_type,
			"trigger": trigger,
			"ticket": ticket,
			"cost_usd": 0,
			"actions": actions if isinstance(actions, str) else json.dumps(actions),
		}
	).db_insert()


def _due_entry(kind: str, deadline: str, ok: bool = True, tool: str = "due_reminder") -> dict:
	return run_log.action_entry(
		tool,
		"Comment",
		"ERPAI-TEST-comment",
		ok,
		reason=None if ok else "lỗi",
		value_after={"kind": kind, "deadline": deadline, "assignees": []},
	)


def _milestone_entry(kind: str, ok: bool = True) -> dict:
	return run_log.action_entry(
		"milestone_reminder",
		"Comment",
		"ERPAI-TEST-comment",
		ok,
		reason=None if ok else "lỗi",
		value_after={"kind": kind, "assignees": []},
	)


class TestNames(FrappeTestCase):
	def setUp(self):
		keep_agent_settings(self)

	def test_constants_match_design(self):
		# U5b.md:122-137, verbatim
		self.assertEqual(due_checks.DUE_REMINDER_TOOL, "due_reminder")
		self.assertEqual(due_checks.MILESTONE_REMINDER_TOOL, "milestone_reminder")
		self.assertEqual((due_checks.KIND_DUE_SOON, due_checks.KIND_OVERDUE), ("due_soon", "overdue"))
		self.assertEqual(
			(due_checks.KIND_BA_NOTE_MISSING, due_checks.KIND_TASK_MISSING),
			("ba_note_missing", "task_missing"),
		)
		self.assertEqual(due_checks.CANDIDATE_LIMIT, 200)
		self.assertEqual(due_checks.LOCK_NAME, "erp_ai_due_checks")
		self.assertEqual(
			due_checks.DUE_SOON_TEXT,
			"Nhắc hạn: phiếu còn dưới {hours} giờ tới hạn {deadline}. Người phụ trách: {people}.",
		)
		self.assertEqual(
			due_checks.OVERDUE_TEXT, "Nhắc hạn: phiếu đã quá hạn {deadline}. Người phụ trách: {people}."
		)
		self.assertEqual(
			due_checks.BA_NOTE_TEXT,
			"Nhắc mốc: phiếu đầu mục C đã quá {hours} giờ mà chưa có BA note. Người phụ trách: {people}.",
		)
		self.assertEqual(
			due_checks.TASK_TEXT,
			"Nhắc mốc: phiếu đã quá {days} ngày mà chưa có Task liên kết. Người phụ trách: {people}.",
		)
		self.assertEqual(due_checks.NO_ASSIGNEE_TEXT, "chưa có người phụ trách")
		self.assertEqual(
			due_checks.CODE_SUBJECT,
			{
				"due_soon": "Phiếu #{name}: còn dưới {hours} giờ tới hạn {deadline}",
				"overdue": "Phiếu #{name}: đã quá hạn {deadline}",
				"task_missing": "Phiếu #{name}: quá {days} ngày chưa có Task liên kết",
			},
		)


class TestDueReminder(FrappeTestCase):
	def setUp(self):
		keep_agent_settings(self)

	def test_boundary_exactly_24h(self):
		cases = (
			# deadline - now = 24:00 counts as due soon; 24:01 is not yet
			(NOW + timedelta(hours=24), 24, "due_soon"),
			(NOW + timedelta(hours=24, minutes=1), 24, None),
			(NOW + timedelta(seconds=1), 24, "due_soon"),
			# deadline - now = 0 is overdue, and so is any deadline before now
			(NOW, 24, "overdue"),
			(NOW - timedelta(days=3), 24, "overdue"),
			# the window is the hours given
			(NOW + timedelta(hours=2), 2, "due_soon"),
			(NOW + timedelta(hours=2, seconds=1), 2, None),
			# no deadline
			(None, 24, None),
		)
		for deadline, hours, expected in cases:
			with self.subTest(deadline=deadline, hours=hours):
				self.assertEqual(due_checks.due_kind(deadline, NOW, hours), expected)


class TestMilestones(FrappeTestCase):
	def setUp(self):
		keep_agent_settings(self)

	def test_milestone_due_boundary(self):
		cases = (
			(NOW - timedelta(hours=23, minutes=59), 24, False),
			(NOW - timedelta(hours=24), 24, True),
			(NOW - timedelta(days=5), 24, True),
			(NOW - timedelta(hours=71, minutes=59, seconds=59), 72, False),
			(NOW - timedelta(hours=72), 72.0, True),
			(NOW - timedelta(minutes=30), 0.5, True),
			(NOW, 24, False),
		)
		for created, hours, expected in cases:
			with self.subTest(created=created, hours=hours):
				self.assertIs(due_checks.milestone_due(created, NOW, hours), expected)


class TestSentKeys(FrappeTestCase):
	def setUp(self):
		keep_agent_settings(self)
		self.addCleanup(frappe.db.rollback)

	def test_reads_ok_entries_and_skips_bad_json(self):
		first, second, third, outside = (_fake_ticket() for _ in range(4))
		_log_row(
			first,
			[
				_due_entry("due_soon", "2026-11-20 23:59:59"),
				_milestone_entry("ba_note_missing"),
				# a failed entry is no key; another tool is no key
				_due_entry("overdue", "2026-11-20 23:59:59", ok=False),
				_milestone_entry("task_missing", ok=False),
				_due_entry("due_soon", "2026-11-25 08:00:00", tool="lifecycle_comment"),
			],
		)
		# unreadable actions: that row is skipped with one warning, the ticket's other rows still count
		_log_row(second, "not json")
		_log_row(second, [_due_entry("overdue", "2026-11-19 08:00:00")])
		# a row of another trigger or entry type is no key
		_log_row(third, [_milestone_entry("task_missing")], trigger="setting_save")
		_log_row(
			third,
			[_due_entry("due_soon", "2026-11-21 09:00:00")],
			entry_type="reason",
			trigger="ticket_insert",
		)
		# a ticket outside the asked names is never read
		_log_row(outside, [_due_entry("due_soon", "2026-11-21 09:00:00")])

		with patch("frappe.logger") as get_logger:
			keys = due_checks.sent_keys([first, second, third])

		self.assertEqual(
			keys,
			{
				(first, "due_soon", "2026-11-20 23:59:59"),
				(first, "ba_note_missing", ""),
				(second, "overdue", "2026-11-19 08:00:00"),
			},
		)
		get_logger.assert_called_with(LOGGER_NAME)
		self.assertEqual(len(get_logger.return_value.warning.call_args_list), 1)
		self.assertEqual(due_checks.sent_keys([]), set())
