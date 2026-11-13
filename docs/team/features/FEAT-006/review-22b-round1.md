# Review T22b vòng 1 — request-changes

Diff: `git -C /home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/feat-006 diff 9f3d789..team/FEAT-006-task-22b -- erp_ai`. Commit 8282aae. Checklist 10/10; lớp 1 (spec) đạt.

## Findings (nguyên văn từ reviewer)

major | STD-TEST-2 | erp_ai/agent/test_runner_routing.py:970-972 | Part of the criterion ("câu cố định, không tên người/nội dung phiếu") is not checked where the comment is built. Only the constant is pinned, by `assertEqual` in `test_route_ticket.py:429-437`. The runner test checks the posted comment with `assertIn(TASK_REQUEST.format(...), text)` and `assertNotIn("chưa gán được người", text)`. If the runner added the assignee or the ticket subject to that line, the test would still pass. The checks on `self.ticket.subject` look at `entry.error` and `entry.actions`, not at the comment. | In this test there is no SLA sentence: `AssignTestBase` patches `applied_sla` with `resolution_s=None`. So use `assertEqual(text, TASK_REQUEST.format(reason=REASON_TASK_NOT_ASSIGNED))`. If `post_comment` changes the content, use `assertNotIn` for `self.person`, its full name and `self.ticket.subject` on `text` instead.

minor | — | route_ticket.py:20 | Comment "Fixed sentences for the routing comment (design 3.6)" lỗi thời cho tới khi design 3.6 liệt kê `TASK_REQUEST`. (Deferred: design amendment.)

## Cannot verify (tech-lead xử lý)

- design.md 3.6 (dòng 251-254), 4.2 bước 4 (dòng 294), tasks.md:153 còn câu cũ → ghi vào "Việc dặn trước": designer sửa khi gộp (không phải lỗi dev; ngoài touchpoint).
- BASE trong progress-c5: sửa thành 9f3d789 (đã sửa ở tick).
