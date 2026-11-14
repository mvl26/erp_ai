Feature: CHG-002
Stage: plan
Author-agent: tech-lead
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. G3 tắt (config.json), để trống. -->

# Tasks CHG-002

Mỗi task 2–5 phút (trừ T1, xem "Ngoại lệ cỡ"). Hai task chung file thì phụ thuộc nhau. Đánh dấu `BLOCKED: <lý do>` cuối dòng khi bị chặn.
Đường dẫn trong `files:` và `test:` tính từ gốc repo `apps/erp_ai`. `test_one` = slot `cmd.test_one` với `{file}` là file ở dòng `test:`; mọi lần chạy qua khóa `.team/miyano-site.lock`.
Giá trị dùng chung (tên trường, hằng, chữ ký, câu chữ) nằm ở `plan.md` mục "Shared constraints"; mọi task thừa hưởng. `§` là mục của `design.md`; số dòng `file:line` trong design là của `develop` @ `2fd42ad`, dò lại bằng tên hàm.
Viết tắt tên file test theo design §8: `AB` = `test_apply_block.py`, `BB` = `test_block_boundary.py`, `CG` = `test_change_guard.py`, `PC` = `test_propose_change.py`, `PR` = `test_process_runner.py`, `TR` = `test_transitions.py`, `RC` = `test_result_comment.py`, `RS` = `test_restart_check.py`, `BL` = `test_block.py`, `DOC` = `test_erp_ai_change_proposal.py`, `ARCH` = `test_architecture.py`.
Mọi task: test đỏ trước rồi mới sửa mã (STD-TEST-1), trừ các task ghi "test đặc tả" hoặc "test nghiệm thu": ở đó xanh ngay lần đầu là kết quả hợp lệ, đỏ thì sửa trong đúng các file ở `files:`.
`design-addendum-1.md` (2026-11-15) **thắng `design.md`** ở chỗ hai bên khác nhau; `A-n` trong task là mục của addendum. Đã chép vào task (build lượt 1): T3, T4, T5, T6, T8, T12, T13, T23, T24, T25, T26, T33, T35, T39, T41, T47, T49, T50.
Cách chạy test của nhánh task (site `miyano` nạp mã ở cây chính, nên phải trỏ `PYTHONPATH` về worktree): từ thư mục bench `/home/miyano/frappe-bench`, `flock -w 1800 apps/erp_ai/.team/miyano-site.lock env PYTHONPATH=<worktree của dev> bench --site miyano run-tests --module <module>`. `bench run-tests` thoát mã 0 cả khi đỏ: đọc dòng `Ran N tests` và `OK`/`FAILED`.

baseline: chưa đo; tech-lead chạy `cmd.test` trên `team/CHG-002` trước T0 và ghi kết quả vào dòng này.
Nhánh `team/CHG-002` chưa tồn tại: `/team:build` tạo nó từ `develop` ở bước đầu. Tối đa 4 dev cùng lúc theo bảng làn ở `plan.md` mục "Nhóm song song".

## Phần 0 — Cổng và walking skeleton

- [ ] T0 — Test đặc tả: `git commit --only` ghi nhận file đã xóa (T-0 của design) — files: erp_ai/agent/changes/test_process_runner.py — test: erp_ai/agent/changes/test_process_runner.py — depends: —
  - Criterion: AC-38, AC-52 (R-9; §8.0). Test đặc tả hành vi git, không sửa mã sản phẩm.
  - Receives: `GitSandbox` (`erp_ai/test_utils.py`), `file_writer.remove_created(full)`, `process_runner.git_commit_only(repo_root, rel_in_repo, subject, body, limit_s)` chữ ký hiện có.
  - Returns: lớp `TestCommitOnlyRecordsDeletion` với `test_single_deleted_path_recorded`: mã thoát 0; `diff-tree --no-commit-id --name-status -r HEAD` = `D\tmyapp/a.py`; `ls-files myapp/a.py` rỗng; `status --porcelain` rỗng; file staged khác của sandbox vẫn staged; in phiên bản git.
  - Expect: `test_one` → `test_single_deleted_path_recorded` xanh. Đỏ thì dừng cả kế hoạch và báo team-leader (cần ADR mới).

- [ ] T1 — Walking skeleton: khối 1 mục sửa đi từ tool tới commit — files: erp_ai/constants.py, erp_ai/erp_ai_agent/doctype/erp_ai_change_operation/__init__.py, erp_ai/erp_ai_agent/doctype/erp_ai_change_operation/erp_ai_change_operation.json, erp_ai/erp_ai_agent/doctype/erp_ai_change_operation/erp_ai_change_operation.py, erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.json, erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py, erp_ai/agent/tools/change_guard.py, erp_ai/agent/tools/propose_change.py, erp_ai/agent/changes/block.py, erp_ai/agent/changes/transitions.py, erp_ai/agent/changes/apply_job.py, erp_ai/agent/changes/test_apply_block.py — test: erp_ai/agent/changes/test_apply_block.py — depends: T0
  - Ngoại lệ cỡ: 12 file vì đây là lát cắt đầu-cuối cỡ L (plan.md "Walking skeleton"); mọi lõi giả, chỉ một mục `edit`, không lệnh. Được sửa `erp_ai/agent/tools/test_registry.py` **chỉ** ở assertion ghim `required` của `propose_file_change`, nếu có.
  - Criterion: AC-36 (khung: 1 đề xuất, 1 comment, 1 lần duyệt, 1 commit); §2.1, §2.2, §2.4.
  - Receives: `make_ticket`, `TempAppsRoot`, `GitSandbox`, `pin_agent_roles`; `propose_change._insert`; `apply_job.run_change(name, "apply")`; phương thức `approve`.
  - Returns:
    - `constants.py`: toàn bộ khối "CHG-002" ở plan.md "Shared constraints" (chưa xóa hai hằng cũ);
    - DocType con `ERP AI Change Operation` đúng §2.1; lớp `ERPAIChangeOperation(Document)` rỗng;
    - `erp_ai_change_proposal.json`: 6 trường §2.2, đều `read_only = 1`;
    - `change_guard.FileOp` (dataclass frozen, đúng 7 trường);
    - `block.py`: `is_block(doc)`, `operations_of(doc)`, `commands_of(doc)` cho **dạng khối** (dạng cũ ở T18);
    - `transitions.content_digest`: dạng cũ giữ nguyên từng byte; dạng khối nối thêm danh sách dòng và `command_list` (§2.4);
    - controller `_set_commit_message`: khối 1 mục dùng nhãn là đường dẫn của mục;
    - `propose_change.propose_file_change`: có `changes` thì gọi `_propose_block(changes, commands, reason, ctx)` bản giả (chỉ `edit`, mỗi mục qua `check_write_path` hiện có), một `insert` cha cùng dòng con, `change_kind = Thay đổi code`, trường vô hướng `file_path`/`content_*` rỗng; schema thêm `changes`, `required = ["reason"]`;
    - `apply_job._run`: `block.is_block(proposal)` thì đi `_apply_block` bản giả (kiểm người chạy, vai trò, công tắc, dấu; ghi; 1 commit); dạng cũ đi đường cũ.
  - Expect: `test_one` → `TestWalkingSkeleton::test_one_edit_block_proposed_approved_applied_one_commit` xanh (1 đề xuất `Chờ duyệt` có 1 dòng con, 1 comment, sau duyệt và job: file đúng byte, 1 commit chứa đúng 1 đường dẫn, `Đã áp dụng`); `cmd.test` xanh sau `cmd.migrate`.
  - Gộp: reviewer `approve` trước khi T2..T50 bắt đầu.

## Phần 1 — Nền

- [ ] T2 — Helper test: `make_block_proposal`, vành đai so thêm repo `erp_ai` thật — files: erp_ai/test_utils.py, erp_ai/tests/test_test_utils.py — test: erp_ai/tests/test_test_utils.py — depends: T1
  - Criterion: NFR-14 (R-11); công cụ cho AC-37..AC-55.
  - Receives: `OPERATION_DOCTYPE`, `CHANGE_OPS`, `change_guard.FileOp` (T1); `make_change_proposal`, `real_core_repos_snapshot`.
  - Returns: `make_block_proposal(operations, commands, ticket=None, **fields)` chèn đề xuất dạng khối `Chờ duyệt` (dòng con từ danh sách `FileOp` hoặc dict, `command_list` JSON, hash tự tính, `ignore_permissions=True`, không commit); `real_core_repos_snapshot()` thêm khóa `erp_ai` (HEAD và `status --porcelain` của repo `erp_ai` thật).
  - Expect: `test_one` → `TestMakeBlockProposal::test_rows_hashes_and_command_list_stored`, `TestRealCoreRepos::test_snapshot_includes_erp_ai` xanh.

- [ ] T3 — Luật "văn bản cho phép": `source.text_refusal` — files: erp_ai/agent/tools/source.py, erp_ai/agent/tools/test_source.py — test: erp_ai/agent/tools/test_source.py — depends: T1
  - Criterion: AC-44 (§3.2; ADR-040 QĐ 5).
  - Receives: `CHANGE_FILE_MAX_BYTES` (T1, `erp_ai/constants.py`).
  - Returns (A-1.2, A-1.3, A-1.4, A-5): `TEXT_MAX_BYTES = CHANGE_FILE_MAX_BYTES` (tên nhập lại từ `erp_ai.constants`, không gán số); `TEXT_TOO_LARGE = f"file lớn hơn {TEXT_MAX_BYTES // (1024 * 1024)} MiB"` (= `file lớn hơn 2 MiB`); hằng `TEXT_NOT_UTF8`, `TEXT_HAS_NUL`, `TEXT_SECRET_NAME`, `GIT_DIR` đúng chữ §3.1; `text_refusal(rel_path, data=None)` theo đúng thứ tự: `TEN_CAM` → thành phần bắt đầu bằng `.git` → kích thước (`len(data) > TEXT_MAX_BYTES`, phép so kích thước duy nhất) → NUL → UTF-8 chặt; `SETSID_EXECUTABLE = "setsid"` ngay cạnh `TIMEOUT_EXECUTABLE`, `BENCH_EXECUTABLE`. `SEARCH_FILE_MAX_BYTES` còn nguyên (xóa ở T49).
  - Expect: `test_one` → `TestTextRefusal::test_order_and_reasons`, `test_github_component_refused`, `test_two_mib_ok_plus_one_refused_names_2_mib` xanh.

