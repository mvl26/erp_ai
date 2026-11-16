from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai import hooks, schedules
from erp_ai.tests.test_architecture import ENQUEUE_TARGETS

# design.md:356-358: the 08:00 daily report, the Monday KPI, the day-1 review.
CRON = {
	"0 8 * * *": ("erp_ai.schedules.enqueue_daily_report", "enqueue_daily_report_job"),
	"0 8 * * 1": ("erp_ai.schedules.enqueue_weekly_kpi", "enqueue_weekly_kpi_job"),
	"0 8 1 * *": ("erp_ai.schedules.enqueue_monthly_review", "enqueue_monthly_review_job"),
}
JOB_TARGETS = (
	"erp_ai.agent.daily_report.run_daily_report",
	"erp_ai.agent.kpi.run_weekly_kpi",
	"erp_ai.agent.monthly_review.run_monthly_review",
)


class TestCron(FrappeTestCase):
	def test_cron_strings(self):
		cron = hooks.scheduler_events["cron"]
		for expression, (entry, _job) in CRON.items():
			with self.subTest(cron=expression):
				self.assertEqual(cron[expression], [entry])
		# T34 / U4a's key is still there.
		self.assertEqual(cron["*/15 * * * *"], ["erp_ai.agent.missed_scan.scan_missed_tickets"])

	def test_each_cron_calls_its_queue_function(self):
		for expression, (entry, job) in CRON.items():
			with self.subTest(cron=expression):
				with patch(f"erp_ai.agent.queue.{job}") as queued:
					frappe.get_attr(entry)()
				queued.assert_called_once_with()

	def test_job_targets_importable(self):
		for target in JOB_TARGETS:
			with self.subTest(target=target):
				self.assertIn(target, ENQUEUE_TARGETS)
				self.assertTrue(callable(frappe.get_attr(target)))

	def test_entry_points_do_not_enqueue_themselves(self):
		# F-2: the only `frappe.enqueue` calls live in agent/queue.py.
		with open(schedules.__file__, encoding="utf-8") as source:
			self.assertNotIn("frappe.enqueue", source.read())
