# Review package FEAT-006 T12, vòng 2 (scoped re-review)

BASE=449e2b5; head=team/FEAT-006-task-12-rework1 (1db4533; một commit trên c52968e).
Chỉ xét fix: `git -C /home/miyano/frappe-bench/apps/erp_ai diff c52968e..1db4533` (toàn bộ: `git diff 449e2b5..1db4533`, 2 file).

Findings vòng 1 cần đánh dấu ADDRESSED / NOT ADDRESSED:
1. major | STD-TEST-8 | test_install.py:337 (install.py:214-215) | bảo vệ "Task chưa cài" của `_ensure_task_ticket_field` không được test thật (setUp đã tạo `Task-ai_ticket`); cần xóa Custom Field trước `ensure_setup` rồi kiểm vẫn vắng.
2. major | STD-TEST-8 | test_install.py:228 (install.py:241-245) | thiếu dòng "mồi" (decoy) cho bộ lọc `share` trên đúng dòng; cần 3 dòng mồi giữ share=0 và `_other_task_perms` chọn thêm `share`.
3. major | STD-TEST-6 | test_install.py:239 | `get_meta("Task")` trong giao dịch có thể để lại meta cũ trong cache redis sau rollback; sửa đề xuất: `addCleanup(frappe.clear_cache, doctype="Task")`. Đánh dấu theo mã: cleanup có đặt đúng chỗ, chạy sau (LIFO) rollback hay không; việc có tái hiện được meta cũ hay không thì kết luận từ đọc mã Frappe, ghi rõ nếu không chắc.
Minor dev đã làm: comment install.py:96 dẫn design 2.4/3.3; dùng `TASK_DOCTYPE` trong `_ensure_task_permission`; test score fields so cả tập fieldname.
Dev báo đã phá từng bảo vệ để chứng minh đỏ (bỏ guard Task; bỏ `if_owner`; bỏ `permlevel`), rồi hoàn tác.
Bằng chứng dev: `test_install` 32 OK; `cmd.test` 738 OK; lint pass.
Ngoài phạm vi -> `deferred`.
