# dev-T23 — Bảng routing dựng từ cấu hình (FEAT-006)

Nhánh: team/FEAT-006-task-23 (từ 1117974). Chạm: prompts.py, runner.py, test_classification.py, test_agent_runner.py.

## Thay đổi
- Xóa `ROUTING_TABLE`; thêm `build_routing_table(mapping, config, names)` (cột như 16.2; A/B/C/F lấy nhóm từ mapping, người từ `assignees` kèm tiền tố; D/E lấy nhóm và trưởng bộ phận từ `departments`; SLA từ `expected_sla`, null = "theo Hạn hoàn thành"; ID không có tên thì hiện ID; rỗng khi không có cấu hình).
- `build_reason_system(prompt_digest, routing_table="")`: rỗng thì bỏ phần routing.
- `runner._reason` dùng `context.category_mapping` và `context.routing_config` (đã nạp sẵn, không đọc lại DB); `get_fullname` cho mọi user trong cấu hình (`_config_users`).

## Đỏ (đúng lý do: hành vi thiếu, hàm/tham số đã tạo trước)
- test_classification: 4 failed (`'a1@x.com' not found in ''`, `'ROUTING-ABC' not found`, `'BẢNG ROUTING' unexpectedly found`, `False is not true`).
- test_agent_runner: 2 failed (`test_reason_system_shows_configured_people`: 'BẢNG ROUTING' not found; `test_request_uses_...`: system khác bảng dựng).

## Xanh
- erp_ai.agent.test_classification: Ran 33 OK; erp_ai.agent.test_agent_runner: Ran 57 OK.
- `--app erp_ai`: Ran 840 tests, OK.
- `grep -rn "ROUTING_TABLE" erp_ai/` -> rỗng.
- pre-commit trên 4 file: sạch (lần đầu ruff tự sửa import/format, chạy lại sạch).
