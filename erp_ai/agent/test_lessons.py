from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.agent import authority, lessons
from erp_ai.constants import (
	AGENT_USER,
	LESSON_DOCTYPE,
	LESSON_SOURCE_CORRECTION,
	LESSON_SOURCE_OUTCOME,
	LESSON_SOURCE_RESOLVED,
	LESSON_SOURCE_TEACHING,
	LESSON_STATUS_ACTIVE,
	LESSON_STATUS_DISABLED,
	LESSON_STATUS_PENDING,
	LESSON_STATUS_REJECTED,
	LESSON_STEPS,
	ROLE_INSTRUCTOR,
)
from erp_ai.test_utils import clear_lesson_store, keep_agent_settings, set_agent_settings

INSTRUCTOR = "erp-ai-lesson-instructor@example.com"
PLAIN = "erp-ai-lesson-plain@example.com"
REVIEWER = "erp-ai-lesson-reviewer@example.com"
MANAGER = "erp-ai-lesson-manager@example.com"
INSTRUCTOR_MANAGER = "erp-ai-lesson-instructor-manager@example.com"
FAKE_KEY = "sk-ant-api03-" + "Ab1" * 13 + "Z"
ERROR_TITLE = "erp_ai: ghi bài học lỗi"


def _make_user(email, *roles):
	"""A user holding exactly `roles`, created inside the test transaction."""
	for role in roles:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)
	if not frappe.db.exists("User", email):
		user = frappe.new_doc("User")
		user.update({"email": email, "first_name": email.split("@")[0], "send_welcome_email": 0})
		for role in roles:
			user.append("roles", {"role": role})
		user.insert(ignore_permissions=True)
	return email


def _ensure_team(name):
	if not frappe.db.exists("HD Team", name):
		frappe.get_doc(
			{"doctype": "HD Team", "team_name": name, "users": [{"user": "Administrator"}]}
		).insert(ignore_permissions=True)


def _count(**filters):
	return frappe.db.count(LESSON_DOCTYPE, filters)


def _steps(name):
	return [row.step for row in frappe.get_doc(LESSON_DOCTYPE, name).history]


