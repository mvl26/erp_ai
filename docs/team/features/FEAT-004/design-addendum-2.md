Feature: FEAT-004
Stage: design
Author-agent: designer
Date: 2026-11-13

# Design FEAT-004, phụ lục 2: pathspec, tên file kiểu mẫu git, hết ngân sách lệnh bench
Bổ sung `design.md`, không viết lại. Nguồn: review-11, review-38, review-43; mã `team/FEAT-004` (`78d9887`, T43 đã merge), `team/FEAT-004-task-38` (`18b5cff`, chưa merge). Tuân ADR-011 QĐ 4, ADR-013 QĐ 3/7, ADR-022 QĐ 2, 3 và Ràng buộc. Clean filter đã có phán quyết riêng (`arch-ruling-clean-filter.md`), không bàn ở đây.

## QĐ-A1. Pathspec chính xác của git đọc và git ghi
**Quyết định.** Ghi đúng các dạng mà mã đang dùng. Không đổi mã nào.
- Design 3.2 bước 5: `check-ignore -q -- ./<rel>`. `check-ignore` không nhận magic `:(...)` (thoát 128), và `./` giữ cho tên bắt đầu bằng `:` không bị đọc là magic.
- Design 3.2 bước 6: `status --porcelain=v1 -z --untracked-files=all -- :(literal)<rel>`. `<rel>` trần là pathspec glob: đích `f*.py` sẽ khớp file bẩn khác.
- Design 3.5, git ghi, giữ nguyên bảng: `["add", "--", rel]`, `["commit", "--only", "--no-gpg-sign", "--quiet", "-m", subject, "-m", body, "--", rel]`, `["rm", "--cached", "-q", "--", rel]`, với `rel` **trần, không** `:(literal)`. Đúng ADR-022 Ràng buộc ("`--` ngay trước đúng một đường dẫn"). `rel` trần chỉ an toàn vì QĐ-A2 bảo đảm `rel` không có ký tự glob và không bắt đầu bằng `:` hay `-`.
- Lệnh đọc khác không mang pathspec: `cat-file` dùng `<commit>:<rel>` (đường dẫn trong cây, không phải pathspec), `diff-tree` không nhận đường dẫn.

**Sửa:** design 3.2 bước 5, 6 (thay `-- <rel>`); design 3.5 thêm một câu dưới bảng đuôi đối số. **Task:** T38 (rework theo review-38 giữ hai dạng này; chỉ còn major `rebase-apply`). T43 không đổi. T44: `test_git_commit_add_rm_argv_shape` kiểm `--` đứng ngay trước đúng một phần tử không bắt đầu bằng `:`.
**Test:** không thêm. Đã ghim bởi `erp_ai/agent/tools/test_source.py::test_read_git_state_pathspec_is_literal` (T38) và `erp_ai/agent/changes/test_process_runner.py::test_git_write_argv_shapes` (T43).

## QĐ-A2. Tên có `* ? [ ]` hoặc bắt đầu bằng `:` / `-`: từ chối lúc đề xuất ở bộ chặn
**Quyết định.** Chọn phương án (a) của review-43: `change_guard.check_write_path` từ chối. Không đổi argv ghi sang `:(literal)`.
- Lý do: (1) `process_runner._check_git_write_call` (T43, đã merge) đã từ chối đúng tập này bằng `ValueError`; nếu bộ chặn cho qua thì đề xuất được duyệt rồi mới lỗi ở T19, sau khi ghi. (2) Tool đọc đã có tiền lệ từ chối glob (`source._git_path_ok`, `_git_log_args_ok` dùng `GIT_GLOB_CHARS`). (3) Đọc ngày 2026-11-13: 0 file đã theo dõi có tên như vậy trong 12 repo dưới `apps/`. (4) Không đụng mã đã merge, không đổi argv của ADR-022.
- Điều kiện, trùng từng ký tự với `process_runner`: gọi `rel_in_repo = os.sep.join(parts[1:])` (đường dẫn sau thư mục app, tính từ `realpath`). Từ chối khi `rel_in_repo.startswith((":", "-"))` hoặc `source.GIT_GLOB_CHARS.search(rel_in_repo)`. Dùng lại hằng của `source`, không viết regex thứ hai (STD-DESIGN-4). `-` hay `:` ở thành phần sau (`app/sub/-x.py`, `app/a:b.py`) vẫn cho qua, giống `process_runner`.
- Vị trí: ngay sau kiểm `GIT_DIR`, trước `full is None`. Như vậy lỗi này xếp sau `GIT_DIR` trong bảng 3.1.
- Mã và câu (hợp đồng, thêm vào bảng lỗi tool 3.1): `PATH_GIT_PATTERN` | `tên file có ký tự * ? [ ] hoặc bắt đầu bằng ":" hay "-", git không commit an toàn được` | thành phần sau tên app chứa `* ? [ ]`, hoặc đường dẫn trong repo bắt đầu bằng `:`/`-`.
- Lúc áp dụng, kiểm lại ở 4.3 bước 4.2 (`check_write_path(read_git=False)`) trả cùng câu trước khi ghi → `Lỗi`, 0 ghi, 0 commit. Kiểm ở `process_runner` giữ nguyên làm lớp thứ hai.

