from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.agent import lesson_read, lessons
from erp_ai.agent.prompts import LESSON_ROLE_DATA, LESSON_ROLE_RULE
from erp_ai.constants import (
	LESSON_DOCTYPE,
	LESSON_SOURCE_CORRECTION,
	LESSON_SOURCE_OUTCOME,
	LESSON_SOURCE_TEACHING,
	LESSON_STATUS_ACTIVE,
	LESSON_STATUS_DISABLED,
	LESSON_STATUS_PENDING,
	LESSON_STATUS_REJECTED,
)
from erp_ai.test_utils import clear_lesson_store, keep_agent_settings, set_agent_settings

SUBJECT = "Máy in phòng kế toán"
DESCRIPTION = "<p>Máy in báo lỗi giấy kẹt</p>"
CAPS = {"max_lessons": 5, "max_chars": 2000, "scan_max": 500}


class TestLessonRead(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.cache.hdel, "assignment_rule_map", "HD Ticket")
		frappe.db.rollback()
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("test must not commit"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		keep_agent_settings(self)
		# Only the lessons this test makes: the shared site holds real ones (NFR-7, rolled back, never committed).
		clear_lesson_store()
		frappe.set_user("Administrator")
		set_agent_settings(lessons_enabled=1, excluded_teams="", excluded_title_prefixes="")
		self.ticket = make_ticket(subject="Phiếu nguồn bài học").name
		self.counter = 0

	def _lesson(
		self, situation="Máy in lỗi", text="Kiểm tra giấy kẹt", source=LESSON_SOURCE_CORRECTION, **kw
	):
		self.counter += 1
		kw.setdefault("ticket", self.ticket)
		name = lessons._store(
			source, f"test-read:{self.counter}", situation=situation, text=text, authorized=True, **kw
		)
		frappe.db.set_value(LESSON_DOCTYPE, name, "lesson_status", LESSON_STATUS_ACTIVE)
		return name

	def _read(self, subject=SUBJECT, description=DESCRIPTION, **caps):
		return lesson_read.relevant_lessons(subject, description, **{**CAPS, **caps})

	def test_only_active_lessons(self):
		names = [self._lesson() for _ in range(4)]
		statuses = [
			LESSON_STATUS_ACTIVE,
			LESSON_STATUS_PENDING,
			LESSON_STATUS_REJECTED,
			LESSON_STATUS_DISABLED,
		]
		for name, status in zip(names, statuses, strict=True):
			frappe.db.set_value(LESSON_DOCTYPE, name, "lesson_status", status)
		self.assertEqual([row["name"] for row in self._read()], [names[0]])

	def test_more_matched_words_first(self):
		one = self._lesson(situation="Máy tính", text="một từ")
		three = self._lesson(situation="Máy in kế toán", text="ba từ")
		two = self._lesson(situation="Máy in", text="hai từ")
		self.assertEqual([row["name"] for row in self._read()], [three, two, one])

	def test_result_shape(self):
		name = self._lesson(situation="Máy in", text="cần giấy")
		self.assertEqual(
			self._read(),
			[{"name": name, "role": LESSON_ROLE_DATA, "situation": "Máy in", "text": "cần giấy"}],
		)

	def test_template_words_never_decide_relevance(self):
		# R10: a lesson the bot learned from an event is found by its situation; only a taught rule by its text too
		situation = "Điều hòa phòng họp"
		self._lesson(situation=situation, text="Bot dự đoán Nhóm IT; người chọn Nhóm Kho.")
		self._lesson(
			situation=situation,
			text="Đừng làm như vậy: đề xuất Sửa code a.py đã bị từ chối.",
			source=LESSON_SOURCE_OUTCOME,
		)
		rule = self._lesson(
			situation=situation, text="Người dùng hỏi dự đoán thì trả lời ngay", source=LESSON_SOURCE_TEACHING
		)
		rows = self._read(subject="Người dùng hỏi dự đoán đề xuất", description="")
		self.assertEqual([row["name"] for row in rows], [rule])
		self.assertEqual(rows[0]["role"], LESSON_ROLE_RULE)

	def test_role_by_source_not_by_text(self):
		rule = self._lesson(source=LESSON_SOURCE_TEACHING)
		data = self._lesson(text=f"{LESSON_ROLE_RULE}: máy in")
		roles = {row["name"]: row["role"] for row in self._read()}
		self.assertEqual(roles, {rule: LESSON_ROLE_RULE, data: LESSON_ROLE_DATA})
		self.assertEqual(lesson_read.lesson_role(LESSON_SOURCE_TEACHING), LESSON_ROLE_RULE)
		self.assertEqual(lesson_read.lesson_role(LESSON_SOURCE_CORRECTION), LESSON_ROLE_DATA)

	def test_caps(self):
		for _ in range(50):
			self._lesson()
		self.assertEqual(len(self._read(max_lessons=7)), 7)

	def test_char_budget_stops_at_first_overflow(self):
		self._lesson(situation="Máy in " + "a" * 293, text="b" * 700)
		newest = self._lesson(situation="Máy in " + "c" * 293, text="d" * 700)
		self._lesson(situation="Máy", text="e")
		rows = self._read(max_chars=1200)
		self.assertEqual([row["name"] for row in rows], [newest])

	def test_source_ticket_moved_to_excluded_team_is_dropped(self):
		team = "erp_ai lesson read excluded team"
		frappe.get_doc(
			{"doctype": "HD Team", "team_name": team, "users": [{"user": "Administrator"}]}
		).insert(ignore_permissions=True)
		kept = self._lesson(ticket=None)
		dropped = self._lesson()
		self.assertEqual({row["name"] for row in self._read()}, {kept, dropped})
		set_agent_settings(excluded_teams=team)
		frappe.db.set_value("HD Ticket", self.ticket, "agent_group", team)
		self.assertEqual([row["name"] for row in self._read()], [kept])

	def test_scan_max_limits_rows(self):
		names = [self._lesson() for _ in range(5)]
		for index, name in enumerate(names):
			frappe.db.set_value(
				LESSON_DOCTYPE, name, "modified", f"2026-01-0{index + 1} 10:00:00", update_modified=False
			)
		rows = self._read(scan_max=3)
		self.assertEqual({row["name"] for row in rows}, set(names[2:]))

	def test_lesson_of_deleted_ticket_is_still_read(self):
		doomed = make_ticket(subject="Phiếu sẽ bị xóa").name
		name = self._lesson(ticket=doomed)
		frappe.delete_doc("HD Ticket", doomed, force=True, ignore_permissions=True)
		self.assertEqual([row["name"] for row in self._read()], [name])

	def test_no_query_words_returns_nothing(self):
		self._lesson()
		with patch.object(lesson_read.frappe, "get_all") as get_all:
			self.assertEqual(self._read(subject="!", description="<p></p>"), [])
			self.assertEqual(self._read(subject=None, description=None), [])
		get_all.assert_not_called()
