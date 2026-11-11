# Review 42 — FEAT-001 T33 (Job hằng ngày: tính lại chi phí tháng)

Verdict: approve (sau 1 vòng rework)
Vòng: 2 (vòng 1 request-changes; vòng 2 scoped re-review approve)
Diff: `git diff a947607..team/FEAT-001-task-33` (head e09ab7b; vòng 2: `git diff 4cf8b52..team/FEAT-001-task-33`)

## Vòng 1 (review-raw-T33.md)
- major STD-ERR-4: job scheduler không có hợp đồng lỗi (D-20): thiếu try/except, rollback, `log_error(title hằng, message tường minh)`.
- major STD-TEST-6: test tổng phụ thuộc dòng ERP AI Log thật của tháng hiện tại.
- minor: log_error patch thừa; timezone không ghim; `update_modified=False` chưa assert; thiếu ca nhãn NULL; nhãn cố định.

## Vòng 2
Cả hai major ADDRESSED (try/except + rollback + `TITLE_RUN_FAILED` + message `recompute_monthly_spend month=YYYY-MM error=<Class>`; test lỗi đỏ khi bỏ try/except; test dời sang tháng 2031, không `frappe.db.delete`, test now mặc định dùng delta so với baseline). Minor 1, 3, 4, 5 ADDRESSED; minor 2 bỏ theo phán quyết.

## Bằng chứng dev
Vòng 1: RED (stub no-op, 6 failure + 1 error) -> GREEN 7 OK; mutation từng guard đỏ. Vòng 2: Ran 10 tests OK; pre-commit pass; đếm 4/3/8/0/198 trước = sau.

## Deferred
- commit guard ném `AssertionError` bị `except Exception` trong job nuốt: thêm `self.log_error.assert_not_called()` ở đường vui nếu cần (minor).
- `test_default_now_is_current_time` đọc đồng hồ thật, qua nửa đêm cuối tháng có thể lệch.
- Nhãn khóa không duy nhất (design 2.2): hai dòng khóa cùng nhãn nhận cùng chi tiêu theo nhãn; ghi nhận cho designer.
- Thứ tự daily (4.5): recompute trước `check_privilege_escalation` — T34 phải giữ thứ tự khi thêm hook.
