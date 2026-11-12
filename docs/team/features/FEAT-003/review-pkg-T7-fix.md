# Scoped re-review package FEAT-003 T7 round 2

- Repo: /home/miyano/frappe-bench/apps/erp_ai (read-only; `git -C`)
- Task branch team/FEAT-003-task-7. Round-1 head 32dd12e. Fix commit a0c75f5.
- Fix diff: `git diff 32dd12e..team/FEAT-003-task-7` (tests/test_ticket_panel.py only)
- Old findings to mark ADDRESSED / NOT ADDRESSED: docs/team/features/FEAT-003/review-T7-r1.md (1 major: AC-8 test data must be exactly 3 human keyword (1 other case) + 2 human plain + 2 agent + 1 keyword comment on another ticket -> 5 names in order; minors 3, 4 fixed by dev; minors 1, 2 deferred).
- Check against spec.md AC-8 row for the exact counts.
