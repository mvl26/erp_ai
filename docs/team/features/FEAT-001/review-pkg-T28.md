# Review package FEAT-001 T28

BASE=b2fdf26 .. team/FEAT-001-task-28 (head 20b2d9a). Diff: `git diff b2fdf26..team/FEAT-001-task-28`; files: erp_ai/agent/runner.py, erp_ai/agent/test_runner.py (new, 18 tests), erp_ai/tests/test_handlers.py (1 test changed; outside touchpoints, tech-lead ruling: spec change, STD-TEST-5 precedent T17 — reviewer please verify the change is minimal and correct).

Task criterion (T28): AC-6, AC-9 (L0: phiếu trước = sau), AC-3 (UNPARSEABLE, lần chạy không hỏng), AC-15 (`daily_limit`), NFR-4 (không gửi khi `can_send_ticket` sai lúc chạy), ADR-003 (a)–(e). Design 4.3.
Binding debt: key-breaker state (credentials.apply_failure/success, uncommitted) must survive a failed run / rollback. Dev's approach: `_call_model` try/finally commits (only when not in_test) after call_model returns or raises; no rollback in the except path. Check this is sound (commits not breaking the savepoint model of tools, T27; commits inside the job transaction before ticket writes; D-20) and that the tests are real (RED when removed).
Dev's concern 2: with no rollback in the except path, a failed run keeps partial ticket changes; tool writes are expected to be savepoint-scoped (execute_tool). Judge whether acceptable for T28 scope (L0 writes no ticket changes) and note for T29/T30.
Test data rule: no records left on miyano; counts printed by dev identical (4/3/8/0/195).
