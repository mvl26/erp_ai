# dev-T22 — Runner (u3) tạo Task cho C/D (FEAT-006)

Nhánh `team/FEAT-006-task-22` (từ `team/FEAT-006` 1b79b96). Files: `erp_ai/agent/runner.py`, `erp_ai/agent/test_runner_routing.py` (đúng touchpoint; `test_agent_runner.py` và `test_doctype_descriptions.py` không vỡ nên không sửa).

## Thay đổi
- `_route`: sau (u2) và trước (u4), `if assigned and decision.needs_task` -> `_task_unit`.
- `_task_unit`: `site_facts.has_linked_task` -> action `create_routed_task` `ok=false` "phiếu đã có Task liên kết"; còn lại `create_routed_task(...)` qua `_run_unit` (savepoint đơn vị lồng, Task và ToDo của Task chung một savepoint). Ngoại lệ -> rollback cả hai, `ok=false` + lớp ngoại lệ, câu `ASSIGN_REQUEST.format(reason=REASON_TASK_NOT_ASSIGNED)` vào `lines` (comment (u4) gửi đúng 1). Từ chối `ok=false` (không ngoại lệ) chỉ ghi action, không thêm câu (câu "chia sẻ tắt" sẽ sai lý do).
- Thành công: action ok=true tên Task, `value_after["task"]`, dòng info `... assigned=%d task=%d comment=%d sla=%s`.
- Test cũ chỉnh vì dòng info thêm `task` (vị trí tham số): `test_route_info_line_has_codes_only`, `test_broken_routing_rules_skip_sla_check_and_log_skipped`, `test_info_line_has_assigned_and_comment_flags`, `test_info_line_counts_the_posted_comment`.

## RED (trước khi code; chỉ thêm import `create_routed_task` vào runner để patch được)
`bench ... run-tests --module erp_ai.agent.test_runner_routing` -> `Ran 52 tests, FAILED (failures=1, errors=3)`:
- test_c_ticket_one_linked_task_assigned, test_rerun_keeps_one_task, test_existing_linked_task_no_new_task: `ValueError: not enough values to unpack (expected 1, got 0)` (không có Task / action `create_routed_task`)
- test_sharing_disabled_no_task_one_comment: `Expected 'create_routed_task' to have been called once. Called 0 times.`
- 3 test âm (other_category, preassigned x2) xanh sẵn, khóa bằng đột biến bên dưới.

## GREEN
- `--module erp_ai.agent.test_runner_routing` -> `Ran 52 tests ... OK`
- `--app erp_ai` -> `Ran 833 tests in 155.589s  OK`
- `pre-commit run --files runner.py test_runner_routing.py` -> tất cả Passed (ruff import/lint/format).

## Đột biến (chạy cả module, khôi phục sau mỗi lần)
| Đột biến | Test đỏ |
|---|---|
| bỏ `needs_task` (`if assigned:`) | test_assigns_configured_person_one_notification, test_info_line_has_assigned_and_comment_flags, test_other_category_or_no_person_no_task |
| bỏ `assigned` (`if decision.needs_task:`) | test_preassigned_by_human_no_task_no_comment, test_preassigned_by_rule_no_task_no_comment, test_rerun_keeps_one_task |
| bỏ `has_linked_task` | test_existing_linked_task_no_new_task |
| bỏ rollback đơn vị (`_run_unit`) | test_sharing_disabled_no_task_one_comment (+ 2 test (u2)/(u4) cũ) |
| bỏ câu REASON_TASK_NOT_ASSIGNED | test_sharing_disabled_no_task_one_comment |

## Ghi chú
- Test rollback: mock gọi `create_routed_task` thật (ghi Task + ToDo) rồi ném `PermissionError`; khẳng định Task = 0, ToDo Task không đổi, ToDo phiếu còn `[person]`, `applied`=1, đúng 1 comment chứa câu, lỗi không chứa subject phiếu.
- `test_rerun_keeps_one_task`: chạy `ticket_insert` lần hai (comment_mention không phân loại); lần hai (u2) `ok=false` nên không có action `create_routed_task`.
- Test dùng `pin_agent_roles` để không phụ thuộc quyền thật của site (STD-TEST-6).
