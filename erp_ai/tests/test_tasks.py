from datetime import datetime
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai import hooks, tasks
from erp_ai.constants import (
	CREDENTIAL_DOCTYPE,
	LOG_DOCTYPE,
	SETTING_DOCTYPE,
	TITLE_RUN_FAILED,
	TRIGGER_TICKET_INSERT,
)
from erp_ai.test_utils import add_credential, set_agent_settings

# Far-future months cannot hold real ERP AI Log rows, so sums only see rows the test inserts.
NOW = datetime(2031, 11, 15, 8, 0, 0)
THIS_MONTH = datetime(2031, 11, 3, 9, 0, 0)
LAST_MONTH = datetime(2031, 10, 31, 23, 59, 59)
FIRST_OF_MONTH = datetime(2031, 11, 1, 0, 0, 0)
NEXT_MONTH = datetime(2031, 12, 1, 0, 0, 0)


def _add_log(cost_usd, label, creation):
	"""Insert an ERP AI Log row inside the test transaction and back-date `creation`."""
	doc = frappe.get_doc(
		{
			"doctype": LOG_DOCTYPE,
			"run_id": "ERPAI-TEST-run",
			"entry_type": "skip",
			"trigger": TRIGGER_TICKET_INSERT,
			"turn": 0,
			"cost_usd": cost_usd,
			"credential_label": label,
		}
	).insert(ignore_permissions=True)
	frappe.db.set_value(LOG_DOCTYPE, doc.name, "creation", creation, update_modified=False)
	return doc.name


class TestRecomputeMonthlySpend(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("commit in test"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		log_error = patch("frappe.log_error")
		self.log_error = log_error.start()
		self.addCleanup(log_error.stop)
		self.label_a = f"ERPAI-TEST-{frappe.generate_hash(length=8)}"
		self.label_b = f"ERPAI-TEST-{frappe.generate_hash(length=8)}"
		set_agent_settings(spent_this_month_usd=99)
		self.row_a = add_credential(self.label_a, spent_month_usd=77)
		self.row_b = add_credential(self.label_b, spent_month_usd=55)

	def _spent_total(self):
		return frappe.db.get_single_value(SETTING_DOCTYPE, "spent_this_month_usd")

	def _spent_key(self, row):
		return frappe.db.get_value(CREDENTIAL_DOCTYPE, row, "spent_month_usd")

	def test_recompute_spend_from_log(self):
		_add_log(0.25, self.label_a, THIS_MONTH)
		_add_log(0.5, self.label_a, FIRST_OF_MONTH)
		_add_log(1.125, self.label_b, THIS_MONTH)
		_add_log(0.0625, "", THIS_MONTH)

		tasks.recompute_monthly_spend(now=NOW)

		self.assertAlmostEqual(self._spent_total(), 1.9375, places=6)
		self.assertAlmostEqual(self._spent_key(self.row_a), 0.75, places=6)
		self.assertAlmostEqual(self._spent_key(self.row_b), 1.125, places=6)

	def test_month_start_resets_to_zero(self):
		_add_log(3.0, self.label_a, LAST_MONTH)

		tasks.recompute_monthly_spend(now=datetime(2031, 11, 1, 0, 5, 0))

		self.assertEqual(self._spent_total(), 0)
		self.assertEqual(self._spent_key(self.row_a), 0)
		self.assertEqual(self._spent_key(self.row_b), 0)

	def test_only_logs_of_the_month_of_now_count(self):
		_add_log(3.0, self.label_a, LAST_MONTH)
		_add_log(0.5, self.label_a, THIS_MONTH)

		tasks.recompute_monthly_spend(now=NOW)

		self.assertAlmostEqual(self._spent_total(), 0.5, places=6)
		self.assertAlmostEqual(self._spent_key(self.row_a), 0.5, places=6)

	def test_logs_after_the_month_of_now_are_not_counted(self):
		_add_log(2.0, self.label_a, NEXT_MONTH)
		_add_log(0.5, self.label_a, THIS_MONTH)

		tasks.recompute_monthly_spend(now=NOW)

		self.assertAlmostEqual(self._spent_total(), 0.5, places=6)

	def test_label_without_credential_row_does_not_break_and_key_without_log_gets_zero(self):
		_add_log(0.5, f"{self.label_a}-gone", THIS_MONTH)

		tasks.recompute_monthly_spend(now=NOW)

		self.assertAlmostEqual(self._spent_total(), 0.5, places=6)
		self.assertEqual(self._spent_key(self.row_a), 0)
		self.assertEqual(self._spent_key(self.row_b), 0)

	def test_default_now_is_current_time(self):
		tasks.recompute_monthly_spend()
		baseline = self._spent_total()
		_add_log(0.5, self.label_a, frappe.utils.now_datetime())

		tasks.recompute_monthly_spend()

		self.assertAlmostEqual(self._spent_total() - baseline, 0.5, places=6)
		self.assertAlmostEqual(self._spent_key(self.row_a), 0.5, places=6)

	def test_null_credential_label_counts_in_total_only(self):
		_add_log(0.5, None, THIS_MONTH)
		_add_log(0.25, self.label_a, THIS_MONTH)

		tasks.recompute_monthly_spend(now=NOW)

		self.assertAlmostEqual(self._spent_total(), 0.75, places=6)
		self.assertAlmostEqual(self._spent_key(self.row_a), 0.25, places=6)
		self.assertEqual(self._spent_key(self.row_b), 0)

	def test_key_rows_are_written_without_touching_modified(self):
		modified_before = frappe.db.get_value(CREDENTIAL_DOCTYPE, self.row_a, "modified")
		_add_log(0.5, self.label_a, THIS_MONTH)

		tasks.recompute_monthly_spend(now=NOW)

		self.assertEqual(frappe.db.get_value(CREDENTIAL_DOCTYPE, self.row_a, "modified"), modified_before)

	def test_db_error_is_logged_and_rolled_back_not_raised(self):
		_add_log(0.5, self.label_a, THIS_MONTH)
		frappe.db.savepoint("t33_before_job")
		real_rollback = frappe.db.rollback

		def rollback_to_savepoint(*args, **kwargs):
			real_rollback(save_point="t33_before_job")

		with (
			patch.object(frappe.db, "set_value", side_effect=frappe.QueryTimeoutError("boom")),
			patch.object(frappe.db, "rollback", side_effect=rollback_to_savepoint) as rollback,
		):
			tasks.recompute_monthly_spend(now=NOW)

		rollback.assert_called_once()
		self.log_error.assert_called_once_with(
			TITLE_RUN_FAILED, "recompute_monthly_spend month=2031-11 error=QueryTimeoutError"
		)
		self.assertEqual(self._spent_total(), 99)
		self.assertEqual(self._spent_key(self.row_a), 77)
		self.assertEqual(self._spent_key(self.row_b), 55)

	def test_hook_registered_in_daily_scheduler(self):
		self.assertIn("erp_ai.tasks.recompute_monthly_spend", hooks.scheduler_events["daily"])
