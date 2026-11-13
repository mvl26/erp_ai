# Review 25 — FEAT-001 T17 (cổng: `call_model` chuyển khóa theo cầu dao)

- Verdict: approve (vòng 2; 1 vòng rework)
- Diff: `git diff e50754a..team/FEAT-001-task-17` (head 1125d18); merge 0718c42
- Vòng 1 request-changes: 4 major (STD-TEST-8 seed Setting trùng mặc định; STD-TEST-2 `latency_ms`; STD-TEST-8 `log_error` trong except/`_alarm_no_key`; STD-TEST-8 `from None` của bad_request). Vòng 2 (FIX_BASE 7bc7f0c): cả bốn ADDRESSED; minor (1) và (3) cũng đã sửa
- Touchpoint mở rộng (tech-lead): `erp_ai/tests/test_handlers.py`, chỉ xóa `test_gateway_stub_raises_not_implemented` (stub đã bị thay, spec đổi)
- Bằng chứng dev: RED Ran 43 (errors=20); GREEN test_gateway Ran 47 OK; `--app erp_ai` Ran 222 OK; pre-commit exit 0; 19+ đột biến một nhánh đều đỏ
- Các nợ review-19/24 đã làm và có test: `request_id` vào `apply_failure`, `decide()` nhận error_count cũ + 1, D-21 theo trạng thái cũ, usage None → 0

## Findings
Không còn blocker/major.

## Deferred
- T28 (runner): trạng thái khóa ghi không commit; nếu runner rollback khi lượt hỏng thì mất trạng thái khóa và Error Log báo động; lỗi ngoài `client.send` (`select_keys`, `apply_success`, `compute_cost`) ra thô, runner phải bắt (D-20).
- `OutgoingEmailError` khi chưa có Email Account: `call_model` đã bắt và ghi log; T34 quyết định đường lỗi.
- NFR-5 đầu-cuối (`test_api_key_never_leaks`) ở T19; nhãn khóa phải duy nhất (`select_keys` loại theo label).
- minor: test `_alarm_no_key` thiếu `assertNotIn("no email account", ...)`; dòng NFR-7 của design 804 còn ghi 3 lần thử.
