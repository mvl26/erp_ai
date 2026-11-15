Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 06 — CHG-002 T6

- Diff: `git diff 990d7b3..7967ec7` (nhánh `team/CHG-002-task-6`, 2 commit `e01b8b4` + `7967ec7`, 6 file, +211/−47)
- Gói: T6 + T7 cùng nhánh, một reviewer chấm cả gói (quyết định decide 10:35); verdict của T7 ở `review-07.md`
- Vòng: 1 (max_rework = 3)
- Verdict: **approve** → merge `98b0e5c` (cùng T7), tick

## Vòng 1 — approve

Phát hiện blocker/major: không.

minor | — | — | 4 điểm nhỏ (xem deferred) | tùy dev

Lớp 1 (khớp đặc tả): đủ tiêu chí, không làm thừa.
- `remove_file` thay `remove_created` ở 2 lời gọi trong `apply_job.py`, 5 chỗ `patch.object` trong `test_apply_job.py` và `test_process_runner.py:517`; không còn lời gọi `remove_created` nào.
- Thứ tự kiểm của `remove_file`: `_refuse_unless_canonical` → `islink` hoặc `not isfile` (`ValueError`) → `os.remove`, đúng A-3.1 và C-2. `write_atomic` gọi `_refuse_unless_canonical` trước `mkstemp`.
- Đã xóa `_refuse_git_dir`, `GIT_DIR_NAME`, `PROPOSAL_FILE_MAX_BYTES` cùng assertion ghim và import.
- `test_architecture.py`: hằng 4 tên, cờ `True`, ca `rename_file` bỏ lớp `patch`, writer tổng hợp thêm `write_atomic` / `remove_file`.
- Phép kiểm `islink` thêm trong `write_atomic` ngoài chữ của hợp đồng nhưng đúng tiêu đề task ("chặn symlink") và có test (symlink tự trỏ chỉ `islink` bắt): reviewer nhận.

Đột biến trong đầu của reviewer: bỏ `_refuse_unless_canonical` ở `remove_file`, bỏ `not isfile`, bỏ `islink`, bỏ phép kiểm chuẩn trong `write_atomic` → mỗi cái có test đỏ. Hai assertion cũ đổi (`FileNotFoundError` → `ValueError`; fixture sang `TempAppsRoot`) do hợp đồng mới, có dòng `test-shape:`; không vi phạm STD-TEST-5.

Bằng chứng của dev: lần gọi 1 (`e01b8b4`) RED `test_file_writer` `Ran 37 tests` / `FAILED (failures=11, errors=19)`, `test_architecture` `Ran 184 tests` / `FAILED (failures=1)`; GREEN `test_file_writer` `Ran 37 tests in 0.101s` / `OK`, `test_apply_job` `Ran 117 tests in 135.426s` / `OK`, `test_apply_block` `Ran 1 test in 1.280s` / `OK`, `test_change_decision` `Ran 10 tests in 9.110s` / `OK`, `test_architecture` `Ran 184 tests in 14.627s` / `OK`. Lần gọi 2 (`7967ec7`) RED `AttributeError: module 'erp_ai.agent.changes.file_writer' has no attribute 'remove_created'` / `Ran 18 tests in 0.085s` / `FAILED (errors=1)`; GREEN `test_process_runner` `Ran 18 tests in 0.120s` / `OK`.

Review checklist (10): 10/10 đạt.

## Không kiểm được từ diff (tech-lead đã xử lý)

- Reviewer không chạy test. Module sau merge trên `team/CHG-002` @ `98b0e5c` (một lần giữ khóa từ 11:42, `cmd.migrate` thoát 0): `test_file_writer` `Ran 37 tests in 0.147s` / `OK`, `test_process_runner` `Ran 21 tests in 0.356s` / `OK`, `test_architecture` `Ran 185 tests in 25.019s` / `OK`, `test_apply_block` `Ran 1 test in 2.453s` / `OK`, `test_change_decision` `Ran 10 tests in 20.704s` / `OK`.
- Cả app của đợt merge: dòng progress của T6 trong `tasks.md`.

## deferred

1. STD-GIT-2: commit `e01b8b4` đứng riêng thì `test_process_runner` đỏ (`AttributeError`), tới `7967ec7` mới xanh (do bảng touchpoint của kế hoạch sót một nơi gọi; không viết lại lịch sử).
2. STD-STYLE-5: chuỗi `file_writer.remove_created(full)` còn trong fixture ở `erp_ai/tests/test_architecture.py:7539`.
3. STD-TEST-8: ca tự kiểm của luật C-2 chỉ có "make_parents bỏ kiểm lại", chưa có ca cho `write_atomic` / `remove_file` (luật thật trên sản phẩm vẫn bắt, theo RED của dev).
4. Thứ tự `canonical → islink` trong `remove_file` không có test ghim (cả hai đều ném `ValueError`).
