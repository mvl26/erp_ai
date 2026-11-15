import dataclasses
import json
import re
from datetime import datetime

import frappe
from frappe.utils import escape_html, now_datetime

from erp_ai.agent import policy, site_facts
from erp_ai.agent.classification import CONFIDENCE_PCT_MAX, Classification
from erp_ai.agent.routing import RouteDecision, decide_route
from erp_ai.agent.tools.registry import ToolContext, ToolSpec
from erp_ai.constants import (
	AGENT_USER,
	CATEGORIES,
	CLASSIFICATION_FIELDS,
	CLASSIFIED_BY_AI,
	CLASSIFIED_BY_HUMAN,
	CONFIDENCE_VALUES,
	LOGGER_NAME,
	SETTING_DOCTYPE,
)

TICKET_DOCTYPE = "HD Ticket"
TASK_DOCTYPE = "Task"
HINT_FIELD = "ai_resolution_hint"
# Written by handlers.ticket_validate at creation; erp_ai.agent may not import erp_ai.handlers (LAYER_RULES).
CREATED_LABELS_FIELD = "ai_created_labels"
REASON_HUMAN_FILLED = "người đã điền lúc tạo phiếu"
# A broken record reads fail-closed: every classification field counts as filled by the person.
_EVERY_FIELD_HUMAN = dict.fromkeys(CLASSIFICATION_FIELDS, True)
# Target field -> DocType holding its allowed values (design 3.5).
LINKED_DOCTYPES = {
	"ticket_type": "HD Ticket Type",
	"agent_group": "HD Team",
	"priority": "HD Ticket Priority",
}
REASON_MAX = 200
# The kinds of the post_comment tool (AC-22, U4b.md:126-133); U8 appends "ba_note".
COMMENT_KINDS = ("de_xuat", "hoi")
CONFIDENCE_LINE = re.compile(r"Độ tin cậy:\s*(\d{1,3})\s*%")
EVIDENCE_HEADER = "Căn cứ"
ASK_FOOTER = "Độ tin cậy phân loại: {pct} (ngưỡng {threshold}%). Bot chỉ hỏi, chưa ghi gì trên phiếu."
REASON_NO_CONFIDENCE = "comment đề xuất thiếu dòng 'Độ tin cậy: NN%' (NN từ 0 đến 100)"
REASON_NO_EVIDENCE = f"comment thiếu phần '**{EVIDENCE_HEADER}:**' có nội dung"
REASON_ASK_ONLY = "độ tin cậy dưới ngưỡng: chỉ được đăng comment hỏi (kind = hoi)"
REASON_ONE_ASK = "đã đăng comment hỏi trong lần chạy này"
_REASON_BAD_KIND = f"kind phải là một trong {', '.join(COMMENT_KINDS)}"
_PCT_UNKNOWN = "chưa có"
# Runs that already asked their one question (AC-22, A-U4b-12); read and written only by the two functions below.
_ASKED_RUNS_FLAG = "erp_ai_asked_runs"
# A section ends at the next line that opens with a `**…:**` heading (U4b.md:168).
_NEXT_HEADING = re.compile(r"^[ \t]*\*\*[^*\n]+:\*\*", re.M)
# Status notices (AC-23): a notice is "<prefix> <body>"; one of a kind per ticket since a mark (U4b.md:134-140).
NOTICE_PREFIXES = {
	"daily_limit": "Bot tạm dừng trên phiếu này hôm nay:",
	"over_budget": "Bot đang chạy ở mức L1:",
	"run_failed": "Bot chưa xử lý xong phiếu này:",
	"ask_fallback": "Bot chưa đủ chắc để xử lý phiếu này:",
}
REASON_NOTICE_SENT = "đã thông báo"


def _fail(reason: str) -> dict:
	return {"ok": False, "reason": reason[:REASON_MAX]}


def locked_rows(
	ticket_name: str, doctype: str, filters: dict, fields: tuple[str, ...] = ("name",)
) -> list[dict]:
	"""Lock the ticket row, then read `fields` of the `doctype` rows matching `filters` with a lock (ADR-036 QĐ 4).

	A locking read sees the latest committed rows, not this transaction's REPEATABLE READ snapshot; both locks
	hold until the transaction's next commit. The one `for_update` of this module. No such ticket → ValueError.
	"""
	if not ticket_name or not frappe.db.get_value(TICKET_DOCTYPE, ticket_name, "name", for_update=True):
		raise ValueError("phiếu không có")
	return frappe.db.get_values(doctype, filters, list(fields), as_dict=True, for_update=True)


def locked_count(ticket_name: str, doctype: str, filters: dict) -> int:
	return len(locked_rows(ticket_name, doctype, filters))


