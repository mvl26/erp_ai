import frappe

from erp_ai.agent.queue import enqueue_agent_run
from erp_ai.constants import AGENT_USER, SETTING_DOCTYPE, TRIGGER_TICKET_INSERT


def ticket_after_insert(doc, method=None):
	try:
		enabled = frappe.db.get_single_value(SETTING_DOCTYPE, "enabled")
	except frappe.DoesNotExistError:
		# The ERP AI Setting DocType is not migrated yet: treat the agent as disabled.
		return
	if not enabled:
		return
	if doc.owner == AGENT_USER:
		return
	enqueue_agent_run(doc.name, TRIGGER_TICKET_INSERT)
