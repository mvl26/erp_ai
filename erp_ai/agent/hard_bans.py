"""Hard bans of the action catalog: one source for the save-time check and the executor (ADR-031).

The ban sets come from `read` and `site_api`; this module names no DocType itself.
"""

import frappe

from erp_ai.agent.tools import read, site_api

REASON_DENIED = "DocType bị cấm với bot (dữ liệu của app, tài khoản hoặc dữ liệu nhạy cảm)"
REASON_PERMISSION = "DocType phân quyền"
REASON_SUBMITTABLE = "chứng từ submit"
REASON_CHILD_TABLE = "bảng con của DocType khác"


def hard_ban_reason(doctype: str) -> str | None:
	"""The first ban the DocType hits, in order: denied to the bot, permission DocType, submittable,
	child table (`istable`, AR3-3); else None.

	An unknown DocType raises `frappe.DoesNotExistError` (from `get_meta`); callers check existence first.
	"""
	if doctype in read.denied_doctypes():
		return REASON_DENIED
	if doctype in site_api.PERMISSION_DOCTYPES:
		return REASON_PERMISSION
	meta = frappe.get_meta(doctype)
	if meta.is_submittable:
		return REASON_SUBMITTABLE
	if meta.istable:
		return REASON_CHILD_TABLE
	return None
