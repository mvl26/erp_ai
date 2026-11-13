# Review package FEAT-001 T20c (BASE 3f63ec7..6f7a566, branch team/FEAT-001-task-20c)

Diff command (authoritative, read-only git): `git diff 3f63ec7..team/FEAT-001-task-20c`

Commit: 6f7a566. File: erp_ai/agent/test_policy.py only.

Problem: `frappe.delete_doc("HD Team")` runs `HDTeam.on_trash` which calls `frappe.db.commit()` (apps/helpdesk/helpdesk/helpdesk/doctype/hd_team/hd_team.py:46), so the T20b `_drop_teams` committed each test's transaction. Fix: create teams inside the test transaction, rely on rollback only, clear Redis `assignment_rule_map` after the rollback, and verify in tearDownClass that teams the class created are absent.
Check: no assertion changed (STD-TEST-5); cleanup order (LIFO: hdel must run AFTER rollback); tearDownClass check really would fail if something was committed (the dev did not show a red for it); no `delete_doc`, no commit; no skip markers.

Dev evidence (raw): test_policy Ran 21 OK; full app Ran 262 OK twice; pre-commit exit 0.

Run `git diff 3f63ec7..team/FEAT-001-task-20c` for the verbatim code.
