from datetime import datetime, timedelta
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erp_ai.agent import system_read
from erp_ai.agent.redact import MASK
from erp_ai.agent.system_read import read_error_logs
from erp_ai.constants import AGENT_USER
from erp_ai.test_utils import keep_agent_settings, pin_agent_roles

# A moment no real Error Log row of this site can have, so only the rows a test seeds fall in its window.
NOW = datetime(2001, 3, 10, 12, 0, 0)
WINDOW_ERROR = "Khoảng thời gian tối đa 7 ngày"


class ErrorLogCase(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		keep_agent_settings(self)
		self.seeded = []
		self.addCleanup(self._delete_seeded)
		# `now` of the module is pinned; no test depends on the real clock.
		self.enterContext(patch.object(system_read, "now_datetime", return_value=NOW))

	def _delete_seeded(self):
		if self.seeded:
			frappe.db.delete("Error Log", {"name": ("in", self.seeded)})

	def seed(self, creation, method="erp_ai.test.method", error="Traceback: boom") -> str:
		doc = frappe.get_doc({"doctype": "Error Log", "method": method, "error": error})
		doc.name = frappe.generate_hash(length=12)
		doc.owner = doc.modified_by = "Administrator"
		doc.creation = doc.modified = creation
		doc.db_insert()
		self.seeded.append(doc.name)
		return doc.name

	def names(self, rows) -> list[str]:
		return [row["name"] for row in rows]


class TestErrorLogs(ErrorLogCase):
	def test_time_and_keyword_filter(self):
		before_window = self.seed(NOW - timedelta(hours=24, seconds=1))
		window_start = self.seed(NOW - timedelta(hours=24), method="sync_orders")
		middle = self.seed(NOW - timedelta(hours=3), error="Traceback: SyncOrders failed")
		window_end = self.seed(NOW, error="Traceback: other")
		after_window = self.seed(NOW + timedelta(seconds=1))

		# default: until = now, since = until - 24 h, both ends included, newest first
		rows = read_error_logs()
		self.assertEqual(self.names(rows), [window_end, middle, window_start])
		self.assertNotIn(before_window, self.names(rows))
		self.assertNotIn(after_window, self.names(rows))
		self.assertEqual(set(rows[0]), {"name", "creation", "method", "error"})
		self.assertEqual(rows[0]["creation"], NOW)

		# only `since`: until is now; only `until`: since is until - 24 h
		self.assertEqual(self.names(read_error_logs(since=NOW - timedelta(hours=3))), [window_end, middle])
		self.assertEqual(
			self.names(read_error_logs(until=NOW - timedelta(seconds=1))),
			[middle, window_start, before_window],
		)
		# explicit window
		self.assertEqual(
			self.names(read_error_logs(since=NOW - timedelta(hours=4), until=NOW - timedelta(hours=2))),
			[middle],
		)

		# keyword matches `method` or `error`, case-insensitive
		self.assertEqual(self.names(read_error_logs(keyword="syncorders")), [middle])
		self.assertEqual(self.names(read_error_logs(keyword="sync_orders")), [window_start])
		self.assertEqual(self.names(read_error_logs(keyword="nothing-like-this")), [])

	def test_limit_bounds(self):
		seeded = [self.seed(NOW - timedelta(minutes=minute)) for minute in range(51)]

		self.assertEqual(self.names(read_error_logs()), seeded[:20])
		self.assertEqual(self.names(read_error_logs(limit=1)), seeded[:1])
		self.assertEqual(self.names(read_error_logs(limit=50)), seeded[:50])
		for limit in (0, 51, -1):
			with self.subTest(limit=limit), self.assertRaises(frappe.ValidationError):
				read_error_logs(limit=limit)

	def test_window_over_seven_days_refused(self):
		oldest = self.seed(NOW - timedelta(days=7))

		self.assertEqual(self.names(read_error_logs(since=NOW - timedelta(days=7), until=NOW)), [oldest])
		for since in (NOW - timedelta(days=7, seconds=1), NOW - timedelta(days=7, microseconds=1)):
			with self.subTest(since=since), self.assertRaisesRegex(frappe.ValidationError, WINDOW_ERROR):
				read_error_logs(since=since, until=NOW)
		# the default `until` (now) counts too
		with self.assertRaisesRegex(frappe.ValidationError, WINDOW_ERROR):
			read_error_logs(since=NOW - timedelta(days=8))

	def test_seeded_secrets_masked(self):
		seeded = self.seed(
			NOW,
			method="erp_ai.sync api_key=fake-method-key",
			error="Traceback\nrequests.post(headers={'Authorization': 'Bearer FAKEBEARER0123456789'})\n"
			"password=fake-pass-01 api_secret: fake-secret-02",
		)

		rows = read_error_logs()
		self.assertEqual(self.names(rows), [seeded])
		row = rows[0]
		self.assertNotIn("fake-method-key", row["method"])
		self.assertEqual(row["method"], f"erp_ai.sync api_key={MASK}")
		for secret in ("FAKEBEARER0123456789", "fake-pass-01", "fake-secret-02"):
			with self.subTest(secret=secret):
				self.assertNotIn(secret, row["error"])
		self.assertIn(f"password={MASK}", row["error"])

	def test_error_keeps_last_2000_chars(self):
		long_error = "HEAD" + "a" * 2492 + "TAIL"
		long_name = self.seed(NOW, error=long_error)
		exact_name = self.seed(NOW - timedelta(seconds=1), error="E" + "b" * 1998 + "F")
		over_name = self.seed(NOW - timedelta(seconds=2), error="G" + "c" * 1999 + "H")

		rows = read_error_logs()
		self.assertEqual(self.names(rows), [long_name, exact_name, over_name])
		errors = {row["name"]: row["error"] for row in rows}
		self.assertEqual(errors[long_name], long_error[-2000:])
		self.assertTrue(errors[long_name].endswith("TAIL"))
		self.assertEqual(errors[exact_name], "E" + "b" * 1998 + "F")
		self.assertEqual(errors[over_name], "c" * 1999 + "H")

	def test_agent_roles_unchanged(self):
		seeded = self.seed(NOW - timedelta(hours=1), error="api_key=fake-agent-key")
		pin_agent_roles(self)
		roles_before = sorted(frappe.get_roles(AGENT_USER))
		frappe.set_user(AGENT_USER)

		# premise: the agent's roles cannot open Error Log as a document
		self.assertFalse(frappe.has_permission("Error Log", "read", user=AGENT_USER))
		rows = read_error_logs()

		self.assertEqual(self.names(rows), [seeded])
		self.assertNotIn("fake-agent-key", rows[0]["error"])
		frappe.clear_cache(user=AGENT_USER)
		self.assertEqual(sorted(frappe.get_roles(AGENT_USER)), roles_before)
		self.assertNotIn("System Manager", roles_before)

	def test_keyword_wildcards_escaped_and_length_bounds(self):
		self.seed(NOW - timedelta(minutes=1), error="plain error")
		percent = self.seed(NOW - timedelta(minutes=2), error="disk 100%% full")
		underscore = self.seed(NOW - timedelta(minutes=3), method="a__b")
		backslash = self.seed(NOW - timedelta(minutes=4), error="path C:\\\\tmp")
		self.seed(NOW - timedelta(minutes=5), error="path C:\\tmp")

		# wildcards are literal: they do not match every row
		self.assertEqual(self.names(read_error_logs(keyword="%%")), [percent])
		self.assertEqual(self.names(read_error_logs(keyword="__")), [underscore])
		self.assertEqual(self.names(read_error_logs(keyword="\\\\")), [backslash])
		self.assertEqual(self.names(read_error_logs(keyword="%_")), [])

		# 2 and 100 characters are accepted; 1 and 101 (and empty) are refused
		self.assertEqual(read_error_logs(keyword="zq"), [])
		self.assertEqual(read_error_logs(keyword="z" * 100), [])
		for keyword in ("", "z", "z" * 101):
			with self.subTest(length=len(keyword)), self.assertRaises(frappe.ValidationError):
				read_error_logs(keyword=keyword)


class TestReadErrorLogs(ErrorLogCase):
	def test_secret_at_tail_cut_masked(self):
		secret = "api_key=fake-tail"
		suffix = " " + "z" * (2000 - len("key=fake-tail") - 1)
		error = "x" * 500 + " " + secret + suffix
		# premise: cutting the raw text first would start the last 2000 chars inside the key name
		self.assertTrue(error[-2000:].startswith("key=fake-tail "))
		seeded = self.seed(NOW, error=error)

		rows = read_error_logs()
		self.assertEqual(self.names(rows), [seeded])
		row = rows[0]
		self.assertNotIn("fake-tail", row["error"])
		self.assertEqual(len(row["error"]), 2000)
		self.assertTrue(row["error"].endswith(f"_key={MASK}{suffix}"))
