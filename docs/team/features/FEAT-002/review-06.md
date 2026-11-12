Feature: FEAT-002
Stage: build
Author-agent: reviewer
Date: 2026-11-12
Approved-by:

# Review 06 — FEAT-002 T6

- Diff: `git diff e93d9b1..team/FEAT-002-task-6` (vòng 2: `git diff c663cbb..team/FEAT-002-task-6`)
- Vòng: 2 (max_rework=3)
- Verdict: approve

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major (vòng 1, ADDRESSED) | STD-TEST-2 | erp_ai/agent/test_runner_status.py:439 | dòng tóm tắt design 4.5 chỉ kiểm tới `errors`; `delay_s`/`waited_s` không kiểm | kiểm `values[5:]`: [4,0] (không post_comment), [4,3] (có trả lời, model 1s), [0,0] (ticket_insert) |
| major (vòng 1, ADDRESSED) | STD-TEST-2 | erp_ai/agent/test_runner_status.py:567 | test không phải so sánh bật/tắt của design 8.1 | savepoint, chạy bật, ghi (Comment, Task, modified), rollback, chạy tắt, so hai bộ |

minor (đã làm): tham số `run=None` thừa, biến `call` che `mock.call`, `assertLess` thừa; `_end_status` bọc try/except từng lời gọi `log_error`/logger kèm 2 test.

## Review checklist (10)
1–10: đạt ở vòng 2. Lưu ý: `run_status.py` ngoài dòng `files:` của T6 nhưng Returns của T6 nêu `signal_count` (design 3.3), đã sửa dòng `files:`.

## Bằng chứng dev
- ĐỎ vòng 1: `test_runner_status` Ran 27, failures=9 (`logger('erp_ai') call not found`; nhánh rollback `0 != 1`). Vòng 2: 2 test bảo vệ `_end_status` đỏ (`RuntimeError: log_error down`, `OSError ... ValueError`).
- Đột biến (5) đều đỏ rồi hoàn lại.
- XANH: `test_runner_status` Ran 30 OK, `test_agent_runner` 56 OK, `test_run_status` 7 OK, `tests.test_handlers` 31 OK, `tests.test_architecture` 44 OK; lint đạt.
- Toàn bộ `--app erp_ai` (vòng 1): Ran 563, failures=16 errors=3 (danh sách đỏ nền: alert/accuracy). DB: HD Team 4, HD Ticket 5, ERP AI Log 32 không đổi; Comment 120165 → 120185 (+20, xem deferred).
- Merge fc9f072; cây sau merge chỉ gồm 3 tệp của nhánh task.

## deferred
- Tăng Comment +20 trong full suite: dev báo `test_agent_runner` riêng cũng thêm ~2 Comment; nguồn nằm ở setup test cũ, chưa dò; kiểm lại ở full suite cuối (so trước/sau).
- `run_for_ticket` `except` gọi `frappe.log_error` ngoài chốt bảo vệ (có sẵn từ trước, ngoài phạm vi).
- 3 minor vòng 2 (không assert `log_error` được gọi trong test thay exception; `failing_done` KeyError với sự kiện không có `state`; ghi `status._errors` riêng tư).
