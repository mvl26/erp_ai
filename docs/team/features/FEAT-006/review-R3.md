# Review R3 (T22/T22b, rework 1, mục 3+4) — approve

- Verdict: approve, 1 vòng (max_rework=3).
- Diff: `git diff f2ba6b8..team/FEAT-006-rw1-r3 -- erp_ai` (BASE f2ba6b8, đầu bb9ddf2). Merge vào `team/FEAT-006`.
- Mục 3: `create_routed_task` ném lớp mới `TaskSharingDisabled` (con của `frappe.ValidationError`) khi `disable_document_sharing` bật và người được giao không đọc được Task; runner dùng câu "chia sẻ tài liệu đang tắt" chỉ cho lớp này, ngoại lệ khác dùng `REASON_TASK_FAILED` ("giao Task không thành công"). Không có nội dung phiếu hay chi tiết ngoại lệ trong comment.
- Mục 4: test chạy runner với `disable_document_sharing` bật thật, không vá `create_routed_task`, có dọn lại; test ngoại lệ RuntimeError -> lý do chung. Test cũ vá `PermissionError` được thay (nó khẳng định đúng cái lỗi mục 3). `test_route_ticket` đổi kỳ vọng sang `TaskSharingDisabled` (STD-TEST-5: đổi hành vi có chủ đích).
- Bằng chứng (dev): đỏ `(False, 'ValidationError') != (False, 'TaskSharingDisabled')` và comment còn câu "chia sẻ tài liệu đang tắt"; xanh `test_runner_routing` Ran 62 OK, `test_route_ticket` Ran 29 OK, cmd.test toàn app Ran 884 OK; pre-commit sạch.

## deferred
- minor: `route_ticket.py:115` lặp điều kiện kiểm tra của Frappe `assign_to.py:123` (STD-DESIGN-4); cờ `sharing_off` ở `runner.py:407` có thể thay bằng đọc lý do action cuối.
- minor STD-DOC-4: design.md 3.6 và dòng 229 chưa nhắc `REASON_TASK_FAILED`, `TaskSharingDisabled`; ghi ở As-Built.
