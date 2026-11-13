Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 37 — FEAT-004 T37

- Diff: `git diff 7f4f5c9..team/FEAT-004-task-37` (2 commit `cc5e093`, `2a8153e`; 4 file)
- Vòng: 2 (max_rework=3)
- Verdict: approve (vòng 1: request-changes)

## Vòng 1 — request-changes (`git diff 7f4f5c9..cc5e093`)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-8 | erp_ai/agent/tools/source.py:387 (test: test_source.py:1249-1272) | `timed_out = returncode in KILLED_EXIT_CODES and elapsed >= limit_s`: chỉ vế sau được kiểm; không có ca thoát bình thường sau hạn giờ, nên bỏ vế mã thoát thì mọi test vẫn xanh | thêm subTest mã thoát 0, 1, 128 với `monotonic` = `[100.0, 107.0]`, `limit_s=7`, mong `timed_out=False` |

minor | — | — | 3 điểm nhỏ: hằng `KILLED_EXIT_CODES`, `GIT_DEFAULT_PATH` ngoài danh sách design; kiểm thêm của `check_subprocess_call_shape` cho lời gọi bọc `timeout` và chốt `len(wrapped) == 1` chồng lên phần T11/T44; `EXPECTED_HOOKS_DIR` lặp công thức của mã | tùy dev

## Vòng 2 — approve (re-review theo phạm vi, `git diff cc5e093..team/FEAT-004-task-37`)
- Phát hiện 1: ADDRESSED (`test_run_git_read_normal_exit_after_limit_is_not_timed_out`, `test_source.py:1273-1282`)
- Mã mới: `run_git_read` từ chối đối số bắt đầu bằng `--output` và dạng viết tắt (`source.py:355-358`), theo ADR-022 QĐ 2 "không tham số nào làm các lệnh này ghi"; mỗi nhánh có test
- Phát hiện mới: không có blocker/major

minor | — | — | 3 điểm nhỏ: `source.py:357` `startswith("--output")` chặn cả `--output-indicator-*` (không ghi file); `test_source.py:1298` so regex "argument" trùng cả thông báo kiểm NUL; docstring `run_git_read` và design 3.2 chưa ghi lỗi từ chối đối số (STD-DOC-7) | tùy dev

## Review checklist (10)
1–10 đạt sau vòng 2. `check_subprocess_only_in_source_tool` không đổi; `check_subprocess_call_shape` chỉ thêm kiểm cho lời gọi bọc `timeout` (`start_new_session=True`, `cwd=`, `env=` không dùng `os.environ`).

## Bằng chứng của dev
- Vòng 1 RED: `test_source` `FAILED (errors=86)` (`AttributeError: ... has no attribute 'run_git_read'`), `test_architecture` `FAILED (failures=14)`; GREEN: `test_architecture` `Ran 98 tests in 1.285s` / `OK`, `test_source` `Ran 72 tests in 1.484s` / `OK`
- Vòng 2 RED: 3 failures với mã bị sửa thành `elapsed >= limit_s`; `AssertionError: ValueError not raised` (9 failures) trước khi có mã từ chối `--output`; GREEN: `test_source` 75 OK, `test_architecture` 98 OK; lint sạch

## Không kiểm được từ diff (tech-lead xử lý)
- Đóng gói `git_no_hooks/README.md` khi build wheel (cài editable của bench giữ thư mục) → deferred cho devops.
- Mã thoát thật khi `timeout -s KILL` diệt nhóm tiến trình chỉ được kiểm bằng mock → T46 (`test_index_lock_fails_fast`) chạy thật trong `GitSandbox`.
- git có nhận dạng viết tắt `--ou` không: từ chối thừa là vô hại.

## deferred
- `diff-tree --ext-diff/--textconv`, `cat-file --filters/--textconv` có thể chạy driver khai trong `.git/config` của repo: kiểm ở T38/T39 khi thêm nơi gọi, và ở luật T44 (ADR-022 QĐ 4).
- Thêm câu từ chối đối số vào design 3.2 (writer).
