# Review package FEAT-006 T13, vòng 2 (scoped re-review)

Repo: `/home/miyano/frappe-bench/apps/erp_ai`. FIX_BASE=fc10afc; head=team/FEAT-006-task-13-rework1 (388f562).
Lệnh diff vòng sửa (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai diff fc10afc..team/FEAT-006-task-13-rework1`
Diff toàn task: `git -C /home/miyano/frappe-bench/apps/erp_ai diff 5688f13..team/FEAT-006-task-13-rework1`
Touchpoint T13: erp_ai/agent/site_facts.py, erp_ai/agent/test_site_facts.py.

Findings vòng 1 (nguyên văn; đánh dấu ADDRESSED / NOT ADDRESSED):
1. major | STD-TEST-2 | test_site_facts.py:40-54 | Bỏ bộ lọc `reference_type: "HD Ticket"` trong `ticket_assignments` (site_facts.py:15) mà mọi test vẫn xanh: decoy ToDo duy nhất khác `reference_name`, không khác `reference_type`. | Thêm ToDo mồi `reference_type` khác (ví dụ "Task"), `reference_name=self.ticket`, status Open; kỳ vọng giữ `[(open_user, rule), (closed_user, None)]`.
2. minor 1: bộ lọc `parent=sla` của `applied_sla` chỉ được dữ liệu có sẵn của site bảo vệ; gieo SLA mồi cùng `priority` khác số giờ.
3. minor 2: `test_facts_work_under_pinned_agent_roles` không kiểm tiền đề; khẳng định `frappe.has_permission("HD Service Level Agreement", "read", user=AGENT_USER)` là False trước.
4. minor 3: `order_by="creation, name"` chưa được khóa (assertCountEqual); chốt thứ tự; docstring đầu module nói "frappe.db" trong khi dùng `get_all`; tên `test_has_linked_task_sees_other_owners_task` khẳng định nhiều hơn điều kiểm.

Chỉ chấm phạm vi `FIX_BASE..HEAD`; ghi chú ngoài phạm vi vào `deferred`.
