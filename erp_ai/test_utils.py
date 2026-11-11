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
