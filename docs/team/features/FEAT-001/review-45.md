# Review 45 — FEAT-001 T35 (Job mỗi giờ: dò lại khóa hết hạn mức)

Verdict: approve
Vòng: 1 (không rework)
Diff: `git diff 11e5775..team/FEAT-001-task-35` (d143b42; 3 file: tasks.py, hooks.py, tests/test_tasks.py)
Reviewer: team:reviewer, checklist (10) đủ 10/10; không blocker, không major.

## Tầng 1
Khớp design 3.7/4.5/4.7 và D-20: job chỉ gọi `gateway.reprobe_exhausted_keys()` (gateway đã lọc `Hết hạn mức`, đổi `Hoạt động` và gửi đúng một `send_notice` mỗi khóa hồi phục), job không gửi tin thêm; hợp đồng lỗi D-20 (try/except, rollback, `log_error(TITLE_RUN_FAILED, message tường minh)`, commit khi không `in_test`). hooks: hourly [reprobe_exhausted_keys]; daily [recompute_monthly_spend, check_privilege_escalation] đúng thứ tự design 4.5 (đăng ký daily giao cho T35 theo review-raw-T34). Hàm T33/T34 không đổi.

## Bằng chứng dev
RED: 5 test mới (thiếu `reprobe_exhausted_keys`, hooks sai) -> GREEN `Ran 33 tests OK`; mutation gửi tin lần hai -> 2 test đỏ (`2 != 1`, `Called 1 times`); pre-commit pass; đếm HD Team/HD Ticket/User/ERP AI Log/Error Log/Email Queue sau = 4/3/8/0/198/9 (không chụp trước lượt đầu).

## Deferred (minor)
- `self.alarm` được vá nhưng không assert; dòng `assertEqual(status active)` luôn đúng; test "đúng một tin" lặp lại đường của test 1.
- Dev chưa chạy mutation cho bộ lọc trạng thái (thuộc gateway T18) và nhánh lỗi; reviewer kết luận từng guard thuộc T35 đều có thể đỏ qua đọc test.
- Đếm Email Queue trên chuỗi thật để `/team:verify` (test đếm lời gọi `send_notice`).
- Cần kiểm lúc chạy: scheduler trên miyano nhận mục hourly sau `bench migrate`.
