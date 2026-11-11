from dataclasses import dataclass

from erp_ai import constants


@dataclass(frozen=True)
class ApiFailure:
	status: int | None
	kind: str
	error_type: str | None = None
	error_code: str | None = None
	message_prefix: str = ""
	retry_after: float | None = None


@dataclass(frozen=True)
class Action:
	new_status: str | None
	pause_seconds: float | None
	switch_key: bool
	notify: str | None
	kind: str


SPEND_LIMIT_ERROR_CODE = "enforced_spend_limit_reached"
QUOTA_MESSAGE_PREFIX = "You have reached your specified"
RATE_LIMIT_DEFAULT_PAUSE_S = 61
SERVER_PAUSE_S = 30
OVERLOADED_STEP_S = 30
OVERLOADED_CAP_S = 600


def _quota():
	return Action(constants.KEY_STATUS_QUOTA_EXHAUSTED, None, True, "message", "quota")


def decide(failure, error_count):
	"""Pure breaker table (design 3.4.3). error_count is the NEW count, already incremented."""
	status = failure.status
	if status == 429:
		if failure.error_code == SPEND_LIMIT_ERROR_CODE:
			return _quota()
		if failure.retry_after is None:
			pause = RATE_LIMIT_DEFAULT_PAUSE_S
		else:
			pause = failure.retry_after + 1
		return Action(constants.KEY_STATUS_PAUSED, pause, True, None, "rate_limit")
	if status == 529:
		pause = min(OVERLOADED_STEP_S * max(error_count, 1), OVERLOADED_CAP_S)
		return Action(constants.KEY_STATUS_PAUSED, pause, True, None, "overloaded")
	if status is not None and status >= 500:
		return Action(constants.KEY_STATUS_PAUSED, SERVER_PAUSE_S, True, None, "server")
	if status is None and failure.kind in ("timeout", "connection"):
		return Action(constants.KEY_STATUS_PAUSED, SERVER_PAUSE_S, True, None, "timeout")
	if status == 402:
		return _quota()
	if status == 400 and failure.message_prefix.startswith(QUOTA_MESSAGE_PREFIX):
		return _quota()
	if status in (401, 403):
		return Action(constants.KEY_STATUS_BAD_KEY, None, True, "alarm", "auth")
	if status is not None and 400 <= status < 500:
		return Action(None, None, False, None, "bad_request")
	return Action(None, None, False, None, "unexpected")
