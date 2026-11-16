import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.constants import AGENT_USER, LESSON_DOCTYPE, ROLE_INSTRUCTOR
from erp_ai.test_utils import keep_agent_settings, set_agent_settings

REVIEW_MONTH = "ERP AI Review Month"
FAKE_KEY = "sk-ant-api03-" + "Ab1" * 13 + "Z"
REVIEW_ITEM = "ERP AI Review Item"
JSON_PATH = Path(__file__).resolve().parent / "erp_ai_review_month.json"
ITEM_JSON_PATH = Path(__file__).resolve().parent.parent / "erp_ai_review_item" / "erp_ai_review_item.json"
MONTH = "2001-02"
NEXT_MONTH = "2001-03"
INSTRUCTOR_USER = "erp-ai-review-instructor@example.com"
MANAGER_USER = "erp-ai-review-manager@example.com"
RIGHTS = ("read", "write", "create", "delete", "submit", "cancel", "amend", "report", "export", "import")
# design.md:272: read and write; nobody creates or deletes (the job runs as Administrator).
GRANTED = {"System Manager": {"read", "write"}, ROLE_INSTRUCTOR: {"read", "write"}}
CONTROLLER_PATH = Path(__file__).resolve().parent / "erp_ai_review_month.py"
GUARDED_HOOKS = ("before_insert", "validate", "on_trash", "before_rename")
HOOK_ARGUMENTS = {"before_rename": ("old-name", "new-name", False)}
REFUSAL = "Tài khoản agent không được ghi"
LOCKED_MESSAGE = "Không được đổi danh sách phiếu của kỳ rà soát"


def _make_user(email, role):
	if not frappe.db.exists("User", email):
		user = frappe.new_doc("User")
		user.update({"email": email, "first_name": email.split("@")[0], "send_welcome_email": 0})
		user.append("roles", {"role": role})
		user.insert(ignore_permissions=True)
	return email


def _tickets(count: int) -> list[str]:
	return [make_ticket(subject=f"ERPAI-TEST review {n}").name for n in range(count)]


def _new_month(tickets: list[str], month: str = MONTH, **fields):
	return frappe.get_doc(
		{
			"doctype": REVIEW_MONTH,
			"month": month,
			"period_start": date(2001, 2, 1),
			"period_end": date(2001, 2, 28),
			"candidate_count": len(tickets),
			"items": [{"ticket": ticket} for ticket in tickets],
			**fields,
		}
	)


class ReviewMonthTestCase(FrappeTestCase):
	def setUp(self):
		self.assertTrue(frappe.db.exists("DocType", REVIEW_MONTH), "DocType ERP AI Review Month is missing")
		keep_agent_settings(self)
		# FrappeTestCase rolls back only after the whole class: undo each test's rows and users.
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")


