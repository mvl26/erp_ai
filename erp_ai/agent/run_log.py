import contextlib
import json
import uuid

import frappe

from erp_ai.agent import policy, redact
from erp_ai.agent.agent_write_guard import allow_agent_write
from erp_ai.agent.tools.site_api import SECRET_FIELDS
from erp_ai.constants import (
	CHANGE_STEPS,
	EVENT_CALL_BUSY,
	EVENT_CALL_MERGED,
	EVENT_CALL_RECEIVED,
	EVENT_RUN_DONE,
	EVENT_RUN_FAILED,
	LOG_DOCTYPE,
	LOG_ENTRY_RUN_EVENT,
	SKIP_AGENT_DISABLED,
	SKIP_CREATED_BY_AGENT,
	SKIP_NOT_SENDABLE,
	SKIP_PREFILLED,
	TITLE_EVENT_FAILED,
	TRIGGER_CHANGE_ACTION,
	TRIGGER_SUPPORT_CHAT,
)

ENTRY_TYPE_CHANGE = "change"
ENTRY_TYPE_BOT_ACTION = "bot_action"
ENTRY_TYPES = ("classify", "reason", "skip", "change", "bot_action", "run_event")
TRIGGERS = ("ticket_insert", "comment_mention", "requester_reply", "kb_draft", TRIGGER_SUPPORT_CHAT)
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
# CHG-009 (ADR-048 QĐ 1, 4; design 3.4): the codes a run_event row carries: the call and run events, then why a
# call was refused, as decided (`policy.send_refusal` for the four send kinds; a missing ticket writes no row).
EVENT_CODES = (
	EVENT_CALL_RECEIVED,
	EVENT_CALL_MERGED,
	EVENT_CALL_BUSY,
	EVENT_RUN_DONE,
	EVENT_RUN_FAILED,
	SKIP_AGENT_DISABLED,
	SKIP_CREATED_BY_AGENT,
	SKIP_PREFILLED,
	*(
		f"{SKIP_NOT_SENDABLE}:{refusal}"
		for refusal in (
			policy.REFUSAL_OPTED_OUT,
			policy.REFUSAL_EXCLUDED_TEAM,
			policy.REFUSAL_EXCLUDED_TITLE,
			policy.REFUSAL_EXCLUDED_BY_CLASSIFICATION,
		)
	),
)
# Only these carry a run_id: the run the received call queued, or the run that ended.
RUN_EVENT_CODES = (EVENT_CALL_RECEIVED, EVENT_RUN_DONE, EVENT_RUN_FAILED)
EVENT_SAVEPOINT = "erp_ai_run_event"


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


def _check_run_event_fields(fields) -> None:
	code, run_id = fields.get("stop_reason"), fields.get("run_id")
	if code not in EVENT_CODES:
		raise ValueError(f"stop_reason must be one of {EVENT_CODES} for a run_event row, got {code!r}")
	if code in RUN_EVENT_CODES and not _is_name(run_id):
		raise ValueError(f"run_id must be a non-empty name for a {code} row, got {run_id!r}")
	if code not in RUN_EVENT_CODES and run_id not in (None, ""):
		raise ValueError(f"run_id must be empty for a {code} row, got {run_id!r}")
	for fieldname in ("actions", "error"):
		if fields.get(fieldname) not in (None, ""):
			raise ValueError(f"{fieldname} must be empty for a run_event row, got {fields.get(fieldname)!r}")
	if fields.get("cost_usd") not in (None, 0):
		raise ValueError(f"cost_usd must be missing or 0 for a run_event row, got {fields.get('cost_usd')!r}")


def _check_actions(fields) -> None:
	"""Every element of `actions` (when given as a list) is a dict holding every key of `ACTION_KEYS`."""
	actions = fields.get("actions")
	if not isinstance(actions, list):
		return
	for index, entry in enumerate(actions):
		if not isinstance(entry, dict) or not set(ACTION_KEYS) <= entry.keys():
			raise ValueError(f"actions[{index}] must be an entry built by action_entry, got {entry!r}")


