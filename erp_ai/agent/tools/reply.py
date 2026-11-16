"""`reply_to_requester` (FEAT-007 U6b, AC-40; ADR-034 QĐ 7 and Ràng buộc): answer or ask the requester by email.

Group `requester_reply`. The one recipient is `raised_by` of `ctx.ticket_name`: the tool takes no recipient and
no ticket. The message goes through `lifecycle.send_to_requester` (a Communication Sent, its email queued), never
as a comment, also when sending fails. An emailed question is the run's one ask (E-1, `w1b-r2.md:75`): the mark
is read and written only through `write_ticket.asked_in_run` / `mark_asked`.
"""

import html

import frappe

from erp_ai.agent import lifecycle, policy
from erp_ai.agent.redact import redact_secrets
from erp_ai.agent.tools import read, write_ticket
from erp_ai.agent.tools.read import _schema
from erp_ai.agent.tools.registry import ToolContext, ToolSpec
from erp_ai.constants import LOGGER_NAME

REPLY_KINDS = ("answer", "question")
KIND_ANSWER, KIND_QUESTION = REPLY_KINDS
REPLY_MAX_CHARS = 4000
SOURCES_MAX = 5
SOURCE_MAX_CHARS = 200
SOURCES_LABEL = "Nguồn: "
REASON_NO_REQUESTER = "phiếu không có người tạo để trả lời"
REASON_BELOW_THRESHOLD = "độ tin cậy dưới ngưỡng: chỉ được hỏi lại"
REASON_QUESTION_MARK = "câu hỏi lại phải có dấu ?"
REASON_F_NEEDS_SOURCE = (
	"đầu mục F: trả lời phải nêu ít nhất một nguồn (bài CSKT, mục HDSD hoặc số phiếu cũ); "
	"không có nguồn thì hỏi lại"
)
REASON_NOT_SENT = "chưa gửi được: site chưa có tài khoản email gửi đi"
SAVEPOINT = "erp_ai_reply"


def _refuse(reason: str) -> dict:
	return {"ok": False, "reason": reason}


def _paragraph(text: str) -> str:
	"""One masked, escaped paragraph. Masked first (R17a): escaped first, a value starting with `<` would start
	with `&lt;`, which no masking rule reads as a value; the mask has no HTML character. Masked before the line
	breaks become `<br>`, so a value on the line after its key is still caught. Quotes stay (text, not an
	attribute)."""
	return "<p>" + "<br>".join(html.escape(redact_secrets(text), quote=False).splitlines()) + "</p>"


def _content(message: str, kind: str, sources: list) -> str:
	content = _paragraph(message)
	if kind == KIND_ANSWER and sources:
		content += _paragraph(SOURCES_LABEL + ", ".join(sources))
	return content


def _refusal(ticket: str, raised_by, message: str, kind, sources: list, ctx: ToolContext) -> dict | None:
	"""Checks 2-5 of `U6b.md:193-200`, then the one ask of the run (E-1); the first that fails, else None."""
	if not (raised_by or "").strip():
		return _refuse(REASON_NO_REQUESTER)
	if ctx.below_threshold and kind != KIND_QUESTION:
		return _refuse(REASON_BELOW_THRESHOLD)
	if kind == KIND_QUESTION and "?" not in message:
		return _refuse(REASON_QUESTION_MARK)
	if (
		policy.latest_classification(ticket)[0] == lifecycle.CATEGORY_F
		and kind == KIND_ANSWER
		and not sources
	):
		return _refuse(REASON_F_NEEDS_SOURCE)
	if kind == KIND_QUESTION and write_ticket.asked_in_run(ctx.run_id):
		return _refuse(write_ticket.REASON_ONE_ASK)
	return None


def reply_to_requester(args: dict, ctx: ToolContext) -> dict:
	"""AC-40: send `message` to the requester of the ticket being handled; `{"ok": True, "communication": name}`.

	A send that fails with a validation error (an outgoing Email Account missing, the email refused) undoes the
	Communication in this tool's savepoint and is refused with REASON_NOT_SENT and one warning line; no comment
	stands in for it (ADR-034 QĐ 7).
	"""
	args = args if isinstance(args, dict) else {}
	ticket = ctx.ticket_name
	refusal = read._check_ticket(ticket)
	if refusal:
		return refusal
	message, kind, sources = args.get("message") or "", args.get("kind"), args.get("sources") or []
	raised_by = frappe.db.get_value("HD Ticket", ticket, "raised_by")
	refusal = _refusal(ticket, raised_by, message, kind, sources, ctx)
	if refusal:
		return refusal
	frappe.db.savepoint(SAVEPOINT)
	try:
		communication = lifecycle.send_to_requester(ticket, _content(message, kind, sources))
	except (frappe.ValidationError, frappe.OutgoingEmailError) as exc:
		frappe.db.rollback(save_point=SAVEPOINT)
		frappe.logger(LOGGER_NAME).warning(
			"reply_to_requester not sent ticket=%s error=%s", ticket, type(exc).__name__
		)
		return _refuse(REASON_NOT_SENT)
	frappe.db.release_savepoint(SAVEPOINT)
	if kind == KIND_QUESTION:
		write_ticket.mark_asked(ctx.run_id)
	return {"ok": True, "communication": communication}


TOOLS = [
	ToolSpec(
		"reply_to_requester",
		"requester_reply",
		_schema(
			"reply_to_requester",
			"Gửi email cho người tạo phiếu đang xử lý (chỉ người tạo, không gửi người khác). kind=answer để trả "
			"lời, kind=question để hỏi lại (phải có dấu ?). Trả lời phiếu đầu mục F phải nêu nguồn ở sources.",
			{
				"message": {"type": "string", "minLength": 1, "maxLength": REPLY_MAX_CHARS},
				"kind": {"type": "string", "enum": list(REPLY_KINDS)},
				"sources": {
					"type": "array",
					"maxItems": SOURCES_MAX,
					"items": {"type": "string", "minLength": 1, "maxLength": SOURCE_MAX_CHARS},
					"description": "Nguồn đã dùng: tên bài CSKT, tên tài liệu HDSD hoặc số phiếu cũ.",
				},
			},
			["message", "kind"],
		),
		reply_to_requester,
	)
]
