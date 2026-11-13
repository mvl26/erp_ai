# dev-T41 (FEAT-001)

Status: DONE. Branch team/FEAT-001-task-41, commit 40ee67f (note: written after the commit, so this file is uncommitted).

## RED (before git mv)
Command: PYTHONPATH=<worktree> bench --site miyano run-tests --module erp_ai.tests.test_architecture
```
AssertionError: Lists differ: ["agent/test_runner.py: file name test_run[49 chars] it"] != []
First extra element 0:
"agent/test_runner.py: file name test_runner.py is skipped by Frappe's test runner, rename it"
Ran 42 tests ... FAILED (failures=1)
```
The scanner test test_frappe_skipped_test_name_check_catches_any_depth was green (the pure function was added together with the tests). Only the tree test was red.

## GREEN (after git mv)
- erp_ai.tests.test_architecture: Ran 42 tests, OK
- erp_ai.agent.test_agent_runner: Ran 52 tests, OK
- Not run: full `--app erp_ai` (not requested in the task).

## Lint
pre-commit run --files (both files): all hooks Passed (ruff import sorter, linter, formatter included).

## Data counts (HD Team / HD Ticket / User / ERP AI Log / Error Log)
Before: 4 / 3 / 8 / 0 / 203. After: 4 / 3 / 8 / 0 / 203. Nothing created or deleted; ERP AI Setting not touched.

## git diff --name-only team/FEAT-001 HEAD
```
erp_ai/agent/test_agent_runner.py   (rename of erp_ai/agent/test_runner.py, content unchanged)
erp_ai/tests/test_architecture.py
```

## Notes
- No stale references to the old path or module name in erp_ai/** (the only hit is the test's own violating fixture string).
- The commit hook gave a WARN (STD-NAME-5) about the message format because the Co-Authored-By trailer follows the subject; the subject itself follows `type(scope): description (FEAT-001)`.
- The tree test asserts the name check first, then that agent/test_agent_runner.py exists.
