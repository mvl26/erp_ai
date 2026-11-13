# Review package R3 (rework 1, mục 3+4, T22/T22b)

BASE=f2ba6b8 (head của team/FEAT-006 trước R3), head team/FEAT-006-rw1-r3 (bb9ddf2). Run from `/home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/feat-006` (shared repo):
`git diff f2ba6b8..team/FEAT-006-rw1-r3 -- erp_ai`

## Commits
bb9ddf2 (1 commit; xem `git log --oneline f2ba6b8..team/FEAT-006-rw1-r3`)

## Stat
erp_ai/agent/runner.py 19; erp_ai/agent/tools/route_ticket.py 12; erp_ai/agent/tools/test_route_ticket.py 3; erp_ai/agent/test_runner_routing.py 54 (docs/.../dev-R3.md is the dev note, ignore it)

## Criteria (acceptance.md rework list, items 3 and 4)
- Item 3 (STD-ERR-1): `REASON_TASK_NOT_ASSIGNED` ("chia sẻ tài liệu đang tắt") may be used only when the exception is really "document sharing disabled" (route_ticket.py:27, runner.py `_task_unit`); any other exception of (u3) must get a general reason. The comment must not carry ticket content or raw exception detail. Still: action ok=false, savepoint rolled back (no Task, no ToDo of the Task), exactly 1 comment, the ticket's own ToDo stays.
- Item 4 (STD-TEST-2): a test that runs the runner with `disable_document_sharing` really turned on (no patching of create_routed_task, no faked exception), cleaned up afterwards (setting restored). A test for a non-sharing exception gets the general reason.
- Out of scope (team-leader accepted as a known limit): the "ghost notification" after rollback (acceptance item 7).
