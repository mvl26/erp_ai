import json

import frappe

from erp_ai.agent import redact
from erp_ai.agent.agent_write_guard import allow_agent_write
from erp_ai.agent.tools.site_api import SECRET_FIELDS
from erp_ai.constants import CHANGE_STEPS, LOG_DOCTYPE, TRIGGER_CHANGE_ACTION

ENTRY_TYPE_CHANGE = "change"
ENTRY_TYPES = ("classify", "reason", "skip", "change")
TRIGGERS = ("ticket_insert", "comment_mention")
CHANGE_TRIGGERS = (TRIGGER_CHANGE_ACTION,)
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
	`NO_REASON`) and `rule` when it is not blank. `doctype` is cut to `ACTION_DOCTYPE_MAX`. The values
	before/after are copied with secret keys, `SECRET_FIELDS` and the DocType's `Password` fields set to
	`SECRET_MASK`, and every string in them passed through `redact.redact_secrets`.

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
		entry["reason"] = reason if _is_name(reason) else NO_REASON
	if rule:
		entry["rule"] = rule
	return entry


def _check_change_fields(fields) -> None:
	if fields.get("change_step") not in CHANGE_STEPS:
		raise ValueError(f"change_step must be one of {CHANGE_STEPS}, got {fields.get('change_step')!r}")
	for fieldname in ("actor", "change_proposal"):
		if not _is_name(fields.get(fieldname)):
			raise ValueError(f"{fieldname} must be a non-empty name, got {fields.get(fieldname)!r}")


def write_entry(**fields) -> str:
	"""Create one ERP AI Log row; the only place that does (ADR-004, ADR-012 QĐ 6).

	List/dict values (`keys_tried`, `tools_called`, `actions`, `value_before`, `value_after`) are stored as JSON.
	`entry_type` and `trigger` are required (Frappe would silently default a Select to its first option).
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
	triggers = CHANGE_TRIGGERS if is_change else TRIGGERS
	if fields.get("trigger") not in triggers:
		raise ValueError(f"trigger must be one of {triggers}, got {fields.get('trigger')!r}")
	if is_change:
		_check_change_fields(fields)
	values = {
		key: json.dumps(value, ensure_ascii=False) if isinstance(value, list | dict) else value
		for key, value in fields.items()
	}
	doc = frappe.get_doc({**values, "doctype": LOG_DOCTYPE})
	with allow_agent_write():
		doc.insert(ignore_permissions=is_change)
	if not frappe.flags.in_test:
		frappe.db.commit()
	return doc.name
