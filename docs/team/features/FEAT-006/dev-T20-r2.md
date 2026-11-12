# dev T20 rework 1 (vòng 2/3)

Nhánh `team/FEAT-006-task-20-rework1` trên 581a6b3. Chạy từ worktree `agent-a30990baacbbf2528`.

| Finding | Thay đổi | Test phủ | Bằng chứng |
|---|---|---|---|
| major 1 (STD-TEST-6) | `test_agent_runner.py`: helper `_slow_sla_action` patch `site_facts.applied_sla` với fact cố định (`resolution_s=86400`), kỳ vọng dựng từ fact + `make_routing_rules()` | `test_l1_empty_route_still_saves_ai_fields_applied_one`, `test_l1_all_fields_skipped_reasons_logged_saves_ai_fields_applied_one` | RED: nhân đôi `resolution_time` của SLA "Standard" thì test cũ đỏ (`2880 phút` vs `1440 phút`). GREEN: `test_agent_runner` Ran 56 OK |
| major 2 (STD-TEST-2) | `test_broken_sla_condition_stops_route_cleanly` khẳng định action = `["apply_route"]`, `logger.warning` không gọi, `_route` trả `[]` | cùng test | Đột biến bỏ ` if result else None` ở `_route`: FAIL `test_broken_sla_condition_stops_route_cleanly` (kèm 2 ERROR ở TestRoutingUnit). Khôi phục: OK |
| major 3 (STD-TEST-8) | test mới `test_apply_exception_keeps_earlier_error_and_adds_its_own` (routing_rules hỏng + `apply_route` ném lỗi; cả `BAD_ROUTING_ERROR` và `route apply_route: ValueError` có mặt) | cùng test | Đột biến `updates["error"] = "; ".join(errors)`: FAIL `test_apply_exception_keeps_earlier_error_and_adds_its_own`. Khôi phục: OK |
| minor 1 | `runner.py`: bỏ `lines=` khỏi dòng info (design 4.2 dòng 296 không có), bỏ tham số `lines` của `_log_route_summary`. Test khẳng định không có `lines=`, `applied=1`, `sla="ok"`, run_id | `test_route_info_line_has_codes_only` | RED: `ValueError: too many values to unpack (expected 5)`; GREEN sau sửa |
| minor 2 | khẳng định logger `LOGGER_NAME` và lý do `NO_SLA_REASON` (action và warning) | `test_no_sla_one_action_one_warning_and_no_sentence_posted_yet`, `test_route_info_line_has_codes_only` | routing: 26 OK |
| minor 3 | ca nhánh `skipped`: routing_rules hỏng, không action `sla_check`, không warning, info `sla=skipped` | `test_broken_routing_rules_skip_sla_check_and_log_skipped` | routing: 26 OK |
| minor 4, 5 | bỏ qua theo chỉ đạo | | |

## Kiểm after_commit (AC-18)
Kết luận: `rollback(save_point=...)` không xóa hàng đợi `after_commit`, nhưng các callback do `doc.save()` HD Ticket xếp hàng chỉ là realtime `doc_update`/`list_update` (frappe `notify_update`) và enqueue chỉ mục tìm kiếm; helpdesk không có hook `HD Ticket` nào xếp callback ghi dữ liệu; `notifications.py` chỉ liên quan reaction của Comment. Không rò dữ liệu, không sửa mã.

## Lệnh và đầu ra
- `bench --site miyano run-tests --module erp_ai.agent.test_runner_routing` -> `Ran 26 tests ... OK`
- `bench --site miyano run-tests --module erp_ai.agent.test_agent_runner` -> `Ran 56 tests ... OK`
- `PYTHONPATH="$R" bench --site miyano run-tests --app erp_ai` -> `Ran 807 tests in 140.144s ... OK`
- `pre-commit run --files` ba file sửa: tất cả Passed.

## Concerns
- Realtime `doc_update`/`list_update` và chỉ mục tìm kiếm vẫn được kích sau commit khi (u1) bị rollback: vô hại (làm mới giao diện, lập chỉ mục trạng thái hiện tại), nhưng ghi lại để biết.
- Giữ ruling: (u1) bị từ chối/ném lỗi không ghi `skipped_fields` (deferred).
- Placeholder `assigned/task/comment` trong dòng info để T21.
