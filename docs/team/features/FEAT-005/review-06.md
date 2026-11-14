Feature: FEAT-005
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 06 — FEAT-005 T6

Tech-lead chép từ tin trả về của reviewer (reviewer không ghi file).

- Diff: `git diff c4338f8..a65af8d` (nhánh `team/FEAT-005-task-6`, 2 commit; vòng 1 `c4338f8..d43ef0b` 2 file +127/−11, vòng 2 `d43ef0b..a65af8d` 2 file +13/−7); merge `ccda05c`
- Vòng: 2
- Verdict: approve (vòng 2); vòng 1 request-changes

## Vòng 2 — approve (`d43ef0b..a65af8d`, chấm lại có phạm vi)

- major STD-TEST-2: ADDRESSED. `erp_ai/agent/test_agent_runner.py:2549-2565`: `_run_with_logger` cho mỗi tên logger một mock riêng (`self.loggers.setdefault(module, MagicMock())`), `_undo_warnings` chỉ đọc `self.loggers.get(LOGGER_NAME)`; cả ba test dùng nó (test callback ở `:2624`). Lời gọi của `_end_status` (`runner.py:224`) ghi `.info`, không tự làm phép kiểm qua được.
- minor (2) docstring: ADDRESSED (`runner.py:689-691`). minor (1) `_undo_turn(run_id)` so với `_undo_turn()` của design: NOT ADDRESSED, tùy dev, không chặn.
- Phát hiện mới: không có blocker/major. minor | — | — | 1 điểm nhỏ: commit `a65af8d` loại `test(...)` nhưng có sửa docstring `runner.py` | tùy dev
- Bằng chứng của dev vòng 2: đột biến nhánh savepoint mất → `frappe.logger()`: `FAIL: test_lost_turn_savepoint_keeps_original_error`, `FAIL: test_lost_turn_savepoint_keeps_commit_callbacks`, `AssertionError: Lists differ: [] != [('reason turn undo failed run_id=%s error[57 chars]or')]`; nhánh callback → `frappe.logger("frappe")`: `FAIL: test_failing_rollback_callback_keeps_original_error`; `Ran 14 tests` / `FAILED (failures=3)`. GREEN `--case TestRunnerTurnUndo` `Ran 14 tests in 6.311s` / `OK`. Cả module trên đầu nhánh task: `FAILED (errors=4)` rồi `FAILED (errors=12)`, toàn `QueryDeadlockError` ở `setUp` → `set_agent_settings`.

## Vòng 1 — request-changes (`c4338f8..d43ef0b`)

Lớp 1 đạt: hai nhánh của design §4.1 bước 1–2 có đủ; savepoint mất → warning chỉ tên lớp lỗi, return, không đụng hàng callback, không đặt lại savepoint; callback ném → bắt với warning riêng; hai chỗ bắt đều có chú thích lý do; ba test §8 có mặt; chỉ sửa trong touchpoint.

- major | STD-TEST-2 | erp_ai/agent/test_agent_runner.py:2552,2575 | Tiêu chí nói `frappe.logger(LOGGER_NAME)` nhưng tên đó không thật sự được kiểm. `_run_with_logger` trả một mock chung cho mọi tên logger. Phép kiểm tên duy nhất là `assertIn(LOGGER_NAME, get_logger.call_args_list)`, mà `_end_status` (runner.py:224, trong `finally` của `_run`) gọi `frappe.logger(LOGGER_NAME)` ở mọi lượt chạy nên phép kiểm luôn qua. Nếu `_undo_turn` gọi `frappe.logger()` hoặc `frappe.logger("frappe")` ở một trong hai nhánh, cả ba test vẫn xanh. Test callback không có phép kiểm tên nào. | Cho mỗi tên logger một mock riêng (`side_effect=lambda name=None, *a, **k: loggers.setdefault(name, MagicMock())`) và đọc `_undo_warnings` từ `loggers[LOGGER_NAME]` ở cả ba test
- minor | — | — | 3 điểm nhỏ: (1) design §4.1 và "Receives" của T6 viết `_undo_turn()`, mã là `_undo_turn(run_id)` (cần cho warning in `run_id`; hàm riêng, một nơi gọi `runner.py:675`; không phải lỗi, design-amd2 hoặc As-Built nên cập nhật); (2) docstring `_undo_turn` chưa nêu nhánh savepoint mất; (3) giả savepoint mất bằng `release savepoint` thô trong `write_entry` đã patch là hợp lệ (MariaDB trả cùng lỗi 1305 như sau commit) | tùy dev

- Bằng chứng của dev vòng 1: RED `--case TestRunnerTurnUndo` `Ran 14 tests` / `FAILED (failures=3)`, `['ticket=43069 trigger=comment_mention error=OperationalError'] != ['ticket=43069 trigger=comment_mention error=TurnFaultForTest']`; GREEN `Ran 14 tests in 6.585s` / `OK`, cả module `Ran 108 tests in 29.322s` / `OK`; 5 đột biến đỏ.

## Tech-lead đã kiểm

- Sau merge `ccda05c`, một lần giữ khóa `miyano-site.lock` (0 lệnh site ngoài khóa trước và sau, migrate exit 0, hai cài đặt để trống rồi trả lại đúng `1` và 4 app): test_agent_runner `Ran 108 tests in 27.033s` / `OK`, 0 deadlock.
- `git diff --name-only c4338f8..a65af8d` = `erp_ai/agent/runner.py`, `erp_ai/agent/test_agent_runner.py` (đúng touchpoint).

## Không kiểm được từ diff

- `CallbackManager.run` của Frappe (`frappe/utils/__init__.py:1222-1226`) dừng ở callback đầu tiên ném; callback rollback xếp sau không chạy và bị commit cuối job xóa. Khớp D-8 ("như `frappe.db.rollback()`") nhưng design không nói có chạy tiếp phần còn lại hay không; test đặt callback lỗi ở cuối nên không phân biệt được. Là quyết định thiết kế, không phải lỗi của dev → báo team-leader (designer thêm một câu vào D-8 hoặc ghi nợ).
- Ở production savepoint mất hiện ra là `OperationalError 1305` qua ánh xạ lỗi của `sql()`; đúng với MariaDB ở đây → qa (verify).
- `cmd.lint` cả repo: chạy ở T16.

## deferred

- minor (1) chữ ký `_undo_turn(run_id)`: cập nhật chữ design-amd2/As-Built (designer, writer).
