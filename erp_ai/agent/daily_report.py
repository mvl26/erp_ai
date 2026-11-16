"""The 08:00 daily report (design 3.6.3, AC-51, AC-26, D-18, A-D5).

Windows come from `anchor` (the cycle's 08:00): "new" means created in `[anchor - 24 h, anchor)`, "done" means
resolved in that window. Every state is read when the job runs: "open" means created before `anchor` and
`status_category` not "Resolved"; first response, BA notes and Tasks are read as they are at run time.
"""

from datetime import datetime, time, timedelta

import frappe
from frappe.utils import escape_html, get_datetime, getdate, now_datetime
from frappe.utils.file_lock import LockTimeoutError
from frappe.utils.synchronization import filelock

from erp_ai.agent import lifecycle, policy
from erp_ai.agent.classification import load_mapping
from erp_ai.agent.kpi import is_bot_close, log_actions
from erp_ai.agent.ops_data import (
	BA_NOTE_MARKER,
	CYCLE_START,
	category_by_ticket_type,
	daily_cycle,
	ticket_category,
)
from erp_ai.agent.redact import redact_secrets
from erp_ai.agent.routing import load_routing_config, processing_deadline, response_overdue
from erp_ai.agent.text_lines import filled_lines
from erp_ai.constants import AGENT_USER, CATEGORIES, LOG_DOCTYPE, LOGGER_NAME, SETTING_DOCTYPE

TICKET = "HD Ticket"
WINDOW = timedelta(hours=24)
UNKNOWN_CATEGORY = "?"
PROGRESS_CATEGORIES = ("D", "E")
# Same rule as the setting's E-2 check; the agent core may not import the controller (ADR-001).
DUE_FIELD_TYPES = ("Date", "Datetime")
# The kind an ok action entry of ERP AI Log counts as in `bot_actions`; any other tool counts as OTHER_ACTION_KIND
# (design-w1-fixes-18 Điểm 2.2).
ACTION_KIND_BY_TOOL = {
	"set_classification": "phân loại",
	"assign_owner": "gán",
	"create_task": "Task",
	"create_routed_task": "Task",
	"post_comment": "comment",
	"post_routing_comment": "comment",
	"reply_to_requester": "trả lời",
	lifecycle.TOOL_LIFECYCLE_COMMENT: "comment",
}
# Ok entries of these tools are not counted: their row is already counted ("phân loại" through `applied`, or the
# `change_step="propose"` row each ok propose entry writes).
TOOLS_COUNTED_ELSEWHERE = frozenset(
	{"apply_route", "propose_file_change", "propose_new_file", "propose_bench_command"}
)
OTHER_ACTION_KIND = "khác"
KIND_CLASSIFY = "phân loại"
KIND_CLOSE = "đóng"
KIND_ERROR = "lỗi"
KIND_BY_CHANGE_STEP = {"propose": "đề xuất chờ duyệt", "approve": "đã duyệt", "reject": "bị từ chối"}
# Every kind of AC-51, in its order, each reported even when 0.
BOT_ACTION_KINDS = (
	KIND_CLASSIFY,
	"gán",
	"Task",
	"comment",
	"trả lời",
	KIND_CLOSE,
	*KIND_BY_CHANGE_STEP.values(),
	KIND_ERROR,
	OTHER_ACTION_KIND,
)
COST_DIGITS = 6
LOCK_NAME = "erp_ai_daily_report"
LOCK_TIMEOUT_S = 5
TITLE_DAILY_REPORT_FAILED = "erp_ai: báo cáo hằng ngày lỗi"
DEADLINE_FORMAT = "%d/%m/%Y %H:%M"
EXCLUDED_LABEL = "(nhóm loại trừ)"
NONE_LABEL = "Không có"
SUBJECT_FORMAT = "[erp_ai] Báo cáo hằng ngày {cycle:%d/%m/%Y}"
LIST_SECTIONS = (
	("new_list", "Phiếu mới"),
	("due_soon", "Sắp đến mốc xử lý"),
	("overdue", "Quá mốc xử lý"),
	("response_overdue", "Quá mốc phản hồi"),
	("c_missing_ba_note", "Đầu mục C chưa có BA note"),
	("cd_missing_task", "Đầu mục C/D chưa có Task"),
)


