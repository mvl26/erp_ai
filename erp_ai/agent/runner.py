import json
import time
import uuid

import frappe
from frappe.utils import get_fullname

from erp_ai import gateway
from erp_ai.agent import authority, policy
from erp_ai.agent.classification import load_mapping, parse_classification, resolve_ticket_values
from erp_ai.agent.prompts import build_classify_request, build_initial_message, build_reason_system
from erp_ai.agent.run_log import write_entry
from erp_ai.agent.tools.read import TOOL_RESULT_MAX_CHARS
from erp_ai.agent.tools.registry import ToolContext, execute_tool, get_tool_schemas
from erp_ai.constants import (
	AGENT_USER,
	JOB_SAFETY_MARGIN_S,
	JOB_TIMEOUT_S,
	LEVELS,
	LOG_DOCTYPE,
	SETTING_DOCTYPE,
	TITLE_RUN_FAILED,
	TITLE_WRONG_USER,
	TRIGGER_COMMENT_MENTION,
	TRIGGER_TICKET_INSERT,
)

CLASSIFY_MAX_TOKENS = 400
REASON_MAX_TOKENS = 4096
STOP_TOOL_USE = "tool_use"
STOP_MAX_TURNS = "max_turns"
STOP_TIME_BUDGET = "time_budget"
STOP_GATEWAY_ERROR = "gateway_error"
DEADLINE_KIND = "deadline"
# Write tools -> (doctype of the record they touch, key of the result that names it; None = the ticket).
WRITE_TOOL_TARGETS = {
	"set_classification": ("HD Ticket", None),
	"set_resolution_hint": ("HD Ticket", None),
	"post_comment": ("Comment", "comment"),
	"create_task": ("Task", "task"),
}
UNPARSEABLE_ERROR = "UNPARSEABLE: không phân loại được"
BAD_MAPPING_ERROR = "category_mapping không hợp lệ, không có giá trị dự đoán"
APPLY_SAVEPOINT = "erp_ai_apply"
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

	if trigger == TRIGGER_COMMENT_MENTION and level == LEVELS[0]:
		_log_skip(ticket_name, trigger, run_id, "level_L0")
		return
	mapping = load_mapping(settings.category_mapping)
	# One context for the whole run (classification and reasoning); never built at L0, which calls no tool.
	context = None
	if level != LEVELS[0]:
		context = ToolContext(
			ticket_name=ticket_name,
			effective_level=level,
			instructor=authority.latest_instructor(ticket_name),
			run_id=run_id,
			category_mapping=mapping,
			agent_user=AGENT_USER,
		)
	classification = None
	if trigger == TRIGGER_TICKET_INSERT:
		proceed, classification = _classify(ticket_name, trigger, run_id, mapping, context, deadline)
		if not proceed:
			return
	if level != LEVELS[0]:
		_reason(ticket_name, trigger, run_id, settings, context, classification, deadline)


def _log_skip(ticket_name, trigger, run_id, stop_reason):
	# a ticket deleted before the job ran cannot be a Link target; keep the skip entry without it
	exists = frappe.db.exists("HD Ticket", ticket_name)
	write_entry(
		ticket=ticket_name if exists else None,
		error=None if exists else f"ticket_missing {ticket_name}",
		run_id=run_id,
		entry_type="skip",
		trigger=trigger,
		turn=0,
		stop_reason=stop_reason,
	)


def _call_fields(result):
	return {
		"model": result.model,
		"cost_usd": result.cost_usd,
		"credential_label": result.credential_label,
		"keys_tried": result.keys_tried,
		"latency_ms": result.latency_ms,
		**{column: result.usage.get(column) or 0 for column in USAGE_COLUMNS},
	}


