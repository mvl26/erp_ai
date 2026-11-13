# Review package FEAT-001 T32

BASE=221187b  head=d03c508 (branch team/FEAT-001-task-32)

Diff command (read-only, run from the repo root): `git diff 221187b..team/FEAT-001-task-32`

## Commits
d03c508 feat(handlers): record human classification correction on the latest classify log (FEAT-001)

Touchpoints: erp_ai/handlers.py, erp_ai/hooks.py, erp_ai/tests/test_handlers.py.
Criterion: AC-11 (a human correction stores the value on the latest `classify` log row and flips "classified by" to Human; an agent edit does not), ADR-004 #5, D7 (log rows written with `frappe.db.set_value(update_modified=False)`; no commit). `ticket_validate`, `ticket_on_update`, `human_corrected_at` only set the first time.
Expected tests: test_human_correction_updates_latest_log (two corrections -> last value, `human_corrected_at` first), test_agent_correction_not_recorded.
Check design 3.1/2.3 for where validate/on_update logic must live, the flag mechanism between validate and on_update, and a human editing fields not part of the classification.
