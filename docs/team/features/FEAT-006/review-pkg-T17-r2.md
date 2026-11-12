# Review package FEAT-006 T17, vòng 2 (scoped re-review)

Repo: `/home/miyano/frappe-bench/apps/erp_ai`. FIX_BASE=887fa2c; head=team/FEAT-006-task-17-rework1 (68da7fc).
Lệnh diff (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai diff 887fa2c..team/FEAT-006-task-17-rework1 -- erp_ai`
Touchpoint T17: erp_ai/agent/tools/write_ticket.py, erp_ai/agent/tools/registry.py, erp_ai/agent/tools/test_write_ticket.py.

Finding vòng 1 cần đánh dấu ADDRESSED / NOT ADDRESSED:
1. major | STD-DESIGN-2 | write_ticket.py:55-60 | D/E không bộ phận: lý do "không có bộ phận" từ `decision.notes` bị bỏ, `_existing_values` ghi "ánh xạ không có giá trị" sai. Sửa: khi `decision.agent_group is None` lấy lý do `agent_group` từ `decision.notes` vào `skipped`; thêm `assertEqual(result["skipped"][0]["reason"], "không có bộ phận")`.

Chỉ xét diff sửa. Ghi chú vượt phạm vi cho `deferred`, không mở rộng vòng. Soi: mapping rỗng thật vẫn ra lý do cũ; `_existing_values(wanted)` một đối số ở `route_ticket.py` còn chạy (tham số `reasons` tùy chọn); test đỏ khi bỏ `reasons`.
