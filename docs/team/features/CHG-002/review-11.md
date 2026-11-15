Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 11 — CHG-002 T11

- Diff: `git diff 990d7b3..1a54b18` (nhánh `team/CHG-002-task-11`: `e64a269` + merge `4cda38f` không mang thay đổi + `1a54b18`; 4 file, +137/−11)
- Vòng: 1 của đề bài theo `design-addendum-6.md` (max_rework = 3); lần gọi dev đầu (round 25) dừng `DESIGN_CONFLICT`, chưa từng review
- Verdict: **approve** → merge `0797cce`, tick

## Vòng 1 — approve

Phát hiện blocker/major: không.

minor | — | — | 2 điểm nhỏ (xem deferred) | tùy dev

Lớp 1 (khớp đặc tả): đủ tiêu chí, đúng bốn file touchpoint.
- AC-47 Returns (`change_guard.py:44-45`, `:283-284`): `RESTART_COMMAND = "restart"` trong `BENCH_COMMANDS`; `build("restart")` trả `["restart"]`, `check(["restart"])` trả `None`; đối số thừa → `CMD_NOT_LISTED` hoặc `CMD_TAKES_NO_APP`; các bước trước (ký tự shell, `--force`, site khác) vẫn thắng.
- Addendum-6 P-1 (`propose_change.py`): `_SINGLE_BENCH_COMMANDS` (`:55-57`) đúng từng byte; enum lấy từ hằng (`:383`); dòng chặn ngay sau `_entry_refusal`, trước `build_bench_args` (`:284-285`); mô tả tool và tool khác không đổi.
- P-2 bước 7: mã `e64a269` khớp Returns; hằng mới chỉ loại `restart` (hai test cũ không đổi chứng minh: enum ghim bảng 6 lệnh, sáu lệnh đi qua handler đều `ok`).
- `test_propose_change.py` chỉ thêm một hunk (0 dòng xóa); `:490`, `:535-546` không đổi.
- Thân commit đúng chữ P-2 bước 6: 1 `test-shape:`, 1 `test-drop:`, 1 `test-new:`, `L-1: 1, L-2: 1`.

Bằng chứng của dev: RED 1 `Ran 33 tests in 44.583s` / `FAILED (failures=2, errors=1)` (`KeyError: 'reason'`; `'restart' unexpectedly found in [...]`); RED 2 `Ran 33 tests in 40.472s` / `FAILED (failures=1)`; GREEN `test_change_guard` `Ran 48 tests in 1.617s` / `OK`, `test_propose_change` `Ran 33 tests in 43.090s` / `OK`, `test_registry` `Ran 41 tests in 3.067s` / `OK`, `test_apply_job` `Ran 117 tests in 224.364s` / `OK`, `test_architecture` `Ran 184 tests in 24.500s` / `OK`.

Review checklist (10): 10/10 đạt.

## Không kiểm được từ diff (tech-lead đã xử lý)

- "Người dùng desk có tự tạo/sửa `command_args` thành `["restart"]` cho đường lệnh đơn được không" (A6-1): `git show 1a54b18:…/erp_ai_change_proposal.json` mục `permissions`: chỉ `ERP AI Agent` có `create` + `read`; `ERP AI Instructor` và `System Manager` chỉ `read`; không vai trò nào có `write`. `command_args` nằm trong danh sách trường nội dung của controller (`erp_ai_change_proposal.py:21`), và job so `content_digest` với `approved_digest` trước khi chạy (`apply_job.py`, `DIGEST_CHANGED`). Tool là nơi duy nhất tạo dòng và tool đóng `restart` tới T28 → không phải thiếu sót của T11.
- `e64a269` là commit đỏ trên nhánh (`test_propose_change`): do addendum-6 P-2 bắt buộc "một commit mới trên `e64a269`, không viết lại lịch sử"; merge `--no-ff`, không phải phát hiện.
- Reviewer không chạy test. Module và cả app sau merge: dòng progress của T11 trong `tasks.md` (đợt merge 11, `349560d`).

## deferred

1. `test_every_denied_command_refused` lặp lại 22 tên của `A6_DENIED_COMMANDS` theo thứ tự khác (STD-DESIGN-4; design nêu tên test này).
2. Không test nào ghim dòng chặn mới đứng sau `_entry_refusal`.