- [ ] T4 — Tool đọc dùng luật văn bản, bỏ lọc theo đuôi — files: erp_ai/agent/tools/source.py, erp_ai/agent/tools/test_source.py — test: erp_ai/agent/tools/test_source.py — depends: T3
  - Criterion: AC-44 (§3.2 "Nơi dùng hàm").
  - Receives: `text_refusal` (T3).
  - Returns (A-1.4): `resolve_safe_path` thay hai dòng kiểm `TEN_CAM` và đuôi bằng `text_refusal(rel) is None`; `read_source` mở `rb`, `data = handle.read(TEXT_MAX_BYTES + 1)`, `text_refusal(rel, data)` có lý do thì `_refuse(reason)` (file quá cỡ: đúng câu `TEXT_TOO_LARGE`), không thì giải mã UTF-8 chặt và chia trang như cũ; `search_source` thay phép so `getsize` bằng đọc `TEXT_MAX_BYTES + 1` byte rồi `text_refusal(rel, data) is not None` thì bỏ file, `_scan_file(full, …)` thành `_scan_text(text, rel, needle, hits)`; tham số `extension` thành `{"type":"string","pattern":"^\\.[A-Za-z0-9]{1,10}$"}`. Hằng `DUOI_CHO_PHEP` và `SEARCH_FILE_MAX_BYTES` còn định nghĩa nhưng `source.py` không dùng nữa (xóa ở T49).
  - Expect: `test_one` → `TestTextRule::test_read_yaml_toml_noext_ok`, `test_read_binary_refused`, `test_search_skips_binary`, `test_extension_pattern`, `TestReadSource::test_file_between_one_and_two_mib_readable`, `test_file_over_two_mib_refused_same_reason`, `TestSearchSource::test_file_between_one_and_two_mib_searched_over_two_skipped` xanh; test cũ ghim 8 đuôi sửa theo §8.3.

- [ ] T5 — `file_writer`: tạo thư mục cha, gỡ thư mục rỗng — files: erp_ai/agent/changes/file_writer.py, erp_ai/agent/changes/test_file_writer.py — test: erp_ai/agent/changes/test_file_writer.py — depends: T1
  - Criterion: AC-39 (§3.5).
  - Returns (A-3.1): hàm riêng `_refuse_unsafe_path(full_path) -> None` ném `ValueError` khi (1) đường dẫn ngoài `realpath(source.get_source_root())`, (2) một thành phần bắt đầu bằng `.git`, (3) `realpath(dirname) != dirname`; `_refuse_git_dir` và `write_atomic` chưa đổi (T6); `make_parents(full_path, app_dir) -> list[str]` (từ trên xuống, `os.mkdir(d, 0o755)`, sau mỗi thư mục kiểm `_refuse_unsafe_path(d)` cộng `os.path.islink(d)`; sai thì gỡ phần vừa tạo rồi `ValueError`); `remove_empty_dirs(dirs) -> list[str]` (từ sâu nhất lên; **bỏ qua**, không lỗi, không có trong kết quả, khi `islink(d)`, `_refuse_unsafe_path(d)` ném lỗi, `realpath(d) != abspath(d)` hoặc thư mục không rỗng; còn lại `os.rmdir(d)`).
  - Expect: `test_one` → `TestMakeParents::test_three_levels_created_top_down`, `test_app_dir_missing_raises`, `test_git_component_rolls_back`, `TestRemoveEmptyDirs::test_keeps_nonempty_and_preexisting`, `test_symlink_dir_skipped_target_untouched`, `test_git_component_dir_skipped`, `test_deepest_first_nonempty_kept` xanh.

- [ ] T6 — `file_writer`: `remove_file` thay `remove_created`, `write_atomic` chặn `.git*` và symlink — files: erp_ai/agent/changes/file_writer.py, erp_ai/agent/changes/test_file_writer.py, erp_ai/agent/changes/apply_job.py, erp_ai/agent/changes/test_apply_job.py — test: erp_ai/agent/changes/test_file_writer.py — depends: T5
  - Criterion: AC-40, AC-52 (§3.5).
  - Receives: `_refuse_unsafe_path` (T5).
  - Returns (A-3.1, A-1.2): `remove_file(full)` theo thứ tự `_refuse_unsafe_path(full)` → `islink(full)` hoặc `not isfile(full)` thì `ValueError` → `os.remove(full)`, mọi kiểm ngay trước `os.remove`; `write_atomic` gọi `_refuse_unsafe_path(full)` trước khi tạo file tạm; xóa `_refuse_git_dir` (không còn người dùng) và `file_writer.PROPOSAL_FILE_MAX_BYTES` cùng assertion ghim `== 1048576` và import của nó ở `test_file_writer.py` (đổi vì ADR-040 C-1, STD-TEST-5). `apply_job.py` và `test_apply_job.py`: chỉ đổi tên lời gọi và `patch.object` từ `remove_created` sang `remove_file`.
  - Expect: `test_one` → `TestRemoveFile::test_regular_file_removed`, `test_symlink_or_directory_refused`, `test_parent_dir_symlink_refused_zero_removed`, `test_git_component_refused_file_kept`, `test_outside_source_root_refused`, `TestWriteAtomic::test_parent_symlink_and_git_component_refused` xanh; `test_one` với `erp_ai/agent/changes/test_apply_job.py` xanh.

- [ ] T7 — `git_commit_only` nhận nhiều đường dẫn — files: erp_ai/agent/changes/process_runner.py, erp_ai/agent/changes/test_process_runner.py, erp_ai/agent/changes/apply_job.py, erp_ai/agent/changes/test_apply_job.py, erp_ai/tests/test_architecture.py — test: erp_ai/agent/changes/test_process_runner.py — depends: T6
  - Criterion: AC-38, AC-52 (§3.4, §8.0 test thứ hai, §8.2 hàng "commit có `--` rồi 1..N đường dẫn").
  - Receives: `TestCommitOnlyRecordsDeletion` (T0).
  - Returns: `git_commit_only(repo_root, rels: tuple[str, ...], subject, body, limit_s)`; `rels` khác rỗng, không trùng, mỗi phần tử qua luật đường dẫn của `_check_git_write_call`; argv kết thúc bằng `"--", *sorted(rels)`. Hai lời gọi trong `apply_job.py` truyền `(rel,)`. `ARCH::_write_argv_problems` và `test_git_commit_add_rm_argv_shape`: commit có 1..N đường dẫn sau `--`; `add` và `rm --cached` vẫn đúng 1. `erp_ai/test_change_decision.py` chỉ sửa stub ở dòng patch `git_commit_only` nếu nó đỏ vì chữ ký.
  - Expect: `test_one` → `test_multi_path_delete_add_modify_rename_in_one_commit` (`name-status` đúng `{D a.py, M b.py, A c.py, D old.txt, A new/dir/new.txt}`, file staged và unstaged ngoài khối giữ nguyên), `test_empty_or_duplicate_rels_refused`, `test_single_deleted_path_recorded` (đổi sang tuple) xanh; `test_one` với `test_apply_job.py` và `erp_ai/tests/test_architecture.py` xanh.

- [ ] T8 — `process_runner.launch_restart` và `RESTART_ARGV` — files: erp_ai/agent/changes/process_runner.py, erp_ai/agent/changes/test_process_runner.py — test: erp_ai/agent/changes/test_process_runner.py — depends: T7, T3
  - Criterion: AC-45 (§3.4, §4.4 bước 2; ADR-040 QĐ 7; A-5).
  - Receives: `RESTART_TIMEOUT_S`, `RESTART_LAUNCH_TIMEOUT_S` (T1); `source.SETSID_EXECUTABLE` (T3), `source.TIMEOUT_EXECUTABLE`, `source.BENCH_EXECUTABLE`; `_minimal_env()`.
  - Returns: `RESTART_ARGV = (source.SETSID_EXECUTABLE, "-f", source.TIMEOUT_EXECUTABLE, "-s", "KILL", str(RESTART_TIMEOUT_S), source.BENCH_EXECUTABLE, "restart")`; `launch_restart() -> tuple[bool, str | None]` gọi `subprocess.run` đúng tham số §3.4; `(True, None)` khi mã thoát 0; `(False, <tên lớp lỗi>)` với `FileNotFoundError`, `TimeoutExpired`, `OSError` hoặc mã thoát khác 0; không ném lỗi.
  - Expect: `test_one` → `TestLaunchRestart::test_argv_shape` (so với các hằng của `source`; chuỗi `"setsid"` không viết lại trong `process_runner.py`), `test_argv_cwd_env_devnull_timeout_new_session` (stub `subprocess.run`), `test_nonzero_exit_returns_false`, `test_file_not_found_timeout_oserror_return_class_name` xanh. Không test nào chạy `bench restart` thật.

- [ ] T9 — Bộ chặn đường dẫn: luật tên và `.git*`, bỏ luật đuôi — files: erp_ai/agent/tools/change_guard.py, erp_ai/agent/tools/test_change_guard.py, erp_ai/agent/tools/test_propose_change.py — test: erp_ai/agent/tools/test_change_guard.py — depends: T4
  - Criterion: AC-44, AC-50, AC-51, AC-52 (§3.2 `check_write_path` bước 1–5).
  - Receives: `source.text_refusal`, `source.TEXT_SECRET_NAME`, `source.GIT_DIR` (T3).
  - Returns: `check_write_path` theo thứ tự 1–5 của §3.2; `NAME_FORBIDDEN` trỏ tới `source.TEXT_SECRET_NAME`; `GIT_DIR` chữ mới `không được chạm .git hoặc tên bắt đầu bằng .git`; thư mục app không tồn tại thì `PATH_INVALID`; xóa `EXT_FORBIDDEN` và bước kiểm đuôi. `test_propose_change.py`: chỉ sửa test ghim 8 đuôi (§8.3).
  - Expect: `test_one` → `TestCheckWritePath::test_any_text_extension_allowed`, `test_gitignore_gitattributes_github_refused_git_dir`, `test_secret_name_refused_before_git_rule`, `test_missing_app_dir_path_invalid`, `test_erp_ai_in_allowed_list_still_refused` xanh; `test_one` với `test_propose_change.py` xanh.

