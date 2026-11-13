Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 06 — FEAT-004 T6

- Diff: `git diff 154d752..2ab30f9` (1 commit trên `team/FEAT-004`, giống từng byte `ad893d7` của nhánh `team/FEAT-004-task-6`; 2 file, +67/-1)
- Vòng: 1 (max_rework=3)
- Verdict: approve

## Vòng 1 — approve
Lớp 1: lời gọi trong `validate` khớp Returns và `design-addendum-3.md` QĐ-B3: `policy.validate_change_apps(self, source.get_source_root())`, đặt sau `check_routing_rules`; có đủ hai import; không hàm nào khác đổi; diff nằm trong 2 file touchpoint.

Không có blocker, major hay minor.

Test sẽ đỏ nếu hành vi mất: bỏ lời gọi → 6 subTest đỏ (khớp RED `failures=6`); truyền gốc thật thay gốc đã patch → subTest `erpnext` đỏ; có dựng thư mục `../x` nên kiểm thư mục không che được luật tên; `nosuch\nerp_ai` ghim thứ tự (tên và `erp_ai` trước thư mục); chuỗi mong đợi viết tay. Đủ ca của Expect: `erp_ai`, `../x`, thư mục không có, None/""/khoảng trắng, `frappe`/`hrms` lưu được.

## Review checklist (10)
Đã phủ 10/10.

## Bằng chứng của dev
- RED: `Ran 27 tests` / `FAILED (failures=6)`, `AssertionError: ValidationError not raised`
- GREEN: `Ran 27 tests in 1.140s` / `OK`; test_architecture `Ran 110 tests … OK`
- `cmd.test` trên `6cf568e`: `Ran 1241 tests in 304.203s` / `OK`

## Không kiểm được từ diff (tech-lead xử lý)
- Mỗi lần lưu `ERP AI Setting` nay kiểm `code_change_apps` đang lưu của site với `apps/` thật; test cũ gọi `doc.save()` không đặt lại trường đó. Tech-lead đã đọc: giá trị đang lưu trên `miyano` là `frappe`, `erpnext`, `helpdesk`, `hrms` (cả 4 thư mục có thật); `cmd.test` chạy với trường này tạm để rỗng và xanh (dòng trên). Còn lại là rủi ro cô lập test đã biết (test đọc cài đặt đang lưu), ghi deferred.
- Mã nhận từ cây làm việc nên thứ tự đỏ trước chỉ có ở dòng dev dán, không có ở thứ tự commit.

## deferred
- Test đọc cài đặt đang lưu của site (`auto_assign_enabled`, `code_change_apps`): lỗi gốc về cô lập test, người đã định mở bug riêng (journal 2026-11-13).
