# dev T24 vòng 2 — báo cáo sửa (FEAT-006)

Nhánh `team/FEAT-006-task-24-rework1` (từ `team/FEAT-006-task-24`, vì nhánh gốc đang checkout ở worktree khác). Chỉ sửa `erp_ai/agent/test_runner_routing.py`; mã sản xuất không đổi (đã hoàn nguyên sau mỗi đột biến). `test_registry.py` không cần đổi.

## Finding -> thay đổi -> test phủ

1. NFR-4 (major): `test_fake_key_in_read_config_absent_from_comment_log_task_logger` gieo FAKE_KEY vào `assignees.*.prefixes` (chạy hợp lệ, có Task, giao việc, cảnh báo SLA chậm) và vào 2 ca `routing_rules` hỏng (không phải JSON; khóa gốc lạ) đi đường `BAD_ROUTING_ERROR`. Chụp `frappe.logger` (`mock_calls`) và `log_error`, `assertNotIn` ở cột log (`*`), Comment, Task, logger, log_error. Khẳng định lần chạy có thật (chuỗi action, 1 Task + ToDo, 1 dòng info route, 1 warning, `error` có BAD_ROUTING_ERROR).
   - Ghi chú: ca "FAKE_KEY làm người phụ trách mặc định" bị bỏ: mã cố ý nêu tên người trong lý do (`<user> không phải HD Agent đang hoạt động`), tên người không phải bí mật.
2. AC-17 (major): `RoutingTestBase.setUp` gọi `pin_agent_roles(self)` (sau dọn rollback); bỏ các lệnh ghim trùng ở `_arrange_c_writes`, TestRoutingTask, TestRoutingInjection, TestRoutingPermissions. Test mới `test_agent_roles_are_the_pinned_set_in_every_case` khẳng định role set = {ERP AI Agent, Agent}. Cả file 60 ca xanh dưới role ghim, không ca cũ nào phải sửa.
3. (a) xóa `TestRoutingTask._configure_c`, dùng hàm module. (b) literal `"phiếu đã có Task liên kết"`, bỏ import `REASON_TASK_EXISTS`. (c) `test_ticket_text_does_not_steer_route` tự tạo SLA mặc định duy nhất (tắt SLA khác), khẳng định `sla` == SLA đó và cả hai mốc ngày có giá trị (> 60 s sau creation); bỏ `if stored_at:`.

## Đỏ trước (AC-17)
`--test test_agent_roles_are_the_pinned_set_in_every_case` trước khi ghim: FAIL, role set ~99 role (Internal Auditor, Customer, Accounts User ...) != {ERP AI Agent, Agent}.

## Đột biến (đã hoàn nguyên, `git diff` mã sản xuất = 0)
- runner.py:277 `BAD_ROUTING_ERROR + frappe.get_single(...).routing_rules[:40]` (cột `error`): 2 subTest FAIL, "sk-ERPAI-LEAK-7c1e9d unexpectedly found".
- runner.py:473 cảnh báo SLA thêm `context.routing_config`: FAIL, key trong `logger.mock_calls`.
- route_ticket.py `description` Task thêm `ctx.routing_config`: FAIL, key trong Task.
- Bỏ `pin_agent_roles` khỏi base và các lớp con: chỉ 3 ca khẳng định role đỏ (`test_agent_roles_are_the_pinned_set_in_every_case`, `test_success_cases_under_pinned_roles`, `test_privilege_findings_unchanged`); không ca AC-6/SLA nào khác biệt vì site không có role thừa nào làm đổi kết quả. Chưa có đột biến cho nhánh comment (ca A của NFR-4 không đăng comment).

## Lệnh
- `bench --site miyano run-tests --module erp_ai.agent.test_runner_routing`: Ran 60, OK.
- `... erp_ai.agent.tools.test_registry`: Ran 26, OK.
- `--app erp_ai`: Ran 850 tests, OK.
- `pre-commit run --files erp_ai/agent/test_runner_routing.py`: tất cả Passed (ruff format đã tự sửa 1 lần, chạy lại Passed).

Chưa làm: (d), (e) (minor, ngoài danh sách yêu cầu).
