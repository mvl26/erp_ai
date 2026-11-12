"""Answer delay of one agent run (design 3.4). Only the runner imports this module."""

import random
import time

from erp_ai.constants import ANSWER_DELAY_MAX_S


def _now() -> float:
	return time.monotonic()


def _sleep(seconds: float) -> None:
	time.sleep(seconds)


def _pick(low: float, high: float) -> float:
	return random.uniform(low, high)


class AnswerDelay:
	"""Random delay before the answer is released.

	Input: min/max seconds (clamped to 0..ANSWER_DELAY_MAX_S, reordered if min > max).
	Output: `delay_s` picked once at start; `wait_before_answer(deadline)` returns seconds slept.
	"""

	def __init__(self, delay_s: float, anchor: float):
		self.delay_s = delay_s
		self.anchor = anchor
		self.waited_s = 0.0
		self._done = False

	@classmethod
	def start(cls, low_s: float | None, high_s: float | None) -> "AnswerDelay":
		low, high = (min(max(v or 0, 0), ANSWER_DELAY_MAX_S) for v in (low_s, high_s))
		if low > high:
			low, high = high, low
		return cls(_pick(low, high), _now())

	def wait_before_answer(self, deadline: float) -> float:
		"""Sleep what is left of the delay, never past the run deadline. Only the first call acts."""
		if self._done:
			return 0.0
		self._done = True
		now = _now()
		wait = min(self.anchor + self.delay_s - now, deadline - now)
		if wait <= 0:
			return 0.0
		_sleep(wait)
		self.waited_s = wait
		return wait
