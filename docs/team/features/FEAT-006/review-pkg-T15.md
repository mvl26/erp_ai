# Review package FEAT-006 T15 (`assign_owner` và `post_routing_comment`), vòng 1

Repo: `/home/miyano/frappe-bench/apps/erp_ai`. BASE=6b4b9f7; head=team/FEAT-006-task-15 (e3e2500).
Lệnh diff (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai diff 6b4b9f7..team/FEAT-006-task-15`

Commits: `git -C /home/miyano/frappe-bench/apps/erp_ai log --oneline 6b4b9f7..team/FEAT-006-task-15` (một commit `e3e2500`, `feat(route): ... (FEAT-006)`).
Touchpoint T15: erp_ai/agent/tools/route_ticket.py, erp_ai/agent/tools/test_route_ticket.py (đã có từ T14).

Tiêu chí: dòng T15 của `docs/team/features/FEAT-006/tasks.md` (AC-6 đúng 1 ToDo, đúng 1 Notification Log, phiếu không bị chia sẻ; AC-8 comment xin phân công; AC-11 comment `NO_SLA`; ADR-021 QĐ 3), design.md (3.6 các câu cố định; gán người), plan.md#shared-constraints.
Returns: `assign_owner(user, ctx) -> {"ok": True, "assignee": user} | {"ok": False, "reason": str}` (thiếu quyền `read` phiếu -> từ chối; gọi `frappe.desk.form.assign_to.add({"assign_to": [user], "doctype": "HD Ticket", "name": ctx.ticket_name})`, không truyền cờ bỏ quyền); `post_routing_comment(lines, ctx)` (nối bằng xuống dòng thành MỘT comment qua `post_comment`); hằng `ASSIGN_REQUEST`, `NO_SLA` và 3 câu lý do ở design 3.6 (không chứa nội dung phiếu hay cấu hình thô).
Expect: `TestAssignOwner::test_ticket_never_shared_one_todo_one_notification`, `test_no_read_permission_refused`; `TestRoutingComment::test_lines_joined_in_one_comment`; 13 test của T14 vẫn xanh.

Điểm cần soi: (1) đối chiếu từng câu cố định với design 3.6 (nguyên văn, không rò nội dung phiếu/cấu hình thô); (2) "phiếu không bị chia sẻ": `assign_to.add` của Frappe v15 thực sự có chia sẻ hay không và test có khóa được điều đó bằng hành vi thay vì chỉ bằng đối số gọi; (3) quyền `read` kiểm đúng chỗ, đúng user; (4) mỗi khẳng định đỏ khi bỏ đúng hành vi nó khóa; tên test khớp điều kiểm; (5) không lặp mã `post_comment` (STD-DESIGN-4); không `ignore_permissions`/`set_user` trong `agent/tools`.