def build_daily_report(anchor: datetime) -> dict:
	"""The ticket figures of the report for the window ending at `anchor`."""
	settings = frappe.get_single(SETTING_DOCTYPE)
	reverse_map = category_by_ticket_type(load_mapping(settings.category_mapping))
	routing = load_routing_config(settings.routing_rules)
	due_field = _due_field(settings.field_due_date)
	start = anchor - WINDOW

	new = _tickets([["creation", ">=", start], ["creation", "<", anchor]], reverse_map)
	open_rows = _tickets(
		[["creation", "<", anchor], ["status_category", "!=", "Resolved"]], reverse_map, due_field
	)
	for row in open_rows:
		row.deadline = processing_deadline(
			row.category, row.resolution_by, row.get(due_field) if due_field else None
		)
	due_until = anchor + timedelta(hours=settings.due_reminder_hours)
	overdue = [row for row in open_rows if row.deadline and row.deadline <= anchor]

	c_old = [
		row
		for row in open_rows
		if row.category == "C" and row.creation <= anchor - timedelta(hours=settings.ba_note_due_hours)
	]
	ba_noted = _ba_noted([row.name for row in c_old])
	cd_old = [
		row
		for row in open_rows
		if row.category in ("C", "D") and row.creation <= anchor - timedelta(days=settings.task_due_days)
	]
	with_task = _with_task([row.name for row in cd_old])

	return {
		"new_by_category_priority": _count_by_category_priority(new),
		"new_list": _items(new),
		"due_soon": _items(
			(row for row in open_rows if row.deadline and anchor < row.deadline <= due_until),
			with_deadline=True,
		),
		"overdue": _items(overdue, with_deadline=True),
		"response_overdue": _items(
			row
			for row in open_rows
			if response_overdue(row.creation, row.first_responded_on, row.category, routing, anchor)
		),
		"c_missing_ba_note": _items(row for row in c_old if row.name not in ba_noted),
		"cd_missing_task": _items(row for row in cd_old if row.name not in with_task),
		"de_progress": _de_progress(start, anchor, open_rows, overdue, reverse_map),
		**_bot_day(anchor),
	}


def _bot_day(anchor: datetime) -> dict:
	"""`bot_actions` and `cost_yesterday` from the ERP AI Log rows created on the day before `anchor`'s date."""
	day_start = datetime.combine(anchor.date() - timedelta(days=1), time.min)
	rows = frappe.get_all(
		LOG_DOCTYPE,
		filters=[["creation", ">=", day_start], ["creation", "<", day_start + timedelta(days=1)]],
		fields=["ticket", "entry_type", "applied", "change_step", "actions", "error", "cost_usd"],
	)
	counts = dict.fromkeys(BOT_ACTION_KINDS, 0)
	for row in rows:
		if row.entry_type == "classify" and row.applied:
			counts[KIND_CLASSIFY] += 1
		if row.change_step in KIND_BY_CHANGE_STEP:
			counts[KIND_BY_CHANGE_STEP[row.change_step]] += 1
		if (row.error or "").strip():
			counts[KIND_ERROR] += 1
		for action in log_actions(row.actions):
			kind = _action_kind(action, row.ticket)
			if kind:
				counts[kind] += 1
	cost = round(float(sum(row.cost_usd or 0 for row in rows)), COST_DIGITS)
	return {"bot_actions": counts, "cost_yesterday": cost}


def _action_kind(action: dict, ticket: str | None) -> str | None:
	"""The kind an action entry counts as, or None when it is not ok or its row already counts it."""
	if action.get("ok") is not True:
		return None
	if is_bot_close(action, ticket):
		return KIND_CLOSE
	tool = action.get("tool")
	if tool in TOOLS_COUNTED_ELSEWHERE:
		return None
	return ACTION_KIND_BY_TOOL.get(tool, OTHER_ACTION_KIND)


def _due_field(due_field: str | None) -> str | None:
	"""The configured due field, or None when it is unset or no longer a Date/Datetime field of HD Ticket."""
	if not due_field:
		return None
	field = frappe.get_meta(TICKET).get_field(due_field)
	if field is None or field.fieldtype not in DUE_FIELD_TYPES:
		frappe.logger(LOGGER_NAME).warning(
			"erp_ai daily_report: due field %s is not a Date/Datetime field of HD Ticket, using resolution_by",
			due_field,
		)
		return None
	return due_field


