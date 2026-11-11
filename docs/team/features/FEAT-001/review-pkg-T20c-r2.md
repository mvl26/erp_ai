# Review package FEAT-001 T20c round 2 (scoped re-review, FIX_BASE 6f7a566..6e0ca14, branch team/FEAT-001-task-20c)

Diff command (authoritative, read-only git): `git diff 6f7a566..team/FEAT-001-task-20c`
Full task diff for context: `git diff 3f63ec7..team/FEAT-001-task-20c`

Old finding (round 1, verbatim): major | STD-TEST-1 | test_policy.py:29-38 | the new tearDownClass leak check came with no red output and is vacuous on a site that already holds the fixed-name teams (`_teams_before == set(TEAMS)`, `leaked` always []). Fix: red-then-green, or make the check independent of site state (commit guard / unique marker). Minor: bare `assert` is skipped under -O.

Fix: setUp patches `frappe.db.commit` with `side_effect=AssertionError` for each test (stopped by cleanup); setUpClass/tearDownClass and the bare assert were removed. Dev red: with a T20b-style `delete_doc("HD Team")` cleanup restored, 21 failures from hd_team.py:46 `frappe.db.commit()` raising; green: Ran 21 OK, full app Ran 262 OK twice.
Check specifically: the patch cannot hide a commit by catching the AssertionError somewhere (does any code in the call path swallow exceptions around commit?); the patch scope does not break FrappeTestCase class-level commits or `before_tests`; cleanup order; assertions unchanged.
