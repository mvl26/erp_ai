Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 04 — CHG-002 T4

- Diff: `git diff f0b737c..56c8121` (nhánh `team/CHG-002-task-4`, 1 commit, 2 file, +225/−28; merge vào `team/CHG-002` ở `c6bb51e`)
- Vòng: 1 (max_rework = 3)
- Verdict: approve (0 blocker, 0 major)

## Vòng 1 — approve
Đối chiếu A-1.4 (thắng design.md): `resolve_safe_path` dùng `text_refusal(...) is None` (`source.py:140`); `read_source` mở `rb`, đọc `TEXT_MAX_BYTES + 1`, từ chối qua `_refuse(reason)` (`:186-191`); `search_source` đọc qua `_read_text`, bỏ file bị từ chối, không còn `getsize`; `_scan_text(text, rel, needle, hits)` thay `_scan_file`; `extension` là `{"type":"string","pattern":…}` và máy chủ kiểm bằng `fullmatch`; `DUOI_CHO_PHEP`, `SEARCH_FILE_MAX_BYTES` còn định nghĩa, `source.py` không dùng. 7 test của Expect có đủ, thêm 2 test biên. Reviewer thử bỏ từng phép kiểm trong đầu: mỗi phép có test bắt.

Ba dòng `test-shape:` (L-1 điểm 2, 3; STD-TEST-5): cả ba khớp, giữ kiểu so, không xóa assertion.
1. `test_secret_names_and_extensions_refused`: `tool.exe`, `noext` → `.github/tool.yml`, `.gitignore` (§3.2 bước 2), giữ `assertIsNone`.
2. `test_search_is_fixed_string_case_insensitive_and_filtered`: `huge.py` 1 MiB + 1 → `source.TEXT_MAX_BYTES + 1`; danh sách kết quả `[a.py, b.js, bad.py]` → `[a.py, b.js, skip.png]`, vẫn `assertEqual` cả danh sách. `bad.py` rơi ra vì kiểm UTF-8 chặt của AC-44 / §3.2, là đổi hành vi theo spec chứ không phải "hình dạng"; STD-TEST-5 cho phép, chỉ nhãn là lỏng.
3. `test_search_refuses_bad_input`: `.exe` → `exe`, giữ `assertFalse`.

minor | — | — | 2 điểm nhỏ (xem deferred) | tùy dev

## Review checklist (10)
1. Đạt. 2. Đạt (2 file touchpoint, không file mới). 3. Đạt (RED 15 lỗi đúng lý do; biên 2 MiB, 2 MiB + 1, 3 MiB, file rỗng, CRLF, NUL trước UTF-8; không skip). 4. Đạt. 5. Đạt (`OSError` bắt có chủ ý; `extension` kiểm kiểu và mẫu). 6. Đạt (phạm vi đọc rộng hơn đã nhận ở ADR-040:219). 7. Đạt (schema và câu từ chối đổi đúng thiết kế). 8. Đạt. 9. Đạt. 10. Đạt (`feat(source): … (CHG-002)`, không dòng AI).

## Không kiểm được từ diff, tech-lead đã xử lý
- Cả app trên nhánh task chưa chạy: đợt merge 3 (`a83923b`, 06:15–06:24) `Ran 1602 tests in 500.711s` / `FAILED (failures=6)`, đúng 6 test của dòng `baseline:`; `test_source` `Ran 125 tests` / `OK`.
- Lint: dev đã chạy `pre-commit run --files` trên hai file, thoát 0 (ruff-format sửa một lần, test chạy lại sau đó). `cmd.lint` cả cây để ở checkpoint T51.
- Tốc độ `search_source` trên cây `apps/` thật (nay mở mọi file không bị từ chối theo tên, tới 2 MiB mỗi file, ngân sách 30 s): không phải tiêu chí của T4; ghi ở deferred để QA đo một lần ở `/team:verify`.
- Rủi ro đã nhận (không phải phát hiện): file chấm và file không đuôi chứa thông tin đăng nhập mà `TEN_CAM` không khớp (`.npmrc`, `.netrc`, `.pypirc`) nay đọc được; ADR-040:219 đã ghi hệ quả này. Báo team-leader.

## deferred
1. STD-NAME-6 `test_source.py:64`: tên `test_secret_names_and_extensions_refused` đã cũ (không còn đuôi nào bị từ chối); L-1 cấm đổi tên ở task này, đổi ở T49 hoặc task sau.
2. STD-TEST-8 `source.py:187`, `:228`: chưa test nào ghim lần đọc có trần `read(TEXT_MAX_BYTES + 1)`; `read()` trần vẫn xanh.
3. Đo một lần `search_source({"pattern": "frappe.whitelist"})` trên site thật (xem trên).
4. Hành vi thấy mà không đụng (dev): `change_guard.check_write_path` trả `PATH_INVALID` cho thành phần `.git*` vì `resolve_safe_path` từ chối trước → thuộc T9.