def _tickets(filters: list, reverse_map: dict[str, str], due_field: str | None = None) -> list:
	"""Ticket rows oldest first, each with its `category` (None when unknown)."""
	rows = frappe.get_all(
		TICKET,
		filters=filters,
		fields=[
			"name",
			"subject",
			"ticket_type",
			"priority",
			"creation",
			"first_responded_on",
			"resolution_by",
			*([due_field] if due_field else []),
		],
		order_by="creation asc, name asc",
	)
	for row in rows:
		row.category = ticket_category(row, reverse_map)
	return rows


def _items(rows, with_deadline: bool = False) -> list[dict]:
	"""List entries; an excluded ticket (A-D5) carries only its number, category and priority.

	With `with_deadline`, a sendable ticket's entry also carries the processing deadline it was listed by.
	"""
	items = []
	for row in rows:
		item = {"name": row.name, "category": row.category or UNKNOWN_CATEGORY, "priority": _priority(row)}
		if policy.can_send_ticket(row.name):
			item.update(subject=row.subject, excluded=False)
			if with_deadline:
				item["deadline"] = row.deadline
		else:
			item["excluded"] = True
		items.append(item)
	return items


def _count_by_category_priority(rows: list) -> dict[str, dict[str, int]]:
	counts: dict[str, dict[str, int]] = {}
	for row in rows:
		by_priority = counts.setdefault(row.category or UNKNOWN_CATEGORY, {})
		priority = _priority(row)
		by_priority[priority] = by_priority.get(priority, 0) + 1
	return counts


def _priority(row) -> str:
	"""HD Ticket does not require a priority; an empty one counts as UNKNOWN_CATEGORY."""
	return row.priority or UNKNOWN_CATEGORY


def _ba_noted(names: list[str]) -> set[str]:
	"""Tickets with a comment by the bot that starts with BA_NOTE_MARKER."""
	if not names:
		return set()
	comments = frappe.get_all(
		"Comment",
		filters={
			"reference_doctype": TICKET,
			"reference_name": ["in", names],
			"comment_type": "Comment",
			"owner": AGENT_USER,
		},
		fields=["reference_name", "content"],
	)
	return {row.reference_name for row in comments if (row.content or "").startswith(BA_NOTE_MARKER)}


def _with_task(names: list[str]) -> set[str]:
	"""Tickets with at least one Task whose `ai_ticket` is the ticket."""
	if not names:
		return set()
	return {
		row.ai_ticket
		for row in frappe.get_all("Task", filters={"ai_ticket": ["in", names]}, fields=["ai_ticket"])
	}


def _de_progress(
	start: datetime, anchor: datetime, open_rows: list, overdue: list, reverse_map: dict
) -> dict:
	"""For D and E: resolved in the window and still Resolved, open, open past the processing deadline."""
	resolved = frappe.get_all(
		TICKET,
		filters=[
			["resolution_date", ">=", start],
			["resolution_date", "<", anchor],
			["status_category", "=", "Resolved"],
		],
		fields=["ticket_type"],
	)
	resolved_categories = [ticket_category(row, reverse_map) for row in resolved]
	return {
		category: {
			"done": resolved_categories.count(category),
			"in_progress": sum(row.category == category for row in open_rows),
			"overdue": sum(row.category == category for row in overdue),
		}
		for category in PROGRESS_CATEGORIES
	}


def run_daily_report(now: datetime | None = None) -> None:
	"""Build the report of the cycle `now` belongs to and queue its email once; the watermark is written here
	only, in the same transaction as the email (design 3.6.3, ADR-033 QĐ 6).

	Nothing leaves this function as an error: a busy lock, an empty recipient list, a weekend with the
	weekend switch off and a failed build, render or send are logged and the job returns (AC-52).
	"""
	logger = frappe.logger(LOGGER_NAME)
	try:
		with filelock(LOCK_NAME, timeout=LOCK_TIMEOUT_S):
			_run_locked(get_datetime(now) if now else now_datetime(), logger)
	except LockTimeoutError:
		logger.info("daily_report: lock busy")


