import json
import time
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.agent import answer_delay, authority, runner
from erp_ai.agent.classification import DEFAULT_CATEGORY_MAPPING
from erp_ai.agent.prompts import TASK_COMMENT, TASK_NEW_TICKET, build_classify_request, build_reason_system
from erp_ai.agent.run_log import write_entry
from erp_ai.agent.tools.read import TOOL_RESULT_MAX_CHARS
from erp_ai.agent.tools.registry import get_tool_schemas
from erp_ai.constants import (
	AGENT_USER,
	CLASSIFIED_BY_AI,
	CLASSIFIED_BY_HUMAN,
	CREDENTIAL_DOCTYPE,
	JOB_SAFETY_MARGIN_S,
	JOB_TIMEOUT_S,
	KEY_STATUS_BAD_KEY,
	LOG_DOCTYPE,
	TITLE_RUN_FAILED,
	TITLE_WRONG_USER,
)
from erp_ai.gateway import GatewayError
from erp_ai.test_utils import (
	FakeGateway,
	add_credential,
	make_model_result,
	make_routing_rules,
	record_status_signals,
	set_agent_settings,
)

PREFIX = "ERPAI-TEST-"
CLASSIFY_A = json.dumps({"dau_muc": "A", "do_tin_cay": "Cao", "ly_do": "x"})
TICKET_FIELDS = [
	"ticket_type",
	"agent_group",
	"priority",
	"status",
	"subject",
	"modified",
	"ai_classified_by",
	"ai_confidence",
	"ai_updated_at",
	"ai_resolution_hint",
]
DAILY_LIMIT = 2  # not the DocType default (5), so the run must read the Setting


def tool_use(block_id, tool_name, /, **arguments):
	return {"type": "tool_use", "id": block_id, "name": tool_name, "input": arguments}


def tool_turn(*blocks, **fields):
	return make_model_result(content=list(blocks), stop_reason="tool_use", **fields)


