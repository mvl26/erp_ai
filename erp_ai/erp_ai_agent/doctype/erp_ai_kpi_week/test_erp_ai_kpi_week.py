import json
from datetime import date
from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.constants import ROLE_INSTRUCTOR
from erp_ai.test_utils import keep_agent_settings

KPI_WEEK_DOCTYPE = "ERP AI KPI Week"
JSON_PATH = Path(__file__).resolve().parent / "erp_ai_kpi_week.json"
# Mondays far before any real ticket on the shared site.
WEEK = date(2001, 1, 1)
NEXT_WEEK = date(2001, 1, 8)
INSTRUCTOR_USER = "erp-ai-kpi-week-instructor@example.com"
MANAGER_USER = "erp-ai-kpi-week-manager@example.com"
# FEAT-007 design.md:256-268: the data fields and their types.
FIELD_TYPES = {
	"week_start": "Date",
	"week_end": "Date",
	"computed_at": "Datetime",
	"first_response_median_min": "Float",
	"first_response_within_15_pct": "Percent",
	"first_response_within_5_pct": "Percent",
	"first_response_sample": "Int",
	"complete_fields_pct": "Percent",
	"complete_fields_sample": "Int",
	"closed_without_human_pct": "Percent",
	"closed_sample": "Int",
	"b_resolution_avg_hours": "Float",
	"b_resolution_sample": "Int",
	"c_task_in_3_days_pct": "Percent",
	"c_task_sample": "Int",
	"stale_over_5_days": "Int",
	"stale_over_7_days": "Int",
}
RIGHTS = ("read", "write", "create", "delete", "submit", "cancel", "amend", "report", "export", "import")
# design.md:270: read and report only; nobody creates, writes or deletes.
GRANTED = {"System Manager": {"read", "report"}, ROLE_INSTRUCTOR: {"read", "report"}}


def _new_week(week_start=WEEK, **fields):
	return frappe.get_doc({"doctype": KPI_WEEK_DOCTYPE, "week_start": week_start, **fields})


def _make_user(email, role):
	user = frappe.new_doc("User")
	user.update({"email": email, "first_name": email.split("@")[0], "send_welcome_email": 0})
	user.append("roles", {"role": role})
	user.insert(ignore_permissions=True)
	return user.name


class KpiWeekTestCase(FrappeTestCase):
	def setUp(self):
		self.assertTrue(frappe.db.exists("DocType", KPI_WEEK_DOCTYPE), "DocType ERP AI KPI Week is missing")
		keep_agent_settings(self)
		# FrappeTestCase rolls back only after the whole class: undo each test's rows and users.
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")


class TestKpiWeek(KpiWeekTestCase):
	def test_doctype_json_fields_and_module(self):
		doctype = json.loads(JSON_PATH.read_text(encoding="utf-8"))
		self.assertEqual(doctype["name"], KPI_WEEK_DOCTYPE)
		self.assertEqual(doctype["module"], "ERP AI agent")
		self.assertFalse(doctype.get("istable"))
		self.assertFalse(doctype.get("is_submittable"))
		self.assertFalse(doctype.get("autoname"))
		data_fields = {
			field["fieldname"]: field["fieldtype"]
			for field in doctype["fields"]
			if field["fieldtype"] not in ("Section Break", "Column Break", "Tab Break")
		}
		self.assertEqual(data_fields, FIELD_TYPES)
		week_start = frappe.get_meta(KPI_WEEK_DOCTYPE).get_field("week_start")
		self.assertEqual((week_start.reqd, week_start.unique), (1, 1))

	def test_name_is_kpi_and_week_start_iso(self):
		doc = _new_week().insert()
		self.assertEqual(doc.name, "KPI-2001-01-01")
		self.assertEqual(_new_week("2001-01-08").insert().name, "KPI-2001-01-08")

	def test_duplicate_week_raises_duplicate_entry(self):
		first = _new_week(first_response_sample=3).insert()
		with self.assertRaises(frappe.DuplicateEntryError):
			_new_week(first_response_sample=4).insert()
		self.assertEqual(frappe.db.count(KPI_WEEK_DOCTYPE, {"week_start": WEEK}), 1)
		self.assertEqual(frappe.db.get_value(KPI_WEEK_DOCTYPE, first.name, "first_response_sample"), 3)
		self.assertEqual(_new_week(NEXT_WEEK).insert().name, "KPI-2001-01-08")

	def test_week_start_is_unique_in_the_table(self):
		# The cycle key holds on its own (ADR-033 QĐ 6), not only through the name.
		_new_week().insert()
		other = _new_week()
		other.name = "KPI-other-name"
		with self.assertRaises(frappe.UniqueValidationError):
			other.db_insert()
		self.assertEqual(frappe.db.count(KPI_WEEK_DOCTYPE, {"week_start": WEEK}), 1)

	def test_week_start_required(self):
		with self.assertRaises(frappe.MandatoryError):
			frappe.get_doc({"doctype": KPI_WEEK_DOCTYPE}).insert()

	def test_permissions_read_report_only(self):
		doctype = json.loads(JSON_PATH.read_text(encoding="utf-8"))
		granted = {
			row["role"]: {
				right for right, value in row.items() if right not in ("role", "permlevel") and value
			}
			for row in doctype["permissions"]
		}
		self.assertEqual(granted, GRANTED)
		stored = frappe.get_all("DocPerm", filters={"parent": KPI_WEEK_DOCTYPE}, fields=["role", *RIGHTS])
		self.assertEqual(
			{row.role: {right for right in RIGHTS if row.get(right)} for row in stored},
			GRANTED,
		)
		self.assertEqual(len(stored), 2)

	def test_instructor_and_manager_read_but_cannot_change(self):
		doc = _new_week().insert()
		for email, role in ((INSTRUCTOR_USER, ROLE_INSTRUCTOR), (MANAGER_USER, "System Manager")):
			user = _make_user(email, role)
			with self.subTest(role=role):
				for ptype in ("read", "report"):
					self.assertTrue(frappe.has_permission(KPI_WEEK_DOCTYPE, ptype, user=user), ptype)
				for ptype in ("create", "write", "delete"):
					self.assertFalse(frappe.has_permission(KPI_WEEK_DOCTYPE, ptype, user=user), ptype)
					self.assertFalse(
						frappe.has_permission(KPI_WEEK_DOCTYPE, ptype, doc=doc, user=user), ptype
					)
		frappe.set_user(INSTRUCTOR_USER)
		with self.assertRaises(frappe.PermissionError):
			_new_week(NEXT_WEEK).insert()
		self.assertFalse(frappe.db.exists(KPI_WEEK_DOCTYPE, {"week_start": NEXT_WEEK}))


class TestKpiWeekAgentGuard(KpiWeekTestCase):
	def test_scheduler_session_inserts(self):
		# A scheduled job runs as Administrator (ADR-033 QĐ 7: the KPI job writes the rows).
		self.assertEqual(frappe.session.user, "Administrator")
		doc = _new_week(week_end=date(2001, 1, 7), first_response_sample=0, stale_over_5_days=2).insert()
		stored = frappe.db.get_value(
			KPI_WEEK_DOCTYPE,
			doc.name,
			["week_start", "week_end", "first_response_sample", "stale_over_5_days", "owner"],
			as_dict=True,
		)
		self.assertEqual(
			stored,
			{
				"week_start": WEEK,
				"week_end": date(2001, 1, 7),
				"first_response_sample": 0,
				"stale_over_5_days": 2,
				"owner": "Administrator",
			},
		)
