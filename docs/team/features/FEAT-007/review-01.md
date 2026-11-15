Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 01 — FEAT-007 T1

- Diff: `git diff b410e73fe556cb3969550901f8e21c8365d117a2..team/FEAT-007-task-1` (đầu nhánh `9beb564`; merge vào `team/FEAT-007` là `19e92a7`)
- Vòng: 2 (trần `max_rework` = 3)
- Verdict: approve (vòng 2); vòng 1 là request-changes

## Vòng 1 — request-changes

- Range: `b410e73..5e5bde3` (1 commit, 5 file, +159/−6)
- Bằng chứng của dev: RED `AssertionError: unexpectedly None : ERP AI Setting has no site_environment field`; `ValidationError: Field site_environment does not exist on ERP AI Setting`; descriptions `27 != 28`, `7 != 8`. GREEN setting `Ran 29 tests ... OK`; test_utils `Ran 12 tests ... OK`; descriptions `Ran 11 tests ... OK`; test_architecture `Ran 112 tests ... OK`.

### Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-5 | erp_ai/tests/test_test_utils.py:262-263 (mã helper: erp_ai/test_utils.py:134-135) | Hai bước dọn cache của `keep_agent_settings` (`frappe.db.value_cache.pop` và `frappe.clear_document_cache`) không có test nào bắt: giữa `keep_agent_settings(inner)` và `doCleanups()` không có lần đọc nào đi qua cache, nên bỏ cả hai bước test vẫn xanh. Các lớp test sau sẽ gọi helper này mà không có rollback nên hai bước đó có ý nghĩa thật. | Trước `inner.doCleanups()` nạp cache bằng giá trị đã đổi (`frappe.db.get_single_value(...)`, `frappe.get_cached_doc(...)`); sau khi dọn, khẳng định qua chính hai hàm đọc có cache đó. |

minor | — | — | 1 điểm nhỏ: `TestFeat007Defaults.setUp` thêm `frappe.db.rollback` chồng lên bước trả lại của helper, vô hại | tùy dev

### Phán của reviewer về test sẵn có bị sửa
`test_descriptions_contain_no_stored_setting_values` nay bỏ qua trường `Select`: chấp nhận, không phải finding, không phải design-defect. Mô tả bắt buộc ở `design.md:164` có chữ "production" và giá trị lưu của `site_environment` cũng là `production`, nên phép kiểm cũ buộc phải đỏ theo spec mới (STD-TEST-5 cho phép sửa test khi spec đổi). Giá trị Select chỉ là một option viết sẵn trong JSON, không phải dữ liệu của site. Không mất độ phủ: Select khác của ERP AI Setting (`permission_level`, và `level_cap_*` sắp thêm) dài 2 ký tự, vốn đã nằm dưới `MIN_STORED_VALUE_CHARS = 4`. Lý do có trong comment cạnh chỗ sửa và trong commit.

### Review checklist (10)
1. đạt — AC-12, section `section_permissions`, `keep_agent_settings`, `TestFeat007Defaults` đúng tiêu chí, không thừa
2. đạt — 5 file đều trong touchpoints
3. trượt một phần (STD-TEST-5, finding trên); không skip/xfail/only
4. đạt — test sẵn có sửa vì spec đổi (phán ở trên)
5. đạt
6. đạt — không bí mật, SQL có tham số
7. đạt — chỉ thêm trường
8. đạt
9. đạt — không dependency mới
10. đạt — nhánh, commit đúng dạng, không dòng ghi công AI

## Vòng 2 — approve (scoped re-review)

- Range sửa: `git diff 5e5bde3..team/FEAT-007-task-1` (1 commit `9beb564`, 1 file `erp_ai/tests/test_test_utils.py`, +6/−1)
- Bằng chứng của dev: RED 1 (bỏ bước `value_cache` của helper) `AssertionError: 'ERPAI-TEST-changed' != 'ERPAI-TEST-keyword'`; RED 2 (bỏ bước `clear_document_cache`) `AssertionError: None != 'ERPAI-TEST-thinking'`; GREEN `erp_ai.tests.test_test_utils` 12 OK, `test_erp_ai_setting` 29 OK, `test_doctype_descriptions` `Ran 11 ... OK`.

| # | Finding vòng 1 | Kết quả |
|---|---|---|
| 1 | major STD-TEST-5 — hai bước dọn cache không được test | ADDRESSED (`test_test_utils.py:260-261` nạp hai cache trước `doCleanups()`, dòng 267-268 đọc lại qua cùng hàm có cache; bỏ bước nào test cũng đỏ) |

Lỗi mới do diff sửa gây ra: không có ở mức blocker/major.

minor | — | — | 1 điểm nhỏ: comment ở `test_test_utils.py:240` nói rollback "không" dọn cache tài liệu; ở Frappe v15 `clear_document_cache` có đăng ký `clear_in_redis` vào `db.after_rollback`, nên comment nói quá. Bước dọn mới vẫn nên giữ làm lớp dự phòng | tùy dev

### Review checklist (10), chỉ diff sửa
1–10: đạt (chi tiết: chỉ sửa đúng finding; file trong touchpoints; có RED cho từng bước; không nới khẳng định nào; commit `test(setting): ... (FEAT-007)` đúng STD-NAME-5).

## Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| `keep_agent_settings` chỉ chụp `tabSingles` và dòng bảng con, không chụp dòng `__Auth` của trường Password `api_key` | Không phải thiếu sót của T1: đúng phạm vi task viết ("chụp `tabSingles` của ERP AI Setting và dòng các bảng con") và `design.md:558`. Đưa vào `deferred`, báo team-leader: NFR-7 có cần phủ `__Auth` hay không là câu hỏi cho designer, không chặn T1. |
| GREEN trên site `miyano` và `cmd.test` toàn app chưa do dev chạy | Tech-lead chạy `cmd.migrate` rồi `cmd.test` trên `team/FEAT-007` @ `19e92a7` sau merge; kết quả ghi ở dòng progress của T1 trong `tasks.md`. |

## deferred

- (thiết kế, không chặn) NFR-7 và `__Auth`: test nào về sau đổi mật khẩu khóa hoặc xóa dòng credential mà không rollback có thể để lại dòng `__Auth` đổi/mồ côi; `keep_agent_settings` không trả lại phần này. Chủ: designer/team-leader quyết định.
- (minor, tùy dev) `rollback` thừa trong `TestFeat007Defaults.setUp`; comment nói quá ở `test_test_utils.py:240`.
