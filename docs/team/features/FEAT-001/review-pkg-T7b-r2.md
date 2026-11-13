# Scoped re-review package T7b round 2 (FEAT-001)

FIX_BASE=2b523ac, head=34d1450 (branch team/FEAT-001-task-7b)
Diff command: `git diff 2b523ac..team/FEAT-001-task-7b` in /home/miyano/frappe-bench/apps/erp_ai

## Old finding to mark ADDRESSED / NOT ADDRESSED
major | STD-TEST-2 | erp_ai/agent/tools/test_source.py:300-307 | The show/diff refusal test passes even if the protection is removed: its args are all refused by the blame checker anyway; source.py falls through to the blame checker for any subcommand other than log. | Add cases blame would accept (`show ["src/a.py"]`, `diff ["--", "src/a.py"]`) under run.assert_not_called(); replace the else with an explicit map so an unknown subcommand is refused.

Out-of-scope notes go to `deferred`. Re-review only the fix diff.
