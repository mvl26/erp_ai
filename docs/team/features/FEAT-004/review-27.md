Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 27 — FEAT-004 T27

- Diff: `git diff 318fddb..3187f7c` (1 commit, 2 file, +129/-1; nhánh xếp chồng trên T26 đã approve). Hàm có từ trước do phiên khác viết ngoài quy trình; reviewer chấm phần T27 của file ở đầu nhánh task, gồm cách dựng và kiểm `command_args`
- Vòng: 1 (max_rework=3)
- Verdict: approve (đường dẫn ký sẵn trong `_comment` thuộc Amendment 2 / CHG-001, chấm ở `review-chg001.md`)

## Vòng 1 — approve
Lớp 1: đạt, trong touchpoint. `propose_bench_command` (`propose_change.py:199-219`) từ chối qua `_entry_refusal` trước, rồi dựng `command_args` chỉ ở server bằng `change_guard.build_bench_args(command, app, allowed_apps, frappe.local.site)`; hàm đó chạy `_bench_shape` rồi `check_bench_args` trên danh sách đã dựng nên kiểm site, ký tự shell và `--force` lúc đề xuất trùng lúc áp dụng; model không cấp `--site` hay tên chương trình. `reversible=0`; trường git `""`/0; schema enum lấy từ `BENCH_COMMANDS`, `app` 1..100. Bộ chặn chỉ đọc file, không sinh tiến trình (`change_guard.py:72-129`) nên AC-8 "0 tiến trình con" đúng theo cấu trúc. Giá trị mong đợi viết tay: bảng 6 lệnh, `command_args` từng lệnh, câu từ chối, cỡ enum.

Không có blocker, major.

minor | — | — | 4 điểm nhỏ: `test_propose_change.py:476-477` dùng `update`, `restart` trong khi design 8.1 nêu `command="execute"`; chưa có ca ở mức tool chứng minh `check_bench_args` chạy (vd `app="a;b"`), hiện chỉ có test của bộ chặn từ T9; chưa có ca `app` toàn khoảng trắng với `build`; `:525-527` đổi user trong vòng lặp | tùy dev

## Review checklist (10)
Đã phủ 10/10.

## Bằng chứng của dev
- RED: `AssertionError: Tuples differ: (1, 80) != (1, 100)`; `(None, None, 0, 0) != ('', '', 0, 0)` ở 6 subTest; test 0 tiến trình con xanh sẵn, chứng minh đỏ bằng một lời gọi `subprocess.run` tạm rồi bỏ: `AssertionError: 6 != 0`
- GREEN: test_propose_change `Ran 19 tests in 14.474s` / `OK`; test_registry `Ran 33 tests in 1.190s` / `OK`

## Không kiểm được từ diff (tech-lead xử lý)
- Design 2.1 ghi "5 trường git rỗng/0" nhưng `commit_message` do controller dựng lúc insert (D-14): test T27 không kiểm trường này cho lệnh bench → giao T50 (test `test_tool_cannot_set_git_fields_or_commit_message`).
- Chữ `proposal_notes` cho lệnh: thuộc T50.

## deferred
- 4 điểm nhỏ ở trên: xét ở T50 (cùng file test).
