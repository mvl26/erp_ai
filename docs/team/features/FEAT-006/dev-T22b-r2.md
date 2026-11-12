# dev T22b round 2 - fix report (FEAT-006)

Branch: team/FEAT-006-task-22b-rework1 (created from team/FEAT-006-task-22b because that branch is checked out in another worktree).

## Finding
major | STD-TEST-2 | erp_ai/agent/test_runner_routing.py:970-972 | the runner test only used `assertIn` on the comment, so extra content (assignee, subject) on the fixed line would not be caught.

## Change
`test_sharing_disabled_no_task_one_comment`: replaced `assertIn(...)` and `assertNotIn("chưa gán được người", text)` with
`self.assertEqual(text, TASK_REQUEST.format(reason=REASON_TASK_NOT_ASSIGNED))`. No other file touched.

## Proof the test catches the bug
Temporary mutation in runner.py line 409: `TASK_REQUEST.format(...) + " " + subject`.
`erp_ai.agent.test_runner_routing` -> `FAIL: test_sharing_disabled_no_task_one_comment`, `Ran 53 tests ... FAILED (failures=1)`:
```
- Bot đã gán ... Nhờ trưởng nhóm giao Task. ERPAI-TEST-runner ticket
+ Bot đã gán ... Nhờ trưởng nhóm giao Task.
```
Mutation reverted (`git checkout erp_ai/agent/runner.py`).

## Green
- test_runner_routing module: `Ran 53 tests ... OK`
- `bench --site miyano run-tests --app erp_ai` (alone): `Ran 835 tests in 157.201s OK`
- `pre-commit run --files erp_ai/agent/test_runner_routing.py`: all hooks passed.

## Not touched
minor (stale comment at route_ticket.py:20, design 3.6 text) deferred to tech-lead per instruction.
