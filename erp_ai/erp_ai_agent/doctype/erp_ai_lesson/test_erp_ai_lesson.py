import json
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.agent import lessons
from erp_ai.constants import (
	AGENT_USER,
	LESSON_DOCTYPE,
	LESSON_SOURCE_CORRECTION,
	LESSON_SOURCE_OUTCOME,
	LESSON_SOURCE_RESOLVED,
	LESSON_SOURCE_TEACHING,
	LESSON_STATUS_ACTIVE,
	LESSON_STATUS_PENDING,
	ROLE_INSTRUCTOR,
)
from erp_ai.erp_ai_agent.doctype.erp_ai_lesson import erp_ai_lesson
from erp_ai.test_utils import clear_lesson_store, keep_agent_settings, set_agent_settings

DOCTYPE_JSON = Path(__file__).with_name("erp_ai_lesson.json")


class TestERPAILesson(FrappeTestCase):
	def setUp(self):
		frappe.db.rollback()
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("test must not commit"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		keep_agent_settings(self)
		# Only the lessons this test makes: the shared site holds real ones (NFR-7, rolled back, never committed).
		clear_lesson_store()

	def test_no_role_can_create_or_write(self):
		permissions = json.loads(DOCTYPE_JSON.read_text(encoding="utf-8"))["permissions"]
		self.assertEqual({row["role"] for row in permissions}, {"System Manager", ROLE_INSTRUCTOR})
		for row in permissions:
			granted = {key for key, value in row.items() if key != "role" and value}
			self.assertEqual(granted, {"read"}, row["role"])

	def test_ticket_with_lesson_can_be_deleted(self):
		ticket = make_ticket(subject="erp_ai lesson ticket delete")
		doc = frappe.get_doc(
			{
				"doctype": LESSON_DOCTYPE,
				"lesson_status": LESSON_STATUS_PENDING,
				"lesson_source": LESSON_SOURCE_TEACHING,
				"situation": "tình huống thử",
				"lesson_text": "bài học thử",
				"ticket": ticket.name,
			}
		)
		doc.flags.erp_ai_lesson_store = True
		doc.insert(ignore_permissions=True)
		frappe.delete_doc("HD Ticket", ticket.name, force=False)
		self.assertFalse(frappe.db.exists("HD Ticket", ticket.name))
		self.assertTrue(frappe.db.exists(LESSON_DOCTYPE, doc.name))


INSTRUCTOR = "erp-ai-lesson-ctl-instructor@example.com"
PLAIN = "erp-ai-lesson-ctl-plain@example.com"
MANAGER = "erp-ai-lesson-ctl-manager@example.com"


def _make_user(email, *roles):
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


def _lesson_values(**fields):
	values = {
		"doctype": LESSON_DOCTYPE,
		"lesson_status": LESSON_STATUS_PENDING,
		"lesson_source": LESSON_SOURCE_TEACHING,
		"situation": "tình huống thử",
		"lesson_text": "bài học thử",
	}
	values.update(fields)
	return values


class TestLessonController(FrappeTestCase):
	def setUp(self):
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
		_make_user(MANAGER, "System Manager")
		set_agent_settings(lessons_enabled=1)

	def _stored(self, **fields):
		doc = frappe.get_doc(_lesson_values(**fields))
		doc.flags.erp_ai_lesson_store = True
		doc.insert(ignore_permissions=True)
		return doc

	def _post(self, user, func, **kwargs):
		frappe.set_user(user)
		try:
			return func(**kwargs)
		finally:
			frappe.set_user("Administrator")

	def test_direct_insert_refused(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(_lesson_values()).insert(ignore_permissions=True)
		self.assertEqual(frappe.db.count(LESSON_DOCTYPE), 0)

	def test_direct_save_refused(self):
		doc = self._stored()
		doc = frappe.get_doc(LESSON_DOCTYPE, doc.name)
		doc.lesson_text = "sửa tay"
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value(LESSON_DOCTYPE, doc.name, "lesson_text"), "bài học thử")

	def test_delete_refused(self):
		doc = self._stored()
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc(LESSON_DOCTYPE, doc.name, force=True)
		self.assertTrue(frappe.db.exists(LESSON_DOCTYPE, doc.name))

	def test_teach_by_instructor_active(self):
		result = self._post(
			INSTRUCTOR, erp_ai_lesson.teach, rule="Phiếu máy in chuyển IT", situation="Máy in"
		)
		rows = frappe.get_all(LESSON_DOCTYPE, fields=["name", "lesson_source", "lesson_status", "ticket"])
		self.assertEqual(len(rows), 1)
		self.assertEqual(result, {"name": rows[0].name})
		self.assertEqual(
			(rows[0].lesson_source, rows[0].lesson_status, rows[0].ticket),
			(LESSON_SOURCE_TEACHING, LESSON_STATUS_ACTIVE, None),
		)
		doc = frappe.get_doc(LESSON_DOCTYPE, rows[0].name)
		self.assertEqual([row.step for row in doc.history], ["Tạo"])

	def test_teach_refused_for_others(self):
		for user in (PLAIN, MANAGER, "Administrator", "Guest", AGENT_USER):
			with self.subTest(user=user):
				with self.assertRaises(frappe.PermissionError):
					self._post(user, erp_ai_lesson.teach, rule="Quy tắc thử")
		self.assertEqual(frappe.db.count(LESSON_DOCTYPE), 0)

	def test_teach_validation(self):
		set_agent_settings(lessons_enabled=0)
		with self.assertRaisesRegex(frappe.ValidationError, "Bot đang tắt việc học"):
			self._post(INSTRUCTOR, erp_ai_lesson.teach, rule="Quy tắc thử")
		set_agent_settings(lessons_enabled=1)
		for rule in (None, "", "   \n "):
			with self.assertRaisesRegex(frappe.ValidationError, "Cần nhập quy tắc"):
				self._post(INSTRUCTOR, erp_ai_lesson.teach, rule=rule)
		self.assertEqual(frappe.db.count(LESSON_DOCTYPE), 0)

	def test_decide_moves_status(self):
		doc = self._stored(lesson_status=LESSON_STATUS_ACTIVE)
		result = self._post(INSTRUCTOR, erp_ai_lesson.decide, name=doc.name, action="disable")
		self.assertEqual(result, {"status": "Đã tắt"})
		with self.assertRaises(lessons.InvalidLessonTransition):
			self._post(INSTRUCTOR, erp_ai_lesson.decide, name=doc.name, action="bogus")

	def test_methods_are_post_only(self):
		for func in (erp_ai_lesson.teach, erp_ai_lesson.decide):
			self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[func], ["POST"])

	def test_list_filters_by_source_and_status(self):
		sources = (
			LESSON_SOURCE_TEACHING,
			LESSON_SOURCE_CORRECTION,
			LESSON_SOURCE_OUTCOME,
			LESSON_SOURCE_RESOLVED,
		)
		for index, source in enumerate(sources):
			status = LESSON_STATUS_ACTIVE if index % 2 else LESSON_STATUS_PENDING
			self._stored(lesson_source=source, lesson_status=status, event_key=f"list-{index}")
		for source in sources:
			self.assertEqual(frappe.get_all(LESSON_DOCTYPE, filters={"lesson_source": source}).__len__(), 1)
		for status in (LESSON_STATUS_ACTIVE, LESSON_STATUS_PENDING):
			self.assertEqual(len(frappe.get_all(LESSON_DOCTYPE, filters={"lesson_status": status})), 2)
