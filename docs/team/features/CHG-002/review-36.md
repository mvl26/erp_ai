Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 36 — CHG-002 T36

- Diff: `git diff 2554f7d..1b5d4d4` trên `team/CHG-002-task-36` (vòng 1; 3 file, +711/−53; commit của task: `9c6252a`, `adec759`, `351014b`, `1b5d4d4`; `2554f7d` = merge `team/CHG-002` vào nhánh task xếp chồng trên T34, T35); sửa vòng 1: `git diff c6e9e4a..f710615` (2 file, +91/−8; `c6e9e4a` = merge `team/CHG-002` @ `c44bf86`)
- Vòng: 2 (max_rework = 3)
- Verdict: **approve** ở vòng 2 → merge `a56785d`, tick

Nhánh có hai commit `wip` (`9c6252a`, `351014b`): diff dở của hai lần gọi dev bị cắt (máy khởi động lại 17:38; một dev hết 60 lượt), tech-lead commit nguyên vẹn để dev sau làm tiếp. Reviewer chấm trạng thái cuối.

## Vòng 1 — request-changes (`git diff 2554f7d..1b5d4d4`)

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-ERR-1, STD-TEST-8 | `apply_job.py` `_commit_block`, dòng `summary = _commit_landed(repo, old_head, lambda _head: given_back(...))` | `_commit_landed` truyền `head_now` khi HEAD đã sang commit của người; lambda của khối bỏ nó; `_give_back_block` so `git_head == old_head` nên job kết `GIT_RESTORE_FAILED` dù mọi file đã trả lại; đường một-file truyền `head` làm `expected_head`; §4.2 bước 7 ghi "Các bước sau giống hôm nay"; không test khối nào phủ | thêm tham số `expected_head` (mặc định `old_head`) cho `_give_back_block` và closure `give_back`, truyền `head`; thêm test stub `git_commit_only` tạo commit của người rồi trả mã 128 |
| major | STD-TEST-8, STD-TEST-5 | `apply_job.py` `_commit_block` (`frappe.db.commit()` sau `transitions.record_commit`), `test_apply_block.py:166-168` | `setUp` vá `frappe.db.commit` thành rỗng, không test nào đọc lời gọi; xóa hoặc dời lệnh commit vẫn xanh (Returns "`record_commit(...)` rồi commit DB") | test ghi trạng thái đã lưu ở từng lần `frappe.db.commit` và kiểm trước `transitions.finish` |
| major | STD-TEST-8 | `apply_job.py` `_commit_block` `except Exception` → `_give_back_after_crash(...)` | không test khối nào ném lỗi giữa `_write_block` và `git_commit_only`; bỏ phần trả lại sau lỗi vẫn xanh | test cho `git_commit_only` ném lỗi, kỳ vọng `Lỗi` kèm tên lớp, `tree()` như trước, 0 commit |

minor | — | — | 3 điểm nhỏ: `test_apply_job.py:1704` tên `test_undo_row_carries_sha256_head_commit_branch` đã lệch nội dung (STD-NAME-2); `wip(apply)` không phải kiểu commit quy ước (STD-GIT-1); thân `1b5d4d4` không nêu việc bỏ `_head` | tùy dev

Tầng 1 ở vòng 1: đủ 14 test Expect (12 của task, 2 của "Sửa kế hoạch" và A8-3); một `git_commit_only` với mọi đường dẫn kể cả hai đầu đổi tên; `_postcheck` tổng quát; các trường của `record_commit`; hình dạng nhật ký §6; `test_apply_job.py` chỉ đổi giá trị nhật ký một-file. 8 dòng `test-shape:` khớp 8 chỗ đổi, 1 dòng `test-input:` khớp (L-1: 8, L-2: 1).

Phán về ba điểm dev nêu: (1) giữ `OP_UNKNOWN` chỉ cho khối có lệnh: nhận, là ranh giới đóng-khi-lỗi tới T37; T37 gỡ nhánh `elif block.commands_of(proposal) or not check.targets`. (2) lấy head trước từ `state.head`: nhận, cùng giá trị ở cả hai nơi gọi. (3) `read_git_state(check.targets[0]…)` sau commit khi mục 1 là xóa: không phải lỗi; `TestDelete::test_delete_removes_file_commit_records_deletion` và `TestRename::test_rename_keeps_bytes` là khối một mục đi qua `_commit_block` và kết `Đã áp dụng`.

