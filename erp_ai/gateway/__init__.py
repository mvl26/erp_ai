import time
from dataclasses import dataclass

import frappe

from erp_ai import alerts
from erp_ai.constants import LOGGER_NAME, SETTING_DOCTYPE
from erp_ai.gateway import breaker, client, cost, credentials

TASKS = ("classify", "reason")
DEFAULT_MAX_KEYS_PER_CALL = 3
DEFAULT_REQUEST_TIMEOUT_S = 60
MIN_REMAINING_S = 5
USAGE_FIELDS = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
PRICE_FIELDS = (
	"price_input_per_mtok",
	"price_cache_write_per_mtok",
	"price_cache_read_per_mtok",
	"price_output_per_mtok",
)


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


def _read_settings() -> dict:
	fields = ("max_keys_per_call", "request_timeout_s", "model_classify_default", *PRICE_FIELDS)
	values = frappe.db.get_singles_dict(SETTING_DOCTYPE, cast=True)
	settings = {field: values.get(field) for field in fields}
	settings["max_keys_per_call"] = max(int(settings["max_keys_per_call"] or DEFAULT_MAX_KEYS_PER_CALL), 1)
	settings["request_timeout_s"] = settings["request_timeout_s"] or DEFAULT_REQUEST_TIMEOUT_S
	return settings


def _normalize_usage(usage) -> dict:
	usage = usage or {}
	return {field: usage.get(field) or 0 for field in USAGE_FIELDS}


def _notify(action, row, failure) -> None:
	subject = f"Khóa '{row.label}': {action.kind}"
	message = f"{subject} (status={failure.status}); trạng thái khóa chuyển sang '{action.new_status}'."
	try:
		if action.notify == "alarm":
			alerts.send_alarm(subject, message)
		else:
			alerts.send_notice(subject, message)
	except Exception:
		frappe.log_error("erp_ai: không gửi được thông báo khóa", f"{subject}; gửi thông báo lỗi")


def _alarm_no_key(task) -> None:
	subject = f"Hết khóa dùng được cho việc '{task}'"
	try:
		alerts.send_alarm(subject, subject)
	except Exception:
		frappe.log_error("erp_ai: không gửi được thông báo khóa", f"{subject}; gửi báo động lỗi")


def call_model(task, *, system, messages, max_tokens, tools=None, deadline=None) -> ModelResult:
	"""Call the model with key failover driven by the breaker table (design 3.4)."""
	if task not in TASKS:
		raise ValueError(f"task must be one of {TASKS}")
	started = time.monotonic()
	settings = _read_settings()
	prices = {field: settings[field] or 0 for field in PRICE_FIELDS}
	keys_tried = []
	tried_labels = set()
	last = {}
	for _ in range(settings["max_keys_per_call"]):
		timeout = settings["request_timeout_s"]
		if deadline is not None:
			remaining = deadline - time.monotonic()
			if remaining < MIN_REMAINING_S:
				raise GatewayError("deadline", keys_tried=keys_tried, **last) from None
			timeout = min(timeout, remaining)
		rows = credentials.select_keys(task, tried_labels)
		if not rows:
			break
		row = rows[0]
		tried_labels.add(row.label)
		api_key = credentials.get_api_key(row.name)
		if api_key is None:
			continue
		model = (
			row.model_reason if task == "reason" else row.model_classify or settings["model_classify_default"]
		)
		request = {"model": model, "max_tokens": max_tokens, "system": system, "messages": messages}
		if tools:
			request["tools"] = tools
		last = {"credential_label": row.label}
		try:
			reply = client.send(api_key, timeout=timeout, request=request)
		except Exception as exc:
			failure = client.to_api_failure(exc)
			if failure is None:
				keys_tried.append({"label": row.label, "outcome": "unexpected"})
				frappe.logger(LOGGER_NAME).warning(
					"gateway unexpected %s key=%s", type(exc).__name__, row.label
				)
				raise GatewayError("unexpected", keys_tried=keys_tried, **last) from None
			request_id = getattr(exc, "request_id", None)
			action = breaker.decide(failure, (row.error_count or 0) + 1)
			credentials.apply_failure(row.name, action, failure, request_id=request_id)
			keys_tried.append({"label": row.label, "outcome": action.kind})
			last = {"status": failure.status, "credential_label": row.label, "request_id": request_id}
			if not action.switch_key:
				raise GatewayError("bad_request", keys_tried=keys_tried, **last) from None
			if action.notify and action.new_status != row.status:
				_notify(action, row, failure)
			continue
		credentials.apply_success(row.name, reply.headers)
		keys_tried.append({"label": row.label, "outcome": "ok"})
		message = reply.message
		usage = _normalize_usage(message.get("usage"))
		content = message.get("content") or []
		return ModelResult(
			content=content,
			text="".join(block.get("text", "") for block in content if block.get("type") == "text"),
			stop_reason=message.get("stop_reason"),
			model=message.get("model") or model,
			usage=usage,
			cost_usd=cost.compute_cost(usage, prices),
			credential_label=row.label,
			keys_tried=keys_tried,
			latency_ms=int((time.monotonic() - started) * 1000),
			request_id=reply.request_id,
		)
	kind = "all_keys_failed" if keys_tried else "no_key"
	_alarm_no_key(task)
	raise GatewayError(kind, keys_tried=keys_tried, **last) from None
