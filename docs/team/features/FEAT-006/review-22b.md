# Review T22b — approve (vòng 2)

Feature: FEAT-006 · Task: T22b (câu comment (u4) đúng từng ca) · Reviewer: team:reviewer · Số vòng: 2 (1 vòng sửa)

Lệnh diff: vòng 1 `git diff 9f3d789..team/FEAT-006-task-22b -- erp_ai` (8282aae); vòng 2 (scoped) `git diff 8282aae..team/FEAT-006-task-22b-rework1 -- erp_ai` (5c2215b). Merge a0bf05b.

## Verdict: approve

- Vòng 1: request-changes, 1 major STD-TEST-2 (test runner chỉ `assertIn` câu; không bắt được tên người/subject chèn thêm), chi tiết ở `review-22b-round1.md`.
- Vòng 2: ADDRESSED (`assertEqual(text, TASK_REQUEST.format(...))`, dev chứng minh đỏ bằng đột biến chèn subject vào câu). Không finding mới.

## Kiểm bằng lệnh thật

- Dev: `erp_ai.agent.test_runner_routing` Ran 53 OK; `erp_ai.agent.tools.test_route_ticket` Ran 29 OK; `bench --site miyano run-tests --app erp_ai` Ran 835 tests OK (đầu nhánh task 5c2215b); lint pre-commit pass.
- Tech-lead: `git diff --stat 5c2215b HEAD -- . ':!docs'` rỗng sau merge a0bf05b.

## Deferred

- minor: `route_ticket.py:20` comment "design 3.6" lỗi thời; design.md 3.6 (dòng 251-254), 4.2 bước 4 (dòng 294), tasks.md:153 còn câu cũ → designer cập nhật khi gộp (`TASK_REQUEST`, reason "chia sẻ tài liệu đang tắt").
