# Review package FEAT-002 T6 round 2 (scoped re-review)

FIX_BASE c663cbb .. team/FEAT-002-task-6 (head 1aa8bb2). Diff: `docs/team/features/FEAT-002/review-pkg-T6-r2.diff` (`git diff c663cbb..team/FEAT-002-task-6`).

## Round 1 findings to mark ADDRESSED / NOT ADDRESSED
1. major STD-TEST-2 test_runner_status.py: summary line delay_s/waited_s unchecked. Required: (a) comment_mention 4/4 no post_comment -> [4, 0]; (b) 4/4, model_seconds=1, _answer_turns() -> [4, 3]; (c) ticket_insert -> [0, 0].
2. major STD-TEST-2 test_feature_adds_no_comment_task_or_ticket_change: rewrite as design 8.1 on/off comparison with post_comment (savepoint, run on, record, rollback, run off, equal tuples).
3. minors: unused `run=None` param, `call` shadowing mock.call, redundant assertLess, _end_status must not raise from finally (guard added + 2 tests).

## Dev evidence (raw)
test_runner_status Ran 30 OK; test_agent_runner 56 OK; test_run_status 7 OK; tests.test_handlers 31 OK; tests.test_architecture 44 OK. Mutations (swap delay/waited, always 0/0, None-branch 1, feature changes ticket, feature adds Comment) each go red.