class TestReviewMonth(ReviewMonthTestCase):
	def test_doctype_json_module_and_child_table(self):
		doctype = json.loads(JSON_PATH.read_text(encoding="utf-8"))
		self.assertEqual((doctype["name"], doctype["module"]), (REVIEW_MONTH, "ERP AI agent"))
		self.assertFalse(doctype.get("istable"))
		fields = {field["fieldname"]: field for field in doctype["fields"]}
		self.assertEqual(
			{name: field["fieldtype"] for name, field in fields.items() if "Break" not in field["fieldtype"]},
			{
				"month": "Data",
				"period_start": "Date",
				"period_end": "Date",
				"candidate_count": "Int",
				"items": "Table",
			},
		)
		self.assertEqual(fields["items"]["options"], REVIEW_ITEM)
		meta = frappe.get_meta(REVIEW_MONTH)
		self.assertEqual((meta.get_field("month").reqd, meta.get_field("month").unique), (1, 1))
		item = json.loads(ITEM_JSON_PATH.read_text(encoding="utf-8"))
		self.assertEqual(item["istable"], 1)
		item_fields = {field["fieldname"]: field for field in item["fields"]}
		self.assertEqual(
			{name: field["fieldtype"] for name, field in item_fields.items()},
			{
				"ticket": "Link",
				"verdict": "Select",
				"note": "Small Text",
				"reviewed_by": "Link",
				"reviewed_at": "Datetime",
			},
		)
		self.assertEqual(item_fields["ticket"]["options"], "HD Ticket")
		self.assertEqual(item_fields["verdict"]["options"], "\nĐúng\nSai")
		for name in ("ticket", "reviewed_by", "reviewed_at"):
			self.assertEqual(item_fields[name].get("read_only"), 1, name)

	def test_name_is_rev_month(self):
		doc = _new_month(_tickets(2)).insert()
		self.assertEqual(doc.name, f"REV-{MONTH}")
		with self.assertRaises(frappe.DuplicateEntryError):
			_new_month(_tickets(1)).insert()

	def test_permissions_read_write_only(self):
		doctype = json.loads(JSON_PATH.read_text(encoding="utf-8"))
		granted = {
			row["role"]: {
				right for right, value in row.items() if right not in ("role", "permlevel") and value
			}
			for row in doctype["permissions"]
		}
		self.assertEqual(granted, GRANTED)
		stored = frappe.get_all("DocPerm", filters={"parent": REVIEW_MONTH}, fields=["role", *RIGHTS])
		self.assertEqual({row.role: {r for r in RIGHTS if row.get(r)} for row in stored}, GRANTED)

	def test_verdict_sets_reviewer(self):
		tickets = _tickets(3)
		_new_month(tickets).insert()
		user = _make_user(INSTRUCTOR_USER, ROLE_INSTRUCTOR)
		frappe.set_user(user)
		doc = frappe.get_doc(REVIEW_MONTH, f"REV-{MONTH}")
		self.assertTrue(all(not row.reviewed_by for row in doc.items))
		doc.items[0].verdict = "Đúng"
		doc.items[2].note = "Cần xem lại"
		doc.save()

		doc = frappe.get_doc(REVIEW_MONTH, f"REV-{MONTH}")
		self.assertEqual([row.reviewed_by for row in doc.items], [user, None, user])
		self.assertTrue(doc.items[0].reviewed_at and doc.items[2].reviewed_at)
		self.assertFalse(doc.items[1].reviewed_at)
		first_at = doc.items[0].reviewed_at
		# Saving again with nothing changed leaves the reviewer and time alone.
		doc.save()
		self.assertEqual(frappe.get_doc(REVIEW_MONTH, doc.name).items[0].reviewed_at, first_at)

	def test_ticket_list_locked(self):
		tickets = _tickets(3)
		extra = _tickets(1)[0]
		_new_month(tickets).insert()
		for label, change in (
			("remove", lambda doc: doc.items.pop()),
			("add", lambda doc: doc.append("items", {"ticket": extra})),
			("swap", lambda doc: setattr(doc.items[0], "ticket", extra)),
			("reorder", lambda doc: doc.set("items", list(reversed(doc.items)))),
		):
			with self.subTest(change=label):
				doc = frappe.get_doc(REVIEW_MONTH, f"REV-{MONTH}")
				change(doc)
				with self.assertRaisesRegex(frappe.ValidationError, LOCKED_MESSAGE):
					doc.save()
		self.assertEqual(
			frappe.get_all(REVIEW_ITEM, filters={"parent": f"REV-{MONTH}"}, order_by="idx", pluck="ticket"),
			tickets,
		)

	def test_manager_cannot_create_or_delete(self):
		doc = _new_month(_tickets(1)).insert()
		user = _make_user(MANAGER_USER, "System Manager")
		for ptype in ("create", "delete"):
			self.assertFalse(frappe.has_permission(REVIEW_MONTH, ptype, doc=doc, user=user), ptype)
		self.assertTrue(frappe.has_permission(REVIEW_MONTH, "write", doc=doc, user=user))


