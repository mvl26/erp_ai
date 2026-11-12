# Dev T24 round 3 - fix report (FEAT-006)

Branch: team/FEAT-006-task-24-rework2 (from rework1; rework1 is checked out in another worktree).

## Finding 1 (major, NFR-4 comment path)
- Change: new test `test_fake_key_in_prefixes_absent_from_the_posted_comment` in erp_ai/agent/test_runner_routing.py. Key in `prefixes`, `_arrange_c_writes(self, None)` (NO_SLA), so the run posts a comment; asserts `post_routing_comment` in the actions, exactly 1 comment, then `_assert_no_key` over log/comment/task/logger/log_error.
- Mutation (reverted): `post_routing_comment` returned `post_comment({"content": "\n".join(lines) + str(ctx.routing_config)}, ctx)`.
  Command: `bench --site miyano run-tests --module erp_ai.agent.test_runner_routing` ->
  `FAIL: test_fake_key_in_prefixes_absent_from_the_posted_comment` - `AssertionError: 'sk-ERPAI-LEAK-7c1e9d' unexpectedly found in '[{"name": ..., "content": "Chưa có SLA ... {'assignees': ...` : comment`; also test_sharing_disabled_no_task_one_comment red. `Ran 61 tests, FAILED (failures=2)`.
- After `git checkout erp_ai/agent/tools/route_ticket.py`: `git status` shows only the test file modified; module `Ran 61 tests OK`.

## Minor (STD-NAME-6)
- Renamed `test_agent_roles_are_the_pinned_set_in_every_case` -> `test_agent_roles_are_the_pinned_set_in_the_base_setup`.

## Full run
- `--app erp_ai`: Ran 851 tests, OK.
- `pre-commit run --files erp_ai/agent/test_runner_routing.py`: all Passed (ruff linter/formatter included).
