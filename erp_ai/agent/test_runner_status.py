import copy
import json
import re
from unittest.mock import call, patch

import frappe
from frappe.utils import get_fullname

from erp_ai.agent import answer_delay, policy, runner
from erp_ai.agent.run_status import FALLBACK_WORK_LABEL, PAYLOAD_KEYS, WORK_LABELS
from erp_ai.agent.test_agent_runner import (
	CLASSIFY_A,
	DAILY_LIMIT,
	TICKET_FIELDS,
	RunnerTestBase,
	tool_turn,
	tool_use,
)
from erp_ai.constants import (
	AGENT_STATUS_EVENT,
	AGENT_USER,
	JOB_TIMEOUT_S,
	LOG_DOCTYPE,
	LOGGER_NAME,
	SETTING_DOCTYPE,
	TITLE_RUN_FAILED,
	TITLE_STATUS_FAILED,
)
from erp_ai.gateway import GatewayError
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
		real_apply_route = runner.apply_route

		def recording_apply_route(*args, **kwargs):
			self.tool_starts.append(
				("apply_route", self.signals[-1]["message"]["text"] if self.signals else None)
			)
			return real_apply_route(*args, **kwargs)

		route_patch = patch.object(runner, "apply_route", side_effect=recording_apply_route)
		route_patch.start()
		self.addCleanup(route_patch.stop)

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
		self.assertEqual(self.tool_starts, [("apply_route", "Đang làm: ghi phân loại…")])

	def test_ticket_insert_never_waits(self):
		self._set_delay(3, 5)
		for level in ("L0", "L1"):
			with self.subTest(level):
				self.signals.clear()
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

	# T6: `done` is the last signal on every ending (AC-4), one summary line per run (design 4.5)

	def _run_closing(self, trigger):
		"""Run once; return the arguments of each `run_status` summary line; sets `self.log_error` and `self.signals_at_entry` (signals out when each entry was written)."""
		self.signals_at_entry = []
		real_write_entry = runner.write_entry

		def recording_write_entry(**fields):
			self.signals_at_entry.append(len(self.signals))
			return real_write_entry(**fields)

		with (
			patch.object(runner, "write_entry", side_effect=recording_write_entry),
			patch.object(frappe, "logger") as get_logger,
			patch.object(frappe, "log_error") as log_error,
		):
			self._run(trigger)
		self.log_error = log_error
		lines = [
			invocation.args
			for invocation in get_logger.return_value.info.call_args_list
			if invocation.args and str(invocation.args[0]).startswith("erp_ai run_status")
		]
		get_logger.assert_any_call(LOGGER_NAME)
		return lines

	def _assert_done_last_and_summarised(self, lines, trigger, errors=0, delay_s=0, waited_s=0):
		states = self._states()
		self.assertEqual(states[0], "thinking")
		self.assertEqual(states.count("done"), 1)
		self.assertEqual(states[-1], "done")
		# no entry is written after `done` (NFR-5)
		self.assertTrue(self.signals_at_entry)
		self.assertLess(self.signals_at_entry[-1], len(self.signals))
		run_id = self.signals[0]["message"]["run_id"]
		self.assertEqual(len(lines), 1)
		fmt, *values = lines[0]
		self.assertEqual(
			fmt,
			"erp_ai run_status ticket=%s run_id=%s trigger=%s signals=%d errors=%d delay_s=%.1f waited_s=%.1f",
		)
		self.assertEqual(values[:5], [self.ticket.name, run_id, trigger, len(self.signals), errors])
		# delay_s and waited_s, in that order (design 4.5)
		self.assertEqual(values[5:], [delay_s, waited_s])

	def test_done_last_when_no_post_comment(self):
		self._set_delay(4, 4)
		self._gateway(make_model_result(text="xong"))

		lines = self._run_closing("comment_mention")

		# the model never answered, so the delay was picked but nothing waited
		self._assert_done_last_and_summarised(lines, "comment_mention", delay_s=4, waited_s=0)
		self.assertEqual(self._states(), ["thinking", "done"])

	def test_summary_line_reports_delay_and_wait(self):
		self._set_delay(4, 4)
		self.model_seconds = 1
		self._gateway(*self._answer_turns())

		lines = self._run_closing("comment_mention")

		# 4 s of delay, 1 s spent in the model: the run slept the other 3 s
		self.assertEqual(self.sleeps, [3])
		self._assert_done_last_and_summarised(lines, "comment_mention", delay_s=4, waited_s=3)

	def test_done_last_on_gateway_error(self):
		self._gateway(GatewayError("server_error", status=500))

		lines = self._run_closing("comment_mention")

		self._assert_done_last_and_summarised(lines, "comment_mention")
		self.assertEqual(self._entries(entry_type="reason")[-1].stop_reason, "gateway_error")

	def test_done_last_on_deadline(self):
		self._gateway(GatewayError("deadline"))

		lines = self._run_closing("comment_mention")

		self._assert_done_last_and_summarised(lines, "comment_mention")
		self.assertEqual(self._entries(entry_type="reason")[-1].stop_reason, "time_budget")

	def test_done_last_on_max_turns(self):
		set_agent_settings(max_turns_per_run=2)
		self._gateway(tool_turn(tool_use("t1", "get_ticket")), tool_turn(tool_use("t2", "get_ticket")))

		lines = self._run_closing("comment_mention")

		self._assert_done_last_and_summarised(lines, "comment_mention")
		self.assertEqual(self._entries(entry_type="reason")[-1].stop_reason, "max_turns")

	def test_done_last_after_tool_exception(self):
		self._gateway(tool_turn(tool_use("t1", "get_ticket")), make_model_result(text="xong"))

		with patch.object(runner, "execute_tool", side_effect=RuntimeError):
			lines = self._run_closing("comment_mention")

		self._assert_done_last_and_summarised(lines, "comment_mention")
		self.assertEqual(self.gateway.call_count, 2)
		self.assertIn("tool get_ticket: RuntimeError", self._entries(entry_type="reason")[0].error)

	def test_done_last_on_classify_gateway_error(self):
		# ticket_insert has no delay, whatever the settings say: the summary reports 0 and 0
		self._set_delay(4, 4)
		self._gateway(GatewayError("server_error", status=500))

		lines = self._run_closing("ticket_insert")

		self._assert_done_last_and_summarised(lines, "ticket_insert")
		self.assertEqual(self._entries()[-1].stop_reason, "gateway_error")

	def test_done_last_on_unexpected_runner_exception(self):
		self._set_delay(4, 4)
		self._gateway(make_model_result(text="xong"))

		with patch.object(runner, "build_initial_message", side_effect=RuntimeError):
			lines = self._run_closing("comment_mention")

		# the run died before any entry: `done` is still last and the summary line is still written
		self.assertEqual(self._states(), ["thinking", "done"])
		self.assertEqual(self.signals_at_entry, [])
		self.assertEqual(len(lines), 1)
		self.assertEqual(lines[0][3:], ("comment_mention", 2, 0, 4, 0))
		# the failure still reaches the log as before, with the class only
		self.assertEqual(
			[invocation.args[0] for invocation in self.log_error.call_args_list], [TITLE_RUN_FAILED]
		)

	def test_done_reaches_page_on_rollback_branch(self):
		before = tuple(frappe.db.get_value("HD Ticket", self.ticket.name, TICKET_FIELDS))
		real_set_value = frappe.db.set_value

		def failing_set_value(doctype, *args, **kwargs):
			if doctype == LOG_DOCTYPE:
				raise RuntimeError("boom")
			return real_set_value(doctype, *args, **kwargs)

		self._gateway(make_model_result(text=CLASSIFY_A))
		with patch.object(frappe.db, "set_value", side_effect=failing_set_value):
			lines = self._run_closing("ticket_insert")

		# the ticket change was rolled back, the classify entry kept, and `done` is out last
		self.assertEqual(tuple(frappe.db.get_value("HD Ticket", self.ticket.name, TICKET_FIELDS)), before)
		self.assertEqual(self._entries(entry_type="classify")[0].applied, 0)
		self.assertEqual(self._states(), ["thinking", "working", "working", "done"])
		self.assertEqual(
			[invocation.args[0] for invocation in self.log_error.call_args_list], [TITLE_RUN_FAILED]
		)
		self.assertEqual(len(lines), 1)

	def test_done_after_last_log_entry(self):
		self._gateway(
			tool_turn(tool_use("t1", "get_ticket")),
			tool_turn(tool_use("t2", "post_comment", content="Đã xử lý")),
			make_model_result(text="xong"),
		)

		self._run_closing("comment_mention")

		# three reason entries, each written before `done`; the last one just before it
		self.assertEqual(len(self.signals_at_entry), 3)
		self.assertEqual(len(self._states()), len(self.signals))
		self.assertEqual(self._states()[-1], "done")
		self.assertEqual(self.signals_at_entry[-1], len(self.signals) - 1)

	def test_done_signal_failure_logged_to_error_log_class_only(self):
		self._set_delay(4, 4)
		self._gateway(*self._answer_turns())
		comments_before = self._comment_count()

		run_ids = []

		def failing_done(event, message, room=None):
			run_ids.append(message["run_id"])
			if message["state"] == "done":
				raise RuntimeError("MARKERXYZ")

		with patch("frappe.realtime.emit_via_redis", side_effect=failing_done):
			lines = self._run_closing("comment_mention")

		# the run still answered; the lost `done` is only reported
		self.assertEqual(self._comment_count(), comments_before + 1)
		run_id = run_ids[0]
		self.assertEqual(
			self.log_error.call_args_list,
			[
				call(
					TITLE_STATUS_FAILED,
					f"ticket={self.ticket.name} run_id={run_id} status_done: RuntimeError",
				)
			],
		)
		self.assertEqual(lines[0][3:], ("comment_mention", 4, 1, 4, 4))

	def _fail_signals(self, failing_state):
		"""Patch the emit so that signals of `failing_state` raise; the others are recorded in `self.signals`."""

		def emit(event, message, room=None):
			if message["state"] == failing_state:
				raise RuntimeError("MARKERXYZ")
			self.signals.append({"event": event, "message": message, "room": room})

		return patch("frappe.realtime.emit_via_redis", side_effect=emit)

	def test_start_signal_failure_still_answers_and_logs_class(self):
		self._gateway(*self._answer_turns())
		comments_before = self._comment_count()

		with self._fail_signals("thinking"):
			lines = self._run_closing("comment_mention")

		self.assertEqual(self._comment_count(), comments_before + 1)
		reasons = self._entries(entry_type="reason")
		self.assertEqual(reasons[0].error, "status_thinking: RuntimeError")
		self.assertNotIn("MARKERXYZ", json.dumps([entry.error for entry in reasons]))
		# `done` is still attempted and delivered although the start signal was lost
		self.assertEqual(self._states(), ["working", "done"])
		# four signals tried (the failed ones count), every failure already went into an entry
		self.assertEqual(lines[0][3:6], ("comment_mention", 4, 0))

	def test_working_signal_failure_still_answers_and_logs_class(self):
		self._gateway(*self._answer_turns())
		comments_before = self._comment_count()

		with self._fail_signals("working"):
			self._run_closing("comment_mention")

		self.assertEqual(self._comment_count(), comments_before + 1)
		reasons = self._entries(entry_type="reason")
		self.assertEqual(reasons[0].error, "status_working: RuntimeError")
		self.assertFalse(reasons[1].error)
		self.assertEqual(self._states(), ["thinking", "thinking", "done"])

	def _fail_first_working(self):
		"""Patch the emit so that only the first `working` signal raises; the others are recorded in `self.signals`."""
		seen = []

		def emit(event, message, room=None):
			if message["state"] == "working" and not seen:
				seen.append(message)
				raise RuntimeError("MARKERXYZ")
			self.signals.append({"event": event, "message": message, "room": room})

		return patch("frappe.realtime.emit_via_redis", side_effect=emit)

	def test_working_failure_on_classify_goes_into_the_classify_entry(self):
		self._gateway(make_model_result(text=CLASSIFY_A))

		with self._fail_first_working():
			self._run_closing("ticket_insert")

		# D-9: the fragment is in the entry of the step that follows the failed signal, not in the Error Log
		entries = self._entries()
		self.assertEqual([entry.entry_type for entry in entries], ["classify", "reason"])
		self.assertEqual(entries[0].error, "status_working: RuntimeError")
		self.assertEqual(entries[0].applied, 1)
		self.assertFalse(entries[1].error)
		self.assertEqual(self.log_error.call_args_list, [])

	def test_thinking_failure_joins_the_classify_gateway_error(self):
		self._gateway(GatewayError("server_error", status=500))

		with self._fail_signals("thinking"):
			self._run_closing("ticket_insert")

		entry = self._entries(entry_type="classify")[-1]
		self.assertEqual(entry.error, "server_error status=500; status_thinking: RuntimeError")
		self.assertEqual(self.log_error.call_args_list, [])

	def test_thinking_failure_joins_the_unparseable_classify_error(self):
		self._gateway(make_model_result(text="không phải JSON"))

		with self._fail_signals("thinking"):
			self._run_closing("ticket_insert")

		entry = self._entries(entry_type="classify")[-1]
		self.assertEqual(entry.error, f"{runner.UNPARSEABLE_ERROR}; status_thinking: RuntimeError")
		self.assertEqual(self.log_error.call_args_list, [])

	def test_thinking_failure_joins_the_reason_gateway_error(self):
		self._gateway(GatewayError("server_error", status=500))

		with self._fail_signals("thinking"):
			self._run_closing("comment_mention")

		entry = self._entries(entry_type="reason")[-1]
		self.assertEqual(entry.error, "server_error status=500; status_thinking: RuntimeError")
		self.assertEqual(self.log_error.call_args_list, [])

	def test_working_failure_joins_the_tool_error_with_semicolon(self):
		self._gateway(tool_turn(tool_use("t1", "get_ticket")), make_model_result(text="xong"))

		with patch.object(runner, "execute_tool", side_effect=RuntimeError), self._fail_signals("working"):
			self._run_closing("comment_mention")

		reasons = self._entries(entry_type="reason")
		self.assertEqual(reasons[0].error, "tool get_ticket: RuntimeError; status_working: RuntimeError")
		self.assertFalse(reasons[1].error)

	def test_pending_fragment_after_a_crash_goes_to_the_error_log(self):
		self._gateway(make_model_result(text="xong"))

		with (
			self._fail_signals("thinking"),
			patch.object(runner, "build_initial_message", side_effect=RuntimeError),
		):
			lines = self._run_closing("comment_mention")

		# no entry was written, so the closing step reports the fragment (D-9), class only; it runs before the crash is logged
		titles = [invocation.args[0] for invocation in self.log_error.call_args_list]
		self.assertEqual(titles, [TITLE_STATUS_FAILED, TITLE_RUN_FAILED])
		run_id = self.signals[0]["message"]["run_id"]
		self.assertEqual(
			self.log_error.call_args_list[0].args[1],
			f"ticket={self.ticket.name} run_id={run_id} status_thinking: RuntimeError",
		)
		self.assertEqual(lines[0][5], 1)

	def test_status_text_never_in_logs(self):
		marker = "MARKERXYZ"
		frappe.db.set_single_value(SETTING_DOCTYPE, "thinking_text", f"{marker} thinking")
		self._gateway(*self._answer_turns())

		def failing(event, message, room=None):
			raise RuntimeError(f"{marker} {message['text']}")

		with (
			patch("frappe.realtime.emit_via_redis", side_effect=failing),
			patch.object(frappe, "logger") as get_logger,
			patch.object(frappe, "log_error") as log_error,
		):
			self._run("comment_mention")

		entries = json.dumps(self._entries(), default=str, ensure_ascii=False)
		error_log = json.dumps(
			[list(invocation.args) for invocation in log_error.call_args_list], ensure_ascii=False
		)
		logger_lines = json.dumps(
			[list(invocation.args) for invocation in get_logger.return_value.mock_calls], ensure_ascii=False
		)
		# non-vacuous: the failed `done` reached the Error Log and the summary line was written
		self.assertEqual(len(log_error.call_args_list), 1)
		self.assertIn("run_status", logger_lines)
		for name, text in (("run log", entries), ("Error Log", error_log), ("logger", logger_lines)):
			for forbidden in (marker, "Đang làm", *WORK_LABELS.values()):
				with self.subTest(name=name, forbidden=forbidden):
					self.assertNotIn(forbidden, text)

	def _count_changes(self):
		"""Run one mention run and return what it changed: (new Comments, new Tasks, ticket `modified` changed?)."""
		comments, tasks = frappe.db.count("Comment"), frappe.db.count("Task")
		modified = frappe.db.get_value("HD Ticket", self.ticket.name, "modified")
		self._gateway(*self._answer_turns())
		self._run("comment_mention")
		return (
			frappe.db.count("Comment") - comments,
			frappe.db.count("Task") - tasks,
			frappe.db.get_value("HD Ticket", self.ticket.name, "modified") != modified,
		)

	def test_feature_adds_no_comment_task_or_ticket_change(self):
		frappe.db.savepoint("erp_ai_changes")
		try:
			self._set_delay(3, 5)
			on = self._count_changes()
			signals_on = len(self.signals)
			frappe.db.rollback(save_point="erp_ai_changes")

			self.signals.clear()
			frappe.db.set_single_value(SETTING_DOCTYPE, "thinking_text", "")
			self._set_delay(0, 0)
			off = self._count_changes()
		finally:
			frappe.db.rollback(save_point="erp_ai_changes")

		# the same stub answered in both runs; only the status signals differ
		self.assertEqual(on[0], 1)
		self.assertGreater(signals_on, 0)
		self.assertEqual(self.signals, [])
		self.assertEqual(on, off)

	def test_end_status_never_raises_when_logging_fails(self):
		status = runner.RunStatus(self.ticket.name, "run1", THINKING_TEXT)
		status.start()
		status._errors.append("status_done: RuntimeError")
		delay = answer_delay.AnswerDelay(4, 0)

		with (
			patch.object(frappe, "log_error", side_effect=RuntimeError("log_error down")),
			patch.object(frappe, "logger", side_effect=RuntimeError("logger down")),
		):
			runner._end_status(status, delay, self.ticket.name, "run1", "comment_mention")

		self.assertEqual(self._states(), ["thinking", "done"])

	def test_failing_error_log_does_not_replace_the_run_exception(self):
		self._gateway(make_model_result(text="xong"))

		def failing_done(event, message, room=None):
			if message["state"] == "done":
				raise RuntimeError("done failed")

		with (
			patch("frappe.realtime.emit_via_redis", side_effect=failing_done),
			patch.object(frappe, "log_error", side_effect=OSError("log_error down")),
			patch.object(runner, "build_initial_message", side_effect=ValueError("the run's own error")),
		):
			with self.assertRaises(ValueError):
				runner._run(self.ticket.name, "comment_mention")
