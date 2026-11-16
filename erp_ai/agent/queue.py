import uuid

import frappe
from frappe.utils import background_jobs

from erp_ai.agent.run_log import record_event
from erp_ai.constants import (
	EVENT_CALL_BUSY,
	EVENT_CALL_MERGED,
	EVENT_CALL_RECEIVED,
	JOB_TIMEOUT_S,
	TRIGGER_COMMENT_MENTION,
	TRIGGER_KB_DRAFT,
	TRIGGER_REQUESTER_REPLY,
	TRIGGER_TICKET_INSERT,
)

PENDING_JOB_IDS_FLAG = "erp_ai_pending_job_ids"
VALID_TRIGGERS = (TRIGGER_TICKET_INSERT, TRIGGER_COMMENT_MENTION, TRIGGER_REQUESTER_REPLY, TRIGGER_KB_DRAFT)
VALID_CHANGE_ACTIONS = ("apply", "undo")
SCHEDULED_JOB_TIMEOUT_S = 1200
LIFECYCLE_JOB_TIMEOUT_S = 300
# What the one RQ read says of a job id (design 3.5): no job yet, waiting in the queue, or running. The last two
# are the values of RQ's JobStatus (a str enum), so the read compares equal to them without importing rq (ADR-001).
JOB_STATE_NEW = "new"
JOB_STATE_QUEUED = "queued"
JOB_STATE_STARTED = "started"


def _clear_pending_job_ids():
	frappe.flags.pop(PENDING_JOB_IDS_FLAG, None)


def requester_reply_key(ticket_name: str, communication_name: str) -> str:
	"""The event key of a requester-reply run (ADR-033 QĐ 2): one per ticket and requester message."""
	return f"{TRIGGER_REQUESTER_REPLY}:{ticket_name}:{communication_name}"


def _job_state(job_id: str) -> str:
	"""Whether the job `job_id` is new, queued or started, by the RQ read Frappe's dedupe makes (ADR-048 QĐ 2).

	The only read of the RQ job state in the app. Any other status, no job, or a failed read is `new`:
	`frappe.enqueue` then reads again and queues or fails as it always did (design 3.5).
	"""
	try:
		status = background_jobs.get_job_status(job_id)
	except Exception:
		# Dropped on purpose: the read only picks the event row; the call itself must go on to frappe.enqueue.
		return JOB_STATE_NEW
	if status == JOB_STATE_QUEUED:
		return JOB_STATE_QUEUED
	if status == JOB_STATE_STARTED:
		return JOB_STATE_STARTED
	return JOB_STATE_NEW


def _claim_pending(job_id: str) -> bool:
	"""False when `job_id` was already queued in this transaction; else remember it until commit or rollback."""
	pending = frappe.flags.get(PENDING_JOB_IDS_FLAG)
	if pending is None:
		pending = set()
		frappe.flags[PENDING_JOB_IDS_FLAG] = pending
		frappe.db.after_commit.add(_clear_pending_job_ids)
		frappe.db.after_rollback.add(_clear_pending_job_ids)
	if job_id in pending:
		return False
	pending.add(job_id)
	return True


