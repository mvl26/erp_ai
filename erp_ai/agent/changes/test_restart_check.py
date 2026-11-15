import calendar
import datetime
import os
import time
from types import SimpleNamespace
from unittest.mock import patch

import psutil
import redis
from frappe.tests.utils import FrappeTestCase

from erp_ai.agent.changes import restart_check
from erp_ai.constants import RESTART_STATUS_CONFIRMED, RESTART_STATUS_UNCONFIRMED, RESTART_TIMEOUT_S

SENT = 1_800_000_000.0
AFTER_DEADLINE = SENT + RESTART_TIMEOUT_S + 1
BEFORE_DEADLINE = SENT + 10
GET_WORKERS = "frappe.utils.background_jobs.get_workers"
SYSTEM_TZ = "Asia/Ho_Chi_Minh"
# A-6: restart_sent_at 10:00 in UTC+7 is 03:00:00 UTC.
SENT_LOCAL = datetime.datetime(2026, 11, 15, 10, 0, 0)
SENT_UTC_EPOCH = float(calendar.timegm((2026, 11, 15, 3, 0, 0)))
BIRTH_AFTER = datetime.datetime(2026, 11, 15, 3, 0, 1)
BIRTH_BEFORE = datetime.datetime(2026, 11, 15, 2, 59, 59)


def _worker(birth_date):
	return SimpleNamespace(birth_date=birth_date)


class TestOutcome(FrappeTestCase):
	def test_both_started_after_confirmed(self):
		self.assertEqual(
			restart_check.outcome(SENT, BEFORE_DEADLINE, SENT + 1, SENT + 2), RESTART_STATUS_CONFIRMED
		)
		self.assertEqual(
			restart_check.outcome(SENT, AFTER_DEADLINE, SENT + 1, SENT + 2), RESTART_STATUS_CONFIRMED
		)
		# Started exactly at the sent moment is not "after" it.
		self.assertIsNone(restart_check.outcome(SENT, BEFORE_DEADLINE, SENT, SENT + 2))
		self.assertIsNone(restart_check.outcome(SENT, BEFORE_DEADLINE, SENT + 2, SENT))

	def test_web_old_after_deadline_unconfirmed(self):
		self.assertEqual(
			restart_check.outcome(SENT, AFTER_DEADLINE, SENT - 1, SENT + 2), RESTART_STATUS_UNCONFIRMED
		)
		self.assertEqual(
			restart_check.outcome(SENT, AFTER_DEADLINE, SENT + 1, SENT - 2), RESTART_STATUS_UNCONFIRMED
		)
		self.assertEqual(restart_check.outcome(SENT, AFTER_DEADLINE, None, None), RESTART_STATUS_UNCONFIRMED)
		# The deadline itself is not yet past it.
		self.assertIsNone(restart_check.outcome(SENT, SENT + RESTART_TIMEOUT_S, SENT - 1, SENT + 2))

	def test_before_deadline_no_conclusion(self):
		self.assertIsNone(restart_check.outcome(SENT, BEFORE_DEADLINE, SENT - 1, SENT + 2))
		self.assertIsNone(restart_check.outcome(SENT, BEFORE_DEADLINE, SENT + 1, None))
		self.assertIsNone(restart_check.outcome(SENT, BEFORE_DEADLINE, None, SENT + 1))

	def test_redis_or_psutil_error_is_no_evidence(self):
		with patch(GET_WORKERS, side_effect=redis.exceptions.ConnectionError("down")):
			self.assertIsNone(restart_check.workers_started())
		with patch(GET_WORKERS, side_effect=psutil.NoSuchProcess(1)):
			self.assertIsNone(restart_check.workers_started())
		with patch(GET_WORKERS, return_value=[]):
			self.assertIsNone(restart_check.workers_started())
		with patch(GET_WORKERS, return_value=[_worker(BIRTH_AFTER), _worker(None)]):
			self.assertIsNone(restart_check.workers_started())
		with patch.object(restart_check.psutil, "Process", side_effect=psutil.NoSuchProcess(1)):
			self.assertIsNone(restart_check.web_started())
		with patch.object(restart_check.psutil, "Process", side_effect=psutil.AccessDenied(1)):
			self.assertIsNone(restart_check.web_started())
		# No evidence never confirms.
		self.assertIsNone(restart_check.outcome(SENT, BEFORE_DEADLINE, None, None))

	def test_programming_error_is_not_no_evidence(self):
		# ADR-040 C-3: only redis/psutil errors mean "no evidence"; a bug must propagate.
		with patch(GET_WORKERS, side_effect=ValueError("bug")):
			with self.assertRaises(ValueError):
				restart_check.workers_started()
		with patch.object(restart_check.psutil, "Process", side_effect=ValueError("bug")):
			with self.assertRaises(ValueError):
				restart_check.web_started()

	def test_evidence_sources(self):
		with patch(GET_WORKERS, return_value=[_worker(BIRTH_AFTER), _worker(BIRTH_BEFORE)]):
			self.assertEqual(restart_check.workers_started(), SENT_UTC_EPOCH - 1)
		with patch.object(restart_check.psutil, "Process") as process:
			process.return_value.create_time.return_value = 1234.5
			self.assertEqual(restart_check.web_started(), 1234.5)
		process.assert_called_once_with(os.getppid())


class TestEpoch(FrappeTestCase):
	def _set_tz(self, tz):
		patcher = patch.dict(os.environ, {"TZ": tz})
		patcher.start()
		self.addCleanup(time.tzset)
		self.addCleanup(patcher.stop)
		time.tzset()

	def test_rq_naive_utc_and_system_tz_compare_on_same_base(self):
		sent = restart_check.epoch_of_system_time(SENT_LOCAL, SYSTEM_TZ)
		after = restart_check.epoch_of_naive_utc(BIRTH_AFTER)
		before = restart_check.epoch_of_naive_utc(BIRTH_BEFORE)
		self.assertEqual(sent, SENT_UTC_EPOCH)
		self.assertEqual(after, SENT_UTC_EPOCH + 1)
		self.assertEqual(before, SENT_UTC_EPOCH - 1)
		self.assertEqual(restart_check.outcome(sent, sent + 10, after, after), RESTART_STATUS_CONFIRMED)
		self.assertIsNone(restart_check.outcome(sent, sent + 10, after, before))

	def test_independent_of_process_timezone(self):
		self._set_tz("UTC")
		in_utc = (
			restart_check.epoch_of_naive_utc(BIRTH_AFTER),
			restart_check.epoch_of_system_time(SENT_LOCAL, SYSTEM_TZ),
		)
		os.environ["TZ"] = "America/New_York"
		time.tzset()
		in_new_york = (
			restart_check.epoch_of_naive_utc(BIRTH_AFTER),
			restart_check.epoch_of_system_time(SENT_LOCAL, SYSTEM_TZ),
		)
		self.assertEqual(in_utc, (SENT_UTC_EPOCH + 1, SENT_UTC_EPOCH))
		self.assertEqual(in_new_york, in_utc)
