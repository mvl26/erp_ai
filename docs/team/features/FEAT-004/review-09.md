Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 09 — FEAT-004 T9

- Diff: `git diff 2f41590..team/FEAT-004-task-9` (2 commit `039d14a`, `e4e9527`; 2 file)
- Vòng: 2 (max_rework=3)
- Verdict: approve (vòng 1: request-changes)

## Vòng 1 — request-changes (`git diff 2f41590..039d14a`)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-2 | erp_ai/agent/tools/test_change_guard.py:374,413,516 (danh sách cho phép ở change_guard.py:31,34) | "ngoài danh sách cho phép" chỉ được kiểm bằng 23 tên A-6 và biến thể của `migrate`; không test nào ghim chính danh sách cho phép (thêm `trim-database` vào `SITE_COMMANDS` thì mọi test vẫn xanh) | so `set(BENCH_COMMANDS)` với tập 6 tên viết tay; thêm lệnh không thuộc danh sách nào (`trim-database`, `doctor`, `show-config`) → `lệnh không có trong danh sách cho phép` ở cả `build` và `check` |

minor | — | — | 3 điểm nhỏ: (1) vế `not _is_site(site)` của bước 3 chưa được kiểm riêng; (2) app symlink tới `erp_ai` nhận `APP_NOT_ALLOWED` ở đây, `APP_FORBIDDEN` ở `check_write_path`; (3) `BENCH_COMMANDS` dựng từ lát cắt khó đọc | tùy dev

## Vòng 2 — approve (re-review theo phạm vi, `git diff 039d14a..team/FEAT-004-task-9`)
- Phát hiện 1: ADDRESSED (`test_bench_allow_list_is_exactly_the_six_design_commands`, `test_change_guard.py:425-438`)
- Minor (1), (3): đã sửa có test; minor (2): dev giữ nguyên
- Phát hiện mới: không có.

## Review checklist (10)
1–10 đạt sau vòng 2.

## Bằng chứng của dev
- Vòng 1 RED: `FAILED (failures=78)`, ví dụ `AssertionError: None != 'lệnh không có trong danh sách cho phép'`; GREEN: `Ran 27 tests ... OK`
- Vòng 2 RED (thêm tạm `trim-database`): `AssertionError: Items in the first set but not the second:`; GREEN: `Ran 28 tests ... OK`; lint sạch

## Không kiểm được từ diff (tech-lead xử lý)
- T18 gọi lại `check_bench_args` trên `command_args` đã lưu với `allowed_apps` và site hiện tại; test "sửa thành `console` sau duyệt" → T18, T21.
- enum `command` của tool (T27) có đúng 6 giá trị và có dựa vào thứ tự `BENCH_COMMANDS` không → reviewer T27.

## deferred
- Câu chữ `APP_NOT_ALLOWED` so với `APP_FORBIDDEN` cho app symlink tới `erp_ai` trong `build` (minor 2).
