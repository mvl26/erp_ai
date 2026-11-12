# dev-R3 — rework 1, mục 3 + 4 (FEAT-006, T22/T22b)

Nhánh `team/FEAT-006-rw1-r3` (từ `team/FEAT-006` f2ba6b8).

## Mục 3 — câu "chia sẻ tài liệu đang tắt" chỉ cho lỗi chia sẻ tắt (STD-ERR-1)
Thay đổi:
- `route_ticket.py`: lớp `TaskSharingDisabled(frappe.ValidationError)`; hằng `REASON_TASK_FAILED = "giao Task không thành công"`.
  `create_routed_task` tự kiểm điều kiện (`disable_document_sharing` bật và người được giao không có quyền trên Task) ngay sau `task.insert()`, trước `assign_to.add`, rồi ném `TaskSharingDisabled` (không dò chuỗi thông điệp). Là lớp con của `ValidationError` nên tương thích ngược.
- `runner.py` `_task_unit`: bọc lời gọi, ghi cờ khi bắt `TaskSharingDisabled` (rồi ném lại); lý do = `REASON_TASK_NOT_ASSIGNED` nếu có cờ, ngược lại `REASON_TASK_FAILED`. Giữ nguyên action `ok=false`, rollback savepoint, 0 Task, 1 comment; comment không chứa nội dung phiếu/ngoại lệ thô.

## Mục 4 — test (STD-TEST-2)
- `test_runner_routing.py::TestRoutingTask::test_sharing_disabled_no_task_one_comment` viết lại: chạy runner với `disable_document_sharing` bật THẬT (System Settings, helper `_disable_document_sharing` có addCleanup trả giá trị cũ + xoá cache), không vá `create_routed_task`; người giao chỉ có role Agent (khẳng định không đọc được Task). Khẳng định: 0 Task, ToDo Task không đổi, ToDo phiếu vẫn là người được gán, action ok=false reason `TaskSharingDisabled`, 1 comment = `TASK_REQUEST.format(reason=REASON_TASK_NOT_ASSIGNED)`.
- Thêm `test_other_exception_generic_reason_not_sharing`: vá `create_routed_task` ghi Task rồi ném `RuntimeError` kiểu DB -> comment dùng `REASON_TASK_FAILED`, không chứa "chia sẻ tài liệu đang tắt" và không chứa chi tiết ngoại lệ.
- Test vá-`PermissionError` cũ được thay bằng hai test trên (STD-TEST-5: nó khẳng định đúng cái hành vi sai là mục 3, câu chia sẻ cho mọi ngoại lệ; spec đổi).
- `test_route_ticket.py::test_sharing_disabled_raises`: nay `assertRaises(TaskSharingDisabled)` (chặt hơn `ValidationError`).

## Đỏ
- `test_runner_routing`: `test_sharing_disabled_no_task_one_comment`: `(False, 'ValidationError') != (False, 'TaskSharingDisabled')`; `test_other_exception_generic_reason_not_sharing`: comment `...chia sẻ tài liệu đang tắt...` != `...giao Task không thành công...`.
- `test_route_ticket`: `test_sharing_disabled_raises` ERROR: `ValidationError: User ... is not permitted ...` (không phải `TaskSharingDisabled`).
(Lý do đúng: hành vi thiếu; hằng và lớp đã khai báo trước nên không đỏ vì import.)

## Xanh
- `bench --site miyano run-tests --module erp_ai.agent.test_runner_routing` -> Ran 62 tests, OK
- `... --module erp_ai.agent.tools.test_route_ticket` -> Ran 29 tests, OK
- `bench --site miyano run-tests --app erp_ai` -> Ran 884 tests, OK
- `pre-commit run --files <4 file>` -> tất cả Passed (ruff import/lint/format).

Seen but not touched: không có.