def enqueue_agent_run(
	ticket_name: str, trigger: str, message_name: str | None = None, communication_name: str | None = None
) -> bool:
	"""Queue one agent run and leave its event row (ADR-048 QĐ 2, design 3.5); True only when the job is new.

	A new job gets a `run_id` (the event key for a requester reply, else a fresh uuid) and a `call_received`
	row carrying it. A job of the same id already queued or started gets no run of its own: a message
	(`comment_mention`) is told so by a `call_merged` or `call_busy` row, another trigger leaves none. The rows
	ride the caller's transaction (never committed here); `frappe.enqueue` is called on every branch (D-3).

	Raises:
		ValueError: an unknown trigger, or the message or Communication name the trigger needs is missing.
	"""
	if trigger not in VALID_TRIGGERS:
		raise ValueError(f"Unknown trigger: {trigger!r}")
	if trigger == TRIGGER_COMMENT_MENTION and not message_name:
		raise ValueError(f"message_name is required for trigger {trigger!r}")
	is_reply = trigger == TRIGGER_REQUESTER_REPLY
	if is_reply and not (isinstance(communication_name, str) and communication_name):
		raise ValueError(f"communication_name is required for trigger {trigger!r}")
	if not is_reply and communication_name is not None:
		raise ValueError(
			f"communication_name is only for trigger {TRIGGER_REQUESTER_REPLY!r}, not {trigger!r}"
		)

	job_id = f"erp_ai::{ticket_name}::{trigger}"
	reply_kwargs = {}
	if is_reply:
		# U6b-fixes Sửa 1 (X-1): one job per requester message, so a message arriving during a run is not
		# merged away; only this job carries the message name, the other jobs keep their arguments.
		job_id = f"{job_id}::{communication_name}"
		reply_kwargs = {"communication_name": communication_name}
	if not _claim_pending(job_id):
		return False

	state = _job_state(job_id)
	run_id = None
	if state == JOB_STATE_NEW:
		run_id = requester_reply_key(ticket_name, communication_name) if is_reply else uuid.uuid4().hex
		record_event(ticket=ticket_name, trigger=trigger, code=EVENT_CALL_RECEIVED, run_id=run_id)
	elif trigger == TRIGGER_COMMENT_MENTION:
		code = EVENT_CALL_MERGED if state == JOB_STATE_QUEUED else EVENT_CALL_BUSY
		record_event(ticket=ticket_name, trigger=trigger, code=code)

	frappe.enqueue(
		"erp_ai.agent.runner.run_for_ticket",
		queue="long",
		timeout=JOB_TIMEOUT_S,
		enqueue_after_commit=True,
		job_id=job_id,
		deduplicate=True,
		ticket_name=ticket_name,
		trigger=trigger,
		message_name=message_name,
		run_id=run_id,
		**reply_kwargs,
	)
	return state == JOB_STATE_NEW


def enqueue_lifecycle_job(ticket_name: str) -> bool:
	"""Queue the ticket lifecycle job (ADR-033 QĐ 6); the target is a string, this module never imports it."""
	if not isinstance(ticket_name, str) or not ticket_name:
		raise ValueError(f"Invalid ticket_name: {ticket_name!r}")

	job_id = f"erp_ai_lifecycle::{ticket_name}"
	if not _claim_pending(job_id):
		return False

	frappe.enqueue(
		"erp_ai.agent.lifecycle.run_task_lifecycle",
		queue="default",
		timeout=LIFECYCLE_JOB_TIMEOUT_S,
		enqueue_after_commit=True,
		job_id=job_id,
		deduplicate=True,
		ticket_name=ticket_name,
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


def enqueue_daily_report_job() -> None:
	frappe.enqueue(
		"erp_ai.agent.daily_report.run_daily_report",
		queue="long",
		timeout=SCHEDULED_JOB_TIMEOUT_S,
		enqueue_after_commit=True,
		job_id="erp_ai::daily_report",
		deduplicate=True,
	)


def enqueue_weekly_kpi_job() -> None:
	frappe.enqueue(
		"erp_ai.agent.kpi.run_weekly_kpi",
		queue="long",
		timeout=SCHEDULED_JOB_TIMEOUT_S,
		enqueue_after_commit=True,
		job_id="erp_ai::weekly_kpi",
		deduplicate=True,
	)


def enqueue_monthly_review_job() -> None:
	frappe.enqueue(
		"erp_ai.agent.monthly_review.run_monthly_review",
		queue="long",
		timeout=SCHEDULED_JOB_TIMEOUT_S,
		enqueue_after_commit=True,
		job_id="erp_ai::monthly_review",
		deduplicate=True,
	)
