import time
import uuid

import frappe

from erp_ai import gateway
from erp_ai.agent import policy
from erp_ai.agent.classification import load_mapping, parse_classification, resolve_ticket_values
from erp_ai.agent.prompts import build_classify_request
from erp_ai.agent.run_log import write_entry
from erp_ai.constants import (
	AGENT_USER,
	JOB_SAFETY_MARGIN_S,
	JOB_TIMEOUT_S,
	LEVELS,
	SETTING_DOCTYPE,
	TITLE_RUN_FAILED,
	TITLE_WRONG_USER,
	TRIGGER_COMMENT_MENTION,
	TRIGGER_TICKET_INSERT,
)

CLASSIFY_MAX_TOKENS = 400
UNPARSEABLE_ERROR = "UNPARSEABLE: không phân loại được"
BAD_MAPPING_ERROR = "category_mapping không hợp lệ, không có giá trị dự đoán"
USAGE_COLUMNS = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


def run_for_ticket(ticket_name: str, trigger: str) -> None:
	"""Agent job (design 4.3). Never raises: a failed run is logged and the job ends normally.

	No rollback on the error path: the gateway writes key breaker state without committing, and a
	rollback would lose the key status and the alarm that state drives (committed by `_call_model`).
	"""
	try:
		_run(ticket_name, trigger)
	except Exception as exc:
		frappe.log_error(
			TITLE_RUN_FAILED, f"ticket={ticket_name} trigger={trigger} error={type(exc).__name__}"
		)


def _call_model(task, **kwargs):
	"""Call the gateway, then commit its key state whether it returned or raised (D-20)."""
	try:
		return gateway.call_model(task, **kwargs)
	finally:
		if not frappe.flags.in_test:
			frappe.db.commit()


def _run(ticket_name, trigger):
	# (a) the job must run as the agent account, checked before the ticket is read (AC-6)
	if not frappe.db.get_value("User", AGENT_USER, "enabled"):
		frappe.log_error(TITLE_WRONG_USER, "Không có tài khoản agent")
		return
	frappe.set_user(AGENT_USER)
	if frappe.session.user != AGENT_USER:
		frappe.log_error(TITLE_WRONG_USER, f"Sai tài khoản: {frappe.session.user}")
		return

	# (b) disabled at run time: stop without a log entry
	settings = frappe.get_single(SETTING_DOCTYPE)
	if not settings.enabled:
		return

	run_id = uuid.uuid4().hex
	# (c) the single send condition, re-checked at run time (NFR-4)
	if not policy.can_send_ticket(ticket_name):
		_log_skip(ticket_name, trigger, run_id, "not_sendable")
		return
	# (d) daily limit counted from the log (AC-15)
	if policy.runs_today(ticket_name) >= settings.max_runs_per_ticket_per_day:
		_log_skip(ticket_name, trigger, run_id, "daily_limit")
		return
	# (e)
	level = policy.effective_level(settings)
	deadline = time.monotonic() + JOB_TIMEOUT_S - JOB_SAFETY_MARGIN_S

	if trigger == TRIGGER_TICKET_INSERT:
		_classify(ticket_name, trigger, run_id, settings, deadline)
	elif trigger == TRIGGER_COMMENT_MENTION and level == LEVELS[0]:
		_log_skip(ticket_name, trigger, run_id, "level_L0")


def _log_skip(ticket_name, trigger, run_id, stop_reason):
	# a ticket deleted before the job ran cannot be a Link target; keep the skip entry without it
	write_entry(
		ticket=ticket_name if frappe.db.exists("HD Ticket", ticket_name) else None,
		run_id=run_id,
		entry_type="skip",
		trigger=trigger,
		turn=0,
		stop_reason=stop_reason,
	)


def _classify(ticket_name, trigger, run_id, settings, deadline):
	"""Classification step (design 4.3 step 6). Writes one `classify` entry; the ticket is not changed."""
	subject, description = frappe.db.get_value("HD Ticket", ticket_name, ["subject", "description"])
	base = {"ticket": ticket_name, "run_id": run_id, "entry_type": "classify", "trigger": trigger, "turn": 0}
	try:
		result = _call_model(
			"classify",
			**build_classify_request(subject, description),
			max_tokens=CLASSIFY_MAX_TOKENS,
			deadline=deadline,
		)
	except gateway.GatewayError as exc:
		write_entry(
			**base,
			error=f"{exc.kind} status={exc.status}",
			stop_reason="gateway_error",
			credential_label=exc.credential_label,
			keys_tried=exc.keys_tried,
		)
		return

	call_fields = {
		"model": result.model,
		"cost_usd": result.cost_usd,
		"credential_label": result.credential_label,
		"keys_tried": result.keys_tried,
		"latency_ms": result.latency_ms,
		**{column: result.usage.get(column) or 0 for column in USAGE_COLUMNS},
	}
	classification = parse_classification(result.text)
	if classification is None:
		write_entry(**base, **call_fields, error=UNPARSEABLE_ERROR, stop_reason="unparseable")
		return

	mapping = load_mapping(settings.category_mapping)
	values = resolve_ticket_values(classification, subject, mapping)
	write_entry(
		**base,
		**call_fields,
		stop_reason=result.stop_reason,
		error=None if mapping else BAD_MAPPING_ERROR,
		predicted_category=classification.category,
		predicted_confidence=classification.confidence,
		predicted_ticket_type=values["ticket_type"],
		predicted_agent_group=values["agent_group"],
		predicted_priority=values["priority"],
		applied=0,
	)
