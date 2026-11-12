# dev-T24 — Test chốt AC-9, AC-16, AC-17, NFR-4 (FEAT-006)

Nhánh `team/FEAT-006-task-24` (từ `team/FEAT-006` 9135b85). Mã sản xuất không đổi; chỉ hai file test.

## Bảng test -> đột biến -> đầu ra đỏ

Mỗi đột biến áp tạm vào mã sản xuất (hoặc vào dòng ghim của test), chạy `erp_ai.agent.test_runner_routing` / `erp_ai.agent.tools.test_registry`, rồi hoàn tác bằng `git checkout --` (kiểm `git status --short` chỉ còn hai file test).

| Test | Đột biến | Khẳng định hỏng |
|---|---|---|
| `test_ticket_text_does_not_steer_route` | `TOOL_MODULES` thêm `route_ticket` có `TOOLS` bọc `assign_owner` | `assertEqual(self._assigned_to(), [self.person])`: `[person, 'Administrator'] != [person]` |
| `test_ticket_text_does_not_steer_route` | `apply_route` ghi `response_by`/`resolution_by` = `creation` sau `save()` | `assertGreater((stored_at - creation).total_seconds(), 60)`: `0.0 not greater than 60` |
| `test_every_write_in_actions_with_before_after` | `before` trong `apply_route` lấy giá trị mới | `value_before["ticket"][field] == before[field]`: `'ERPAI-TEST-route-type' != ''` (trường `ticket_type`) |
| `test_every_write_in_actions_with_before_after` | `after` báo `priority` = `Low` | `value_after["ticket"][field] == after[field]`: `'Low' != 'High'` (trường `priority`) |
| `test_every_write_in_actions_with_before_after` | `_record_route` bỏ `after["assign"]` | `set(value_after) == {"ticket","assign","task"}`: thiếu `'assign'` |
| `test_refusals_have_ok_false_reason` | `_route_action` bỏ khóa `reason` | cả ba ca con đỏ: `KeyError: 'reason'` ở `apply_route` (người đã phân loại), `assign_owner` (đã có người), `create_routed_task` (đã có Task) |
| `test_success_cases_under_pinned_roles` | `assign_owner` chèn Has Role `System Manager` cho tài khoản agent | `assertEqual(self._agent_roles(), PINNED_ROLES)`: `'System Manager'` thừa |
| `test_success_cases_under_pinned_roles` | bỏ dòng `pin_agent_roles(self)` trong `setUp` | `assertEqual(self._agent_roles(), PINNED_ROLES)`: 97 role thừa của site (`Translator`, `PM Manager`, ...) |
| `test_privilege_findings_unchanged` | như đột biến chèn Has Role | `assertEqual(self._findings(), before)`: `role_drift ['thừa role System Manager']`, `permission_records ['Has Role ...']`, hai cảnh báo mới |
| `test_privilege_findings_unchanged` | bỏ dòng ghim | `assertEqual(before["role_drift"], [])`: 97 phần tử thừa |
| `test_fake_key_absent_from_comment_log_task` | `NO_SLA` chứa khóa giả | `assertNotIn(FAKE_KEY, ...)` ở `comment <tên>` |
| `test_fake_key_absent_from_comment_log_task` | cột `error` của nhật ký chứa khóa giả | `assertNotIn(FAKE_KEY, ...)` ở dòng nhật ký |
| `test_fake_key_absent_from_comment_log_task` | mô tả Task chứa khóa giả | `assertNotIn(FAKE_KEY, ...)` ở `TASK-2026-00001` |
| `test_no_tool_schema_takes_person_sla_priority_or_score` | thêm thuộc tính `assignee` vào schema `set_classification` | `'assign' unexpectedly found in 'assignee' : set_classification accepts assignee` |
| `test_no_tool_schema_takes_person_sla_priority_or_score` | `route_ticket` vào `TOOL_MODULES` có tool nhận `user` | `'user' unexpectedly found in 'user' : assign_owner accepts user` |
| `test_route_functions_not_executable_as_tools` | như đột biến trên | `assertNotIn(name, granted)`: `'assign_owner' unexpectedly found in [... 'assign_owner']` |

Không có đỏ nào do import/cú pháp: các đột biến chỉ đổi giá trị hoặc thêm dòng hợp lệ.

## Ghi chú thiết kế test
- Lớp mới `TestRoutingInjection`, `TestRoutingPermissions` kế thừa `AssignTestBase`. `TestRoutingLog`, `TestRoutingEndToEnd` có sẵn kế thừa `RoutingTestBase` (đổi nền sẽ phá test cũ), nên dùng hai hàm cấp module mới `_configure_c`, `_arrange_c_writes` (tạo người, team, cấu hình, SLA giả, ghim role) thay cho `AssignTestBase`. `_configure_c` trùng nội dung `TestRoutingTask._configure_c`, giữ lại để không sửa test cũ.
- Ca SLA (AC-9): Helpdesk tự tính lại ngày SLA mỗi lần lưu phiếu, nên cuối lượt không còn thấy ghi của tầng định tuyến. Test đọc ngày ngay sau `apply_route` (qua `side_effect` bọc hàm thật) và ở cuối.
- `before`/`after` (AC-16) so với giá trị đọc từ DB trước/sau lần chạy, và tập khóa phải đúng tập trường đã đổi (`ai_classified_by`, `ai_updated_at` không nằm trong hợp đồng before/after nên không xét).
- Ca từ chối (AC-16) có cả `ok is False` lẫn chuỗi lý do cụ thể, và kiểm không có ghi nào (không ToDo, không Task mới).
- Test registry dùng `REAL_ALL_SPECS` vì `TestRegistry.setUp` thay `_all_specs` bằng giả.

## Kết quả cuối
- `erp_ai.agent.test_runner_routing`: Ran 59 tests, OK (6 test mới, trước đó 53).
- `erp_ai.agent.tools.test_registry`: Ran 26 tests, OK (2 test mới).
- `--app erp_ai`: Ran 849 tests, OK.
- `pre-commit run --files <hai file>`: tất cả Passed (ruff-format tự sửa một lần, chạy lại sạch).
- Seen but not touched: không có.
