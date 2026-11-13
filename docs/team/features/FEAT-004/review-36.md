Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 36 — FEAT-004 T36

- Diff: `git diff 3aa363f..team/FEAT-004-task-36` (1 commit `2820e28`, 2 file, +252)
- Vòng: 1
- Verdict: approve

## Phát hiện (chỉ blocker/major)
Không có.

minor | — | — | 3 điểm nhỏ: (a) `test_source.py:536-552` `host.doCleanups()` là dọn dẹp duy nhất của `host`; (b) `test_utils.py:404-405` `_write` không giữ `rel` trong repo; (c) `test_utils.py:388` `git()` cho `cwd == root` nên git dò lên trên thư mục tạm | tùy dev (đã giao cho T51 làm cùng)

## Review checklist (10)
1–10 đạt. Không có hàm nào của T51 lọt vào.

## Bằng chứng của dev
- RED: `FAIL: test_git_sandbox_redirects_apps_root ... AssertionError: '/home/miyano/frappe-bench/apps' != ''`, tổng `FAILED (failures=15, errors=1)`
- GREEN: `test_source` `Ran 36 tests ... OK`; `test_change_guard` `Ran 10 tests ... OK`; lint sạch

## Không kiểm được từ diff (tech-lead xử lý)
- `cmd.test` sau merge: `Ran 924 tests in 211.667s` / `OK` trên `66ddf58`.
- git của runner CI cần ≥ 2.31 (`--initial-branch`, `--path-format=absolute`): máy này 2.43 → deferred cho devops.
- `TMPDIR` nằm trong một repo git: T51 đặt `GIT_CEILING_DIRECTORIES`.

## deferred
- Kiểm phiên bản git của runner CI.
