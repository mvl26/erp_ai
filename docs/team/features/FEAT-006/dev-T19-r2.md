# dev T19 vòng 2 (rework 1/3) - FEAT-006

Nhánh: team/FEAT-006-task-19-rework1 (gom một commit từ a62944e).

## Finding (major, STD-TEST-6): test phụ thuộc `routing_rules` thật của site
- RED: tạm đặt `routing_rules` trong `RunnerTestBase.setUp` thành giá trị có `assignees.*.default` là agent hợp lệ và `departments` không rỗng (mô phỏng site đã cấu hình), chưa sửa gì khác:
  - `test_runner_routing.TestRoutingLog.test_l1_no_score_writes_zero_logs_no_score`: `AssertionError: 'erpai-test-agent-...@example.com' is not false`
  - `test_agent_runner.TestRunner.test_l0_logs_prediction_ticket_unchanged`: `Tuples differ` (system prompt có thêm `DANH SÁCH BỘ PHẬN: Kế toán`)
- Sửa: `RunnerTestBase.setUp` đặt `routing_rules=make_routing_rules()` (không người, không bộ phận) nên mọi test kế thừa (cả `RoutingTestBase`) không còn phụ thuộc cấu hình site.
- Phủ: hai test trên + toàn bộ test kế thừa; chạy lại xanh.

## Minor
- `test_l0_entry_has_scores_ticket_unchanged` kiểm thêm `ai_importance` và `ai_score_reason` của phiếu không đổi (rỗng).

## Lệnh
- `run-tests --module erp_ai.agent.test_runner_routing` và `erp_ai.agent.test_agent_runner`: OK.
- `run-tests --app erp_ai`: `Ran 792 tests ... OK`.
- `pre-commit run --files` hai file test: Passed (ruff linter và formatter).
