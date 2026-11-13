# Review package FEAT-001 T17 (BASE e50754a..7bc7f0c, branch team/FEAT-001-task-17)

Diff command (authoritative, read-only git): `git diff e50754a..team/FEAT-001-task-17`

Commits: d870081 feat(gateway): call_model key failover by breaker; 7bc7f0c test(handlers): drop obsolete gateway stub test.
Files: erp_ai/gateway/__init__.py, erp_ai/gateway/test_gateway.py, erp_ai/tests/test_handlers.py (touchpoint extended by tech-lead ONLY to delete `test_gateway_stub_raises_not_implemented`, which asserted the removed stub; spec changed).

Task: T17 line in tasks.md; design 3.4.1-3.4.3 (call_model flow, breaker table, notification rules D-21). Criteria: AC-17, NFR-7, NFR-2, AC-15, NFR-5.
Requirements carried from earlier reviews (docs/team/features/FEAT-001/review-19.md, review-24.md Deferred): pass `request_id` into `credentials.apply_failure`; `decide()` gets error_count old+1; notify only on a real status change (D-21); normalize usage None -> 0 before compute_cost.

Dev evidence (raw): RED Ran 43 FAILED (errors=20); GREEN test_gateway Ran 43 OK; full app Ran 218 OK; pre-commit exit 0.

Run `git diff e50754a..team/FEAT-001-task-17` for the verbatim code.
