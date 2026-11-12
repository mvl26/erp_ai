# Review T24 vòng 2 (scoped re-review) — request-changes

Diff fix: `git -C /home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/feat-006 diff 8439972..team/FEAT-006-task-24-rework1 -- erp_ai` (1cb487e). Mã sản xuất không đổi.

## Đối chiếu vòng 1

- major 1 (NFR-4): NOT ADDRESSED cho đường comment; đạt cho prefixes, 2 ca `routing_rules` hỏng (`BAD_ROUTING_ERROR`), logger, `log_error`, cột nhật ký, Task.
- major 2 (AC-17): ADDRESSED (ghim role ở `RoutingTestBase.setUp`, test role set = tập ghim; reviewer chấp nhận việc bỏ ghim chỉ làm 3 test khẳng định role đỏ).
- minor (a), (b), (c): ADDRESSED; (d), (e): không làm (minor, không chặn).

## Finding mới (nguyên văn)

major | STD-TEST-2 | erp_ai/agent/test_runner_routing.py:341-359 | NFR-4: when the key is in routing_config, no Comment is posted (lagging SLA + valid person, so `lines` is empty), so assertNotIn on "comment" can never fail; echoing routing_config into the comment stays green | add a subtest with the key in prefixes and `_arrange_c_writes(self, None)` (NO_SLA, which posts a comment) or a prefix pointing to AGENT_USER; assert exactly 1 comment was posted, then _assert_no_key | confirmed

minor: `test_agent_roles_are_the_pinned_set_in_every_case` (:317) kiểm một ca, tên nói "every case" (STD-NAME-6): đổi tên cho đúng.

## Deferred

- Bad-rules subtests tạo phiếu bằng `make_ticket` khi agent đã bật (pattern có sẵn từ :1406).
- Câu hỏi cho designer: `value_before` vs design 3.5 (`assign`/`task`); mở rộng hàng test-plan 493 thành "mọi đầu vào cấu hình lần chạy đọc".
