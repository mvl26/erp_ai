import json

import frappe

from erp_ai.constants import LOG_DOCTYPE


def write_entry(**fields) -> str:
	"""Create one ERP AI Log row under the current (agent) session user; the only place that does (ADR-004).

	List/dict values (`keys_tried`, `tools_called`, `actions`, `value_before`, `value_after`) are stored as JSON.
	"""
	values = {
		key: json.dumps(value, ensure_ascii=False) if isinstance(value, list | dict) else value
		for key, value in fields.items()
	}
	doc = frappe.get_doc({"doctype": LOG_DOCTYPE, **values}).insert()
	if not frappe.flags.in_test:
		frappe.db.commit()
	return doc.name
