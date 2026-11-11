from dataclasses import dataclass

import anthropic

from erp_ai.gateway.breaker import ApiFailure

MESSAGE_PREFIX_LENGTH = 100


@dataclass(frozen=True)
class RawReply:
	message: dict
	headers: dict
	request_id: str


def _build_client(api_key: str, timeout: float):
	return anthropic.Anthropic(api_key=api_key, max_retries=0, timeout=timeout)


def send(api_key: str, *, timeout: float, request: dict) -> RawReply:
	raw = _build_client(api_key, timeout).messages.with_raw_response.create(**request)
	message = raw.parse()
	return RawReply(
		message=message.model_dump(),
		headers=dict(raw.headers),
		request_id=getattr(message, "_request_id", None),
	)


def _retry_after(response) -> float | None:
	try:
		return float(response.headers.get("retry-after"))
	except (TypeError, ValueError):
		return None


def to_api_failure(exc) -> ApiFailure | None:
	"""Đổi ngoại lệ SDK thành ApiFailure; ngoại lệ không thuộc API → None."""
	if isinstance(exc, anthropic.APITimeoutError):
		return ApiFailure(status=None, kind="timeout")
	if isinstance(exc, anthropic.APIConnectionError):
		return ApiFailure(status=None, kind="connection")
	if isinstance(exc, anthropic.APIStatusError):
		body = exc.body if isinstance(exc.body, dict) else {}
		error = body.get("error")
		error = error if isinstance(error, dict) else {}
		details = error.get("details")
		details = details if isinstance(details, dict) else {}
		return ApiFailure(
			status=exc.status_code,
			kind="api",
			error_type=error.get("type"),
			error_code=details.get("error_code"),
			message_prefix=str(error.get("message") or "")[:MESSAGE_PREFIX_LENGTH],
			retry_after=_retry_after(exc.response),
		)
	return None