def _existing_values(wanted: dict, reasons: dict | None = None) -> tuple[dict, list]:
	"""Values to write (only those that exist on the site) and the skipped fields with a reason.

	`reasons` holds the routing reason for fields the route left empty on purpose.
	"""
	reasons = reasons or {}
	values, skipped = {}, []
	for field, value in wanted.items():
		if not value:
			skipped.append({"field": field, "reason": reasons.get(field, "ánh xạ không có giá trị")})
		elif not frappe.db.exists(LINKED_DOCTYPES[field], value):
			skipped.append({"field": field, "reason": "giá trị không tồn tại trên hệ thống"})
		else:
			values[field] = value
	return values, skipped


def created_labels(raw: str | None) -> dict:
	"""The classification fields a person typed at creation, read from `ai_created_labels`; empty → {}.

	Broken JSON, a value that is not a dict or a key outside CLASSIFICATION_FIELDS → all three (fail-closed);
	the caller logs the warning, it knows the ticket.
	"""
	if not raw:
		return {}
	try:
		labels = json.loads(raw)
	except (TypeError, ValueError):
		return dict(_EVERY_FIELD_HUMAN)
	if not isinstance(labels, dict) or not set(labels) <= set(CLASSIFICATION_FIELDS):
		return dict(_EVERY_FIELD_HUMAN)
	return labels


def keep_human_fields(decision: RouteDecision, labels: dict) -> RouteDecision:
	"""`decision` with every field of `labels` emptied and noted REASON_HUMAN_FILLED; the rest unchanged."""
	filled = [field for field in CLASSIFICATION_FIELDS if field in labels]
	if not filled:
		return decision
	notes = (*decision.notes, *({"field": field, "reason": REASON_HUMAN_FILLED} for field in filled))
	return dataclasses.replace(decision, **dict.fromkeys(filled), notes=notes)


def _mapped_values(doc, args: dict, ctx: ToolContext) -> tuple[dict, list]:
	classification = Classification(
		category=args["category"],
		confidence=args["confidence"],
		complexity=doc.ai_complexity or 0,
		importance=doc.ai_importance or 0,
	)
	labels = created_labels(doc.get(CREATED_LABELS_FIELD))
	if labels == _EVERY_FIELD_HUMAN:
		frappe.logger(LOGGER_NAME).warning(f"erp_ai created_labels invalid ticket={doc.name}")
	decision = keep_human_fields(
		decide_route(
			classification,
			doc.subject,
			ctx.category_mapping,
			ctx.routing_config or {},
			team_exists=site_facts.team_exists,
			is_excluded_team=policy.is_excluded_team,
			is_active_agent=site_facts.is_active_agent,
		),
		labels,
	)
	wanted = {
		"ticket_type": decision.ticket_type,
		"agent_group": decision.agent_group,
		"priority": decision.priority,
	}
	reasons = {note["field"]: note["reason"] for note in decision.notes if note["field"] in wanted}
	return _existing_values(wanted, reasons)


def set_classification(args: dict, ctx: ToolContext) -> dict:
	doc = frappe.get_doc(TICKET_DOCTYPE, ctx.ticket_name)
	if not doc.has_permission("write"):
		return _fail("thiếu quyền ghi phiếu")
	if doc.get("ai_classified_by") == CLASSIFIED_BY_HUMAN:
		return _fail("người đã phân loại, không ghi đè")
	values, skipped = _mapped_values(doc, args, ctx)
	if not values:
		return {"ok": True, "before": {}, "after": {}, "skipped": skipped}
	values["ai_confidence"] = args["confidence"]
	for field in (*values, "ai_classified_by", "ai_updated_at"):
		if not doc.has_permlevel_access_to(field, permission_type="write"):
			return _fail(f"thiếu quyền ghi trường {field}")
	before = {field: doc.get(field) for field in values}
	doc.update(values)
	doc.ai_classified_by = CLASSIFIED_BY_AI
	doc.ai_updated_at = now_datetime()
	doc.save()
	return {"ok": True, "before": before, "after": dict(values), "skipped": skipped}


def set_resolution_hint(args: dict, ctx: ToolContext) -> dict:
	doc = frappe.get_doc(TICKET_DOCTYPE, ctx.ticket_name)
	if not doc.has_permission("write"):
		return _fail("thiếu quyền ghi phiếu")
	if not doc.has_permlevel_access_to(HINT_FIELD, permission_type="write"):
		return _fail(f"thiếu quyền ghi trường {HINT_FIELD}")
	before = doc.get(HINT_FIELD)
	doc.set(HINT_FIELD, args["text"])
	doc.save()
	# Frappe sanitizes Text Editor values on save: report what was stored, not the raw input.
	return {"ok": True, "before": before, "after": doc.get(HINT_FIELD)}


