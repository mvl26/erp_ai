# dev-T21 — Runner (u2) gán người và (u4) comment (FEAT-006)

Nhánh `team/FEAT-006-task-21` (từ `team/FEAT-006` b6d3504).

## Thay đổi
- `erp_ai/agent/runner.py`: `_route` chạy (u1) -> kiểm SLA -> (u2) `_assign_unit` (chỉ khi `auto_assign`, ở L1+) -> (u4) `_comment_unit`; (u1) lỗi/`ok=false` thì không chạy phần còn lại. `_run_unit` bọc mỗi lần ghi (assign, comment) trong savepoint `erp_ai_route_unit` lồng trong savepoint `erp_ai_route` bên ngoài; ngoại lệ -> rollback đơn vị, action `ok=false` + lớp ngoại lệ, `error` thêm `route <tool>: <Lớp>`, không thử lại, không ném lên. `post_routing_comment` chỉ gọi khi `lines` khác rỗng, tối đa 1 lần. `value_after` thêm `"assign": [user]` khi có gán. Dòng info: `... applied=%d assigned=%d comment=%d sla=%s`.
- `erp_ai_setting.json`: `description` của `auto_assign_enabled` (382 ký tự, trong giới hạn 400).
- `test_doctype_descriptions.py`: tuple của `auto_assign_enabled` thêm "Assignment Rule", "chưa có ai được gán"; giữ các cụm cũ.
- `test_runner_routing.py`: thêm `TestRoutingAssign`, `TestRoutingNoOverride`, 3 ca `TestRoutingSla`; sửa 2 ca cũ vì hành vi mới (unpack dòng info có thêm `assigned`, `comment`; ca NO_SLA cũ không còn khẳng định "0 comment" vì T21 giờ gửi comment). Không nới assertion nào.
- `test_agent_runner.py`: không cần sửa (xanh nguyên trạng).

## RED (trước khi code, lý do: thiếu hành vi)
`bench --site miyano run-tests --module erp_ai.agent.test_runner_routing` -> `Ran 42 tests`, `FAILED (failures=8, errors=6)`, ví dụ:
- `test_assigns_configured_person_one_notification`: `AssertionError: Lists differ: [] != ['erpai-test-agent-...@example.com']`
- `test_no_sla_one_warning_one_comment`: `AssertionError: 0 != 1`
- `test_info_line_has_assigned_and_comment_flags`: `'assigned=%d comment=%d' not found in 'erp_ai route ticket=%s run_id=%s applied=%d sla=%s'`
- `test_agent_account_never_assigned_one_comment`: `ValueError: not enough values to unpack (expected 1, got 0)` (chưa có action `assign_owner`).
Để `patch.object(runner, "assign_owner")` không đỏ vì AttributeError, bước RED đã import tạm hai hàm vào runner.
Descriptions: `AssertionError: {'auto_assign_enabled': ['Assignment Rule']} != {}`.

## Mutation (STD-TEST-2)
Tạm đổi `if result:` -> `if True:`, `if auto_assign:` -> `if True:`, `if existing:` -> `if False:`: 13 ca đỏ (gồm `test_human_classified_no_route_writes`, `test_switch_off_no_todo_no_task`, `test_existing_assignment_kept`, `test_rule_assignment_in_route_save_kept`, `test_team_rule_assigns_bot_does_not`); đã hoàn tác. `test_l0_no_todo_no_task` khóa bởi `context is None` ở L0 (không có `_route`), không có đột biến tương đương ngoài việc bỏ rào đó.

## GREEN
- `erp_ai.agent.test_runner_routing`: `Ran 42 tests ... OK`
- `erp_ai.agent.test_agent_runner`: `Ran 56 tests ... OK`
- `erp_ai.tests.test_doctype_descriptions`: `Ran 10 tests ... OK`
- `--app erp_ai`: `Ran 823 tests in 151.215s ... OK`
- `pre-commit run --files <4 file>`: tất cả Passed (ruff-format tự sửa 2 file ở lần đầu, lần hai sạch).

## Ghi chú
- Savepoint: giữ savepoint ngoài `erp_ai_route` (bảo vệ cập nhật bản ghi log, như T20) và thêm `erp_ai_route_unit` cho từng đơn vị ghi sau (u1), vì dùng lại cùng một tên sẽ ghi đè savepoint ngoài.
- Khi (u2) thấy phiếu đã có người gán thì không comment (đúng AC-7a); khi công tắc tắt mà thiếu SLA thì vẫn 1 comment `NO_SLA` (design 4.2 bước 5).
- Seen but not touched: không có.
