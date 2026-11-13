# dev-T17 — FEAT-006

Nhánh `team/FEAT-006-task-17` (BASE ebe8431), commit 887fa2c. Files: erp_ai/agent/tools/write_ticket.py, registry.py, test_write_ticket.py (đúng touchpoint).

## RED (module erp_ai.agent.tools.test_write_ticket, 36 test)
- `TestSetClassification.test_de_skips_team_without_department`: `AssertionError: 'T25 Nhóm' != None` (agent_group vẫn bị ghi từ ánh xạ).
- `TestSetClassification.test_same_priority_as_route`: `AssertionError: 'Medium' != 'Urgent'` (importance 2 chưa tính).
- failures=2, đỏ do thiếu hành vi.

## GREEN
- Cùng lệnh: `Ran 36 tests ... OK` (sau cả lần ruff-format).
- `cmd.test` toàn app trên đầu nhánh: `Ran 782 tests in 132.865s` / `OK`.
- pre-commit --files 3 file: tất cả Passed (ruff-format sửa 1 file ở lần chạy đầu, lần hai Passed).

## Thay đổi
- `ToolContext.routing_config: dict | None = None` (trường cuối).
- `_mapped_values` gọi `decide_route(...)` với `complexity/importance` từ phiếu; chỉ dùng `ticket_type`/`agent_group`/`priority`; `department` không truyền (None). Schema không đổi.

## Seen but not touched
- Hook cảnh báo STD-NAME-5 vì dòng Co-Authored-By trong thân commit; dòng đầu đúng định dạng.