def _classify(ticket_name, trigger, run_id, mapping, context, deadline):
	"""Classification step (design 4.3 step 6). Writes one `classify` entry; with a context (L1+) also applies it.

	Returns `(proceed, classification)`: `proceed` is False when the run must end here (gateway error);
	`classification` is the summary handed to the reasoning step, or None when nothing was classified.
	"""
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
		return False, None

	call_fields = _call_fields(result)
	classification = parse_classification(result.text)
	if classification is None:
		write_entry(**base, **call_fields, error=UNPARSEABLE_ERROR, stop_reason="unparseable")
		return True, None

	values = resolve_ticket_values(classification, subject, mapping)
	# The entry is written first with applied=0 and committed before the ticket is touched (D-20).
	log_name = write_entry(
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
	if context is not None:
		_apply_classification(log_name, classification, context)
	summary = {"category": classification.category, "confidence": classification.confidence, **values}
	return True, summary


def _apply_classification(log_name, classification, context):
	"""Run `set_classification` and record its outcome on the entry as one unit.

	The ticket change and the entry update share a savepoint: an exception between them undoes the
	ticket change, so the entry never says applied=0 over a changed ticket (the entry row itself was
	committed before and survives). Nothing is committed until both are written.
	"""
	frappe.db.savepoint(APPLY_SAVEPOINT)
	try:
		result = execute_tool(
			"set_classification",
			{"category": classification.category, "confidence": classification.confidence},
			context,
		)
		if result.get("ok") and result.get("after"):
			action = {
				"tool": "set_classification",
				"doctype": "HD Ticket",
				"name": context.ticket_name,
				"ok": True,
			}
			frappe.db.set_value(
				LOG_DOCTYPE,
				log_name,
				{
					"applied": 1,
					"value_before": json.dumps(result["before"], ensure_ascii=False),
					"value_after": json.dumps(result["after"], ensure_ascii=False),
					"actions": json.dumps([action], ensure_ascii=False),
				},
				update_modified=False,
			)
	except Exception:
		frappe.db.rollback(save_point=APPLY_SAVEPOINT)
		raise
	frappe.db.release_savepoint(APPLY_SAVEPOINT)
	if not frappe.flags.in_test:
		frappe.db.commit()


def _reason(ticket_name, trigger, run_id, settings, context, classification, deadline):
	"""Reasoning step (design 4.3 step 8): at most `max_turns_per_run` model turns, one `reason` entry each."""
	comments = authority.fetch_ticket_comments(ticket_name)
	# the role is decided on the owner; only then is the author replaced by the full name shown to the model
	labelled = [
		{**comment, "author": get_fullname(comment["author"])}
		for comment in authority.label_comments(ticket_name, comments)
	]
	ticket = frappe.db.get_value(
		"HD Ticket",
		ticket_name,
		["subject", "description", "status", "priority", "ticket_type", "agent_group", "creation"],
		as_dict=True,
	)
	tools = get_tool_schemas(context.effective_level, bool(context.instructor))
	if tools:
		tools[-1]["cache_control"] = {"type": "ephemeral"}
	system = build_reason_system(settings.prompt_digest)
	messages = [{"role": "user", "content": build_initial_message(ticket, labelled, trigger, classification)}]
	base = {
		"ticket": ticket_name,
		"run_id": run_id,
		"entry_type": "reason",
		"trigger": trigger,
		"instructor": context.instructor,
	}
	max_turns = settings.max_turns_per_run
	for turn in range(1, max_turns + 1):
		try:
			result = _call_model(
				"reason",
				system=system,
				messages=messages,
				tools=tools,
				max_tokens=REASON_MAX_TOKENS,
				deadline=deadline,
			)
		except gateway.GatewayError as exc:
			write_entry(
				**base,
				turn=turn,
				error=f"{exc.kind} status={exc.status}",
				stop_reason=STOP_TIME_BUDGET if exc.kind == DEADLINE_KIND else STOP_GATEWAY_ERROR,
				credential_label=exc.credential_label,
				keys_tried=exc.keys_tried,
			)
			return

		tool_blocks = [block for block in result.content if block.get("type") == "tool_use"]
		tool_results, actions, before, after, tool_errors = [], [], {}, {}, []
		for block in tool_blocks:
			tool_results.append(_run_tool(block, context, actions, before, after, tool_errors))
		stop_reason = result.stop_reason
		wants_tools = stop_reason == STOP_TOOL_USE
		if wants_tools and turn == max_turns:
			stop_reason = STOP_MAX_TURNS
		write_entry(
			**base,
			**_call_fields(result),
			turn=turn,
			stop_reason=stop_reason,
			tools_called=[block["name"] for block in tool_blocks] or None,
			error="; ".join(tool_errors) or None,
			actions=actions or None,
			value_before=before or None,
			value_after=after or None,
		)
		if not wants_tools or not tool_results:
			return
		messages.append({"role": "assistant", "content": result.content})
		messages.append({"role": "user", "content": tool_results})


def _run_tool(block, context, actions, before, after, tool_errors):
	"""Execute one `tool_use` block; record write outcomes and crashes in the turn's accumulators; return its `tool_result`.

	A crash is logged as tool name + exception class only (D-20, STD-SEC-6); the model sees the class too.
	"""
	name = block["name"]
	try:
		outcome = execute_tool(name, block.get("input") or {}, context)
	except Exception as exc:
		tool_errors.append(f"tool {name}: {type(exc).__name__}")
		if name in WRITE_TOOL_TARGETS:
			actions.append(_action(name, context, None, False))
		return {
			"type": "tool_result",
			"tool_use_id": block["id"],
			"content": f"Lỗi: {type(exc).__name__}",
			"is_error": True,
		}
	if name in WRITE_TOOL_TARGETS:
		actions.append(_action(name, context, outcome, bool(outcome.get("ok"))))
		if outcome.get("ok") and "after" in outcome:
			before[name] = outcome.get("before")
			after[name] = outcome["after"]
	content = json.dumps(outcome, ensure_ascii=False, default=str)[:TOOL_RESULT_MAX_CHARS]
	return {"type": "tool_result", "tool_use_id": block["id"], "content": content}


def _action(name, context, outcome, ok):
	doctype, key = WRITE_TOOL_TARGETS[name]
	record = context.ticket_name if key is None else (outcome or {}).get(key)
	return {"tool": name, "doctype": doctype, "name": record, "ok": ok}
