Feature: FEAT-005
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 07 — FEAT-005 T7

Tech-lead chép từ tin trả về của reviewer (reviewer không ghi file).

- Diff: `git diff 568daa5..23f3ee1` (nhánh `team/FEAT-005-task-7`, 2 commit: `b2d53ba`, `23f3ee1`; merge `5223674`)
- Vòng: 2
- Verdict: approve (vòng 2)

## Vòng 1 — request-changes (`568daa5..b2d53ba`)

Lớp 1 (khớp spec): trường Datetime, `read_only`, ở `section_alerts` ngay sau `alert_recipients`, mô tả tiếng Việt < 400 ký tự; `restore_self_managed_fields` khôi phục từ `get_single_value(..., cache=False)`; `field_count` 27 → 28, thêm vào `read_only_fields` và `phrases`, `section_count` không đổi. Bốn file đều là touchpoint.

Trên Frappe 15 (`frappe/database/database.py:36,868`, `frappe/model/document.py:699`): `get_single_value` ép trường Datetime rỗng thành `datetime(1,1,1)`; chữ `"0001-01-01 00:00:00"` đọc lại thành `None`; `update_single` ghi nguyên giá trị.

- major | STD-TEST-2 | erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py:93 | Mốc rỗng: hàm khôi phục đặt trường thành `datetime(1,1,1)`, `save()` ghi chữ `0001-01-01 00:00:00` vào DB; người lưu form làm đổi DB (rỗng → năm 1), trái ADR-024 QĐ 3.2 và Expect "DB không đổi" | Coi giá trị năm 1 là rỗng trước khi đặt trường; vẫn đọc bằng `get_single_value(cache=False)`
- major | STD-TEST-5 | erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py:174 | subTest `in_db=None` chỉ xanh vì DB đã mang chữ năm 1; phép kiểm trong bộ nhớ bị bỏ đúng ở ca này: test ghim lỗi thay vì luật | Với `in_db is None` kiểm cột `value` thô của `tabSingles` (None) và trường trong bộ nhớ
- minor | — | — | 2 điểm nhỏ: mô tả trường nói "giá trị gõ vào bị bỏ khi lưu" trong khi trường chỉ đọc; `cache=False` chưa có test | tùy dev

Bằng chứng của dev: RED 1 (trước migrate) `unexpectedly None : field privilege_alert_checked_until is missing`; RED 2 (sau migrate, trước sửa .py) `datetime(2031,1,1,0,0) != datetime(2030,5,1,10,0)`; GREEN test_erp_ai_setting `Ran 28 tests` / `OK`, test_doctype_descriptions `Ran 11 tests` / `OK`.

## Vòng 2 — approve (`b2d53ba..23f3ee1`, re-review theo phạm vi)

- major 1: ADDRESSED (`erp_ai_setting.py:97-98`, hằng `EMPTY_DATETIME` dòng 59: năm 1 → `None`, `save()` ghi NULL)
- major 2: ADDRESSED (`test_erp_ai_setting.py:161-184`: giá trị thô `tabSingles` là `None` trước và sau khi lưu, trường trong bộ nhớ `None`)
- Phát hiện mới: không có.
- minor | — | — | 2 điểm nhỏ giữ nguyên từ vòng 1 (chữ mô tả; `cache=False` chưa có test) | tùy dev

Bằng chứng của dev: RED trên mã `b2d53ba`: `AssertionError: '0001-01-01 00:00:00' is not None`, `Ran 28 tests` / `FAILED (failures=1)`; GREEN `Ran 28 tests ... OK`, `Ran 11 tests ... OK`.

## Không kiểm được từ diff (tech-lead xử lý)

- Lint dòng dài ở `erp_ai_setting.py:97`: dev báo `pre-commit run --files` Passed; `cmd.lint` cả repo chạy ở T16.
- Site đã chạy mã `b2d53ba` có thể còn chữ năm 1 trong `tabSingles`: test rollback nên `miyano` không bị; T16 đọc cột `value` thô để chắc.
- `modified` của JSON = 2026-11-14 18:40: nếu worktree khác (FEAT-007 cũng sửa JSON này) migrate với `modified` muộn hơn thì lần sync sau có thể bị bỏ qua và trường biến mất; khi gộp nhánh phải lấy `modified` mới nhất rồi migrate lại. Báo team-leader.
- Sau merge `5223674`: `cmd.migrate` từ worktree feat-005 (không "Orphaned"/"Deleting"/"ALTER TABLE"/lỗi), test_erp_ai_setting `Ran 28 tests in 1.019s` / `OK`, test_doctype_descriptions `Ran 11 tests in 0.346s` / `OK`.
- Ghi chú thiết kế (không chặn T7): design-amd2 §4.2 bước 2 và §6 giả định mốc rỗng đọc ra `None`; thật là `datetime(1,1,1)` sau migrate mới. Đã ghi cho T8, T11, T16 ở `tasks.md`; cần designer thêm một dòng.

## deferred

- 2 minor trên (tùy dev), không mở vòng mới.
