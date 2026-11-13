# Review package R2 (rework 1, mục 2+5+6, T21) — test-only

BASE=91d89039e1b9aaea910f2533e21fb510e45d1189, head team/FEAT-006-rw1-r2 (0c9661e). Run from `/home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/feat-006` (shared repo):
`git diff 91d8903..team/FEAT-006-rw1-r2 -- erp_ai`

## Commits
0c9661e test(routing): siet AC-11 AC-7c AC-14 co rang (FEAT-006)

## Stat
erp_ai/agent/test_runner_routing.py | 42 +++- (docs/team/features/FEAT-006/dev-R2.md is the dev note, ignore it)

## Criteria (acceptance.md rework list)
- AC-11 (item 2): in the no-SLA cases (`TestRoutingSla::test_no_sla_*`, `test_switch_off_no_sla_still_one_comment`), assert the ticket is still saved with the CORRECT priority (`priority`, `entry.applied == 1`) and the HD Service Level Agreement count is the same before and after.
- AC-7(c) (item 5): `TestRoutingNoOverride::test_switch_off_no_todo_no_task` must assert the classification is still written (`apply_route` ok=True, team/priority on the ticket).
- AC-14 (item 6): `TestRoutingAssign::test_changed_default_person_assigned_next_run` must use a next ticket whose heading is B (spec says "đầu mục B"), with B's default person changed.
- Tests must fail when the behavior is broken (teeth); no skip/xfail; test-only change.
