import frappe

from erp_ai.agent.queue import enqueue_agent_run
from erp_ai.constants import AGENT_USER, SETTING_DOCTYPE, TRIGGER_TICKET_INSERT


def ticket_after_insert(doc, method=None):
	# Temporary guard: the hook is registered in T1 but the setting DocType is created in T9.
	# T31 removes this guard once T9 has created the DocType.
	if not frappe.db.exists("DocType", SETTING_DOCTYPE):
		return
	if not frappe.db.get_single_value(SETTING_DOCTYPE, "enabled"):
		return
	if doc.owner == AGENT_USER:
		return
	enqueue_agent_run(doc.name, TRIGGER_TICKET_INSERT)
