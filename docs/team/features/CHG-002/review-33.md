Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 33 — CHG-002 T33

- Diff: `git diff 0499815..ca9a03d` (nhánh `team/CHG-002-task-33r`, 2 commit `4087cbf` + `ca9a03d`, 4 file)
- Gói: T33 + T34 được giao cùng một dev; T34 chấm riêng (`review-34.md` khi có phán quyết), T33 tách sang nhánh `-33r` để merge trước
- Vòng: 2 (max_rework = 3)
- Verdict: **approve** ở vòng 2 → merge `7b7f000`, tick

## Vòng 1 — request-changes (`git diff 0499815..4087cbf`)

major | STD-TEST-8 | erp_ai/agent/changes/apply_job.py:292 (test: test_apply_block.py:457) | Tham số của `check_block` lúc áp dụng mới ghim một nửa: chỉ `legacy=True` (dạng cũ) được kiểm; phía khối (`legacy=False`, nhánh bật luật restart/migrate) không có ca nào; không ca nào ghim `diff_text`. Đổi thành `legacy=True` cố định hoặc `diff_text=""` thì cả gói vẫn xanh. | Thêm ca khối bị từ chối chỉ vì `legacy=False`; ở test dạng cũ assert `guard.call_args.kwargs["diff_text"] == <diff đã lưu>`.

minor | — | — | 4 điểm nhỏ (xem deferred) | tùy dev

Đạt ở vòng 1: `_recheck_block` chạy `check_block(at_apply=True, diff_text=cstr(doc.diff), legacy=not is_block)` trên kết quả bộ chuyển đổi cho cả hai dạng; mỗi dòng kiểm cả hai hash; bản xem trước commit được so; `_apply_block` giả đã bỏ; P-6 (đường dẫn rỗng) và `[[]]` bị từ chối lúc áp dụng; `test_change_decision.py` thêm vào touchpoint đúng luật của lượt build; 4 dòng `test-shape:` và 1 dòng `test-input:` đúng định dạng, tên subtest có thật. `STORED_HASH_MISMATCH` không có tiền tố mục: đúng thiết kế (design-addendum-7.md:101). Đường hoàn tác của `_recheck` không còn `check_bench_args`: an toàn vì `transitions.py:252` không cho hoàn tác đề xuất không phải code.

Bằng chứng của dev (vòng 1): RED `FAIL: test_guard_fails_at_apply_error_names_item (item=2)`: `('Lỗi', 'loại mục phải là edit, create, delete hoặc rename', None) != ('Lỗi', 'mục 2 (custom_app/docs/b.txt): đường dẫn đi qua symlink', None)`, `Ran 9 tests in 5.812s` / `FAILED (failures=11, errors=3)`; GREEN `test_apply_block` `Ran 9 tests in 6.596s` / `OK`, `test_block` `Ran 10 tests in 0.038s` / `OK`, `test_change_decision` `Ran 10 tests in 10.037s` / `OK`, `test_architecture` `Ran 185 tests in 15.382s` / `OK`, `test_apply_job` `Ran 117 tests in 146.727s` / `OK`. L-1: 4, L-2: 0, test-input (luật mới): 1.

## Vòng 2 — approve (`git diff 4087cbf..ca9a03d`, chỉ `test_apply_block.py`)

- ADDRESSED | STD-TEST-8 | hai ca mới: "block .py without restart" (`:303`) → `PY_NEEDS_RESTART`, "block restart without .py" (`:304-309`) → `RESTART_WITHOUT_PY` (hai luật nằm dưới `if not legacy:` ở `change_guard.py:498-503`); chiều ngược lại ghim bằng `assertEqual(kwargs["legacy"], True)` (`:386`); `diff_text` ghim ở `:370-371,388`. Dev dùng `RESTART_WITHOUT_PY` thay cho gợi ý `RESTART_NEEDS_MIGRATE` của reviewer: đúng, vì `RESTART_NEEDS_MIGRATE` được kiểm ngoài nhánh `legacy`.

Lỗi mới trong các dòng đổi: không.

Bằng chứng của dev (vòng 2): RED bằng đột biến `('Lỗi', 'loại mục phải là edit, create, delete hoặc rename', None) != ('Lỗi', 'khối có file .py phải kết thúc bằng migrate rồi restart', None)`, `AssertionError: '' != '--- a/pkg/legacy.py\n+++ b/pkg/legacy.py\n-x = 1\n+x = 2\n'`, `Ran 9 tests in 9.288s` / `FAILED (failures=3)`; GREEN `test_apply_block` Ran 9, OK; `test_block` Ran 10, OK; `test_change_decision` Ran 10, OK; `test_architecture` Ran 185, OK; `test_apply_job` Ran 117, OK.

## Không kiểm được từ diff (tech-lead đã xử lý)

- Helper `legacy(diff=…)` và `approve()` cho qua khối `.py` chỉ có `migrate`: ngoài diff sửa; xác nhận bằng module sau merge trên `team/CHG-002` @ `7b7f000` (dòng progress của T33 trong `tasks.md`).
- `read_git_state(new_file=True)` với file tạo trong thư mục chưa có: thuộc T35 (`test_rename_into_new_dir_fails_after_add_restores_index_and_dirs`, đã có trong lệnh giao T35).
- Khối có mục ở nhiều app: `check_block` từ chối trước (`BLOCK_TWO_APPS`, T12), nên `old_head` luôn của một repo.
- Cả app sau merge: dòng progress của T33 trong `tasks.md` (đợt merge 15, `7b7f000`).

## deferred

1. Khối hợp lệ nhưng chưa ghi được kết thúc `Lỗi` với `OP_UNKNOWN` (`apply_job.py:221`): chỗ tạm, T36 / T37 phải gỡ (đã ghi vào lệnh giao).
2. AC-46 (a) lúc áp dụng mới có ca `.json`; ca `.py` thuộc T38 (`TestRestart::test_syntax_rechecked_at_apply_zero_written`).
3. Tên `test_stored_command_edited_to_denied_blocked_at_apply` không còn khớp ca `.py` mới; chú thích `:302` chưa chính xác.
