import json
from datetime import datetime, timedelta
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, now_datetime

from erp_ai.constants import CATEGORIES, LOG_DOCTYPE
from erp_ai.erp_ai_agent.report.erp_ai_accuracy.erp_ai_accuracy import CORRECTION_WINDOW, execute
from erp_ai.test_utils import make_log_entry

PREFIX = "ERPAI-TEST-"
REPORT = "ERP AI Accuracy"
PLAIN_USER = "erp-ai-accuracy-plain@example.com"
PREDICTED = {"ticket_type": "T1", "agent_group": "G1", "priority": "Low"}
COLUMN_FIELDS = ["category", "predictions", "corrected", "pending", "accuracy_pct"]
DAY = timedelta(days=1)


class AccuracyTestCase(FrappeTestCase):
	def setUp(self):
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("test must not commit"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		# ERP AI Log cannot be deleted: every row made here is undone by the rollback.
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		self.now = now_datetime().replace(microsecond=0)

	def _log(self, category, days_ago, corrected_after=None, corrected_to=None, entry_type="classify"):
		"""One log row created `days_ago` days ago; `corrected_after` (timedelta) sets the correction time."""
		name = make_log_entry(
			run_id=f"{PREFIX}{category}",
			entry_type=entry_type,
			predicted_category=category,
			predicted_ticket_type=PREDICTED["ticket_type"],
			predicted_agent_group=PREDICTED["agent_group"],
			predicted_priority=PREDICTED["priority"],
		)
		created = self.now - timedelta(days=days_ago)
		values = {"creation": created}
		if corrected_after is not None:
			values["human_corrected_at"] = created + corrected_after
			values["human_corrected_to"] = (
				corrected_to
				if isinstance(corrected_to, str)
				else json.dumps({**PREDICTED, **(corrected_to or {})})
			)
		frappe.db.set_value(LOG_DOCTYPE, name, values, update_modified=False)
		return name

	def _filters(self):
		return {"from_date": add_days(getdate(self.now), -60), "to_date": getdate(self.now)}

	def _rows(self, filters=None):
		_, data = execute(filters or self._filters())
		return {row["category"]: row for row in data}


class TestAccuracyTenLogSample(AccuracyTestCase):
	def _make_sample(self):
		# A: 3 predictions, 1 corrected (a correction after 7 days does not count)
		self._log("A", 20)
		self._log("A", 20, corrected_after=2 * DAY, corrected_to={"priority": "High"})
		self._log("A", 20, corrected_after=9 * DAY, corrected_to={"priority": "High"})
		# B: set back to the predicted value is no correction; exactly 7 days still counts; one pending
		self._log("B", 15, corrected_after=1 * DAY)
		self._log("B", 15, corrected_after=7 * DAY, corrected_to={"agent_group": "G2"})
		self._log("B", 3)
		# C
		self._log("C", 3, corrected_after=1 * DAY, corrected_to={"ticket_type": "T2"})
		self._log("C", 10)
		# D: only a pending prediction
		self._log("D", 2)
		# F
		self._log("F", 10, corrected_after=1 * DAY, corrected_to={"priority": "Urgent"})

	def test_accuracy_ten_log_sample(self):
		self._make_sample()
		rows = self._rows()
		# Hand-computed: accuracy = (predictions - pending - corrected) / (predictions - pending) * 100
		expected = {
			"A": (3, 1, 0, 66.67),
			"B": (3, 1, 1, 50.0),
			"C": (2, 1, 0, 50.0),
			"D": (1, 0, 1, None),
			"E": (0, 0, 0, None),
			"F": (1, 1, 0, 0.0),
			"Tổng": (10, 4, 2, 50.0),
		}
		self.assertEqual(list(rows), [*CATEGORIES, "Tổng"])
		for category, (predictions, corrected, pending, accuracy) in expected.items():
			with self.subTest(category=category):
				row = rows[category]
				self.assertEqual(row["predictions"], predictions)
				self.assertEqual(row["corrected"], corrected)
				self.assertEqual(row["pending"], pending)
				self.assertEqual(row["accuracy_pct"], accuracy)

	def test_correction_after_seven_days_counts_as_correct(self):
		self._log("A", 20, corrected_after=timedelta(days=7, seconds=1), corrected_to={"priority": "High"})
		row = self._rows()["A"]
		self.assertEqual((row["corrected"], row["accuracy_pct"]), (0, 100.0))

	def test_correction_back_to_predicted_value_is_not_a_correction(self):
		self._log("A", 20, corrected_after=DAY)
		row = self._rows()["A"]
		self.assertEqual((row["corrected"], row["accuracy_pct"]), (0, 100.0))

	def test_unparseable_correction_counts_as_correction(self):
		self._log("A", 20, corrected_after=DAY, corrected_to="not json")
		self.assertEqual(self._rows()["A"]["corrected"], 1)

	def test_empty_predicted_and_corrected_values_are_equal(self):
		# NULL is what the database stores for an unset field; "" must count as the same "empty".
		cases = (
			("predicted empty string, corrected null", "", None),
			("predicted null, corrected empty string", None, ""),
		)
		for label, predicted, corrected in cases:
			with self.subTest(label):
				name = self._log("A", 20, corrected_after=DAY)
				frappe.db.set_value(
					LOG_DOCTYPE,
					name,
					{
						"predicted_agent_group": predicted,
						"human_corrected_to": json.dumps(
							{"ticket_type": "T1", "agent_group": corrected, "priority": "Low"}
						),
					},
				)
				self.assertEqual(self._rows()["A"]["corrected"], 0)
				frappe.db.set_value(LOG_DOCTYPE, name, "entry_type", "reason")

	def test_prediction_exactly_seven_days_old_is_no_longer_pending(self):
		with patch(f"{execute.__module__}.now_datetime", return_value=self.now):
			self._log("A", 7)
			self._log("B", 7, corrected_after=None)
			frappe.db.set_value(
				LOG_DOCTYPE,
				self._log("C", 0),
				"creation",
				self.now - (CORRECTION_WINDOW - timedelta(seconds=1)),
			)
			rows = self._rows()
		self.assertEqual((rows["A"]["pending"], rows["A"]["accuracy_pct"]), (0, 100.0))
		self.assertEqual((rows["C"]["pending"], rows["C"]["accuracy_pct"]), (1, None))

	def test_no_prediction_in_range_gives_empty_data(self):
		columns, data = execute(self._filters())
		self.assertEqual(data, [])
		self.assertEqual([column["fieldname"] for column in columns], COLUMN_FIELDS)

	def test_only_classify_rows_with_a_predicted_category_count(self):
		self._log("A", 20)
		self._log("B", 20, entry_type="reason")
		self._log("Z", 20)
		make_log_entry(run_id=f"{PREFIX}none", entry_type="classify")
		rows = self._rows()
		self.assertEqual(rows["Tổng"]["predictions"], 1)
		self.assertEqual(rows["B"]["predictions"], 0)


class TestAccuracyFiltersAndColumns(AccuracyTestCase):
	def test_date_range_is_inclusive_on_both_ends_by_creation(self):
		today = getdate(self.now)
		last_second = timedelta(hours=23, minutes=59, seconds=59)
		# A = first second of from_date, B = last second of to_date; C is the day before, D the day after
		placements = (
			("A", -10, timedelta()),
			("B", -5, last_second),
			("C", -11, last_second),
			("D", -4, timedelta()),
		)
		for category, offset, time_of_day in placements:
			name = self._log(category, 0)
			created = datetime.combine(add_days(today, offset), datetime.min.time()) + time_of_day
			frappe.db.set_value(LOG_DOCTYPE, name, "creation", created, update_modified=False)
		rows = self._rows({"from_date": add_days(today, -10), "to_date": add_days(today, -5)})
		self.assertEqual([rows[c]["predictions"] for c in "ABCD"], [1, 1, 0, 0])
		self.assertEqual(rows["Tổng"]["predictions"], 2)

	def test_columns_have_the_documented_fieldnames(self):
		columns, _ = execute(self._filters())
		self.assertEqual([column["fieldname"] for column in columns], COLUMN_FIELDS)
		self.assertEqual(columns[-1]["fieldtype"], "Percent")

	def test_missing_or_inverted_dates_are_rejected(self):
		today = getdate(self.now)
		bad_filters = (
			{},
			{"from_date": today},
			{"to_date": today},
			{"from_date": today, "to_date": add_days(today, -1)},
		)
		for filters in bad_filters:
			with self.subTest(filters=filters), self.assertRaises(frappe.ValidationError):
				execute(filters)

	def _plain_user(self):
		if not frappe.db.exists("User", PLAIN_USER):
			user = frappe.new_doc("User")
			user.update({"email": PLAIN_USER, "first_name": "plain", "send_welcome_email": 0})
			user.insert(ignore_permissions=True)
		return PLAIN_USER

	def test_user_without_report_permission_is_refused(self):
		frappe.set_user(self._plain_user())
		with self.assertRaises(frappe.PermissionError):
			execute(self._filters())

	def test_report_record_is_system_manager_only_script_report(self):
		report = frappe.get_doc("Report", REPORT)
		self.assertEqual(report.report_type, "Script Report")
		self.assertEqual(report.ref_doctype, LOG_DOCTYPE)
		self.assertEqual(report.module, "ERP AI agent")
		self.assertEqual([row.role for row in report.roles], ["System Manager"])
		self.assertEqual(report.is_standard, "Yes")
		self.assertTrue(frappe.has_permission("Report", doc=report, user="Administrator"))
