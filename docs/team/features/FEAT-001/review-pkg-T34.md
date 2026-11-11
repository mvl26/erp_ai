# Review package FEAT-001 T34

BASE=881fa66  head=dd51bf4 (branch team/FEAT-001-task-34)

Diff command (read-only, run from the repo root): `git diff 881fa66..team/FEAT-001-task-34`

## Commits
dd51bf4 feat(tasks): daily privilege escalation check with alarms (FEAT-001)

Touchpoints: erp_ai/tasks.py, erp_ai/tests/test_tasks.py.
Criterion: AC-18 (a) agent account role outside {ERP AI Agent, Agent}; (b) permission records modified by the agent; (c) Server Script / Webhook created by the agent and enabled; (d) key enabled with empty secret. One `alerts.send_alarm` per true condition, <= 5 names listed, no key decryption, no alarm when nothing is wrong. Design 4.5/4.6, D-20 error contract (try/except, rollback, log_error with constant title and explicit message).
Dev's notes: roles are read from Has Role minus AUTOMATIC_ROLES; a missing agent account also alarms (design 4.6); permission doctypes are those in design 4.6; the empty-key check reads only the masked `api_key` column; `hooks.py` is NOT touched (daily hook for `check_privilege_escalation` is registered by T35, ruling recorded in tasks.md).
Check: SQL/qb parameterisation, no secret in alarm messages, guards each reachable by a test, T33's recompute function and its error contract unchanged.
