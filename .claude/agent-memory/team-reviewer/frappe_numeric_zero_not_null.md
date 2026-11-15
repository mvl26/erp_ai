---
name: frappe-numeric-zero-not-null
description: Frappe Int/Check/Float columns are NOT NULL DEFAULT 0 and readers cast missing values to 0; designs that expect None/"unknown" for old rows break
metadata:
  type: project
---

Recurring in FEAT-007 (2 times):
- 2026-11-14 T2: `frappe.db.get_single_value` casts a missing `tabSingles` Check row to 0, so default tests pass without the default.
- 2026-11-14 T3: `predicted_confidence_pct` added as Int (design D-5 / 2.3), but `frappe/database/schema.py:197-199` makes Int/Check `not null default 0` (Float/Currency/Percent same, :202-203). Old ERP AI Log rows read 0, while `design-addendum-1-U1.md:130, 339, 459` (A-U1-1) expects None = unknown = below threshold. With `confidence_threshold` 0 (range 0..100) unknown becomes "meets threshold" (fail-open). Raised as design-defect.

- 2026-11-14 FEAT-005 T7: Datetime single. `get_single_value` uses `frappe.utils.cast` (database.py:36,868): NULL/missing -> `datetime(1,1,1)`, the string "0001-01-01 00:00:00" -> None (get_datetime treats it invalid). A restore `self.f = get_single_value(...)` on an empty watermark writes "0001-01-01 00:00:00" on save (update_single, no normalization); a test `assertIsNone(get_single_value(...))` then passes only because of that sentinel.

**Why:** Frappe has no nullable numeric field; "no value" and 0 are the same in DB and in `get_all`/`get_value`.
**How to apply:** when a diff adds an Int/Check/Float/Percent field, grep the design/addenda for readers that test `is None` or "not present" on it; if any, flag a design-defect (needs Data/Small Text, or a separate marker).
