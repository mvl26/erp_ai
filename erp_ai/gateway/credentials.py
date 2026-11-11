import datetime

import frappe
from frappe.utils import add_to_date, now_datetime
from frappe.utils.data import convert_utc_to_system_timezone
from frappe.utils.password import get_decrypted_password

from erp_ai.constants import (
	CREDENTIAL_DOCTYPE,
	KEY_STATUS_ACTIVE,
	KEY_STATUS_BAD_KEY,
	KEY_STATUS_PAUSED,
	KEY_STATUS_QUOTA_EXHAUSTED,
	SETTING_DOCTYPE,
)

PROVIDER = "Anthropic"
DEFAULT_TRY_ORDER = 99
LOW_TOKENS_THRESHOLD = 20000
TOKENS_REMAINING_HEADER = "anthropic-ratelimit-tokens-remaining"
TOKENS_RESET_HEADER = "anthropic-ratelimit-tokens-reset"
ROW_FIELDS = [
	"name",
	"idx",
	"label",
	"provider",
	"model_classify",
	"model_reason",
	"try_order",
	"purpose",
	"budget_month_usd",
	"spent_month_usd",
	"enabled",
	"status",
	"paused_until",
	"tokens_remaining",
	"limit_reset_at",
	"error_count",
	"last_error",
	"last_success_at",
]
UNUSABLE_STATUSES = (KEY_STATUS_BAD_KEY, KEY_STATUS_QUOTA_EXHAUSTED)


def _is_usable(row, task, exclude, now):
	if not row.enabled or row.status in UNUSABLE_STATUSES or row.provider != PROVIDER:
		return False
	if row.label in exclude:
		return False
	if row.paused_until and row.paused_until > now:
		return False
	if (row.budget_month_usd or 0) > 0 and (row.spent_month_usd or 0) >= row.budget_month_usd:
		return False
	return task != "reason" or bool(row.model_reason)


def select_keys(task: str, exclude: set[str]) -> list[dict]:
	"""Key rows usable for `task`, best first; `exclude` holds labels already tried. Never returns the key text."""
	rows = frappe.db.get_all(
		CREDENTIAL_DOCTYPE,
		filters={
			"parent": SETTING_DOCTYPE,
			"parenttype": SETTING_DOCTYPE,
			"parentfield": "credentials",
		},
		fields=ROW_FIELDS,
	)
	now = now_datetime()
	usable = [row for row in rows if _is_usable(row, task, exclude, now)]
	usable.sort(key=lambda r: (r.try_order or DEFAULT_TRY_ORDER, r.error_count or 0, r.idx))
	return usable


def get_api_key(row_name: str) -> str | None:
	return get_decrypted_password(CREDENTIAL_DOCTYPE, row_name, "api_key", raise_exception=False)


def _write(row_name, values):
	frappe.db.set_value(CREDENTIAL_DOCTYPE, row_name, values, update_modified=False)


def apply_failure(row_name, action, failure, request_id=None) -> None:
	"""Record a breaker `action`; no new status means the failure is not the key's fault."""
	if action.new_status is None:
		return
	error_count = frappe.db.get_value(CREDENTIAL_DOCTYPE, row_name, "error_count") or 0
	last_error = f"{action.kind} status={failure.status}"
	if request_id:
		last_error += f" request_id={request_id}"
	values = {
		"status": action.new_status,
		"error_count": error_count + 1,
		"last_error": last_error,
	}
	if action.pause_seconds is not None:
		values["paused_until"] = add_to_date(now_datetime(), seconds=action.pause_seconds)
	_write(row_name, values)


def _parse_tokens_remaining(headers):
	try:
		return int(headers.get(TOKENS_REMAINING_HEADER))
	except (TypeError, ValueError):
		return None


def _parse_reset_time(headers):
	try:
		parsed = datetime.datetime.fromisoformat(headers.get(TOKENS_RESET_HEADER))
	except (TypeError, ValueError):
		return None
	if parsed.tzinfo is None:
		return None
	return convert_utc_to_system_timezone(parsed.astimezone(datetime.timezone.utc)).replace(tzinfo=None)


def apply_success(row_name, headers) -> None:
	values = {
		"status": KEY_STATUS_ACTIVE,
		"error_count": 0,
		"last_error": "",
		"last_success_at": now_datetime(),
		"paused_until": None,
	}
	tokens_remaining = _parse_tokens_remaining(headers)
	reset_at = _parse_reset_time(headers)
	if tokens_remaining is not None:
		values["tokens_remaining"] = tokens_remaining
	if reset_at is not None:
		values["limit_reset_at"] = reset_at
	if tokens_remaining is not None and tokens_remaining < LOW_TOKENS_THRESHOLD and reset_at is not None:
		values["status"] = KEY_STATUS_PAUSED
		values["paused_until"] = reset_at
	_write(row_name, values)
