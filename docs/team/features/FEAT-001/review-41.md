# Review 41 — FEAT-001 T32 (Handler: ghi nhận người sửa phân loại)

Verdict: approve (sau 1 vòng rework)
Vòng: 2 (vòng 1 request-changes; vòng 2 scoped re-review approve)
Diff: `git diff 221187b..team/FEAT-001-task-32` (head 7a16d44; vòng 2: `git diff d03c508..team/FEAT-001-task-32`)

## Vòng 1 (review-raw-T32.md)
- major STD-TEST-8: bộ lọc `entry_type: classify` của `_latest_classify_log` không có test (hàng `reason` mới hơn che).
- minor: `creation=` không có tác dụng; cờ cũ không reset; nhánh không tới được + hai truy vấn; hằng TRIGGER cục bộ.
- Cần xác minh permlevel 8 (ai_classified_by là permlevel 8, mọi test dùng ignore_permissions).

## Vòng 2
Tất cả ADDRESSED (test `test_latest_classify_row_wins_over_newer_reason_row` đỏ khi bỏ bộ lọc; ghim `creation` bằng set_value; reset cờ đầu validate; cờ mang tên dòng log). Minor 4 hoãn theo phán quyết. Permlevel 8: Frappe chạy `validate_higher_perm_levels` (document.py:534) trước hook validate nên giá trị hook đặt được giữ; hai test (người dùng vai trò `Agent` thật không `ignore_permissions`; test vá `get_permlevel_access` bỏ mức 8 kèm đối chứng `ai_confidence` bị reset) hợp lệ, không bị che. Không DESIGN_CONFLICT.

## Bằng chứng dev
Vòng 1: RED 1 failure + 2 errors đúng lý do -> GREEN 27 OK, mutation từng guard đỏ. Vòng 2: test_handlers 31 OK, test_runner 52 OK, pre-commit pass, đếm 4/3/8/0/196 trước = sau.

## Deferred
- minor: tên cờ `erp_ai_human_corrected` nay chứa tên dòng log (STD-NAME-6); `human_corrected_at` đọc lại ở on_update.
- TRIGGER_HUMAN_CORRECTION về constants.py (ngoài touchpoint).
- `test_ticket_without_classify_log_saves_without_error` chỉ chồng lấp phủ; bộ lọc đã có test riêng.
- Dev báo còn một mục stash "On team/FEAT-001-task-32: t32" trong danh sách stash dùng chung (classifier chặn `git stash drop`); mục an toàn để xóa, chờ người xử lý, không tự xóa.
