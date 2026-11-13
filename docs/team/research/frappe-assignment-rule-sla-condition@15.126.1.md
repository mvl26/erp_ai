# Cache: Assignment Rule, assign_to, SLA condition — frappe 15.126.1 / helpdesk 15.1.0

Date: 2026-11-12. Nguồn chi tiết: `docs/team/features/FEAT-006/research.md` (mục 1–3). Đọc mã đã cài.

- `assign_to.add` chỉ kiểm quyền **read** của người gọi trên tài liệu; ToDo và Notification Log insert `ignore_permissions` (`frappe/desk/form/assign_to.py:85-86,114,140-148`).
- Assignment Rule chạy ở `on_update` (cả insert và save), sau method controller (`frappe/hooks.py:174`, `model/document.py:1506-1526`). Có ToDo không-Cancelled → rule chỉ gỡ ToDo mang tên chính nó; ToDo gán tay (không `assignment_rule`) chặn rule gán thêm (`assignment_rule.py:223-232,302-329`).
- Helpdesk gỡ mọi người khi đổi `agent_group` nếu người hiện tại không thuộc nhóm mới và nhóm mới có rule bật + user (`hd_ticket.py:428-482`).
- SLA `condition`: `safe_eval` với context `{"doc": ticket.as_dict(), "frappe": utils}` → viết `doc.<field>`, đọc được Custom Field; lỗi đánh giá KHÔNG bị bắt → chặn lưu phiếu (`hd_service_level_agreement/utils.py:12-52`, `helpdesk/utils.py:163-174`). SLA phải có priority của phiếu.
- ERPNext 15.83.0 Task: không có Link tới HD Ticket (`issue` → `Issue`).

## Sources

- https://github.com/frappe/frappe/blob/2e9ecdc03fa5b5b8d1ba05224a1aff7dad832bd0/frappe/automation/doctype/assignment_rule/assignment_rule.py (truy cập 2026-11-12)
- https://github.com/frappe/frappe/blob/2e9ecdc03fa5b5b8d1ba05224a1aff7dad832bd0/frappe/desk/form/assign_to.py (truy cập 2026-11-12)
- https://github.com/frappe/helpdesk/blob/a1858964f63a9deb287a6577ca785cc90800e402/helpdesk/helpdesk/doctype/hd_service_level_agreement/utils.py (truy cập 2026-11-12)
- https://github.com/frappe/helpdesk/blob/a1858964f63a9deb287a6577ca785cc90800e402/helpdesk/helpdesk/doctype/hd_ticket/hd_ticket.py (truy cập 2026-11-12)