- [ ] T10 — Bộ chặn đường dẫn: symlink và kho git lồng — files: erp_ai/agent/tools/change_guard.py, erp_ai/agent/tools/test_change_guard.py — test: erp_ai/agent/tools/test_change_guard.py — depends: T9
  - Criterion: AC-50 (symlink, worktree), AC-52 (§3.2 bước 6–7).
  - Receives: `_common_dirs_upward(start, stop, *, nearest_only)`.
  - Returns: hằng `PATH_SYMLINK`, `NESTED_REPO` đúng chữ §3.1; bước 6 (`normpath` của phần đang tồn tại khác `realpath`) và bước 7 (`.git` gần nhất từ thư mục tồn tại sâu nhất lên tới thư mục app phải cùng common dir với thư mục app).
  - Expect: `test_one` → `TestCheckWritePath::test_path_through_symlink_refused`, `test_symlink_to_erp_ai_refused`, `test_nested_repo_refused`, `test_new_dirs_not_yet_existing_use_deepest_existing` xanh.

- [ ] T11 — Danh sách lệnh bench thêm `restart` — files: erp_ai/agent/tools/change_guard.py, erp_ai/agent/tools/test_change_guard.py — test: erp_ai/agent/tools/test_change_guard.py — depends: T10
  - Criterion: AC-47 (§3.2 `BENCH_COMMANDS`).
  - Returns: `RESTART_COMMAND = "restart"` trong `BENCH_COMMANDS`; `build_bench_args("restart", None, …)` trả `["restart"]`; `check_bench_args(["restart"], …)` trả `None`; có đối số nào khác thì `CMD_NOT_LISTED` hoặc `CMD_TAKES_NO_APP`.
  - Expect: `test_one` → `TestBenchArgs::test_restart_plain_accepted`, `test_restart_with_any_arg_refused`, `test_every_denied_command_refused` (21 lệnh của AC-47), `test_force_shell_other_site_refused` xanh; test cũ `test_bench_allow_list_is_exactly_the_six_design_commands` sửa thành đúng 7 lệnh (§8.3).

- [ ] T12 — `check_block`: hình dạng khối, đường dẫn, thư mục mới, một app — files: erp_ai/agent/tools/change_guard.py, erp_ai/agent/tools/test_change_guard.py — test: erp_ai/agent/tools/test_change_guard.py — depends: T11
  - Criterion: AC-36 (hai app), AC-39 (§3.2 `check_block` bước 1–2 trừ nội dung và cú pháp; D-9).
  - Receives: `FileOp` (T1), `check_write_path` (T10), `CHANGE_MAX_FILE_OPS`, `CHANGE_MAX_COMMANDS`.
  - Returns: `BlockCheck(reason, app, targets)`, `OpTarget(op, full_path, full_new_path, new_dirs, guard)`, `check_block(ops, commands, allowed_apps, site, *, at_apply: bool, diff_text: str, legacy: bool = False)` (A-1.4: `diff_text` bắt buộc, không mặc định; đếm ở T13); hằng `BLOCK_EMPTY`, `BLOCK_TOO_MANY_OPS`, `BLOCK_TOO_MANY_COMMANDS`, `BLOCK_TWO_APPS`, `BLOCK_PATH_TWICE`, `OP_UNKNOWN`, `OP_FIELDS`, cùng hai hằng câu chữ `NOT_REGULAR_FILE`, `EXECUTABLE_FILE` (tool dùng ở T27); lý do có tiền tố `mục {n} ({đường dẫn}): `; `read_git = not at_apply`; từng thư mục của `new_dirs` qua `check_write_path(dir, new_file=True, read_git=False)`.
  - Expect: `test_one` → `TestCheckBlock::test_empty_block_refused`, `test_ops_50_ok_51_refused`, `test_commands_6_ok_7_refused`, `test_two_apps_refused_names_both`, `test_path_twice_refused`, `test_path_inside_another_path_refused`, `test_new_dir_directly_under_apps_refused`, `test_new_dir_under_sites_refused`, `test_new_dir_in_unlisted_app_refused`, `test_reason_names_item_number_and_path` xanh.

- [ ] T13 — `check_block`: nội dung văn bản, tổng byte, cú pháp `.py` và `.json` — files: erp_ai/agent/tools/change_guard.py, erp_ai/agent/tools/test_change_guard.py — test: erp_ai/agent/tools/test_change_guard.py — depends: T12
  - Criterion: AC-43 (trần), AC-46 (a) (§3.2 bước 2 phần `text_refusal` và cú pháp, bước 3).
  - Receives: `source.text_refusal`, `source.TEXT_MAX_BYTES`, `CHANGE_MAX_TOTAL_BYTES`.
  - Returns (A-1.2, A-1.3, A-1.4): hằng `BLOCK_TOO_LARGE = f"tổng nội dung của khối (kể cả diff) lớn hơn {CHANGE_MAX_TOTAL_BYTES // (1024 * 1024)} MiB"`, `PY_SYNTAX`, `JSON_SYNTAX`; `total = Σ(len(before.encode()) + len(after.encode()))` trên mọi dòng (thiếu tính 0; đổi tên tính hai lần) `+ len(diff_text.encode("utf-8"))`, `total > CHANGE_MAX_TOTAL_BYTES` thì `BLOCK_TOO_LARGE`, đúng bằng trần thì nhận; trần mỗi file chỉ qua `text_refusal` (không so `TEXT_MAX_BYTES` ở `change_guard.py`); `compile(after, rel, "exec", dont_inherit=True)` cho đích `.py`, `json.loads(after)` cho đích `.json`, áp cho Sửa, Tạo, đích Đổi tên; `RecursionError` và `MemoryError` là `PY_SYNTAX` dòng 0.
  - Expect: `test_one` → `TestCheckBlock::test_py_syntax_error_refused_with_line`, `test_json_invalid_refused_with_line`, `test_rename_dest_py_checked`, `test_total_bytes_at_limit_ok_plus_one_refused` (tổng có `diff_text`), `test_total_counts_diff_bytes` (trước + sau ≤ 8 MiB, cộng `diff_text` > 8 MiB thì từ chối), `test_file_at_text_max_ok_plus_one_refused` (biên 2 MiB, lý do chứa `2 MiB`), `test_content_with_nul_refused` xanh, mỗi ca ở cả `at_apply=False` và `True`.

- [ ] T14 — `check_block`: luật lệnh và restart — files: erp_ai/agent/tools/change_guard.py, erp_ai/agent/tools/test_change_guard.py — test: erp_ai/agent/tools/test_change_guard.py — depends: T13
  - Criterion: AC-45, AC-47 (§3.2 bước 4; R-4, R-5, D-3).
  - Receives: `check_bench_args`, `RESTART_COMMAND` (T11).
  - Returns: hằng `RESTART_PLACE`, `RESTART_NEEDS_MIGRATE`, `PY_NEEDS_RESTART`, `RESTART_WITHOUT_PY`; lý do lệnh có tiền tố `lệnh {n}: `; luật `.py ⇔ restart` chỉ khi khối có mục file và `legacy=False`; `.py` tính trên mọi đường dẫn của khối kể cả nguồn và đích đổi tên.
  - Expect: `test_one` → `TestCheckBlock::test_command_only_restart_block_valid`, `test_restart_twice_or_not_last_refused`, `test_py_without_restart_refused`, `test_restart_without_py_refused`, `test_file_block_restart_without_migrate_refused`, `test_legacy_py_without_restart_allowed`, `test_denied_command_in_block_names_command_number` xanh.

- [ ] T15 — `transitions`: trường trạng thái mới, `record_commit`, `finish(command_results=)` — files: erp_ai/agent/changes/transitions.py, erp_ai/agent/changes/test_transitions.py — test: erp_ai/agent/changes/test_transitions.py — depends: T1
  - Criterion: AC-37, AC-49 (§3.6).
  - Returns: `STATE_FIELDS` thêm `command_results`, `created_dirs`, `restart_status`, `restart_sent_at` (`prepare_new` xóa trắng); `GIT_RESULT_FIELDS` thêm `created_dirs`; `record_commit(name, expected, *, fields) -> bool` (chỉ khi đang `Đang áp dụng` hoặc `Đang hoàn tác`, không đổi trạng thái, không ghi nhật ký, trạng thái khác `expected` trả `False`); `finish(…, command_results=None)` ghi JSON.
  - Expect: `test_one` → `TestPrepareNew::test_new_state_fields_cleared`, `TestRecordCommit::test_writes_git_fields_keeps_status_no_log_row`, `test_wrong_status_returns_false`, `TestFinish::test_command_results_stored` xanh.

- [ ] T16 — `transitions`: cạnh `Lỗi → Đang hoàn tác` có điều kiện — files: erp_ai/agent/changes/transitions.py, erp_ai/agent/changes/test_transitions.py — test: erp_ai/agent/changes/test_transitions.py — depends: T15
  - Criterion: AC-42 (§3.3 `undo`, §3.6, §4.3 đoạn "Cạnh mới").
  - Returns: `request_undo` nhận `Lỗi` khi và chỉ khi `change_kind = Thay đổi code`, `apply_commit_sha` có, `undo_commit_sha` rỗng; `_lock` đọc thêm hai trường này; câu từ chối giữ nguyên; khối chỉ có lệnh: `Lệnh bench không hoàn tác được`.
  - Expect: `test_one` → `TestRequestUndo::test_from_failed_needs_apply_sha_and_no_undo_sha`, `test_from_failed_without_sha_refused`, `test_command_only_block_not_undoable`, `test_two_callers_one_wins` xanh; test cũ `test_request_undo_refused_for_code_outside_applied` sửa theo §8.3 (vẫn từ chối mọi trạng thái khác).

