# Review T22 vòng 1 — request-changes (nguyên văn từ reviewer)

BASE=1b79b96, head ada855c (`team/FEAT-006-task-22`).

- major | STD-TEST-8 | erp_ai/agent/runner.py:406 (test thiếu ở test_runner_routing.py) | Nhánh `if len(errors) > failures` tách hai trường hợp: ném ngoại lệ thì thêm câu, còn trả về `ok=false` thì không thêm câu. Chưa test nào cho `create_routed_task` trả `{"ok": False}` mà không ném. Đột biến "luôn thêm câu" vẫn xanh (kiểm bằng đọc mã) | Thêm ca: patch `create_routed_task` trả `{"ok": False, "reason": "thiếu quyền tạo Task"}`, rồi khẳng định action `ok=false` đúng reason, 0 Task và 0 comment
- major | STD-TEST-6 | erp_ai/agent/test_runner_routing.py:915 | `assertEqual(self._task_todos(), 0)` đếm mọi ToDo `reference_type="Task"` trên cả site, không lọc theo user hay reference và không lấy hiệu. Site chỉ cần còn sót một ToDo của Task là test đỏ | Dùng `_task_todos(self.person)`, hoặc lấy hiệu so với `before` như hai test kia
- minor | — | — | test (i) mô phỏng lỗi bằng `PermissionError` builtin, trong khi test plan 473 ghi `disable_document_sharing=1`. Đường lỗi thật đã có `test_route_ticket.py:499 test_sharing_disabled_raises`. Test hiện tại còn ghi thật Task + ToDo rồi mới ném, nên kiểm rollback chặt hơn | dev quyết

Cannot verify (tech-lead chốt):
(a) Bị từ chối không ném (thiếu quyền tạo Task / không có DocType): phiếu đã có người được gán, không Task, không comment; chỉ log ghi. Ruling: giữ (design 4.2 bước 4 chỉ định comment "không giao được Task…" cho ngoại lệ chia sẻ; thêm câu này cho lý do khác là sai lý do). Ghi vào deferred cho team-leader/designer để chốt có cần câu riêng.
(b) Câu comment "Bot chưa gán được người phụ trách…: không giao được Task…" khi phiếu đã được gán: đúng chữ design 4.2:294, người đọc dễ nhầm: deferred cho designer.
(c) Chưa có ca đầu mục D trong runner: `needs_task` tính ở `decide_route` (đã có test ở test_routing.py); không bắt buộc.
