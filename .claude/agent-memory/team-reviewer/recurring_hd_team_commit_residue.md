---
name: recurring-hd-team-commit-residue
description: FEAT-001 recurring defect - test cleanup deletes an HD Team with delete_doc; HD Team.on_trash calls frappe.db.commit, so the test transaction is committed and the team survives the later rollback
metadata:
  type: project
---

2026-11-11: Recurring (>= 2 times in FEAT-001): test cleanup `frappe.delete_doc("HD Team", ...)` (to clear the `assignment_rule_map` Redis cache) runs Helpdesk `HDTeam.on_trash`, which calls `frappe.db.commit()` (helpdesk hd_team.py:46) BEFORE `delete_from_table` (frappe delete_doc.py:136-155). Result: everything made in the test so far (ticket, users, ticket type, writes) is committed, the Assignment Rule delete is committed, and the following `frappe.db.rollback` restores the HD Team row with a dangling `assignment_rule`.
- T20b: erp_ai/agent/test_policy.py `_drop_teams` (merged, found during T25 review).
- T25: erp_ai/agent/tools/test_write_ticket.py `_drop_team`; also no `ignore_permissions`, so it raises for OUTSIDER/CUSTOMER when that test runs first.

**Why:** dev copies the "delete team + hdel cache" pattern believing the rollback undoes it; the framework commit inside a hook breaks that.
**How to apply:** whenever a test cleans up with `delete_doc`/`save` on a third-party DocType, read that DocType's on_trash/on_update for `frappe.db.commit`. Suggest `ignore_on_trash=True` + explicit Assignment Rule handling, or rollback first then `hdel` the cache. See [[recurring-masked-tests]].
- 2026-11-11 T20c r2: accepted guard pattern = setUp `patch.object(frappe.db, "commit", side_effect=AssertionError)` started in setUp, stop registered before rollback (so rollback runs while guarded). Prefer it over "set difference vs site state" leak checks, which are vacuous on a dirty site. Blind spots: raw `frappe.db.sql("commit")`, DDL implicit commits, except-AssertionError/bare except in the call path.
- 2026-11-11 T25 r2: second accepted pattern = no delete at all, rollback-only cleanup + `hdel` after rollback (LIFO addCleanup), plus a tearDownClass check that the fixed names (team, ticket type, user) are ABSENT. Not vacuous because it ignores pre-existing site state (residue makes it fail loudly). It needs a clean site and catches only commits that persist those names; weaker than the commit-patch guard.
