# dev-T19 (lần 3) — FEAT-006

Nhánh: team/FEAT-006-task-19c (từ 5fa6d4b).

## Thay đổi
Chỉ đổi 2 dòng khẳng định `max_tokens` 400 → 600 theo D-8 (STD-TEST-5, spec đổi):
- erp_ai/agent/test_agent_runner.py:240
- erp_ai/tests/test_handlers.py:241

## ĐỎ trước khi sửa
- test_agent_runner: `AssertionError: 600 != 400` (Ran 56, failures=1)
- test_handlers: `AssertionError: 600 != 400` (Ran 31, failures=1)

## XANH sau khi sửa
- erp_ai.agent.test_agent_runner: 56 OK
- erp_ai.tests.test_handlers: 31 OK
- erp_ai.agent.test_runner_routing: 11 OK
- erp_ai.erp_ai_agent.doctype.erp_ai_log.test_erp_ai_log: 7 OK
- erp_ai.tests.test_doctype_descriptions: 10 OK
- `bench --site miyano run-tests --app erp_ai`: Ran 792 tests, OK
- pre-commit --files hai file: ruff, ruff format, ast đều Passed

Không skip/xfail, không push.
