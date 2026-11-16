import dataclasses
import json
import time
import uuid
from datetime import datetime

import frappe
from frappe.desk.form.document_follow import follow_document
from frappe.utils import escape_html, get_fullname, getdate, now_datetime

from erp_ai import gateway
from erp_ai.agent import authority, policy, site_facts
from erp_ai.agent.answer_delay import AnswerDelay
from erp_ai.agent.authority import TITLE_WRONG_USER as TITLE_WRONG_USER  # re-export, U1.md:264
from erp_ai.agent.classification import load_mapping, parse_classification, split_request_comment
from erp_ai.agent.prompts import (
	TICKET_FIELD_LABELS,
	build_classify_request,
	build_initial_message,
	build_reason_system,
	build_routing_table,
)
from erp_ai.agent.routing import decide_route, departments, load_routing_config, sla_lag
from erp_ai.agent.run_log import ENTRY_TYPE_CHANGE, action_entry, write_entry
from erp_ai.agent.run_status import CLASSIFY_STEP, RunStatus
from erp_ai.agent.tools.read import TOOL_RESULT_MAX_CHARS
from erp_ai.agent.tools.registry import ToolContext, execute_tool, grant
from erp_ai.agent.tools.route_ticket import (
	ASSIGN_REQUEST,
	NO_SLA,
	REASON_ASSIGN_FAILED,
	REASON_NO_VALID_ASSIGNEE,
	REASON_TASK_FAILED,
	REASON_TASK_NOT_ASSIGNED,
	TASK_REQUEST,
	TaskSharingDisabled,
	apply_route,
	assign_owner,
	create_routed_task,
	post_routing_comment,
)
from erp_ai.agent.tools.write_ticket import (
	ASK_FOOTER,
	CREATED_LABELS_FIELD,
	FIELD_LABELS,
	GUIDANCE_SECTIONS,
	HINT_FIELD,
	REASON_GUIDANCE_EXISTS,
	REASON_NO_CONTENT,
	ROUTE_DONE,
	SECTION_DECIDE,
	SECTION_DONE,
	asked_in_run,
	close_collector,
	collect,
	collected,
	collecting,
	count_guidance,
	created_labels,
	keep_human_fields,
	locked_rows,
	mark_asked,
	mark_work_only,
	open_collector,
	post_guidance,
	post_notice,
)
from erp_ai.constants import (
	AGENT_USER,
	CLASSIFICATION_FIELDS,
	CLASSIFIED_BY_HUMAN,
	JOB_SAFETY_MARGIN_S,
	JOB_TIMEOUT_S,
	LEVELS,
	LOG_DOCTYPE,
	LOGGER_NAME,
	PROPOSAL_DOCTYPE,
	SETTING_DOCTYPE,
	TITLE_RUN_FAILED,
	TITLE_STATUS_FAILED,
	TRIGGER_CHANGE_ACTION,
	TRIGGER_COMMENT_MENTION,
	TRIGGER_TICKET_INSERT,
)

CLASSIFY_MAX_TOKENS = 600
REASON_MAX_TOKENS = 4096
STOP_TOOL_USE = "tool_use"
STOP_MAX_TURNS = "max_turns"
STOP_TIME_BUDGET = "time_budget"
STOP_GATEWAY_ERROR = "gateway_error"
DEADLINE_KIND = "deadline"
# The tool whose call is the answer the delay holds back (D-6).
ANSWER_TOOL = "post_comment"
# Write tools -> (doctype of the record they touch, key of the result that names it; None = the ticket).
# A doctype of None means the model names it: it is read from the result, else from the call's arguments.
WRITE_TOOL_TARGETS = {
	"set_classification": ("HD Ticket", None),
	"set_resolution_hint": ("HD Ticket", None),
	"post_comment": ("Comment", "comment"),
	"create_task": ("Task", "task"),
	"propose_file_change": (PROPOSAL_DOCTYPE, "proposal"),
	"propose_new_file": (PROPOSAL_DOCTYPE, "proposal"),
	"propose_bench_command": (PROPOSAL_DOCTYPE, "proposal"),
	"api_create_record": (None, "name"),
	"api_update_record": (None, "name"),
	"api_delete_record": (None, "name"),
	"api_submit_record": (None, "name"),
	"api_call_method": ("Method", "method"),
}
# Generic write tools: the model names the DocType; each successful call keeps its full snapshot (AC-13).
GENERIC_WRITE_TOOLS = tuple(name for name, (doctype, _) in WRITE_TOOL_TARGETS.items() if doctype is None)
# `ERP AI Log.actions` is a Small Text column: MariaDB `text`, 65535 bytes. The JSON the runner stores there
# stays within ACTIONS_MAX_BYTES (utf-8); each string in it within ACTION_VALUE_MAX_BYTES. A cut is marked.
ACTIONS_MAX_BYTES = 60000
ACTION_VALUE_MAX_BYTES = 1024
ACTION_CUT_MARKER = "[đã cắt]"
ACTION_VALUE_KEYS = ("value_before", "value_after")
# Tools that create a record without returning before/after: their entry carries the call arguments as `value_after`.
# Key of the proposal status in a propose tool's entry values (the DocType field; this module never writes it).
PROPOSAL_STATUS_KEY = "change_status"
CREATING_TOOLS = ("post_comment", "create_task")
PROPOSE_TOOLS = ("propose_file_change", "propose_new_file", "propose_bench_command")
PROPOSE_STEP = "propose"
UNPARSEABLE_ERROR = "UNPARSEABLE: không phân loại được"
BAD_MAPPING_ERROR = "category_mapping không hợp lệ, không có giá trị dự đoán"
BAD_ROUTING_ERROR = "routing_rules không hợp lệ, định tuyến dùng giá trị rỗng"
NO_SCORE_REASON = "không có điểm"
NO_SLA_REASON = "chưa có SLA áp vào phiếu"
REASON_TASK_EXISTS = "phiếu đã có Task liên kết"
# The route comment's own sentences (U4b.md:210-214); ROUTE_DONE and FIELD_LABELS come from write_ticket (U4b-8).
ROUTE_NO_CHANGE = "Bot đã phân loại phiếu, các trường đã đúng nên không đổi."
ROUTE_ASSIGNED = "Đã gán cho {person}."
ROUTE_TASK = "Đã tạo Task {task}."
ROUTE_WATCHER = "Đã thêm {person} làm người theo dõi."
# (u5) the D watcher (AC-27, U4b-fixes Fix 6)
WATCHER_TOOL = "add_watcher"
REASON_ALREADY_FOLLOWING = "đã theo dõi"
REASON_FOLLOW_OFF = "người theo dõi tắt nhận theo dõi tài liệu"
# Status notices of the run (AC-23, U4b.md:216-222): one comment per kind and period, through write_ticket.post_notice.
NOTICE_TOOL = "post_notice"
DAILY_LIMIT_BODY = (
	"đã dùng hết {limit} lần chạy trong ngày. Bot xử lý tiếp từ ngày mai; cần gấp thì nhờ người phụ trách."
)
OVER_BUDGET_BODY = (
	"chi phí AI tháng này đã vượt ngân sách, bot chỉ đọc, phân loại và đề xuất, không làm thay đổi gì ngoài phiếu. "
	"Quản trị tăng ngân sách trên ERP AI Setting để mở lại."
)
RUN_FAILED_BODY = "{cause}. Bot sẽ thử lại ở lần quét kế tiếp; cần gấp thì nhờ người phụ trách."
CAUSE_GATEWAY = "lỗi khi gọi mô hình AI"
CAUSE_TIME = "hết thời gian của lần chạy"
# A run below the threshold whose model asked nothing ends with this question (AC-22, U4b.md:220, :252).
ASK_FALLBACK_BODY = (
	"anh/chị bổ sung giúp mô tả cụ thể hơn (màn hình, mã chứng từ, bước làm).\n"
	"**Căn cứ:** nội dung phiếu chưa đủ để chọn đầu mục và nhóm."
)
ASK_PCT_UNKNOWN = "chưa có"
# The triggers each notice may be posted for (U4b-fixes Fix 8, A-U4b-13): an allow list, fail-closed for a new
# trigger. "daily_limit" is not in it: it holds for every trigger that reaches step (d).
NOTICE_TRIGGERS = {
	"over_budget": (TRIGGER_TICKET_INSERT, TRIGGER_COMMENT_MENTION, TRIGGER_CHANGE_ACTION),
	"run_failed": (TRIGGER_TICKET_INSERT, TRIGGER_COMMENT_MENTION, TRIGGER_CHANGE_ACTION),
	"ask_fallback": (TRIGGER_TICKET_INSERT, TRIGGER_COMMENT_MENTION, TRIGGER_CHANGE_ACTION),
}
# ADR-037 QĐ 4: a ticket is routed at most once; a later route call writes only this refusal on its classify row.
ROUTE_ALREADY_DONE = "đã định tuyến"
ROUTE_SAVEPOINT = "erp_ai_route"
# One write unit after (u1) (assign, comment) nests inside the savepoint above.
ROUTE_UNIT_SAVEPOINT = "erp_ai_route_unit"
# Set right after each reason turn's model call: a failing turn is undone to here (ADR-024 QĐ 2).
REASON_TURN_SAVEPOINT = "erp_ai_reason_turn"
USAGE_COLUMNS = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
# The settings naming an HD Ticket field (U4b.md:209, AC-24): "field_<key>" for each key of the prompt labels.
TICKET_FIELD_SETTINGS = tuple(f"field_{key}" for key in TICKET_FIELD_LABELS)
# A run on a ticket that already has its guidance comment says so once in the log (AC-65 (c), w1.md:68).
GUIDANCE_EXISTS_LOG = "erp_ai guidance ticket=%s run_id=%s: đã có hướng xử lý"
# The action entry of the run's one guidance comment (ADR-036 QĐ 8, w1.md:105).
GUIDANCE_TOOL = "post_guidance"


