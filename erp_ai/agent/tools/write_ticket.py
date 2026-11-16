import dataclasses
import html
import json
import math
import re
import unicodedata
from datetime import datetime
from decimal import Decimal

import frappe
from frappe.utils import escape_html, now_datetime

from erp_ai.agent import policy, site_facts
from erp_ai.agent.classification import CONFIDENCE_PCT_MAX, Classification
from erp_ai.agent.messages import add_message
from erp_ai.agent.ops_data import BA_NOTE_MARKER
from erp_ai.agent.routing import RouteDecision, decide_route
from erp_ai.agent.tools.registry import ToolContext, ToolSpec
from erp_ai.constants import (
	AGENT_USER,
	CATEGORIES,
	CLASSIFICATION_FIELDS,
	CLASSIFIED_BY_AI,
	CLASSIFIED_BY_HUMAN,
	CONFIDENCE_VALUES,
	LEVELS,
	LOGGER_NAME,
	MESSAGE_DOCTYPE,
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
# ADR-019 Amendment 1: the reasoning step corrects the complexity the classify step guessed, always with its reason.
COMPLEXITY_FIELD = "ai_complexity"
SCORE_REASON_FIELD = "ai_score_reason"
COMPLEXITY_VALUES = (1, 2, 3)
COMPLEXITY_REASON_MAX = 300
REASON_COMPLEXITY_NO_REASON = "độ phức tạp mới cần lý do (complexity_reason)"
# The kinds of the post_comment tool (AC-22, U4b.md:126-133); U8 appends "ba_note" (AC-62).
COMMENT_KINDS = ("de_xuat", "hoi", "ba_note")
CONFIDENCE_LINE = re.compile(r"Độ tin cậy:\s*(\d{1,3})\s*%")
EVIDENCE_HEADER = "Căn cứ"
ASK_FOOTER = "Độ tin cậy phân loại: {pct} (ngưỡng {threshold}%). Bot chỉ hỏi, chưa ghi gì trên phiếu."
REASON_NO_CONFIDENCE = "comment đề xuất thiếu dòng 'Độ tin cậy: NN%' (NN từ 0 đến 100)"
REASON_NO_EVIDENCE = f"comment thiếu phần '**{EVIDENCE_HEADER}:**' có nội dung"
REASON_ASK_ONLY = "độ tin cậy dưới ngưỡng: chỉ được đăng comment hỏi (kind = hoi)"
REASON_ONE_ASK = "đã đăng comment hỏi trong lần chạy này"
# The BA note (AC-62, U4b.md:152-156, U4b-fixes Fix 3): five non-empty parts, once per category C ticket, posted under
# ops_data.BA_NOTE_MARKER (the 08:00 report finds it by that marker).
BA_NOTE_CATEGORY = "C"
BA_NOTE_SECTIONS = ("Mục tiêu", "Phạm vi", "Tính năng sẵn có", "Rủi ro", "Câu hỏi mở")
BA_NOTE_FEATURE = BA_NOTE_SECTIONS[2]
BA_NOTE_SOURCE = "Nguồn"
REASON_BA_NOTE_MISSING = "BA note thiếu hoặc rỗng mục: {sections}"
REASON_BA_NOTE_FEATURE = "mục 'Tính năng sẵn có' phải bắt đầu bằng Có hoặc Không và có 'Nguồn:' không rỗng"
REASON_BA_NOTE_EXISTS = "phiếu đã có BA note"
REASON_BA_NOTE_NOT_C = "BA note chỉ dành cho phiếu đầu mục C ở mức L1 trở lên"
_FEATURE_ANSWER = re.compile(r"[*_\s]*(?:Có|Không)\b")
# "Nguồn:" inside a line of the feature part, followed by text on that line.
_INLINE_SOURCE = re.compile(rf"{BA_NOTE_SOURCE}:(?:\*\*)?[ \t]*[^\s*]")
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
# The guidance comment (ADR-036, w1.md:30-63): at most one per ticket, line 1 is the marker; defined here only.
_GUIDANCE_KEY = "erp_ai:huong-xu-ly"
GUIDANCE_MARKER = f"<!-- {_GUIDANCE_KEY} -->"
GUIDANCE_HEADER = "Hướng xử lý"
ANALYSIS_HEADER = "Nhận định"
# A run a message started whose answer the guidance comment took still answers in the conversation (CHG-003
# Amendment 3): the finding of its analysis, then where the rest is. Plain text: the panel only sets text.
GUIDANCE_REPLY = (
	"Bot đã viết hướng xử lý cho phiếu: nhận định đầy đủ, việc đã làm, đề xuất chờ duyệt và việc cần người làm nằm ở "
	'mục "Thông tin AI của phiếu" phía trên và ở comment hướng xử lý của phiếu.'
)
SECTION_DONE, SECTION_PENDING = "Đã làm", "Chờ duyệt"
# Collector key of "work a person must do by hand, with the reason": shown inside the plan section, no heading of
# its own (design-w1-fixes-20 Điểm 1.1, spec-addendum-5 AC-65 (a)).
SECTION_DECIDE = GUIDANCE_HEADER
GUIDANCE_SECTIONS = (SECTION_DONE, SECTION_PENDING, SECTION_DECIDE)
# What a run concluded and did, copied onto the ticket so the ticket itself carries it. Information only:
# whether a ticket has its guidance is still read from the comment (ADR-036 QĐ 6).
CLASSIFICATION_REASON_FIELD = "ai_classification_reason"
ANALYSIS_FIELD = "ai_analysis"
SECTION_FIELDS = {"ai_done": SECTION_DONE, "ai_pending": SECTION_PENDING, "ai_manual": SECTION_DECIDE}
RUN_INFO_FIELDS = (ANALYSIS_FIELD, *SECTION_FIELDS)
RUN_INFO_SAVEPOINT = "erp_ai_run_info"
# Per-job state, like the asked runs: run_id -> {"analysis": str | None, <section>: [raw lines]}.
_GUIDANCE_FLAG = "erp_ai_guidance"
_ANALYSIS_KEY = "analysis"
# Runs on a ticket that already has its guidance comment.
_WORK_ONLY_FLAG = "erp_ai_work_only_runs"
# The body when the model wrote no analysis (design-w1-fixes-20 Điểm 1.3): the plan line is last, so the work left
# to a person lands right under it.
GUIDANCE_FALLBACK = (
	"**Nhận định:** bot chưa viết được nhận định cho phiếu này.\n"
	f"**{GUIDANCE_HEADER}:** người phụ trách làm các việc ghi ngay dưới (nếu có); việc bot đã làm và đề xuất chờ "
	"duyệt nằm ở các mục cuối comment; cần bot làm tiếp thì nhắc @ai."
)
# Once per comment, in the heading paragraph of the pending section (design-w1-fixes-20 Điểm 2.1); a trusted constant.
PENDING_NOTE = (
	'Nút "Duyệt ngay" nằm ở ngăn "Trao đổi với bot" của phiếu; đề xuất không có nút thì duyệt ở form đề xuất.'
)
# The run_failed notice names done, pending and manual lines apart (design-w1-fixes-20 Điểm 3.1).
FAILURE_DONE = "Trước khi lỗi, bot đã làm: "
FAILURE_PENDING = "Đề xuất đã tạo, đang chờ duyệt: "
FAILURE_MANUAL = "Việc người phải làm tay: "
REASON_GUIDANCE_EXISTS = "phiếu đã có hướng xử lý"
REASON_NO_CONTENT = "không có nội dung"
# The post_comment tool's refusals and hold around the guidance comment (w1.md:39-42, :96).
REASON_MARKER = "nội dung chứa dấu hiệu dành riêng cho comment hướng xử lý của hệ thống; bỏ dấu hiệu đó"
REASON_GUIDANCE_HEADER = (
	f"{REASON_GUIDANCE_EXISTS}: chỉ báo kết quả việc vừa làm, không viết mục '{GUIDANCE_HEADER}'"
)
HELD_NOTE = "đã giữ làm nhận định của comment hướng xử lý; bot đăng một lần ở cuối lần chạy"
REASON_SYSTEM_SECTION = (
	f"mục '{SECTION_DONE}' và '{SECTION_PENDING}' do hệ thống tự viết; bỏ dòng mở đầu bằng tiêu đề đó"
)
# The done line of a classification written in a guidance run (U4b.md:210, :215; the runner imports them).
ROUTE_DONE = "Bot đã phân loại phiếu: {fields}."
FIELD_LABELS = {"ticket_type": "Loại", "agent_group": "Nhóm", "priority": "Ưu tiên"}
# create_task (AC-63, U4b.md:157-161): an hour estimate on every Task, at most a configured number per run.
DEFAULT_MAX_TASKS_PER_RUN = 10
REASON_NO_ESTIMATE = "Task cần ước lượng bằng giờ, số dương"
REASON_TASK_LIMIT = "đã tạo đủ {limit} Task trong lần chạy này"
REASON_TASK_DUPLICATE = "phiếu đã có Task cùng tiêu đề: {task}"
# The done line of a Task created in a guidance run (U8-1, w1.md:120).
TASK_DONE = "Đã tạo Task {task} ({hours} giờ)."
# Per-job state, like the asked runs: run_id -> the number of Tasks the run created.
_RUN_TASKS_FLAG = "erp_ai_run_tasks"
# The plan section ends at the next line opening a `**…:**` heading or the confidence line (Điểm 1.2 bước 2); so does
# each part of a BA note, the confidence line being no part's content.
_PLAN_END = re.compile(r"^[ \t]*(?:\*\*[^*\n]+:\*\*|Độ tin cậy:)", re.M)


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
	scores = _scores(args)
	if scores is None:
		return _fail(REASON_COMPLEXITY_NO_REASON)
	values, skipped = _mapped_values(doc, args, ctx)
	if not values and not scores:
		return {"ok": True, "before": {}, "after": {}, "skipped": skipped}
	if values:
		values["ai_confidence"] = args["confidence"]
		# The tool takes no classification reason: one left by an earlier classification would describe the wrong one.
		if doc.get(CLASSIFICATION_REASON_FIELD):
			values[CLASSIFICATION_REASON_FIELD] = ""
	values.update(scores)
	for field in (*values, "ai_classified_by", "ai_updated_at"):
		if not doc.has_permlevel_access_to(field, permission_type="write"):
			return _fail(f"thiếu quyền ghi trường {field}")
	before = {field: doc.get(field) for field in values}
	doc.update(values)
	doc.ai_classified_by = CLASSIFIED_BY_AI
	doc.ai_updated_at = now_datetime()
	doc.save()
	# In a guidance run the write is a line of "Đã làm", not a comment (U4b-8, AC-66 (a)).
	fields = ", ".join(
		f"{FIELD_LABELS[field]} {value}" for field, value in values.items() if field in FIELD_LABELS
	)
	if fields:
		collect(ctx.run_id, SECTION_DONE, ROUTE_DONE.format(fields=fields))
	return {"ok": True, "before": before, "after": dict(values), "skipped": skipped}


def _scores(args: dict) -> dict | None:
	"""The complexity the model found while working and its reason, as ticket values; {} when it gave none; None
	when it gave a complexity without a reason."""
	if args.get("complexity") is None:
		return {}
	reason = (args.get("complexity_reason") or "").strip()
	if not reason:
		return None
	return {COMPLEXITY_FIELD: args["complexity"], SCORE_REASON_FIELD: reason}


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


def _post_message(content: str, ctx: ToolContext) -> dict:
	"""One message of the bot in the ticket's conversation, as written, under the session user's permissions."""
	if not content.strip():
		return _fail(REASON_NO_CONTENT)
	if not frappe.get_doc(TICKET_DOCTYPE, ctx.ticket_name).has_permission("read"):
		return _fail("thiếu quyền đọc phiếu")
	try:
		name = add_message(ctx.ticket_name, content, run_id=ctx.run_id)
	except frappe.PermissionError:
		return _fail("không được phép thêm tin vào ngăn trao đổi")
	return {"ok": True, "message": name}


def _heading_line(header: str) -> re.Pattern:
	"""A line opening with the `<header>:` heading, the `**` around it optional (U4b.md:168)."""
	return re.compile(rf"^[ \t]*(?:\*\*)?{re.escape(header)}:(?:\*\*)?", re.M)


_BLOCK_TAG = re.compile(r"<\s*/?\s*(?:p|br|div|li|ul|ol|h[1-6]|tr|blockquote|pre)\b[^>]*>", re.I)
_ANY_TAG = re.compile(r"<[^>]*>")
_SYSTEM_WORDS = tuple(
	unicodedata.normalize("NFC", word).casefold() for word in (SECTION_DONE, SECTION_PENDING)
)


def _normalised_lines(text: str):
	"""Each line of `text` as a reader sees it: block tags end a line, other tags go, entities are unescaped, no-break
	and zero-width characters become spaces or vanish, emphasis marks (`*`, `_`, `#`) go, spaces collapse, NFC, casefold."""
	text = _BLOCK_TAG.sub("\n", text)
	text = html.unescape(_ANY_TAG.sub("", text))
	text = "".join(ch for ch in text if unicodedata.category(ch) != "Cf")
	for line in text.split("\n"):
		line = re.sub(r"[*_#]", "", line)
		yield re.sub(r"\s+", " ", unicodedata.normalize("NFC", line)).strip().casefold()


def opens_system_section(text: str) -> bool:
	"""True when a line of `text` is, once normalised, "Đã làm" or "Chờ duyệt" alone or followed by a colon; the
	words in the middle of a sentence do not count (C8-fix1 R13c)."""
	return any(
		line == word or line.startswith((f"{word}:", f"{word} :"))
		for line in _normalised_lines(text)
		for word in _SYSTEM_WORDS
	)


def section_text(content: str, header: str, end: re.Pattern = _NEXT_HEADING) -> str | None:
	"""The text of the `**<header>:**` section (the `**` may be left out), stripped: the rest of its heading line and
	the lines after it up to the next line `end` finds, by default one opening with `**…:**`. No line opens with that
	heading → None."""
	heading = _heading_line(header).search(content)
	if heading is None:
		return None
	stop = end.search(content, heading.end())
	return content[heading.end() : stop.start() if stop else len(content)].strip()


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
	result = _post_message(f"{content}\n\n{_ask_footer(ctx.ticket_name)}", ctx)
	if result["ok"]:
		mark_asked(ctx.run_id)
	return result


def _confidence_refusal(content: str) -> dict | None:
	"""Step (3): a kind=de_xuat comment needs a 'Độ tin cậy: NN%' line, NN at most 100."""
	confidence = CONFIDENCE_LINE.search(content)
	if confidence is None or int(confidence.group(1)) > CONFIDENCE_PCT_MAX:
		return _fail(REASON_NO_CONFIDENCE)
	return None


def _hold_or_refuse(content: str, ctx: ToolContext) -> dict | None:
	"""Steps (3c), (3d) of a kind=de_xuat comment (design-w1-fixes-20 Điểm 1.4): in a guidance run it is held as the
	analysis of the guidance comment, no grounds needed; outside one it needs non-empty grounds (AC-22)."""
	if collecting(ctx.run_id):
		hold_analysis(ctx.run_id, content)
		return {"ok": True, "held": True, "note": HELD_NOTE}
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


def guidance_filters(ticket_name: str) -> dict:
	"""The agent's guidance comment of the ticket: the marker at position 0, so the model's text inside another
	comment never counts; an `Info` row never counts (ADR-036 QĐ 3)."""
	return {**_agent_comment_filters(ticket_name), "content": ["like", f"{GUIDANCE_MARKER}%"]}


def count_guidance(ticket_name: str, *, lock: bool = False) -> int:
	"""The one count of the ticket's guidance comments (ADR-036 QĐ 3): lock=True locks the ticket and reads with a lock."""
	if lock:
		return locked_count(ticket_name, "Comment", guidance_filters(ticket_name))
	return frappe.db.count("Comment", guidance_filters(ticket_name))


def open_collector(run_id: str) -> None:
	"""Start the run's guidance collector: no analysis yet, every section empty."""
	frappe.flags.setdefault(_GUIDANCE_FLAG, {})[run_id] = {
		_ANALYSIS_KEY: None,
		**{section: [] for section in GUIDANCE_SECTIONS},
	}


def collecting(run_id: str) -> bool:
	return run_id in frappe.flags.get(_GUIDANCE_FLAG, {})


def collect(run_id: str, section: str, line: str) -> None:
	"""Add `line` (raw text, no HTML) to `section` of the run's collector; no open collector → nothing; the same
	(section, line) pair twice → kept once (AD3.md:127). A section outside GUIDANCE_SECTIONS → ValueError."""
	if section not in GUIDANCE_SECTIONS:
		raise ValueError(f"mục lạ: {section}")
	if not collecting(run_id):
		return
	lines = frappe.flags.get(_GUIDANCE_FLAG)[run_id][section]
	if line not in lines:
		lines.append(line)


def hold_analysis(run_id: str, content: str) -> None:
	"""Keep the model's analysis for the guidance comment; a later hold replaces an earlier one; no collector → nothing."""
	if collecting(run_id):
		frappe.flags.get(_GUIDANCE_FLAG)[run_id][_ANALYSIS_KEY] = content


def collected(run_id: str) -> tuple[str | None, dict[str, list[str]]]:
	"""(analysis, {section: lines}) of the run's collector, as copies; no collector → (None, every section empty)."""
	collector = frappe.flags.get(_GUIDANCE_FLAG, {}).get(run_id, {})
	return collector.get(_ANALYSIS_KEY), {
		section: list(collector.get(section, ())) for section in GUIDANCE_SECTIONS
	}


def close_collector(run_id: str) -> None:
	frappe.flags.get(_GUIDANCE_FLAG, {}).pop(run_id, None)


def mark_work_only(run_id: str) -> None:
	"""Record a run on a ticket that already has its guidance comment (ADR-036 QĐ 7)."""
	frappe.flags.setdefault(_WORK_ONLY_FLAG, set()).add(run_id)


def _plan_end(text: str) -> int | None:
	"""The end of the plan section of `text`: the index of the `\\n` before the first line after its heading line that
	opens a `**…:**` heading or the confidence line; no such line → len(text); no plan heading → None."""
	heading = _heading_line(GUIDANCE_HEADER).search(text)
	if heading is None:
		return None
	line_end = text.find("\n", heading.end())
	if line_end < 0:
		return len(text)
	stop = _PLAN_END.search(text, line_end + 1)
	return stop.start() - 1 if stop else len(text)


def _items(lines: list[str]) -> str:
	"""Collected raw lines as a list, each escaped exactly once (AD3-4)."""
	return "<ul>" + "".join(f"<li>{escape_html(line)}</li>" for line in lines) + "</ul>"


def _with_manual_lines(text: str, manual: list[str]) -> str:
	"""`text` with the work left to a person listed at the end of its plan section; no plan heading → the system adds
	exactly one (design-w1-fixes-20 Điểm 1.2 bước 2)."""
	if not manual:
		return text
	end = _plan_end(text)
	if end is None:
		return f"{text}\n<p><strong>{GUIDANCE_HEADER}:</strong></p>{_items(manual)}"
	return f"{text[:end]}\n{_items(manual)}{text[end:]}"


def _store_run_info(ticket_name: str, analysis: str | None, sections: dict[str, list[str]]) -> bool:
	"""Copy what the guidance comment says onto the ticket's own fields; returns whether it was stored.

	The fallback analysis is not stored: it only points at the comment. The comment stands either way:
	without the write right on a field nothing is stored, and a save that fails validation is undone
	back to the point before this copy.
	"""
	doc = frappe.get_doc(TICKET_DOCTYPE, ticket_name)
	values = {ANALYSIS_FIELD: analysis or ""}
	values.update({field: "\n".join(sections[section]) for field, section in SECTION_FIELDS.items()})
	if not doc.has_permission("write") or not all(
		doc.has_permlevel_access_to(field, permission_type="write") for field in values
	):
		frappe.logger(LOGGER_NAME).warning(f"erp_ai run_info not stored ticket={ticket_name} reason=no_write")
		return False
	doc.update(values)
	frappe.db.savepoint(RUN_INFO_SAVEPOINT)
	try:
		doc.save()
	except frappe.ValidationError as exc:
		frappe.db.rollback(save_point=RUN_INFO_SAVEPOINT)
		frappe.logger(LOGGER_NAME).warning(
			f"erp_ai run_info not stored ticket={ticket_name} reason={type(exc).__name__}"
		)
		return False
	return True


def post_guidance(ticket_name: str, run_id: str) -> dict:
	"""The one writer of the ticket's guidance comment (ADR-036 QĐ 1, 4); the runner calls it once, at the end of a
	guidance run; not a tool. Counted under the ticket lock, so a ticket has at most one. Body (design-w1-fixes-20
	Điểm 1.2): marker, the model's analysis as written (or the fallback) with the manual lines inside its plan
	section, then the done and the pending sections; an empty section does not show."""
	if count_guidance(ticket_name, lock=True):
		return _fail(REASON_GUIDANCE_EXISTS)
	analysis, sections = collected(run_id)
	if not analysis and not any(sections.values()):
		return _fail(REASON_NO_CONTENT)
	parts = [GUIDANCE_MARKER, _with_manual_lines(analysis or GUIDANCE_FALLBACK, sections[SECTION_DECIDE])]
	for section in (SECTION_DONE, SECTION_PENDING):
		if sections[section]:
			note = f" {PENDING_NOTE}" if section == SECTION_PENDING else ""
			parts.append(f"<p><strong>{section}:</strong>{note}</p>{_items(sections[section])}")
	result = _post(ticket_name, "\n".join(parts))
	if not result["ok"]:
		return result
	return {
		**result,
		"counts": {section: len(sections[section]) for section in GUIDANCE_SECTIONS},
		"stored": _store_run_info(ticket_name, analysis, sections),
	}


def post_guidance_reply(ctx: ToolContext) -> dict | None:
	"""The answer of a run a message started when the guidance comment took it (CHG-003 Amendment 3): one message with
	the finding of the run's held analysis, when it has one, and where the rest of the guidance is; the runner calls it
	right after `post_guidance`. A run nothing typed started, or one that already said something in the conversation
	→ None, nothing written."""
	if not ctx.in_conversation or frappe.db.exists(
		MESSAGE_DOCTYPE, {"ticket": ctx.ticket_name, "run_id": ctx.run_id}
	):
		return None
	analysis = collected(ctx.run_id)[0]
	finding = section_text(analysis, ANALYSIS_HEADER) if analysis else None
	return _post_message(
		f"{ANALYSIS_HEADER}: {finding}\n\n{GUIDANCE_REPLY}" if finding else GUIDANCE_REPLY, ctx
	)


def failure_summary(run_id: str) -> str:
	"""What the run did before it failed, for its run_failed notice (design-w1-fixes-20 Điểm 3.1): one part per
	non-empty section, done, pending and manual apart, each line escaped once; not collecting → ""."""
	if not collecting(run_id):
		return ""
	sections = collected(run_id)[1]
	return "\n".join(
		prefix + "; ".join(escape_html(line) for line in sections[section])
		for prefix, section in (
			(FAILURE_DONE, SECTION_DONE),
			(FAILURE_PENDING, SECTION_PENDING),
			(FAILURE_MANUAL, SECTION_DECIDE),
		)
		if sections[section]
	)


def _feature_part(content: str) -> str:
	"""The 'Tính năng sẵn có' part with its own `**Nguồn:**` line: from its heading to the next `**…:**` heading that
	is not 'Nguồn', or the confidence line; no such heading → ""."""
	heading = _heading_line(BA_NOTE_FEATURE).search(content)
	if heading is None:
		return ""
	source_heading = _heading_line(BA_NOTE_SOURCE)
	for following in _PLAN_END.finditer(content, heading.end()):
		if not source_heading.match(content, following.start()):
			return content[heading.end() : following.start()]
	return content[heading.end() :]


def _ba_note_refusal(content: str, ctx: ToolContext) -> dict | None:
	"""The checks of a kind=ba_note comment before its dedup (U4b-fixes Fix 3): the run's category and the main-path
	level the runner put in the context (no level is computed here), the confidence line, the five parts, then the
	feature answer and its source."""
	level = ctx.grant_inputs().main_path_level
	if policy.latest_classification(ctx.ticket_name)[0] != BA_NOTE_CATEGORY or level not in LEVELS[1:]:
		return _fail(REASON_BA_NOTE_NOT_C)
	if refusal := _confidence_refusal(content):
		return refusal
	missing = [section for section in BA_NOTE_SECTIONS if not section_text(content, section, _PLAN_END)]
	if missing:
		return _fail(REASON_BA_NOTE_MISSING.format(sections=", ".join(missing)))
	feature = _feature_part(content)
	has_source = section_text(feature, BA_NOTE_SOURCE) or _INLINE_SOURCE.search(feature)
	if not _FEATURE_ANSWER.match(section_text(content, BA_NOTE_FEATURE, _PLAN_END)) or not has_source:
		return _fail(REASON_BA_NOTE_FEATURE)
	return None


def _ba_note_filters(ticket_name: str) -> dict:
	"""The agent's BA note of the ticket: the marker at position 0; another person's note or an `Info` row never
	counts."""
	return {**_agent_comment_filters(ticket_name), "content": ["like", f"{BA_NOTE_MARKER}%"]}


def _ba_note_content(content: str) -> str:
	"""BA_NOTE_MARKER on line 1, then the note without a marker the model already wrote."""
	body = content.strip()
	if body.startswith(BA_NOTE_MARKER):
		body = body[len(BA_NOTE_MARKER) :].lstrip()
	return f"{BA_NOTE_MARKER}\n{body}"


def post_comment_tool(args: dict, ctx: ToolContext) -> dict:
	"""Handler of the post_comment tool (AC-22, U4b.md:171, w1.md:96): checks the steps in order, then posts; a
	refusal posts nothing, and in a guidance run a proposal is held for post_guidance instead. A question or a
	proposal is what the bot says to people: a message of the ticket's conversation, whatever started the run
	(CHG-003 Amendment 3); the BA note is ticket information, always a comment."""
	kind, content = args.get("kind"), args["content"]
	# Step (0): the marker is the writer's alone, whatever the kind, before any other check (AC-65 (d)).
	if _GUIDANCE_KEY in re.sub(r"\s+", "", content).lower():
		return _fail(REASON_MARKER)
	# Step (0b): "Đã làm" and "Chờ duyệt" are the system's, in every kind and in a held analysis (AC-66, AC-67).
	if opens_system_section(content):
		return _fail(REASON_SYSTEM_SECTION)
	if kind not in COMMENT_KINDS:
		return _fail(_REASON_BAD_KIND)
	if ctx.below_threshold:
		return _ask_below_threshold(kind, content, ctx)
	if kind == "de_xuat" and (refusal := _confidence_refusal(content)):
		return refusal
	# Step (3b): once the ticket has its guidance, a comment only reports the work just done (AC-65 (c)).
	if ctx.run_id in frappe.flags.get(_WORK_ONLY_FLAG, set()) and section_text(content, GUIDANCE_HEADER):
		return _fail(REASON_GUIDANCE_HEADER)
	# The BA note (AC-62, w1.md:121): once per ticket, the dedup read is locked_count's; posted on its own, also in a
	# guidance run, never held for the guidance comment.
	if kind == "ba_note":
		if refusal := _ba_note_refusal(content, ctx):
			return refusal
		if locked_count(ctx.ticket_name, "Comment", _ba_note_filters(ctx.ticket_name)):
			return _fail(REASON_BA_NOTE_EXISTS)
		return _post(ctx.ticket_name, _ba_note_content(content))
	if kind == "de_xuat" and (outcome := _hold_or_refuse(content, ctx)):
		return outcome
	# Steps (4), (5): a question above the threshold needs nothing more.
	return _post_message(content, ctx)


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


def _valid_estimate(hours) -> bool:
	"""A positive, finite number of hours; a bool is no number (U4b.md:174)."""
	return (
		isinstance(hours, int | float) and not isinstance(hours, bool) and math.isfinite(hours) and hours > 0
	)


def _hours_text(hours) -> str:
	"""The estimate of a done line as given, never with an exponent: a whole number without ".0" (w1.md:120)."""
	value = float(hours)
	return str(int(value)) if value.is_integer() else format(Decimal(repr(value)), "f")


def _max_tasks_per_run() -> int:
	return frappe.db.get_single_value(SETTING_DOCTYPE, "max_tasks_per_run") or DEFAULT_MAX_TASKS_PER_RUN


def create_task(args: dict, ctx: ToolContext) -> dict:
	"""AC-63 (U4b.md:174, w1.md:120): a Task of the ticket with its hour estimate, once per subject, at most
	`max_tasks_per_run` per run; in a guidance run it becomes a line of "Đã làm", never a comment."""
	if not ctx.instructor:
		return _fail("không có người ra lệnh")
	if refusal := _task_refusal(ctx):
		return refusal
	hours = args.get("expected_hours")
	if not _valid_estimate(hours):
		return _fail(REASON_NO_ESTIMATE)
	subject = args["subject"].strip()
	# AR3-7: the dedup read is locked_count's (ticket lock, then a locking read); the Task name is read after it, as a
	# locking read too, so it sees the same rows (w1.md:120).
	same_subject = {"ai_ticket": ctx.ticket_name, "subject": subject}
	if locked_count(ctx.ticket_name, TASK_DOCTYPE, same_subject):
		existing = locked_rows(ctx.ticket_name, TASK_DOCTYPE, same_subject)[0]["name"]
		return _fail(REASON_TASK_DUPLICATE.format(task=existing))
	created = frappe.flags.setdefault(_RUN_TASKS_FLAG, {})
	limit = _max_tasks_per_run()
	if created.get(ctx.run_id, 0) >= limit:
		return _fail(REASON_TASK_LIMIT.format(limit=limit))
	link = _ticket_link_html(ctx.ticket_name)
	text = escape_html(args["description"]).replace("\r\n", "\n").replace("\n", "<br>")
	task = frappe.get_doc(
		{
			"doctype": TASK_DOCTYPE,
			"subject": subject,
			"ai_ticket": ctx.ticket_name,
			"description": f"{link}\n<p>{text}</p>",
			"expected_time": float(hours),
		}
	)
	task.insert()
	created[ctx.run_id] = created.get(ctx.run_id, 0) + 1
	collect(ctx.run_id, SECTION_DONE, TASK_DONE.format(task=task.name, hours=_hours_text(hours)))
	return {"ok": True, "task": task.name}


TOOLS: list[ToolSpec] = [
	ToolSpec(
		name="set_classification",
		group="ticket_write",
		schema={
			"name": "set_classification",
			"description": (
				"Ghi phân loại của phiếu hiện tại theo đầu mục A-F và độ tin cậy. "
				"Loại, nhóm và mức ưu tiên lấy từ ánh xạ đầu mục, không nhận tên trường. "
				"complexity (1-3) và complexity_reason: độ phức tạp thật sau khi đã đọc code và dữ liệu, kèm lý do; "
				"bỏ trống thì giữ điểm cũ."
			),
			"input_schema": {
				"type": "object",
				"properties": {
					"category": {"type": "string", "enum": list(CATEGORIES)},
					"confidence": {"type": "string", "enum": list(CONFIDENCE_VALUES)},
					"complexity": {"type": "integer", "enum": list(COMPLEXITY_VALUES)},
					"complexity_reason": {"type": "string", "maxLength": COMPLEXITY_REASON_MAX},
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
				"Nói với người trên phiếu hiện tại: câu đề xuất và câu hỏi là tin trong ngăn 'Trao đổi với bot' "
				"của phiếu, BA note là comment của phiếu. "
				"kind=de_xuat: nhận định và phương án, hoặc báo việc đã làm; phải có dòng 'Độ tin cậy: NN%'. "
				"kind=hoi: câu hỏi; khi độ tin cậy dưới ngưỡng chỉ được dùng kind này, một lần, "
				f"và vẫn phải có '**{EVIDENCE_HEADER}:**' nêu vì sao chưa chắc. "
				"kind=ba_note: chỉ phiếu đầu mục C, một lần mỗi phiếu; đủ 5 mục **Mục tiêu:**, **Phạm vi:**, "
				"**Tính năng sẵn có:** (Có/Không, **Nguồn:**), **Rủi ro:**, **Câu hỏi mở:** "
				"và dòng 'Độ tin cậy: NN%'. "
				"Không tự liệt kê việc đã làm, đề xuất đang chờ hay việc hệ thống từ chối: "
				"hệ thống tự thêm chúng vào comment. "
				"Khi phiếu đã có hướng xử lý: chỉ báo kết quả việc vừa làm."
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
			"description": (
				"Tạo một Task cho phiếu hiện tại; chỉ dùng khi có người ra lệnh. "
				"Mỗi Task một việc, có ước lượng giờ; tiêu đề trùng Task đã có của phiếu bị từ chối; "
				"tối đa theo cấu hình mỗi lần chạy."
			),
			"input_schema": {
				"type": "object",
				"properties": {
					"subject": {"type": "string", "minLength": 1, "maxLength": 140},
					"description": {"type": "string", "minLength": 1, "maxLength": 5000},
					"expected_hours": {"type": "number", "exclusiveMinimum": 0},
				},
				"required": ["subject", "description", "expected_hours"],
			},
		},
		handler=create_task,
	),
]
