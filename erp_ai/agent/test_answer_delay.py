from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from erp_ai.agent import answer_delay
from erp_ai.agent.answer_delay import AnswerDelay
from erp_ai.constants import ANSWER_DELAY_MAX_S


class TestAnswerDelay(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self.clock = [100.0]
		self.sleeps = []

		def fake_sleep(seconds):
			self.sleeps.append(seconds)
			self.clock[0] += seconds

		for target, fake in (
			("_now", lambda: self.clock[0]),
			("_sleep", fake_sleep),
			("_pick", lambda low, high: high),
		):
			patcher = patch.object(answer_delay, target, fake)
			patcher.start()
			self.addCleanup(patcher.stop)

	def test_full_delay_when_model_instant(self):
		delay = AnswerDelay.start(4, 4)
		waited = delay.wait_before_answer(deadline=self.clock[0] + 600)
		self.assertEqual(self.sleeps, [4])
		self.assertEqual(waited, 4)
		self.assertEqual(delay.waited_s, 4)

	def test_delay_always_within_min_max(self):
		picks = []

		def record(low, high):
			picks.append((low, high))
			return answer_delay.random.uniform(low, high)

		with patch.object(answer_delay, "_pick", record):
			for _ in range(50):
				delay = AnswerDelay.start(1, 4)
				self.assertGreaterEqual(delay.delay_s, 1)
				self.assertLessEqual(delay.delay_s, 4)
		self.assertEqual(picks, [(1, 4)] * 50)

	def test_fixed_delay_when_min_equals_max(self):
		for _ in range(10):
			self.assertEqual(AnswerDelay.start(3, 3).delay_s, 3)

	def test_no_wait_when_model_slower_than_delay(self):
		delay = AnswerDelay.start(3, 3)
		self.clock[0] += 10
		waited = delay.wait_before_answer(deadline=self.clock[0] + 600)
		self.assertEqual(self.sleeps, [])
		self.assertEqual(waited, 0)

	def test_no_wait_when_zero_zero(self):
		delay = AnswerDelay.start(0, 0)
		self.assertEqual(delay.wait_before_answer(deadline=self.clock[0] + 600), 0)
		self.assertEqual(self.sleeps, [])

	def test_wait_capped_by_run_deadline(self):
		delay = AnswerDelay.start(10, 10)
		waited = delay.wait_before_answer(deadline=self.clock[0] + 2)
		self.assertEqual(self.sleeps, [2])
		self.assertEqual(waited, 2)
		self.assertEqual(self.clock[0], 102.0)

	def test_waits_only_once(self):
		delay = AnswerDelay.start(5, 5)
		self.clock[0] += 1
		self.assertEqual(delay.wait_before_answer(deadline=self.clock[0] + 600), 4)
		self.assertEqual(delay.wait_before_answer(deadline=self.clock[0] + 600), 0)
		self.assertEqual(self.sleeps, [4])
		self.assertEqual(delay.waited_s, 4)

	def test_out_of_range_db_values_are_clamped(self):
		delay = AnswerDelay.start(-5, 99)
		self.assertEqual(delay.delay_s, ANSWER_DELAY_MAX_S)
		self.assertEqual(AnswerDelay.start(None, None).delay_s, 0)
		# min > max is reordered: _pick receives (2, 9), never (9, 2)
		calls = []
		with patch.object(answer_delay, "_pick", lambda low, high: calls.append((low, high)) or low):
			AnswerDelay.start(9, 2)
		self.assertEqual(calls, [(2, 9)])
