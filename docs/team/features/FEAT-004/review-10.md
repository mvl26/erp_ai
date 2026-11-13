Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 10 — FEAT-004 T10

- Diff: `git diff 3aa363f..team/FEAT-004-task-10` (1 commit `e059ce9`, 2 file, +200)
- Vòng: 1
- Verdict: approve

## Phát hiện (chỉ blocker/major)
Không có.

minor | — | — | 5 điểm nhỏ: tên test nhánh lỗi khác tên trong test plan (`test_write_atomic_failure_removes_temp_and_keeps_old_file`, `..._on_new_file_leaves_nothing`); `test_file_writer.py:146` ghim giá trị 1048576 chứ không ghim nguồn `source.SEARCH_FILE_MAX_BYTES`; `file_writer.py:49` kiểu trả `-> str` trong khi `sha256_of` có thể trả `None`; `:45-47` lỗi của `os.remove(temp)` che lỗi gốc; `:19` kiểm `.git` bằng `abspath`, không `realpath` | tùy dev

## Review checklist (10)
1–10 đạt.

## Bằng chứng của dev
- RED: `FAILED (failures=12)`, ví dụ `AssertionError: '' is not None`, `AssertionError: OSError not raised`
- GREEN: `Ran 10 tests in 0.080s` / `OK`; lint sạch

## Không kiểm được từ diff (tech-lead xử lý)
- Symlink trỏ vào `.git` và thư mục cha thiếu: `check_write_path` đưa `realpath` và trả `NO_PARENT`; nhắc reviewer T18, T19 kiểm nơi gọi.
- Luật kiến trúc cho `file_writer` do T31/T32 thêm; `cmd.test` sau merge: `Ran 924 tests ... OK`.

## deferred
- qa trỏ AC-6 (nhánh lỗi) vào hai tên test thật ở trên.
