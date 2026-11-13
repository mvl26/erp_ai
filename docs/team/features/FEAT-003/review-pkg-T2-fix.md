# Scoped re-review package FEAT-003 T2 round 2

- Repo: /home/miyano/frappe-bench/apps/erp_ai (read-only; `git -C`)
- Task branch team/FEAT-003-task-2. Round-1 head 31c4b75. Fix commit 10990fa.
- Fix diff: `git diff 31c4b75..team/FEAT-003-task-2` (agent_status_indicator.js, tests/test_architecture.py)
- Old findings to mark ADDRESSED / NOT ADDRESSED: docs/team/features/FEAT-003/review-T2-r1.md (1 major literal first argument of call; minors a, b; c left for T14; ADR-gap note goes to T15).
- The dev also added a static test that every `call(` has a literal first argument in PANEL_METHODS (+ a test that the checker catches variable/unknown/multi-line forms): check it is not decorative.
