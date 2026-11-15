Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 65 — FEAT-007 T65

- Diff: `git diff ce696e161d9d9a208ae2e4d46d6c4598b819d61c..7332572` (nhánh `team/FEAT-007-task-65`; 2 commit `b07ace2` test, `7332572` mã; 2 file: `site_api.py` +3/−2, `test_site_api.py` +90)
- Vòng: 1 (trần `max_rework` = 3). Hai lần gọi dev: call 1 trả `DESIGN_CONFLICT` (round 73, không commit), call 2 sau phán quyết `design-w1-fixes-1.md` Điểm 2 (chọn (a)).
- Verdict: approve; merge `f6f14b1` trên `team/FEAT-007`
- File này do tech-lead viết từ báo cáo của reviewer (reviewer chỉ đọc, không ghi file).

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED @ `b07ace2` (chỉ test), `MIGRATE_EXIT=0`: `Ran 77 tests in 23.045s FAILED (failures=4)`; bốn subTest khoảng trắng ĐẦU: `roles` (tạo, sửa) `-  'reason': 'hệ thống từ chối: Could not find Row #1: Role:   System Manager'}` / `+  'reason': 'vai trò không được gán qua công cụ: System Manager'}`; `role_profile_name` (tạo, sửa) `-  'reason': 'hệ thống từ chối: Could not find Role Profile:   SITEAPI Ho so cam'}` / `+  'reason': 'vai trò không được gán qua công cụ: System Manager'}`. Xanh ngay lần đầu: có dấu, hoa thường, khoảng trắng CUỐI, `role_profiles`, hai test thêm. GREEN @ `7332572`, `MIGRATE_EXIT=0`: test_site_api `Ran 77 tests in 24.359s OK`, test_architecture `Ran 181 tests in 15.635s OK`.
- Sáu điểm tech-lead yêu cầu phán:
  1. Diff mã chỉ trong `_wanted_roles`, đúng điểm 2 của phán quyết: đạt. `site_api.py:158` cắt mỗi `row.get("role")` là `str`; `:162` cắt mỗi tên Role Profile là `str` trước `_profile_roles` (cả `values.get("role_profile_name")` lẫn `row.get("role_profile")`, danh sách dựng ở `:160`); nhánh hình dạng sai (`:155-156`) và lối ra sớm `ctx.unrestricted` (`:173`) không đổi; `_stored_name`, `_named_in`, `_profile_roles` không đổi; không import mới.
  2. Không gì ghi xuống DB đổi: đạt. `_wanted_roles` dựng danh sách mới, không sửa `values`; `create_record` (`:313`) và `update_record` (`:336`) ghi `values` gốc. `test_whitespace_around_an_allowed_role_still_rejected_by_frappe` (`test_site_api.py:832-845`) ghim điều này.
  3. Khoảng trắng cuối xanh trước khi sửa: lệch đo được, chấp nhận; không cần designer; STD-TEST-1 đạt. Trên `ce696e1` tên có khoảng trắng cuối đã bị chính phép kiểm của ta từ chối qua tra DB (`_stored_name` → `frappe.db.get_value`, `_profile_roles` → `frappe.db.exists`; collation `_ci` là PAD SPACE nên khoảng trắng cuối không tính khi so tên); khoảng trắng đầu thì có tính, nên đúng bốn subTest khoảng trắng đầu đỏ. Dòng Expect tự dẫn `failures=4` của round 73, cũng là bốn ca đó. Sau khi sửa, các ca khoảng trắng cuối bị `.strip()` từ chối, không còn dựa vào collation. Mức chắc chắn: reviewer suy lời giải thích PAD SPACE từ đầu ra RED và mã, không truy vấn DB.
  4. Độ phủ test và hai test thêm: đạt, trong phạm vi. `test_variant_spellings_refused` (`:810-830`): 4 cách viết × {`roles`, `role_profile_name`} × {tạo, sửa} + `role_profiles`; mỗi subTest khẳng định đúng dict kết quả và bản ghi không đổi. Hai test thêm là test ghim cho ràng buộc có trong dòng Returns (điểm 3 của phán quyết; "`ctx.unrestricted` giữ hành vi"), không thêm tính năng.
  5. STD-TEST-6, STD-SEC-4: đạt. `setUp` (`:774-787`) chặn commit, rollback ở cleanup; test tự tạo user và Role Profile; `_values_refusal` chạy trước `_write` ở cả `create_record` (`:309`) và `update_record` (`:323`).
  6. Commit, nhánh, skip: đạt. Test trước mã; không dòng ghi công AI; không skip/xfail.
- Checklist (10): 10/10 đạt.

### Findings

Không có blocker, không có major.

- minor | — | — | 2 điểm nhỏ: (1) `site_api.py:157`: chú thích `(" System Manager" is the stored name)` đọc như thể cách viết có khoảng trắng là tên lưu; (2) nhánh không phải `str` của phép cắt `row.get("role")` (`site_api.py:158`) không có test | dev's call

### Không kiểm được từ diff — tech-lead giải

- Phép cắt `row.get("role_profile")` không tới được trên bản Frappe này (phép kiểm trường từ chối `role_profiles` trước): đúng điểm 5 của phán quyết, đã có subTest ghim lỗi `DocType không có trường: role_profiles`. Nhận.
- Đường DocType Role Profile không chạy riêng: điểm 4 của phán quyết nói không cần test riêng. Nhận.
- Reviewer không chạy test và gói không có đầu ra `cmd.lint`. Tech-lead chạy sau merge trên `team/FEAT-007` @ `f6f14b1`, một lần giữ khóa, `MIGRATE_EXIT=0`: test_site_api `Ran 77 tests in 24.101s OK`, test_architecture `Ran 181 tests in 15.649s OK`; `pre-commit run --all-files`: mọi hook `Passed`.

## deferred

- Không có.
