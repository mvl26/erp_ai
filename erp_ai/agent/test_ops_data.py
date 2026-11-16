from datetime import date, datetime
from unittest.mock import call, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.agent import ops_data
from erp_ai.constants import AGENT_USER, LOGGER_NAME
from erp_ai.test_utils import keep_agent_settings

TYPE_A = "Sự cố & lỗi hệ thống"
TYPE_D = "Chuẩn hóa dữ liệu & quy trình trên ERP"
HUMAN_AGENT = "erpai-test-ops-human@example.com"
# A real Datetime Custom Field erp_ai installs on HD Ticket, and a Date field of HD Ticket itself (Helpdesk core).
DATETIME_DUE_FIELD = "ai_updated_at"
DATE_DUE_FIELD = "opening_date"


def _fake_ticket() -> str:
	"""A ticket name no real ticket has: the helpers only match it against Comment and Task columns."""
	return f"ERPAI-TEST-ops-{frappe.generate_hash(length=10)}"


def _comment(ticket: str, owner: str, content: str) -> None:
	doc = frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Comment",
			"reference_doctype": "HD Ticket",
			"reference_name": ticket,
			"content": content,
		}
	)
	doc.db_insert()
	frappe.db.set_value("Comment", doc.name, "owner", owner, update_modified=False)


def _task(ticket: str) -> None:
	frappe.get_doc({"doctype": "Task", "subject": "ERPAI-TEST ops", "ai_ticket": ticket}).db_insert()


class TestCycles(FrappeTestCase):
	def setUp(self):
		keep_agent_settings(self)

	def test_daily_weekly_monthly_cycles(self):
		daily = (
			# the 08:00 cut-over, both sides
			(datetime(2026, 11, 17, 8, 0, 0), date(2026, 11, 17)),
			(datetime(2026, 11, 17, 7, 59, 59, 999999), date(2026, 11, 16)),
			# a run at 02:00 belongs to yesterday's cycle
			(datetime(2026, 11, 17, 2, 0, 0), date(2026, 11, 16)),
			(datetime(2026, 11, 17, 0, 0, 0), date(2026, 11, 16)),
			(datetime(2026, 11, 17, 23, 59, 59), date(2026, 11, 17)),
			# month and year change
			(datetime(2026, 12, 1, 2, 0, 0), date(2026, 11, 30)),
			(datetime(2027, 1, 1, 7, 59, 59, 999999), date(2026, 12, 31)),
			(datetime(2027, 1, 1, 8, 0, 0), date(2027, 1, 1)),
		)
		weekly = (
			# Monday 08:00 cut-over, both sides
			(datetime(2026, 11, 16, 8, 0, 0), date(2026, 11, 16)),
			(datetime(2026, 11, 16, 7, 59, 59, 999999), date(2026, 11, 9)),
			(datetime(2026, 11, 16, 2, 0, 0), date(2026, 11, 9)),
			# decoy: early morning on another weekday stays in the same week
			(datetime(2026, 11, 17, 2, 0, 0), date(2026, 11, 16)),
			(datetime(2026, 11, 14, 12, 0, 0), date(2026, 11, 9)),
			# Sunday is the last day of the Monday week
			(datetime(2026, 11, 22, 23, 59, 59), date(2026, 11, 16)),
			# year change
			(datetime(2027, 1, 1, 10, 0, 0), date(2026, 12, 28)),
			(datetime(2027, 1, 3, 23, 59, 59), date(2026, 12, 28)),
			(datetime(2027, 1, 4, 7, 59, 59, 999999), date(2026, 12, 28)),
			(datetime(2027, 1, 4, 8, 0, 0), date(2027, 1, 4)),
		)
		monthly = (
			# day 1 08:00 cut-over, both sides
			(datetime(2026, 12, 1, 8, 0, 0), "2026-12"),
			(datetime(2026, 12, 1, 7, 59, 59, 999999), "2026-11"),
			(datetime(2026, 12, 1, 2, 0, 0), "2026-11"),
			# decoy: early morning on another day stays in the same month
			(datetime(2026, 12, 2, 2, 0, 0), "2026-12"),
			# last day of a month
			(datetime(2026, 11, 30, 23, 59, 59), "2026-11"),
			(datetime(2027, 2, 28, 23, 59, 59), "2027-02"),
			(datetime(2027, 3, 1, 7, 59, 59), "2027-02"),
			# year change
			(datetime(2027, 1, 1, 7, 59, 59, 999999), "2026-12"),
			(datetime(2027, 1, 1, 8, 0, 0), "2027-01"),
		)
		for now, expected in daily:
			with self.subTest(fn="daily_cycle", now=now):
				result = ops_data.daily_cycle(now)
				self.assertIs(type(result), date)
				self.assertEqual(result, expected)
		for now, expected in weekly:
			with self.subTest(fn="weekly_cycle", now=now):
				result = ops_data.weekly_cycle(now)
				self.assertIs(type(result), date)
				self.assertEqual(result, expected)
		for now, expected in monthly:
			with self.subTest(fn="monthly_cycle", now=now):
				self.assertEqual(ops_data.monthly_cycle(now), expected)


