import frappe

from erp_ai.constants import JOB_TIMEOUT_S, TRIGGER_COMMENT_MENTION, TRIGGER_TICKET_INSERT

PENDING_JOB_IDS_FLAG = "erp_ai_pending_job_ids"
VALID_TRIGGERS = (TRIGGER_TICKET_INSERT, TRIGGER_COMMENT_MENTION)
VALID_CHANGE_ACTIONS = ("apply", "undo")


def _clear_pending_job_ids():
	frappe.flags.pop(PENDING_JOB_IDS_FLAG, None)


def enqueue_agent_run(ticket_name: str, trigger: str) -> bool:
	if trigger not in VALID_TRIGGERS:
		raise ValueError(f"Unknown trigger: {trigger!r}")

	job_id = f"erp_ai::{ticket_name}::{trigger}"

	pending = frappe.flags.get(PENDING_JOB_IDS_FLAG)
	if pending is None:
		pending = set()
		frappe.flags[PENDING_JOB_IDS_FLAG] = pending
		frappe.db.after_commit.add(_clear_pending_job_ids)
		frappe.db.after_rollback.add(_clear_pending_job_ids)
	if job_id in pending:
		return False
	pending.add(job_id)

	frappe.enqueue(
		"erp_ai.agent.runner.run_for_ticket",
		queue="long",
		timeout=JOB_TIMEOUT_S,
		enqueue_after_commit=True,
		job_id=job_id,
		deduplicate=True,
		ticket_name=ticket_name,
		trigger=trigger,
	)
	return True


def enqueue_change_job(proposal_name: str, action: str) -> None:
	if not isinstance(proposal_name, str) or not proposal_name:
		raise ValueError(f"Invalid proposal_name: {proposal_name!r}")
	if action not in VALID_CHANGE_ACTIONS:
		raise ValueError(f"Unknown action: {action!r}")

	frappe.enqueue(
		"erp_ai.agent.changes.apply_job.run_change",
		queue="long",
		timeout=JOB_TIMEOUT_S,
		enqueue_after_commit=True,
		job_id=f"erp_ai_change::{proposal_name}::{action}",
		deduplicate=True,
		proposal_name=proposal_name,
		action=action,
	)
