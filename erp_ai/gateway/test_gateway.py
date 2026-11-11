import ast
import pathlib
from unittest.mock import patch

import httpx
from frappe.tests.utils import FrappeTestCase

from erp_ai.gateway import client, cost
from erp_ai.gateway.breaker import ApiFailure
from erp_ai.test_utils import fake_anthropic_client

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
