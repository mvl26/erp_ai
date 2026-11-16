from datetime import date

import frappe
from frappe.desk.query_report import run as run_report
from frappe.tests.utils import FrappeTestCase

from erp_ai.constants import KPI_IDS, ROLE_AGENT, ROLE_INSTRUCTOR
from erp_ai.erp_ai_agent.report.erp_ai_kpi_weekly.erp_ai_kpi_weekly import NO_DATA_LABEL, execute
from erp_ai.test_utils import keep_agent_settings

REPORT = "ERP AI KPI Weekly"
KPI_WEEK = "ERP AI KPI Week"
THIS_WEEK = date(2001, 1, 8)
LAST_WEEK = date(2001, 1, 1)
INSTRUCTOR_USER = "erp-ai-kpi-report-instructor@example.com"
AGENT_ONLY_USER = "erp-ai-kpi-report-agent@example.com"
SYSTEM_MANAGER_USER = "erp-ai-kpi-report-sysmanager@example.com"
COLUMNS = ["kpi", "this_week", "last_week", "target_gd2", "target_gd4", "unit"]
TARGETS = (
	"{"
	'"first_response_minutes": {"gd2": 15, "gd4": 5}, '
	'"complete_fields_pct": {"gd2": 100, "gd4": 100}, '
	'"closed_without_human_pct": {"gd2": 10, "gd4": 30}, '
	'"b_resolution_hours": {"gd2": 4, "gd4": 1.5}, '
	'"c_task_in_3_days_pct": {"gd2": 80, "gd4": 100}, '
	'"stale_over_5_days": {"gd2": 10, "gd4": 4}'
	"}"
)


def _make_user(email, role):
	if not frappe.db.exists("User", email):
		user = frappe.new_doc("User")
		user.update({"email": email, "first_name": email.split("@")[0], "send_welcome_email": 0})
		user.append("roles", {"role": role})
		user.insert(ignore_permissions=True)
	return email


class TestReport(FrappeTestCase):
	def setUp(self):
		keep_agent_settings(self)
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		# The shared site may hold real rows: this class sees only its own.
		frappe.db.delete(KPI_WEEK)
		frappe.db.set_single_value("ERP AI Setting", "kpi_targets", TARGETS)

	def _rows(self):
		frappe.get_doc(
			{
				"doctype": KPI_WEEK,
				"week_start": LAST_WEEK,
				"first_response_median_min": 9.25,
				"complete_fields_pct": 80,
				"b_resolution_avg_hours": None,
				"stale_over_5_days": 7,
			}
		).insert()
		frappe.get_doc(
			{
				"doctype": KPI_WEEK,
				"week_start": THIS_WEEK,
				"first_response_median_min": 4,
				"complete_fields_pct": 100,
				"closed_without_human_pct": 12.5,
				"b_resolution_avg_hours": 3.5,
				"c_task_in_3_days_pct": None,
				"stale_over_5_days": 0,
			}
		).insert()

	def test_six_rows_columns(self):
		self._rows()
		columns, data = execute({"week_start": THIS_WEEK})[:2]
		self.assertEqual([column["fieldname"] for column in columns], COLUMNS)
		self.assertTrue(all(column["fieldtype"] == "Data" for column in columns))
		self.assertEqual(len(data), 6)
		self.assertEqual(
			[(row["this_week"], row["last_week"]) for row in data],
			[
				("4", "9.3"),
				("100", "80"),
				("12.5", NO_DATA_LABEL),
				("3.5", NO_DATA_LABEL),
				(NO_DATA_LABEL, NO_DATA_LABEL),
				("0", "7"),
			],
		)
		self.assertEqual(
			[(row["target_gd2"], row["target_gd4"]) for row in data],
			[("15", "5"), ("100", "100"), ("10", "30"), ("4", "1.5"), ("80", "100"), ("10", "4")],
		)
		self.assertEqual([row["unit"] for row in data], ["phút", "%", "%", "giờ", "%", "phiếu"])
		self.assertEqual(len({row["kpi"] for row in data}), len(KPI_IDS))

	def test_default_week_is_the_newest_row(self):
		self._rows()
		data = execute({})[1]
		self.assertEqual(data[0]["this_week"], "4")
		self.assertEqual(data[0]["last_week"], "9.3")

	def test_no_row_means_no_data_everywhere(self):
		data = execute({"week_start": THIS_WEEK})[1]
		self.assertEqual(len(data), 6)
		self.assertEqual({(row["this_week"], row["last_week"]) for row in data}, {(NO_DATA_LABEL,) * 2})
		self.assertEqual(execute({})[1], data)

	def test_access_three_accounts(self):
		self._rows()
		report = frappe.get_doc("Report", REPORT)
		self.assertEqual(
			(report.report_type, report.ref_doctype, report.is_standard, report.module),
			("Script Report", KPI_WEEK, "Yes", "ERP AI agent"),
		)
		self.assertEqual(sorted(row.role for row in report.roles), [ROLE_INSTRUCTOR, "System Manager"])
		filters = {"week_start": str(THIS_WEEK)}

		frappe.set_user(_make_user(INSTRUCTOR_USER, ROLE_INSTRUCTOR))
		self.assertNotIn("System Manager", frappe.get_roles())
		self.assertEqual(len(run_report(REPORT, filters=filters)["result"]), 6)

		frappe.set_user(_make_user(AGENT_ONLY_USER, ROLE_AGENT))
		with self.assertRaises(frappe.PermissionError):
			run_report(REPORT, filters=filters)
		with self.assertRaises(frappe.PermissionError):
			execute(filters)

		frappe.set_user(_make_user(SYSTEM_MANAGER_USER, "System Manager"))
		self.assertNotIn(ROLE_INSTRUCTOR, frappe.get_roles())
		self.assertEqual(len(run_report(REPORT, filters=filters)["result"]), 6)
