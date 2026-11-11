# dev-T29 — FEAT-001 T29 (runner: L1 ghi phân loại qua tool)

Status: DONE. Branch `team/FEAT-001-task-29` (từ a39ee7c). Files: `erp_ai/agent/runner.py`, `erp_ai/agent/test_runner.py` (đúng touchpoints) + file báo cáo này.

## Thiết kế
- `_classify` ghi dòng `classify` (applied=0) TRƯỚC, `write_entry` commit khi not in_test. Sau đó ở `level >= L1` dựng `ToolContext` một lần (instructor = `authority.latest_instructor`) và gọi `_apply_classification`.
- `_apply_classification`: savepoint `erp_ai_apply` quanh `execute_tool("set_classification")` + `frappe.db.set_value` của dòng log (`applied=1`, `value_before/after`, `actions`; chỉ khi `ok` và `after` không rỗng). Ngoại lệ giữa chừng -> `rollback(save_point)` hoàn tác phiếu rồi raise (`run_for_ticket` ghi `log_error`); dòng log đã commit nên còn, applied=0. Commit đúng một lần sau khi cả hai đã ghi (chỉ khi not in_test). Handler không commit.
- Cầu dao khóa (commit của `_call_model`) không bị động: không rollback toàn phần.

## RED (trước khi có code runner, `run-tests --module erp_ai.agent.test_runner`)
Ran 30 tests, failures=3 (đúng lý do hành vi thiếu), phần còn lại là deadlock do T31 chạy song song (không phải lỗi test):
- test_l1_applies_mapping_confidence_and_hint: `('', None, 'Medium') != ('ERPAI-TEST-loại', 'ERPAI-TEST-nhóm', 'High')`
- test_ticket_change_is_never_committed_before_its_log_outcome: `('', 0) != ('AI', 1)`
- test_failure_after_tool_rolls_ticket_back_and_keeps_entry: `Expected 'log_error' to have been called once. Called 0 times.`
- test_not_ok_result_with_after_is_not_applied: lỗi vì `runner` chưa có `execute_tool` (thiếu import, hết sau khi có code).

## GREEN
- test_runner: `Ran 30 tests ... OK` (4 lần liên tiếp, một lần sau format). test_registry: `Ran 24 tests OK`.
- Không chạy full cmd.test (T31 song song). Deadlock 1213 xảy ra ở `set_single_value` khi T31 chạy cùng; chạy lại thì xanh.
- lint: `pre-commit run --files runner.py test_runner.py` -> tất cả Passed (ruff format sửa file 1 lần, chạy lại Passed). typecheck: không có slot.

## Mutation (STD-TEST-8): mỗi guard có test đỏ khi bỏ
| Bỏ guard | Test đỏ |
|---|---|
| `result.get("after")` | test_l1_empty_after_keeps_applied_zero |
| `result.get("ok")` | test_not_ok_result_with_after_is_not_applied |
| rollback về savepoint | test_failure_after_tool_rolls_ticket_back_and_keeps_entry |
| commit cuối | test_ticket_change_is_never_committed_before_its_log_outcome |
| `level == L0: return` | test_l0_still_does_not_apply (bắt buộc patch `execute_tool` và assert not called; vì registry đã chặn L0, nếu không guard này không quan sát được) |
Ghi chú: human-not-overwritten được tool chặn (test_l1_human_classified_not_overwritten); test cổng commit: setUp patch `frappe.db.commit` raise AssertionError, `log_error` patch.

## Dữ liệu test
Fixture tiền tố `ERPAI-TEST-` (HD Ticket Type, HD Team) tạo trong test, rollback ở cleanup, `frappe.db.commit` bị chặn. Đếm HD Team/HD Ticket/User/ERP AI Log/Error Log trước = sau = 4/3/8/0/195.

## Seen but not touched
- Test cấu trúc: tách `RunnerTestBase` (setUp dùng chung) khỏi `TestRunner`; lớp mới `TestRunnerL1Classification`.
- Lỗi mid-run sau khi dòng log đã commit nhưng trước `release_savepoint` đều quay về applied=0 và phiếu cũ; nếu `frappe.db.commit()` cuối tự nó lỗi thì không còn hoàn tác (không xử lý).
- Phần "hint" (`set_resolution_hint`) thuộc T30.