def run_for_ticket(ticket_name: str, trigger: str, comment_name: str | None = None) -> None:
	"""Agent job (design 4.3). Never raises: a failed run is logged and the job ends normally.

	No rollback on the error path: the gateway writes key breaker state without committing, and a
	rollback would lose the key status and the alarm that state drives (committed by `_call_model`).
	"""
	try:
		_run(ticket_name, trigger, comment_name)
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


def _run(ticket_name, trigger, comment_name=None):
	# (a) the job must run as the agent account, checked before the ticket is read (AC-6)
	if not authority.enter_agent_session():
		return

	# (b) disabled at run time: stop without a log entry
	settings = frappe.get_single(SETTING_DOCTYPE)
	if not settings.enabled:
		return
	routing = load_routing_config(settings.routing_rules)

	run_id = uuid.uuid4().hex
	# the ask_fallback dedup counts from here: one question per run, not per ticket (AC-22, ADR-037)
	started_at = now_datetime()
	field_map, missing = _ticket_fields(settings)
	if missing:
		# one line per run, configuration names only (AC-24)
		frappe.logger(LOGGER_NAME).info(
			"erp_ai ticket_fields run_id=%s missing=%s", run_id, "; ".join(missing)
		)
	# (c) the single send condition, re-checked at run time (NFR-4)
	if not policy.can_send_ticket(ticket_name):
		_log_skip(ticket_name, trigger, run_id, "not_sendable")
		return
	# (d) daily limit counted from the log (AC-15); above L0 the person is told once a day (AC-23, AC-61)
	limit = settings.max_runs_per_ticket_per_day
	if policy.runs_today(ticket_name) >= limit:
		notice = None
		if policy.effective_level(settings, over_budget=False) != LEVELS[0]:
			notice = ("daily_limit", DAILY_LIMIT_BODY.format(limit=limit), _start_of_today())
		_log_skip(ticket_name, trigger, run_id, "daily_limit", notice)
		return
	# (e)
	over_budget = policy.is_over_budget(settings)
	level = policy.effective_level(settings, over_budget=over_budget)
	switches = policy.permission_switches(settings)
	threshold = policy.confidence_threshold(settings)
	auto_assign = policy.auto_assign_enabled(settings)
	deadline = time.monotonic() + JOB_TIMEOUT_S - JOB_SAFETY_MARGIN_S

	if trigger == TRIGGER_COMMENT_MENTION and level == LEVELS[0]:
		_log_skip(ticket_name, trigger, run_id, "level_L0")
		return
	status = RunStatus(ticket_name, run_id, settings.get("thinking_text"))
	delay = None
	try:
		status.start()
		# anchor of the delay = right after the start signal (AC-3); ticket_insert never waits
		if trigger == TRIGGER_COMMENT_MENTION:
			delay = AnswerDelay.start(settings.answer_delay_min_s, settings.answer_delay_max_s)
		mapping = load_mapping(settings.category_mapping)
		# One context for the whole run (classification and reasoning); never built at L0, which calls no tool.
		context = None
		classification = None
		posted = False
		if level != LEVELS[0]:
			instructor = authority.run_instructor(ticket_name, trigger, comment_name)
			# An insert run has no classification yet: `_classify` recomputes both from its own (U1.md:261).
			category, pct = (None, None)
			if trigger != TRIGGER_TICKET_INSERT:
				category, pct = policy.latest_classification(ticket_name)
				if category is not None:
					# the reasoning step knows the earlier classification, the same pair (U4b.md:238, Fix 12)
					classification = {"category": category, "confidence_pct": pct}
			context = ToolContext(
				ticket_name=ticket_name,
				effective_level=level,
				instructor=instructor,
				run_id=run_id,
				category_mapping=mapping,
				agent_user=AGENT_USER,
				routing_config=routing,
				change_enabled=switches.code_change,
				allowed_apps=policy.change_settings(settings).allowed_apps,
				unrestricted=switches.unrestricted,
				record_tools=switches.record_tools,
				act_now=switches.act_now,
				one_click_approval=switches.one_click_approval,
				over_budget=over_budget,
				main_path_level=policy.main_path_level(settings, level, category),
				below_threshold=_below_threshold(pct, threshold, instructor, switches.act_now),
			)
			# ADR-036 QĐ 7: the one count, read once; the mode is chosen once the classification is known
			posted = count_guidance(ticket_name) > 0
		if trigger == TRIGGER_TICKET_INSERT:
			proceed, classification, context = _classify(
				ticket_name,
				trigger,
				run_id,
				mapping,
				routing,
				context,
				auto_assign,
				deadline,
				status,
				settings,
				threshold,
				field_map,
				posted,
			)
			if not proceed:
				return
		elif context is not None:
			_choose_mode(context, posted)
		if level != LEVELS[0]:
			notices = []
			# over budget at a base level of L2/L3 the run lost something: said once a day (A-U4b-7)
			if over_budget and policy.effective_level(settings, over_budget=False) in LEVELS[2:]:
				entry = _notice(
					ticket_name,
					"over_budget",
					OVER_BUDGET_BODY,
					_start_of_today(),
					trigger=trigger,
					instructor=context.instructor,
				)
				notices = [entry] if entry else []
				# post_notice's dedup read locked the ticket row: free it before the model call (D-20)
				if not frappe.flags.in_test:
					frappe.db.commit()
			_reason(
				ticket_name,
				trigger,
				run_id,
				settings,
				context,
				classification,
				deadline,
				status,
				delay,
				started_at=started_at,
				field_map=field_map,
				notices=notices,
				guidance_posted=posted,
			)
	finally:
		close_collector(run_id)
		_end_status(status, delay, ticket_name, run_id, trigger)


