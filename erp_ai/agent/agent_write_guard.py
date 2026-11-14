"""Write guard of the agent account on the app's DocTypes (ADR-023 QĐ 5, measure M5).

The check is on the session user, so it covers every path that reaches a controller (tools, `call_method`,
`frappe.client.*`, `savedocs`, background jobs queued by the agent). The only opening is `AGENT_WRITE_FLAG` in
`frappe.flags`, set by `allow_agent_write()`; it is never read from `doc.flags` or a doc field, so a dict sent
by a client cannot forge it.
"""

from contextlib import contextmanager

import frappe

from erp_ai.constants import AGENT_USER

AGENT_WRITE_FLAG = "erp_ai_agent_write_allowed"


@contextmanager
def allow_agent_write():
	"""Open the guard for the agent account inside this block; restore the previous flag value on exit."""
	previous = frappe.flags.get(AGENT_WRITE_FLAG)
	frappe.flags[AGENT_WRITE_FLAG] = True
	try:
		yield
	finally:
		frappe.flags[AGENT_WRITE_FLAG] = previous


def refuse_agent_write(doc) -> None:
	"""Raise `frappe.PermissionError` when the agent account writes `doc` outside `allow_agent_write()`."""
	if frappe.session.user == AGENT_USER and not frappe.flags.get(AGENT_WRITE_FLAG):
		frappe.throw(f"Tài khoản agent không được ghi {doc.doctype}", frappe.PermissionError)
