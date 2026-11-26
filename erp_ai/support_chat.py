"""Entry of the user-support chat in helpdesk's Miyano bot: checks who asks and what, then hands over to
agent/support.py. Like the panel, it never calls the model itself (ADR-001)."""

import json

import frappe
from frappe import _
from helpdesk.utils import is_agent

from erp_ai.agent import support


@frappe.whitelist(methods=["POST"])
def ask(question: str, history: str | list | None = None) -> dict:
	"""The bot's answer to `question`, after the earlier `history` turns (a list, or its JSON).

	Output: `{"answer", "articles": [{"name", "title"}], "answered"}`.
	Errors: PermissionError (not an active agent); ValidationError (blank question or over the length limit).
	"""
	if not is_agent():
		frappe.throw(_("Chỉ nhân viên hỗ trợ mới dùng được bot này."), frappe.PermissionError)
	question = question.strip() if isinstance(question, str) else ""
	if not question:
		frappe.throw(_("Hãy nhập câu hỏi."), frappe.ValidationError)
	if len(question) > support.MAX_QUESTION_CHARS:
		frappe.throw(
			_("Câu hỏi dài quá {0} ký tự.").format(support.MAX_QUESTION_CHARS), frappe.ValidationError
		)
	return support.answer(question, _turns(history))


def _turns(history) -> list:
	if isinstance(history, str):
		try:
			history = json.loads(history)
		except ValueError:
			return []
	return history if isinstance(history, list) else []
