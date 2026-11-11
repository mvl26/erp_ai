import ast
import pathlib
import time
from unittest.mock import patch

import frappe
import httpx
import pytz
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, get_datetime, get_system_timezone, now_datetime

from erp_ai import gateway
from erp_ai.agent.run_log import write_entry
from erp_ai.constants import (
	CREDENTIAL_DOCTYPE,
	KEY_STATUS_ACTIVE,
	KEY_STATUS_BAD_KEY,
	KEY_STATUS_PAUSED,
	KEY_STATUS_QUOTA_EXHAUSTED,
	LOG_DOCTYPE,
	SETTING_DOCTYPE,
)
from erp_ai.gateway import GatewayError, client, cost, credentials
from erp_ai.gateway.breaker import Action, ApiFailure
from erp_ai.test_utils import add_credential, fake_anthropic_client, set_agent_settings

PRICES = {
	"price_input_per_mtok": 3.0,
	"price_cache_write_per_mtok": 3.75,
	"price_cache_read_per_mtok": 0.3,
	"price_output_per_mtok": 15.0,
}
API_URL = "https://api.anthropic.com/v1/messages"


def make_status_error(status, body=None, headers=None):
	import anthropic

	response = httpx.Response(status, request=httpx.Request("POST", API_URL), headers=headers or {})
	return anthropic.APIStatusError("boom", response=response, body=body)


class TestCost(FrappeTestCase):
	def test_cost_uses_four_token_prices(self):
		usage = {
			"input_tokens": 1000,
			"output_tokens": 2000,
			"cache_creation_input_tokens": 4000,
			"cache_read_input_tokens": 10000,
		}
		# (1000*3 + 4000*3.75 + 10000*0.3 + 2000*15) / 1e6 = 0.051
		self.assertEqual(cost.compute_cost(usage, PRICES), 0.051)

	def test_cost_none_usage_is_zero(self):
		self.assertEqual(cost.compute_cost(None, PRICES), 0)

	def test_cost_missing_keys_count_as_zero_and_rounds_to_six_places(self):
		self.assertEqual(cost.compute_cost({"input_tokens": 1}, PRICES), 0.000003)
		prices = dict(PRICES, price_input_per_mtok=0.123456)
		self.assertEqual(cost.compute_cost({"input_tokens": 1}, prices), 0.0)


class TestClient(FrappeTestCase):
	def test_client_built_with_no_retries_and_timeout(self):
		built = client._build_client("sk-test", 12.5)
		self.assertEqual(built.max_retries, 0)
		self.assertEqual(built.timeout, 12.5)

	def test_send_returns_raw_reply(self):
		fake = fake_anthropic_client(
			message={"type": "message", "content": [{"type": "text", "text": "hi"}]},
			headers={"anthropic-ratelimit-tokens-remaining": "50000"},
			request_id="req_1",
		)
		with patch.object(client, "_build_client", return_value=fake) as build:
			reply = client.send("sk-test", timeout=7, request={"model": "m", "max_tokens": 1})
		build.assert_called_once_with("sk-test", 7)
		self.assertEqual(fake.requests, [{"model": "m", "max_tokens": 1}])
		self.assertEqual(reply.message["content"][0]["text"], "hi")
		self.assertEqual(reply.headers["anthropic-ratelimit-tokens-remaining"], "50000")
		self.assertEqual(reply.request_id, "req_1")

	def test_to_api_failure_maps_status_error(self):
		body = {
			"type": "error",
			"error": {
				"type": "rate_limit_error",
				"message": "You have reached your specified API usage limits.",
				"details": {"error_code": "enforced_spend_limit_reached"},
			},
		}
		failure = client.to_api_failure(make_status_error(429, body, {"retry-after": "12"}))
		self.assertEqual(
			failure,
			ApiFailure(
				status=429,
				kind="api",
				error_type="rate_limit_error",
				error_code="enforced_spend_limit_reached",
				message_prefix="You have reached your specified API usage limits.",
				retry_after=12.0,
			),
		)

	def test_to_api_failure_status_error_without_body(self):
		failure = client.to_api_failure(make_status_error(500))
		self.assertEqual((failure.status, failure.kind, failure.error_code), (500, "api", None))
		self.assertIsNone(failure.retry_after)

	def test_to_api_failure_timeout_and_connection(self):
		import anthropic

		request = httpx.Request("POST", API_URL)
		timeout = client.to_api_failure(anthropic.APITimeoutError(request=request))
		self.assertEqual((timeout.status, timeout.kind), (None, "timeout"))
		conn = client.to_api_failure(anthropic.APIConnectionError(request=request))
		self.assertEqual((conn.status, conn.kind), (None, "connection"))

	def test_to_api_failure_non_api_exception_is_none(self):
		self.assertIsNone(client.to_api_failure(ValueError("x")))

	def test_only_client_imports_anthropic(self):
		app_dir = pathlib.Path(client.__file__).parent.parent
		allowed = {pathlib.Path(client.__file__), pathlib.Path(__file__)}
		offenders = []
		for path in app_dir.rglob("*.py"):
			if path in allowed:
				continue
			for node in ast.walk(ast.parse(path.read_text())):
				names = []
				if isinstance(node, ast.Import):
					names = [a.name for a in node.names]
				elif isinstance(node, ast.ImportFrom):
					names = [node.module or ""]
				if any(n == "anthropic" or n.startswith("anthropic.") for n in names):
					offenders.append(str(path.relative_to(app_dir)))
		self.assertEqual(offenders, [])