- [ ] T17 — `transitions`: `record_restart`, `confirm_restart` — files: erp_ai/agent/changes/transitions.py, erp_ai/agent/changes/test_transitions.py — test: erp_ai/agent/changes/test_transitions.py — depends: T16
  - Criterion: AC-45, AC-46 (c) (§3.6).
  - Receives: `RESTART_STATUS_*` (T1).
  - Returns: `record_restart(name, expected, value, sent_at) -> bool` (`expected` ∈ {`Đã áp dụng`, `Đã hoàn tác`}, `value` ∈ {`Đã gửi`, `Lỗi khởi chạy`}, không ghi nhật ký, không đổi `change_status`); `confirm_restart(name, value) -> bool` (chỉ từ `Đã gửi`, `value` ∈ {`Đã xác nhận`, `Chưa xác nhận`}).
  - Expect: `test_one` → `TestRecordRestart::test_sent_and_launch_failed_stored_status_unchanged`, `test_wrong_expected_or_value_refused`, `TestConfirmRestart::test_only_from_sent`, `test_invalid_value_refused` xanh.

- [ ] T18 — Bộ chuyển đổi đọc đề xuất dạng cũ — files: erp_ai/agent/changes/block.py, erp_ai/agent/changes/test_block.py — test: erp_ai/agent/changes/test_block.py — depends: T1
  - Criterion: AC-42 (tương thích), §2.3, §2.4, §3.8.
  - Receives: `block.is_block`, `operations_of`, `commands_of` dạng khối (T1); `make_change_proposal`.
  - Returns: `operations_of` dạng cũ trả 1 `FileOp` `Sửa` hoặc `Tạo` từ các trường vô hướng; đề xuất lệnh dạng cũ trả `()`; `commands_of` dạng cũ trả `[command_args]` hoặc `[]`.
  - Expect: `test_one` → `TestAdapter::test_legacy_edit_one_op`, `test_legacy_new_file_one_create_op`, `test_legacy_command_one_argv`, `test_block_rows_in_idx_order`, `TestLegacyDigest::test_legacy_digest_is_byte_identical` (giá trị dấu ghim bằng chuỗi hex tính từ công thức 14 trường) xanh.

- [ ] T19 — Thân commit của khối: nhãn và danh sách mục — files: erp_ai/agent/change_text.py, erp_ai/agent/test_change_text.py — test: erp_ai/agent/test_change_text.py — depends: T1
  - Criterion: AC-38 (§3.7 "Commit message").
  - Returns: `apply_message(proposal, ticket, label, approver, operations=None)`, `undo_message(…, operations=None)`; có `operations` thì thân thêm sau dòng "Phiếu" các dòng `sửa …`, `tạo …`, `xóa …`, `đổi tên … → …`; `operations=None` cho đúng chữ cũ; hàm `block_label(operations) -> str` trả đường dẫn khi 1 mục, `{n} file` khi nhiều hơn.
  - Expect: `test_one` → `TestBlockMessage::test_none_operations_is_byte_identical_to_old`, `test_body_lists_each_item_after_ticket_line`, `test_label_path_or_n_files` xanh.

- [ ] T20 — `proposal_notes` của khối: đếm, từng mục, lệnh, dòng restart — files: erp_ai/agent/change_text.py, erp_ai/agent/test_change_text.py — test: erp_ai/agent/test_change_text.py — depends: T19
  - Criterion: AC-48 (§3.7 dòng 1–6; R-6, D-4).
  - Receives: `proposal_fields` có `operations` (danh sách dòng con) và `command_list` (JSON).
  - Returns: `proposal_notes` cho dạng khối theo đúng thứ tự và chữ §3.7 (dòng `XÓA`, `ĐỔI TÊN … → …` viết hoa; dòng "sẽ restart" khi và chỉ khi có `restart`; dòng "Lệnh trong khối không hoàn tác được…" khi có lệnh); câu `Sau khi áp dụng cần người chạy bench restart.` chỉ còn ở dạng cũ.
  - Expect: `test_one` → `TestBlockNotes::test_counts_then_items_then_commands_in_order`, `test_restart_line_iff_restart_listed`, `test_commands_not_undoable_line`, `test_legacy_py_note_only_for_legacy`, `test_no_remote_url` xanh.

- [ ] T21 — Nhãn kết quả restart trên form — files: erp_ai/agent/change_text.py, erp_ai/agent/test_change_text.py — test: erp_ai/agent/test_change_text.py — depends: T20
  - Criterion: AC-45 (R-2, D-13), AC-46 (c) (§3.7 "Nhãn trên form").
  - Receives: `RESTART_STATUS_*` (T1); trường `restart_status`, `restart_sent_at`.
  - Returns: `proposal_notes` thêm đúng một nhãn theo bảng §3.7 cho bốn giá trị; rỗng thì không thêm.
  - Expect: `test_one` → `TestRestartLabel::test_four_values_exact_text`, `test_unconfirmed_says_permission_may_be_missing_and_todo_restart`, `test_empty_status_no_label` xanh.

- [ ] T22 — Controller: dòng con bất biến, `command_list` là nội dung, bản xem trước commit của khối — files: erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py, erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py — test: erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py — depends: T19, T2
  - Criterion: AC-54 (§2.4, §7 hàng controller; ADR-012 QĐ 1).
  - Receives: `change_text.apply_message(…, operations=)`, `change_text.block_label` (T19); `block.operations_of` (T1); `make_block_proposal` (T2).
  - Returns: `CONTENT_FIELDS` thêm `command_list`; `validate` so dòng con với `get_doc_before_save()` (số dòng, thứ tự và 7 trường của từng dòng), khác thì ném câu "Nội dung đề xuất không sửa được sau khi tạo" hiện có; `_set_commit_message` của khối dùng `block_label` và `operations`.
  - Expect: `test_one` → `TestERPAIChangeProposal::test_child_rows_immutable_after_insert`, `test_row_added_or_removed_refused`, `test_command_list_immutable`, `test_block_commit_preview_lists_items` xanh.

- [ ] T23 — Bằng chứng restart: `restart_check` — files: erp_ai/agent/changes/restart_check.py, erp_ai/agent/changes/test_restart_check.py — test: erp_ai/agent/changes/test_restart_check.py — depends: T1
  - Criterion: AC-46 (c) (§4.4 bước 5; D-5).
  - Receives: `RESTART_TIMEOUT_S`, `RESTART_STATUS_CONFIRMED`, `RESTART_STATUS_UNCONFIRMED` (T1).
  - Returns (A-6: mọi mốc đổi về epoch giây UTC trước khi so): `outcome(sent_epoch, now_epoch, web_epoch, workers_epoch)` thuần; hai hàm thuần `epoch_of_naive_utc(dt) -> float` (`dt.replace(tzinfo=datetime.timezone.utc).timestamp()`, cho `birth_date` của rq) và `epoch_of_system_time(dt, tz_name) -> float` (`dt.replace(tzinfo=zoneinfo.ZoneInfo(tz_name)).timestamp()`, cho `restart_sent_at`, `tz_name = frappe.utils.get_system_timezone()`); `web_started() -> float | None` (`psutil.Process(os.getppid()).create_time()`); `workers_started() -> float | None` (`min` của `epoch_of_naive_utc(w.birth_date)` trên `frappe.utils.background_jobs.get_workers()`; rỗng, lỗi Redis hay psutil trả `None`). Cấm `.timestamp()` trên `datetime` không múi giờ. Không subprocess, không ghi hệ tệp, không enqueue.
  - Expect: `test_one` → `TestOutcome::test_both_started_after_confirmed`, `test_web_old_after_deadline_unconfirmed`, `test_before_deadline_no_conclusion`, `test_redis_or_psutil_error_is_no_evidence`, `TestEpoch::test_rq_naive_utc_and_system_tz_compare_on_same_base`, `test_independent_of_process_timezone` (đặt `TZ` bằng `patch.dict(os.environ)` + `time.tzset()`, trả lại trong `addCleanup`) xanh.

- [ ] T24 — Phương thức `confirm_restart` — files: erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py, erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py — test: erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py — depends: T22, T23, T17
  - Criterion: AC-46 (c), AC-55 (§3.3, §5).
  - Receives: `restart_check.outcome`, `web_started`, `workers_started` (T23); `transitions.confirm_restart` (T17).
  - Returns (A-2.1): `@frappe.whitelist(methods=["POST"]) confirm_restart(name=None) -> {"name", "restart_status"}`; gọi `_decider(name)` **đầu tiên**, đúng hàm của `approve`/`reject`/`undo` (chỉ `ERP AI Instructor`, ngoài `NEVER_AUTHORITY`; `System Manager` không có `ERP AI Instructor` bị `PermissionError`; không có đề xuất thì `DoesNotExistError`, cũng từ `_decider`); không có luật quyền thứ hai; chỉ ghi khi `restart_status = Đã gửi` và `outcome` có kết luận (mốc đổi về epoch bằng hai hàm của T23); logger `erp_ai restart proposal=%s status=%s`.
  - Expect: `test_one` → `TestConfirmRestart::test_only_from_sent`, `test_no_conclusion_writes_nothing`, `test_agent_account_refused`, `test_administrator_guest_no_role_refused`, `test_system_manager_without_instructor_refused_status_unchanged` (stub `transitions.confirm_restart` 0 lần gọi), `test_instructor_records_conclusion`, `test_uses_decider` (`_decider` được gọi đúng 1 lần với `name` trước mọi lần đọc bằng chứng), `test_missing_proposal_does_not_exist` xanh.

