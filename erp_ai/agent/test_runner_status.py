import copy
import json
import re
from unittest.mock import patch

import frappe
from frappe.utils import get_fullname

from erp_ai.agent import answer_delay, policy
from erp_ai.agent.run_status import PAYLOAD_KEYS
from erp_ai.agent.test_agent_runner import DAILY_LIMIT, RunnerTestBase, tool_turn, tool_use
from erp_ai.constants import AGENT_STATUS_EVENT, AGENT_USER, JOB_TIMEOUT_S, SETTING_DOCTYPE
from erp_ai.test_utils import FakeGateway, make_model_result, set_agent_settings

THINKING_TEXT = "Đang suy nghĩ…"


class TestRunnerStatus(RunnerTestBase):
	def setUp(self):
		super().setUp()
		# `thinking_text` is added to the DocType by a later task; the Single value is rolled back with the test.
		frappe.db.set_single_value(SETTING_DOCTYPE, "thinking_text", THINKING_TEXT)
		set_agent_settings(permission_level="L1")
		self.signals_on_model_call = []
		self.model_messages = []
		self.model_seconds = 0
		# Fake clock: only a model call moves it, so the delay maths is exact.
		self.clock = [0.0]
		clock_patch = patch.object(answer_delay, "_now", side_effect=lambda: self.clock[0])
		clock_patch.start()
		self.addCleanup(clock_patch.stop)
		# What the page showed and what the ticket had when the run went to sleep.
		self.at_sleep = []

		def sleeper(seconds):
			self.sleeps.append(seconds)
			self.at_sleep.append(([s["message"]["state"] for s in self.signals], self._comment_count()))

		sleep_patch = patch.object(answer_delay, "_sleep", side_effect=sleeper)
		sleep_patch.start()
		self.addCleanup(sleep_patch.stop)

	def _gateway(self, *results):
		def on_call(task, kwargs):
			self.signals_on_model_call.append(len(self.signals))
			self.model_messages.append(copy.deepcopy(kwargs["messages"]) if "messages" in kwargs else None)
			self.clock[0] += self.model_seconds

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

	def _answer_turns(self, cost_usd=0.0):
		return (
			tool_turn(tool_use("t1", "post_comment", content="Đã xử lý"), cost_usd=cost_usd),
			make_model_result(text="xong", cost_usd=cost_usd),
		)

	def _set_delay(self, low, high):
		set_agent_settings(answer_delay_min_s=low, answer_delay_max_s=high)

	def test_answer_waits_from_start_signal(self):
		self._set_delay(4, 4)
		self.model_seconds = 1
		self._gateway(*self._answer_turns())
		comments_before = self._comment_count()

		self._run("comment_mention")

		# anchor = right after the start signal; the model took 1 s of the 4 s
		self.assertEqual(self.sleeps, [3])
		self.assertEqual(self.at_sleep, [(["thinking"], comments_before)])
		self.assertEqual(self._comment_count(), comments_before + 1)

	def test_indicator_stays_thinking_while_waiting(self):
		self._set_delay(4, 4)
		self._gateway(*self._answer_turns())

		self._run("comment_mention")

		states, _ = self.at_sleep[0]
		self.assertEqual(set(states), {"thinking"})
		# no signal between the model call and the sleep
		self.assertEqual(len(states), self.signals_on_model_call[0])

	def test_skipped_runs_emit_nothing_and_never_wait(self):
		self._set_delay(3, 5)
		cases = {
			"disabled": lambda: set_agent_settings(enabled=0),
			"not_sendable": lambda: frappe.db.set_value("HD Ticket", self.ticket.name, "ai_opt_out", 1),
			"daily_limit": lambda: self._seed_runs(DAILY_LIMIT),
			"level_L0": lambda: set_agent_settings(permission_level="L0"),
		}
		for name, arrange in cases.items():
			with self.subTest(name):
				frappe.db.savepoint("erp_ai_skip_case")
				self._gateway(*self._answer_turns())
				arrange()

				self._run("comment_mention")

				self.assertEqual(self.signals, [])
				self.assertEqual(self.sleeps, [])
				self.assertEqual(self.gateway.call_count, 0)
				frappe.db.rollback(save_point="erp_ai_skip_case")

	def test_empty_text_no_signal_delay_still_applies(self):
		self._set_delay(3, 5)
		for text in ("", "   "):
			with self.subTest(repr(text)):
				frappe.db.savepoint("erp_ai_empty_case")
				self.sleeps.clear()
				frappe.db.set_single_value(SETTING_DOCTYPE, "thinking_text", text)
				self._gateway(*self._answer_turns())

				self._run("comment_mention")

				self.assertEqual(self.signals, [])
				self.assertEqual(len(self.sleeps), 1)
				self.assertTrue(3 <= self.sleeps[0] <= 5, self.sleeps)
				frappe.db.rollback(save_point="erp_ai_empty_case")

	def test_mention_run_counts_once_for_daily_limit(self):
		self._set_delay(3, 5)
		self._gateway(*self._answer_turns())

		self._run("comment_mention")

		self.assertEqual(len(self._entries(entry_type="reason")), 2)
		self.assertEqual(policy.runs_today(self.ticket.name), 1)

	def _run_with(self, low, high, text):
		"""One mention run under the given feature settings; returns (model messages per call, call count, total cost)."""
		frappe.db.savepoint("erp_ai_on_off")
		self._set_delay(low, high)
		frappe.db.set_single_value(SETTING_DOCTYPE, "thinking_text", text)
		self.model_messages.clear()
		self._gateway(*self._answer_turns(cost_usd=0.25))
		self._run("comment_mention")
		cost = sum(entry.cost_usd for entry in self._entries())
		# the id of the comment a run creates is random; everything else must be identical
		messages = re.sub(r'(comment\\": \\")\w+', r"\1<id>", json.dumps(self.model_messages, sort_keys=True))
		outcome = (messages, self.gateway.call_count, cost)
		frappe.db.rollback(save_point="erp_ai_on_off")
		return outcome

	def test_model_messages_same_with_feature_on_and_off(self):
		on = self._run_with(3, 5, THINKING_TEXT)
		off = self._run_with(0, 0, "")

		self.assertIn("<id>", on[0])
		self.assertEqual(on[0], off[0])

	def test_same_gateway_calls_and_cost_with_feature_on_and_off(self):
		on = self._run_with(3, 5, THINKING_TEXT)
		off = self._run_with(0, 0, "")

		self.assertEqual(on[1], off[1])
		self.assertEqual(on[1], 2)
		self.assertAlmostEqual(on[2], off[2])
		self.assertAlmostEqual(on[2], 0.5)