def _choose_mode(context, posted: bool) -> None:
	"""The run's mode (ADR-036 QĐ 7, w1.md:68): a ticket that has its guidance gets a work-only run and one log
	line; otherwise a run at a main path level above L0 that is not below the threshold opens the collector of the
	run's one guidance comment. Below the threshold nothing opens: the run only asks (AC-65 (b))."""
	if posted:
		mark_work_only(context.run_id)
		frappe.logger(LOGGER_NAME).info(GUIDANCE_EXISTS_LOG, context.ticket_name, context.run_id)
	elif context.main_path_level != LEVELS[0] and not context.below_threshold:
		open_collector(context.run_id)


def _ticket_fields(settings) -> tuple[dict[str, str], list[str]]:
	"""The configured ticket fields still on HD Ticket as {key: fieldname}, and why each other one is left out (AC-24).

	A setting saved once and then the field removed from the ticket is left out like an empty one: the run goes on.
	"""
	meta = frappe.get_meta("HD Ticket")
	field_map, missing = {}, []
	for (key, label), setting in zip(TICKET_FIELD_LABELS.items(), TICKET_FIELD_SETTINGS, strict=True):
		fieldname = (settings.get(setting) or "").strip()
		if not fieldname:
			missing.append(f"chưa cấu hình trường {label}")
		elif not meta.has_field(fieldname):
			missing.append(f"trường {fieldname} không có trên phiếu")
		else:
			field_map[key] = fieldname
	return field_map, missing


def _ticket_field_values(ticket_name: str, field_map: dict[str, str]) -> dict[str, object]:
	"""{key: value} of the configured ticket fields that hold a value, in one read of the ticket (U4b.md:235)."""
	if not field_map:
		return {}
	row = frappe.db.get_value("HD Ticket", ticket_name, list(field_map.values()), as_dict=True) or {}
	return {
		key: row.get(fieldname)
		for key, fieldname in field_map.items()
		if row.get(fieldname) not in (None, "")
	}


def _below_threshold(pct, threshold, instructor, act_now):
	"""The run's one below-threshold predicate (ADR-030 QD 4), for both kinds of run."""
	return policy.is_below_confidence(pct, threshold, has_instructor=bool(instructor), act_now=act_now)


def _end_status(status, delay, ticket_name, run_id, trigger):
	"""Close the run's status (design 4.5): `done`, leftover emit failures to the Error Log, one summary line.

	Codes and numbers only, never the status text (NFR-4'). No commit, no rollback: a signal never
	changes data, and `done` is out of the transaction so a rollback cannot take it back (R-2).
	"""
	status.done()
	errors = status.take_errors()
	# Runs in a `finally`: a failing log call must never replace the run's own exception (or the normal
	# return). There is no better place left to report a failure of the log itself, so it is dropped.
	for piece in errors:
		try:
			frappe.log_error(TITLE_STATUS_FAILED, f"ticket={ticket_name} run_id={run_id} {piece}")
		except Exception:
			pass
	try:
		frappe.logger(LOGGER_NAME).info(
			"erp_ai run_status ticket=%s run_id=%s trigger=%s signals=%d errors=%d delay_s=%.1f waited_s=%.1f",
			ticket_name,
			run_id,
			trigger,
			status.signal_count,
			len(errors),
			delay.delay_s if delay else 0,
			delay.waited_s if delay else 0,
		)
	except Exception:
		pass


def _log_skip(ticket_name, trigger, run_id, stop_reason, notice=None):
	"""One `skip` entry; `notice` = (kind, body, since) posts that status notice first, its entry on the row."""
	# a ticket deleted before the job ran cannot be a Link target; keep the skip entry without it
	exists = frappe.db.exists("HD Ticket", ticket_name)
	entry = _notice(ticket_name, *notice, trigger=trigger) if notice and exists else None
	write_entry(
		ticket=ticket_name if exists else None,
		error=None if exists else f"ticket_missing {ticket_name}",
		run_id=run_id,
		entry_type="skip",
		trigger=trigger,
		turn=0,
		stop_reason=stop_reason,
		actions=[entry] if entry else None,
	)


def _start_of_today() -> datetime:
	"""00:00 of today, system time: the same mark as `policy.runs_today`."""
	return datetime.combine(getdate(), datetime.min.time())


def _notice(ticket_name, notice, body, since, *, trigger, instructor=None) -> dict | None:
	"""Post one status notice of the run (U4b-fixes Fix 8); returns its action entry, or None when nothing was written.

	A kind of NOTICE_TRIGGERS is posted only for its listed triggers. One of the kind already posted on the ticket
	since `since` (or any refusal of post_notice) writes nothing, so it has no entry.
	"""
	if notice in NOTICE_TRIGGERS and trigger not in NOTICE_TRIGGERS[notice]:
		return None
	result = post_notice(ticket_name, notice, body, since)
	if not result.get("ok"):
		return None
	return action_entry(
		NOTICE_TOOL, "Comment", result["comment"], True, value_after={"notice": notice}, instructor=instructor
	)


def _last_success_at(ticket_name) -> datetime | None:
	"""When the ticket last had a successful step: a classify row with a category, or a reason row that did not stop
	on the gateway or the time budget (U4b.md:241). The mark of the run_failed notice (A-U4b-5)."""
	classified = frappe.get_all(
		LOG_DOCTYPE,
		filters={"ticket": ticket_name, "entry_type": "classify", "predicted_category": ("is", "set")},
		pluck="creation",
		order_by="creation desc",
		limit=1,
	)
	reasoned = frappe.get_all(
		LOG_DOCTYPE,
		filters={
			"ticket": ticket_name,
			"entry_type": "reason",
			"stop_reason": ("not in", (STOP_GATEWAY_ERROR, STOP_TIME_BUDGET)),
		},
		pluck="creation",
		order_by="creation desc",
		limit=1,
	)
	return max([*classified, *reasoned], default=None)