def _run_locked(now: datetime, logger) -> None:
	cycle = daily_cycle(now)
	sent_on = frappe.db.get_single_value(SETTING_DOCTYPE, "daily_report_sent_on")
	if sent_on and getdate(sent_on) == cycle:
		logger.info("daily_report: already sent for %s", cycle)
		return
	if cycle.weekday() >= 5 and not frappe.db.get_single_value(SETTING_DOCTYPE, "daily_report_weekends"):
		logger.info("daily_report: weekend, skipped")
		return
	recipients = list(
		dict.fromkeys(filled_lines(frappe.db.get_single_value(SETTING_DOCTYPE, "coo_report_recipients")))
	)
	if not recipients:
		logger.info("daily_report: chưa có người nhận")
		return
	step = "build"
	try:
		data = build_daily_report(datetime.combine(cycle, CYCLE_START))
		message = render_daily_report(data)
		step = "send"
		frappe.sendmail(
			recipients=recipients,
			subject=SUBJECT_FORMAT.format(cycle=cycle),
			message=message,
			delayed=True,
		)
		frappe.db.set_single_value(SETTING_DOCTYPE, "daily_report_sent_on", cycle)
	except Exception as exc:
		frappe.db.rollback()
		frappe.log_error(TITLE_DAILY_REPORT_FAILED, f"{step} error={type(exc).__name__}")
		return
	if not frappe.flags.in_test:
		# the lock is released after this function: the watermark must be durable by then
		frappe.db.commit()
	logger.info(
		"erp_ai daily_report: %s new tickets, %s past the response mark",
		len(data["new_list"]),
		len(data["response_overdue"]),
	)


def render_daily_report(data: dict) -> str:
	"""The report as HTML. Ticket text goes through `redact_secrets` then `escape_html`; an excluded ticket is
	printed by number only. Lists keep the order of `data`."""
	parts = [
		_section("Phiếu mới theo đầu mục và ưu tiên", _count_table(data["new_by_category_priority"])),
	]
	for key, title in LIST_SECTIONS:
		parts.append(_section(title, _list_html(data[key])))
	progress = "".join(
		f"<tr><td>{category}</td><td>{values['done']}</td><td>{values['in_progress']}</td>"
		f"<td>{values['overdue']}</td></tr>"
		for category, values in data["de_progress"].items()
	)
	parts.append(
		_section(
			"Đầu mục D, E",
			"<table><tr><th>Đầu mục</th><th>Đã xong</th><th>Đang xử lý</th><th>Quá mốc</th></tr>"
			f"{progress}</table>",
		)
	)
	actions = "".join(
		f"<tr><td>{escape_html(kind)}</td><td>{count}</td></tr>"
		for kind, count in data["bot_actions"].items()
	)
	parts.append(_section("Việc bot đã làm hôm qua", f"<table>{actions}</table>"))
	parts.append(_section("Tổng phí hôm qua (USD)", f"{data['cost_yesterday']:.{COST_DIGITS}f}"))
	return "".join(parts)


def _section(title: str, body: str) -> str:
	return f"<h3>{escape_html(title)}</h3>{body}"


def _text(value: str | None) -> str:
	return escape_html(redact_secrets(value))


def _list_html(items: list[dict]) -> str:
	if not items:
		return f"<p>{NONE_LABEL}</p>"
	lines = []
	for item in items:
		if item.get("excluded"):
			lines.append(f"<li>#{escape_html(item['name'])} {EXCLUDED_LABEL}</li>")
			continue
		line = (
			f"#{escape_html(item['name'])} - {escape_html(item['category'])} - "
			f"{escape_html(item['priority'])} - {_text(item.get('subject'))}"
		)
		if item.get("deadline"):
			line += f" - {item['deadline']:{DEADLINE_FORMAT}}"
		lines.append(f"<li>{line}</li>")
	return f"<ul>{''.join(lines)}</ul>"


def _count_table(counts: dict[str, dict[str, int]]) -> str:
	categories = [*CATEGORIES, UNKNOWN_CATEGORY]
	priorities = sorted(
		{priority for by in counts.values() for priority in by if priority != UNKNOWN_CATEGORY}
	)
	if any(UNKNOWN_CATEGORY in by for by in counts.values()):
		priorities.append(UNKNOWN_CATEGORY)
	if not priorities:
		return f"<p>{NONE_LABEL}</p>"
	head = "".join(f"<th>{escape_html(priority)}</th>" for priority in priorities)
	rows = "".join(
		f"<tr><td>{category}</td>"
		+ "".join(f"<td>{counts.get(category, {}).get(priority, 0)}</td>" for priority in priorities)
		+ "</tr>"
		for category in categories
	)
	return f"<table><tr><th>Đầu mục</th>{head}</tr>{rows}</table>"
