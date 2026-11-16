"""`create_kb_draft` (FEAT-007 U6b, AC-45; ADR-034 QĐ 6): one draft knowledge-base article per closed ticket.

Group `kb_draft`. The article is inserted under the session user (the agent account), without
`ignore_permissions`; `article_guard` refuses any status other than Draft for that account. Every piece of the
content is HTML-escaped, then masked (NFR-1, NFR-6).
"""

import html

import frappe

from erp_ai.agent.redact import redact_secrets
from erp_ai.agent.tools import read
from erp_ai.agent.tools.read import _schema
from erp_ai.agent.tools.registry import ToolContext, ToolSpec, _invalid

KB_TITLE_MAX = 140
TITLE_MIN_CHARS = 5
PROBLEM_MIN_CHARS, PROBLEM_MAX_CHARS = 20, 4000
STEPS_MIN, STEPS_MAX = 1, 20
STEP_MAX_CHARS = 1000
ARTICLE_DOCTYPE = "HD Article"
SOURCE_TICKET_FIELD = "ai_source_ticket"
DRAFT_STATUS = "Draft"
RESOLVED_CATEGORY = "Resolved"
REASON_NOT_CLOSED = "phiếu chưa đóng"
REASON_HAS_ARTICLE = "phiếu đã có bài CSKT"


def _refuse(reason: str) -> dict:
	return {"ok": False, "reason": reason}


def _html(text) -> str:
	"""Escaped then masked; masked before the line breaks become `<br>`, so a value on the next line is caught."""
	return "<br>".join(redact_secrets(html.escape(str(text), quote=False)).splitlines())


def _content(ticket: str, problem: str, steps: list) -> str:
	items = "".join(f"<li>{_html(step)}</li>" for step in steps)
	return (
		f"<h2>Vấn đề</h2><p>{_html(problem)}</p>"
		f"<h2>Các bước đã giải quyết</h2><ol>{items}</ol>"
		f"<p>Phiếu nguồn: #{_html(ticket)}</p>"
	)


def create_kb_draft(args: dict, ctx: ToolContext) -> dict:
	"""AC-45: a Draft HD Article linked to the ticket being handled, once it is closed and has no article yet;
	`{"ok": True, "article": name}`."""
	args = args if isinstance(args, dict) else {}
	steps = args.get("resolution_steps") or []
	if len(steps) < STEPS_MIN:
		# The registry checks maxItems only.
		return _invalid("resolution_steps")
	ticket = ctx.ticket_name
	refusal = read._check_ticket(ticket)
	if refusal:
		return refusal
	if frappe.db.get_value("HD Ticket", ticket, "status_category") != RESOLVED_CATEGORY:
		return _refuse(REASON_NOT_CLOSED)
	if frappe.db.exists(ARTICLE_DOCTYPE, {SOURCE_TICKET_FIELD: ticket}):
		return _refuse(REASON_HAS_ARTICLE)
	article = frappe.get_doc(
		{
			"doctype": ARTICLE_DOCTYPE,
			# A Data field, shown as text: masked, then cut to the field's length (a mask can be longer).
			"title": redact_secrets(args.get("title") or "")[:KB_TITLE_MAX],
			"content": _content(ticket, args.get("problem") or "", steps),
			"status": DRAFT_STATUS,
			SOURCE_TICKET_FIELD: ticket,
		}
	).insert()
	return {"ok": True, "article": article.name}


TOOLS = [
	ToolSpec(
		"create_kb_draft",
		"kb_draft",
		_schema(
			"create_kb_draft",
			"Soạn một bài CSKT nháp (HD Article, trạng thái Draft) từ phiếu đã đóng đang xử lý: tiêu đề, vấn đề "
			"và các bước đã giải quyết. Mỗi phiếu chỉ một bài; bot không xuất bản được bài.",
			{
				"title": {"type": "string", "minLength": TITLE_MIN_CHARS, "maxLength": KB_TITLE_MAX},
				"problem": {"type": "string", "minLength": PROBLEM_MIN_CHARS, "maxLength": PROBLEM_MAX_CHARS},
				"resolution_steps": {
					"type": "array",
					"minItems": STEPS_MIN,
					"maxItems": STEPS_MAX,
					"items": {"type": "string", "minLength": 1, "maxLength": STEP_MAX_CHARS},
				},
			},
			["title", "problem", "resolution_steps"],
		),
		create_kb_draft,
	)
]
