# Review package T4 (FEAT-001)

Diff command: `git diff a85f798..team/FEAT-001-task-4` (BASE=a85f798, head 47dede6)
Commits: 47dede6 feat(gateway): pure circuit-breaker table decide() (FEAT-001)
Files (new): erp_ai/gateway/breaker.py, erp_ai/gateway/test_breaker.py
Run the diff command in /home/miyano/frappe-bench/apps/erp_ai (branch is local).
Criteria (tasks.md T4): AC-17 rows 1-9 of design 3.4.3; 529 pause capped at 600 s; 429 without retry-after -> 61 s; ApiFailure, Action, decide(failure, error_count) -> Action exact shapes.
Touchpoints: erp_ai/gateway/breaker.py, erp_ai/gateway/test_breaker.py.
