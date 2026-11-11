from dataclasses import dataclass


@dataclass(frozen=True)
class ModelResult:
	content: list
	text: str
	stop_reason: str
	model: str
	usage: dict
	cost_usd: float
	credential_label: str
	keys_tried: list
	latency_ms: int
	request_id: str


class GatewayError(Exception):
	def __init__(self, kind, status=None, credential_label=None, request_id=None, keys_tried=None):
		self.kind = kind
		self.status = status
		self.credential_label = credential_label
		self.request_id = request_id
		self.keys_tried = keys_tried or []
		super().__init__(f"kind={kind} status={status} credential={credential_label} request_id={request_id}")


def call_model(task, *, system, messages, max_tokens, tools=None, deadline=None) -> ModelResult:
	raise NotImplementedError("Cổng model chưa được cài đặt")
