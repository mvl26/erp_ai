Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 02 — FEAT-007 T2

- Diff: `git diff 58b667411121655d13f8d775710bcdcc44721311..cd2ba95` (đầu nhánh `team/FEAT-007-task-2` lúc review; merge vào `team/FEAT-007` là `80469e7`)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve

## Vòng 1 — approve

- Range: `58b6674..cd2ba95` (1 commit, 4 file, +142/−27), đúng 4 file của touchpoints.
- Bằng chứng của dev: RED `erp_ai.tests.test_install` `FAILED (failures=3)`, `test_migrate_keeps_old_switches_new_switches_off`: `'record_tools_enabled': '<missing>'` ở chỗ mong `'0'`; GREEN sau `migrate`: `test_install` `Ran 36 tests in 14.786s OK`; `test_erp_ai_setting` `Ran 29 tests in 0.981s OK`; `test_doctype_descriptions` `Ran 11 tests in 0.334s OK`; `test_architecture` `Ran 112 tests in 2.994s OK`.

### Phát hiện (chỉ blocker/major)

Không có finding nào ở mức blocker hay major.

minor | — | — | 3 điểm nhỏ: (1) `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py:591-593`: ba dòng Check mới đọc qua `frappe.db.get_single_value`, hàm này biến dòng `tabSingles` thiếu thành 0, nên bỏ `"default": "0"` ba dòng này vẫn xanh (phép đọc thô ở `test_install.py` thì bắt được); (2) `erp_ai/tests/test_doctype_descriptions.py:307`: comment đầu `FORBIDDEN_PHRASES` không còn đúng cho mục ERP AI Setting mới (comment ở `:309` có giải thích); (3) mô tả `permission_level` nay đúng 400 ký tự, task sau thêm chữ vào đó phải cắt chỗ khác | tùy dev

### Ghi nhận của reviewer

- Trường: `record_tools_enabled`, `act_now_enabled`, `one_click_approval_enabled` là Check, mặc định "0"; thứ tự 5 ô và `site_environment` theo `design.md:98` ở cả `field_order` và mảng `fields`; `section_code_change` chỉ còn `code_change_apps`.
- Mô tả: 4 ô khớp từng chữ `design.md:159-163`; `code_change_enabled` viết "được duyệt bởi ERP AI Instructor" thay cho "được ERP AI Instructor duyệt" (thiết kế cho "dev giữ ý", cụm bắt buộc "được duyệt" còn); `permission_level` có câu bắt buộc, câu "ô Cho phép sửa code" đã bỏ và được `FORBIDDEN_PHRASES` ghim.
- AC-1: cả ba test của `TestFeat007Migrate` đều bắt được thay đổi thật (đọc thô `tabSingles`, giá trị gieo khác mặc định, so cả tập Singles gồm `modified`).
- NFR-7: lớp test mới gọi `keep_agent_settings` và rollback. NFR-8: lý do sửa ghim `CODE_CHANGE_FIELDS` và `test_code_change_block_follows_feat006_fields` có trong commit và comment. D-7: không file `.py` ngoài test nào bị sửa.

### Review checklist (10)
1. đạt — AC-1, mô tả theo `design.md:159-164, 184`
2. đạt — đúng 4 file touchpoints
3. đạt — RED trước (thiếu trường, không phải lỗi import); không skip/xfail/only
4. đạt — test sẵn có sửa vì thiết kế đổi vị trí và nghĩa của ô (NFR-8)
5. không áp dụng
6. đạt
7. đạt — chỉ thêm trường, chuyển chỗ; không đổi tên trường
8. đạt (3 điểm nhỏ ở trên)
9. đạt — không dependency mới
10. đạt — `feat(setting): ... (FEAT-007)`, không dòng ghi công AI

## Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| Chữ trên form đi trước mã: `code_change_enabled` ghi "không còn mở công cụ bản ghi" trong khi chưa mã nào đọc 3 ô mới | Thứ tự đã định (U0 trước U1) và đã nhận ở `plan.md` mục Rủi ro (dòng A-D1). `team/FEAT-007` không vào `develop` trước T57, T58 (`plan.md` Thứ tự 5). Không phải thiếu sót của T2. |
| `cmd.test` cả bộ chưa chạy | Theo N-6 cả bộ chạy ở M1 (sau T5). |
| `cmd.migrate` trên site trước lần GREEN | Sau merge tech-lead chạy lại trên `team/FEAT-007` @ `80469e7`. Hai lần `migrate` đầu (17:10) hỏng: `LockTimeoutError: Failed to aquire lock: bench_migrate` (phiên khác đang migrate), nên hai lần chạy test khi đó đỏ vì site thiếu trường (`test_install` `FAILED (failures=3)`, `test_erp_ai_setting` `FAILED (failures=1, errors=4)`, kể cả `site_environment` của T1). Lần `migrate` thứ ba xong (exit 0); sau đó `test_install` `Ran 36 tests in 17.542s OK`, `test_erp_ai_setting` `Ran 29 tests in 1.632s OK`, `test_doctype_descriptions` `Ran 11 tests in 0.322s OK`, `test_architecture` `Ran 112 tests in 3.032s OK`. |
| `cmd.lint` | `ruff-format` đỏ ở đúng một file `erp_ai/test_change_decision.py` (nợ của nền, xem `review-59.md`); không file nào của T2. |

## deferred

- (minor, tùy dev) 3 điểm nhỏ ở trên; điểm (1) nên được task U0 kế tiếp sửa `test_every_new_field_default` lưu ý (đọc thô khi kiểm mặc định của Check).
- (thiết kế, không chặn) nhãn 3 ô mới do dev đặt ("Công cụ bản ghi chung", "Làm luôn, không hỏi lại", "Duyệt một lần bấm") vì thiết kế không cho nhãn; T6 dùng nhãn này trong thông báo.