def _failure_notice(ticket_name, exc, trigger, instructor) -> dict | None:
	"""The run_failed notice of a gateway error, once per chain of failures since the last success (AC-23)."""
	cause = CAUSE_TIME if exc.kind == DEADLINE_KIND else CAUSE_GATEWAY
	return _notice(
		ticket_name,
		"run_failed",
		RUN_FAILED_BODY.format(cause=cause),
		_last_success_at(ticket_name) or datetime.min,
		trigger=trigger,
		instructor=instructor,
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


def _classify(
	ticket_name,
	trigger,
	run_id,
	mapping,
	routing,
	context,
	auto_assign,
	deadline,
	status,
	settings,
	threshold,
	field_map,
	posted=False,
):
	"""Classification step (design 4.3 step 6). Writes one `classify` entry; with a context (L1+) recomputes its
	main-path level and below-threshold flag from the classification, chooses the run's mode from them and `posted`
	(the run's one guidance count, ADR-036 QĐ 7, ADR-037 QĐ 3), then routes only at the threshold or above.

	The request carries the configured ticket fields (AC-24). The route leaves out the fields the person typed at
	creation, while the entry keeps the model's prediction and names the typed set (AC-19, AC-21, A-U4b-2).

	Returns `(proceed, classification, context)`: `proceed` is False when the run must end here (gateway error);
	`classification` is the summary handed to the reasoning step, or None when nothing was classified;
	`context` is the one the reasoning step uses (recomputed when a classification was parsed).
	"""
	ticket = frappe.db.get_value(
		"HD Ticket",
		ticket_name,
		[
			"subject",
			"description",
			"creation",
			"ai_classified_by",
			CREATED_LABELS_FIELD,
			*CLASSIFICATION_FIELDS,
		],
		as_dict=True,
	)
	subject = ticket.subject
	field_values = _ticket_field_values(ticket_name, field_map)
	base = {"ticket": ticket_name, "run_id": run_id, "entry_type": "classify", "trigger": trigger, "turn": 0}
	status.working(CLASSIFY_STEP)
	try:
		result = _call_model(
			"classify",
			**build_classify_request(
				subject, ticket.description, departments(routing), ticket_fields=field_values
			),
			max_tokens=CLASSIFY_MAX_TOKENS,
			deadline=deadline,
		)
	except gateway.GatewayError as exc:
		# above L0 the person is told, its entry on this failed row; at L0 the bot says nothing (AC-23)
		failed = None
		if context is not None:
			failed = _failure_notice(ticket_name, exc, trigger, context.instructor)
		write_entry(
			**base,
			error="; ".join([f"{exc.kind} status={exc.status}", *status.take_errors()]),
			stop_reason="gateway_error",
			credential_label=exc.credential_label,
			keys_tried=exc.keys_tried,
			actions=[failed] if failed else None,
		)
		_log_classify(ticket_name, run_id, False, ticket.creation)
		return False, None, context

	call_fields = _call_fields(result)
	classification = parse_classification(result.text)
	if classification is None:
		error = "; ".join([UNPARSEABLE_ERROR, *status.take_errors()])
		write_entry(**base, **call_fields, error=error, stop_reason="unparseable")
		_log_classify(ticket_name, run_id, False, ticket.creation)
		return True, None, context

	decision = decide_route(
		classification,
		subject,
		mapping,
		routing,
		team_exists=site_facts.team_exists,
		is_excluded_team=policy.is_excluded_team,
		is_active_agent=site_facts.is_active_agent,
		due_at=field_values.get("due_date"),
		due_field_configured="due_date" in field_map,
		d_watcher=settings.get("d_ticket_watcher") or "",
		now=now_datetime(),
	)
	labels = created_labels(ticket.get(CREATED_LABELS_FIELD))
	# a broken record reads as all three typed (fail-closed): no value of it is a typed one
	typed = {field: value for field, value in labels.items() if value is not True}
	if len(typed) < len(labels):
		frappe.logger(LOGGER_NAME).warning("erp_ai created_labels invalid ticket=%s", ticket_name)
	route_decision = keep_human_fields(decision, labels)
	# `predicted_*` stay the model's own prediction (AC-19); the route gets the decision without the typed fields
	values = {
		"ticket_type": decision.ticket_type,
		"agent_group": decision.agent_group,
		"priority": decision.priority,
	}
	# AC-28: the split question is asked once per ticket; a classify row records it only once the route comment
	# carrying it was posted (`_record_route`), so a run that posts none leaves it to a later run
	split_text = split_request_comment(classification)
	if split_text and frappe.db.exists(
		LOG_DOCTYPE, {"ticket": ticket_name, "entry_type": "classify", "split_requested": 1}
	):
		split_text = None
	# A-U4b-4: the ticket is Người before this row; the fields it holds are the person's label of the prediction
	corrected = (
		json.dumps({field: ticket.get(field) for field in CLASSIFICATION_FIELDS}, ensure_ascii=False)
		if ticket.ai_classified_by == CLASSIFIED_BY_HUMAN
		else None
	)
	# The entry is written first with applied=0 and committed before the ticket is touched (D-20).
	log_name = write_entry(
		**base,
		**call_fields,
		stop_reason=result.stop_reason,
		error="; ".join(
			[
				*([] if mapping else [BAD_MAPPING_ERROR]),
				*([] if routing else [BAD_ROUTING_ERROR]),
				*status.take_errors(),
			]
		)
		or None,
		predicted_category=classification.category,
		predicted_confidence=classification.confidence,
		predicted_confidence_pct=classification.confidence_pct,
		predicted_ticket_type=values["ticket_type"],
		predicted_agent_group=values["agent_group"],
		predicted_priority=values["priority"],
		predicted_complexity=classification.complexity,
		predicted_importance=classification.importance,
		predicted_score_reason=classification.score_reason or NO_SCORE_REASON,
		predicted_assignee=decision.assignee,
		created_labels=json.dumps(typed, ensure_ascii=False, sort_keys=True) if typed else None,
		human_corrected_to=corrected,
		applied=0,
	)
	_log_classify(ticket_name, run_id, True, ticket.creation)
	if context is not None:
		context = dataclasses.replace(
			context,
			main_path_level=policy.main_path_level(
				settings, context.effective_level, classification.category
			),
			below_threshold=_below_threshold(
				classification.confidence_pct, threshold, context.instructor, context.act_now
			),
		)
		# R5-2: after the below-threshold gate, before the route lock
		_choose_mode(context, posted)
		if not context.below_threshold:
			status.working("set_classification")
			_route(
				log_name,
				classification,
				route_decision,
				context,
				auto_assign,
				subject,
				split_text,
				collect_run_id=run_id,
			)
	summary = {"category": classification.category, "confidence": classification.confidence, **values}
	return True, summary, context


def _log_classify(ticket_name, run_id, ok, created) -> None:
	"""AC-17: one line per classification, codes and numbers only: the seconds from the ticket's creation."""
	frappe.logger(LOGGER_NAME).info(
		"erp_ai classify ticket=%s run_id=%s ok=%d latency_s=%d",
		ticket_name,
		run_id,
		1 if ok else 0,
		int((now_datetime() - created).total_seconds()),
	)


def _route(
	log_name, classification, decision, context, auto_assign, subject, split_text=None, collect_run_id=None
):
	"""Run the route unit (u1), check the SLA and record the outcome on the entry as one unit (design 4.2).

	Deterministic code, no model call (ADR-033 QĐ 3). After (u1) succeeds: SLA check, (u2) assign, (u3) Task,
	(u5) the D watcher, each write one unit with one action entry; then exactly one comment says what was
	classified, given, created and followed, the gathered sentences and the split question after it (AC-23, AC-28).
	Returns `lines`, the sentences of that one comment (already posted by (u4)).
	`collect_run_id` of a run whose collector is open (a guidance run, w1.md:103): no comment of its own; what was
	done goes to "Đã làm", the other sentences (warnings, requests, the split question) to the plan section of the
	run's one guidance comment, raw (AD3-4); the same `lines` are returned. None, or no open collector: as above.
	Nothing here raises for an unusable unit: it is rolled back, recorded as `ok=false` with the exception
	class only (D-16). (u1) failing or refusing stops the SLA check and (u2)-(u5).

	The ticket change and the entry update share a savepoint: an exception between them undoes the
	ticket change, so the entry never says applied=0 over a changed ticket (the entry row itself was
	committed before and survives). Nothing is committed until both are written.

	It starts by locking the ticket row and reading its applied classify rows with a lock (ADR-037 QĐ 4): one
	there → no unit runs, this entry records the refusal, one logger line. The lock holds until the commit at
	the end of this step, so never across a model call.
	"""
	ticket = context.ticket_name
	if locked_rows(ticket, LOG_DOCTYPE, {"ticket": ticket, "entry_type": "classify", "applied": 1}):
		return _route_skipped(log_name, decision, context)
	actions, lines, errors = [], [], []
	assigned = task = watcher = commented = None
	sla = None
	frappe.db.savepoint(ROUTE_SAVEPOINT)
	try:
		result = _apply_route_unit(decision, classification, context, actions, errors)
		if result:
			sla = _check_sla(classification.category, context, actions, lines)
			if auto_assign:
				assigned = _assign_unit(decision, context, actions, lines, errors)
			if assigned and decision.needs_task:
				task = _task_unit(assigned, subject, classification, context, actions, lines, errors)
			if decision.watcher:
				watcher = _watch_unit(decision.watcher, context, actions, errors)
			done = _route_lines(result, assigned, task, watcher)
			others = [*lines, *([split_text] if split_text else [])]
			lines = [*done, *others]
			if collect_run_id and collecting(collect_run_id):
				commented = _collect_route_lines(collect_run_id, done, others)
			else:
				commented = _comment_unit(lines, context, actions, errors)
		split = classification.requests if commented and split_text else None
		_record_route(log_name, result, decision, assigned, task, actions, errors, split)
		_log_route_summary(context, result, assigned, task, commented, sla)
	except Exception:
		frappe.db.rollback(save_point=ROUTE_SAVEPOINT)
		raise
	frappe.db.release_savepoint(ROUTE_SAVEPOINT)
	if not frappe.flags.in_test:
		frappe.db.commit()
	return lines


def _route_skipped(log_name, decision, context) -> list:
	"""The ticket was routed by an earlier run: record the refusal on this entry, commit to free the lock."""
	ticket = context.ticket_name
	refusal = _route_action(
		"apply_route", "HD Ticket", ticket, False, ROUTE_ALREADY_DONE, instructor=context.instructor
	)
	_record_route(log_name, None, decision, None, None, [refusal], [])
	frappe.logger(LOGGER_NAME).info(
		"erp_ai route_skipped ticket=%s run_id=%s reason=already_routed", ticket, context.run_id
	)
	if not frappe.flags.in_test:
		frappe.db.commit()
	return []


def _route_action(
	tool, doctype, name, ok, reason=None, rule=None, *, value_before=None, value_after=None, instructor=None
):
	return action_entry(
		tool,
		doctype,
		name,
		ok,
		reason=reason,
		rule=rule,
		value_before=value_before,
		value_after=value_after,
		instructor=instructor,
	)


def _run_unit(tool, call, doctype, name, actions, errors):
	"""Run one write unit in its own savepoint. Returns its result when ok, else None (recorded in `actions`).

	An exception undoes the unit, is recorded by class only and is not retried (ADR-020 QĐ 6).
	"""
	frappe.db.savepoint(ROUTE_UNIT_SAVEPOINT)
	try:
		result = call()
	except Exception as exc:
		frappe.db.rollback(save_point=ROUTE_UNIT_SAVEPOINT)
		error = type(exc).__name__
		errors.append(f"route {tool}: {error}")
		actions.append(_route_action(tool, doctype, name, False, error))
		return None
	frappe.db.release_savepoint(ROUTE_UNIT_SAVEPOINT)
	if not result.get("ok"):
		actions.append(_route_action(tool, doctype, name, False, result.get("reason")))
		return None
	return result


def _assign_unit(decision, context, actions, lines, errors):
	"""(u2): give the ticket to the configured person unless someone already owns it. Returns the user or None.

	Looked at after (u1): a team's Assignment Rule fires inside (u1)'s save, and then the bot stays out (ADR-020 QĐ 2).
	"""
	ticket = context.ticket_name
	existing = site_facts.ticket_assignments(ticket)
	if existing:
		users = ", ".join(dict.fromkeys(row["allocated_to"] for row in existing))
		rule = next((row["assignment_rule"] for row in existing if row["assignment_rule"]), None)
		reason = f"phiếu đã có người được gán: {users}"
		actions.append(
			_route_action(
				"assign_owner", "HD Ticket", ticket, False, reason, rule, instructor=context.instructor
			)
		)
		return None
	user = decision.assignee
	if user is None:
		note = next((item["reason"] for item in decision.notes if item["field"] == "assignee"), None)
		actions.append(
			_route_action("assign_owner", "HD Ticket", ticket, False, note, instructor=context.instructor)
		)
		lines.append(ASSIGN_REQUEST.format(reason=REASON_NO_VALID_ASSIGNEE))
		return None
	if _run_unit("assign_owner", lambda: assign_owner(user, context), "HD Ticket", user, actions, errors):
		actions.append(_route_action("assign_owner", "HD Ticket", user, True, instructor=context.instructor))
		return user
	lines.append(ASSIGN_REQUEST.format(reason=REASON_ASSIGN_FAILED))
	return None


def _task_unit(user, subject, classification, context, actions, lines, errors):
	"""(u3): one linked Task for `user`, created and given in one savepoint. Returns the Task name or None.

	A ticket that already has a Task, whoever made it, gets no second one. An exception (document sharing
	off) undoes the Task and its ToDo, and adds the sentence asking the team lead to act (ADR-020 QĐ 7); the
	sentence names sharing only for `TaskSharingDisabled`, any other exception gets the general reason.
	"""
	ticket = context.ticket_name
	if site_facts.has_linked_task(ticket):
		actions.append(
			_route_action(
				"create_routed_task", "Task", None, False, REASON_TASK_EXISTS, instructor=context.instructor
			)
		)
		return None
	failures = len(errors)
	sharing_off = []

	def create():
		try:
			return create_routed_task(user, subject, classification, context)
		except TaskSharingDisabled:
			sharing_off.append(True)
			raise

	result = _run_unit(
		"create_routed_task",
		create,
		"Task",
		None,
		actions,
		errors,
	)
	if result is None:
		if len(errors) > failures:
			reason = REASON_TASK_NOT_ASSIGNED if sharing_off else REASON_TASK_FAILED
			lines.append(TASK_REQUEST.format(reason=reason))
		return None
	actions.append(
		_route_action("create_routed_task", "Task", result["task"], True, instructor=context.instructor)
	)
	return result["task"]


def _comment_unit(lines, context, actions, errors):
	"""(u4): post the gathered sentences as at most one comment. Returns True when it was posted."""
	if not lines:
		return False
	# the split question quotes the model's reading of the ticket: every line is escaped once, here, where it is posted
	result = _run_unit(
		"post_routing_comment",
		lambda: post_routing_comment([escape_html(line) for line in lines], context),
		"Comment",
		None,
		actions,
		errors,
	)
	if result is None:
		return False
	actions.append(
		_route_action(
			"post_routing_comment", "Comment", result["comment"], True, instructor=context.instructor
		)
	)
	return True


def _collect_route_lines(run_id, done, others) -> bool:
	"""(u4) of a guidance run (w1.md:103): the route's sentences go to the run's collector as raw text, the done ones
	under "Đã làm", the rest inside the plan section; they reach the person in the run's one comment. Returns True
	when a sentence was gathered, as `_comment_unit` does when it posted."""
	for line in done:
		collect(run_id, SECTION_DONE, line)
	for line in others:
		collect(run_id, SECTION_DECIDE, line)
	return bool(done or others)


def _route_lines(result, assigned, task, watcher) -> list[str]:
	"""The route comment's own sentences (U4b.md:247): fields written, person given, Task created, watcher added.

	Fixed text with names only, never the ticket's content. No field changed → the "already right" sentence.
	"""
	fields = ", ".join(
		f"{FIELD_LABELS[field]} {value}"
		for field, value in (result.get("after") or {}).items()
		if field in FIELD_LABELS
	)
	lines = [ROUTE_DONE.format(fields=fields) if fields else ROUTE_NO_CHANGE]
	if assigned:
		lines.append(ROUTE_ASSIGNED.format(person=get_fullname(assigned)))
	if task:
		lines.append(ROUTE_TASK.format(task=task))
	if watcher:
		lines.append(ROUTE_WATCHER.format(person=get_fullname(watcher)))
	return lines


def _watch_unit(watcher, context, actions, errors) -> str | None:
	"""(u5): the D watcher follows the ticket through Frappe's `follow_document`, once (AC-27). Returns the user or None.

	Already following → an `ok=false` entry, nothing written. An exception undoes only this unit (Fix 6).
	"""
	ticket = context.ticket_name
	if frappe.db.exists(
		"Document Follow", {"ref_doctype": "HD Ticket", "ref_docname": ticket, "user": watcher}
	):
		actions.append(
			_route_action(
				WATCHER_TOOL,
				"HD Ticket",
				ticket,
				False,
				REASON_ALREADY_FOLLOWING,
				instructor=context.instructor,
			)
		)
		return None
	if (
		_run_unit(WATCHER_TOOL, lambda: _follow(watcher, ticket), "HD Ticket", ticket, actions, errors)
		is None
	):
		return None
	actions.append(
		_route_action(
			WATCHER_TOOL,
			"HD Ticket",
			ticket,
			True,
			value_after={"watcher": watcher},
			instructor=context.instructor,
		)
	)
	return watcher


def _follow(watcher, ticket) -> dict:
	"""`follow_document` returns nothing when the person turned follow notifications off (A-U4b-9): not forced."""
	if not follow_document("HD Ticket", ticket, watcher):
		return {"ok": False, "reason": REASON_FOLLOW_OFF}
	return {"ok": True}


def _apply_route_unit(decision, classification, context, actions, errors):
	"""(u1): the ticket write. Returns its result when ok, else None (the failure is already in `actions`)."""
	ticket = context.ticket_name
	try:
		result = apply_route(decision, classification, context)
	except Exception as exc:
		frappe.db.rollback(save_point=ROUTE_SAVEPOINT)
		name = type(exc).__name__
		errors.append(f"route apply_route: {name}")
		actions.append(
			_route_action("apply_route", "HD Ticket", ticket, False, name, instructor=context.instructor)
		)
		return None
	if not result.get("ok"):
		actions.append(
			_route_action(
				"apply_route", "HD Ticket", ticket, False, result.get("reason"), instructor=context.instructor
			)
		)
		return None
	actions.append(
		_route_action(
			"apply_route",
			"HD Ticket",
			ticket,
			True,
			value_before=result.get("before"),
			value_after=result.get("after"),
			instructor=context.instructor,
		)
	)
	return result


def _check_sla(category, context, actions, lines):
	"""Read-only SLA check (D-9). Returns "none" / "slow" / "ok", or "skipped" without a routing config."""
	routing = context.routing_config
	if not routing:
		return "skipped"
	ticket = context.ticket_name
	fact = site_facts.applied_sla(ticket)
	if fact is None:
		reason, state = NO_SLA_REASON, "none"
		lines.append(NO_SLA)
	else:
		lag = sla_lag(category, fact["resolution_s"], routing)
		if lag is None:
			return "ok"
		reason = f"SLA {fact['sla']} xử lý {int(lag[0])} phút > mong đợi {lag[1]} phút ({category})"
		state = "slow"
	actions.append(
		_route_action("sla_check", "HD Ticket", ticket, False, reason, instructor=context.instructor)
	)
	frappe.logger(LOGGER_NAME).warning("erp_ai sla ticket=%s run_id=%s %s", ticket, context.run_id, reason)
	return state


def _record_route(log_name, result, decision, assigned, task, actions, errors, split=None):
	"""Update the `classify` entry once (design 3.5). `split`: the requests of the split question, given only when a
	comment carrying it was posted; only then is the question recorded as asked (AC-28)."""
	updates = {
		"applied": 1 if result else 0,
		"actions": json.dumps(_bounded_actions(actions), ensure_ascii=False),
	}
	if split is not None:
		updates["split_requested"] = 1
		updates["split_requests"] = json.dumps(split, ensure_ascii=False)
	if result:
		before = {"ticket": result["before"]} if result.get("before") else {}
		after = {"ticket": result["after"]} if result.get("after") else {}
		if assigned:
			after["assign"] = [assigned]
		if task:
			after["task"] = task
		for column, value in (("value_before", before), ("value_after", after)):
			if value:
				updates[column] = json.dumps(value, ensure_ascii=False)
		# a route note names the reason a field was left empty; it replaces the generic reason for that field
		noted = {note["field"] for note in decision.notes}
		skipped = [item for item in result.get("skipped") or [] if item["field"] not in noted]
		skipped.extend(decision.notes)
		if skipped:
			updates["skipped_fields"] = json.dumps(skipped, ensure_ascii=False)
	if errors:
		previous = frappe.db.get_value(LOG_DOCTYPE, log_name, "error")
		updates["error"] = "; ".join([*([previous] if previous else []), *errors])
	frappe.db.set_value(LOG_DOCTYPE, log_name, updates, update_modified=False)


def _log_route_summary(context, result, assigned, task, commented, sla):
	"""One info line, codes and numbers only (STD-OPS-5, NFR-4')."""
	frappe.logger(LOGGER_NAME).info(
		"erp_ai route ticket=%s run_id=%s applied=%d assigned=%d task=%d comment=%d sla=%s",
		context.ticket_name,
		context.run_id,
		1 if result else 0,
		1 if assigned else 0,
		1 if task else 0,
		1 if commented else 0,
		sla or "-",
	)


def _config_users(routing: dict) -> set[str]:
	"""Every user ID the routing config names: default and prefix assignees, department heads."""
	users = set()
	for entry in ((routing or {}).get("assignees") or {}).values():
		users.add(entry.get("default"))
		users.update((entry.get("prefixes") or {}).values())
	users.update(entry.get("head") for entry in ((routing or {}).get("departments") or {}).values())
	return {user for user in users if user}


def _routing_table(context) -> str:
	"""Routing table of the reason prompt, from the config and mapping already loaded for this run."""
	routing = context.routing_config
	names = {user: get_fullname(user) for user in _config_users(routing)}
	return build_routing_table(context.category_mapping, routing, names)


def _reason(
	ticket_name,
	trigger,
	run_id,
	settings,
	context,
	classification,
	deadline,
	status,
	delay,
	started_at,
	field_map=None,
	notices=None,
	guidance_posted=False,
):
	"""Reasoning step (design 4.3 step 8): at most `max_turns_per_run` model turns, one `reason` entry each.

	The first message carries the configured ticket fields that hold a value as data (AC-24, U4b.md:249), and
	`guidance_posted` when the ticket already has its guidance comment (ticket data, ADR-036 QĐ 7, U4b-10).
	`notices` are the entries of notices posted before this step: they go on the first entry written (U4b.md:250).
	A gateway error posts the run_failed notice on its own entry (U4b.md:251). `started_at` is the run's start: the
	ask_fallback question counts only the ones posted since, so each run below the threshold asks once (AC-22).
	The last turn of a guidance run (every exit without error: no tool wanted, no tool result, the last allowed turn)
	posts the run's one guidance comment before its entry (ADR-036 QĐ 1, AD3-2, R5-16).
	Returns False when the run stopped on a gateway error, True otherwise.
	"""
	pending = list(notices or [])
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
	granted = grant(context.grant_inputs())
	tools = granted.schemas()
	if tools:
		tools[-1]["cache_control"] = {"type": "ephemeral"}
	system = build_reason_system(
		settings.prompt_digest,
		_routing_table(context),
		change_tools=granted.change_block,
		site_admin_tools=granted.record_block,
		unrestricted_tools=granted.unrestricted_block,
		act_now=granted.act_now_block,
		ask_only=granted.ask_only_block,
	)
	fields = _ticket_field_values(ticket_name, field_map or {})
	messages = [
		{
			"role": "user",
			"content": build_initial_message(
				ticket,
				labelled,
				trigger,
				classification,
				ticket_fields=fields,
				guidance_posted=guidance_posted,
			),
		}
	]
	base = {
		"ticket": ticket_name,
		"run_id": run_id,
		"entry_type": "reason",
		"trigger": trigger,
		"instructor": context.instructor,
	}
	max_turns = settings.max_turns_per_run
	for turn in range(1, max_turns + 1):
		status.thinking()
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
			failed = _failure_notice(ticket_name, exc, trigger, context.instructor)
			write_entry(
				**base,
				turn=turn,
				error="; ".join([f"{exc.kind} status={exc.status}", *status.take_errors()]),
				stop_reason=STOP_TIME_BUDGET if exc.kind == DEADLINE_KIND else STOP_GATEWAY_ERROR,
				credential_label=exc.credential_label,
				keys_tried=exc.keys_tried,
				actions=[*pending, *([failed] if failed else [])] or None,
			)
			return False

		# after the call, so the gateway key state it wrote survives an undo; not released: the commit of the
		# `reason` row's `write_entry` ends it (within the turn the runner commits nothing else), and the next
		# turn's savepoint of the same name replaces it
		frappe.db.savepoint(REASON_TURN_SAVEPOINT)
		try:
			tool_blocks = [block for block in result.content if block.get("type") == "tool_use"]
			tool_results, actions, before, after, tool_errors, skipped = [], [], {}, {}, [], []
			# the whole turn waits, before any of its tools runs (D-6)
			if delay is not None and any(block["name"] == ANSWER_TOOL for block in tool_blocks):
				delay.wait_before_answer(deadline)
			for block in tool_blocks:
				status.working(block["name"])
				tool_results.append(_run_tool(block, context, actions, before, after, tool_errors, skipped))
			stop_reason = result.stop_reason
			wants_tools = stop_reason == STOP_TOOL_USE
			if wants_tools and turn == max_turns:
				stop_reason = STOP_MAX_TURNS
			final = not wants_tools or not tool_results or turn == max_turns
			if final and collecting(run_id):
				_finish_guidance(context, actions)
			# below the threshold the run asks exactly one question, the model's or this one (AC-22, Fix 9)
			if final and context.below_threshold and not asked_in_run(run_id):
				asked = _notice(
					ticket_name,
					"ask_fallback",
					_ask_fallback_body(run_id, classification, settings),
					started_at,
					trigger=trigger,
					instructor=context.instructor,
				)
				if asked:
					actions.append(asked)
					mark_asked(run_id)
			# the notices posted before this step go on its first entry, ahead of the turn's own writes
			actions[:0] = pending
			pending = []
			write_entry(
				**base,
				**_call_fields(result),
				turn=turn,
				stop_reason=stop_reason,
				tools_called=[block["name"] for block in tool_blocks] or None,
				error="; ".join([*tool_errors, *status.take_errors()]) or None,
				actions=_bounded_actions(actions) if actions else None,
				value_before=before or None,
				value_after=after or None,
				skipped_fields=skipped or None,
			)
		except Exception:
			# no change of the turn may be committed without its `reason` entry (NFR-3); `run_for_ticket` logs it
			_undo_turn(run_id)
			raise
		_write_propose_rows(actions, context)
		if not wants_tools or not tool_results:
			return True
		messages.append({"role": "assistant", "content": result.content})
		messages.append({"role": "user", "content": tool_results})
	return True


def _finish_guidance(context, actions) -> None:
	"""The one place the runner calls `post_guidance` (ADR-036 QĐ 1, w1.md:105): inside the last turn, after its tools
	and before its entry, so the comment is undone with the turn (R5-16). Posted → one action entry with the section
	counts (QĐ 8). A run in parallel posted the ticket's guidance first → one log line, and the run's collected lines
	go out as before: one result comment without the marker, in the order of GUIDANCE_SECTIONS, one sentence per line,
	each escaped once, no section heading (design-w1-fixes-20 Điểm 1.6, AD3-4). Nothing to say → one log line."""
	ticket, run_id = context.ticket_name, context.run_id
	result = post_guidance(ticket, run_id)
	if result.get("ok"):
		actions.append(
			action_entry(
				GUIDANCE_TOOL,
				"Comment",
				result["comment"],
				True,
				value_after={"counts": result["counts"]},
				instructor=context.instructor,
			)
		)
		return
	reason = result.get("reason")
	if reason == REASON_NO_CONTENT:
		frappe.logger(LOGGER_NAME).info("erp_ai guidance run_id=%s skipped=no_content", run_id)
		return
	if reason != REASON_GUIDANCE_EXISTS:
		actions.append(
			action_entry(GUIDANCE_TOOL, "Comment", None, False, reason=reason, instructor=context.instructor)
		)
		return
	frappe.logger(LOGGER_NAME).info(GUIDANCE_EXISTS_LOG, ticket, run_id)
	sections = collected(run_id)[1]
	lines = [line for section in GUIDANCE_SECTIONS for line in sections[section]]
	if not lines:
		return
	posted = post_routing_comment([escape_html(line) for line in lines], context)
	actions.append(
		_route_action(
			"post_routing_comment",
			"Comment",
			posted.get("comment"),
			bool(posted.get("ok")),
			posted.get("reason"),
			instructor=context.instructor,
		)
	)


def _ask_fallback_body(run_id, classification, settings) -> str:
	"""The fallback question with the footer the question tool adds: the run's confidence and the threshold.

	The confidence is this run's own: its classify row (an insert run; none when it could not classify), else the
	pair the context was built from (U1.md:260). An insert run reads no other run's classification (U1.md:261).
	"""
	own = frappe.get_all(
		LOG_DOCTYPE,
		filters={"run_id": run_id, "entry_type": "classify"},
		fields=["predicted_category", "predicted_confidence_pct"],
		limit=1,
	)
	if own:
		pct = own[0].predicted_confidence_pct if own[0].predicted_category else None
	else:
		pct = (classification or {}).get("confidence_pct")
	footer = ASK_FOOTER.format(
		pct=ASK_PCT_UNKNOWN if pct is None else f"{pct}%", threshold=policy.confidence_threshold(settings)
	)
	return f"{ASK_FALLBACK_BODY}\n\n{footer}"


def _undo_turn(run_id) -> None:
	"""Undo the uncommitted writes of the failing reason turn, back to right after its model call.

	As `frappe.db.rollback()` does, stopping at the savepoint (design-amd2 D-8): the commit callbacks queued
	since are dropped (only the turn's: the commit before the savepoint ran the earlier ones) and the rollback
	callbacks run. When the savepoint is already gone, nothing is undone and neither happens: both callback
	queues are left as they are. Raises nothing: the caller re-raises the turn's own error, which must reach
	the Error Log.
	"""
	try:
		frappe.db.rollback(save_point=REASON_TURN_SAVEPOINT)
	except Exception as exc:
		# the savepoint is gone: a commit inside a tool (DDL, a controller's own commit) kept the turn's earlier
		# writes (ADR-024 QĐ 5, accepted). Not set again and the callback queues left alone: the remaining
		# writes will be committed, so their callbacks must run (D-8)
		frappe.logger(LOGGER_NAME).warning(
			"reason turn undo failed run_id=%s error=%s", run_id, type(exc).__name__
		)
		return
	frappe.db.before_commit.reset()
	frappe.db.after_commit.reset()
	try:
		frappe.db.after_rollback.run()
	except Exception as exc:
		# the turn's writes are already undone; a rollback hook's failure must not replace the turn's error
		frappe.logger(LOGGER_NAME).warning(
			"reason turn undo callback failed run_id=%s error=%s", run_id, type(exc).__name__
		)


def _write_propose_rows(actions, context) -> None:
	"""The `propose` step of each proposal the turn made, written by the agent account (design 4.1 step 4).

	Only after the turn's `reason` row (design-amd2 D-7): `write_entry` commits, and a commit inside the turn
	would keep its writes without that row. Read from the turn's own `actions`, not their bounded copy.
	"""
	for action in actions:
		if action["tool"] in PROPOSE_TOOLS and action["ok"]:
			write_entry(
				entry_type=ENTRY_TYPE_CHANGE,
				trigger=TRIGGER_CHANGE_ACTION,
				change_step=PROPOSE_STEP,
				actor=AGENT_USER,
				change_proposal=action["name"],
				ticket=context.ticket_name,
				run_id=context.run_id,
				instructor=context.instructor,
			)


def _run_tool(block, context, actions, before, after, tool_errors, skipped):
	"""Execute one `tool_use` block; record write outcomes, skipped fields and crashes in the turn's accumulators; return its `tool_result`.

	A crash is logged as tool name + exception class only (D-20, STD-SEC-6); the model sees the class too.
	"""
	name = block["name"]
	arguments = block.get("input") or {}
	try:
		outcome = execute_tool(name, arguments, context)
	except Exception as exc:
		tool_errors.append(f"tool {name}: {type(exc).__name__}")
		if name in WRITE_TOOL_TARGETS:
			actions.append(_action(name, context, None, False, arguments, crash=f"lỗi: {type(exc).__name__}"))
		return {
			"type": "tool_result",
			"tool_use_id": block["id"],
			"content": f"Lỗi: {type(exc).__name__}",
			"is_error": True,
		}
	# a comment held for the run's guidance comment writes nothing now: no entry (ADR-036 QĐ 8, U4b-16 (a))
	if name in WRITE_TOOL_TARGETS and not outcome.get("held"):
		actions.append(_action(name, context, outcome, bool(outcome.get("ok")), arguments))
		_record_snapshot(name, outcome, len(actions), before, after)
		if outcome.get("ok") and "after" in outcome:
			before[name] = outcome.get("before")
			after[name] = outcome["after"]
		if name == "set_classification" and outcome.get("ok"):
			skipped.extend(outcome.get("skipped") or [])
	content = json.dumps(outcome, ensure_ascii=False, default=str)[:TOOL_RESULT_MAX_CHARS]
	return {"type": "tool_result", "tool_use_id": block["id"], "content": content}


def _record_snapshot(name, outcome, n, before, after) -> None:
	"""Keep a generic write call's full before/after under `<tool>#<n>`, n = its position in the turn's actions;
	the snapshot is always taken out of the outcome, so it never reaches the model (design-amd2 §4.1)."""
	snapshot = outcome.pop("_snapshot", None)
	if name in GENERIC_WRITE_TOOLS and snapshot is not None:
		before[f"{name}#{n}"] = snapshot["before"]
		after[f"{name}#{n}"] = snapshot["after"]


def _action(name, context, outcome, ok, arguments, *, crash=None):
	"""One action entry of a write tool, through the one builder `run_log.action_entry` (U3 3.2)."""
	doctype, key = WRITE_TOOL_TARGETS[name]
	if doctype is None:
		requested = arguments.get("doctype") if isinstance(arguments, dict) else None
		doctype = str((outcome or {}).get("doctype") or requested or "") or None
	record = context.ticket_name if key is None else (outcome or {}).get(key)
	value_before, value_after = _entry_values(name, outcome, arguments) if ok else (None, None)
	return action_entry(
		name,
		doctype,
		record,
		ok,
		reason=crash or (outcome or {}).get("reason"),
		value_before=value_before,
		value_after=value_after,
		instructor=context.instructor,
	)


def _entry_values(name, outcome, arguments):
	"""The (before, after) values of a successful write tool's action entry (U3 3.2 table)."""
	if "value_before" in outcome or "value_after" in outcome:
		return outcome.get("value_before"), outcome.get("value_after")
	if "before" in outcome or "after" in outcome:
		before, after = outcome.get("before"), outcome.get("after")
		if isinstance(after, dict) or isinstance(before, dict):
			return before, after
		return {HINT_FIELD: before}, {HINT_FIELD: after}
	if name in PROPOSE_TOOLS:
		return None, {PROPOSAL_STATUS_KEY: outcome.get("status")}
	if name in CREATING_TOOLS and isinstance(arguments, dict):
		return None, arguments
	return None, None


def _stored_bytes(value) -> int:
	"""Size of `value` as `write_entry` stores it (utf-8 JSON)."""
	return len(json.dumps(value, ensure_ascii=False).encode("utf-8"))


def _cut_strings(value):
	"""`value` with every string longer than ACTION_VALUE_MAX_BYTES cut on a character boundary and marked."""
	if isinstance(value, str):
		data = value.encode("utf-8")
		if len(data) <= ACTION_VALUE_MAX_BYTES:
			return value
		room = ACTION_VALUE_MAX_BYTES - len(ACTION_CUT_MARKER.encode("utf-8"))
		return data[:room].decode("utf-8", errors="ignore") + ACTION_CUT_MARKER
	if isinstance(value, dict):
		return {key: _cut_strings(item) for key, item in value.items()}
	if isinstance(value, list | tuple):
		return [_cut_strings(item) for item in value]
	return value


def _without_values(entry):
	"""`entry` with its before/after values replaced by the marker; who, what and the outcome stay."""
	if not isinstance(entry, dict):
		return entry
	return {
		key: ACTION_CUT_MARKER if key in ACTION_VALUE_KEYS and value is not None else value
		for key, value in entry.items()
	}


def _bounded_actions(actions) -> list:
	"""The turn's `actions` cut to fit the `actions` column: at most ACTIONS_MAX_BYTES as stored (F-1).

	Each string is first cut to ACTION_VALUE_MAX_BYTES. When the list is still too large, entries lose their
	before/after values to the marker, the costliest values first, so as many entries as fit keep theirs.
	Every entry stays (one per tool call) unless even the entries without values do not fit: then the last
	ones are dropped and one closing `{"cut": marker, "dropped": count}` entry says how many.
	"""
	entries = [_cut_strings(entry) for entry in actions]
	if _stored_bytes(entries) <= ACTIONS_MAX_BYTES:
		return entries
	bare = [_without_values(entry) for entry in entries]
	# replacing one list item changes the stored size by exactly the difference of the two items
	costs = [
		_stored_bytes(entry) - _stored_bytes(stripped) for entry, stripped in zip(entries, bare, strict=True)
	]
	room = ACTIONS_MAX_BYTES - _stored_bytes(bare)
	if room >= 0:
		kept = list(bare)
		for index in sorted(range(len(entries)), key=costs.__getitem__):
			if costs[index] > room:
				break
			kept[index] = entries[index]
			room -= costs[index]
		return kept
	while bare and _stored_bytes([*bare, _dropped_entry(len(entries) - len(bare))]) > ACTIONS_MAX_BYTES:
		bare.pop()
	return [*bare, _dropped_entry(len(entries) - len(bare))]


def _dropped_entry(count: int) -> dict:
	return {"cut": ACTION_CUT_MARKER, "dropped": count}
