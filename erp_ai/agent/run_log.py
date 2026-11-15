import json
import uuid

import frappe

from erp_ai.agent import policy, redact
from erp_ai.agent.agent_write_guard import allow_agent_write
from erp_ai.agent.tools.site_api import SECRET_FIELDS
from erp_ai.constants import CHANGE_STEPS, LOG_DOCTYPE, TRIGGER_CHANGE_ACTION

ENTRY_TYPE_CHANGE = "change"
ENTRY_TYPE_BOT_ACTION = "bot_action"
ENTRY_TYPES = ("classify", "reason", "skip", "change", "bot_action")
TRIGGERS = ("ticket_insert", "comment_mention")
CHANGE_TRIGGERS = (TRIGGER_CHANGE_ACTION,)
TRIGGER_SETTING_SAVE = "setting_save"
TRIGGER_SCHEDULED_JOB = "scheduled_job"
BOT_ACTION_TRIGGERS = (TRIGGER_SETTING_SAVE, TRIGGER_SCHEDULED_JOB)
TOOL_PERMISSION_SWITCH = "permission_switch"
# The one action-entry shape (ADR-033 QĐ 5): these keys always, in this order; then `reason`, `rule`.
ACTION_KEYS = ("tool", "doctype", "name", "ok", "value_before", "value_after", "instructor")
SECRET_MASK = "[đã ẩn]"
NO_REASON = "tool không nêu lý do"
ACTION_DOCTYPE_MAX = 80


def _is_name(value) -> bool:
	return isinstance(value, str) and bool(value.strip())


def _password_fields(doctype: str | None) -> frozenset:
	if not doctype or not frappe.db.exists("DocType", doctype):
		return frozenset()
	return frozenset(
		field.fieldname for field in frappe.get_meta(doctype).get("fields", {"fieldtype": "Password"})
	)


def _mask(values, secret_fields: frozenset):
	"""Copy `values`, masking secret keys and `secret_fields` by name and secrets inside every string leaf."""
	if isinstance(values, dict):
		return {
			key: SECRET_MASK
			if key in secret_fields or redact.is_secret_key(str(key))
			else _mask(value, secret_fields)
			for key, value in values.items()
		}
	if isinstance(values, list | tuple):
		return [_mask(value, secret_fields) for value in values]
	if isinstance(values, str):
		return redact.redact_secrets(values)
	return values


def action_entry(
	tool: str,
	doctype: str | None,
	name: str | None,
	ok: bool,
	*,
	reason: str | None = None,
	value_before: dict | None = None,
	value_after: dict | None = None,
	instructor: str | None = None,
	rule: str | None = None,
) -> dict:
	"""Build one entry of a log row's `actions`; the only place that does (ADR-033 Ràng buộc, U3 3.1).

	The entry has every key of `ACTION_KEYS` in order, then `reason` when `ok` is False (blank gives
	`NO_REASON`; otherwise `reason` passed through `redact.redact_secrets`) and `rule` when it is not
	blank. `doctype` is cut to `ACTION_DOCTYPE_MAX`. The values before/after are copied with secret keys,
	`SECRET_FIELDS` and the DocType's `Password` fields set to `SECRET_MASK`, and every string in them
	passed through `redact.redact_secrets`.

	Raises:
		ValueError: `tool` is not a non-empty string, `ok` is not a bool, or a value set is not a dict or None.
	"""
	if not _is_name(tool):
		raise ValueError(f"tool must be a non-empty string, got {tool!r}")
	if not isinstance(ok, bool):
		raise ValueError(f"ok must be a bool, got {ok!r}")
	for key, values in (("value_before", value_before), ("value_after", value_after)):
		if values is not None and not isinstance(values, dict):
			raise ValueError(f"{key} must be a dict or None, got {values!r}")
	secret_fields = SECRET_FIELDS | _password_fields(doctype)
	entry = {
		"tool": tool,
		"doctype": doctype[:ACTION_DOCTYPE_MAX] if doctype else None,
		"name": name,
		"ok": ok,
		"value_before": None if value_before is None else _mask(value_before, secret_fields),
		"value_after": None if value_after is None else _mask(value_after, secret_fields),
		"instructor": instructor,
	}
	if not ok:
		entry["reason"] = redact.redact_secrets(reason) if _is_name(reason) else NO_REASON
	if rule:
		entry["rule"] = rule
	return entry


def _check_change_fields(fields) -> None:
	if fields.get("change_step") not in CHANGE_STEPS:
		raise ValueError(f"change_step must be one of {CHANGE_STEPS}, got {fields.get('change_step')!r}")
	for fieldname in ("actor", "change_proposal"):
		if not _is_name(fields.get(fieldname)):
			raise ValueError(f"{fieldname} must be a non-empty name, got {fields.get(fieldname)!r}")


