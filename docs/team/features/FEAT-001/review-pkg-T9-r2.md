# Scoped re-review package T9 round 2 (FEAT-001)

FIX_BASE=f32354f, head=765c672 (branch team/FEAT-001-task-9; only test_erp_ai_setting.py changed)
Diff command: `git diff f32354f..team/FEAT-001-task-9` in /home/miyano/frappe-bench/apps/erp_ai

## Old findings to mark ADDRESSED / NOT ADDRESSED
1. major | STD-TEST-6 | test_erp_ai_setting.py:160-161 (affects :134-156) | Class-scoped rollback leaked state (enabled=1, prices 0) between tests so most negative cases raised at check_enabled_requirements whatever guard was removed. Fix asked: reset a baseline per test (setUp / addCleanup rollback) and use assertRaisesRegex per guard.
2. major | STD-TEST-2 | test_erp_ai_setting.py:67-100 | Criterion (a) tested for only 3 of the 8 self-managed fields. Fix asked: restore test with non-default values for all 8 fields in DB vs different form values; new-row test asserting all 8 defaults.

Out-of-scope notes go to `deferred`. Re-review only the fix diff; check that each test would go red if its guard were removed.