def write_entry(**fields) -> str:
	"""Create one ERP AI Log row; the only place that does (ADR-004, ADR-012 QĐ 6).

	List/dict values (`keys_tried`, `tools_called`, `actions`, `value_before`, `value_after`) are stored as JSON.
	`entry_type` and `trigger` are required (Frappe would silently default a Select to its first option).
	`bot_action` rows (the bot's own work or a permission-switch change, never a model call) take
	`setting_save|scheduled_job`, a non-empty `actions` list and cost 0, and are inserted with
	`ignore_permissions=True`; every row without a `site_environment` gets `policy.site_environment()`.
	Every element of an `actions` list must hold every key of `ACTION_KEYS` (build it with `action_entry`).
	The checks run before the insert, so a refused row leaves nothing; insert and commit stay in this one call.
	`classify|reason|skip` rows take `ticket_insert|comment_mention` and are inserted under the session
	user's permissions. `change` rows (one per proposal step) take `trigger="change_action"` plus
	`change_step` in `CHANGE_STEPS`, `actor` and `change_proposal`, and are inserted with
	`ignore_permissions=True` so an approver who may not create ERP AI Log still leaves the audit row.
	`run_event` rows (ADR-048, written through `record_event`) take a `TRIGGERS` trigger, a `stop_reason` in
	`EVENT_CODES`, a `run_id` exactly when the code is in `RUN_EVENT_CODES` (else none is stored), no
	`actions` or `error` and cost 0; they are inserted with `ignore_permissions=True` and never committed here:
	they ride the caller's transaction. Every other row is committed right after its insert (ADR-024).
	Unknown fields are dropped by Frappe; a `doctype` argument is ignored. The insert alone runs inside
	`allow_agent_write()`: the one path by which the agent account may write ERP AI Log (ADR-023 QĐ 5).

	Raises:
		ValueError: `entry_type` or `trigger` is missing or not allowed for the entry type, an `actions`
			element is not a dict with every key of `ACTION_KEYS`, a `change`
			row has a missing/unknown `change_step` or a missing/blank `actor` or `change_proposal`, or a
			`run_event` row breaks one of its rules above.
		frappe.PermissionError: a non-`change` row and the session user may not create ERP AI Log.
	"""
	entry_type = fields.get("entry_type")
	if entry_type not in ENTRY_TYPES:
		raise ValueError(f"entry_type must be one of {ENTRY_TYPES}, got {entry_type!r}")
	is_change = entry_type == ENTRY_TYPE_CHANGE
	is_bot_action = entry_type == ENTRY_TYPE_BOT_ACTION
	is_run_event = entry_type == LOG_ENTRY_RUN_EVENT
	# Any agent may ask the support chat, few may create ERP AI Log: its row is written for them.
	is_support = fields.get("trigger") == TRIGGER_SUPPORT_CHAT
	triggers = CHANGE_TRIGGERS if is_change else BOT_ACTION_TRIGGERS if is_bot_action else TRIGGERS
	if fields.get("trigger") not in triggers:
		raise ValueError(f"trigger must be one of {triggers}, got {fields.get('trigger')!r}")
	if is_change:
		_check_change_fields(fields)
	if is_bot_action:
		_check_bot_action_fields(fields)
		fields = {**fields, "cost_usd": 0}
	if is_run_event:
		_check_run_event_fields(fields)
		# change_step "" (not None) so Frappe leaves it empty instead of its first option "propose", which the
		# 08:00 report counts as a proposal (design 2 "còn lại trống", ADR-048 QĐ 5)
		fields = {**fields, "cost_usd": 0, "run_id": fields.get("run_id") or None, "change_step": ""}
	_check_actions(fields)
	if not fields.get("site_environment"):
		fields = {**fields, "site_environment": policy.site_environment()}
	values = {
		key: json.dumps(value, ensure_ascii=False) if isinstance(value, list | dict) else value
		for key, value in fields.items()
	}
	doc = frappe.get_doc({**values, "doctype": LOG_DOCTYPE})
	with allow_agent_write():
		doc.insert(ignore_permissions=is_change or is_bot_action or is_run_event or is_support)
	if not frappe.flags.in_test and not is_run_event:
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


def record_event(*, ticket, trigger, code, run_id=None) -> str | None:
	"""Write one `run_event` row for `ticket` and return its name (ADR-048 QĐ 1, 3; design 3.4).

	The row holds only codes: `trigger`, `code` (in `EVENT_CODES`) and `run_id` (only for `RUN_EVENT_CODES`).
	It is written inside savepoint `EVENT_SAVEPOINT` of the caller's transaction and never committed here: the
	caller's own commit keeps it. A ticket that does not exist gives None and no row. Any error undoes the
	write back to the savepoint, leaves one Error Log `TITLE_EVENT_FAILED` holding the codes and the error class
	only, and gives None; a failing rollback or Error Log is dropped. Never raises: the caller's work goes on.
	"""
	saved = False
	try:
		if not ticket or not frappe.db.exists(policy.TICKET_DOCTYPE, ticket):
			return None
		frappe.db.savepoint(EVENT_SAVEPOINT)
		saved = True
		name = write_entry(
			entry_type=LOG_ENTRY_RUN_EVENT, ticket=ticket, trigger=trigger, stop_reason=code, run_id=run_id
		)
		frappe.db.release_savepoint(EVENT_SAVEPOINT)
		return name
	except Exception as exc:
		_drop_event(saved, f"ticket={ticket} trigger={trigger} code={code} error={type(exc).__name__}")
		return None


def _drop_event(saved: bool, message: str) -> None:
	"""Undo a failed event write back to its savepoint, then leave one Error Log with `message`.

	A failure of either is dropped on purpose: the event row is a note for the panel, and the caller's own
	work (a ticket, a comment, a message, a run) must still be saved (ADR-048 QĐ 3).
	"""
	if saved:
		with contextlib.suppress(Exception):
			frappe.db.rollback(save_point=EVENT_SAVEPOINT)
	with contextlib.suppress(Exception):
		frappe.log_error(TITLE_EVENT_FAILED, message)
