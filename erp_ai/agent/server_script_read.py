"""Bounded, read-only reads of Server Script for the `script_read` tools (2026-11-27).

The switch is the grant: `server_script_read_enabled` of ERP AI Setting opens these reads, and only System Manager
may write that Setting, so turning it on is the administrator's decision. The reads therefore skip document
permissions on purpose (`frappe.get_all`, `frappe.db.get_value`). The agent account holds no role that reads Server
Script and must not get one: `tasks._agent_role_drift` alarms on any extra role, and a role would open the whole
DocType to every tool, writes included. Like `system_read` for the Error Log, this module sits outside `agent/tools/`,
where ADR-005 bars permission-free reads; it reads only the columns below and writes nothing.

`script` goes through `redact_secrets` before it leaves (tokens, API keys and passwords become `redact.MASK`); the
caller cuts it after, so a cut never drops a key name and leaves its value behind.
"""

import frappe

from erp_ai.agent.redact import redact_secrets

SERVER_SCRIPT_DOCTYPE = "Server Script"
# The options of Server Script.script_type (pinned against the meta by the tests).
SCRIPT_TYPES = ("DocType Event", "Scheduler Event", "Permission Query", "API")
LIST_FIELDS = (
	"name",
	"script_type",
	"reference_doctype",
	"doctype_event",
	"api_method",
	"event_frequency",
	"disabled",
	"modified",
)
DETAIL_FIELDS = (*LIST_FIELDS, "cron_format")


def list_scripts(
	*, reference_doctype: str | None, name_contains: str | None, script_type: str | None, limit: int
) -> list[dict]:
	"""Server Scripts, disabled ones too, last changed first, at most `limit`; LIST_FIELDS only, never the body.

	`name_contains` is a LIKE on the name: a `%` or `_` in it only widens the match.
	"""
	filters = {}
	if reference_doctype:
		filters["reference_doctype"] = reference_doctype
	if script_type:
		filters["script_type"] = script_type
	if name_contains:
		filters["name"] = ["like", f"%{name_contains}%"]
	rows = frappe.get_all(
		SERVER_SCRIPT_DOCTYPE,
		filters=filters,
		fields=list(LIST_FIELDS),
		order_by="modified desc, name desc",
		limit_page_length=limit,
	)
	return [{field: row.get(field) for field in LIST_FIELDS} for row in rows]


def get_script(name: str) -> dict | None:
	"""DETAIL_FIELDS of the Server Script `name` and its `script` with the secrets masked; None when there is none."""
	row = frappe.db.get_value(SERVER_SCRIPT_DOCTYPE, name, [*DETAIL_FIELDS, "script"], as_dict=True)
	if not row:
		return None
	return {**{field: row.get(field) for field in DETAIL_FIELDS}, "script": redact_secrets(row.get("script"))}
