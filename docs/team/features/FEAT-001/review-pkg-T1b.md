# Review package T1b (FEAT-001)

Task: T1b move erp_ai/test_handlers.py to erp_ai/tests/test_handlers.py (+ empty erp_ai/tests/__init__.py). Branch team/FEAT-001-task-1b. BASE=88c1a2c, head 9c0a390 (one commit).
Why: Frappe test_runner._add_test drops the module name for test files at the app package root, so `bench run-tests --app erp_ai` ran 0 tests. Decision D2 in docs/team/journal/FEAT-001.md and plan.md.

Diff (read-only, from /home/miyano/frappe-bench/apps/erp_ai): git diff -M 88c1a2c..team/FEAT-001-task-1b ; git show --stat 9c0a390
Criteria: `bench --site miyano run-tests --app erp_ai` reports "Ran 6 tests ... OK" (before: "Ran 0 tests / NO TESTS RAN"). Touchpoints: erp_ai/tests/__init__.py, erp_ai/tests/test_handlers.py, erp_ai/test_handlers.py (moved). test_utils.py must stay where it is.
Evidence (verification run, PYTHONPATH=worktree): --app erp_ai: Ran 6 tests OK; --module erp_ai.tests.test_handlers: Ran 6 tests OK; the rename is content-identical (2 files, 0 insertions/deletions).
Design: docs/team/features/FEAT-001/design.md (not affected).