class TestCredentials(FrappeTestCase):
	def setUp(self):
		# FrappeTestCase rolls back only after the whole class: undo each test, then start from no keys.
		self.addCleanup(frappe.db.rollback)
		frappe.db.delete(CREDENTIAL_DOCTYPE, {"parent": SETTING_DOCTYPE})

	def row(self, name):
		return frappe.db.get_value(CREDENTIAL_DOCTYPE, name, "*", as_dict=True)

	def labels(self, task="classify", exclude=None):
		return [r["label"] for r in credentials.select_keys(task, exclude or set())]

	def test_selection_filters_and_order(self):
		future = add_to_date(now_datetime(), minutes=5)
		past = add_to_date(now_datetime(), minutes=-5)
		add_credential("disabled", enabled=0)
		add_credential("bad", status=KEY_STATUS_BAD_KEY)
		add_credential("quota", status=KEY_STATUS_QUOTA_EXHAUSTED)
		add_credential("paused_future", status=KEY_STATUS_PAUSED, paused_until=future)
		add_credential("over_budget", budget_month_usd=5, spent_month_usd=5)
		add_credential("openai", provider="OpenAI")
		add_credential("excluded")
		add_credential("paused_past", status=KEY_STATUS_PAUSED, paused_until=past, try_order=20)
		add_credential("under_budget", budget_month_usd=5, spent_month_usd=4.9, try_order=20, error_count=1)
		add_credential("unlimited_budget", budget_month_usd=0, spent_month_usd=99, try_order=20)
		add_credential("first", try_order=5, error_count=9)
		add_credential("tie_less_errors", try_order=20, error_count=0)
		add_credential("zero_order", try_order=0)
		self.assertEqual(
			self.labels(exclude={"excluded"}),
			[
				"first",
				"paused_past",
				"unlimited_budget",
				"tie_less_errors",
				"under_budget",
				"zero_order",
			],
		)

	def test_selection_ties_keep_row_order(self):
		add_credential("a", try_order=7)
		add_credential("b", try_order=7)
		real_get_all = frappe.db.get_all

		def reversed_rows(*args, **kwargs):
			return sorted(real_get_all(*args, **kwargs), key=lambda r: -r.idx)

		with patch.object(frappe.db, "get_all", reversed_rows):
			self.assertEqual(self.labels(), ["a", "b"])

	def test_selection_returns_row_name_and_never_the_key(self):
		name = add_credential("k1", model_classify="m-c")
		(row,) = credentials.select_keys("classify", set())
		self.assertEqual((row["name"], row["label"], row["model_classify"]), (name, "k1", "m-c"))
		self.assertNotIn("sk-k1", str(row))

	def test_exclude_matches_labels_only(self):
		add_credential("one")
		add_credential("two")
		self.assertEqual(self.labels(exclude={"one"}), ["two"])

	def test_reason_requires_model_reason(self):
		add_credential("no_reason")
		add_credential("with_reason", model_reason="m-r")
		self.assertEqual(self.labels("reason"), ["with_reason"])
		self.assertEqual(self.labels("classify"), ["no_reason", "with_reason"])

	def test_get_api_key_decrypts_and_missing_is_none(self):
		name = add_credential("k1")
		self.assertEqual(credentials.get_api_key(name), "sk-k1")
		self.assertIsNone(credentials.get_api_key("does-not-exist"))

	def failure(self, **kw):
		return ApiFailure(**{"status": 429, "kind": "api", **kw})

	def test_apply_failure_writes_status_pause_and_counts(self):
		name = add_credential("k1", error_count=2)
		before = now_datetime()
		action = Action(KEY_STATUS_PAUSED, 61, True, None, "rate_limit")
		credentials.apply_failure(name, action, self.failure())
		row = self.row(name)
		self.assertEqual(row.status, KEY_STATUS_PAUSED)
		self.assertEqual(row.error_count, 3)
		self.assertEqual(row.last_error, "rate_limit status=429")
		paused = (get_datetime(row.paused_until) - before).total_seconds()
		self.assertTrue(60 <= paused <= 63, paused)

	def test_apply_failure_records_request_id_in_last_error(self):
		name = add_credential("k1")
		action = Action(KEY_STATUS_PAUSED, 61, True, None, "rate_limit")
		credentials.apply_failure(name, action, self.failure(), request_id="req_9")
		self.assertEqual(self.row(name).last_error, "rate_limit status=429 request_id=req_9")

	def test_apply_failure_without_pause_keeps_paused_until_empty(self):
		name = add_credential("k1")
		action = Action(KEY_STATUS_BAD_KEY, None, True, "alarm", "auth")
		credentials.apply_failure(name, action, self.failure(status=401))
		row = self.row(name)
		self.assertEqual((row.status, row.error_count), (KEY_STATUS_BAD_KEY, 1))
		self.assertIsNone(row.paused_until)

	def test_apply_failure_with_no_new_status_changes_nothing(self):
		name = add_credential("k1", error_count=2)
		action = Action(None, None, False, None, "bad_request")
		credentials.apply_failure(name, action, self.failure(status=400))
		row = self.row(name)
		self.assertEqual((row.status, row.error_count, row.last_error), (KEY_STATUS_ACTIVE, 2, None))

	def test_apply_success_resets_error_state(self):
		future = add_to_date(now_datetime(), minutes=5)
		name = add_credential(
			"k1", error_count=4, last_error="x", status=KEY_STATUS_PAUSED, paused_until=future
		)
		credentials.apply_success(name, {})
		row = self.row(name)
		self.assertEqual((row.status, row.error_count), (KEY_STATUS_ACTIVE, 0))
		self.assertFalse(row.last_error)
		self.assertIsNotNone(row.last_success_at)
		self.assertIsNone(row.paused_until)

	def test_low_tokens_pause_until_reset_and_missing_headers_ignored(self):
		reset = add_to_date(now_datetime(), minutes=10).replace(microsecond=0)
		reset_header = self.to_utc_header(reset)

		def headers(tokens):
			return {
				"anthropic-ratelimit-tokens-remaining": tokens,
				"anthropic-ratelimit-tokens-reset": reset_header,
			}

		low = add_credential("low")
		credentials.apply_success(low, headers("19999"))
		row = self.row(low)
		self.assertEqual(row.status, KEY_STATUS_PAUSED)
		self.assertEqual(row.tokens_remaining, 19999)
		self.assertEqual(get_datetime(row.limit_reset_at), reset)
		self.assertEqual(get_datetime(row.paused_until), reset)

		edge = add_credential("edge")
		credentials.apply_success(edge, headers("20000"))
		row = self.row(edge)
		self.assertEqual(row.status, KEY_STATUS_ACTIVE)
		self.assertEqual(row.tokens_remaining, 20000)
		self.assertEqual(get_datetime(row.limit_reset_at), reset)
		self.assertIsNone(row.paused_until)

		bare = add_credential("bare", tokens_remaining=5, limit_reset_at=reset)
		credentials.apply_success(bare, {})
		row = self.row(bare)
		self.assertEqual((row.status, row.tokens_remaining), (KEY_STATUS_ACTIVE, 5))
		self.assertEqual(get_datetime(row.limit_reset_at), reset)

		no_reset = add_credential("no_reset")
		credentials.apply_success(no_reset, {"anthropic-ratelimit-tokens-remaining": "10"})
		row = self.row(no_reset)
		self.assertEqual((row.status, row.tokens_remaining), (KEY_STATUS_ACTIVE, 10))
		self.assertIsNone(row.paused_until)

	def test_malformed_rate_limit_headers_are_ignored(self):
		stored_reset = add_to_date(now_datetime(), hours=1).replace(microsecond=0)
		name = add_credential("k1", tokens_remaining=7, limit_reset_at=stored_reset)
		credentials.apply_success(
			name,
			{
				"anthropic-ratelimit-tokens-remaining": "lots",
				"anthropic-ratelimit-tokens-reset": "tomorrow",
			},
		)
		row = self.row(name)
		self.assertEqual((row.status, row.tokens_remaining), (KEY_STATUS_ACTIVE, 7))
		self.assertEqual(get_datetime(row.limit_reset_at), stored_reset)

		for reset in ("tomorrow", "2030-01-01T00:00:00"):
			credentials.apply_success(
				name,
				{
					"anthropic-ratelimit-tokens-remaining": "100",
					"anthropic-ratelimit-tokens-reset": reset,
				},
			)
			row = self.row(name)
			self.assertEqual((row.status, row.tokens_remaining), (KEY_STATUS_ACTIVE, 100), reset)
			self.assertEqual(get_datetime(row.limit_reset_at), stored_reset, reset)
			self.assertIsNone(row.paused_until, reset)

	@staticmethod
	def to_utc_header(naive_system_time):
		aware = pytz.timezone(get_system_timezone()).localize(naive_system_time)
		return aware.astimezone(pytz.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


MESSAGE = {
	"type": "message",
	"model": "claude-served",
	"stop_reason": "end_turn",
	"content": [{"type": "text", "text": "xin "}, {"type": "text", "text": "chào"}],
	"usage": {"input_tokens": 1000, "output_tokens": 2000},
}
CALL = {"system": "sys", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 50}


class ScriptedSend:
	"""Replaces `client.send`: plays the scripted outcomes in order (exception -> raised)."""

	def __init__(self, *outcomes):
		self.outcomes = list(outcomes)
		self.calls = []

	def __call__(self, api_key, *, timeout, request):
		self.calls.append({"api_key": api_key, "timeout": timeout, "request": request})
		outcome = self.outcomes.pop(0)
		if isinstance(outcome, BaseException):
			raise outcome
		return outcome


def ok_reply(message=None, headers=None, request_id="req_ok"):
	return client.RawReply(message=message or MESSAGE, headers=headers or {}, request_id=request_id)


def err(status, **kw):
	return make_status_error(status, headers={"request-id": "req_err"}, **kw)


class TestCallModel(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		frappe.db.delete(CREDENTIAL_DOCTYPE, {"parent": SETTING_DOCTYPE})
		set_agent_settings(
			max_keys_per_call=2,
			request_timeout_s=45,
			model_classify_default="default-model",
			**PRICES,
		)
		self.alarm = self.enterContext(patch("erp_ai.alerts.send_alarm"))
		self.notice = self.enterContext(patch("erp_ai.alerts.send_notice"))

	def run_call(self, *outcomes, task="classify", **kw):
		send = ScriptedSend(*outcomes)
		with patch.object(client, "send", send):
			try:
				result = gateway.call_model(task, **{**CALL, **kw})
			except GatewayError as exc:
				result = exc
		return send, result

	def row(self, name):
		return frappe.db.get_value(CREDENTIAL_DOCTYPE, name, "*", as_dict=True)

	def first_row(self):
		return frappe.db.get_value(CREDENTIAL_DOCTYPE, {"parent": SETTING_DOCTYPE}, "name")

	def test_invalid_task_raises_value_error(self):
		add_credential("k1")
		send = ScriptedSend()
		with patch.object(client, "send", send), self.assertRaises(ValueError):
			gateway.call_model("summarize", **CALL)
		self.assertEqual(send.calls, [])

	def test_success_builds_result_and_records_success(self):
		name = add_credential("k1", error_count=2, last_error="x")
		reply = ok_reply(headers={"anthropic-ratelimit-tokens-remaining": "50000"})
		send, result = self.run_call(reply, tools=[{"name": "t"}])
		self.assertEqual(send.calls[0]["api_key"], "sk-k1")
		self.assertEqual(send.calls[0]["timeout"], 45)
		self.assertEqual(
			send.calls[0]["request"],
			{**CALL, "model": "default-model", "tools": [{"name": "t"}]},
		)
		self.assertEqual(result.text, "xin chào")
		self.assertEqual(result.content, MESSAGE["content"])
		self.assertEqual((result.stop_reason, result.model), ("end_turn", "claude-served"))
		self.assertEqual(result.credential_label, "k1")
		self.assertEqual(result.request_id, "req_ok")
		self.assertEqual(result.keys_tried, [{"label": "k1", "outcome": "ok"}])
		# usage thiếu khóa -> 0; chi phí theo đơn giá trong Setting: (1000*3 + 2000*15) / 1e6
		self.assertEqual(
			result.usage,
			{
				"input_tokens": 1000,
				"output_tokens": 2000,
				"cache_creation_input_tokens": 0,
				"cache_read_input_tokens": 0,
			},
		)
		self.assertEqual(result.cost_usd, 0.033)
		row = self.row(name)
		self.assertEqual((row.status, row.error_count, row.tokens_remaining), (KEY_STATUS_ACTIVE, 0, 50000))
		self.assertFalse(row.last_error)

	def test_latency_ms_is_elapsed_milliseconds(self):
		add_credential("k1")
		clock = [100.0]

		def slow_send(api_key, *, timeout, request):
			clock[0] += 1.5
			return ok_reply()

		with (
			patch.object(gateway.time, "monotonic", lambda: clock[0]),
			patch.object(client, "send", slow_send),
		):
			result = gateway.call_model("classify", **CALL)
		self.assertEqual(result.latency_ms, 1500)

	def test_none_usage_values_count_as_zero(self):
		add_credential("k1")
		usage = {"input_tokens": 10, "output_tokens": 0, "cache_creation_input_tokens": None}
		_, result = self.run_call(ok_reply(message={**MESSAGE, "usage": usage}))
		self.assertEqual(result.usage["cache_creation_input_tokens"], 0)
		self.assertEqual(result.usage["cache_read_input_tokens"], 0)
		self.assertEqual(result.cost_usd, 0.00003)
		_, result = self.run_call(ok_reply(message={**MESSAGE, "usage": None}))
		self.assertEqual((result.usage["input_tokens"], result.cost_usd), (0, 0))

	def test_model_follows_task_and_key(self):
		add_credential("k1", model_classify="key-classify", model_reason="key-reason")
		send, _ = self.run_call(ok_reply(), task="classify")
		self.assertEqual(send.calls[0]["request"]["model"], "key-classify")
		self.assertNotIn("tools", send.calls[0]["request"])
		send, _ = self.run_call(ok_reply(), task="reason")
		self.assertEqual(send.calls[0]["request"]["model"], "key-reason")
		frappe.db.set_value(CREDENTIAL_DOCTYPE, self.first_row(), "model_classify", "")
		send, _ = self.run_call(ok_reply(), task="classify")
		self.assertEqual(send.calls[0]["request"]["model"], "default-model")

	def test_rate_limit_switches_to_next_key_without_notification(self):
		first = add_credential("k1", try_order=1)
		second = add_credential("k2", try_order=2)
		send, result = self.run_call(err(429), ok_reply())
		self.assertEqual([c["api_key"] for c in send.calls], ["sk-k1", "sk-k2"])
		self.assertEqual(result.credential_label, "k2")
		self.assertEqual(
			result.keys_tried,
			[{"label": "k1", "outcome": "rate_limit"}, {"label": "k2", "outcome": "ok"}],
		)
		row = self.row(first)
		self.assertEqual((row.status, row.error_count), (KEY_STATUS_PAUSED, 1))
		self.assertEqual(row.last_error, "rate_limit status=429 request_id=req_err")
		self.assertGreater(get_datetime(row.paused_until), now_datetime())
		self.assertEqual(self.row(second).status, KEY_STATUS_ACTIVE)
		self.alarm.assert_not_called()
		self.notice.assert_not_called()

	def test_overloaded_pause_uses_incremented_error_count(self):
		name = add_credential("k1", error_count=1)
		self.run_call(err(529))
		row = self.row(name)
		# error_count mới = 2 -> nghỉ 60 s (không phải 30 s của lần đếm cũ)
		paused = (get_datetime(row.paused_until) - now_datetime()).total_seconds()
		self.assertTrue(55 <= paused <= 61, paused)

	def test_timeout_error_switches_key(self):
		import anthropic

		add_credential("k1", try_order=1)
		add_credential("k2", try_order=2)
		request = httpx.Request("POST", API_URL)
		send, result = self.run_call(anthropic.APITimeoutError(request=request), ok_reply())
		self.assertEqual(result.keys_tried[0], {"label": "k1", "outcome": "timeout"})
		self.assertEqual(len(send.calls), 2)

	def test_max_keys_per_call(self):
		for index in range(5):
			add_credential(f"k{index}", try_order=index + 1)
		send, error = self.run_call(*[err(529) for _ in range(5)])
		self.assertEqual(len(send.calls), 2)
		self.assertIsInstance(error, GatewayError)
		self.assertEqual(error.kind, "all_keys_failed")
		self.assertEqual([k["label"] for k in error.keys_tried], ["k0", "k1"])
		self.assertEqual((error.status, error.credential_label, error.request_id), (529, "k1", "req_err"))
		self.alarm.assert_called_once()
		self.assertIn("Hết khóa dùng được cho việc 'classify'", self.alarm.call_args.args[0])

	def test_empty_settings_fall_back_to_defaults(self):
		set_agent_settings(max_keys_per_call=0, request_timeout_s=0)
		for index in range(5):
			add_credential(f"k{index}", try_order=index + 1)
		send, error = self.run_call(*[err(529) for _ in range(5)])
		self.assertEqual(len(send.calls), 3)
		self.assertEqual({call["timeout"] for call in send.calls}, {60})
		self.assertEqual(error.kind, "all_keys_failed")

	def test_non_positive_max_keys_still_tries_one_key(self):
		set_agent_settings(max_keys_per_call=-2)
		add_credential("k1", try_order=1)
		add_credential("k2", try_order=2)
		send, error = self.run_call(err(529), ok_reply())
		self.assertEqual(len(send.calls), 1)
		self.assertEqual(error.kind, "all_keys_failed")

	def test_all_keys_failing_before_max_keys_is_all_keys_failed(self):
		add_credential("k1")
		_, error = self.run_call(err(529))
		self.assertEqual(error.kind, "all_keys_failed")
		self.alarm.assert_called_once()

	def test_bad_request_does_not_switch_key(self):
		first = add_credential("k1", try_order=1, error_count=2)
		second = add_credential("k2", try_order=2)
		send, error = self.run_call(err(400), ok_reply())
		self.assertEqual(len(send.calls), 1)
		self.assertEqual(error.kind, "bad_request")
		self.assertIsNone(error.__cause__)
		self.assertTrue(error.__suppress_context__)
		self.assertEqual((error.status, error.credential_label, error.request_id), (400, "k1", "req_err"))
		self.assertEqual(error.keys_tried, [{"label": "k1", "outcome": "bad_request"}])
		row = self.row(first)
		self.assertEqual((row.status, row.error_count), (KEY_STATUS_ACTIVE, 2))
		self.assertEqual(self.row(second).status, KEY_STATUS_ACTIVE)
		self.alarm.assert_not_called()
		self.notice.assert_not_called()

	def test_no_usable_key_alarm(self):
		add_credential("disabled", enabled=0)
		send, error = self.run_call()
		self.assertEqual(send.calls, [])
		self.assertEqual(error.kind, "no_key")
		self.assertEqual(error.keys_tried, [])
		self.alarm.assert_called_once()
		self.assertIn("Hết khóa dùng được cho việc 'classify'", self.alarm.call_args.args[0])
		self.notice.assert_not_called()

	def test_bad_key_401_marks_key_alarms_and_switches(self):
		first = add_credential("k1", try_order=1)
		add_credential("k2", try_order=2)
		_, result = self.run_call(err(401), ok_reply())
		self.assertEqual(self.row(first).status, KEY_STATUS_BAD_KEY)
		self.assertEqual(result.credential_label, "k2")
		self.alarm.assert_called_once()
		self.assertIn("k1", self.alarm.call_args.args[0] + self.alarm.call_args.args[1])
		self.notice.assert_not_called()

	def test_quota_402_marks_key_sends_notice_and_switches(self):
		first = add_credential("k1", try_order=1)
		add_credential("k2", try_order=2)
		_, result = self.run_call(err(402), ok_reply())
		self.assertEqual(self.row(first).status, KEY_STATUS_QUOTA_EXHAUSTED)
		self.assertEqual(result.credential_label, "k2")
		self.notice.assert_called_once()
		self.assertIn("k1", self.notice.call_args.args[0] + self.notice.call_args.args[1])
		self.alarm.assert_not_called()

	def test_notification_only_when_status_really_changes(self):
		name = add_credential("k1", status=KEY_STATUS_BAD_KEY)
		stale_row = frappe.db.get_all(CREDENTIAL_DOCTYPE, filters={"name": name}, fields=["*"])
		with patch.object(credentials, "select_keys", side_effect=[stale_row, []]):
			self.run_call(err(401))
		self.alarm.assert_called_once()  # chỉ báo động hết khóa, không có báo động lỗi khóa
		self.assertIn("Hết khóa", self.alarm.call_args.args[0])
		self.notice.assert_not_called()

	def test_notification_failure_does_not_break_the_call(self):
		add_credential("k1", try_order=1)
		add_credential("k2", try_order=2)
		self.alarm.side_effect = RuntimeError("no email account")
		with patch.object(frappe, "log_error") as log_error:
			_, result = self.run_call(err(401), ok_reply())
		self.assertEqual(result.credential_label, "k2")
		log_error.assert_called_once()
		title, message = log_error.call_args.args
		self.assertEqual(title, "erp_ai: không gửi được thông báo khóa")
		self.assertIn("RuntimeError", message)
		self.assertNotIn("no email account", message)

	def test_alarm_failure_when_no_key_still_raises_no_key(self):
		add_credential("disabled", enabled=0)
		self.alarm.side_effect = RuntimeError("no email account")
		with patch.object(frappe, "log_error") as log_error:
			_, error = self.run_call()
		self.assertEqual(error.kind, "no_key")
		log_error.assert_called_once()
		title, message = log_error.call_args.args
		self.assertEqual(title, "erp_ai: không gửi được thông báo khóa")
		self.assertIn("RuntimeError", message)

	def test_deadline_under_five_seconds_makes_no_call(self):
		add_credential("k1")
		send, error = self.run_call(deadline=time.monotonic() + 3)
		self.assertEqual(send.calls, [])
		self.assertEqual(error.kind, "deadline")

	def test_deadline_limits_attempt_timeout(self):
		add_credential("k1")
		send, _ = self.run_call(ok_reply(), deadline=time.monotonic() + 30)
		self.assertTrue(25 < send.calls[0]["timeout"] <= 30, send.calls[0]["timeout"])
		send, _ = self.run_call(ok_reply(), deadline=time.monotonic() + 600)
		self.assertEqual(send.calls[0]["timeout"], 45)

	def test_deadline_checked_before_every_attempt(self):
		add_credential("k1", try_order=1)
		add_credential("k2", try_order=2)
		clock = [900.0]
		calls = []

		def failing_send(api_key, *, timeout, request):
			calls.append(api_key)
			clock[0] = 996.0
			raise err(529)

		with (
			patch.object(gateway.time, "monotonic", lambda: clock[0]),
			patch.object(client, "send", failing_send),
			self.assertRaises(GatewayError) as caught,
		):
			gateway.call_model("classify", deadline=1000.0, **CALL)
		self.assertEqual(len(calls), 1)
		self.assertEqual(caught.exception.kind, "deadline")
		self.assertEqual(caught.exception.keys_tried, [{"label": "k1", "outcome": "overloaded"}])

	def test_unexpected_exception_hides_cause_and_does_not_switch(self):
		name = add_credential("k1", try_order=1)
		add_credential("k2", try_order=2)
		send, error = self.run_call(RuntimeError("leak sk-k1 here"))
		self.assertEqual(len(send.calls), 1)
		self.assertEqual(error.kind, "unexpected")
		self.assertEqual(error.credential_label, "k1")
		self.assertEqual(error.keys_tried, [{"label": "k1", "outcome": "unexpected"}])
		self.assertIsNone(error.__cause__)
		self.assertTrue(error.__suppress_context__)
		self.assertNotIn("sk-k1", str(error))
		self.assertEqual(self.row(name).status, KEY_STATUS_ACTIVE)
		self.alarm.assert_not_called()

	def test_key_without_stored_secret_is_skipped(self):
		first = add_credential("k1", try_order=1)
		add_credential("k2", try_order=2)
		real = credentials.get_api_key
		with (
			patch.object(credentials, "get_api_key", side_effect=lambda n: None if n == first else real(n)),
			patch.object(gateway.frappe, "logger") as logger,
		):
			send, result = self.run_call(ok_reply())
		logger.return_value.warning.assert_called_once()
		self.assertIn("k1", logger.return_value.warning.call_args.args)
		self.assertEqual([c["api_key"] for c in send.calls], ["sk-k2"])
		self.assertEqual(result.credential_label, "k2")


class TestProbe(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		frappe.db.delete(CREDENTIAL_DOCTYPE, {"parent": SETTING_DOCTYPE})
		set_agent_settings(model_classify_default="default-model")
		self.alarm = self.enterContext(patch("erp_ai.alerts.send_alarm"))
		self.notice = self.enterContext(patch("erp_ai.alerts.send_notice"))

	def probe(self, name, *outcomes):
		send = ScriptedSend(*outcomes)
		with patch.object(client, "send", send):
			return send, gateway.probe_credential(name)

	def reprobe(self, *outcomes):
		send = ScriptedSend(*outcomes)
		with patch.object(client, "send", send):
			return send, gateway.reprobe_exhausted_keys()

	def row(self, name):
		return frappe.db.get_value(CREDENTIAL_DOCTYPE, name, "*", as_dict=True)

	def test_probe_success_activates_key_and_sends_one_token_ping(self):
		name = add_credential(
			"k1", status=KEY_STATUS_QUOTA_EXHAUSTED, error_count=4, last_error="quota", model_classify="m-own"
		)
		send, result = self.probe(name, ok_reply())
		self.assertEqual(result, {"label": "k1", "ok": True, "error_kind": None, "status": None})
		call = send.calls[0]
		self.assertEqual(call["api_key"], "sk-k1")
		self.assertEqual(call["timeout"], 10)
		self.assertEqual(
			call["request"],
			{"model": "m-own", "max_tokens": 1, "messages": [{"role": "user", "content": "ping"}]},
		)
		row = self.row(name)
		self.assertEqual((row.status, row.error_count, row.last_error), (KEY_STATUS_ACTIVE, 0, ""))

	def test_probe_uses_default_model_when_key_has_none(self):
		name = add_credential("k1")
		send, _ = self.probe(name, ok_reply())
		self.assertEqual(send.calls[0]["request"]["model"], "default-model")

	def test_probe_failure_reports_kind_and_status_and_applies_breaker(self):
		name = add_credential("k1", status=KEY_STATUS_QUOTA_EXHAUSTED)
		_, result = self.probe(name, err(401))
		self.assertEqual(result, {"label": "k1", "ok": False, "error_kind": "auth", "status": 401})
		self.assertEqual(self.row(name).status, KEY_STATUS_BAD_KEY)
		self.assertEqual(self.row(name).error_count, 1)
		self.alarm.assert_called_once()

	def test_probe_rate_limit_pauses_key(self):
		name = add_credential("k1")
		_, result = self.probe(name, err(429))
		self.assertEqual((result["ok"], result["error_kind"], result["status"]), (False, "rate_limit", 429))
		self.assertEqual(self.row(name).status, KEY_STATUS_PAUSED)

	def test_probe_bad_request_leaves_status(self):
		name = add_credential("k1", status=KEY_STATUS_QUOTA_EXHAUSTED)
		_, result = self.probe(name, err(422))
		self.assertEqual((result["error_kind"], result["status"]), ("bad_request", 422))
		self.assertEqual(self.row(name).status, KEY_STATUS_QUOTA_EXHAUSTED)

	def test_probe_unexpected_exception_has_no_status_and_hides_text(self):
		name = add_credential("k1", status=KEY_STATUS_QUOTA_EXHAUSTED)
		_, result = self.probe(name, RuntimeError("leak sk-k1"))
		self.assertEqual(result, {"label": "k1", "ok": False, "error_kind": "unexpected", "status": None})
		self.assertEqual(self.row(name).status, KEY_STATUS_QUOTA_EXHAUSTED)

	def test_probe_unsupported_provider_does_not_send_or_change_status(self):
		name = add_credential("k1", provider="OpenAI", status=KEY_STATUS_QUOTA_EXHAUSTED)
		send, result = self.probe(name)
		self.assertEqual(
			result, {"label": "k1", "ok": False, "error_kind": "unsupported_provider", "status": None}
		)
		self.assertEqual(send.calls, [])
		self.assertEqual(self.row(name).status, KEY_STATUS_QUOTA_EXHAUSTED)

	def test_probe_missing_secret_does_not_send(self):
		name = add_credential("k1", status=KEY_STATUS_QUOTA_EXHAUSTED)
		with patch.object(credentials, "get_api_key", return_value=None):
			send, result = self.probe(name)
		self.assertEqual(result, {"label": "k1", "ok": False, "error_kind": "no_secret", "status": None})
		self.assertEqual(send.calls, [])
		self.assertEqual(self.row(name).status, KEY_STATUS_QUOTA_EXHAUSTED)

	def test_probe_unknown_row(self):
		send, result = self.probe("no-such-row")
		self.assertEqual(result, {"label": None, "ok": False, "error_kind": "not_found", "status": None})
		self.assertEqual(send.calls, [])

	def test_reprobe_only_exhausted_enabled_keys(self):
		exhausted = add_credential("ex", status=KEY_STATUS_QUOTA_EXHAUSTED)
		bad = add_credential("bad", status=KEY_STATUS_BAD_KEY)
		active = add_credential("act")
		paused = add_credential("pau", status=KEY_STATUS_PAUSED)
		disabled = add_credential("dis", status=KEY_STATUS_QUOTA_EXHAUSTED, enabled=0)
		other = add_credential("oth", status=KEY_STATUS_QUOTA_EXHAUSTED, provider="OpenAI")
		send, results = self.reprobe(ok_reply(), ok_reply())
		self.assertEqual(
			results,
			[
				{"label": "ex", "ok": True, "error_kind": None, "status": None},
				{"label": "oth", "ok": False, "error_kind": "unsupported_provider", "status": None},
			],
		)
		self.assertEqual(len(send.calls), 1)
		self.assertEqual(send.calls[0]["api_key"], "sk-ex")
		self.assertEqual(self.row(exhausted).status, KEY_STATUS_ACTIVE)
		self.assertEqual(self.row(bad).status, KEY_STATUS_BAD_KEY)
		self.assertEqual(self.row(active).status, KEY_STATUS_ACTIVE)
		self.assertEqual(self.row(paused).status, KEY_STATUS_PAUSED)
		self.assertEqual(self.row(disabled).status, KEY_STATUS_QUOTA_EXHAUSTED)
		self.assertEqual(self.row(other).status, KEY_STATUS_QUOTA_EXHAUSTED)

	def test_reprobe_orders_by_idx_and_keeps_failed_key_exhausted_without_notice(self):
		first = add_credential("a", status=KEY_STATUS_QUOTA_EXHAUSTED)
		second = add_credential("b", status=KEY_STATUS_QUOTA_EXHAUSTED)
		send, results = self.reprobe(err(402), ok_reply())
		self.assertEqual([r["label"] for r in results], ["a", "b"])
		self.assertEqual([c["api_key"] for c in send.calls], ["sk-a", "sk-b"])
		self.assertEqual((results[0]["ok"], results[0]["error_kind"]), (False, "quota"))
		self.assertEqual(self.row(first).status, KEY_STATUS_QUOTA_EXHAUSTED)
		self.assertEqual(self.row(second).status, KEY_STATUS_ACTIVE)
		self.notice.assert_called_once()
		self.assertIn("b", self.notice.call_args.args[0])

	def test_reprobe_with_nothing_exhausted_returns_empty(self):
		add_credential("k1")
		send, results = self.reprobe()
		self.assertEqual((results, send.calls), ([], []))
		self.notice.assert_not_called()

	def test_reprobe_notice_failure_is_logged_and_does_not_stop_loop(self):
		add_credential("a", status=KEY_STATUS_QUOTA_EXHAUSTED)
		add_credential("b", status=KEY_STATUS_QUOTA_EXHAUSTED)
		self.notice.side_effect = RuntimeError("smtp down")
		with patch.object(gateway.frappe, "log_error") as log_error:
			_, results = self.reprobe(ok_reply(), ok_reply())
		self.assertEqual([r["ok"] for r in results], [True, True])
		self.assertEqual(log_error.call_count, 2)
		self.assertIn("RuntimeError", log_error.call_args.args[1])


class TestApiKeyLeak(FrappeTestCase):
	"""AC-14 (key part), NFR-5: a fake key's marker never reaches any store, on success or on any failure path."""

	TEXT_FIELD_TYPES = ("Data", "Small Text", "Text", "Long Text", "Code")

	def setUp(self):
		self.addCleanup(frappe.db.rollback)
		self.enterContext(
			patch.object(frappe.db, "commit", side_effect=AssertionError("test must not commit"))
		)
		frappe.db.delete(CREDENTIAL_DOCTYPE, {"parent": SETTING_DOCTYPE})
		set_agent_settings(
			max_keys_per_call=2,
			model_classify_default="default-model",
			alert_recipients="ops@example.com",
			**PRICES,
		)
		self.sendmail = self.enterContext(patch.object(frappe, "sendmail"))
		# an Error Log insert is not undone by rollback on this site: capture the calls instead of writing rows
		self.log_error = self.enterContext(patch.object(frappe, "log_error"))
		# the gateway's file logger (logs/erp_ai.log) is a store too: capture what it is asked to write
		self.logger = self.enterContext(patch.object(frappe, "logger"))

	def stores_containing(self, marker, outputs):
		like = f"%{marker}%"
		found = {}
		log_fields = [
			df.fieldname
			for df in frappe.get_meta(LOG_DOCTYPE).fields
			if df.fieldtype in self.TEXT_FIELD_TYPES
		]
		stores = {
			LOG_DOCTYPE: (LOG_DOCTYPE, [[LOG_DOCTYPE, f, "like", like] for f in log_fields]),
			"HD Ticket Comment": ("HD Ticket Comment", [["HD Ticket Comment", "content", "like", like]]),
			"Comment": ("Comment", [["Comment", "content", "like", like]]),
			"last_error": (CREDENTIAL_DOCTYPE, [[CREDENTIAL_DOCTYPE, "last_error", "like", like]]),
		}
		for store, (doctype, or_filters) in stores.items():
			found[store] = len(frappe.get_all(doctype, or_filters=or_filters, pluck="name"))
		found["sendmail"] = int(marker in repr(self.sendmail.call_args_list))
		found["log_error calls"] = int(marker in repr(self.log_error.call_args_list))
		found["frappe.logger"] = int(marker in repr(self.logger.mock_calls))
		found["gateway output"] = int(marker in outputs)
		return {store: count for store, count in found.items() if count}

	def used_sinks(self):
		last_errors = frappe.get_all(CREDENTIAL_DOCTYPE, filters={"last_error": ["is", "set"]}, pluck="name")
		used = {
			"sendmail": self.sendmail.called,
			"log_error": self.log_error.called,
			"frappe.logger": self.logger.called,
			"last_error": bool(last_errors),
		}
		return {sink for sink, was_used in used.items() if was_used}

	def run_path(self, label, outcomes, markers):
		for sink in (self.sendmail, self.log_error, self.logger):
			sink.reset_mock()
		frappe.db.delete(CREDENTIAL_DOCTYPE, {"parent": SETTING_DOCTYPE})
		for index, marker in enumerate(markers, start=1):
			add_credential(f"ERPAI-TEST-leak-{label}-{index}", api_key=marker, try_order=index)
		send = ScriptedSend(*outcomes)
		with patch.object(client, "send", send):
			try:
				result = gateway.call_model("classify", **CALL)
				error = None
			except GatewayError as exc:
				result, error = None, exc
		outputs = repr(result) + repr(error) + str(error) + repr(getattr(error, "keys_tried", None))
		if error is not None:
			outputs += repr(error.__cause__) + repr(error.__context__)
		# the runner (T28) logs what the gateway returns/raises: do the same so the log store is exercised
		write_entry(
			run_id=f"ERPAI-TEST-leak-{label}",
			entry_type="classify",
			trigger="ticket_insert",
			credential_label=error.credential_label if error else result.credential_label,
			keys_tried=error.keys_tried if error else result.keys_tried,
			error=str(error) if error else None,
			stop_reason=error.kind if error else result.stop_reason,
		)
		return send, result, error, outputs

	def assert_no_leak(self, label, outcomes, markers, expect_error=None, expect_sinks=()):
		send, result, error, outputs = self.run_path(label, outcomes, markers)
		self.assertEqual(error.kind if error else None, expect_error)
		# every sink this path writes to was really used, so its "no marker" check is not vacuous
		self.assertEqual(self.used_sinks(), set(expect_sinks), label)
		self.assertEqual(send.calls[0]["api_key"], markers[0])  # the marker really was sent to the SDK
		for marker in markers:
			self.assertEqual(self.stores_containing(marker, outputs), {}, label)

	def test_api_key_never_leaks(self):
		key = f"ERPAI-TEST-SECRET-KEY-{frappe.generate_hash(length=8)}-{{}}"  # unique per run
		leaking_body = {"type": "error", "error": {"type": "authentication_error", "message": ""}}

		def failing(status, marker):
			body = {**leaking_body, "error": {**leaking_body["error"], "message": f"bad key {marker}"}}
			return make_status_error(status, body=body, headers={"request-id": "req_err"})

		with self.subTest("success"):
			self.assert_no_leak("success", [ok_reply()], [key.format("success")])
		with self.subTest("401 then next key succeeds"):
			markers = [key.format("401-a"), key.format("401-b")]
			self.assert_no_leak(
				"401",
				[failing(401, markers[0]), ok_reply()],
				markers,
				expect_sinks={"sendmail", "log_error", "last_error"},
			)
		with self.subTest("unexpected exception"):
			marker = key.format("unexpected")
			self.assert_no_leak(
				"unexpected",
				[RuntimeError(f"boom {marker}")],
				[marker],
				expect_error="unexpected",
				expect_sinks={"frappe.logger"},
			)
		with self.subTest("all keys failed (529 alarm)"):
			markers = [key.format("all-a"), key.format("all-b")]
			self.assert_no_leak(
				"all",
				[failing(529, markers[0]), failing(529, markers[1])],
				markers,
				expect_error="all_keys_failed",
				expect_sinks={"sendmail", "log_error", "last_error"},
			)
