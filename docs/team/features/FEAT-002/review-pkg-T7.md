# Review package FEAT-002 T7

BASE 8108969 .. team/FEAT-002-task-7 (head 79d10d0). Diff: `docs/team/features/FEAT-002/review-pkg-T7.diff` (`git diff 8108969..team/FEAT-002-task-7`). Only test files changed; no product code.

## Commits
79d10d0 test(status): ... (FEAT-002)

## Dev evidence (raw)
Tests were green on first run, so teeth were proved by 4 mutations (removing `self.started = True`; `{exc}` instead of `type(exc).__name__`; dropping `*status.take_errors()` from the `_reason` entry error; appending `{status.text}` to the Error Log message), each red then restored. GREEN: test_runner_status Ran 33 OK, test_run_status 9 OK, test_agent_runner 56 OK, tests.test_handlers 31 OK, tests.test_architecture 44 OK.
The T6 test `test_leftover_status_errors_go_to_error_log_class_only` was renamed to `test_done_signal_failure_logged_to_error_log_class_only` (T7 list) and extended.