def _post(ticket_name: str, content: str) -> dict:
	"""The one posting body: a core Comment on the ticket under the session user's permissions."""
	doc = frappe.get_doc(TICKET_DOCTYPE, ticket_name)
	if not doc.has_permission("read"):
		return _fail("thiếu quyền đọc phiếu")
	if not frappe.has_permission("Comment", "create"):
		return _fail("thiếu quyền tạo comment")
	try:
		name = doc.new_comment(content)
	except frappe.PermissionError:
		return _fail("không được phép thêm comment vào phiếu")
	return {"ok": True, "comment": name}


def post_comment(args: dict, ctx: ToolContext) -> dict:
	"""Post `args["content"]` as is, no kind check: for code callers (route_ticket); the model's text never comes here."""
	return _post(ctx.ticket_name, args["content"])


def section_text(content: str, header: str) -> str | None:
	"""The text of the `**<header>:**` section (the `**` may be left out), stripped: the rest of its heading line and
	the lines after it up to the next line opening with `**…:**`. No line opens with that heading → None."""
	heading = re.compile(rf"^[ \t]*(?:\*\*)?{re.escape(header)}:(?:\*\*)?", re.M).search(content)
	if heading is None:
		return None
	end = _NEXT_HEADING.search(content, heading.end())
	return content[heading.end() : end.start() if end else len(content)].strip()


def asked_in_run(run_id: str) -> bool:
	return run_id in frappe.flags.get(_ASKED_RUNS_FLAG, set())


def mark_asked(run_id: str) -> None:
	"""Record that the run asked its one question (comment, ask_fallback or an emailed question: Fix 9)."""
	if not run_id:
		raise ValueError("run_id rỗng")
	frappe.flags.setdefault(_ASKED_RUNS_FLAG, set()).add(run_id)


def _ask_footer(ticket_name: str) -> str:
	pct = policy.latest_classification(ticket_name)[1]
	return ASK_FOOTER.format(
		pct=_PCT_UNKNOWN if pct is None else f"{pct}%",
		threshold=policy.confidence_threshold(frappe.get_single(SETTING_DOCTYPE)),
	)


def _ask_below_threshold(kind: str, content: str, ctx: ToolContext) -> dict:
	"""Step (2): one question per run, with grounds; the footer states the confidence and the threshold."""
	if kind != "hoi":
		return _fail(REASON_ASK_ONLY)
	if asked_in_run(ctx.run_id):
		return _fail(REASON_ONE_ASK)
	if not section_text(content, EVIDENCE_HEADER):
		return _fail(REASON_NO_EVIDENCE)
	result = _post(ctx.ticket_name, f"{content}\n\n{_ask_footer(ctx.ticket_name)}")
	if result["ok"]:
		mark_asked(ctx.run_id)
	return result


def _proposal_refusal(content: str) -> dict | None:
	"""Step (3): a kind=de_xuat comment needs a 'Độ tin cậy: NN%' line (NN at most 100) and non-empty grounds."""
	confidence = CONFIDENCE_LINE.search(content)
	if confidence is None or int(confidence.group(1)) > CONFIDENCE_PCT_MAX:
		return _fail(REASON_NO_CONFIDENCE)
	if not section_text(content, EVIDENCE_HEADER):
		return _fail(REASON_NO_EVIDENCE)
	return None


def _agent_comment_filters(ticket_name: str) -> dict:
	"""The ticket's core `Comment` rows written by the agent account (an `Info` row is no comment)."""
	return {
		"reference_doctype": TICKET_DOCTYPE,
		"reference_name": ticket_name,
		"comment_type": "Comment",
		"owner": AGENT_USER,
	}


def post_notice(ticket_name: str, notice: str, body: str, since: datetime) -> dict:
	"""Post the `notice` status comment unless the agent posted one of that kind on the ticket since `since`
	(AC-23, NFR-3, w1.md:97). The dedup read is locked_count's (ticket lock, then a locking read); no lock of its own.
	"""
	if notice not in NOTICE_PREFIXES:
		raise ValueError(f"notice lạ: {notice}")
	prefix = NOTICE_PREFIXES[notice]
	filters = {
		**_agent_comment_filters(ticket_name),
		"creation": [">=", since],
		"content": ["like", f"{prefix}%"],
	}
	if locked_count(ticket_name, "Comment", filters):
		return _fail(REASON_NOTICE_SENT)
	return _post(ticket_name, f"{prefix} {body}")