- [ ] T25 — Form: nút Hoàn tác ở `Lỗi` có commit, câu xác nhận của khối, gọi `confirm_restart` — files: erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.js, erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py — test: erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py — depends: T24, T21
  - Criterion: AC-42, AC-46 (c), AC-48 (form) (§7 hàng `.js`).
  - Receives: `confirm_restart` (T24); `change_notes` trong `onload` (T20, T21).
  - Returns: nút Hoàn tác hiện khi `Đã áp dụng`, hoặc `Lỗi` có `apply_commit_sha` và `undo_commit_sha` rỗng, với `change_kind = Thay đổi code`; hộp xác nhận nêu số mục và "Lệnh trong khối không hoàn tác được"; khi `restart_status = Đã gửi` **và** `frappe.user.has_role("ERP AI Instructor")` (A-2.1, D-17) form gọi `confirm_restart` một lần lúc mở rồi tải lại nếu giá trị đổi; người chỉ có `System Manager` thì không có lời gọi, không hộp lỗi.
  - Expect: `test_one` → `TestChangeProposalFormScript::test_undo_button_shown_for_failed_with_commit`, `test_calls_confirm_restart_only_when_sent`, `test_confirm_restart_called_only_for_instructor`, `test_form_diff_covers_every_item` (trường `diff` chứa đoạn của mọi mục) xanh.

## Phần 2 — Tool đề xuất

- [ ] T26 — `_propose_block` thật cho mục sửa và tạo, kèm thư mục cha mới — files: erp_ai/agent/tools/propose_change.py, erp_ai/agent/tools/test_propose_change.py — test: erp_ai/agent/tools/test_propose_change.py — depends: T14, T2
  - Criterion: AC-36, AC-39, AC-44 (§3.1, §4.1 bước 1–4, §2.2 "Trường có sẵn dùng lại").
  - Receives: `change_guard.check_block(…, at_apply=False)` (T14); `source.text_refusal`, `source.TEXT_MAX_BYTES`; `_apply_edits`, `_diff`, `_insert`.
  - Returns (A-1.2, A-1.5): `_propose_block(changes, commands, reason, ctx)` chuẩn hóa `edit` và `create` thành `FileOp`; file của mục `edit` đọc tối đa `TEXT_MAX_BYTES + 1` byte rồi `text_refusal(rel, data)`; **bước 2b**: dựng `diff_text` gộp đúng một lần (từng mục bằng `_diff`, nối theo `idx`), gọi `check_block(…, at_apply=False, diff_text=diff_text)`, rồi `insert` **chính chuỗi đó** vào trường `diff` của bản ghi cha cùng dòng con; dạng gọi cũ `{path, find, replace}` hiểu là 1 mục `edit`; `propose_new_file` đi qua `_propose_block` (1 mục `create`, `content` rỗng được phép); hằng `BLOCK_SHAPE`; xóa `NO_PARENT`, `propose_change.PROPOSAL_FILE_MAX_BYTES` và `propose_change.TOO_LARGE` (câu quá cỡ nay là `source.TEXT_TOO_LARGE`); `NOT_UTF8` trỏ tới hằng `source.TEXT_*`.
  - Expect: `test_one` → `TestProposeBlock::test_file_over_two_mib_refused_names_2_mib` (0 đề xuất), `test_edit_and_create_block_one_proposal_rows_in_order`, `test_legacy_call_shape_is_one_edit_item`, `test_changes_and_path_together_refused`, `test_create_in_new_three_level_dir_ok`, `test_text_files_any_extension_created`, `test_binary_png_pyc_refused`, `test_create_with_nul_refused`, `test_pem_key_gitignore_refused`, `test_two_apps_refused_names_both_zero_proposals`, `test_refusal_makes_zero_proposals_zero_comments` xanh; test cũ ghim "thư mục cha phải có" sửa theo §8.3.

- [ ] T27 — Mục xóa và đổi tên trong tool — files: erp_ai/agent/tools/propose_change.py, erp_ai/agent/tools/test_propose_change.py — test: erp_ai/agent/tools/test_propose_change.py — depends: T26
  - Criterion: AC-36, AC-40, AC-41, AC-50 (§4.1 bước 2; R-7, R-8, D-8).
  - Receives: `change_guard.NOT_REGULAR_FILE`, `change_guard.EXECUTABLE_FILE` (T12); `_propose_block` cho `edit` và `create` (T26).
  - Returns: `_propose_block` nhận `delete` và `rename`: đọc byte của file Xóa và nguồn Đổi tên, `isfile` và không `islink` (sai thì `NOT_REGULAR_FILE`), `st_mode & 0o111` (có thì `EXECUTABLE_FILE`); đích đổi tên đã `lexists` thì `EXISTS`; `diff` của Xóa so với `/dev/null`, của Đổi tên là hai dòng `rename from` / `rename to`.
  - Expect: `test_one` → `TestProposeBlock::test_five_item_block_makes_one_pending_proposal_one_comment_three_links`, `test_ten_item_block`, `test_delete_directory_refused`, `test_delete_missing_refused`, `test_delete_dirty_refused`, `test_delete_untracked_refused`, `test_delete_binary_refused`, `test_delete_executable_refused`, `test_rename_dest_exists_refused`, `test_rename_source_missing_refused`, `test_rename_across_apps_refused`, `test_rename_end_in_ring_refused`, `test_nine_valid_plus_one_erp_ai_refused_whole` xanh.

- [ ] T28 — Lệnh trong khối; ba tool về một hàm — files: erp_ai/agent/tools/propose_change.py, erp_ai/agent/tools/test_propose_change.py — test: erp_ai/agent/tools/test_propose_change.py — depends: T27
  - Criterion: AC-36, AC-47, NFR-12 (§3.1 bảng tool, §2.2 `command_list`, `change_kind`, `app`).
  - Receives: `change_guard.build_bench_args`, `RESTART_COMMAND` (T11); luật restart của `check_block` (T14).
  - Returns: `commands` (mảng `{command, app?}`) dựng bằng `build_bench_args` rồi lưu `command_list` JSON đúng thứ tự; `propose_new_file` nhận `commands`; `propose_bench_command` đi qua `_propose_block([], [cmd], …)` cho ra đề xuất khối chỉ có lệnh (`change_kind = Lệnh bench`, `reversible = 0`, không có `branch` trong kết quả); enum `command` có `restart`.
  - Expect: `test_one` → `TestProposeBlock::test_py_block_with_migrate_restart_stored_in_order`, `test_py_block_without_restart_refused`, `test_command_only_block_has_no_branch`, `test_bench_command_restart_plain_ok`, `test_denied_command_refused_names_command`, `test_no_effect_before_approval_tree_head_process_restart_stubs_unchanged` (cây thư mục, HEAD, stub `run_bench`, stub `launch_restart` không đổi với đủ 4 loại mục) xanh.

- [ ] T29 — Schema tool: bỏ ba giới hạn cũ — files: erp_ai/agent/tools/propose_change.py, erp_ai/agent/tools/test_propose_change.py, erp_ai/constants.py, erp_ai/agent/tools/test_registry.py — test: erp_ai/agent/tools/test_propose_change.py — depends: T28
  - Criterion: AC-43 (ca 1, 2), AC-56 (tên tool không đổi) (§3.1 cột "Thay đổi", §2.5 "Xóa").
  - Returns: schema đúng bảng §3.1 (`changes` 1..50, `commands` 0..6, bỏ `maxItems`/`maxLength` của `find`/`replace`, `content` bỏ `minLength`/`maxLength`); `EDIT_SHAPE = "find và replace phải cùng số phần tử, ít nhất 1"`; xóa `PROPOSAL_TEXT_MAX_CHARS`, `REPLACE_MAX_ITEMS` khỏi `constants.py` và mọi nơi dùng; `PROPOSE_TOOL_NAMES` không đổi.
  - Expect: `test_one` → `TestProposeBlock::test_new_file_20001_chars_accepted`, `test_edit_with_11_replacements_accepted`, `test_schema_matches_design_table` xanh; `test_one` với `erp_ai/agent/tools/test_registry.py` xanh (ma trận AC-1, AC-2: ba tên tool như cũ); test cũ ghim 20 000 và 10 sửa theo §8.3.

- [ ] T30 — Comment đề xuất của khối — files: erp_ai/agent/tools/propose_change.py, erp_ai/agent/tools/test_propose_change.py — test: erp_ai/agent/tools/test_propose_change.py — depends: T29, T20
  - Criterion: AC-48 (§3.7 "Comment đề xuất trên phiếu").
  - Receives: `change_text.proposal_notes` dạng khối (T20).
  - Returns: `_comment` câu đầu `Đề xuất {tên} đang chờ duyệt: khối {n} mục trong app {app}.` hoặc `…: {m} lệnh bench.`, sau đó các dòng của `proposal_notes`, rồi ba liên kết như hôm nay; mọi giá trị qua `escape_html`.
  - Expect: `test_one` → `TestBlockComment::test_comment_counts_paths_delete_rename_lines_commands_restart_note`, `test_restart_line_iff_restart_listed`, `test_no_remote_url`, `test_command_only_first_sentence`, `test_fifty_items_all_paths_listed` xanh.

## Phần 3 — Comment kết quả

- [ ] T31 — Comment trước restart — files: erp_ai/agent/changes/result_comment.py, erp_ai/agent/changes/test_result_comment.py — test: erp_ai/agent/changes/test_result_comment.py — depends: T1
  - Criterion: AC-46 (b) (§3.7 "Comment trước restart").
  - Returns: `post_restart_notice(name, action) -> str | None` ghi 1 comment `Info` đúng chữ §3.7 (sha 12 ký tự trong câu đầu, sha đủ trong lệnh `git -C apps/{app} revert --no-edit {sha}`); `action = "undo"` dùng `undo_commit_sha` và chữ "hoàn tác"; lỗi ghi comment thì `log_error` như `post_result`, không ném.
  - Expect: `test_one` → `TestRestartNotice::test_apply_notice_text_commit_branch_recovery`, `test_undo_notice_uses_undo_commit`, `test_no_remote_url_or_token` xanh.