**Sửa:** design 3.1 (bảng lỗi tool: thêm một dòng sau `GIT_DIR`), 3.2 (thứ tự kiểm của `check_write_path`), 3.5 (ghi chú: `ValueError` của `_check_git_write_call` không bao giờ tới được khi bộ chặn đúng). **Task:** T42 (chưa làm, đã có `change_guard.py`, `test_change_guard.py` trong `files:`) mang thêm kiểm này. Không task đã merge nào phải đổi mã. T7 chỉ có một test dạng bảng được nối thêm ca qua T42. T19, T43, T45 không đổi.
**Test thêm (T42, `erp_ai/agent/tools/test_change_guard.py`):**
- `test_refuses_git_pattern_names` (subTest bị chặn: `app/[id].vue`, `app/src/a*.py`, `app/a?.py`, `app/a].py`, `app/:x.py`, `app/-x.py`; ca cho qua: `app/sub/-x.py`, `app/a:b.py`);
- `test_git_pattern_refusal_also_with_read_git_false` (cùng câu, 0 lệnh git);
- `test_guard_and_process_runner_agree_on_git_pattern_names` (mỗi tên bộ chặn từ chối thì `process_runner._check_git_write_call` ném `ValueError`; mỗi ca cho qua thì không ném);
- nối thêm dòng `PATH_GIT_PATTERN` vào `test_refusal_wording_matches_design_table`.

## QĐ-A3. Lệnh bench khi hết ngân sách (`limit < 1`): `Lỗi` "quá thời gian", không gọi `run_bench`
**Quyết định.** Thay design 4.3 bước 4 dòng đầu:
1. `limit = int(deadline − time.monotonic())`. Không dùng `max(0, …)`. `run_bench` nhận 1..540, và `timeout -s KILL 0` nghĩa là không giới hạn.
2. `limit < 1` → **không** gọi `run_bench`, 0 tiến trình con. `finish(Đang áp dụng → Lỗi, step="fail", reason="quá thời gian")`, đúng câu của AC-10 và của nhánh `timed_out`. Lưu `exit_code` rỗng (`None`), `duration_ms = 0`, `command_output = ""` lên đề xuất và vào `value_after` của đúng 1 dòng nhật ký `fail`.
3. `limit ≥ 1` → `run_bench(args, limit)` như cũ (`limit ≤ 540` vì `deadline = bắt đầu + COMMAND_TIMEOUT_S`).
- Không dùng `max(1, …)` như git. Với bench, 1 s không đủ chạy lệnh nào, và vẫn vượt hạn chót của job.

**Sửa:** design 4.3 bước 4 (dòng `limit = max(0, …)`). **Task:** T21 (sửa `Returns`, thêm AC-10 vào `Criterion`). T22 không đổi (`test_limit_passed_is_remaining_budget` vẫn đúng). T11 không đổi (`ValueError` khi `limit_s` ngoài 1..540 vẫn là hợp đồng).
**Test thêm (T21, `erp_ai/agent/changes/test_apply_job.py`):**
- `test_command_without_budget_fails_as_timeout_without_subprocess` (stub `time.monotonic`; subTest còn 0.999 s và −5 s: `Lỗi`, lý do `quá thời gian`, 0 lời gọi `subprocess.run`, `exit_code` rỗng, `duration_ms = 0`, 1 dòng `fail`);
- `test_command_budget_of_one_second_runs_with_limit_1` (còn 1.0 s → `run_bench(args, 1)`, đúng 1 lời gọi).

## Assumptions decided by the team
- QĐ-A2 làm bot không sửa được file tên kiểu `[id].vue`. Hiện có 0 file như vậy. Khi cần, mở design mới đổi argv sang `:(literal)` (phải sửa ADR-022 Ràng buộc).
- Không có câu hỏi nghiệp vụ.
