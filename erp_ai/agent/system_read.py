"""Bounded read of the Error Log (AC-50, design 3.7, ADR-021 QĐ 4).

The query builder skips document permissions: this is the only permission-free path of the new read
group (ADR-034), so the agent account reads the Error Log without any extra role. It is `frappe.qb`
and not `frappe.get_all` because `get_all` turns every backslash of a LIKE value into a literal one,
so an escaped `%` or `_` cannot be expressed through it; the keyword goes in as a bound parameter.

Every `method` and `error` goes through `redact_secrets` before it leaves; `error` is masked first and
cut after (`design-w0-fixes-3.md` 3a), so a cut can never drop a key name and leave its value behind.
A row whose reference is an HD Ticket of `policy.excluded_ticket_names` is never read (R17c).
"""

from datetime import timedelta

import frappe
from frappe.query_builder import Order
from frappe.query_builder.functions import Coalesce
from frappe.utils import now_datetime

from erp_ai.agent import policy
from erp_ai.agent.redact import redact_secrets

DEFAULT_WINDOW = timedelta(hours=24)
MAX_WINDOW = timedelta(days=7)
MIN_LIMIT, MAX_LIMIT = 1, 50
MIN_KEYWORD_LENGTH, MAX_KEYWORD_LENGTH = 2, 100
ERROR_TAIL_LENGTH = 2000


def _like_pattern(keyword: str) -> str:
	"""`%keyword%` with the LIKE wildcards and the escape character taken literally."""
	escaped = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
	return f"%{escaped}%"


def read_error_logs(since=None, until=None, keyword=None, limit=20) -> list[dict]:
	"""Error Log rows created in [since, until], newest first, at most `limit`, secrets masked.

	Defaults: `until` = now, `since` = `until` - 24 h. A window over 7 days, a `limit` outside 1..50 or a
	`keyword` outside 2..100 characters is refused. `keyword` matches `method` or `error` (LIKE, escaped).
	"""
	until = until or now_datetime()
	since = since or until - DEFAULT_WINDOW
	if until - since > MAX_WINDOW:
		frappe.throw("Khoảng thời gian tối đa 7 ngày")
	if not MIN_LIMIT <= limit <= MAX_LIMIT:
		frappe.throw(f"Số dòng phải từ {MIN_LIMIT} đến {MAX_LIMIT}")

	error_log = frappe.qb.DocType("Error Log")
	query = (
		frappe.qb.from_(error_log)
		.select(error_log.name, error_log.creation, error_log.method, error_log.error)
		.where((error_log.creation >= since) & (error_log.creation <= until))
		.orderby(error_log.creation, order=Order.desc)
		.orderby(error_log.name, order=Order.desc)
		.limit(limit)
	)
	if keyword is not None:
		if not MIN_KEYWORD_LENGTH <= len(keyword) <= MAX_KEYWORD_LENGTH:
			frappe.throw(f"Từ khóa phải dài từ {MIN_KEYWORD_LENGTH} đến {MAX_KEYWORD_LENGTH} ký tự")
		pattern = _like_pattern(keyword)
		query = query.where(error_log.method.like(pattern) | error_log.error.like(pattern))
	if excluded := [str(name) for name in policy.excluded_ticket_names()]:
		# R17c (NFR-1): inside the query, so `limit` counts only returned rows; a NULL column keeps its row.
		query = query.where(
			(Coalesce(error_log.reference_doctype, "") != policy.TICKET_DOCTYPE)
			| Coalesce(error_log.reference_name, "").notin(excluded)
		)

	rows = query.run(as_dict=True)
	return [
		{
			"name": row.name,
			"creation": row.creation,
			"method": redact_secrets(row.method),
			"error": redact_secrets(row.error)[-ERROR_TAIL_LENGTH:],
		}
		for row in rows
	]