class TestLessonStore(FrappeTestCase):
	def setUp(self):
		# HD Team.after_insert caches an Assignment Rule in Redis; registered first so it runs after the rollback.
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
		_make_user(INSTRUCTOR, ROLE_INSTRUCTOR)
		_make_user(PLAIN, "Desk User")
		_make_user(REVIEWER, "Desk User")
		_make_user(MANAGER, "System Manager")
		_make_user(INSTRUCTOR_MANAGER, ROLE_INSTRUCTOR, "System Manager")
		set_agent_settings(
			enabled=0,
			lessons_enabled=1,
			excluded_teams="",
			excluded_title_prefixes="",
			monthly_reviewers=REVIEWER,
		)
		self.ticket = make_ticket(
			subject="Máy in phòng kế toán không in được",
			description="<p>Máy in <b>báo</b> lỗi</p><p>giấy   kẹt</p>",
		).name

	def _store(self, user, key, source=LESSON_SOURCE_CORRECTION, **values):
		frappe.set_user(user)
		values.setdefault("situation", "Máy in không in được")
		values.setdefault("text", "Phiếu máy in chuyển nhóm IT")
		values.setdefault("authorized", False)
		values.setdefault("ticket", self.ticket)
		try:
			return lessons._store(source, key, **values)
		finally:
			frappe.set_user("Administrator")

	def _pending(self, key):
		return self._store(PLAIN, key)

	def _active(self, key):
		return self._store(INSTRUCTOR, key, authorized=True)

	def _transition(self, user, name, action):
		frappe.set_user(user)
		try:
			return lessons.transition(name, action)
		finally:
			frappe.set_user("Administrator")

	def test_correction_by_instructor_is_active_by_other_is_pending(self):
		self.assertTrue(authority.is_instruction(INSTRUCTOR, self.ticket))
		self.assertFalse(authority.is_instruction(PLAIN, self.ticket))
		active = self._store(
			INSTRUCTOR, "test:instructor", authorized=authority.is_instruction(INSTRUCTOR, self.ticket)
		)
		pending = self._store(PLAIN, "test:plain", authorized=authority.is_instruction(PLAIN, self.ticket))
		row = frappe.db.get_value(
			LESSON_DOCTYPE, active, ["lesson_status", "lesson_source", "ticket", "author"], as_dict=True
		)
		self.assertEqual(
			(row.lesson_status, row.lesson_source, row.ticket, row.author),
			(LESSON_STATUS_ACTIVE, LESSON_SOURCE_CORRECTION, self.ticket, INSTRUCTOR),
		)
		self.assertEqual(frappe.db.get_value(LESSON_DOCTYPE, pending, "lesson_status"), LESSON_STATUS_PENDING)
		self.assertEqual(frappe.db.get_value(LESSON_DOCTYPE, pending, "author"), PLAIN)
		self.assertEqual(_steps(active), ["Tạo"])

	def test_teaching_without_authority_makes_nothing(self):
		self.assertIsNone(self._store(PLAIN, "test:teach", source=LESSON_SOURCE_TEACHING, authorized=False))
		self.assertEqual(_count(), 0)
		name = self._store(INSTRUCTOR, "test:teach", source=LESSON_SOURCE_TEACHING, authorized=True)
		self.assertEqual(frappe.db.get_value(LESSON_DOCTYPE, name, "lesson_status"), LESSON_STATUS_ACTIVE)

	def test_outcome_is_active(self):
		name = self._store(PLAIN, "test:outcome", source=LESSON_SOURCE_OUTCOME, authorized=False)
		self.assertEqual(frappe.db.get_value(LESSON_DOCTYPE, name, "lesson_status"), LESSON_STATUS_ACTIVE)
		resolved = self._store(INSTRUCTOR, "test:resolved", source=LESSON_SOURCE_RESOLVED, authorized=True)
		self.assertEqual(
			frappe.db.get_value(LESSON_DOCTYPE, resolved, "lesson_status"), LESSON_STATUS_PENDING
		)

	def test_same_event_key_twice_makes_one_row(self):
		first = self._store(PLAIN, "test:twice")
		second = self._store(INSTRUCTOR, "test:twice", authorized=True, text="Một bài khác hẳn")
		self.assertEqual(first, second)
		self.assertEqual(_count(event_key="test:twice"), 1)
		self.assertEqual(_steps(first), ["Tạo"])
		row = frappe.db.get_value(
			LESSON_DOCTYPE, first, ["lesson_text", "lesson_status", "author"], as_dict=True
		)
		self.assertEqual(
			(row.lesson_text, row.lesson_status, row.author),
			("Phiếu máy in chuyển nhóm IT", LESSON_STATUS_PENDING, PLAIN),
		)

	def test_updatable_key_updates_text_and_status(self):
		name = self._store(INSTRUCTOR, "test:update", authorized=True, updatable=True)
		self.assertEqual(frappe.db.get_value(LESSON_DOCTYPE, name, "lesson_status"), LESSON_STATUS_ACTIVE)
		again = self._store(
			PLAIN,
			"test:update",
			authorized=False,
			updatable=True,
			situation="Tình huống mới",
			text="Phiếu máy in chuyển nhóm Kế toán",
		)
		self.assertEqual(again, name)
		self.assertEqual(_count(), 1)
		doc = frappe.get_doc(LESSON_DOCTYPE, name)
		self.assertEqual(
			(doc.lesson_text, doc.situation, doc.lesson_status, doc.author),
			("Phiếu máy in chuyển nhóm Kế toán", "Tình huống mới", LESSON_STATUS_PENDING, PLAIN),
		)
		self.assertEqual([row.step for row in doc.history], ["Tạo", "Cập nhật"])
		self.assertEqual(doc.history[1].actor, PLAIN)
		self.assertIsNotNone(doc.history[1].happened_at)

	def test_update_with_same_content_is_noop(self):
		name = self._store(INSTRUCTOR, "test:same", authorized=True, updatable=True)
		modified = frappe.db.get_value(LESSON_DOCTYPE, name, "modified")
		again = self._store(
			INSTRUCTOR_MANAGER,
			"test:same",
			authorized=True,
			updatable=True,
			situation="  Máy in   không in được ",
			text="Phiếu máy in\nchuyển nhóm IT",
		)
		self.assertEqual(again, name)
		self.assertEqual(_steps(name), ["Tạo"])
		row = frappe.db.get_value(LESSON_DOCTYPE, name, ["author", "modified"], as_dict=True)
		self.assertEqual((row.author, row.modified), (INSTRUCTOR, modified))

	def test_update_that_changes_status_clears_review(self):
		name = self._store(PLAIN, "test:review", updatable=True)
		self._transition(REVIEWER, name, "approve")
		self._store(INSTRUCTOR, "test:review", authorized=True, updatable=True, text="Bài đã sửa lần một")
		row = frappe.db.get_value(LESSON_DOCTYPE, name, ["lesson_status", "reviewed_by"], as_dict=True)
		self.assertEqual((row.lesson_status, row.reviewed_by), (LESSON_STATUS_ACTIVE, REVIEWER))
		self._store(PLAIN, "test:review", authorized=False, updatable=True, text="Bài đã sửa lần hai")
		doc = frappe.get_doc(LESSON_DOCTYPE, name)
		self.assertEqual(
			(doc.lesson_status, doc.reviewed_by, doc.reviewed_at, doc.lesson_text),
			(LESSON_STATUS_PENDING, None, None, "Bài đã sửa lần hai"),
		)
		self.assertEqual([row.step for row in doc.history], ["Tạo", "Duyệt", "Cập nhật", "Cập nhật"])

	def test_learning_off_makes_nothing(self):
		set_agent_settings(lessons_enabled=0)
		for source in (LESSON_SOURCE_CORRECTION, LESSON_SOURCE_TEACHING, LESSON_SOURCE_OUTCOME):
			self.assertIsNone(self._store(INSTRUCTOR, f"test:off:{source}", source=source, authorized=True))
		self.assertEqual(_count(), 0)

	def test_excluded_ticket_makes_nothing(self):
		team = "erp_ai lesson excluded team"
		_ensure_team(team)
		set_agent_settings(excluded_teams=team)
		frappe.db.set_value("HD Ticket", self.ticket, "agent_group", team)
		self.assertIsNone(self._store(INSTRUCTOR, "test:excluded", authorized=True))
		self.assertEqual(lessons._ticket_situation(self.ticket, with_description=True), "")
		opted_out = make_ticket(subject="Phiếu không dùng AI").name
		frappe.db.set_value("HD Ticket", opted_out, "ai_opt_out", 1)
		self.assertIsNone(
			self._store(INSTRUCTOR, "test:opt-out", source=LESSON_SOURCE_OUTCOME, ticket=opted_out)
		)
		self.assertEqual(_count(), 0)

	def test_secrets_masked_and_text_cut(self):
		secret_text = f"Dùng khóa {FAKE_KEY} và password=hunter2 để   vào\n\nmáy"
		name = self._store(
			PLAIN, "test:secret", text=secret_text, situation=f"Tình huống {FAKE_KEY} password=hunter2"
		)
		row = frappe.db.get_value(LESSON_DOCTYPE, name, ["lesson_text", "situation"], as_dict=True)
		for value in (row.lesson_text, row.situation):
			self.assertNotIn("sk-ant-api03-", value)
			self.assertNotIn(FAKE_KEY[13:], value)
			self.assertNotIn("hunter2", value)
		self.assertTrue(row.lesson_text.endswith("để vào máy"), row.lesson_text)
		long_name = self._store(PLAIN, "test:long", text="x" * 5000, situation="y" * 5000)
		row = frappe.db.get_value(LESSON_DOCTYPE, long_name, ["lesson_text", "situation"], as_dict=True)
		self.assertEqual(
			(len(row.lesson_text), len(row.situation)), (lessons.TEXT_MAX, lessons.SITUATION_MAX)
		)
		self.assertEqual((lessons.TEXT_MAX, lessons.SITUATION_MAX), (1000, 300))
		self.assertIsNone(self._store(PLAIN, "test:blank", text="  \n\t "))
		self.assertEqual(_count(event_key="test:blank"), 0)

	def test_agent_session_refused(self):
		for source in (LESSON_SOURCE_CORRECTION, LESSON_SOURCE_TEACHING, LESSON_SOURCE_OUTCOME):
			with self.assertRaises(frappe.PermissionError):
				self._store(AGENT_USER, f"test:agent:{source}", source=source, authorized=True)
		self.assertEqual(_count(), 0)

	def test_ticket_situation(self):
		self.assertEqual(
			lessons._ticket_situation(self.ticket, with_description=False),
			"Máy in phòng kế toán không in được",
		)
		self.assertEqual(
			lessons._ticket_situation(self.ticket, with_description=True),
			"Máy in phòng kế toán không in được: Máy in báo lỗi giấy kẹt",
		)
		self.assertEqual(lessons._ticket_situation("không-có-phiếu-này", with_description=True), "")

	def test_transitions(self):
		approved = self._pending("test:approve")
		self.assertEqual(self._transition(REVIEWER, approved, "approve"), LESSON_STATUS_ACTIVE)
		rejected = self._pending("test:reject")
		self.assertEqual(self._transition(MANAGER, rejected, "reject"), LESSON_STATUS_REJECTED)
		self.assertEqual(self._transition(INSTRUCTOR, approved, "disable"), LESSON_STATUS_DISABLED)
		self.assertEqual(self._transition(INSTRUCTOR, approved, "enable"), LESSON_STATUS_ACTIVE)

		doc = frappe.get_doc(LESSON_DOCTYPE, approved)
		self.assertEqual(doc.lesson_status, LESSON_STATUS_ACTIVE)
		self.assertEqual([row.step for row in doc.history], ["Tạo", "Duyệt", "Tắt", "Bật"])
		self.assertEqual([row.actor for row in doc.history], [PLAIN, REVIEWER, INSTRUCTOR, INSTRUCTOR])
		self.assertTrue(all(row.happened_at for row in doc.history))
		self.assertEqual(doc.reviewed_by, INSTRUCTOR)
		self.assertIsNotNone(doc.reviewed_at)
		self.assertEqual(doc.author, PLAIN)

		doc = frappe.get_doc(LESSON_DOCTYPE, rejected)
		self.assertEqual(doc.lesson_status, LESSON_STATUS_REJECTED)
		self.assertEqual([row.step for row in doc.history], ["Tạo", "Từ chối"])
		self.assertEqual((doc.history[1].actor, doc.reviewed_by), (MANAGER, MANAGER))
		self.assertIsNotNone(doc.reviewed_at)
		self.assertTrue(set(lessons.ACTIONS[action][2] for action in lessons.ACTIONS) <= set(LESSON_STEPS))

	def test_transition_permissions(self):
		pending = self._pending("test:perm-pending")
		active = self._active("test:perm-active")
		disabled = self._active("test:perm-disabled")
		self._transition(INSTRUCTOR, disabled, "disable")
		lesson_for = {"approve": pending, "reject": pending, "disable": active, "enable": disabled}

		def refused(user, action):
			name = lesson_for[action]
			before = (frappe.db.get_value(LESSON_DOCTYPE, name, "lesson_status"), _steps(name))
			with self.assertRaises(frappe.PermissionError, msg=f"{user} {action}"):
				self._transition(user, name, action)
			self.assertEqual(
				(frappe.db.get_value(LESSON_DOCTYPE, name, "lesson_status"), _steps(name)), before
			)

		for user in (AGENT_USER, PLAIN, "Administrator", "Guest"):
			for action in lessons.ACTIONS:
				refused(user, action)
		for action in ("disable", "enable"):
			refused(REVIEWER, action)
			refused(MANAGER, action)
		for action in ("approve", "reject"):
			refused(INSTRUCTOR, action)
		self.assertEqual(self._transition(INSTRUCTOR_MANAGER, pending, "approve"), LESSON_STATUS_ACTIVE)
		set_agent_settings(monthly_reviewers=INSTRUCTOR)
		other = self._pending("test:perm-listed")
		self.assertEqual(self._transition(INSTRUCTOR, other, "reject"), LESSON_STATUS_REJECTED)

	def test_repeat_transition_refused(self):
		name = self._pending("test:repeat")
		self._transition(REVIEWER, name, "approve")
		with self.assertRaises(lessons.InvalidLessonTransition):
			self._transition(REVIEWER, name, "approve")
		self.assertEqual(_steps(name), ["Tạo", "Duyệt"])

		rejected = self._pending("test:repeat-reject")
		self._transition(REVIEWER, rejected, "reject")
		for action in lessons.ACTIONS:
			user = REVIEWER if action in ("approve", "reject") else INSTRUCTOR
			with self.assertRaises(lessons.InvalidLessonTransition, msg=action):
				self._transition(user, rejected, action)
		self.assertEqual(_steps(rejected), ["Tạo", "Từ chối"])
		self.assertEqual(
			frappe.db.get_value(LESSON_DOCTYPE, rejected, "lesson_status"), LESSON_STATUS_REJECTED
		)

	def test_unknown_action_and_missing_lesson(self):
		name = self._pending("test:unknown")
		for action in ("delete", "", None, "Approve"):
			with self.assertRaises(lessons.InvalidLessonTransition, msg=repr(action)):
				self._transition(REVIEWER, name, action)
		for missing in ("AILSN-không-có", "", None, {"lesson_status": LESSON_STATUS_PENDING}):
			with self.assertRaises(frappe.DoesNotExistError, msg=repr(missing)):
				self._transition(REVIEWER, missing, "approve")
		self.assertEqual(_steps(name), ["Tạo"])
		self.assertEqual(frappe.db.get_value(LESSON_DOCTYPE, name, "lesson_status"), LESSON_STATUS_PENDING)

	def test_transition_of_lesson_whose_ticket_was_deleted(self):
		name = self._pending("test:deleted-ticket")
		frappe.delete_doc("HD Ticket", self.ticket, force=False)
		frappe.db.value_cache.clear()  # the decision comes in a later request, which has not cached the ticket
		self.assertEqual(self._transition(REVIEWER, name, "approve"), LESSON_STATUS_ACTIVE)

	def test_safely_swallows_and_logs(self):
		kept = self._pending("test:kept")
		before = frappe.db.count("Error Log", {"method": ERROR_TITLE})
		real_store = lessons._store

		def store_then_fail(*args, **kwargs):
			real_store(*args, **kwargs)
			raise RuntimeError(f"boom {FAKE_KEY}")

		frappe.set_user(PLAIN)
		with patch.object(lessons, "_store", side_effect=store_then_fail):
			result = lessons.safely(
				lessons._store,
				LESSON_SOURCE_CORRECTION,
				"test:undone",
				situation="Tình huống",
				text="Bài sẽ bị hoàn lại",
				authorized=False,
				ticket=self.ticket,
			)
		frappe.set_user("Administrator")
		self.assertIsNone(result)
		self.assertTrue(frappe.db.exists(LESSON_DOCTYPE, kept))
		self.assertEqual(_count(event_key="test:undone"), 0)
		self.assertEqual(frappe.db.count("Error Log", {"method": ERROR_TITLE}), before + 1)
		error = frappe.get_all(
			"Error Log", filters={"method": ERROR_TITLE}, fields=["error"], order_by="creation desc", limit=1
		)[0].error
		self.assertIn("RuntimeError", error)
		self.assertNotIn("sk-ant-api03-", error)
		self.assertNotIn(FAKE_KEY[13:], error)
		self.assertEqual(lessons.safely(lambda value: value, "giá trị"), "giá trị")

	def test_safely_drops_the_messages_of_a_swallowed_failure(self):
		# A message left in message_log goes back on the person's successful response as a red dialog.
		self.addCleanup(setattr, frappe.local, "message_log", list(frappe.local.message_log))
		frappe.msgprint("Tin của chính người dùng")
		before = list(frappe.local.message_log)

		def warn_then_throw():
			frappe.msgprint("Cảnh báo trong kho")
			frappe.throw("Kho bài học lỗi")

		self.assertIsNone(lessons.safely(warn_then_throw))
		self.assertEqual(frappe.local.message_log, before)
		frappe.set_user(AGENT_USER)
		self.assertIsNone(
			lessons.safely(
				lessons._store,
				LESSON_SOURCE_CORRECTION,
				"test:agent-message",
				situation="Tình huống",
				text="Bài học",
				authorized=True,
				ticket=self.ticket,
			)
		)
		frappe.set_user("Administrator")
		self.assertEqual(frappe.local.message_log, before)
		self.assertEqual(_count(), 0)
