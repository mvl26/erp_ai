# Review package FEAT-001 T33

BASE=a947607  head=4cf8b52 (branch team/FEAT-001-task-33)

Diff command (read-only, run from the repo root): `git diff a947607..team/FEAT-001-task-33`

## Commits
4cf8b52 feat(tasks): daily recompute of monthly AI spend from the log (FEAT-001)

Touchpoints: erp_ai/tasks.py (new), erp_ai/hooks.py, erp_ai/tests/test_tasks.py.
Criterion: AC-16 (monthly cost summed from the log; over budget -> effective level falls back, handled by policy.effective_level; month start resets to zero), D-19. `recompute_monthly_spend(now=None)`; hook `scheduler_events.daily`. Setting total field is `spent_this_month_usd` (design 3.7), per-key field `spent_month_usd`.
Expected tests: test_recompute_spend_from_log (total + per key), test_month_start_resets_to_zero.
Check: month boundaries and timezone (site vs UTC), rows with NULL cost, per-credential matching by label, write path (set_value / set_single_value, no save, no commit in test), whether the dev replaced a commented-out scheduler_events template correctly, and that D-20 commit behaviour is right for a scheduler job.
