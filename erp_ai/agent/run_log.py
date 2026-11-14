import json

import frappe

from erp_ai.agent.agent_write_guard import allow_agent_write
from erp_ai.constants import CHANGE_STEPS, LOG_DOCTYPE, TRIGGER_CHANGE_ACTION

ENTRY_TYPE_CHANGE = "change"
ENTRY_TYPES = ("classify", "reason", "skip", "change")
TRIGGERS = ("ticket_insert", "comment_mention")
CHANGE_TRIGGERS = (TRIGGER_CHANGE_ACTION,)


def _is_name(value) -> bool:
	return isinstance(value, str) and bool(value.strip())


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
