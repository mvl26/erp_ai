# Review package FEAT-006 T17 (`set_classification` dùng chung `decide_route`; `ToolContext.routing_config`), vòng 1

Repo: `/home/miyano/frappe-bench/apps/erp_ai`. BASE=ebe8431; head=team/FEAT-006-task-17 (887fa2c).
Lệnh diff (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai diff ebe8431..team/FEAT-006-task-17`
Commits: `git -C /home/miyano/frappe-bench/apps/erp_ai log --oneline ebe8431..team/FEAT-006-task-17` (một commit 887fa2c).
`git -C /home/miyano/frappe-bench/apps/erp_ai diff --stat ebe8431..team/FEAT-006-task-17`: registry.py +1; test_write_ticket.py +70; write_ticket.py +24/-3.
Touchpoint T17: erp_ai/agent/tools/write_ticket.py, erp_ai/agent/tools/registry.py, erp_ai/agent/tools/test_write_ticket.py.

Tiêu chí: dòng T17 của `docs/team/features/FEAT-006/tasks.md` (dòng 125-128): AC-3 (cùng ưu tiên qua mọi đường ghi), ADR-019 QĐ 4, D-14. `ToolContext` thêm trường cuối `routing_config: dict | None = None` (`TOOL_MODULES` không đổi); `_mapped_values` gọi `decide_route(...)` với `department=None`; chỉ dùng `ticket_type`/`agent_group`/`priority`; schema `set_classification` không đổi.
Expect: `TestSetClassification::test_same_priority_as_route`, `test_de_skips_team_without_department` xanh; test cũ của file vẫn xanh.
Design: design.md (cùng thư mục), plan.md#shared-constraints.

Điểm cần soi: (1) kết quả `set_classification` và `route` cùng ưu tiên với cùng đầu vào (AC-3), `department=None` đúng; (2) `resolve_ticket_values` không còn được import ở file này (xóa hàm là T18); (3) mỗi khẳng định đỏ khi bỏ đúng hành vi nó khóa; (4) `test_architecture`, STD-DESIGN-4 (không lặp R1-R5).
