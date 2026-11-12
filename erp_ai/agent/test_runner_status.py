from unittest.mock import patch

import frappe
from frappe.utils import get_fullname

from erp_ai.agent.run_status import PAYLOAD_KEYS
from erp_ai.agent.test_agent_runner import RunnerTestBase, tool_turn, tool_use
from erp_ai.constants import AGENT_STATUS_EVENT, AGENT_USER, JOB_TIMEOUT_S, SETTING_DOCTYPE
from erp_ai.test_utils import FakeGateway, make_model_result, record_status_signals, set_agent_settings

THINKING_TEXT = "Đang suy nghĩ…"


class TestRunnerStatus(RunnerTestBase):
	def setUp(self):
		super().setUp()
		# `thinking_text` is added to the DocType by a later task; the Single value is rolled back with the test.
		frappe.db.set_single_value(SETTING_DOCTYPE, "thinking_text", THINKING_TEXT)
		set_agent_settings(permission_level="L1")
		self.signals = record_status_signals(self)
		self.signals_on_model_call = []

	def _gateway(self, *results):
		def on_call(task, kwargs):
			self.signals_on_model_call.append(len(self.signals))

		self.gateway = FakeGateway(*results, on_call=on_call)
		patcher = patch("erp_ai.gateway.call_model", self.gateway)
		patcher.start()
		self.addCleanup(patcher.stop)

	def test_start_signal_before_first_model_call(self):
		self._gateway(make_model_result(text="xong"))

		self._run("comment_mention")

		self.assertTrue(self.signals, "no status signal was emitted")
		first = self.signals[0]
		self.assertEqual(first["event"], AGENT_STATUS_EVENT)
		self.assertEqual(first["room"], f"doc:HD Ticket/{self.ticket.name}")
		self.assertEqual(list(first["message"]), list(PAYLOAD_KEYS))
		self.assertEqual(len(first["message"]), 7)
		self.assertEqual(
			first["message"],
			{
				"ticket_id": str(self.ticket.name),
				"run_id": first["message"]["run_id"],
				"agent_user": AGENT_USER,
				"agent_name": get_fullname(AGENT_USER),
				"state": "thinking",
				"text": THINKING_TEXT,
				"expires_in_s": JOB_TIMEOUT_S,
			},
		)
		self.assertEqual(len(first["message"]["run_id"]), 32)
		self.assertEqual(self.gateway.call_count, 1)
		self.assertEqual(self.signals_on_model_call, [1])

	def test_done_last_when_answered(self):
		self._gateway(
			tool_turn(tool_use("t1", "post_comment", content="Đã xử lý")),
			make_model_result(text="xong"),
		)
		comments_before = self._comment_count()

		self._run("comment_mention")

		self.assertEqual(self._comment_count(), comments_before + 1)

		states = [signal["message"]["state"] for signal in self.signals]
		self.assertTrue(states, "no status signal was emitted")
		self.assertEqual(states[0], "thinking")
		self.assertEqual(states.count("done"), 1)
		self.assertEqual(states[-1], "done")
		self.assertEqual(len({signal["message"]["run_id"] for signal in self.signals}), 1)
		self.assertEqual(self.signals[-1]["message"]["text"], "")
		self.assertEqual(list(self.signals[-1]["message"]), list(PAYLOAD_KEYS))
		self.assertEqual(len(self.signals[-1]["message"]), 7)
		self.assertEqual({entry.run_id for entry in self._entries()}, {self.signals[0]["message"]["run_id"]})

	def test_no_signal_when_run_skipped_at_level_l0(self):
		set_agent_settings(permission_level="L0")
		self._gateway()

		self._run("comment_mention")

		self.assertEqual(self.signals, [])
