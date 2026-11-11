from datetime import datetime
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai import hooks, tasks
from erp_ai.constants import CREDENTIAL_DOCTYPE, LOG_DOCTYPE, SETTING_DOCTYPE, TRIGGER_TICKET_INSERT
from erp_ai.test_utils import add_credential, set_agent_settings

NOW = datetime(2026, 11, 15, 8, 0, 0)
THIS_MONTH = datetime(2026, 11, 3, 9, 0, 0)
LAST_MONTH = datetime(2026, 10, 31, 23, 59, 59)
FIRST_OF_MONTH = datetime(2026, 11, 1, 0, 0, 0)
NEXT_MONTH = datetime(2026, 12, 1, 0, 0, 0)


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
		log_error.start()
		self.addCleanup(log_error.stop)
		set_agent_settings(spent_this_month_usd=99)
		self.row_a = add_credential("ERPAI-TEST-A", spent_month_usd=77)
		self.row_b = add_credential("ERPAI-TEST-B", spent_month_usd=55)

	def _spent_total(self):
		return frappe.db.get_single_value(SETTING_DOCTYPE, "spent_this_month_usd")

	def _spent_key(self, row):
		return frappe.db.get_value(CREDENTIAL_DOCTYPE, row, "spent_month_usd")

	def test_recompute_spend_from_log(self):
		_add_log(0.25, "ERPAI-TEST-A", THIS_MONTH)
		_add_log(0.5, "ERPAI-TEST-A", FIRST_OF_MONTH)
		_add_log(1.125, "ERPAI-TEST-B", THIS_MONTH)
		_add_log(0.0625, "", THIS_MONTH)

		tasks.recompute_monthly_spend(now=NOW)

		self.assertAlmostEqual(self._spent_total(), 1.9375, places=6)
		self.assertAlmostEqual(self._spent_key(self.row_a), 0.75, places=6)
		self.assertAlmostEqual(self._spent_key(self.row_b), 1.125, places=6)

	def test_month_start_resets_to_zero(self):
		_add_log(3.0, "ERPAI-TEST-A", LAST_MONTH)

		tasks.recompute_monthly_spend(now=datetime(2026, 11, 1, 0, 5, 0))

		self.assertEqual(self._spent_total(), 0)
		self.assertEqual(self._spent_key(self.row_a), 0)
		self.assertEqual(self._spent_key(self.row_b), 0)

	def test_only_logs_of_the_month_of_now_count(self):
		_add_log(3.0, "ERPAI-TEST-A", LAST_MONTH)
		_add_log(0.5, "ERPAI-TEST-A", THIS_MONTH)

		tasks.recompute_monthly_spend(now=NOW)

		self.assertAlmostEqual(self._spent_total(), 0.5, places=6)
		self.assertAlmostEqual(self._spent_key(self.row_a), 0.5, places=6)

	def test_logs_after_the_month_of_now_are_not_counted(self):
		_add_log(2.0, "ERPAI-TEST-A", NEXT_MONTH)
		_add_log(0.5, "ERPAI-TEST-A", THIS_MONTH)

		tasks.recompute_monthly_spend(now=NOW)

		self.assertAlmostEqual(self._spent_total(), 0.5, places=6)

	def test_label_without_credential_row_does_not_break_and_key_without_log_gets_zero(self):
		_add_log(0.5, "ERPAI-TEST-GONE", THIS_MONTH)

		tasks.recompute_monthly_spend(now=NOW)

		self.assertAlmostEqual(self._spent_total(), 0.5, places=6)
		self.assertEqual(self._spent_key(self.row_a), 0)
		self.assertEqual(self._spent_key(self.row_b), 0)

	def test_default_now_is_current_time(self):
		_add_log(0.5, "ERPAI-TEST-A", frappe.utils.now_datetime())

		tasks.recompute_monthly_spend()

		self.assertAlmostEqual(self._spent_total(), 0.5, places=6)

	def test_hook_registered_in_daily_scheduler(self):
		self.assertIn("erp_ai.tasks.recompute_monthly_spend", hooks.scheduler_events["daily"])
