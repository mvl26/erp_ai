Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 42 — FEAT-004 T42

- Diff: `git diff 2ab30f9..7e90e5e` (1 commit trên `team/FEAT-004`, giống từng byte `8983584` của nhánh `team/FEAT-004-task-42`; 2 file, +225/-8)
- Vòng: 1 (max_rework=3)
- Verdict: approve

## Vòng 1 — approve
Lớp 1: `GuardResult` thêm `is_core_app`, `git`; `check_write_path` thêm `read_git=True`; câu từ chối của trạng thái git đi vào `reason`; cho qua thì `git=state` và `is_core_app` lấy từ `CORE_APPS`; `read_git=False` không chạy lệnh git, file không có `subprocess`. `PATH_GIT_PATTERN` đúng chữ phụ lục 2 QĐ-A2, kiểm sau `GIT_DIR`, trước `full is None`, dùng lại `source.GIT_GLOB_CHARS`; điều kiện trùng `process_runner._check_git_write_call`. Đủ 4 test của Expect và 3 test của phụ lục, có nối dòng vào bảng chữ từ chối. Test cũ chỉ đổi cách gọi (`read_git=False`), không đổi assertion. Mặc định mới `read_git=True`: `git grep` không thấy nơi gọi nào ngoài `change_guard.py`.

Không có blocker, major.

minor | — | — | 1 điểm nhỏ: chưa có ca `[` đứng một mình không có `]` (vd `custom_app/a[.py`); `GIT_GLOB_CHARS` thuộc `source.py`, ngoài diff | tùy dev

Test sẽ đỏ nếu hành vi mất: hai câu từ chối git khác nhau (bẩn, bị ignore) loại trừ lý do viết cứng; `a*.py` đã theo dõi và bẩn ghim kiểm mẫu trước khi đọc git, 0 lần `run_git_read`; `:x/.git/a.py` ghim `GIT_DIR` trước kiểm mẫu; so cả `GitState` viết tay; `custom_app` không là app lõi; `sub/-x.py` và `a:b.py` được cho qua.

## Review checklist (10)
Đã phủ 10/10.

## Bằng chứng của dev
- RED: `AssertionError: None != 'file đích có thay đổi chưa commit'`
- GREEN: `Ran 35 tests in 1.345s` / `OK`
- `cmd.test` trên `6cf568e`: `Ran 1241 tests in 304.203s` / `OK`

## Không kiểm được từ diff (tech-lead xử lý)
- GREEN của dev chỉ phủ `test_change_guard`: `cmd.test` cả app trên `6cf568e` xanh (dòng trên).
- Thứ tự "trước `full is None`" không quan sát được bằng test (`resolve_safe_path` chỉ trả `None` ở ca mà kiểm trước đã từ chối): không là phát hiện.

## deferred
- Cho designer (từ round 46): `is_core_app` được đặt cả khi `read_git=False`; design chưa nói.