- [ ] T32 — Comment kết quả của khối — files: erp_ai/agent/changes/result_comment.py, erp_ai/agent/changes/test_result_comment.py — test: erp_ai/agent/changes/test_result_comment.py — depends: T31, T15, T2
  - Criterion: AC-45 (R-2), AC-49 (§3.7 "Comment kết quả").
  - Receives: trường `command_results`, `restart_status` (T15); `block.operations_of`, `block.commands_of`; `make_block_proposal` (T2).
  - Returns: `result_lines` cho dạng khối: 6 nhóm dòng đúng thứ tự và chữ §3.7 (từng mục `đã áp dụng` hoặc `chưa áp dụng`; `commit {sha12}`; từng lệnh `mã thoát {x}` hoặc `quá thời gian`; `restart: {đã gửi | lỗi khởi chạy | không cần}`; `việc người còn phải làm: …` với bốn gợi ý hoặc `không`); `RESULT_FIELDS` không thêm nội dung file hay đầu ra lệnh; dạng cũ giữ chữ cũ.
  - Expect: `test_one` → `TestBlockResult::test_one_result_comment_per_outcome_with_items_commit_exit_codes_restart_todo`, `test_command_timeout_names_command_keeps_files_no_restart`, `test_build_and_migrate_todo_hints`, `test_unconfirmed_label_says_permission_may_be_missing_and_todo_restart`, `test_seeded_token_zero`, `test_legacy_result_text_unchanged` xanh.

## Phần 4 — Job áp dụng và hoàn tác

- [ ] T33 — Job: kiểm lại khối trước khi ghi, một đường cho cả hai dạng — files: erp_ai/agent/changes/apply_job.py, erp_ai/agent/changes/test_apply_block.py, erp_ai/agent/changes/test_apply_job.py — test: erp_ai/agent/changes/test_apply_block.py — depends: T7, T14, T18, T22, T2
  - Criterion: AC-37, AC-46 (a lúc áp dụng), AC-47 (§4.2 bước 1–3).
  - Receives: `block.operations_of`, `commands_of`, `is_block` (T18); `check_block(…, at_apply=True, diff_text=cstr(doc.diff), legacy=not is_block)` (T14; A-1.5); `change_text.apply_message(…, operations=)` (T19); `make_block_proposal` (T2).
  - Returns: `_recheck` chạy trên kết quả bộ chuyển đổi cho cả dạng cũ và dạng khối; từng dòng kiểm `sha256(content_after) == after_hash` và `sha256(content_before) == base_hash` (`STORED_HASH_MISMATCH`); bản xem trước commit khớp `commit_message`; lý do có tiền tố mục hoặc lệnh; bỏ nhánh `_apply_block` giả của T1.
  - Expect: `test_one` → `TestBlockAllOrNothing::test_guard_fails_at_apply_error_names_item`, `test_app_removed_from_list_error`, `test_syntax_broken_at_apply_error`, `TestApplyBlock::test_stored_command_edited_to_denied_blocked_at_apply`, `test_stored_hash_mismatch_refused`, `TestLegacyThroughAdapter::test_legacy_approved_proposal_applies` xanh, mỗi ca 0 byte ghi và 0 commit; `test_one` với `test_apply_job.py` xanh.

- [ ] T34 — Job: so đĩa và git trước khi ghi — files: erp_ai/agent/changes/apply_job.py, erp_ai/agent/changes/test_apply_block.py — test: erp_ai/agent/changes/test_apply_block.py — depends: T33
  - Criterion: AC-37, AC-40 (§4.2 bước 4–5).
  - Receives: `file_writer.sha256_of`; `source.read_git_state(full_path, *, new_file, limit_s)`.
  - Returns: mọi dòng được so trước khi ghi bất kỳ byte nào (Sửa, Xóa, nguồn Đổi tên: hash = `base_hash`; Tạo, đích Đổi tên: chưa `lexists`); sai thì `Hết hiệu lực` với `mục n (path): file đích đã đổi kể từ lúc đề xuất`; `read_git_state` từng đường dẫn, từ chối thì `Lỗi` kèm mục, nhánh khác `target_branch` thì `Hết hiệu lực`; nhớ `old_head`.
  - Expect: `test_one` → `TestBlockAllOrNothing::test_stale_target_first_middle_last_zero_written`, `test_branch_changed_stale`, `test_create_target_appeared_stale`, `TestDelete::test_changed_since_proposal_stale_zero_deleted` xanh.

- [ ] T35 — Job: ghi theo thứ tự bốn loại mục, trả lại ngược khi lỗi — files: erp_ai/agent/changes/apply_job.py, erp_ai/agent/changes/test_apply_block.py — test: erp_ai/agent/changes/test_apply_block.py — depends: T34
  - Criterion: AC-37, AC-39, AC-40, AC-41, NFR-13 (§4.2 bước 6).
  - Receives: `file_writer.write_atomic`, `make_parents`, `remove_file`, `remove_empty_dirs` (T5, T6); `process_runner.git_add_new`, `git_unstage_new`.
  - Returns: ghi theo `idx` đúng bảng §4.2 bước 6; nhật ký trả lại trong bộ nhớ; lỗi ở mục k, hash đọc lại sai, hoặc `git add` lỗi thì trả lại theo thứ tự ngược (ghi lại `before`, gỡ file đã tạo, tạo lại file đã xóa, trả đổi tên, `git_unstage_new`, `remove_empty_dirs`); kết quả `Lỗi` với `ghi mục k (path) lỗi, đã trả mọi file về như trước`; trả lại không trọn thì `GIT_RESTORE_FAILED`.
  - Expect: `test_one` → `TestBlockAllOrNothing::test_writer_fails_at_item_3_of_5_restores_bytes_dirs_zero_commit`, `test_writer_fails_at_first_and_last_item`, `test_rename_into_new_dir_fails_after_add_restores_index_and_dirs`, `test_restore_incomplete_reports_restore_failed`, `TestDelete::test_parent_swapped_to_symlink_after_check_zero_deleted_outside` (A-3.3: bọc `change_guard.check_block` thật, sau khi nó trả về thì đổi thư mục cha của mục Xóa thành symlink ra ngoài app → `Lỗi`, 0 commit, file ngoài app còn nguyên, các mục trước trả lại trùng từng byte) xanh (cây thư mục, HEAD và index trùng trước và sau).

- [ ] T36 — Job: một commit cho cả khối, hậu kiểm, ghi commit vào đề xuất — files: erp_ai/agent/changes/apply_job.py, erp_ai/agent/changes/test_apply_block.py, erp_ai/agent/changes/test_apply_job.py — test: erp_ai/agent/changes/test_apply_block.py — depends: T35, T15
  - Criterion: AC-36, AC-37, AC-38, AC-39, AC-40, AC-41 (§4.2 bước 7–8, §6 "Quan sát").
  - Receives: `git_commit_only(repo, rels, …)` (T7); `transitions.record_commit` (T15); `source.git_commit_summary`, `git_blob`, `git_is_ancestor`.
  - Returns: một `git_commit_only` với mọi đường dẫn của khối kể cả nguồn và đích đổi tên; `_postcheck` tổng quát (1 parent, `old_head` là tổ tiên, `set(summary.paths) == set(paths)`, nhánh đúng, từng blob đúng byte hoặc `None`); `record_commit(Đang áp dụng, fields={apply_commit_sha, applied_branch, applied_ahead_count, created_dirs})` rồi commit DB; nhật ký bước mang `value_before = {"head", "files": {rel: sha256}}`, `value_after = {"commit", "branch", "files": {rel: sha256|null}}`. `test_apply_job.py`: chỉ sửa giá trị nhật ký một-file (§8.3).
  - Expect: `test_one` → `TestApplyBlock::test_one_approval_applies_whole_block_decision_calls_1`, `TestBlockCommit::test_commit_holds_exactly_block_paths_with_rename_both_ends`, `test_other_staged_and_unstaged_files_untouched_refs_unchanged`, `test_postcheck_extra_path_is_mismatch`, `test_blob_bytes_equal_approved`, `test_crash_after_commit_keeps_sha_and_files`, `TestBlockAllOrNothing::test_commit_fails_restores_all_head_and_index_unchanged`, `test_commit_timeout_restores_all`, `test_one_log_row_per_outcome`, `TestNewDirs::test_create_three_level_tree_matches_proposal`, `TestDelete::test_delete_removes_file_commit_records_deletion`, `TestRename::test_rename_keeps_bytes` xanh.

- [ ] T37 — Job: chạy lệnh của khối theo thứ tự — files: erp_ai/agent/changes/apply_job.py, erp_ai/agent/changes/test_apply_block.py — test: erp_ai/agent/changes/test_apply_block.py — depends: T36
  - Criterion: AC-49, AC-54 (§4.2 bước 9–10, 12).
  - Receives: `process_runner.run_bench(args, limit_s)`; `transitions.finish(…, command_results=)` (T15).
  - Returns: lệnh chạy đúng thứ tự đã lưu, trừ `restart` ở cuối; còn dưới 1 s thì không chạy và ghi `quá thời gian`; lệnh j lỗi hoặc quá giờ thì dừng, `Lỗi` với `lệnh j (bench …): lệnh trả mã x` hoặc `quá thời gian`, giữ sha và file, 0 restart; `exit_code`, `duration_ms`, `command_output` là của lệnh cuối đã chạy; dòng logger thêm `ops=<n> commands=<m> restart=<giá trị>`. Dev ghi số đo `bench build --app frappe` và `--app helpdesk` trên `miyano` vào báo cáo (không chạy trong test).
  - Expect: `test_one` → `TestBlockCommands::test_commands_run_in_stored_order_results_recorded`, `test_command_2_fails_stops_keeps_commit_status_failed_undoable`, `test_command_timeout_names_command_no_restart`, `test_less_than_one_second_left_not_run`, `TestOneApproval::test_commands_run_equal_commands_shown` xanh (stub `run_bench`).

