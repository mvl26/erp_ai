"""The agent account saves only its own draft knowledge-base articles (AC-45, ADR-034 QĐ 6).

`doc_events` of HD Article, so the check runs server-side whatever `ignore_permissions` says.
"""

import frappe

from erp_ai.constants import AGENT_USER

DRAFT_ONLY = "Bot chỉ được tạo bài CSKT ở trạng thái nháp"
NOT_OWN = "Bot không được sửa bài không do bot tạo"
NO_DELETE = "Bot không được xóa bài CSKT"


def check_article_write(doc, method):
	"""`validate`: under the agent account, only a `Draft` the bot itself created may be saved."""
	if frappe.session.user != AGENT_USER:
		return
	if not doc.is_new() and doc.owner != AGENT_USER:
		frappe.throw(NOT_OWN, frappe.PermissionError)
	if doc.status != "Draft":
		frappe.throw(DRAFT_ONLY, frappe.PermissionError)


def check_article_delete(doc, method):
	"""`on_trash`: the agent account never deletes an article."""
	if frappe.session.user == AGENT_USER:
		frappe.throw(NO_DELETE, frappe.PermissionError)
