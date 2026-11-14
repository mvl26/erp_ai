import itertools
import json
from datetime import datetime, timedelta
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, now_datetime

from erp_ai.constants import CATEGORIES, LOG_DOCTYPE
from erp_ai.erp_ai_agent.report.erp_ai_accuracy.erp_ai_accuracy import (
	GATE_MIN_ACCURACY,
	GATE_MIN_SAMPLE,
	GATE_WINDOW_DAYS,
	GateResult,
	execute,
	l0_l1_gate,
)
from erp_ai.test_utils import keep_agent_settings, make_log_entry

PREFIX = "ERPAI-TEST-"
REPORT = "ERP AI Accuracy"
PLAIN_USER = "erp-ai-accuracy-plain@example.com"
PREDICTED = {"ticket_type": "T1", "agent_group": "G1", "priority": "Low"}
COLUMN_FIELDS = ["category", "predictions", "labeled", "correct", "accuracy_pct", "failed_runs"]
DAY = timedelta(days=1)
TICKET_NUMBERS = itertools.count(1)


class AccuracyTestCase(FrappeTestCase):
	def setUp(self):
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("test must not commit"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		# ERP AI Log cannot be deleted: every row made here is undone by the rollback.
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		# Rows from real use of the site must not reach the report: hide every existing prediction
		# inside this transaction (rolled back in cleanup), so the rows made by the test are the only ones.
		frappe.db.sql(f"update `tab{LOG_DOCTYPE}` set entry_type = 'reason' where entry_type = 'classify'")
		self.now = now_datetime().replace(microsecond=0)

	def _log(self, category, days_ago, corrected_after=None, corrected_to=None, entry_type="classify"):
		"""One log row of a new ticket created `days_ago` days ago; `corrected_after` (timedelta) sets the
		correction time."""
		name = make_log_entry(
			run_id=f"{PREFIX}{category}",
			entry_type=entry_type,
			predicted_category=category,
			predicted_ticket_type=PREDICTED["ticket_type"],
			predicted_agent_group=PREDICTED["agent_group"],
			predicted_priority=PREDICTED["priority"],
		)
		created = self.now - timedelta(days=days_ago)
		values = {"creation": created, "ticket": f"{PREFIX}{next(TICKET_NUMBERS)}"}
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
		# A: 3 predictions, 2 labeled by a correction (also after 7 days), both wrong
		self._log("A", 20)
		self._log("A", 20, corrected_after=2 * DAY, corrected_to={"priority": "High"})
		self._log("A", 20, corrected_after=9 * DAY, corrected_to={"priority": "High"})
		# B: set back to the predicted value is a correct label; a changed group is a wrong one; one silent
		self._log("B", 15, corrected_after=1 * DAY)
		self._log("B", 15, corrected_after=7 * DAY, corrected_to={"agent_group": "G2"})
		self._log("B", 3)
		# C
		self._log("C", 3, corrected_after=1 * DAY, corrected_to={"ticket_type": "T2"})
		self._log("C", 10)
		# D: only a silent prediction
		self._log("D", 2)
		# F
		self._log("F", 10, corrected_after=1 * DAY, corrected_to={"priority": "Urgent"})

	def test_accuracy_ten_log_sample(self):
		self._make_sample()
		rows = self._rows()
		# Hand-computed (AC-19: silence is no label): accuracy = correct / labeled * 100
		expected = {
			"A": (3, 2, 0, 0.0),
			"B": (3, 2, 1, 50.0),
			"C": (2, 1, 0, 0.0),
			"D": (1, 0, 0, None),
			"E": (0, 0, 0, None),
			"F": (1, 1, 0, 0.0),
			"Tổng": (10, 6, 1, 16.67),
		}
		self.assertEqual(list(rows), [*CATEGORIES, "Tổng"])
		for category, (predictions, labeled, correct, accuracy) in expected.items():
			with self.subTest(category=category):
				row = rows[category]
				self.assertEqual(row["predictions"], predictions)
				self.assertEqual(row["labeled"], labeled)
				self.assertEqual(row["correct"], correct)
				self.assertEqual(row["accuracy_pct"], accuracy)

	def test_correction_after_seven_days_is_still_a_label(self):
		self._log("A", 20, corrected_after=timedelta(days=7, seconds=1), corrected_to={"priority": "High"})
		row = self._rows()["A"]
		self.assertEqual((row["labeled"], row["correct"], row["accuracy_pct"]), (1, 0, 0.0))

	def test_correction_back_to_predicted_value_is_a_correct_label(self):
		self._log("A", 20, corrected_after=DAY)
		row = self._rows()["A"]
		self.assertEqual((row["labeled"], row["correct"], row["accuracy_pct"]), (1, 1, 100.0))

	def test_unparseable_correction_is_no_label(self):
		self._log("A", 20, corrected_after=DAY, corrected_to="not json")
		row = self._rows()["A"]
		self.assertEqual((row["labeled"], row["correct"]), (0, 0))

	def test_empty_predicted_or_label_value_is_not_compared(self):
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
				row = self._rows()["A"]
				self.assertEqual((row["labeled"], row["correct"]), (1, 1))
				frappe.db.set_value(LOG_DOCTYPE, name, "entry_type", "reason")

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
		fieldtypes = {column["fieldname"]: column["fieldtype"] for column in columns}
		self.assertEqual(fieldtypes["accuracy_pct"], "Percent")
		self.assertEqual(
			[fieldtypes[name] for name in ("predictions", "labeled", "correct", "failed_runs")], ["Int"] * 4
		)

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


class TestLabels(AccuracyTestCase):
	"""AC-19, D-9: a prediction is compared with the label typed at creation, else the label a person set later."""

	def setUp(self):
		super().setUp()
		keep_agent_settings(self)
		self.now = datetime(2026, 11, 10, 12, 0, 0)

	def _classify(
		self,
		ticket,
		category,
		days_ago=5,
		predicted=None,
		created_labels=None,
		corrected_to=None,
		entry_type="classify",
	):
		"""One row of `ticket` (`None` = no ticket); `category=None` is a failed run (no predicted category)."""
		prediction = PREDICTED if predicted is None else predicted
		name = make_log_entry(
			run_id=f"{PREFIX}{ticket}",
			entry_type=entry_type,
			predicted_category=category,
			**(
				{}
				if category is None
				else {f"predicted_{field}": value for field, value in prediction.items()}
			),
		)
		values = {"creation": self.now - timedelta(days=days_ago)}
		if ticket is not None:
			values["ticket"] = f"{PREFIX}{ticket}"
		if created_labels is not None:
			values["created_labels"] = json.dumps(created_labels)
		if corrected_to is not None:
			values["human_corrected_to"] = json.dumps(corrected_to)
		frappe.db.set_value(LOG_DOCTYPE, name, values, update_modified=False)
		return name

	def test_six_label_cases(self):
		# A, label typed at creation equal to the prediction: labeled and correct
		self._classify("created", "A", created_labels=PREDICTED)
		# B, no label at creation, a person changed the priority later: labeled and wrong
		self._classify("corrected", "B", corrected_to={**PREDICTED, "priority": "High"})
		# C, nobody labeled anything: not labeled, so neither correct nor wrong
		self._classify("silent", "C")
		# failed run: no predicted category; only in `failed_runs` of the total row
		self._classify("failed", None)
		# D, the bot left the group empty and a person set it: the group is not compared, the rest is equal
		self._classify(
			"d-blank-group",
			"D",
			predicted={**PREDICTED, "agent_group": ""},
			created_labels={**PREDICTED, "agent_group": "G9"},
		)
		# E, the label at creation equals the prediction, the later one differs: the label at creation wins
		self._classify(
			"two-labels", "E", created_labels=PREDICTED, corrected_to={**PREDICTED, "priority": "Urgent"}
		)
		rows = self._rows()
		expected = {
			# category: (predictions, labeled, correct, accuracy_pct, failed_runs)
			"A": (1, 1, 1, 100.0, None),
			"B": (1, 1, 0, 0.0, None),
			"C": (1, 0, 0, None, None),
			"D": (1, 1, 1, 100.0, None),
			"E": (1, 1, 1, 100.0, None),
			"F": (0, 0, 0, None, None),
			"Tổng": (5, 4, 3, 75.0, 1),
		}
		self.assertEqual(list(rows), [*CATEGORIES, "Tổng"])
		for category, numbers in expected.items():
			with self.subTest(category=category):
				row = rows[category]
				self.assertEqual(
					tuple(
						row.get(key)
						for key in ("predictions", "labeled", "correct", "accuracy_pct", "failed_runs")
					),
					numbers,
				)

	def _numbers(self, row):
		return tuple(row.get(key) for key in ("predictions", "labeled", "correct", "failed_runs"))

	def test_each_field_falls_back_to_the_later_label_on_its_own(self):
		# A: the label at creation has only the priority (equal); the later ticket type differs → wrong
		self._classify("partial", "A", created_labels={"priority": "Low"}, corrected_to={"ticket_type": "T2"})
		# B: an empty priority at creation is no label; the later priority differs → wrong
		self._classify(
			"empty-created", "B", created_labels={"priority": ""}, corrected_to={"priority": "High"}
		)
		rows = self._rows()
		self.assertEqual(self._numbers(rows["A"]), (1, 1, 0, None))
		self.assertEqual(self._numbers(rows["B"]), (1, 1, 0, None))

	def test_label_only_for_a_field_the_bot_left_empty_is_no_label(self):
		self._classify(
			"group-only",
			"D",
			predicted={**PREDICTED, "agent_group": ""},
			created_labels={"agent_group": "G9"},
			corrected_to={"agent_group": "G8"},
		)
		row = self._rows()["D"]
		self.assertEqual((row["labeled"], row["correct"], row["accuracy_pct"]), (0, 0, None))

	def test_only_the_first_successful_row_of_a_ticket_counts(self):
		# one ticket: a failed run, then a correct A, then a wrong B; only the A row counts, no failed run
		self._classify("rerun", None, days_ago=6)
		self._classify("rerun", "A", days_ago=5, created_labels=PREDICTED)
		self._classify("rerun", "B", days_ago=4, created_labels={"priority": "High"})
		# first success before the range (filter starts 60 days back): a later success in range does not count
		self._classify("old", "C", days_ago=70)
		self._classify("old", "C", days_ago=3)
		rows = self._rows()
		self.assertEqual(self._numbers(rows["A"]), (1, 1, 1, None))
		self.assertEqual(self._numbers(rows["B"]), (0, 0, 0, None))
		self.assertEqual(self._numbers(rows["C"]), (0, 0, 0, None))
		self.assertEqual(self._numbers(rows["Tổng"]), (1, 1, 1, 0))

	def test_failed_runs_count_tickets_without_success_in_the_range(self):
		self._classify("failed-twice", None, days_ago=5)
		self._classify("failed-twice", None, days_ago=4)
		# decoys: failed before the range, failed after the range end, success before the range,
		# another entry type, no ticket (failed and successful)
		self._classify("failed-before", None, days_ago=70)
		self._classify("failed-after", None, days_ago=-1)
		self._classify("succeeded-before", "A", days_ago=70)
		self._classify("succeeded-before", None, days_ago=5)
		self._classify("reason-row", None, entry_type="reason")
		self._classify(None, None)
		self._classify(None, "A")
		_, data = execute(self._filters())
		self.assertEqual([row["category"] for row in data], [*CATEGORIES, "Tổng"])
		self.assertEqual(self._numbers(data[-1]), (0, 0, 0, 1))
		self.assertEqual([row["failed_runs"] for row in data[:-1]], [None] * len(CATEGORIES))

	def test_failed_run_at_the_first_second_of_the_range_counts(self):
		# the filter starts at 00:00:00 of the day 60 days back; one second earlier is outside
		start = datetime.combine(getdate(self._filters()["from_date"]), datetime.min.time())
		for ticket, created in (("at-start", start), ("before-start", start - timedelta(seconds=1))):
			name = self._classify(ticket, None)
			frappe.db.set_value(LOG_DOCTYPE, name, "creation", created, update_modified=False)
		self.assertEqual(self._numbers(self._rows()["Tổng"]), (0, 0, 0, 1))


class TestGate(AccuracyTestCase):
	"""AC-18, design 3.5.3: verdict of the L0 → L1 gate over the 14 days before `now`."""

	def setUp(self):
		super().setUp()
		keep_agent_settings(self)
		self.now = datetime(2026, 11, 10, 12, 0, 0)

	def _classify(self, created, correct=True, labeled=True):
		"""A new ticket with one `classify` row created at `created`; its label equals the prediction when
		`correct`, else differs in the priority; `labeled=False` leaves it without a label."""
		ticket = f"{PREFIX}gate-{next(TICKET_NUMBERS)}"
		self._row(ticket, created, "A", correct if labeled else None)
		return ticket

	def _row(self, ticket, created, category, correct):
		name = make_log_entry(
			run_id=ticket,
			entry_type="classify",
			predicted_category=category,
			**(
				{}
				if category is None
				else {f"predicted_{field}": value for field, value in PREDICTED.items()}
			),
		)
		values = {"creation": created, "ticket": ticket}
		if correct is not None:
			values["created_labels"] = json.dumps(PREDICTED if correct else {**PREDICTED, "priority": "High"})
		frappe.db.set_value(LOG_DOCTYPE, name, values, update_modified=False)

	def _sample(self, labeled, correct, days_ago=3):
		for index in range(labeled):
			self._classify(self.now - timedelta(days=days_ago), correct=index < correct)

	def _gate(self):
		result = l0_l1_gate(self.now)
		return result.verdict, result.labeled, result.correct

	def test_constants_are_the_documented_numbers(self):
		self.assertEqual((GATE_WINDOW_DAYS, GATE_MIN_SAMPLE, GATE_MIN_ACCURACY), (14, 30, 0.85))

	def test_not_enough_sample_29(self):
		self._sample(29, 29)
		# unlabeled tickets are not in the sample of 30
		for _ in range(5):
			self._classify(self.now - DAY, labeled=False)
		self.assertEqual(self._gate(), ("Chưa đủ mẫu", 29, 29))

	def test_no_sample_at_all(self):
		self.assertEqual(self._gate(), ("Chưa đủ mẫu", 0, 0))

	def test_pass_exactly_85(self):
		self._sample(40, 34)
		self.assertEqual(self._gate(), ("Đạt", 40, 34))

	def test_fail_82_5(self):
		self._sample(40, 33)
		self.assertEqual(self._gate(), ("Chưa đạt", 40, 33))

	def test_pass_30_26(self):
		self._sample(30, 26)
		self.assertEqual(self._gate(), ("Đạt", 30, 26))

	def test_fail_30_25(self):
		self._sample(30, 25)
		self.assertEqual(self._gate(), ("Chưa đạt", 30, 25))

	def test_outside_window_ignored(self):
		start = self.now - timedelta(days=14)
		second = timedelta(seconds=1)
		self._sample(30, 30)
		# in the window (now - 14 days, now]: one second after its start, and `now` itself (both wrong)
		self._classify(start + second, correct=False)
		self._classify(self.now, correct=False)
		# outside: exactly at its start, one second after `now`, well before it
		self._classify(start, correct=False)
		self._classify(self.now + second, correct=False)
		self._classify(self.now - timedelta(days=20), correct=False)
		self.assertEqual(self._gate(), ("Đạt", 32, 30))

	def test_window_uses_the_first_successful_row_of_each_ticket(self):
		self._sample(30, 30)
		# first success before the window, a later (wrong) success inside it: the ticket is not counted
		old = self._classify(self.now - timedelta(days=15))
		self._row(old, self.now - DAY, "B", correct=False)
		# a failed run before the window, then the first success inside it (wrong): the ticket counts
		late = f"{PREFIX}gate-late"
		self._row(late, self.now - timedelta(days=20), None, None)
		self._row(late, self.now - DAY, "A", correct=False)
		# first success inside the window is wrong, a later one is right: the first one decides
		rerun = self._classify(self.now - 2 * DAY, correct=False)
		self._row(rerun, self.now - DAY, "A", correct=True)
		self.assertEqual(self._gate(), ("Đạt", 32, 30))

	def test_rows_of_other_entry_types_are_ignored(self):
		self._sample(29, 29)
		# a full, correct prediction: only the `entry_type` keeps it out of the sample (else 30 of 30, "Đạt")
		name = make_log_entry(
			run_id=f"{PREFIX}gate-reason",
			entry_type="reason",
			predicted_category="A",
			**{f"predicted_{field}": value for field, value in PREDICTED.items()},
		)
		frappe.db.set_value(
			LOG_DOCTYPE,
			name,
			{
				"creation": self.now - DAY,
				"ticket": f"{PREFIX}gate-reason",
				"created_labels": json.dumps(PREDICTED),
			},
			update_modified=False,
		)
		self.assertEqual(self._gate(), ("Chưa đủ mẫu", 29, 29))

	def test_default_now_is_the_current_time(self):
		# far from the real clock, so the sample counts only when `now` comes from `now_datetime()`
		self.now = datetime(2020, 1, 1, 12, 0, 0)
		self._sample(30, 30, days_ago=0)
		with patch(
			"erp_ai.erp_ai_agent.report.erp_ai_accuracy.erp_ai_accuracy.now_datetime", return_value=self.now
		):
			result = l0_l1_gate()
		self.assertEqual(result, GateResult("Đạt", 30, 30))
