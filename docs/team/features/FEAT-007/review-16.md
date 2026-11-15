Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 16 — FEAT-007 T16

- Diff: `git diff 7572547..c69e572` (nhánh `team/FEAT-007-task-16`, 1 commit `c69e572`, 4 file +380/−8)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve

## Vòng 1 — approve

- Lệnh đã dùng (chỉ đọc): `git log --oneline 7572547..team/FEAT-007-task-16`, `git diff --stat …`, `git diff … -- <từng file>`, `git diff --check` (sạch), `git log -1 --format='%an%n%B' c69e572`, `git show team/FEAT-007-task-16:<path>` cho controller, file test và `.team/profile.json`; đọc mã Frappe của `validate_email_address`, `parse_addr`, `get_invalid_links`, `_validate_code_fields`.
- Bằng chứng của dev: RED sau migrate (exit 0): `AssertionError: False is not true : ERP AI Setting has no coo_report_recipients` (3 test `TestOperationPeople`), `AssertionError: unexpectedly None : ERP AI Setting has no review_sample_size field`, `'section_operations' not found in [...]`, `Ran 73 tests … FAILED (failures=5, errors=12)`; `test_doctype_descriptions`: `59 != 71`, `12 != 13`, `Lists differ`, `FAILED (failures=5)`. `test_response_targets_reuse_routing_rules` xanh ngay lần đầu (dòng Expect cho phép). GREEN một lần giữ khóa, `MIGRATE_EXIT=0`: `test_erp_ai_setting` `Ran 74 tests in 16.278s OK`; `test_doctype_descriptions` `Ran 12 tests in 0.657s OK`; `test_architecture` `Ran 112 tests in 6.145s OK`; `test_install` `Ran 37 tests in 71.905s OK`.
- Lớp 1 (khớp spec): mọi tiêu chí đạt, không thiếu, không thừa; sửa trong đúng 4 touchpoints.
  - `section_operations` có 12 trường của `design.md:108`, đúng thứ tự, kiểu, mặc định; `kpi_targets` mặc định đúng JSON của `design.md:189-197`; hai trường mốc read-only.
  - 5 dòng `INT_LIMITS` mới đúng khoảng; `max_tasks_per_run` mặc định 10, nhận 1..20 (AC-63).
  - AC-26: mốc phản hồi ghim vào `routing_rules`; test khẳng định không có trường nào tên chứa "response".
  - `check_kpi_targets` (T17) và bước khôi phục hai mốc (T18) được để lại đúng phạm vi.
  - Ba chữ lỗi của `check_operation_people` khớp `design.md:309` từng chữ; chạy ở bước 9, sau `check_manuals_dir`, có test ghim thứ tự.
  - Phép khẳng định thứ tự section trong `test_doctype_descriptions.py` mở từ 23 lên 36 mục theo bảng `design.md:108`, không nới (đúng dòng "Bổ sung" ở khối T13).

### Phát hiện (chỉ blocker/major)

Không có blocker, không có major.

minor | — | — | 3 điểm nhỏ: (1) `erp_ai_setting.py:280` kiểm email chặt hơn chữ của `design.md:309`: từ chối dòng có dấu phẩy hoặc dạng "Tên <a@x>"; `validate_email_address(throw=False)` trần sẽ nhận `"a@x.com, sai"` và `"a@x.com, b@x.com"`; bản chặt khớp bảng thiết kế ("mỗi dòng một email") và mô tả trường, chữ lỗi không đổi; (2) `erp_ai_setting.json:619`: mô tả `kpi_targets` nói "không lưu được" nhưng chưa gì chặn JSON hỏng cho tới T17 (`_validate_code_fields` của Frappe chỉ kiểm Python); chữ lấy từ `design.md:180`; (3) STD-DESIGN-4: `_filled_lines` mới (`erp_ai_setting.py:293`) trùng biểu thức còn viết thẳng ở `:319`, `:356`, kiểu trả về là `list` trần | tùy dev

### Độ mạnh của test

- Email: mỗi vế của điều kiện có một ca chỉ vế đó bắt (`"a@example.com, b@example.com"` chỉ bị phép dấu phẩy bắt; `"Giám đốc <coo@example.com>"` chỉ bị phép `!= typed` bắt); khoảng trắng, escape `<b>x</b>` có ca riêng; giá trị sai đặt ở dòng giữa nên đột biến chỉ kiểm dòng đầu/cuối sẽ đỏ.
- Người rà soát: tài khoản tắt, tài khoản không có, giá trị được escape; dòng trống được bỏ qua thật.
- Người theo dõi: test khẳng định `AGENT_USER` đang bật trước khi thử; người tắt thử riêng vế "đang bật"; `AGENT_USER.upper()` bị từ chối đúng (Frappe trả Link về đúng chữ đã lưu trước `validate`).
- Thứ tự `manuals_dir` → COO → người rà soát → người theo dõi được ghim; mỗi lần từ chối đều khẳng định giá trị đã lưu không đổi.

### Review checklist (10)

1. đạt 2. đạt (4 file, không file mới) 3. đạt (RED có cho mọi test mới trừ test AC-26 mà Expect cho phép; biên low−1, high+1, low, high; không skip) 4. đạt (phép khẳng định thứ tự được mở rộng theo dòng "Bổ sung", lý do trong commit; lớp test mới gọi `keep_agent_settings`, tự tạo user, rollback) 5. đạt 6. đạt (`get_value` có tham số; giá trị gõ được escape trong chữ lỗi) 7. đạt (chỉ thêm trường vào Single; migrate exit 0) 8. đạt 9. đạt 10. đạt (`feat(setting): … (FEAT-007)`, không trailer AI, thân commit ghi lý do STD-TEST-5)

## Không kiểm được từ diff — kết luận của tech-lead

- Reviewer không chạy test → tech-lead chạy sau merge trên `team/FEAT-007` @ `267a0a3` (một lần giữ khóa, `MIGRATE_EXIT=0`): `test_erp_ai_setting` `Ran 74 tests in 10.654s OK`, `test_doctype_descriptions` `Ran 12 tests in 0.608s OK`, `test_architecture` `Ran 112 tests in 5.754s OK`, `test_install` `Ran 37 tests in 39.813s OK`.
- Cách báo cáo 08:00 đọc `coo_report_recipients` chưa được thiết kế hay U5a nói rõ; nếu U5a cần dòng dạng "Tên <email>" thì phép kiểm chặt ở `erp_ai_setting.py:280` sẽ từ chối. Không phải lỗ của task này (khớp "mỗi dòng một email" của bảng thiết kế); chuyển team-leader xin designer ghi một dòng vào `design.md:309`, U5a (T51–T54) đọc theo cách chặt.
- Từ merge T16 tới merge T17, `kpi_targets` nhận mọi chữ dù mô tả nói không. T17 là task kế trong chuỗi U0 và phải merge trước mọi mốc chạy cả app hay nghiệm thu; không chặn tick T16.

## deferred

- 3 điểm nhỏ ở trên; điểm (3) (`_filled_lines` lặp) để dọn cùng lượt `/team:clean` của `erp_ai_setting.py`.