def _check_bot_action_fields(fields) -> None:
	actions = fields.get("actions")
	if not isinstance(actions, list) or not actions:
		raise ValueError(f"actions must be a non-empty list for a bot_action row, got {actions!r}")
	if fields.get("cost_usd") not in (None, 0):
		raise ValueError(
			f"cost_usd must be missing or 0 for a bot_action row, got {fields.get('cost_usd')!r}"
		)


def write_entry(**fields) -> str:
	"""Create one ERP AI Log row; the only place that does (ADR-004, ADR-012 QĐ 6).

	List/dict values (`keys_tried`, `tools_called`, `actions`, `value_before`, `value_after`) are stored as JSON.
	`entry_type` and `trigger` are required (Frappe would silently default a Select to its first option).
	`bot_action` rows (the bot's own work or a permission-switch change, never a model call) take
	`setting_save|scheduled_job`, a non-empty `actions` list and cost 0, and are inserted with
	`ignore_permissions=True`; every row without a `site_environment` gets `policy.site_environment()`.
	The checks run before the insert, so a refused row leaves nothing; insert and commit stay in this one call.
	`classify|reason|skip` rows take `ticket_insert|comment_mention` and are inserted under the session
	user's permissions. `change` rows (one per proposal step) take `trigger="change_action"` plus
	`change_step` in `CHANGE_STEPS`, `actor` and `change_proposal`, and are inserted with
	`ignore_permissions=True` so an approver who may not create ERP AI Log still leaves the audit row.
	Unknown fields are dropped by Frappe; a `doctype` argument is ignored. The insert alone runs inside
	`allow_agent_write()`: the one path by which the agent account may write ERP AI Log (ADR-023 QĐ 5).

	Raises:
		ValueError: `entry_type` or `trigger` is missing or not allowed for the entry type, or a `change`
			row has a missing/unknown `change_step` or a missing/blank `actor` or `change_proposal`.
		frappe.PermissionError: a non-`change` row and the session user may not create ERP AI Log.
	"""
	entry_type = fields.get("entry_type")
	if entry_type not in ENTRY_TYPES:
		raise ValueError(f"entry_type must be one of {ENTRY_TYPES}, got {entry_type!r}")
	is_change = entry_type == ENTRY_TYPE_CHANGE
	is_bot_action = entry_type == ENTRY_TYPE_BOT_ACTION
	triggers = CHANGE_TRIGGERS if is_change else BOT_ACTION_TRIGGERS if is_bot_action else TRIGGERS
	if fields.get("trigger") not in triggers:
		raise ValueError(f"trigger must be one of {triggers}, got {fields.get('trigger')!r}")
	if is_change:
		_check_change_fields(fields)
	if is_bot_action:
		_check_bot_action_fields(fields)
		fields = {**fields, "cost_usd": 0}
	if not fields.get("site_environment"):
		fields = {**fields, "site_environment": policy.site_environment()}
	values = {
		key: json.dumps(value, ensure_ascii=False) if isinstance(value, list | dict) else value
		for key, value in fields.items()
	}
	doc = frappe.get_doc({**values, "doctype": LOG_DOCTYPE})
	with allow_agent_write():
		doc.insert(ignore_permissions=is_change or is_bot_action)
	if not frappe.flags.in_test:
		frappe.db.commit()
	return doc.name


def write_bot_action(
	*,
	trigger: str,
	actions: list[dict],
	ticket: str | None = None,
	instructor: str | None = None,
	run_id: str | None = None,
	site_environment: str | None = None,
) -> str:
	"""Write one `bot_action` row (cost 0) and return its name (U3 3.1, ADR-033 QĐ 6).

	`run_id` is a new `uuid4().hex` when not given; `site_environment` is passed on only when not None
	(else `write_entry` fills it). Outside tests `write_entry` commits in this call, so the caller writes its
	own effect and its cycle lock first and calls this last: one commit covers all three.

	Raises:
		ValueError: as `write_entry` for a `trigger` outside `BOT_ACTION_TRIGGERS` or `actions` not a non-empty list.
	"""
	fields = {
		"entry_type": ENTRY_TYPE_BOT_ACTION,
		"trigger": trigger,
		"ticket": ticket,
		"instructor": instructor,
		"run_id": run_id or uuid.uuid4().hex,
		"actions": actions,
		"cost_usd": 0,
	}
	if site_environment is not None:
		fields["site_environment"] = site_environment
	return write_entry(**fields)
