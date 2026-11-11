# Review package FEAT-001 T20b (BASE 3b412e7..6c52cbf, branch team/FEAT-001-task-20b)

Diff command (authoritative, read-only git): `git diff 3b412e7..team/FEAT-001-task-20b`

Commit: 6c52cbf. File: erp_ai/agent/test_policy.py only.

Task: test_policy.py must not leave Redis state behind. Cause: `_ensure_team("IT")` inserted a real HD Team; HD Team.after_insert creates Assignment Rule "IT - Support Rotation" cached in Redis `assignment_rule_map`; `addCleanup(frappe.db.rollback)` does not clear Redis, so later HD Ticket inserts in other test modules raised DoesNotExistError. Pattern reference: helpdesk `test_hd_agent.py:365-370`.
Criteria: all existing assertions unchanged (STD-TEST-5); cleanup deletes only teams the test created; cache key cleared; STD-TEST-6.

Run `git diff 3b412e7..team/FEAT-001-task-20b` for the verbatim code.
