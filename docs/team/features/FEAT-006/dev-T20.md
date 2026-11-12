# dev-T20 — Runner `_route` (u1) và kiểm SLA (FEAT-006)

Nhánh `team/FEAT-006-task-20` (từ `team/FEAT-006` 77dce93). Trạng thái: **DESIGN_CONFLICT** (5 test cũ ở `test_agent_runner.py` đỏ vì hành vi mới theo spec).

## RED (đúng lý do: thiếu hành vi)
Lệnh: `PYTHONPATH=<worktree> bench --site miyano run-tests --module erp_ai.agent.test_runner_routing`
```
FAIL test_applied_follows_ok_even_when_nothing_changed: 0 != 1
FAIL test_exception_in_unit_...: log_error called 'erp_ai: lần chạy lỗi ... error=ValueError'
FAIL test_refusal_records_reason...: applied 1 != 0 (sau khi sửa test dùng CLASSIFIED_BY_HUMAN)
FAIL test_skipped_field_has_one_reason...: 'ánh xạ không có giá trị' != 'không có bộ phận'
FAIL test_route_info_line_has_codes_only: 0 != 1
ERROR test_slow_sla / test_no_sla: không có action sla_check (unpack 0 values)
Ran 24 tests ... FAILED (failures=5, errors=3)
```
(Hai lỗi do bộ dựng test: `make_sla` validate `condition` khi insert nên điều kiện hỏng được ghi bằng `db.set_value`; sửa test, không phải sửa hành vi.)

## GREEN
```
Ran 24 tests in 6.8s  OK      (erp_ai.agent.test_runner_routing)
pre-commit run --files runner.py test_runner_routing.py: tất cả Passed (ruff format đã chạy lại)
Toàn app: Ran 805 tests ... FAILED (failures=5)  — 5 test cũ, xem DESIGN_CONFLICT
```

## Finding -> thay đổi -> test
1. `applied` theo `result["ok"]`: `_record_route` ghi `applied = 1 if result` (result chỉ có khi ok). Test `test_applied_follows_ok_even_when_nothing_changed`. `applied_sla` có `sla` mà `priority`/`resolution_s` None: `sla_lag` trả None, không action. Test `test_sla_without_priority_or_resolution_is_not_a_lag`.
2. `skipped_fields` = `skipped` của (u1) trừ các trường đã có trong `decision.notes`, cộng `notes`: mỗi trường chỉ một lý do. Test `test_skipped_field_has_one_reason_when_route_note_explains_it` (E không bộ phận: `agent_group` chỉ "không có bộ phận").
3. `_route` trả `lines` (có `NO_SLA`), không gửi comment. Test `test_no_sla_one_action_one_warning_and_no_sentence_posted_yet`.
4. Ngoại lệ (u1): rollback savepoint `erp_ai_route`, action `ok=false` + `reason` = lớp ngoại lệ, `error` thêm `route apply_route: <Lớp>`, không ném, bước suy luận vẫn chạy. Test `test_exception_in_unit_...`, `test_broken_sla_condition_stops_route_cleanly` (không có `db.set_value` HD Ticket từ runner; 0 ToDo, 0 comment; phiếu trước = sau).
5. `ok=false` (người đã phân loại): action `ok=false` + `reason`, không kiểm SLA. Test `test_refusal_records_reason_and_skips_sla_check`.
6. Kiểm SLA ở L1+ bất kể công tắc: `sla_check` ok=false + `frappe.logger("erp_ai").warning` cho "không SLA" và "lệch" (`SLA <tên> xử lý <a> phút > mong đợi <b> phút (<cat>)`, `a` ép `int` vì `resolution_s` là float). Bỏ qua khi `routing_config` rỗng (design 4.3). Test `test_slow_sla_warning_in_log`, `test_matching_sla_no_action_no_warning`.
7. Dòng info `erp_ai route ticket= run_id= applied= sla= lines=` (chỉ mã/số; T21 thêm assigned/task/comment). Test `test_route_info_line_has_codes_only`.
8. AC-3/AC-4/NFR-2: `test_priority_from_scores_through_runner`, `test_changed_importance_table_used_next_run`, `test_no_helpdesk_config_records_created` (xanh ngay vì skeleton T19 đã đủ; là test hồi quy).

## DESIGN_CONFLICT: test cũ ngoài touchpoints, kỳ vọng phải đổi
Tất cả ở `erp_ai/agent/test_agent_runner.py::TestRunnerL1Classification`, do spec T20 (design 3.5, 4.2):
- `test_l1_applies_mapping_confidence_and_hint` (`assertFalse(entry.skipped_fields)`): giờ có note `{"field":"assignee","reason":"cấu hình không có người cho đầu mục A"}` (design 3.5 "cộng `notes`").
- `test_l1_missing_value_reason_logged_on_classify_entry`: `skipped_fields` có thêm note `assignee`.
- `test_l1_empty_route_still_saves_ai_fields_applied_one` và `test_l1_all_fields_skipped_reasons_logged_saves_ai_fields_applied_one`: `actions` phải bằng đúng `[apply_route]`, giờ có thêm `sla_check` ok=false (ticket test không có SLA áp hoặc lệch).
- `test_l1_human_classified_not_overwritten` (`assertFalse(entry.actions)`): spec yêu cầu ghi action `ok=false` + lý do khi (u1) từ chối.
Cần tech-lead cho phép sửa các kỳ vọng này (hoặc giao task riêng).

## Lưu ý
- `value_before/after` giữ dạng phẳng như T19 (test cũ so bằng từng khóa); design 3.5 viết dạng lồng `{"ticket": ...}`. Đổi sang dạng lồng khi T21 thêm `assign`/`task` sẽ phải sửa thêm test cũ ở `test_agent_runner.py`. Chờ quyết định.
- Savepoint `erp_ai_route` bao (u1) + kiểm SLA + cập nhật bản ghi: lỗi khi ghi bản ghi vẫn hoàn tác phiếu và ném lên (giữ test cũ `test_failure_after_tool_rolls_ticket_back_and_keeps_entry`).
