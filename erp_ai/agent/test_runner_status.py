import copy
import json
import re
from unittest.mock import patch

import frappe
from frappe.utils import get_fullname

from erp_ai.agent import answer_delay, policy, runner
from erp_ai.agent.run_status import FALLBACK_WORK_LABEL, PAYLOAD_KEYS
from erp_ai.agent.test_agent_runner import CLASSIFY_A, DAILY_LIMIT, RunnerTestBase, tool_turn, tool_use
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
		self.classification_at_sleep = []
		# (tool name, text of the last signal) at the moment each tool really runs
		self.tool_starts = []
		real_execute_tool = runner.execute_tool

		def recording_execute_tool(name, *args, **kwargs):
			self.tool_starts.append((name, self.signals[-1]["message"]["text"] if self.signals else None))
			return real_execute_tool(name, *args, **kwargs)

		tool_patch = patch.object(runner, "execute_tool", side_effect=recording_execute_tool)
		tool_patch.start()
		self.addCleanup(tool_patch.stop)

		def sleeper(seconds):
			self.sleeps.append(seconds)
			self.at_sleep.append(([s["message"]["state"] for s in self.signals], self._comment_count()))
			self.classification_at_sleep.append(self._classification())

		sleep_patch = patch.object(answer_delay, "_sleep", side_effect=sleeper)
		sleep_patch.start()
		self.addCleanup(sleep_patch.stop)

	def _classification(self):
		return tuple(
			frappe.db.get_value(
				"HD Ticket", self.ticket.name, ["ai_classified_by", "ai_confidence", "priority"]
			)
		)

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

	def _states(self):
		return [signal["message"]["state"] for signal in self.signals]

	def _texts(self):
		return [signal["message"]["text"] for signal in self.signals]

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
		real_load_mapping = runner.load_mapping

		def slow_load_mapping(*args, **kwargs):
			# a step between the start signal and the first model call; the anchor was taken before it
			self.clock[0] += 0.5
			return real_load_mapping(*args, **kwargs)

		with patch.object(runner, "load_mapping", side_effect=slow_load_mapping):
			self._run("comment_mention")

		# anchor = right after the start signal; 0.5 s of set-up and 1 s of model took 1.5 s of the 4 s
		self.assertEqual(self.sleeps, [2.5])
		self.assertEqual(self.at_sleep, [(["thinking"], comments_before)])
		self.assertEqual(self._comment_count(), comments_before + 1)
		# the "working" signal of the answer comes only after the wait
		self.assertEqual(self._states(), ["thinking", "working", "thinking", "done"])
		self.assertEqual(self.signals[1]["message"]["text"], "Đang làm: viết trả lời…")

	def test_whole_turn_waits_before_its_first_tool(self):
		"""D-6: the wait sits before every tool of the answer turn, not just before the post_comment block."""
		self._set_delay(4, 4)
		set_agent_settings(category_mapping=json.dumps({"A": {"priority": "High"}}))
		self._gateway(
			tool_turn(
				tool_use("t1", "set_classification", category="A", confidence="Cao"),
				tool_use("t2", "post_comment", content="Đã xử lý"),
			),
			make_model_result(text="xong"),
		)
		comments_before = self._comment_count()
		classification_before = self._classification()

		self._run("comment_mention")

		self.assertEqual(self.sleeps, [4])
		# at sleep time neither tool of the turn had run
		self.assertEqual(self.classification_at_sleep, [classification_before])
		self.assertEqual(self.at_sleep, [(["thinking"], comments_before)])
		# after the run both did
		self.assertNotEqual(self._classification(), classification_before)
		self.assertEqual(self._comment_count(), comments_before + 1)

	def test_indicator_stays_thinking_while_waiting(self):
		self._set_delay(4, 4)
		self._gateway(*self._answer_turns())

		self._run("comment_mention")

		states, _ = self.at_sleep[0]
		self.assertEqual(set(states), {"thinking"})
		# no signal between the model call and the sleep
		self.assertEqual(len(states), self.signals_on_model_call[0])
		# the sleep ends, then the answer is announced as work
		self.assertEqual(self._states()[:2], ["thinking", "working"])
		self.assertEqual(self.signals[1]["message"]["text"], "Đang làm: viết trả lời…")

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
				try:
					self._gateway(*self._answer_turns())
					arrange()

					self._run("comment_mention")

					self.assertEqual(self.signals, [])
					self.assertEqual(self.sleeps, [])
					self.assertEqual(self.gateway.call_count, 0)
				finally:
					frappe.db.rollback(save_point="erp_ai_skip_case")

	def test_empty_text_no_signal_delay_still_applies(self):
		self._set_delay(3, 5)
		for text in ("", "   "):
			with self.subTest(repr(text)):
				frappe.db.savepoint("erp_ai_empty_case")
				try:
					self.sleeps.clear()
					frappe.db.set_single_value(SETTING_DOCTYPE, "thinking_text", text)
					self._gateway(*self._answer_turns())

					self._run("comment_mention")

					self.assertEqual(self.signals, [])
					self.assertEqual(len(self.sleeps), 1)
					self.assertTrue(3 <= self.sleeps[0] <= 5, self.sleeps)
				finally:
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
		try:
			self.model_messages.clear()
			self._gateway(*self._answer_turns(cost_usd=0.25))
			self._run("comment_mention")
			cost = sum(entry.cost_usd for entry in self._entries())
			# the id of the comment a run creates is random; everything else must be identical
			messages = re.sub(
				r'(comment\\": \\")\w+', r"\1<id>", json.dumps(self.model_messages, sort_keys=True)
			)
			return (messages, self.gateway.call_count, cost)
		finally:
			frappe.db.rollback(save_point="erp_ai_on_off")

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

	def test_signal_sequence_read_tool_then_answer(self):
		self._gateway(
			tool_turn(tool_use("t1", "get_ticket")),
			tool_turn(tool_use("t2", "post_comment", content="Đã xử lý")),
			make_model_result(text="xong"),
		)

		self._run("comment_mention")

		self.assertEqual(self._states(), ["thinking", "working", "thinking", "working", "thinking", "done"])
		self.assertEqual(
			self._texts(),
			[
				THINKING_TEXT,
				"Đang làm: đọc phiếu…",
				THINKING_TEXT,
				"Đang làm: viết trả lời…",
				THINKING_TEXT,
				"",
			],
		)
		# AC-9: each work signal is out before its tool runs
		self.assertEqual(
			self.tool_starts,
			[("get_ticket", "Đang làm: đọc phiếu…"), ("post_comment", "Đang làm: viết trả lời…")],
		)

	def test_ticket_insert_l0_gets_start_signal(self):
		set_agent_settings(permission_level="L0")
		self._gateway(make_model_result(text=CLASSIFY_A))

		self._run("ticket_insert")

		self.assertEqual(self._states(), ["thinking", "working", "done"])
		self.assertEqual(self._texts()[1], "Đang làm: phân loại phiếu…")
		# AC-2 / AC-9: the start signal and the classify work signal are both out before the model call
		self.assertEqual(self.signals[0]["message"]["state"], "thinking")
		self.assertEqual(self.signals_on_model_call, [2])

	def test_ticket_insert_l1_signal_sequence(self):
		self._gateway(make_model_result(text=CLASSIFY_A), make_model_result(text="xong"))

		self._run("ticket_insert")

		self.assertEqual(self._states(), ["thinking", "working", "working", "thinking", "done"])
		self.assertEqual(self._texts()[1:3], ["Đang làm: phân loại phiếu…", "Đang làm: ghi phân loại…"])
		# classify work signal before the classify call; the second call comes after both work signals
		self.assertEqual(self.signals_on_model_call, [2, 4])
		self.assertEqual(self.tool_starts, [("set_classification", "Đang làm: ghi phân loại…")])

	def test_ticket_insert_never_waits(self):
		self._set_delay(3, 5)
		for level in ("L0", "L1"):
			with self.subTest(level):
				frappe.db.savepoint("erp_ai_insert_case")
				try:
					set_agent_settings(permission_level=level)
					self._gateway(
						make_model_result(text=CLASSIFY_A),
						tool_turn(tool_use("t1", "post_comment", content="Đã xử lý")),
						make_model_result(text="xong"),
					)

					self._run("ticket_insert")

					self.assertEqual(self.sleeps, [])
					self.assertTrue(self.signals, "no status signal was emitted")
					# the L1 run got through the answer turn, where the wait would have been
					self.assertEqual(self.gateway.call_count, 1 if level == "L0" else 3)
				finally:
					frappe.db.rollback(save_point="erp_ai_insert_case")

	def test_tool_arguments_and_ticket_text_never_in_payload(self):
		marker = "MARKERXYZ"
		frappe.db.set_value("HD Ticket", self.ticket.name, "subject", f"{marker} subject")
		self._gateway(
			tool_turn(
				tool_use("t1", f"tool_{marker}", secret=marker),
				tool_use("t2", "post_comment", content=f"{marker} answer"),
			),
			make_model_result(text="xong"),
		)

		self._run("comment_mention")

		self.assertIn("working", self._states())
		self.assertNotIn(marker, json.dumps(self.signals, ensure_ascii=False))
		self.assertIn(f"Đang làm: {FALLBACK_WORK_LABEL}…", self._texts())
