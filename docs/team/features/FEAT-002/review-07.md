Feature: FEAT-002
Stage: build
Author-agent: reviewer
Date: 2026-11-12
Approved-by:

# Review 07 — FEAT-002 T7

- Diff: `git diff 8108969..team/FEAT-002-task-7` (vòng 2: `git diff 79d10d0..team/FEAT-002-task-7`)
- Vòng: 2 (max_rework=3)
- Verdict: approve

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major (vòng 1, ADDRESSED) | STD-TEST-2 | erp_ai/agent/runner.py:203,214,234,331,356 | D-9: mảnh lỗi phát nối vào `error` của bản ghi kế tiếp ở 5 chỗ; chỉ chỗ 356 (không lỗi khác) có test, phép nối `"; "` chưa kiểm | 5 test mới, mỗi chỗ bỏ `*status.take_errors()` đều đỏ đúng test tương ứng |

minor (đã làm): danh sách chữ cấm dùng nhãn `WORK_LABELS` trần, bỏ `THINKING_TEXT` vô nghĩa, bỏ thu `info` hai lần, thêm test mảnh treo khi crash. minor còn lại: `_fail_first_working` gần trùng `_fail_signals`; `self._gateway(...)` thừa trong test crash.

## Review checklist (10)
1–10: đạt ở vòng 2. Không đổi mã sản phẩm (chỉ test).

## Bằng chứng dev
- Vòng 1 xanh ngay (thay đổi chỉ test, mã đã đúng); bằng chứng độ nhạy là đột biến: bỏ `removing self.started = True`, `{exc}` thay tên lớp, bỏ `*status.take_errors()`, thêm `status.text` vào Error Log: đều đỏ rồi hoàn lại. Vòng 2: bỏ `*status.take_errors()` ở 214/224/234/331/356 → mỗi chỗ đỏ đúng test.
- XANH: `test_runner_status` Ran 39 OK, `test_run_status` 9 OK, `test_agent_runner` 56 OK, `tests.test_handlers` 31 OK, `tests.test_architecture` 44 OK; lint đạt.
- Merge 533f93f.

## deferred
2 minor nêu trên (không chặn).