- [ ] T38 — Job: restart là bước cuối, đúng một lần — files: erp_ai/agent/changes/apply_job.py, erp_ai/agent/changes/test_apply_block.py — test: erp_ai/agent/changes/test_apply_block.py — depends: T37, T8, T17, T32
  - Criterion: AC-45, AC-46 (b), AC-49 (§4.4 bước 1–4, §4.5).
  - Receives: `result_comment.post_restart_notice` (T31), `post_result` dạng khối (T32); `process_runner.launch_restart` (T8); `transitions.record_restart` (T17).
  - Returns: sau `finish(→ Đã áp dụng)` và commit DB, nếu danh sách có `restart`: `post_restart_notice` → commit DB → `sent_at = now_datetime()` → `launch_restart()` → `record_restart(expected, "Đã gửi" | "Lỗi khởi chạy", sent_at)` → commit DB; lỗi khởi chạy thêm `frappe.log_error(TITLE_CHANGE_FAILED, "proposal=… action=restart error=<lớp>")`; `change_status` không đổi; job không chờ; đúng 1 comment kết quả đến sau comment trước restart.
  - Expect: `test_one` → `TestRestart::test_py_block_launches_once_after_applied_committed`, `test_no_py_block_zero_launch`, `test_refused_stale_failed_command_timeout_zero_launch`, `test_launch_failure_records_launch_failed_status_unchanged`, `test_notice_comment_exists_before_launch_stub_called`, `test_syntax_rechecked_at_apply_zero_written`, `test_exactly_one_result_comment_after_notice` xanh (stub `launch_restart`).

- [ ] T39 — Job: hoàn tác phần file của khối bằng một commit — files: erp_ai/agent/changes/apply_job.py, erp_ai/agent/changes/test_apply_block.py — test: erp_ai/agent/changes/test_apply_block.py — depends: T38
  - Criterion: AC-39, AC-40, AC-41, AC-42, NFR-13 (§4.3 bước 1–4; D-10).
  - Receives: `created_dirs` đã lưu (T36); `transitions.record_commit` (T15); `change_text.undo_message(…, operations=)` (T19).
  - Returns: `_recheck` của hoàn tác gọi `check_block(…, at_apply=True, diff_text=cstr(doc.diff))` (A-1.5) với `allowed_apps=(proposal.app,)` cho đường dẫn và `settings.allowed_apps ∪ {app}` cho lệnh, bỏ kiểm cú pháp; kiểm hết rồi mới ghi (hash = `after_hash`; file Xóa và nguồn Đổi tên vắng mặt; `read_git_state`; `apply_commit_sha` là tổ tiên của HEAD); ghi ngược theo bảng §4.3 bước 3; `remove_empty_dirs(created_dirs)`; một commit hoàn tác, hậu kiểm với blob đảo ngược; `record_commit(Đang hoàn tác, {undo_commit_sha})`; lỗi giữa chừng trả về trạng thái đã áp dụng.
  - Expect: `test_one` → `TestUndoBlock::test_undo_five_item_block_one_commit_bytes_and_tree_equal`, `test_any_path_changed_after_apply_refused_zero_written`, `test_apply_commit_not_ancestor_refused`, `test_git_precheck_refusal`, `test_undo_write_fails_midway_restores_applied_state`, `TestNewDirs::test_undo_removes_created_empty_dirs_keeps_preexisting_and_nonempty`, `TestDelete::test_undo_restores_bytes`, `TestRename::test_undo_restores_source_removes_dest_and_dirs` xanh.

- [ ] T40 — Job: hoàn tác chạy lại lệnh và restart; hoàn tác từ `Lỗi`; đề xuất dạng cũ — files: erp_ai/agent/changes/apply_job.py, erp_ai/agent/changes/test_apply_block.py, erp_ai/agent/changes/test_block.py — test: erp_ai/agent/changes/test_apply_block.py — depends: T39
  - Criterion: AC-42, AC-45 (A-39) (§4.3 bước 5–7).
  - Receives: bước lệnh (T37), bước restart (T38) dùng lại với `expected = Đã hoàn tác`; `transitions.request_undo` cạnh `Lỗi` (T16).
  - Returns: sau commit hoàn tác chạy lại `command_list` cùng thứ tự, `finish(Đang hoàn tác → Đã hoàn tác)`, rồi restart nếu có; hoàn tác bị từ chối ở bước kiểm thì `Lỗi` với lý do mới và giữ `apply_commit_sha`; đề xuất dạng cũ hoàn tác qua cùng đường, không lệnh, không restart.
  - Expect: `test_one` → `TestUndoBlock::test_undo_with_py_reruns_commands_and_restarts_once`, `test_undo_from_failed_with_commit_allowed`, `test_refused_undo_keeps_apply_sha_retry_possible` xanh; `test_one` với `erp_ai/agent/changes/test_block.py` → `TestLegacyUndo::test_legacy_applied_proposal_undoes` xanh.

## Phần 5 — Test nghiệm thu theo AC

- [ ] T41 — Test nghiệm thu: ba giới hạn cũ không còn chặn; trần mới ở hai thời điểm — files: erp_ai/agent/changes/test_apply_block.py — test: erp_ai/agent/changes/test_apply_block.py — depends: T40, T29
  - Criterion: AC-43 (ca 1, 2 và trần; §8.1 hàng AC-43). Test nghiệm thu.
  - Receives: tool `propose_file_change`, `propose_new_file` (T29); job áp dụng và hoàn tác (T40).
  - Returns (A-1.8): lớp `TestLimits`; `test_form_load_at_ceiling_measured` in kích thước JSON của `frappe.get_doc(...).as_dict()` và thời gian tải cho khối ở đúng trần `CHANGE_MAX_TOTAL_BYTES` (kể cả `diff`) để dán vào `acceptance.md`; lớp `TestPacketBudget` (ngân sách gói SQL, qua `propose_file_change` thật trên site test, đọc lại bằng `frappe.get_doc` trùng từng byte ở mọi dòng con và `diff`).
  - Expect: `test_one` → `TestLimits::test_new_file_20001_chars_applies_and_undoes`, `test_edit_with_11_replacements`, `test_block_over_total_bytes_refused_at_apply_names_limit` (lý do chứa `(kể cả diff)` và `8 MiB`), `test_form_load_at_ceiling_measured`, `TestPacketBudget::test_ceiling_block_all_empty_lines_inserts_and_reads_back` (test tự assert `total == CHANGE_MAX_TOTAL_BYTES`), `test_ceiling_block_all_quote_lines_inserts_and_reads_back`, `test_child_row_two_full_files_of_quotes_inserts_and_reads_back` xanh.

- [ ] T42 — Test nghiệm thu: một đề xuất một lần duyệt; bot không tự duyệt — files: erp_ai/agent/changes/test_apply_block.py — test: erp_ai/agent/changes/test_apply_block.py — depends: T41, T24
  - Criterion: AC-54, AC-55 (§8.1). Test nghiệm thu.
  - Receives: `approve`, `reject`, `undo`, `confirm_restart`; `change_link.decision_path`; `FakeGateway`.
  - Returns: lớp `TestOneApproval`, `TestNoSelfApproval`.
  - Expect: `test_one` → `TestOneApproval::test_two_proposals_same_file_each_needs_own_approval`, `test_row_edited_in_db_after_approval_refused_file_unchanged`, `TestNoSelfApproval::test_agent_admin_guest_no_role_refused_both_paths_block`, `test_model_claims_approved_zero_applied_zero_restart` xanh.

- [ ] T43 — Test nghiệm thu: không lọt khóa; git an toàn sau áp dụng và hoàn tác — files: erp_ai/agent/changes/test_apply_block.py — test: erp_ai/agent/changes/test_apply_block.py — depends: T42
  - Criterion: AC-51, AC-52 (§8.1). Test nghiệm thu.
  - Returns: lớp `TestNoKeyLeakBlock`, `TestGitSafety`.
  - Expect: `test_one` → `TestNoKeyLeakBlock::test_seeded_key_zero_in_proposal_comment_log_output`, `TestGitSafety::test_remote_refs_branch_unchanged_zero_hooks_after_apply_and_undo` xanh.

- [ ] T44 — Ma trận vành đai: vành `erp_ai` và vành bí mật, cấu hình site — files: erp_ai/agent/changes/test_block_boundary.py — test: erp_ai/agent/changes/test_block_boundary.py — depends: T40, T30
  - Criterion: AC-50, AC-51 (§8.4 hàng A, B). Test nghiệm thu.
  - Receives: `TempAppsRoot`, `GitSandbox`, `make_block_proposal`, `RealCoreReposUntouchedMixin` (T2); `propose_file_change`; `run_change`.
  - Returns: lớp `TestRingMatrix` với bộ dựng gốc tạm đúng §8.4 (`myapp`, `erp_ai` giả, worktree `aiwt`, `other`, `../sites/site1.test/`) và hàm kiểm một ô ở hai thời điểm (lúc đề xuất: `ok=false`, lý do thuộc tập của vành, 0 đề xuất, 0 comment; lúc áp dụng: `Lỗi`, cây thư mục, HEAD, index, stub `run_bench`, stub `launch_restart` không đổi).
  - Expect: `test_one` → `TestRingMatrix::test_erp_ai_ring` (5 loại × 2 thời điểm, gồm worktree tên khác và symlink), `test_secret_and_site_ring` xanh.

