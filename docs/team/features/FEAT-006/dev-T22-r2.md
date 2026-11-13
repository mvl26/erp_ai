# Dev T22 rework 1 (vòng 2/3)

Branch `team/FEAT-006-task-22-rework1` (từ `team/FEAT-006-task-22` ada855c). Chỉ sửa `erp_ai/agent/test_runner_routing.py`; runner.py không đổi.

| Finding | Thay đổi | Test phủ | Lệnh + đầu ra |
|---|---|---|---|
| major STD-TEST-8: `create_routed_task` trả `ok=false` không ném | Thêm `test_refused_task_without_exception_no_task_no_comment`: patch trả `{"ok": False, "reason": "thiếu quyền tạo Task"}`; khẳng định action `ok=false` đúng reason, 0 Task, ToDo của phiếu từ (u2) còn (`_assigned_to() == [person]`), 0 comment mới, không có `task` trong value_after | chính test đó | Đột biến `if len(errors) > failures:` -> `if True:` (luôn thêm câu): `FAIL: test_refused_task_without_exception_no_task_no_comment`, `AssertionError: 1 != 0` (assertion `_comment_count() == before_comments`). Hoàn nguyên đột biến, test xanh. |
| major STD-TEST-6: đếm ToDo toàn site | `test_existing_linked_task_no_new_task`: `before_todos = self._task_todos(self.person)` rồi `assertEqual(self._task_todos(self.person), before_todos)`; lọc theo `allocated_to` và lấy hiệu, ToDo Task của user khác không ảnh hưởng | test đó | `Ran 53 tests ... OK` (test_runner_routing) |
| minor (i) PermissionError mô phỏng | Giữ nguyên (đường thật đã có ở test_route_ticket.py:499; ca hiện tại kiểm rollback chặt hơn). Không đổi `disable_document_sharing`. | - | - |

Rulings (a)-(c): không đổi mã (a giữ; b, c deferred cho designer/team-leader).

Kết quả:
- test_runner_routing: `Ran 53 tests in 27.073s` OK
- test_agent_runner: `Ran 56 tests in 11.192s` OK
- `bench --site miyano run-tests --app erp_ai`: `Ran 834 tests in 157.432s` OK
- `pre-commit run --files erp_ai/agent/test_runner_routing.py`: tất cả Passed (ruff lint/format Passed)
