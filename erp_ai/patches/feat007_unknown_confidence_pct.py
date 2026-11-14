"""FEAT-007 design-w0-fixes-2.md section 1: `predicted_confidence_pct` -1 means "unknown".

Sites that got the column with default 0 hold only "unknown" zeros (no code wrote it in wave 0),
so every 0 becomes -1, in batches, until no row changes. On a fresh site the column is created
with default -1 first and this changes nothing.
"""

import frappe

from erp_ai.constants import LOG_DOCTYPE

BATCH_SIZE = 10000
UNKNOWN_PCT = -1


def execute():
	while True:
		frappe.db.sql(
			f"""update `tab{LOG_DOCTYPE}` set predicted_confidence_pct = %s
			where predicted_confidence_pct = 0 limit %s""",
			(UNKNOWN_PCT, BATCH_SIZE),
		)
		if not frappe.db._cursor.rowcount:
			break
