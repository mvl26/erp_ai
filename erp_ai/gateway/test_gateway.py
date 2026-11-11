import ast
import pathlib
from unittest.mock import patch

import frappe
import httpx
import pytz
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, get_datetime, get_system_timezone, now_datetime

from erp_ai.constants import (
	CREDENTIAL_DOCTYPE,
	KEY_STATUS_ACTIVE,
	KEY_STATUS_BAD_KEY,
	KEY_STATUS_PAUSED,
	KEY_STATUS_QUOTA_EXHAUSTED,
	SETTING_DOCTYPE,
)
from erp_ai.gateway import client, cost, credentials
from erp_ai.gateway.breaker import Action, ApiFailure
from erp_ai.test_utils import add_credential, fake_anthropic_client

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
