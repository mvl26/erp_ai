"""Entry point of the Duyệt / Từ chối links in the bot's ticket comment: one click decides the proposal.

The link only carries the decision; the role and state checks are the same ones the proposal form uses.
"""

import frappe
from frappe import _

from erp_ai.agent import change_link
from erp_ai.constants import PROPOSAL_DOCTYPE
from erp_ai.erp_ai_agent.doctype.erp_ai_change_proposal import erp_ai_change_proposal as proposal_form

PAGE_TITLE = "Đề xuất thay đổi của ERP AI"
BAD_LINK = "Đường dẫn duyệt không hợp lệ hoặc đã bị sửa."
DECIDERS = {
	change_link.ACTION_APPROVE: proposal_form.approve,
	change_link.ACTION_REJECT: proposal_form.reject,
}


def _refuse(message: str) -> None:
	frappe.respond_as_web_page(_(PAGE_TITLE), frappe.utils.escape_html(message), indicator_color="red")


@frappe.whitelist(methods=["GET"])
def decide(name=None, action=None, _signature=None) -> None:
	"""Approve or reject proposal `name` for the signed link the session user opened, then return to the ticket."""
	if action not in DECIDERS or not change_link.signature_ok(name, action, _signature):
		_refuse(BAD_LINK)
		return
	try:
		DECIDERS[action](name)
	except (frappe.PermissionError, frappe.ValidationError) as exc:
		frappe.clear_messages()
		_refuse(frappe.utils.strip_html(str(exc)))
		return
	ticket = frappe.db.get_value(PROPOSAL_DOCTYPE, name, "ticket")
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = f"/helpdesk/tickets/{ticket}"
