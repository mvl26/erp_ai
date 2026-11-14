Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 52 — FEAT-004 T52

- Diff: `git diff c8af79f..04e1dbc` (1 commit; 2 file, +32/-3; merge vào `team/FEAT-004` trong `e1182d0`)
- Vòng: 1 (max_rework=3)
- Verdict: approve

## Vòng 1 — approve
Lớp 1: khớp `design-addendum-3.md` QĐ-B6 và Returns. `erp_ai_change_proposal.py:105,114,121`: cả ba method là `(name=None)`, không chú thích kiểu; không đổi gì khác trong controller; thứ tự kiểm (role → name → chuyển trạng thái → xếp job) giữ nguyên; `_decider` đã đưa `name` không phải chuỗi về `DoesNotExistError`.

Không có blocker, major hay minor.

Test `test_erp_ai_change_proposal.py:730-757` (`test_methods_missing_name_is_not_found`): gọi qua `frappe.call` có kiểm `in_test` nên lớp kiểm kiểu của Frappe chạy; phủ 3 method × {thiếu, None, 123, list}, kiểm đúng loại lỗi và câu; ảnh chụp trường đề xuất, dòng log `change`, số dòng log và 0 job được xếp. Đỏ khi bỏ mặc định (RED của dev) và đỏ khi chú thích kiểu quay lại (123 sẽ ra lỗi kiểu 417).

## Review checklist (10)
Đã phủ 10/10.

## Bằng chứng của dev
- RED: `TypeError: approve() missing 1 required positional argument: 'name'`
- GREEN: `Ran 24 tests in 19.864s` / `OK`
- `cmd.test` trên `6cf568e` (chứa merge `e1182d0`): `Ran 1241 tests in 304.203s` / `OK`

## Không kiểm được từ diff (tech-lead xử lý)
- Bảng method và dòng 404 của `design.md` mục 3.3 đã sửa theo QĐ-B6 chưa: chưa, phụ lục 3 đang là căn cứ → ghi deferred cho designer.

## deferred
- Cho designer: gộp QĐ-B6 vào `design.md` mục 3.3.
