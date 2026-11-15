Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 48 — CHG-002 T48

- Diff: `git diff b46d730..e6a18af` (nhánh `team/CHG-002-task-47`, 1 commit, 1 file `erp_ai/tests/test_architecture.py`, +96/−5)
- Gói: T47 + T48 cùng nhánh, một reviewer chấm cả gói; verdict của T47 ở `review-47.md`
- Vòng: 1 (max_rework = 3)
- Verdict: **approve** → merge `ae8edc5` (cùng T47, sau khi T47 qua vòng 2), tick

## Vòng 1 — approve

Phát hiện blocker/major: không.

minor | — | — | 2 điểm nhỏ (xem deferred) | tùy dev

Lớp 1 (AC-47, AC-52, §8.2): đạt, đúng touchpoint.
- `FORBIDDEN_BENCH_COMMANDS` khớp ADR-040 QĐ 6 từng chữ (10 lệnh: execute, console, install-app, uninstall-app, reinstall, backup, restore, set-config, drop-site, new-site); `GIT_RUNNING_BENCH_SUBCOMMANDS` khớp ADR-022 QĐ 2 (update, switch-to-branch, get-app, remove-app, new-app, setup, init); cả hai so với cùng tập `BENCH_COMMANDS`.
- Ca "thiếu restart" bị bắt; mỗi lệnh cấm có ca ở dạng bảng và dạng `SITE_COMMANDS`, đồng thời khẳng định "thiếu restart" không nổ nhầm; ca gộp khẳng định cả hai thông điệp.
- `assertLessEqual(set(FS_WRITE_OS_FUNCTIONS), FS_WRITE_FUNCTIONS)` ghim bảy tên `os.*` trong test có sẵn; mỗi tên có ca bị bắt ở 4 file ngoài `file_writer` và ca sạch trong `file_writer`.
- `check_tools_never_bypass_permissions` không đổi.
- Dòng `test-shape:`: giá trị cũ và mới khớp diff, giữ kiểu so; `test_bench_allowlist_caught` và subtest `case="table"` có thật (`:8103`).

Bằng chứng của dev: RED (phần bench; phần `os.*` đã xanh sẵn theo `arch-preflight-1.md`, không đòi RED): `test_bench_table_with_forbidden_command_caught` ×20 subtest, `test_bench_table_without_restart_caught`, `test_bench_table_without_restart_and_with_forbidden_command_reports_both`, đều `AssertionError: 0 not greater than 0 : scanner missed the violation`, `Ran 195 tests in 16.253s` / `FAILED (failures=22)`; GREEN `Ran 195 tests in 16.007s` / `OK`. L-1: 1.

Review checklist (10): 10/10 đạt.

## Không kiểm được từ diff (tech-lead đã xử lý)

- Reviewer không chạy test. Module và cả app sau merge: dòng progress của T48 trong `tasks.md` (đợt merge 14, `ae8edc5`).

## deferred

1. Dòng `test-shape:` dùng `->` thay `→` và có hai dòng cho một test (nội dung đúng).
2. Mẫu `change_guard` trong `GIT_CLEAN` cũng được sửa (`:5537`, thêm `RESTART_COMMAND`); thân commit có nêu nhưng không có dòng `test-shape:` riêng.