def post_comment_tool(args: dict, ctx: ToolContext) -> dict:
	"""Handler of the post_comment tool (AC-22, U4b.md:171): checks the kind's rules, then posts; a refusal posts nothing."""
	kind, content = args.get("kind"), args["content"]
	if kind not in COMMENT_KINDS:
		return _fail(_REASON_BAD_KIND)
	if ctx.below_threshold:
		return _ask_below_threshold(kind, content, ctx)
	if kind == "de_xuat" and (refusal := _proposal_refusal(content)):
		return refusal
	# Step (4): a question above the threshold needs nothing more.
	return _post(ctx.ticket_name, content)


def _ticket_link_html(name: str) -> str:
	"""The clickable ticket paragraph that opens a Task description (Text Editor, HTML)."""
	path = f"/helpdesk/tickets/{name}"
	return f'<p>Phiếu {escape_html(name)}: <a href="{escape_html(path)}">{escape_html(path)}</a></p>'


def _task_refusal(ctx: ToolContext) -> dict | None:
	"""`ok=false` result when a Task cannot be created for the ticket, else None."""
	if not frappe.db.exists("DocType", TASK_DOCTYPE):
		return _fail("hệ thống không có DocType Task")
	if not frappe.get_doc(TICKET_DOCTYPE, ctx.ticket_name).has_permission("read"):
		return _fail("thiếu quyền đọc phiếu")
	if not frappe.has_permission(TASK_DOCTYPE, "create"):
		return _fail("thiếu quyền tạo Task")
	return None


def create_task(args: dict, ctx: ToolContext) -> dict:
	if not ctx.instructor:
		return _fail("không có người ra lệnh")
	if refusal := _task_refusal(ctx):
		return refusal
	link = _ticket_link_html(ctx.ticket_name)
	text = escape_html(args["description"]).replace("\r\n", "\n").replace("\n", "<br>")
	task = frappe.get_doc(
		{
			"doctype": TASK_DOCTYPE,
			"subject": args["subject"],
			"ai_ticket": ctx.ticket_name,
			"description": f"{link}\n<p>{text}</p>",
		}
	)
	task.insert()
	return {"ok": True, "task": task.name}


TOOLS: list[ToolSpec] = [
	ToolSpec(
		name="set_classification",
		group="ticket_write",
		schema={
			"name": "set_classification",
			"description": (
				"Ghi phân loại của phiếu hiện tại theo đầu mục A-F và độ tin cậy. "
				"Loại, nhóm và mức ưu tiên lấy từ ánh xạ đầu mục, không nhận tên trường."
			),
			"input_schema": {
				"type": "object",
				"properties": {
					"category": {"type": "string", "enum": list(CATEGORIES)},
					"confidence": {"type": "string", "enum": list(CONFIDENCE_VALUES)},
				},
				"required": ["category", "confidence"],
			},
		},
		handler=set_classification,
	),
	ToolSpec(
		name="set_resolution_hint",
		group="ticket_write",
		schema={
			"name": "set_resolution_hint",
			"description": "Ghi hướng giải quyết gợi ý cho phiếu hiện tại.",
			"input_schema": {
				"type": "object",
				"properties": {"text": {"type": "string", "minLength": 1, "maxLength": 5000}},
				"required": ["text"],
			},
		},
		handler=set_resolution_hint,
	),
	ToolSpec(
		name="post_comment",
		group="ticket_write",
		schema={
			"name": "post_comment",
			"description": (
				"Đăng một comment lên phiếu hiện tại. "
				"kind=de_xuat: nhận định, phương án hoặc báo việc đã làm; phải có dòng 'Độ tin cậy: NN%' "
				f"và phần '**{EVIDENCE_HEADER}:**' có nội dung. "
				"kind=hoi: câu hỏi; khi độ tin cậy dưới ngưỡng chỉ được dùng kind này, một lần, "
				f"và vẫn phải có '**{EVIDENCE_HEADER}:**' nêu vì sao chưa chắc."
			),
			"input_schema": {
				"type": "object",
				"properties": {
					"content": {"type": "string", "minLength": 1, "maxLength": 5000},
					"kind": {"type": "string", "enum": list(COMMENT_KINDS)},
				},
				"required": ["content", "kind"],
			},
		},
		handler=post_comment_tool,
	),
	ToolSpec(
		name="create_task",
		group="task_write",
		schema={
			"name": "create_task",
			"description": "Tạo một Task cho phiếu hiện tại; chỉ dùng khi có người ra lệnh.",
			"input_schema": {
				"type": "object",
				"properties": {
					"subject": {"type": "string", "minLength": 1, "maxLength": 140},
					"description": {"type": "string", "minLength": 1, "maxLength": 5000},
				},
				"required": ["subject", "description"],
			},
		},
		handler=create_task,
	),
]
