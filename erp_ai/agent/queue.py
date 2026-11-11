import frappe

from erp_ai.constants import JOB_TIMEOUT_S


def enqueue_agent_run(ticket_name: str, trigger: str) -> bool:
	frappe.enqueue(
		"erp_ai.agent.runner.run_for_ticket",
		queue="long",
		timeout=JOB_TIMEOUT_S,
		enqueue_after_commit=True,
		job_id=f"erp_ai::{ticket_name}::{trigger}",
		deduplicate=True,
		ticket_name=ticket_name,
		trigger=trigger,
	)
	return True
