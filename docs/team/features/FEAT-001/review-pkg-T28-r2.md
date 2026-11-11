# Scoped re-review FEAT-001 T28 round 2

FIX_BASE=20b2d9a .. team/FEAT-001-task-28 (head d1c88e9). The dev first merged team/FEAT-001 into the task branch (merge commit: ignore it); review only the fix commit: `git diff 20b2d9a..d1c88e9 -- erp_ai/agent/runner.py erp_ai/agent/test_runner.py erp_ai/tests/test_handlers.py` (use `git log --first-parent`/`git show d1c88e9` to isolate the fix commit if needed).
Old findings: docs/team/features/FEAT-001/review-raw-T28.md (3 majors + minors 1-4). Mark each ADDRESSED / NOT ADDRESSED.
Dev notes: limit seeded 2; AC-9 test compares Comment count and ai_* fields; deadline = JOB_TIMEOUT_S - JOB_SAFETY_MARGIN_S with 2 new tests; minor 4: `_log_skip` writes ticket=None when the HD Ticket is missing.