## Vòng 2 — approve (`git diff c6e9e4a..f710615`)

1. ADDRESSED | `apply_job.py:372` `give_back(expected_head: str = old_head)`, `:436` `given_back(reason, expected_head)`, `:450-452` lambda truyền `head`, `:548` so `git_head == expected_head`; test `test_apply_block.py:1410` `test_commit_fails_after_a_person_committed_restores_all_keeps_their_commit`.
2. ADDRESSED | test `test_apply_block.py:1457` `test_git_fields_committed_to_db_before_done`: lần `frappe.db.commit` ngay trước `finish` đã có `apply_commit_sha`, `applied_branch`, `created_dirs` với `Đang áp dụng`.
3. ADDRESSED | test `test_apply_block.py:1444` `test_crash_before_commit_restores_all_zero_commit`.

Lỗi mới trong các dòng đổi: không.

Bằng chứng của dev. Lần gọi đầu, RED bằng đột biến trong `apply_job.py` (đã trả lại): M1 bỏ nguồn đổi tên khỏi commit `FAILED (failures=10)` gồm `test_commit_holds_exactly_block_paths_with_rename_both_ends`; M2 `set(summary.paths) == set(blobs)` thành phép con `FAIL: test_postcheck_extra_path_is_mismatch`: `('Đã áp dụng', None) != ('Lỗi', 'commit không đúng nội dung đã duyệt, cần người kiểm')`; M6 `FAIL: test_crash_after_commit_keeps_sha_and_files`: `None != 'cbe9af74...'`; GREEN `test_apply_block` `Ran 46 tests in 51.615s` / `OK`, `test_apply_job` `Ran 117 tests in 136.398s` / `OK`, `test_block` `Ran 10 tests in 0.029s` / `OK`, `test_architecture` `Ran 195 tests in 16.069s` / `OK`. Sửa vòng 1: RED (1) `('Lỗi', '…lỗi và không trả lại được trạng thái kho…', None) != ('Lỗi', 'commit git lỗi, đã trả file về như trước: fatal: không commit được', None)`; (2) xóa dòng commit DB: `('Đang áp dụng', None, None, None) != ('Đang áp dụng', '72e1c0dd…', …)`; (3) bỏ `_give_back_after_crash`: cây còn `fresh/`, `fresh/deep`, `moved/`; GREEN `test_apply_block` `Ran 50` / `OK`, `test_apply_job` `Ran 117` / `OK`, `test_block` `Ran 10` / `OK`, `test_architecture` `Ran 195` / `OK`.

## Review checklist (10)
1 đạt (vòng 1 thiếu hai phần, đã sửa) · 2 đạt · 3 đạt · 4 đạt · 5 đạt (vòng 1 trượt STD-ERR-1, đã sửa) · 6 đạt · 7 đạt · 8 đạt (1 minor) · 9 đạt · 10 đạt (1 minor về `wip`).

## Không kiểm được từ diff (tech-lead đã xử lý)

- Cả app, đợt merge 18, `team/CHG-002` @ `238544c` (20:13–20:25, `cmd.migrate` thoát 0): `Ran 1885 tests in 680.363s` / `FAILED (failures=6)`, đúng 6 test của dòng `baseline:`. Lần chạy này phủ cả phần merge `c6e9e4a` mà reviewer không soát lại.
- `transitions.record_commit` lưu `created_dirs` thành JSON: `json.loads(state.created_dirs)` trong test của T36 xanh; hợp đồng T15 (đã tick) không đổi.
- Hai commit `wip` không squash: merge `--no-ff`, không viết lại lịch sử (STD-GIT-4); ghi vào báo cáo lượt 5.

## deferred

1. `TestDelete` / `TestRename` không khẳng định `applied_ahead_count`.
2. Docstring `_commit_block` (`apply_job.py:414-419`) chưa nhắc ca commit của người làm HEAD đổi.
3. Ba minor của vòng 1.
