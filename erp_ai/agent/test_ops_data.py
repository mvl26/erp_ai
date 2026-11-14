from datetime import date, datetime

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.agent import ops_data
from erp_ai.test_utils import keep_agent_settings

TYPE_A = "Sự cố & lỗi hệ thống"
TYPE_D = "Chuẩn hóa dữ liệu & quy trình trên ERP"


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

	def test_ba_note_marker(self):
		self.assertEqual(ops_data.BA_NOTE_MARKER, "**BA note**")
