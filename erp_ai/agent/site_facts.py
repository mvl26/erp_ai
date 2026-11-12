"""Read-only facts about the site that routing decisions depend on (ADR-019 QĐ 5, ADR-021 QĐ 4).

Everything goes through `frappe.db`, never through document permissions, so the agent account can
read facts (such as the applied SLA) that its roles may not open as documents. The results only
feed decisions; they are not handed to the model or written into comments.
"""

import frappe


def ticket_assignments(ticket: str) -> list[dict]:
	"""ToDo rows of the ticket that are not Cancelled (Closed ones count: the ticket had an owner)."""
	return frappe.get_all(
		"ToDo",
		filters={"reference_type": "HD Ticket", "reference_name": ticket, "status": ("!=", "Cancelled")},
		fields=["allocated_to", "assignment_rule"],
		order_by="creation, name",
	)


def has_linked_task(ticket: str) -> bool:
	"""True when any Task, whoever owns it, points at the ticket through `ai_ticket`."""
	return bool(frappe.db.exists("Task", {"ai_ticket": ticket}))


def is_active_agent(user: str) -> bool:
	return bool(user) and bool(frappe.db.exists("HD Agent", {"user": user, "is_active": 1}))


def team_exists(team: str) -> bool:
	return bool(team) and bool(frappe.db.exists("HD Team", team))


def applied_sla(ticket: str) -> dict | None:
	"""`{"sla", "priority", "resolution_s"}` of the SLA on the ticket; None when the ticket has no SLA."""
	sla, priority = frappe.db.get_value("HD Ticket", ticket, ["sla", "priority"]) or (None, None)
	if not sla:
		return None
	resolution_s = frappe.db.get_value(
		"HD Service Level Priority", {"parent": sla, "priority": priority}, "resolution_time"
	)
	return {"sla": sla, "priority": priority, "resolution_s": resolution_s}
