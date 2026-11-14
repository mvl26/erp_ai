"""The decision behind the Duyệt / Từ chối links in the bot's ticket comment (ADR-023 QĐ 1, M1).

The signed link opens the proposal form; the form POSTs here once, with the session's CSRF token.
The link only carries the decision; the role and state checks are the same ones the form buttons use.
"""

import frappe
from frappe import _

from erp_ai.agent import change_link
from erp_ai.erp_ai_agent.doctype.erp_ai_change_proposal import erp_ai_change_proposal as proposal_form

BAD_LINK = "Đường dẫn duyệt không hợp lệ hoặc đã bị sửa."
DECIDERS = {
	change_link.ACTION_APPROVE: proposal_form.approve,
	change_link.ACTION_REJECT: proposal_form.reject,
}


@frappe.whitelist(methods=["POST"])
def decide(name=None, action=None, _signature=None) -> dict:
	"""Approve or reject proposal `name` for the signed link the session user opened.

	Raises:
		frappe.PermissionError: unknown `action` or a signature that is not the one of `name` + `action`
			(nothing written); or the role check of the proposal form.
	"""
	if action not in DECIDERS or not change_link.signature_ok(name, action, _signature):
		frappe.throw(_(BAD_LINK), frappe.PermissionError)
	return {"ok": True, "status": DECIDERS[action](name)["status"]}
