import json
import time
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.test_utils import make_ticket

from erp_ai.agent import authority, runner
from erp_ai.agent.classification import DEFAULT_CATEGORY_MAPPING
from erp_ai.agent.prompts import build_classify_request
from erp_ai.agent.run_log import write_entry
from erp_ai.constants import (
	AGENT_USER,
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
from erp_ai.test_utils import FakeGateway, add_credential, make_model_result, set_agent_settings

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


class TestRunner(FrappeTestCase):
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
		)
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
		self.assertEqual(call["max_tokens"], 400)
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
