---
name: frappe-error-log-myisam
description: Frappe's Error Log table is MyISAM (error_log.json:6), so rollback and test-transaction rollback never remove Error Log rows; designs and docstrings that claim otherwise are wrong
metadata:
  type: project
---

Frappe 15 `Error Log` is `"engine": "MyISAM"` (`apps/frappe/frappe/core/doctype/error_log/error_log.json:6`): a row written by `frappe.log_error` survives `frappe.db.rollback()`, savepoint rollback and the FrappeTestCase rollback.

Seen twice (2026-11-14, FEAT-005 T13): ADR-024 QĐ 3.5 / design-amd2 §4.2 step 5 claim "rollback cả Error Log cảnh báo, Email Queue và mốc" (design-defect); test helper `_real_alarms` docstring says its Error Log rows are "rolled back with the test" (they persist on the shared site `miyano`).

**Why:** designs infer "same transaction" from `log_error` not committing, without checking the engine.
**How to apply:** any design, criterion or test that expects an Error Log row to vanish on rollback → design-defect or masked test; tests that let real `log_error` run leave residue on the shared site; a real Error Log count is a non-transactional witness that the code path ran before a rollback. Related: [[frappe-numeric-zero-not-null]].
