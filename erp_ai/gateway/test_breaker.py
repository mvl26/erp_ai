from frappe.tests.utils import FrappeTestCase

from erp_ai import constants
from erp_ai.gateway.breaker import Action, ApiFailure, decide

SPEND_CODE = "enforced_spend_limit_reached"
QUOTA_PREFIX = "You have reached your specified"
PAUSED = constants.KEY_STATUS_PAUSED
QUOTA = constants.KEY_STATUS_QUOTA_EXHAUSTED
BAD_KEY = constants.KEY_STATUS_BAD_KEY


def failure(status, kind="api", **kwargs):
	return ApiFailure(status=status, kind=kind, **kwargs)


class TestBreaker(FrappeTestCase):
	def test_breaker_table(self):
		cases = [
			(
				"row1 spend limit 429",
				failure(429, error_code=SPEND_CODE, retry_after=5),
				1,
				Action(QUOTA, None, True, "message", "quota"),
			),
			(
				"row2 429 with retry-after",
				failure(429, retry_after=30),
				1,
				Action(PAUSED, 31, True, None, "rate_limit"),
			),
			("row2 429 without retry-after", failure(429), 1, Action(PAUSED, 61, True, None, "rate_limit")),
			("row3 529 first", failure(529), 1, Action(PAUSED, 30, True, None, "overloaded")),
			("row3 529 third", failure(529), 3, Action(PAUSED, 90, True, None, "overloaded")),
			("row3 529 capped", failure(529), 50, Action(PAUSED, 600, True, None, "overloaded")),
			("row4 500", failure(500), 1, Action(PAUSED, 30, True, None, "server")),
			("row4 503", failure(503), 2, Action(PAUSED, 30, True, None, "server")),
			("row4 timeout", failure(None, kind="timeout"), 1, Action(PAUSED, 30, True, None, "timeout")),
			(
				"row4 connection",
				failure(None, kind="connection"),
				1,
				Action(PAUSED, 30, True, None, "timeout"),
			),
			("row5 402", failure(402), 1, Action(QUOTA, None, True, "message", "quota")),
			(
				"row6 400 quota message",
				failure(400, message_prefix=QUOTA_PREFIX),
				1,
				Action(QUOTA, None, True, "message", "quota"),
			),
			("row7 401", failure(401), 1, Action(BAD_KEY, None, True, "alarm", "auth")),
			("row7 403", failure(403), 1, Action(BAD_KEY, None, True, "alarm", "auth")),
			(
				"row8 400 other",
				failure(400, message_prefix="bad"),
				1,
				Action(None, None, False, None, "bad_request"),
			),
			("row8 404", failure(404), 1, Action(None, None, False, None, "bad_request")),
			("row8 413", failure(413), 1, Action(None, None, False, None, "bad_request")),
			("row8 422", failure(422), 1, Action(None, None, False, None, "bad_request")),
			(
				"row9 not an api error",
				failure(None, kind="unexpected"),
				1,
				Action(None, None, False, None, "unexpected"),
			),
		]
		for name, fail, count, expected in cases:
			with self.subTest(name):
				self.assertEqual(decide(fail, count), expected)

	def test_529_pause_boundary_at_cap(self):
		# 20 x 30 s = 600 s exactly; 21 x 30 s = 630 s is capped
		self.assertEqual(decide(failure(529), 19).pause_seconds, 570)
		self.assertEqual(decide(failure(529), 20).pause_seconds, 600)
		self.assertEqual(decide(failure(529), 21).pause_seconds, 600)

	def test_429_retry_after_zero_and_fractional(self):
		self.assertEqual(decide(failure(429, retry_after=0), 1).pause_seconds, 1)
		self.assertEqual(decide(failure(429, retry_after=2.5), 1).pause_seconds, 3.5)

	def test_429_spend_limit_wins_over_retry_after(self):
		action = decide(failure(429, error_code=SPEND_CODE, retry_after=10), 1)
		self.assertEqual(action.kind, "quota")
		self.assertIsNone(action.pause_seconds)

	def test_400_quota_prefix_only_applies_to_400(self):
		self.assertEqual(decide(failure(422, message_prefix=QUOTA_PREFIX), 1).kind, "bad_request")

	def test_status_below_400_is_unexpected(self):
		self.assertEqual(decide(failure(302), 1).kind, "unexpected")