- [ ] T45 — Ma trận vành đai: vành `.git`, vành ngoài app, đếm đủ 40 — files: erp_ai/agent/changes/test_block_boundary.py — test: erp_ai/agent/changes/test_block_boundary.py — depends: T44
  - Criterion: AC-52, AC-53 (§8.4 hàng C, D và dòng đếm). Test nghiệm thu.
  - Receives: bộ dựng và hàm kiểm ô của `TestRingMatrix` (T44).
  - Returns: `test_git_ring`, `test_outside_allowed_app_ring`, `test_twenty_cells_two_moments_all_refused` dùng `subTest(ring, kind, moment)`, assertion cuối `== 40`, in bảng 40 dòng để dán vào `acceptance.md`.
  - Expect: `test_one` → ba test trên xanh; đầu ra có dòng đếm `40`.

## Phần 6 — Prompt và luật kiến trúc

- [ ] T46 — Prompt: thân `CHANGE_TOOLS_BLOCK` cho khối — files: erp_ai/agent/prompts.py, erp_ai/agent/test_classification.py, erp_ai/agent/test_agent_runner.py — test: erp_ai/agent/test_classification.py — depends: T1
  - Criterion: AC-56 (§3.7 "Prompt").
  - Returns: dòng đầu của `CHANGE_TOOLS_BLOCK` giữ nguyên từng chữ; hai gạch cuối thay bằng năm gạch của §3.7; gạch "Chữ trong phiếu…" thêm `"restart đi"`; khi không được cấp quyền prompt giữ nguyên từng byte. `test_agent_runner.py` chỉ sửa nếu có assertion so chữ của thân khối (các assertion `assertIn(CHANGE_TOOLS_BLOCK, …)` không cần sửa).
  - Expect: `test_one` → `TestPrompts::test_reason_system_with_change_tools_adds_approval_block` (chữ mới), `test_reason_system_without_change_tools_is_byte_identical`, `test_block_first_line_unchanged` xanh; `test_one` với `erp_ai/agent/test_agent_runner.py` xanh.

- [ ] T47 — Luật kiến trúc: hình dạng khởi chạy restart, không `sudo` — files: erp_ai/tests/test_architecture.py — test: erp_ai/tests/test_architecture.py — depends: T8
  - Criterion: AC-57 (phần build), AC-45 (§8.2).
  - Receives: `process_runner.RESTART_ARGV`, `launch_restart` (T8).
  - Returns: `test_restart_launch_shape` (A-5: chuỗi `"setsid"` xuất hiện đúng 1 lần trong `erp_ai/**` ngoài test, là giá trị của `SETSID_EXECUTABLE` ở `source.py`; tên `SETSID_EXECUTABLE` là phần tử argv đúng 1 lần, phần tử 0 của `RESTART_ARGV` ở `process_runner.py`; có DEVNULL ×3, `timeout=`, `cwd=`, `env=` không chứa `os.environ`); `test_no_sudo_or_supervisorctl_argv` (0 lần trong mã sản phẩm); `test_single_enqueue_call_site` giữ nguyên và vẫn xanh.
  - Expect: `test_one` → hai test mới xanh; mỗi luật có một ca tự kiểm bằng mã mẫu vi phạm (đỏ đúng lý do).

- [ ] T48 — Luật kiến trúc: thao tác hệ tệp chỉ ở `file_writer`, danh sách lệnh bench — files: erp_ai/tests/test_architecture.py — test: erp_ai/tests/test_architecture.py — depends: T47, T11, T6
  - Criterion: AC-47, AC-52 (§8.2).
  - Returns: `test_fs_writes_only_in_file_writer` phủ thêm `os.mkdir`, `os.makedirs`, `os.rmdir`, `os.rename`, `os.replace`, `os.remove`, `os.unlink`; `test_bench_allowlist_has_no_git_running_subcommands` mở rộng: `BENCH_COMMANDS` có `restart` và không có lệnh nào của ADR-040 QĐ 6 hay ADR-022 QĐ 2.
  - Expect: `test_one` → hai test trên xanh; ca mẫu vi phạm `os.mkdir` ngoài `file_writer` bị bắt.

- [ ] T49 — Luật kiến trúc: một luật văn bản, giới hạn định nghĩa một lần; xóa `DUOI_CHO_PHEP` — files: erp_ai/tests/test_architecture.py, erp_ai/agent/tools/source.py, erp_ai/agent/tools/test_source.py — test: erp_ai/tests/test_architecture.py — depends: T48, T9, T29
  - Criterion: AC-43, AC-44 (§8.2; ADR-040 QĐ 5).
  - Thêm theo A-1.8, A-8.2: xóa `source.SEARCH_FILE_MAX_BYTES` (sau T6 và T26 không còn người dùng; còn thì báo `NEEDS_CONTEXT`); `test_change_file_max_bytes_defined_once_compared_only_in_text_refusal` (AST: `CHANGE_FILE_MAX_BYTES = <số>` đúng 1 lần ở `constants.py`; phép gán khác chỉ là `TEXT_MAX_BYTES = CHANGE_FILE_MAX_BYTES` ở `source.py`; mọi phép so `<`, `<=`, `>`, `>=` có `TEXT_MAX_BYTES` hoặc `CHANGE_FILE_MAX_BYTES` chỉ nằm trong `text_refusal`); `test_search_file_max_bytes_gone` (tên xuất hiện 0 lần trong `erp_ai/**`); `test_change_limits_defined_once` gồm cả `CHANGE_FILE_MAX_BYTES`.
  - Returns: xóa hằng `DUOI_CHO_PHEP` khỏi `source.py` (và import của nó trong `test_source.py` nếu có); `test_single_text_rule_no_extension_list` (tên `DUOI_CHO_PHEP` xuất hiện 0 lần; chỉ `source.text_refusal` giải mã UTF-8 chặt và so `TEXT_MAX_BYTES` cho nội dung file); `test_change_limits_defined_once` (`CHANGE_MAX_FILE_OPS`, `CHANGE_MAX_TOTAL_BYTES`, `CHANGE_MAX_COMMANDS`, `RESTART_*` chỉ gán ở `constants.py`; `TEXT_MAX_BYTES` chỉ gán ở `source.py`; số 20000 và `1024 * 1024` không xuất hiện ở `propose_change.py`, `change_guard.py`, `file_writer.py`).
  - Expect: `test_one` → hai test mới xanh; `test_one` với `erp_ai/agent/tools/test_source.py` xanh.

- [ ] T50 — Test nghiệm thu: trần mỗi file theo phán quyết C-1 — files: erp_ai/agent/changes/test_apply_block.py — test: erp_ai/agent/changes/test_apply_block.py — depends: T49, T43
  - Điều kiện bắt đầu đã đủ (2026-11-15): ADR-040 có "Phán quyết C-1" (`CHANGE_FILE_MAX_BYTES` = 2 MiB) và `design-addendum-1.md` A-1 đã nhận. Hằng do T1 tạo ở `constants.py`, `source.TEXT_MAX_BYTES` nhập lại ở T3; task này chỉ còn test nghiệm thu, nên `source.py` và `constants.py` rời khỏi touchpoint.
  - Criterion: AC-43 ca 3 (file nguồn 1 MiB + 1 byte qua; vượt 2 MiB thì từ chối nêu `2 MiB`) (A-1.8). Test nghiệm thu.
  - Receives: `CHANGE_FILE_MAX_BYTES` (T1), `source.TEXT_TOO_LARGE` (T3); tool và job (T29, T40); `make_block_proposal` (T2).
  - Returns: thêm vào lớp `TestLimits` hai test dưới đây.
  - Expect: `test_one` → `TestLimits::test_source_file_one_mib_plus_one` (tạo, áp dụng, hoàn tác đúng từng byte), `test_file_over_two_mib_refused_at_apply_names_2_mib` (đề xuất dựng thẳng có `after` = `CHANGE_FILE_MAX_BYTES + 1` byte → `Lỗi`, lý do chứa `2 MiB`, 0 byte ghi) xanh.

## Checkpoint cuối (tech-lead, không giao dev)

- [ ] T51 — Checkpoint: `cmd.test` cả app trong một lần giữ khóa site, `cmd.lint`, `cmd.migrate` lên/xuống/lên, `diff.patch` — files: docs/team/features/CHG-002/diff.patch, docs/team/features/CHG-002/tasks.md — test: `cmd.test` (cả app) — depends: T0..T50
  - Criterion: mọi AC-36..AC-57 phần build, NFR-12..NFR-14; design §6 (Lên, Xuống, Đối soát, Thành công); STD-CI-2.
  - Receives: mọi `review-NN.md` là approve; không dev nào còn chạy test; không còn worktree dev hay nhánh task.
  - Returns: đầu ra thật, dán vào dòng progress: (1) trong MỘT lần giữ `.team/miyano-site.lock`: đối soát trước (số `ERP AI Change Proposal`, `content_digest` của mọi đề xuất có `approved_digest`), `cmd.migrate` lên → xuống (design §6 "Xuống") → lên, `count(tabERP AI Change Operation) = 0` sau khi lên, `cmd.test` cả app, đối soát sau; (2) `cmd.lint`; (3) `git -C apps/<app> rev-parse HEAD` và `status --porcelain` của `frappe`, `erpnext`, `helpdesk`, `hrms`, `erp_ai` trước = sau (NFR-14); (4) `git diff --stat develop...team/CHG-002` không có file nào thuộc danh sách "Không đụng" của `plan.md`, 0 dấu skip thêm vào; (5) dòng đếm `40` của ma trận AC-53 và số đo của `TestLimits::test_form_load_at_ceiling_measured`; (6) `diff.patch` = `git diff develop...team/CHG-002`; `.team/active-build-CHG-002` đã xóa.
  - Lưu ý chiều "xuống": journal FEAT-004 (T34) ghi `bench migrate` của Frappe 15 xóa DocType mồ côi (`remove_orphan_doctypes`), trái câu "Frappe không xóa bảng thừa" của design §6. Trước khi chạy chiều xuống, tech-lead xác nhận nó chỉ chạm DocType con mới (0 dòng theo đối soát); khác thế thì dừng và báo team-leader, không tự đổi cách làm.
  - Expect: tất cả xanh (không test đỏ nào ngoài dòng `baseline:`); lệch thì không tick, đi tìm nguyên nhân.