class TestCategoryLookup(FrappeTestCase):
	def setUp(self):
		keep_agent_settings(self)

	def test_reverse_mapping_keeps_only_ticket_types(self):
		mapping = {
			"A": {"ticket_type": TYPE_A, "agent_group": "IT", "priority": "High"},
			"D": {"ticket_type": TYPE_D, "agent_group": "", "priority": "Medium"},
			"E": {"ticket_type": "", "priority": ""},
			"F": {"agent_group": "IT", "priority": "Low"},
		}
		self.assertEqual(ops_data.category_by_ticket_type(mapping), {TYPE_A: "A", TYPE_D: "D"})

	def test_shared_ticket_type_earliest_category_wins(self):
		# the category met first in CATEGORIES order wins, whatever the JSON key order
		mapping = {"C": {"ticket_type": "X"}, "A": {"ticket_type": "X"}, "B": {"ticket_type": "Y"}}
		reversed_mapping = dict(reversed(list(mapping.items())))
		self.assertEqual(list(reversed_mapping), ["B", "A", "C"])
		for case in (mapping, reversed_mapping):
			with self.subTest(keys=list(case)):
				self.assertEqual(ops_data.category_by_ticket_type(case), {"X": "A", "Y": "B"})

	def test_keys_outside_categories_are_left_out(self):
		mapping = {
			"G": {"ticket_type": "Type G"},
			"a": {"ticket_type": "Type a"},
			"B": {"ticket_type": "Type B"},
		}
		self.assertEqual(ops_data.category_by_ticket_type(mapping), {"Type B": "B"})

	def test_empty_mapping_gives_empty_reverse_map(self):
		self.assertEqual(ops_data.category_by_ticket_type({}), {})

	def test_ticket_category(self):
		reverse_map = {TYPE_A: "A", TYPE_D: "D"}
		self.assertEqual(ops_data.ticket_category({"ticket_type": TYPE_A}, reverse_map), "A")
		self.assertEqual(ops_data.ticket_category(frappe._dict(ticket_type=TYPE_D), reverse_map), "D")
		# unknown ticket type, a category letter used as a ticket type, no ticket type
		self.assertIsNone(ops_data.ticket_category({"ticket_type": "Unknown"}, reverse_map))
		self.assertIsNone(ops_data.ticket_category({"ticket_type": "A"}, reverse_map))
		self.assertIsNone(ops_data.ticket_category({"ticket_type": None}, reverse_map))
		self.assertIsNone(ops_data.ticket_category({}, reverse_map))
		self.assertIsNone(ops_data.ticket_category({"ticket_type": TYPE_A}, {}))

	def test_ticket_category_empty_type_is_none_even_if_mapped(self):
		# an empty or missing type has no category, even with a hand-built map that holds such a key
		reverse_map = {"": "A", None: "B"}
		self.assertIsNone(ops_data.ticket_category({"ticket_type": ""}, reverse_map))
		self.assertIsNone(ops_data.ticket_category({"ticket_type": None}, reverse_map))
		self.assertIsNone(ops_data.ticket_category({}, reverse_map))

	def test_ba_note_marker(self):
		self.assertEqual(ops_data.BA_NOTE_MARKER, "**BA note**")


