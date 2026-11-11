import json

import frappe

from erp_ai.constants import LOG_DOCTYPE

ENTRY_TYPES = ("classify", "reason", "skip")
TRIGGERS = ("ticket_insert", "comment_mention")


def write_entry(**fields) -> str:
	"""Create one ERP AI Log row under the current (agent) session user; the only place that does (ADR-004).

	List/dict values (`keys_tried`, `tools_called`, `actions`, `value_before`, `value_after`) are stored as JSON.
	`entry_type` and `trigger` are required (Frappe would silently default a Select to its first option).
	Unknown fields are dropped by Frappe; a `doctype` argument is ignored.

	Raises:
		ValueError: `entry_type` or `trigger` is missing or not one of the allowed options.
		frappe.PermissionError: the session user may not create ERP AI Log.
	"""
	if fields.get("entry_type") not in ENTRY_TYPES:
		raise ValueError(f"entry_type must be one of {ENTRY_TYPES}, got {fields.get('entry_type')!r}")
	if fields.get("trigger") not in TRIGGERS:
		raise ValueError(f"trigger must be one of {TRIGGERS}, got {fields.get('trigger')!r}")
	values = {
		key: json.dumps(value, ensure_ascii=False) if isinstance(value, list | dict) else value
		for key, value in fields.items()
	}
	doc = frappe.get_doc({**values, "doctype": LOG_DOCTYPE}).insert()
	if not frappe.flags.in_test:
		frappe.db.commit()
	return doc.name
