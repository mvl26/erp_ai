Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 21 — FEAT-004 T21

- Diff: `team/FEAT-004-task-21` (head 3d19fda), base 485f09c (head của T47, review riêng)
- Vòng: 1
- Verdict: approve

Lệnh git đã chạy (chỉ đọc):
```
git log --oneline 485f09c..team/FEAT-004-task-21        # 1 commit 3d19fda
git diff --stat 485f09c..team/FEAT-004-task-21          # 4 file, +154 −15
git diff 485f09c..team/FEAT-004-task-21
git show team/FEAT-004:docs/team/features/FEAT-004/tasks.md | grep -n -A8 '^- \[ \] T21'
git show team/FEAT-004-task-21:erp_ai/agent/changes/apply_job.py      # run_change, _Stop, _apply_command
git show team/FEAT-004-task-21:erp_ai/agent/changes/process_runner.py # run_bench, _run_wrapped
git show team/FEAT-004-task-21:erp_ai/agent/changes/test_apply_job.py # helper result/log_row, test lệnh kề bên
git show team/FEAT-004-task-21:erp_ai/agent/tools/source.py           # git đọc qua subprocess.run
git log -1 --format=%B 3d19fda
```

## Layer 1 — khớp spec
- Thiếu: không. Đủ AC-8 (1 lời gọi, đuôi đối số = `command_args`, `timeout -s KILL <n>`, không `shell`, `cwd` = bench, `timeout=`, `start_new_session=True`, 0 lệnh git, commit trạng thái trước tiến trình), AC-9 (sửa thành lệnh cấm: cả nhánh digest lẫn nhánh danh sách cho phép, 0 lời gọi `subprocess.run`), AC-10 / QĐ-A3 (`limit = int(...)` không `max(0, …)`; `limit < 1` → không gọi `run_bench`, `Lỗi` "quá thời gian", `duration_ms = 0`, `command_output = ""`, đúng 1 dòng `fail`; 1.0 s → `run_bench(args, 1)`), QĐ-B4 (đề xuất `exit_code = 0`, `value_after.exit_code is None`; JSON `depends_on` đúng chuỗi). Câu chữ design 4.3 bước 4 đúng từng chữ: "không tìm thấy bench trên máy chủ", "lệnh trả mã <n>".
- Thừa: không. 4 file đúng touchpoint; nhánh `timed_out` giữ câu cũ (thuộc T22), chỉ tách test sang `test_timed_out_command_ends_as_failed`.
- Hiểu sai: không.

## Kiểm đột biến (đọc tay, không chạy)
- Bỏ nhánh `limit < 1` → `run_bench(args, 0)` ném `ValueError` (hợp đồng T11) → nhánh `except Exception` ghi lý do "ValueError" + `log_error` → test hết ngân sách đỏ (khớp RED của dev).
- `limit < 0` thay `< 1` → ca 0.999 s đỏ; `limit < 2` → test 1 giây đỏ.
- Câu chữ: test so chuỗi viết tay, không so hằng → đổi hằng là đỏ.
- 0 lệnh git: git đọc (`source.py:300,398`) và git ghi (`process_runner._run_wrapped`) đều qua `subprocess.run` đã patch, nên `call_count == 1` bắt được mọi lệnh git.
- Stub `time.monotonic`: nếu có lời gọi khác chen trước `started`, hạn chót lệch và test đỏ (lỗi lộ ra, không bị che).

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| — | — | — | Không có blocker/major | — |

minor | — | — | 2 điểm nhỏ: (1) STD-TEST-8: nhánh thành công chưa kiểm `duration_ms` trên đề xuất và `value_after` của dòng `apply` (Returns "mọi nhánh"); hiện chỉ dựa vào `transitions.finish` của T14 và `command_output == "xong"`; (2) STD-STYLE-5: lọc `"git" in call.args[0]` trong `test_approved_command_runs_once_with_exact_args` (test_apply_job.py:2288) thừa vì đã có `call_count == 1` và `argv[4:] == ["bench", ...]` | tùy dev

## Review checklist (10)
1. Đạt — làm đúng và đủ Returns đã sửa theo QĐ-A3/QĐ-B4, không thừa (STD-DESIGN-5, STD-TEST-2).
2. Đạt — 4 file đúng touchpoint, không file mới (STD-DESIGN-1, STD-STRUCT-1).
3. Đạt — RED có trong gói (câu chữ, `ValueError ... 0`, `None != depends_on`); có test biên 0.999 s, −5 s, 1.0 s, mã None + `not_found`; không skip/xfail (STD-TEST-1, STD-TEST-8, STD-TEST-4).
4. Đạt — test cũ chỉ đổi theo spec mới (câu chữ design 4.3, đổi tên theo Expect); đồng hồ được stub, không phụ thuộc giờ thật (STD-TEST-5, STD-TEST-6).
5. Đạt — lệnh vẫn có `timeout` + backstop; hết ngân sách thì không chạy tiến trình; lỗi đi qua `_Stop`, không nuốt (STD-ERR-1, STD-ERR-5).
6. Đạt — không shell, đối số dạng danh sách, AC-9 chặn lệnh bị sửa; không bí mật (STD-SEC-1, STD-SEC-3).
7. Đạt — chỉ thêm `depends_on` (meta UI, không đổi cột), `modified` tăng để migrate nhận; đảo ngược được bằng xóa khóa (STD-DESIGN-3, STD-OPS-2).
8. Đạt — tên hằng/test theo profile và Expect; không code chết (STD-NAME-2, STD-STYLE-5).
9. Đạt — không thêm phụ thuộc (`import subprocess` là thư viện chuẩn, chỉ trong test) (STD-DEP-1).
10. Đạt — nhánh `team/FEAT-004-task-21`, commit `feat(changes): ... (FEAT-004)`, không trailer AI; không đổi hành vi tài liệu người dùng ngoài form (STD-NAME-4, STD-NAME-5, STD-GIT-1, STD-GIT-8).

## Không kiểm được từ diff
- `bench migrate` chưa chạy: `depends_on` chỉ có hiệu lực trên form sau khi tech-lead migrate (QĐ-B4 yêu cầu chạy một mình). Test JSON chỉ đọc file, không kiểm meta trên site.
- `cmd.test` đầy đủ chưa chạy (site chung); GREEN của dev chỉ gồm `test_apply_job` (100 OK) và `test_erp_ai_change_proposal` (25 OK). Reviewer không chạy test.
- `design.md:626` vẫn ghi `limit = max(0, …)`; QĐ-A3 ghi "Sửa: design 4.3 bước 4" nhưng design.md chưa được sửa → tech-lead báo designer cập nhật (không phải lỗi của dev).
- Ẩn ô `exit_code` khi `Lỗi` + mã 0 là hành vi UI: cần xem form thật sau migrate.

## Deferred
- Không có.