class TestReviewMonthAgentGuard(ReviewMonthTestCase):
	def test_scheduler_session_creates(self):
		# A scheduled job runs as Administrator (ADR-033 QĐ 7: the review job writes the row).
		self.assertEqual(frappe.session.user, "Administrator")
		doc = _new_month(_tickets(2), month=NEXT_MONTH).insert()
		self.assertEqual(frappe.db.get_value(REVIEW_MONTH, doc.name, "owner"), "Administrator")
		self.assertEqual(frappe.db.count(REVIEW_ITEM, {"parent": doc.name}), 2)

	def test_reviewer_session_writes_verdict(self):
		_new_month(_tickets(2)).insert()
		frappe.set_user(_make_user(INSTRUCTOR_USER, ROLE_INSTRUCTOR))
		doc = frappe.get_doc(REVIEW_MONTH, f"REV-{MONTH}")
		doc.items[1].verdict = "Sai"
		doc.save()
		self.assertEqual(frappe.get_doc(REVIEW_MONTH, doc.name).items[1].verdict, "Sai")

	def test_every_guarded_hook_refuses_agent(self):
		doc = _new_month(_tickets(2)).insert()
		# The ticket list is changed too: the refusal must come before the lock check.
		doc.items.pop()
		frappe.set_user(AGENT_USER)
		for hook in GUARDED_HOOKS:
			with self.subTest(hook=hook):
				with self.assertRaisesRegex(frappe.PermissionError, REFUSAL):
					doc.run_method(hook, *HOOK_ARGUMENTS.get(hook, ()))
		source = CONTROLLER_PATH.read_text(encoding="utf-8")
		self.assertEqual(source.count("refuse_agent_write(self)"), len(GUARDED_HOOKS))
		self.assertNotIn("allow_agent_write", source)

	def test_agent_insert_save_delete_refused(self):
		doc = _new_month(_tickets(2)).insert()
		frappe.set_user(AGENT_USER)
		paths = {
			"insert": lambda: _new_month(_tickets(1), month=NEXT_MONTH).insert(ignore_permissions=True),
			"save": lambda: _set_verdict(doc.name),
			"delete": lambda: frappe.delete_doc(REVIEW_MONTH, doc.name, ignore_permissions=True),
		}
		for path, write in paths.items():
			with self.subTest(path=path):
				frappe.db.savepoint("erp_ai_review_month_guard")
				with self.assertRaisesRegex(frappe.PermissionError, REFUSAL):
					write()
				frappe.db.rollback(save_point="erp_ai_review_month_guard")
		frappe.set_user("Administrator")
		self.assertTrue(frappe.db.exists(REVIEW_MONTH, doc.name))
		self.assertFalse(frappe.db.exists(REVIEW_MONTH, f"REV-{NEXT_MONTH}"))
		self.assertFalse(frappe.get_doc(REVIEW_MONTH, doc.name).items[0].verdict)


def _set_verdict(name: str) -> None:
	doc = frappe.get_doc(REVIEW_MONTH, name)
	doc.items[0].verdict = "Đúng"
	doc.save(ignore_permissions=True)


class TestVerdictLessons(ReviewMonthTestCase):
	"""A monthly-review verdict "Sai" becomes one "don't do this" lesson (FEAT-008 AC-11)."""

	def setUp(self):
		frappe.db.rollback()
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("test must not commit"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		super().setUp()
		set_agent_settings(enabled=0, lessons_enabled=1, excluded_teams="", excluded_title_prefixes="")
		self.ticket = _tickets(1)[0]
		self.month = _new_month([self.ticket]).insert(ignore_permissions=True)

	def _judge(self, verdict, note=""):
		doc = frappe.get_doc(REVIEW_MONTH, self.month.name)
		doc.items[0].verdict = verdict
		doc.items[0].note = note
		doc.save(ignore_permissions=True)

	def _lessons(self):
		return frappe.get_all(
			LESSON_DOCTYPE,
			filters={"ticket": self.ticket},
			fields=["lesson_source", "lesson_status", "lesson_text"],
		)

	def test_sai_verdict_makes_lesson_with_note(self):
		self._judge("Sai", f"Phải là nhóm IT, khóa {FAKE_KEY}")
		(lesson,) = self._lessons()
		self.assertEqual(
			(lesson.lesson_source, lesson.lesson_status), ("Kết quả duyệt và rà soát", "Đang dùng")
		)
		self.assertTrue(lesson.lesson_text.startswith("Đừng làm như vậy"))
		self.assertIn("Phải là nhóm IT", lesson.lesson_text)
		self.assertNotIn("sk-ant-api03-", lesson.lesson_text)

	def test_dung_or_blank_makes_none(self):
		self._judge("Đúng")
		self._judge("")
		self.assertEqual(self._lessons(), [])

	def test_sai_twice_makes_one(self):
		self._judge("Sai", "lần một")
		self._judge("Đúng")
		self._judge("Sai", "lần hai")
		self.assertEqual(len(self._lessons()), 1)