class RunnerTestBase(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		self.addCleanup(frappe.set_user, "Administrator")
		commit_guard = patch.object(frappe.db, "commit", side_effect=AssertionError("test must not commit"))
		commit_guard.start()
		self.addCleanup(commit_guard.stop)
		# Create the ticket before enabling the agent so the insert handler enqueues nothing.
		self.ticket = make_ticket(subject=f"{PREFIX}runner ticket")
		set_agent_settings(
			enabled=1,
			permission_level="L0",
			max_runs_per_ticket_per_day=DAILY_LIMIT,
			category_mapping=json.dumps(DEFAULT_CATEGORY_MAPPING),
			answer_delay_min_s=0,
			answer_delay_max_s=0,
			routing_rules=make_routing_rules(),
		)
		# No status signal reaches Redis and no run sleeps for real (the delay is 0 here; a test that sets one reads `sleeps`).
		self.signals = record_status_signals(self)
		self.sleeps = []
		sleep_patch = patch.object(answer_delay, "_sleep", side_effect=self.sleeps.append)
		sleep_patch.start()
		self.addCleanup(sleep_patch.stop)
		self.gateway = FakeGateway(make_model_result(text=CLASSIFY_A))
		gateway_patch = patch("erp_ai.gateway.call_model", self.gateway)
		gateway_patch.start()
		self.addCleanup(gateway_patch.stop)

	def _entries(self, **filters):
		return frappe.get_all(
			LOG_DOCTYPE,
			filters={"ticket": self.ticket.name, **filters},
			fields=["*"],
			order_by="creation asc",
		)

	def _run(self, trigger="ticket_insert"):
		runner.run_for_ticket(self.ticket.name, trigger)

	def _comment_count(self):
		return frappe.db.count("Comment", authority.ticket_comment_filters(self.ticket.name))

	def _seed_runs(self, count):
		for index in range(count):
			write_entry(
				ticket=self.ticket.name,
				run_id=f"{PREFIX}run-{index}",
				entry_type="classify",
				trigger="ticket_insert",
				turn=0,
			)


class TestRunner(RunnerTestBase):
	# (a) account

	def test_wrong_session_user_stops_before_model(self):
		with (
			patch.object(frappe, "set_user"),
			patch.object(frappe, "log_error") as log_error,
			patch.object(frappe.db, "get_value", wraps=frappe.db.get_value) as get_value,
		):
			self._run()

		log_error.assert_called_once_with(TITLE_WRONG_USER, "Sai tài khoản: Administrator")
		self.assertEqual(self.gateway.call_count, 0)
		self.assertEqual(self._entries(), [])
		self.assertEqual([c for c in get_value.call_args_list if c.args[0] == "HD Ticket"], [])

	def test_missing_agent_user_stops(self):
		with (
			patch.object(runner, "AGENT_USER", f"{PREFIX.lower()}missing@example.com"),
			patch.object(frappe, "log_error") as log_error,
		):
			self._run()

		log_error.assert_called_once_with(TITLE_WRONG_USER, "Không có tài khoản agent")
		self.assertEqual(self.gateway.call_count, 0)
		self.assertEqual(frappe.session.user, "Administrator")

	def test_disabled_agent_user_stops(self):
		frappe.db.set_value("User", AGENT_USER, "enabled", 0)
		with patch.object(frappe, "log_error") as log_error:
			self._run()

		log_error.assert_called_once_with(TITLE_WRONG_USER, "Không có tài khoản agent")
		self.assertEqual(self.gateway.call_count, 0)

	# (b) (c) (d)

	def test_disabled_at_run_time_no_model_call(self):
		set_agent_settings(enabled=0)
		self._run()

		self.assertEqual(self.gateway.call_count, 0)
		self.assertEqual(self._entries(), [])

	def test_not_sendable_at_run_time_no_model_call(self):
		frappe.db.set_value("HD Ticket", self.ticket.name, "ai_opt_out", 1)
		self._run()

		self.assertEqual(self.gateway.call_count, 0)
		entries = self._entries()
		self.assertEqual([(e.entry_type, e.stop_reason) for e in entries], [("skip", "not_sendable")])
		self.assertEqual(entries[0].trigger, "ticket_insert")

	def test_run_over_setting_limit_same_day_no_call(self):
		self._seed_runs(DAILY_LIMIT)
		self._run()

		self.assertEqual(self.gateway.call_count, 0)
		skips = self._entries(entry_type="skip")
		self.assertEqual([e.stop_reason for e in skips], ["daily_limit"])

	def test_last_run_within_setting_limit_still_calls(self):
		self._seed_runs(DAILY_LIMIT - 1)
		self._run()

		self.assertEqual(self.gateway.call_count, 1)
		self.assertEqual(self._entries(entry_type="skip"), [])

	def test_disabled_and_not_sendable_writes_no_log(self):
		set_agent_settings(enabled=0)
		frappe.db.set_value("HD Ticket", self.ticket.name, "ai_opt_out", 1)
		self._run()

		self.assertEqual(self._entries(), [])

	def test_not_sendable_wins_over_daily_limit(self):
		frappe.db.set_value("HD Ticket", self.ticket.name, "ai_opt_out", 1)
		self._seed_runs(DAILY_LIMIT)
		self._run()

		self.assertEqual([e.stop_reason for e in self._entries(entry_type="skip")], ["not_sendable"])

	def test_deleted_ticket_logs_skip_without_failing(self):
		missing = f"{PREFIX}missing-ticket"
		before = set(frappe.get_all(LOG_DOCTYPE, pluck="name"))
		with patch.object(frappe, "log_error") as log_error:
			runner.run_for_ticket(missing, "ticket_insert")

		log_error.assert_not_called()
		new_rows = [
			row
			for row in frappe.get_all(
				LOG_DOCTYPE, fields=["name", "entry_type", "stop_reason", "ticket", "error"]
			)
			if row.name not in before
		]
		self.assertEqual(
			[(r.entry_type, r.stop_reason, r.ticket, r.error) for r in new_rows],
			[("skip", "not_sendable", None, f"ticket_missing {missing}")],
		)
		self.assertEqual(self.gateway.call_count, 0)

	# (e) and classification step at L0

	def test_l0_logs_prediction_ticket_unchanged(self):
		self.ticket.add_comment("Comment", f"{PREFIX}human comment")
		frappe.db.set_value(
			"HD Ticket",
			self.ticket.name,
			{
				"ai_classified_by": CLASSIFIED_BY_HUMAN,
				"ai_confidence": "Thấp",
				"ai_resolution_hint": f"{PREFIX}hint",
			},
		)
		before = frappe.db.get_value("HD Ticket", self.ticket.name, TICKET_FIELDS, as_dict=True)
		comments_before = self._comment_count()
		self.assertEqual(comments_before, 1)
		self._run()

		after = frappe.db.get_value("HD Ticket", self.ticket.name, TICKET_FIELDS, as_dict=True)
		self.assertEqual(before, after)
		self.assertEqual(self._comment_count(), comments_before)
		self.assertEqual(self.gateway.call_count, 1)
		call = self.gateway.calls[0]
		self.assertEqual(call["task"], "classify")
		self.assertEqual(call["max_tokens"], 600)
		expected = build_classify_request(self.ticket.subject, self.ticket.description)
		self.assertEqual((call["system"], call["messages"]), (expected["system"], expected["messages"]))

		(entry,) = self._entries()
		mapped = DEFAULT_CATEGORY_MAPPING["A"]
		self.assertEqual((entry.entry_type, entry.turn, entry.trigger), ("classify", 0, "ticket_insert"))
		self.assertEqual(entry.owner, AGENT_USER)
		self.assertRegex(entry.run_id, r"^[0-9a-f]{32}$")
		self.assertEqual((entry.predicted_category, entry.predicted_confidence), ("A", "Cao"))
		self.assertEqual(
			(entry.predicted_ticket_type, entry.predicted_agent_group, entry.predicted_priority),
			(mapped["ticket_type"], mapped["agent_group"], mapped["priority"]),
		)
		self.assertEqual(
			(entry.applied, entry.model, entry.credential_label, entry.stop_reason),
			(0, "fake-model", "fake", "end_turn"),
		)
		self.assertFalse(entry.skipped_fields)

	def test_deadline_follows_job_timeout_constants(self):
		with (
			patch.object(runner, "JOB_TIMEOUT_S", 100),
			patch.object(runner, "JOB_SAFETY_MARGIN_S", 30),
		):
			self._run()

		remaining = self.gateway.calls[0]["deadline"] - time.monotonic()
		self.assertGreater(remaining, 60)
		self.assertLessEqual(remaining, 70)

	def test_default_deadline_is_job_timeout_minus_margin(self):
		self._run()

		remaining = self.gateway.calls[0]["deadline"] - time.monotonic()
		self.assertGreater(remaining, JOB_TIMEOUT_S - JOB_SAFETY_MARGIN_S - 10)
		self.assertLessEqual(remaining, JOB_TIMEOUT_S - JOB_SAFETY_MARGIN_S)

	def test_classify_entry_records_usage_cost_and_keys(self):
		usage = {
			"input_tokens": 11,
			"output_tokens": 12,
			"cache_creation_input_tokens": 13,
			"cache_read_input_tokens": 14,
		}
		self.gateway.results = [
			make_model_result(
				text=CLASSIFY_A,
				usage=usage,
				cost_usd=0.000123,
				latency_ms=77,
				keys_tried=[{"label": "fake", "outcome": "ok"}],
			)
		]
		self._run()

		(entry,) = self._entries()
		self.assertEqual(
			(
				entry.input_tokens,
				entry.output_tokens,
				entry.cache_creation_input_tokens,
				entry.cache_read_input_tokens,
			),
			(11, 12, 13, 14),
		)
		self.assertEqual((entry.cost_usd, entry.latency_ms), (0.000123, 77))
		self.assertEqual(json.loads(entry.keys_tried), [{"label": "fake", "outcome": "ok"}])

	def test_urgent_subject_prediction_is_urgent(self):
		frappe.db.set_value("HD Ticket", self.ticket.name, "subject", f"[GẤP] {PREFIX}runner")
		self._run()

		(entry,) = self._entries()
		self.assertEqual(entry.predicted_priority, "Urgent")

	def test_bad_mapping_error_logged_without_failing(self):
		set_agent_settings(category_mapping="not json")
		with patch.object(frappe, "log_error") as log_error:
			self._run()

		log_error.assert_not_called()
		(entry,) = self._entries()
		self.assertEqual(entry.error, runner.BAD_MAPPING_ERROR)
		self.assertEqual(entry.predicted_category, "A")

	def test_l0_comment_mention_skipped_no_call(self):
		self._run("comment_mention")

		self.assertEqual(self.gateway.call_count, 0)
		entries = self._entries()
		self.assertEqual(
			[(e.entry_type, e.stop_reason, e.trigger) for e in entries],
			[("skip", "level_L0", "comment_mention")],
		)

	def test_l1_comment_mention_is_not_skipped_as_level_l0(self):
		set_agent_settings(permission_level="L1")
		self._run("comment_mention")

		self.assertEqual(self._entries(entry_type="skip"), [])

	def test_unparseable_classification_logged_run_continues(self):
		self.gateway.results = [make_model_result(text="không phải JSON", cost_usd=0.5)]
		with patch.object(frappe, "log_error") as log_error:
			self._run()

		log_error.assert_not_called()
		(entry,) = self._entries()
		self.assertEqual(entry.entry_type, "classify")
		self.assertEqual((entry.error, entry.stop_reason), (runner.UNPARSEABLE_ERROR, "unparseable"))
		self.assertFalse(entry.predicted_category)
		self.assertEqual(entry.cost_usd, 0.5)

	def test_gateway_error_logged_run_ends_cleanly(self):
		self.gateway.results = [
			GatewayError(
				"all_keys_failed",
				status=529,
				credential_label="k2",
				request_id="req_x",
				keys_tried=[
					{"label": "k1", "outcome": "overloaded"},
					{"label": "k2", "outcome": "overloaded"},
				],
			)
		]
		with patch.object(frappe, "log_error") as log_error:
			self._run()

		log_error.assert_not_called()
		(entry,) = self._entries()
		self.assertEqual(entry.entry_type, "classify")
		self.assertEqual((entry.error, entry.stop_reason), ("all_keys_failed status=529", "gateway_error"))
		self.assertEqual(entry.credential_label, "k2")
		self.assertEqual(len(json.loads(entry.keys_tried)), 2)

	# error path

	def test_unexpected_exception_logged_with_two_arguments_not_raised(self):
		def boom(task, **kwargs):
			raise RuntimeError("sk-secret-should-not-appear")

		with patch("erp_ai.gateway.call_model", boom), patch.object(frappe, "log_error") as log_error:
			self._run()

		log_error.assert_called_once()
		args, kwargs = log_error.call_args
		self.assertEqual(kwargs, {})
		self.assertEqual(
			args,
			(TITLE_RUN_FAILED, f"ticket={self.ticket.name} trigger=ticket_insert error=RuntimeError"),
		)

	# DEBT: breaker state survives a failed run

	def _simulate_key_failure_then(self, error):
		"""Run with a gateway that changes a key's status (as `apply_failure` does) and then raises `error`.

		Commits are not real: `frappe.flags.in_test` is forced False so the runner takes its production path,
		and commit/rollback are recorded in order with the key status visible at that moment.
		"""
		key_row = add_credential(f"{PREFIX}key")
		events = []

		def failing_gateway(task, **kwargs):
			frappe.db.set_value(
				CREDENTIAL_DOCTYPE, key_row, {"status": KEY_STATUS_BAD_KEY}, update_modified=False
			)
			events.append(("gateway_write",))
			raise error

		def record_commit():
			events.append(("commit", frappe.db.get_value(CREDENTIAL_DOCTYPE, key_row, "status")))

		def record_rollback(*args, **kwargs):
			events.append(("rollback",))

		def record_log_entry(**fields):
			events.append(("log_entry",))
			return write_entry(**fields)

		self.addCleanup(setattr, frappe.flags, "in_test", frappe.flags.in_test)
		frappe.flags.in_test = False
		with (
			patch("erp_ai.gateway.call_model", failing_gateway),
			patch.object(frappe.db, "commit", side_effect=record_commit),
			patch.object(frappe.db, "rollback", side_effect=record_rollback),
			patch.object(runner, "write_entry", side_effect=record_log_entry),
			patch.object(frappe, "log_error"),
		):
			self._run()
		return events

	def test_key_state_committed_before_log_after_gateway_error(self):
		error = GatewayError("all_keys_failed", status=401, credential_label=f"{PREFIX}key")
		events = self._simulate_key_failure_then(error)

		self.assertEqual(events[:3], [("gateway_write",), ("commit", KEY_STATUS_BAD_KEY), ("log_entry",)])
		self.assertNotIn(("rollback",), events)

	def test_key_state_committed_and_not_rolled_back_when_run_fails(self):
		events = self._simulate_key_failure_then(RuntimeError("boom"))

		self.assertEqual(events, [("gateway_write",), ("commit", KEY_STATUS_BAD_KEY)])


L1_TYPE = f"{PREFIX}loại"
L1_TEAM = f"{PREFIX}nhóm"
CLASSIFY_FIELDS = (
	"ticket_type",
	"agent_group",
	"priority",
	"ai_confidence",
	"ai_classified_by",
	"status",
	"ai_resolution_hint",
)


ASSIGNEE_NOTE = {"field": "assignee", "reason": "cấu hình không có người cho đầu mục A"}


class TestRunnerL1Classification(RunnerTestBase):
	"""Classification step at L1 (T29): the tool applies it, the run itself records the outcome."""

	def setUp(self):
		super().setUp()
		# Cleanups run LIFO: set_user, rollback, then the stale Redis rule map (HD Team.after_insert).
		self.addCleanup(frappe.cache.hdel, "assignment_rule_map", "HD Ticket")
		frappe.set_user("Administrator")
		if not frappe.db.exists("HD Ticket Type", L1_TYPE):
			frappe.get_doc({"doctype": "HD Ticket Type", "name": L1_TYPE}).insert()
		if not frappe.db.exists("HD Team", L1_TEAM):
			frappe.get_doc(
				{"doctype": "HD Team", "team_name": L1_TEAM, "users": [{"user": AGENT_USER}]}
			).insert()
		self.mapping = {"A": {"ticket_type": L1_TYPE, "agent_group": L1_TEAM, "priority": "High"}}
		set_agent_settings(permission_level="L1", category_mapping=json.dumps(self.mapping))
		log_error = patch.object(frappe, "log_error")
		self.log_error = log_error.start()
		self.addCleanup(log_error.stop)

	def _ticket_row(self):
		return frappe.db.get_value("HD Ticket", self.ticket.name, CLASSIFY_FIELDS, as_dict=True)

	def _single_entry(self):
		(entry,) = self._entries(entry_type="classify")
		return entry

	def test_l1_applies_mapping_confidence_and_hint(self):
		before = self._ticket_row()
		self.gateway.results = [
			make_model_result(text=CLASSIFY_A),
			tool_turn(tool_use("toolu_hint", "set_resolution_hint", text=f"{PREFIX}hướng giải quyết")),
			make_model_result(stop_reason="end_turn"),
		]
		self._run()

		self.log_error.assert_not_called()
		row = self._ticket_row()
		self.assertIn(f"{PREFIX}hướng giải quyết", row.ai_resolution_hint)
		self.assertFalse(before.ai_resolution_hint)
		self.assertEqual((row.ticket_type, row.agent_group, row.priority), (L1_TYPE, L1_TEAM, "High"))
		self.assertEqual((row.ai_confidence, row.ai_classified_by), ("Cao", CLASSIFIED_BY_AI))
		self.assertEqual(row.status, before.status)
		entry = self._single_entry()
		self.assertEqual(entry.applied, 1)
		self.assertEqual(json.loads(entry.value_before)["ticket"]["ticket_type"], before.ticket_type)
		self.assertEqual(
			json.loads(entry.value_after),
			{
				"ticket": {
					"ticket_type": L1_TYPE,
					"agent_group": L1_TEAM,
					"priority": "High",
					"ai_confidence": "Cao",
					"ai_score_reason": "",
				}
			},
		)
		self.assertEqual(
			json.loads(entry.actions),
			[{"tool": "apply_route", "doctype": "HD Ticket", "name": self.ticket.name, "ok": True}],
		)
		self.assertEqual((entry.predicted_category, entry.predicted_confidence), ("A", "Cao"))
		self.assertEqual(json.loads(entry.skipped_fields), [ASSIGNEE_NOTE])

	def test_l1_human_classified_not_overwritten(self):
		frappe.db.set_value("HD Ticket", self.ticket.name, "ai_classified_by", CLASSIFIED_BY_HUMAN)
		before = self._ticket_row()
		self._run()

		self.assertEqual(self._ticket_row(), before)
		entry = self._single_entry()
		self.assertEqual(entry.applied, 0)
		self.assertFalse(entry.value_after)
		self.assertEqual(
			json.loads(entry.actions),
			[
				{
					"tool": "apply_route",
					"doctype": "HD Ticket",
					"name": self.ticket.name,
					"ok": False,
					"reason": "người đã phân loại, không ghi đè",
				}
			],
		)
		self.assertFalse(entry.skipped_fields)

	def test_l1_empty_route_still_saves_ai_fields_applied_one(self):
		unknown = {"A": {"ticket_type": f"{PREFIX}không-có", "agent_group": "", "priority": ""}}
		set_agent_settings(category_mapping=json.dumps(unknown))
		before = self._ticket_row()
		self._run()

		# ADR-020 QĐ 1, QĐ 6: the ticket is always saved with the AI fields, even when no route value applies.
		self.assertEqual(
			self._ticket_row(),
			{**before, "ai_confidence": "Cao", "ai_classified_by": CLASSIFIED_BY_AI},
		)
		entry = self._single_entry()
		self.assertEqual(entry.applied, 1)
		self.assertEqual(
			json.loads(entry.value_after),
			{"ticket": {"ai_confidence": "Cao", "ai_score_reason": ""}},
		)
		self.assertEqual(
			json.loads(entry.actions),
			[
				{"tool": "apply_route", "doctype": "HD Ticket", "name": self.ticket.name, "ok": True},
				{
					"tool": "sla_check",
					"doctype": "HD Ticket",
					"name": self.ticket.name,
					"ok": False,
					"reason": "SLA Standard xử lý 1440 phút > mong đợi 480 phút (A)",
				},
			],
		)
		skipped = json.loads(entry.skipped_fields)
		self.assertIn("ticket_type", [item["field"] for item in skipped])
		self.assertIn(ASSIGNEE_NOTE, skipped)

	def test_l1_missing_value_reason_logged_on_classify_entry(self):
		self.mapping["A"]["ticket_type"] = f"{PREFIX}không-có"
		set_agent_settings(category_mapping=json.dumps(self.mapping))
		before = self._ticket_row()
		self._run()

		row = self._ticket_row()
		self.assertEqual(row.ticket_type, before.ticket_type)
		self.assertEqual((row.agent_group, row.priority), (L1_TEAM, "High"))
		entry = self._single_entry()
		self.assertEqual(entry.applied, 1)
		self.assertNotIn("ticket_type", json.loads(entry.value_after)["ticket"])
		self.assertEqual(
			json.loads(entry.skipped_fields),
			[
				{"field": "ticket_type", "reason": "giá trị không tồn tại trên hệ thống"},
				ASSIGNEE_NOTE,
			],
		)

	def test_l1_all_fields_skipped_reasons_logged_saves_ai_fields_applied_one(self):
		unknown = {"A": {"ticket_type": f"{PREFIX}không-có", "agent_group": "", "priority": ""}}
		set_agent_settings(category_mapping=json.dumps(unknown))
		before = self._ticket_row()
		self._run()

		# ADR-020 QĐ 1, QĐ 6: the ticket is always saved with the AI fields; no route field changes.
		self.assertEqual(
			self._ticket_row(),
			{**before, "ai_confidence": "Cao", "ai_classified_by": CLASSIFIED_BY_AI},
		)
		entry = self._single_entry()
		self.assertEqual(entry.applied, 1)
		self.assertEqual(
			set(json.loads(entry.value_after)["ticket"]),
			{"ai_confidence", "ai_score_reason"},
		)
		self.assertEqual(
			json.loads(entry.actions),
			[
				{"tool": "apply_route", "doctype": "HD Ticket", "name": self.ticket.name, "ok": True},
				{
					"tool": "sla_check",
					"doctype": "HD Ticket",
					"name": self.ticket.name,
					"ok": False,
					"reason": "SLA Standard xử lý 1440 phút > mong đợi 480 phút (A)",
				},
			],
		)
		self.assertEqual(
			json.loads(entry.skipped_fields),
			[
				{"field": "ticket_type", "reason": "giá trị không tồn tại trên hệ thống"},
				{"field": "agent_group", "reason": "ánh xạ không có giá trị"},
				{"field": "priority", "reason": "ánh xạ không có giá trị"},
				ASSIGNEE_NOTE,
			],
		)

	def test_apply_failure_leaves_skipped_fields_empty(self):
		self.mapping["A"]["ticket_type"] = f"{PREFIX}không-có"
		set_agent_settings(category_mapping=json.dumps(self.mapping))
		before = self._ticket_row()
		real_set_value = frappe.db.set_value

		def failing_set_value(doctype, *args, **kwargs):
			if doctype == LOG_DOCTYPE:
				raise RuntimeError("boom")
			return real_set_value(doctype, *args, **kwargs)

		with patch.object(frappe.db, "set_value", side_effect=failing_set_value):
			self._run()

		self.log_error.assert_called_once()
		self.assertEqual(self.log_error.call_args.args[0], TITLE_RUN_FAILED)
		self.assertEqual(self._ticket_row(), before)
		entry = self._single_entry()
		self.assertEqual(entry.applied, 0)
		self.assertFalse(entry.skipped_fields)

	def test_not_ok_result_with_after_is_not_applied(self):
		failed = {"ok": False, "reason": "x", "before": {}, "after": {"priority": "High"}}
		with patch.object(runner, "apply_route", return_value=failed):
			self._run()

		self.assertEqual(self._single_entry().applied, 0)

	def test_failure_after_tool_rolls_ticket_back_and_keeps_entry(self):
		before = self._ticket_row()
		real_set_value = frappe.db.set_value

		def failing_set_value(doctype, *args, **kwargs):
			if doctype == LOG_DOCTYPE:
				raise RuntimeError("boom")
			return real_set_value(doctype, *args, **kwargs)

		with patch.object(frappe.db, "set_value", side_effect=failing_set_value):
			self._run()

		self.log_error.assert_called_once()
		self.assertEqual(self.log_error.call_args.args[0], TITLE_RUN_FAILED)
		self.assertEqual(self._ticket_row(), before)
		entry = self._single_entry()
		self.assertEqual(entry.applied, 0)
		self.assertEqual(entry.predicted_category, "A")

	def test_ticket_change_is_never_committed_before_its_log_outcome(self):
		snapshots = []

		def record_commit():
			ticket_by = frappe.db.get_value("HD Ticket", self.ticket.name, "ai_classified_by")
			applied = frappe.db.get_value(
				LOG_DOCTYPE, {"ticket": self.ticket.name, "entry_type": "classify"}, "applied"
			)
			snapshots.append((ticket_by, applied))

		self.addCleanup(setattr, frappe.flags, "in_test", frappe.flags.in_test)
		frappe.flags.in_test = False
		with patch.object(frappe.db, "commit", side_effect=record_commit):
			self._run()

		self.assertTrue(snapshots)
		self.assertEqual(snapshots[-1], (CLASSIFIED_BY_AI, 1))
		self.assertNotIn((CLASSIFIED_BY_AI, 0), snapshots)
		self.assertNotIn((CLASSIFIED_BY_AI, None), snapshots)

	def test_l0_still_does_not_apply(self):
		set_agent_settings(permission_level="L0")
		before = self._ticket_row()
		with patch.object(runner, "execute_tool") as execute_tool:
			self._run()

		execute_tool.assert_not_called()
		self.assertEqual(self._ticket_row(), before)
		self.assertEqual(self._single_entry().applied, 0)


class TestRunnerReasoning(RunnerTestBase):
	"""Reasoning loop (T30, design 4.3 step 8) on a comment mention, so the first model call is a reason turn."""

	def setUp(self):
		super().setUp()
		set_agent_settings(permission_level="L1")
		log_error = patch.object(frappe, "log_error")
		self.log_error = log_error.start()
		self.addCleanup(log_error.stop)

	def _reason_entries(self):
		return self._entries(entry_type="reason")

	def _user_message(self, call_index=0):
		content = self.gateway.calls[call_index]["messages"][0]["content"]
		return json.JSONDecoder().raw_decode(content)[0], content

	# AC-15

	def test_stops_after_max_turns(self):
		set_agent_settings(max_turns_per_run=8)
		self.gateway.results = [tool_turn(tool_use(f"toolu_{i}", "get_ticket")) for i in range(12)]
		self._run("comment_mention")

		entries = self._reason_entries()
		self.assertEqual(self.gateway.call_count, 8)
		self.assertEqual([e.turn for e in entries], [1, 2, 3, 4, 5, 6, 7, 8])
		self.assertEqual([e.stop_reason for e in entries], ["tool_use"] * 7 + ["max_turns"])

	def test_max_turns_follows_setting(self):
		set_agent_settings(max_turns_per_run=3)
		self.gateway.results = [tool_turn(tool_use(f"toolu_{i}", "get_ticket")) for i in range(12)]
		self._run("comment_mention")

		self.assertEqual(self.gateway.call_count, 3)
		self.assertEqual(
			[e.stop_reason for e in self._reason_entries()], ["tool_use", "tool_use", "max_turns"]
		)

	def test_end_turn_on_last_turn_is_not_max_turns(self):
		set_agent_settings(max_turns_per_run=2)
		self.gateway.results = [tool_turn(tool_use("toolu_1", "get_ticket")), make_model_result()]
		self._run("comment_mention")

		self.assertEqual([e.stop_reason for e in self._reason_entries()], ["tool_use", "end_turn"])

	def test_tool_use_without_blocks_stops(self):
		self.gateway.results = [tool_turn(), tool_turn(tool_use("toolu_1", "get_ticket"))]
		self._run("comment_mention")

		self.assertEqual(self.gateway.call_count, 1)
		self.assertEqual([e.stop_reason for e in self._reason_entries()], ["tool_use"])

	def test_turn_log_fields(self):
		hint = f"{PREFIX}gợi ý"
		first_keys = [{"label": "key-1", "outcome": "ok"}]
		self.gateway.results = [
			tool_turn(
				tool_use("toolu_1", "set_resolution_hint", text=hint),
				tool_use("toolu_2", "get_ticket"),
				model="model-x",
				usage={
					"input_tokens": 100,
					"output_tokens": 20,
					"cache_creation_input_tokens": 30,
					"cache_read_input_tokens": 40,
				},
				cost_usd=0.0125,
				credential_label="key-1",
				keys_tried=first_keys,
				latency_ms=250,
			),
			make_model_result(
				usage={"input_tokens": 7, "output_tokens": 3, "cache_read_input_tokens": 5},
				cost_usd=0.0075,
				credential_label="key-2",
				latency_ms=90,
			),
		]
		with patch.object(authority, "latest_instructor", return_value="Administrator"):
			self._run("comment_mention")

		first, second = self._reason_entries()
		self.assertEqual(
			(first.turn, first.trigger, first.instructor), (1, "comment_mention", "Administrator")
		)
		self.assertEqual((first.model, first.credential_label, first.latency_ms), ("model-x", "key-1", 250))
		self.assertEqual(
			(
				first.input_tokens,
				first.output_tokens,
				first.cache_creation_input_tokens,
				first.cache_read_input_tokens,
			),
			(100, 20, 30, 40),
		)
		self.assertEqual(first.cost_usd, 0.0125)
		self.assertEqual(json.loads(first.keys_tried), first_keys)
		self.assertEqual(first.stop_reason, "tool_use")
		self.assertEqual(json.loads(first.tools_called), ["set_resolution_hint", "get_ticket"])
		self.assertEqual(
			json.loads(first.actions),
			[{"tool": "set_resolution_hint", "doctype": "HD Ticket", "name": self.ticket.name, "ok": True}],
		)
		stored_hint = frappe.db.get_value("HD Ticket", self.ticket.name, "ai_resolution_hint")
		self.assertIn(hint, stored_hint)
		self.assertEqual(json.loads(first.value_after), {"set_resolution_hint": stored_hint})
		self.assertEqual(json.loads(first.value_before), {"set_resolution_hint": None})
		# a missing usage count is stored as 0; the second turn has its own cost, tokens and no tools
		self.assertEqual((second.turn, second.stop_reason, second.cost_usd), (2, "end_turn", 0.0075))
		self.assertEqual(
			(
				second.input_tokens,
				second.output_tokens,
				second.cache_creation_input_tokens,
				second.cache_read_input_tokens,
			),
			(7, 3, 0, 5),
		)
		self.assertFalse(second.tools_called or second.actions or second.value_after)
		# the cost is the gateway's figure stored as given; the run total is the hand-added 0.0125 + 0.0075
		self.assertAlmostEqual(first.cost_usd + second.cost_usd, 0.02, places=6)
		self.assertEqual(first.run_id, second.run_id)

	# AC-8, request shape

	def test_request_uses_tools_system_and_budget_of_the_run(self):
		set_agent_settings(prompt_digest=f"{PREFIX}digest")
		self._run("comment_mention")

		(call,) = self.gateway.calls
		self.assertEqual(call["task"], "reason")
		self.assertEqual(call["max_tokens"], 4096)
		self.assertGreater(call["deadline"], time.monotonic())
		self.assertEqual(call["system"], build_reason_system(f"{PREFIX}digest"))
		names = [tool["name"] for tool in call["tools"]]
		self.assertIn("set_resolution_hint", names)
		self.assertNotIn("create_task", names)
		self.assertEqual(call["tools"][-1]["cache_control"], {"type": "ephemeral"})
		self.assertTrue(all("cache_control" not in tool for tool in call["tools"][:-1]))
		self.assertTrue(all("cache_control" not in tool for tool in get_tool_schemas("L1", False)))

	def test_create_task_offered_only_with_instructor(self):
		with patch.object(authority, "latest_instructor", return_value="Administrator"):
			self._run("comment_mention")

		self.assertIn("create_task", [tool["name"] for tool in self.gateway.calls[0]["tools"]])

	def test_initial_message_carries_comments_by_full_name_and_classification(self):
		comments = [
			{"name": "c1", "author": "Administrator", "creation": "2026-01-01", "content": "<p>xin chào</p>"}
		]
		with (
			patch.object(authority, "latest_instructor", return_value=None),
			patch.object(authority, "fetch_ticket_comments", return_value=comments) as fetch,
			patch.object(authority, "is_instruction", wraps=authority.is_instruction) as is_instruction,
			patch.object(runner, "get_fullname", return_value=f"{PREFIX}Họ Tên") as get_fullname,
		):
			self._run("comment_mention")

		fetch.assert_called_once_with(self.ticket.name)
		is_instruction.assert_called_with("Administrator", self.ticket.name)
		get_fullname.assert_called_once_with("Administrator")
		payload, content = self._user_message()
		self.assertEqual(
			[(c["author"], c["role"], c["content"]) for c in payload["comments"]],
			[(f"{PREFIX}Họ Tên", "dữ liệu", "xin chào")],
		)
		self.assertEqual(payload["trigger"], "comment_mention")
		self.assertIsNone(payload["classification"])
		self.assertEqual(payload["ticket"]["subject"], f"{PREFIX}runner ticket")
		self.assertTrue(content.endswith(TASK_COMMENT))

	def test_ticket_insert_passes_classification_to_reasoning(self):
		self._run()

		self.assertEqual([c["task"] for c in self.gateway.calls], ["classify", "reason"])
		payload, content = self._user_message(1)
		self.assertEqual(
			(payload["classification"]["category"], payload["classification"]["confidence"]), ("A", "Cao")
		)
		self.assertTrue(content.endswith(TASK_NEW_TICKET))

	# tool_result

	def test_tool_result_matches_tool_use_id(self):
		blocks = [tool_use("toolu_A", "get_ticket"), tool_use("toolu_B", "get_ticket", name="NOPE-999")]
		self.gateway.results = [tool_turn(*blocks), make_model_result()]
		self._run("comment_mention")

		messages = self.gateway.calls[1]["messages"]
		self.assertEqual([m["role"] for m in messages], ["user", "assistant", "user"])
		self.assertEqual(messages[1]["content"], blocks)
		results = messages[2]["content"]
		self.assertEqual(
			[(r["type"], r["tool_use_id"]) for r in results],
			[("tool_result", "toolu_A"), ("tool_result", "toolu_B")],
		)
		self.assertEqual(json.loads(results[1]["content"])["ok"], False)
		self.assertNotIn("is_error", results[1])

	def test_tool_exception_becomes_error_result_and_run_continues(self):
		self.gateway.results = [tool_turn(tool_use("toolu_1", "get_ticket")), make_model_result()]
		with patch.object(runner, "execute_tool", side_effect=KeyError("bí mật")):
			self._run("comment_mention")

		self.log_error.assert_not_called()
		self.assertEqual(
			self.gateway.calls[1]["messages"][2]["content"],
			[{"type": "tool_result", "tool_use_id": "toolu_1", "is_error": True, "content": "Lỗi: KeyError"}],
		)
		first, second = self._reason_entries()
		self.assertEqual(json.loads(first.tools_called), ["get_ticket"])
		self.assertEqual(first.error, "tool get_ticket: KeyError")
		self.assertNotIn("bí mật", first.error)
		self.assertFalse(second.error)
		self.assertEqual(second.stop_reason, "end_turn")

	def test_several_failed_tools_are_joined_in_the_turn_error(self):
		self.gateway.results = [
			tool_turn(
				tool_use("toolu_1", "get_ticket"), tool_use("toolu_2", "set_resolution_hint", text="x")
			),
			make_model_result(),
		]
		with patch.object(runner, "execute_tool", side_effect=RuntimeError("bí mật")):
			self._run("comment_mention")

		first = self._reason_entries()[0]
		self.assertEqual(first.error, "tool get_ticket: RuntimeError; tool set_resolution_hint: RuntimeError")

	def test_failed_write_tool_is_logged_as_not_ok(self):
		self.gateway.results = [
			tool_turn(tool_use("toolu_1", "set_resolution_hint", text="x")),
			make_model_result(),
		]
		with patch.object(runner, "execute_tool", side_effect=RuntimeError):
			self._run("comment_mention")

		first = self._reason_entries()[0]
		self.assertEqual(
			json.loads(first.actions),
			[{"tool": "set_resolution_hint", "doctype": "HD Ticket", "name": self.ticket.name, "ok": False}],
		)
		self.assertFalse(first.value_after)

	def test_comment_and_task_actions_name_the_created_record(self):
		self.gateway.results = [
			tool_turn(
				tool_use("toolu_1", "post_comment", content="x"),
				tool_use("toolu_2", "create_task", subject="s", description="d"),
			),
			make_model_result(),
		]
		results = {
			"post_comment": {"ok": True, "comment": "CMT-1"},
			"create_task": {"ok": False, "reason": "không có người ra lệnh"},
		}
		with patch.object(runner, "execute_tool", side_effect=lambda name, args, ctx: results[name]):
			self._run("comment_mention")

		self.assertEqual(
			json.loads(self._reason_entries()[0].actions),
			[
				{"tool": "post_comment", "doctype": "Comment", "name": "CMT-1", "ok": True},
				{"tool": "create_task", "doctype": "Task", "name": None, "ok": False},
			],
		)

	def test_tool_result_is_cut_for_the_model(self):
		self.gateway.results = [tool_turn(tool_use("toolu_1", "get_ticket")), make_model_result()]
		huge = {"ok": True, "text": "x" * (TOOL_RESULT_MAX_CHARS + 500)}
		with patch.object(runner, "execute_tool", return_value=huge):
			self._run("comment_mention")

		content = self.gateway.calls[1]["messages"][2]["content"][0]["content"]
		self.assertEqual(len(content), TOOL_RESULT_MAX_CHARS)

	def test_one_tool_context_serves_classification_and_reasoning(self):
		self.gateway.results = [
			make_model_result(text=CLASSIFY_A),
			tool_turn(tool_use("toolu_1", "get_ticket")),
			make_model_result(),
		]
		contexts = []

		def spy(name, arguments, context):
			contexts.append(context)
			return {"ok": True}

		def spy_route(decision, classification, context):
			contexts.append(context)
			return {"ok": True}

		with (
			patch.object(runner, "execute_tool", side_effect=spy),
			patch.object(runner, "apply_route", side_effect=spy_route),
			patch.object(runner, "ToolContext", wraps=runner.ToolContext) as make_context,
		):
			self._run()

		make_context.assert_called_once()
		self.assertEqual([c.ticket_name for c in contexts], [self.ticket.name] * 2)
		self.assertIs(contexts[0], contexts[1])

	# stops

	def test_deadline_error_logs_time_budget(self):
		self.gateway.results = [
			tool_turn(tool_use("toolu_1", "get_ticket")),
			GatewayError("deadline", keys_tried=[{"label": "k", "outcome": "ok"}]),
		]
		self._run("comment_mention")

		self.log_error.assert_not_called()
		first, second = self._reason_entries()
		self.assertEqual(first.stop_reason, "tool_use")
		self.assertEqual((second.turn, second.stop_reason), (2, "time_budget"))
		self.assertEqual(self.gateway.call_count, 2)

	def test_other_gateway_error_logs_gateway_error(self):
		self.gateway.results = [GatewayError("server_error", status=500, credential_label="k")]
		self._run("comment_mention")

		(entry,) = self._reason_entries()
		self.assertEqual((entry.stop_reason, entry.error), ("gateway_error", "server_error status=500"))
		self.assertEqual(entry.credential_label, "k")

	def test_unparseable_classification_still_reasons_at_l1(self):
		self.gateway.results = [make_model_result(text="không phải JSON")]
		self._run()

		self.assertEqual([c["task"] for c in self.gateway.calls], ["classify", "reason"])
		self.assertEqual(self._entries(entry_type="classify")[0].stop_reason, "unparseable")
		self.assertIsNone(self._user_message(1)[0]["classification"])

	def test_classify_gateway_error_stops_before_reasoning(self):
		self.gateway.results = [GatewayError("server_error", status=500)]
		self._run()

		self.assertEqual(self.gateway.call_count, 1)
		self.assertEqual(self._reason_entries(), [])

	def test_l0_ticket_insert_has_no_reasoning(self):
		set_agent_settings(permission_level="L0")
		self._run()

		self.assertEqual([c["task"] for c in self.gateway.calls], ["classify"])
		self.assertEqual(self._reason_entries(), [])

	def test_reason_entries_are_committed_one_by_one(self):
		commits = []
		self.addCleanup(setattr, frappe.flags, "in_test", frappe.flags.in_test)
		frappe.flags.in_test = False
		self.gateway.results = [tool_turn(tool_use("toolu_1", "get_ticket")), make_model_result()]
		with patch.object(
			frappe.db,
			"commit",
			side_effect=lambda: commits.append(frappe.db.count(LOG_DOCTYPE, {"ticket": self.ticket.name})),
		):
			self._run("comment_mention")

		# per turn: the gateway call commits its key state (0, 1 rows), then the entry commits itself (1, 2 rows)
		self.assertEqual(commits, [0, 1, 1, 2])

	# AC-10: skipped fields of set_classification on a reason turn

	def test_reason_turn_logs_skipped_fields_of_set_classification(self):
		if not frappe.db.exists("HD Ticket Type", L1_TYPE):
			frappe.get_doc({"doctype": "HD Ticket Type", "name": L1_TYPE}).insert()
		mapping = {"A": {"ticket_type": L1_TYPE, "agent_group": f"{PREFIX}không-có", "priority": "High"}}
		set_agent_settings(category_mapping=json.dumps(mapping))
		self.gateway.results = [
			tool_turn(tool_use("toolu_cls", "set_classification", category="A", confidence="Cao")),
			make_model_result(stop_reason="end_turn"),
		]
		self._run("comment_mention")

		first, second = self._reason_entries()
		self.assertEqual(
			json.loads(first.skipped_fields),
			[{"field": "agent_group", "reason": "giá trị không tồn tại trên hệ thống"}],
		)
		self.assertFalse(second.skipped_fields)