class TestTicketDeadline(FrappeTestCase):
	def setUp(self):
		keep_agent_settings(self)

	def test_date_value_is_end_of_day(self):
		resolution_by = datetime(2026, 11, 21, 17, 0)
		end_of_day = datetime(2026, 11, 20, 23, 59, 59)
		due_at = datetime(2026, 11, 20, 9, 30)
		cases = (
			# D, E: a Date due value is the end of that day (A-U5b-3); a Datetime is kept
			("D", resolution_by, date(2026, 11, 20), end_of_day),
			("E", resolution_by, date(2026, 11, 20), end_of_day),
			("D", resolution_by, due_at, due_at),
			("E", resolution_by, due_at, due_at),
			# D, E with an empty due value: resolution_by
			("D", resolution_by, None, resolution_by),
			("E", resolution_by, "", resolution_by),
			# A, B (and an unknown category): always resolution_by, whatever the due value
			("A", resolution_by, date(2026, 11, 20), resolution_by),
			("B", resolution_by, due_at, resolution_by),
			(None, resolution_by, due_at, resolution_by),
			# resolution_by read as a string is turned into a datetime; none at all -> None
			("A", "2026-11-21 17:00:00", None, resolution_by),
			("D", "2026-11-21 17:00:00", None, resolution_by),
			("A", None, None, None),
			("D", "", None, None),
		)
		for category, resolution, due_value, expected in cases:
			with self.subTest(category=category, resolution_by=resolution, due_value=due_value):
				result = ops_data.ticket_deadline(category, resolution, due_value)
				self.assertEqual(result, expected)
				if expected is not None:
					self.assertIs(type(result), datetime)


class TestMilestoneHelpers(FrappeTestCase):
	def setUp(self):
		keep_agent_settings(self)
		self.addCleanup(frappe.db.rollback)

	def test_ba_note_and_task_sets(self):
		noted, human_only, plain, other = (_fake_ticket() for _ in range(4))
		_comment(noted, AGENT_USER, f"{ops_data.BA_NOTE_MARKER}\nPhân tích nghiệp vụ")
		# a person's comment that starts with the marker is not a BA note; the bot's comment must start with it
		_comment(human_only, HUMAN_AGENT, f"{ops_data.BA_NOTE_MARKER}\nghi chú của người")
		_comment(plain, AGENT_USER, f"Ghi chú: {ops_data.BA_NOTE_MARKER} chưa có")
		# a ticket outside the asked names is never returned
		_comment(other, AGENT_USER, f"{ops_data.BA_NOTE_MARKER}\nphiếu khác")
		_task(noted)
		_task(noted)
		_task(other)
		names = [noted, human_only, plain]

		self.assertEqual(ops_data.tickets_with_ba_note([]), set())
		self.assertEqual(ops_data.tickets_with_task([]), set())
		self.assertEqual(ops_data.tickets_with_ba_note(names), {noted})
		self.assertEqual(ops_data.tickets_with_task(names), {noted})
		self.assertEqual(ops_data.tickets_with_ba_note([human_only, plain]), set())
		self.assertEqual(ops_data.tickets_with_task([human_only, plain]), set())

	def test_due_field_rejects_non_date_field(self):
		for due_field in (None, ""):
			with self.subTest(due_field=due_field), patch("frappe.logger") as get_logger:
				self.assertIsNone(ops_data.due_field(due_field))
				self.assertEqual(get_logger.return_value.warning.call_args_list, [])
		for due_field in (DATETIME_DUE_FIELD, DATE_DUE_FIELD):
			with self.subTest(due_field=due_field), patch("frappe.logger") as get_logger:
				self.assertEqual(ops_data.due_field(due_field), due_field)
				self.assertEqual(get_logger.return_value.warning.call_args_list, [])
		# "subject" is a field of HD Ticket but not a Date/Datetime field
		for due_field in ("erpai_test_no_such_field", "subject"):
			with self.subTest(due_field=due_field), patch("frappe.logger") as get_logger:
				self.assertIsNone(ops_data.due_field(due_field))
				get_logger.assert_called_with(LOGGER_NAME)
				self.assertEqual(
					get_logger.return_value.warning.call_args_list,
					[
						call(
							"erp_ai daily_report: due field %s is not a Date/Datetime field of HD Ticket, "
							"using resolution_by",
							due_field,
						)
					],
				)
