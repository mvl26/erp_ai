# Review package FEAT-006 T22 (runner (u3) tạo Task cho C/D), vòng 1

Repo: `/home/miyano/frappe-bench/apps/erp_ai`. BASE=1b79b96; head=team/FEAT-006-task-22 (ada855c).
Lệnh diff (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai diff 1b79b96..team/FEAT-006-task-22 -- erp_ai`
Commits: `git -C /home/miyano/frappe-bench/apps/erp_ai log --oneline 1b79b96..team/FEAT-006-task-22`; stat: `git -C /home/miyano/frappe-bench/apps/erp_ai diff --stat 1b79b96..team/FEAT-006-task-22`.

Touchpoint T22: erp_ai/agent/runner.py, erp_ai/agent/test_runner_routing.py (mở rộng được chấp nhận nhưng không dùng: test_agent_runner.py, test_doctype_descriptions.py). Bốn test cũ đọc dòng info theo vị trí được đổi chỉ số vì dòng giờ có `task=%d` giữa `assigned` và `comment`.

Tiêu chí: dòng T22 của `docs/team/features/FEAT-006/tasks.md` (dòng 151-154): AC-13 (đúng 1 Task; chạy lại vẫn 1; đã có Task; đầu mục khác/không người → 0 Task; nhánh (i) chia sẻ tắt; nhánh (ii) đã có người từ trước), ADR-020 QĐ 7, A-12. (u3) chỉ khi `assigned` và `decision.needs_task`: `has_linked_task` có → action `create_routed_task` `ok=false` "phiếu đã có Task liên kết"; còn lại `create_routed_task(assigned, subject, classification, ctx)` trong MỘT savepoint cùng lần giao Task; ngoại lệ → rollback cả Task và ToDo của Task, `ok=false`, câu "không giao được Task cho người phụ trách (chia sẻ tài liệu đang tắt)" vào `lines` (comment (u4) gửi đúng 1 comment). `value_after["task"]`, dòng info `task=`.
Expect: `TestRoutingTask` 7 ca (test_c_ticket_one_linked_task_assigned, test_rerun_keeps_one_task, test_existing_linked_task_no_new_task, test_other_category_or_no_person_no_task, test_sharing_disabled_no_task_one_comment, test_preassigned_by_human_no_task_no_comment, test_preassigned_by_rule_no_task_no_comment).
Design: design.md cùng thư mục (3.5, 4.2 bước 4, 4.3, 5).

Điểm cần soi: (1) mỗi khẳng định đỏ khi bỏ hành vi nó khóa (dev báo đột biến: bỏ `needs_task`, `assigned`, `has_linked_task`, rollback đơn vị, câu `REASON_TASK_NOT_ASSIGNED` đều làm test đỏ; 3 test phủ định xanh ngay từ đầu nên cần đột biến chứng minh); (2) rollback đơn vị (u3) xóa Task và ToDo của Task, giữ ToDo của phiếu và (u1); (3) khi `create_routed_task` trả `ok=false` mà không ném (từ chối quyền), dev ghi action nhưng không thêm câu "chia sẻ tài liệu đang tắt" vì sẽ sai lý do: có chấp nhận được và có lỗ hổng comment không (người dùng thấy gì)?; (4) thứ tự (u3) trước (u4) để câu vào comment duy nhất; (5) test không phụ thuộc cấu hình thật của site (STD-TEST-6); (6) kỳ vọng cũ đổi chỉ số có nới lỏng không.
Ruling cũ giữ nguyên: nhánh `after_commit`/realtime của `assign_to.add` không bị rollback savepoint hủy (concern đã ghi ở review-21); `decision.notes` không vào `skipped_fields` khi (u1) lỗi.
