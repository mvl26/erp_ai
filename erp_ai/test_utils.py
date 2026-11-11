import frappe

from erp_ai.agent.run_log import write_entry
from erp_ai.constants import SETTING_DOCTYPE
from erp_ai.gateway import GatewayError, ModelResult


def make_model_result(**kw) -> ModelResult:
	fields = {
		"content": [],
		"text": "",
		"stop_reason": "end_turn",
		"model": "fake-model",
		"usage": {
			"input_tokens": 0,
			"output_tokens": 0,
			"cache_creation_input_tokens": 0,
			"cache_read_input_tokens": 0,
		},
		"cost_usd": 0.0,
		"credential_label": "fake",
		"keys_tried": [],
		"latency_ms": 0,
		"request_id": "req_fake",
	}
	fields.update(kw)
	return ModelResult(**fields)


class FakeGateway:
	"""Thay `erp_ai.gateway.call_model`: trả lần lượt các kết quả đã xếp, ném nếu là GatewayError."""

	def __init__(self, *results):
		self.results = list(results)
		self.calls = []

	@property
	def call_count(self) -> int:
		return len(self.calls)

	def __call__(self, task, **kwargs):
		self.calls.append({"task": task, **kwargs})
		result = self.results.pop(0) if self.results else make_model_result()
		if isinstance(result, GatewayError):
			raise result
		return result


def set_agent_settings(**fields) -> None:
	"""Set ERP AI Setting values directly in the DB (no validate), for tests."""
	for fieldname, value in fields.items():
		frappe.db.set_single_value(SETTING_DOCTYPE, fieldname, value)


def add_credential(label, **fields) -> str:
	"""Append a key row to ERP AI Setting without validation and return the child row name."""
	settings = frappe.get_single(SETTING_DOCTYPE)
	settings.append("credentials", {"label": label, "api_key": f"sk-{label}", **fields})
	settings.flags.ignore_validate = True
	settings.save(ignore_permissions=True)
	return settings.credentials[-1].name


class _FakeRawResponse:
	def __init__(self, message, headers, request_id):
		self._message = message
		self.headers = headers
		self.request_id = request_id

	def parse(self):
		return _FakeMessage(self._message, self.request_id)


class _FakeMessage:
	def __init__(self, message, request_id):
		self._message = message
		self._request_id = request_id

	def model_dump(self) -> dict:
		return dict(self._message)


class _FakeRawMessages:
	def __init__(self, owner):
		self._owner = owner

	def create(self, **request):
		self._owner.requests.append(request)
		if self._owner.error is not None:
			raise self._owner.error
		return _FakeRawResponse(self._owner.message, self._owner.headers, self._owner.request_id)


class _FakeMessages:
	def __init__(self, owner):
		self.with_raw_response = _FakeRawMessages(owner)


class FakeAnthropicClient:
	"""Thay `anthropic.Anthropic` trong test: không mạng, ghi lại mọi `messages.create(**request)`."""

	def __init__(self, message=None, headers=None, request_id="req_fake", error=None):
		self.message = message if message is not None else {"type": "message", "content": []}
		self.headers = headers or {}
		self.request_id = request_id
		self.error = error
		self.requests = []
		self.messages = _FakeMessages(self)


def fake_anthropic_client(**kwargs) -> FakeAnthropicClient:
	return FakeAnthropicClient(**kwargs)


def make_log_entry(**fields) -> str:
	"""Write an ERP AI Log row through `run_log.write_entry` (current session user must be allowed) and return its name."""
	values = {"run_id": "ERPAI-TEST-run", "entry_type": "skip", "trigger": "ticket_insert", "turn": 0}
	values.update(fields)
	return write_entry(**values)
