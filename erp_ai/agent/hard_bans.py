"""Hard bans of the action catalog: one source for the save-time check and the executor (ADR-031).

The ban sets come from `read` and `site_api`; this module names no DocType itself.
"""

import frappe

from erp_ai.agent.tools import read, site_api

REASON_DENIED = "DocType bị cấm với bot (dữ liệu của app, tài khoản hoặc dữ liệu nhạy cảm)"
REASON_PERMISSION = "DocType phân quyền"
REASON_SUBMITTABLE = "chứng từ submit"


def hard_ban_reason(doctype: str) -> str | None:
	"""The first ban the DocType hits, in order: denied to the bot, permission DocType, submittable; else None.

	An unknown DocType raises `frappe.DoesNotExistError` (from `get_meta`); callers check existence first.
	"""
	if doctype in read.denied_doctypes():
		return REASON_DENIED
	if doctype in site_api.PERMISSION_DOCTYPES:
		return REASON_PERMISSION
	if frappe.get_meta(doctype).is_submittable:
		return REASON_SUBMITTABLE
	return None
