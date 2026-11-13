# Review package FEAT-001 T35

BASE=11e5775  head=d143b42 (branch team/FEAT-001-task-35)

Diff command (read-only, run from the repo root): `git diff 11e5775..team/FEAT-001-task-35`

## Commits
d143b42 feat(tasks): hourly reprobe of exhausted keys, schedule privilege check daily (FEAT-001)

Touchpoints: erp_ai/tasks.py, erp_ai/hooks.py, erp_ai/tests/test_tasks.py.
Criterion: AC-18 (only `Hết hạn mức` keys are re-probed; recovery -> `Hoạt động` + exactly 1 notice email). `tasks.reprobe_exhausted_keys()` calls `gateway.reprobe_exhausted_keys()` (which already filters status, updates it and calls `alerts.send_notice`), so the job sends nothing itself. D-20 error contract (try/except, rollback, log_error constant title + explicit message, commit when not in_test). hooks: hourly [reprobe_exhausted_keys]; daily [recompute_monthly_spend, check_privilege_escalation] (the daily registration was assigned to T35 by tech-lead ruling in review-raw-T34.md, a touchpoint extension of intent only, hooks.py is already a T35 touchpoint). T33/T34 functions must be untouched.
Dev did not mutation-test the error-handling guard nor the status filter (the filter lives in the gateway, T18); judge whether the tests can fail for the guards this task owns (no second notice; error path; hooks order).
