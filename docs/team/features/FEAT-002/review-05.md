Feature: FEAT-002
Stage: build
Author-agent: reviewer
Date: 2026-11-12
Approved-by:

# Review 05 — FEAT-002 T5

- Diff: `git diff 177f013..team/FEAT-002-task-5` (vòng 2: `git diff 201915a..120cb7e`; vòng 3: `git diff 120cb7e..f3153bf`)
- Vòng: 3 (max_rework=3; vòng 3 sạch)
- Verdict: approve

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major (vòng 1, ADDRESSED vòng 2) | STD-TEST-2 | erp_ai/agent/test_runner_status.py:342-357 | dời `working(CLASSIFY_STEP)` / `working("set_classification")` xuống sau việc vẫn xanh (AC-9, AC-2 ở `ticket_insert`) | kiểm `signals_on_model_call` `[2]` (L0) và `[2, 4]` (L1); bộ ghi `execute_tool` ghi (tên, chữ tín hiệu gần nhất) |
| major (vòng 1, ADDRESSED vòng 2) | STD-TEST-2 | erp_ai/agent/test_runner_status.py:320-340 | dời `status.working(block["name"])` xuống sau `_run_tool` vẫn xanh | cùng bộ ghi `execute_tool`: `get_ticket`/`post_comment`/`set_classification` có nhãn đúng lúc chạy |
| major (vòng 2, ADDRESSED vòng 3) | STD-TEST-1 | erp_ai/agent/run_status.py:60-64 | nhánh `try/except TypeError` ở `working()` không có test (dev nêu test không có trong commit) | `test_unhashable_step_never_throws` (`["x"]`, `{}`), đỏ khi bỏ `try`: `TypeError: unhashable type` |

minor (đã làm): nhánh `ticket_insert` không chờ kiểm thêm tín hiệu và `gateway.call_count`; bỏ `len(granted)==11`; xóa `self.signals` giữa các subTest.

## Review checklist (10)
1–10: đạt ở vòng 3 (vòng 1 phủ 10/10).

## Bằng chứng dev
- ĐỎ vòng 1: `test_run_status` 1 failed + 5 errors (`'RunStatus' object has no attribute 'working'`); `test_runner_status` 6 failed (`['thinking','done'] != ['thinking','working',...]`).
- Đột biến vòng 2 (ba chỗ) đều ĐỎ rồi hoàn lại: `[1] != [2]`, `[1, 4] != [2, 4]`, nhãn `Đang suy nghĩ…` thay `Đang làm: đọc phiếu…`, `phân loại phiếu` thay `ghi phân loại`. Vòng 3: bỏ `try` → `TypeError: unhashable type: 'list'`/`'dict'`.
- XANH: `test_run_status` Ran 7 OK, `test_runner_status` Ran 16 OK, `test_agent_runner` Ran 56 OK, `tests.test_handlers` Ran 31 OK, `test_architecture` Ran 44 OK; lint đạt.
- Toàn bộ `--app erp_ai` (vòng 1): nền (sau T4+T8) Ran 533 failures=16 errors=3; sau T5 Ran 544 failures=16 errors=3; 0 Deadlock; danh sách đỏ giống nền. Đếm DB trước/sau: HD Team 4, HD Ticket 5, ERP AI Log 29, không đổi; HD Form Script 0 (T9 xác nhận 0).
- Lưu ý vận hành: hai dev chạy test song song trên site chung vẫn gây deadlock thoáng qua (không chỉ full suite); chạy lại là sạch (D-3 mở rộng).

## deferred
`test_runner_status` `self.sleeps` không reset giữa subTest (chỉ làm kiểm tra chặt hơn, không phải lỗi).
