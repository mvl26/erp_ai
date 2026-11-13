Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 03 — FEAT-004 T3

- Diff: `git diff f0054f5..team/FEAT-004-task-3` (1 commit `1637502`, 2 file, +84/-2)
- Vòng: 1
- Verdict: approve

## Phát hiện (chỉ blocker/major)
Không có.

minor | — | — | 1 điểm nhỏ: `test_doctype_descriptions.py:411` `assertLess(routing_rules < section_code_change)` lặp điều lát cắt neo tại `prompt_digest` đã chứng minh | tùy dev

## Review checklist (10)
1–4 đạt; 5 không áp dụng (JSON và test); 6–10 đạt. Mô tả hai trường trùng design 2.4 từng chữ (~210 ký tự, ≤ 400); số nền thật 24 trường, 6 section → 26, 7.

## Bằng chứng của dev
- RED: `Ran 11 tests ... FAILED (failures=4)`: `AssertionError: 24 != 26`, `AssertionError: 6 != 7`, lệch tập `phrases`, `Lists differ` (thứ tự trường)
- migrate: `Queued rebuilding of search index for miyano`
- GREEN: `test_doctype_descriptions` `Ran 11 tests in 0.396s` / `OK`; `test_erp_ai_setting` `Ran 25 tests in 2.948s` / `OK`; lint sạch

## Không kiểm được từ diff (tech-lead xử lý)
- Nhãn hai trường ("Cho phép sửa code và lệnh bench", "App được phép sửa") do dev đặt vì design 2.4 không ghi nhãn: tech-lead chấp nhận, ghi cho writer đưa vào As-Built.
- `POLICY_FIELDS` thêm hai tên: việc của T5.
- `test_descriptions_contain_no_stored_setting_values` đọc `ERP AI Setting` thật: nếu site lưu đúng một tên app ≥ 4 ký tự trong `code_change_apps` thì test đó đỏ → deferred (STD-TEST-6, ngoài phạm vi T3).

## deferred
- Cô lập Single `ERP AI Setting` trong `test_descriptions_contain_no_stored_setting_values`.
