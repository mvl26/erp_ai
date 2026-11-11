# Review package FEAT-001 T25 round 2 (scoped re-review, FIX_BASE 5ca4748..7ea9807, branch team/FEAT-001-task-25)

Diff command (authoritative, read-only git): `git diff 5ca4748..team/FEAT-001-task-25 -- erp_ai`
Full task diff for context: `git diff e50754a..team/FEAT-001-task-25 -- erp_ai`

Old findings to mark ADDRESSED / NOT ADDRESSED (round 1, verbatim):
1. major | STD-TEST-6 | test_write_ticket.py:49-52 (and :35-45) | `_drop_team` -> `frappe.delete_doc("HD Team")` -> `HDTeam.on_trash` commits the whole test transaction (hd_team.py:46); residue HD Team "T25 Nhóm" etc.; delete without ignore_permissions depends on the current user. Fix: create in the test transaction, rely on rollback, hdel `assignment_rule_map` after rollback, prove nothing committed after the class.
2. major | STD-TEST-2 | test_write_ticket.py:79 | `assertTrue(get_datetime(row.ai_updated_at))` never fails (`get_datetime(None)` = now); use assertIsNotNone + fixed/lower-bound time.
3. minors: (1) `ai_classified_by`/`ai_updated_at` entries of the permlevel loop untested; (2) `if not value` branch with None and reason; (3) wrong comment about HD Customer refusal.

Touchpoints: erp_ai/agent/tools/write_ticket.py, erp_ai/agent/tools/test_write_ticket.py (only the test file changed in the fix).
