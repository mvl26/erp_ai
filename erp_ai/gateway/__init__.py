import time
from dataclasses import dataclass

import frappe

from erp_ai import alerts
from erp_ai.constants import (
	CREDENTIAL_DOCTYPE,
	KEY_STATUS_QUOTA_EXHAUSTED,
	LOGGER_NAME,
	PROBE_TIMEOUT_S,
	SETTING_DOCTYPE,
)
from erp_ai.gateway import breaker, client, cost, credentials

TASKS = ("classify", "reason")
DEFAULT_MAX_KEYS_PER_CALL = 3
DEFAULT_REQUEST_TIMEOUT_S = 60
MIN_REMAINING_S = 5
# Classify answers with one short JSON object. Haiku 5.5 thinks by default and its (hidden) thinking
# tokens count against max_tokens, so with thinking on a 600 ceiling is hit about 1 call in 4.
CLASSIFY_THINKING = {"type": "disabled"}
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
	except Exception as exc:
		frappe.log_error(
			"erp_ai: không gửi được thông báo khóa", f"{subject}; gửi thông báo lỗi: {type(exc).__name__}"
		)


def _alarm_no_key(task) -> None:
	subject = f"Hết khóa dùng được cho việc '{task}'"
	try:
		alerts.send_alarm(subject, subject)
	except Exception as exc:
		frappe.log_error(
			"erp_ai: không gửi được thông báo khóa", f"{subject}; gửi báo động lỗi: {type(exc).__name__}"
		)


@dataclass(frozen=True)
class _Attempt:
	kind: str
	reply: object = None
	failure: object = None
	request_id: str | None = None
	switch_key: bool = False


def _attempt_key(row, api_key, timeout, request) -> _Attempt:
	"""One send on one key: applies the breaker table to the key row and notifies (design 3.4)."""
	try:
		reply = client.send(api_key, timeout=timeout, request=request)
	except Exception as exc:
		failure = client.to_api_failure(exc)
		if failure is None:
			frappe.logger(LOGGER_NAME).warning("gateway unexpected %s key=%s", type(exc).__name__, row.label)
			return _Attempt("unexpected")
		request_id = getattr(exc, "request_id", None)
		action = breaker.decide(failure, (row.error_count or 0) + 1)
		credentials.apply_failure(row.name, action, failure, request_id=request_id)
		if action.notify and action.new_status != row.status:
			_notify(action, row, failure)
		return _Attempt(action.kind, failure=failure, request_id=request_id, switch_key=action.switch_key)
	credentials.apply_success(row.name, reply.headers)
	return _Attempt("ok", reply=reply)


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
			frappe.logger(LOGGER_NAME).warning("gateway key has no stored secret key=%s", row.label)
			continue
		model = (
			row.model_reason if task == "reason" else row.model_classify or settings["model_classify_default"]
		)
		request = {"model": model, "max_tokens": max_tokens, "system": system, "messages": messages}
		if task == "classify":
			request["thinking"] = CLASSIFY_THINKING
		if tools:
			request["tools"] = tools
		last = {"credential_label": row.label}
		attempt = _attempt_key(row, api_key, timeout, request)
		keys_tried.append({"label": row.label, "outcome": attempt.kind})
		if attempt.kind == "unexpected":
			raise GatewayError("unexpected", keys_tried=keys_tried, **last) from None
		if attempt.failure is not None:
			last = {
				"status": attempt.failure.status,
				"credential_label": row.label,
				"request_id": attempt.request_id,
			}
			if not attempt.switch_key:
				raise GatewayError("bad_request", keys_tried=keys_tried, **last) from None
			continue
		reply = attempt.reply
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


def probe_credential(row_name: str) -> dict:
	"""One-token ping on one key row; updates the key status like a real call (design 3.4.1)."""
	row = frappe.db.get_value(CREDENTIAL_DOCTYPE, row_name, credentials.ROW_FIELDS, as_dict=True)
	if row is None:
		return {"label": None, "ok": False, "error_kind": "not_found", "status": None}
	result = {"label": row.label, "ok": False, "error_kind": None, "status": None}
	if row.provider != credentials.PROVIDER:
		return {**result, "error_kind": "unsupported_provider"}
	api_key = credentials.get_api_key(row.name)
	if api_key is None:
		return {**result, "error_kind": "no_secret"}
	model = row.model_classify or _read_settings()["model_classify_default"]
	request = {"model": model, "max_tokens": 1, "messages": [{"role": "user", "content": "ping"}]}
	attempt = _attempt_key(row, api_key, PROBE_TIMEOUT_S, request)
	if attempt.kind == "ok":
		return {**result, "ok": True}
	return {
		**result,
		"error_kind": attempt.kind,
		"status": attempt.failure.status if attempt.failure else None,
	}


def reprobe_exhausted_keys() -> list[dict]:
	"""Probe only enabled keys in status 'Hết hạn mức'; a recovered key gets a notice."""
	names = frappe.db.get_all(
		CREDENTIAL_DOCTYPE,
		filters={
			"parent": SETTING_DOCTYPE,
			"parenttype": SETTING_DOCTYPE,
			"parentfield": "credentials",
			"enabled": 1,
			"status": KEY_STATUS_QUOTA_EXHAUSTED,
		},
		order_by="idx",
		pluck="name",
	)
	results = []
	for name in names:
		result = probe_credential(name)
		if result["ok"]:
			subject = f"Khóa {result['label']} đã dùng lại được"
			try:
				alerts.send_notice(subject, subject)
			except Exception as exc:
				frappe.log_error(
					"erp_ai: không gửi được thông báo khóa",
					f"{subject}; gửi thông báo lỗi: {type(exc).__name__}",
				)
		results.append(result)
	return results
