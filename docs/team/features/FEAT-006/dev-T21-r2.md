# dev T21 rework 1 (vong 2/3) — FEAT-006

Branch `team/FEAT-006-task-21-rework1` from `team/FEAT-006-task-21` (8de1908). Only `erp_ai/agent/test_runner_routing.py` changed (the code in runner.py was already correct; the findings were test gaps).

| Finding | Change | Test | Mutation proof (runner.py mutated, then restored) |
|---|---|---|---|
| major 1 STD-TEST-8 | two new tests: the mock really writes (`assign_to.add` / real `post_routing_comment`) then raises | `test_assign_that_wrote_then_raised_is_undone_but_route_kept`, `test_comment_that_wrote_then_raised_is_undone_but_route_kept`: ToDo == [] / comment count unchanged, ticket `agent_group`/`priority` still (u1) values (team, "Urgent"), `applied == 1`, error line | remove `rollback(ROUTE_UNIT_SAVEPOINT)` (runner.py:344) -> both FAIL; roll back to outer `ROUTE_SAVEPOINT` -> both FAIL |
| major 2 STD-TEST-2 | new test with agent account (a comment is posted) asserts info args `(1, 0, 1, "ok")` | `test_info_line_counts_the_posted_comment` | hard-code `0` for comment (runner.py:470) -> that test FAIL (the old one stayed green, as the reviewer said) |
| major 3 STD-TEST-2 | `assertEqual(action["rule"], frappe.db.get_value("HD Team", team, "assignment_rule"))` | `test_team_rule_assigns_bot_does_not` | rule := user name -> `test_team_rule_assigns_bot_does_not` and `test_existing_assignment_kept` FAIL |
| minor duplicate tests | skipped (dev's call, per tech-lead) | | |
| minor design 4.2 savepoint name | not touched, deferred to team-leader/designer: design 4.2 should name `erp_ai_route_unit` | | |

RED note: the findings are missing assertions on code that already behaves correctly, so the new tests are green on the current code; their red is shown by the mutations above (each run: `Ran 45 tests ... FAILED` with the named tests).

## after_commit / realtime check (frappe `assign_to.py`, `notification_log.py`, `utils/background_jobs.py`, `database.py`)
Conclusion: `assign_to.add` -> `notify_assignment` -> `enqueue_create_notification` uses `frappe.enqueue(enqueue_after_commit=True)` in production, which registers a callback in `frappe.db.after_commit`; `rollback(save_point=...)` does not clear it (only a full rollback does), and the ToDo/Notification Log realtime publishes use `after_commit=True` likewise. So a ghost notification is possible only if the exception is raised AFTER `notify_assignment` inside `assign_to.add` (it is the last step of the loop; what follows is `msgprint` and `get(args)`), or if our own code raised after a successful `assign_owner` (nothing does: the ok-path releases the savepoint). A fix would need to poke `CallbackManager._functions` (private) and is not a touchpoint-sized change -> no code change; recorded as concern (low probability).

## Commands and output
- `PYTHONPATH=<worktree> bench --site miyano run-tests --module erp_ai.agent.test_runner_routing` -> `Ran 45 tests in 20.886s OK`
- `... erp_ai.agent.test_agent_runner` -> `Ran 56 tests in 10.437s OK`
- `... erp_ai.tests.test_doctype_descriptions` -> `Ran 10 tests in 0.326s OK`
- `... run-tests --app erp_ai` -> `Ran 826 tests in 152.297s OK`
- `pre-commit run --files erp_ai/agent/test_runner_routing.py` -> all hooks Passed/Skipped
- no skip/xfail/only added.
