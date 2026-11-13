# Review package FEAT-006 T16 (`create_routed_task` và `create_task` đặt `ai_ticket`), vòng 1

Repo: `/home/miyano/frappe-bench/apps/erp_ai`. BASE=24f04a4; head=team/FEAT-006-task-16 (a24b9a2).
Lệnh diff (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai diff 24f04a4..team/FEAT-006-task-16`

Commits: `git -C /home/miyano/frappe-bench/apps/erp_ai log --oneline 24f04a4..team/FEAT-006-task-16` (một commit `a24b9a2`, `feat(route): ... (FEAT-006)`).
Touchpoint T16: erp_ai/agent/tools/route_ticket.py, erp_ai/agent/tools/write_ticket.py, erp_ai/agent/tools/test_route_ticket.py, erp_ai/agent/tools/test_write_ticket.py.

Tiêu chí: dòng T16 của `docs/team/features/FEAT-006/tasks.md` (AC-13 Task có tham chiếu `ai_ticket`, giao đúng người, lỗi chia sẻ ném để runner rollback; NFR-4 mô tả Task không chứa khóa/cấu hình thô; ADR-021 QĐ 2/5), design.md (Task cho C/D; chia sẻ Task qua `assign_to`), plan.md#shared-constraints.
Returns: `write_ticket.py` tách `_ticket_link_html(name)` và `_existing_values(wanted)` (dùng lại, STD-DESIGN-4); `create_task` đặt `ai_ticket`; `route_ticket.create_routed_task(user, ticket_subject, classification, ctx) -> {"ok": True, "task": str} | {"ok": False, "reason": str}`: `subject` cắt 140 ký tự; `ai_ticket`; `description` = đoạn link phiếu + dòng "Độ phức tạp {c}/3, độ quan trọng {i}/3: {lý do}" (`escape_html`); sau `Task.insert()` gọi `assign_to.add` trên Task; không có DocType Task / thiếu quyền tạo / thiếu quyền đọc phiếu -> `ok=false`; lỗi chia sẻ ném `frappe.ValidationError`.
Expect: `TestCreateRoutedTask::test_assignee_without_projects_user_gets_share`, `test_description_escaped_and_has_scores`, `test_sharing_disabled_raises`; `TestCreateTask::test_sets_ai_ticket` (test_write_ticket.py); các test hiện có vẫn xanh.

Điểm cần soi: (1) hợp đồng trả về và `ok=false` cho 3 điều kiện; lỗi chia sẻ KHÔNG bị bắt (kể cả trong `_task_refusal` dùng chung); (2) `description`/`subject` an toàn (escape, cắt 140, không chứa khóa/cấu hình thô, NFR-4); (3) refactor `_ticket_link_html`/`_existing_values`/`_task_refusal`: hành vi `create_task` và `apply_route` không đổi, không lặp mã; (4) test chia sẻ chạy qua `assign_to` thật và quyền thật (người được giao không có Projects User vẫn thấy Task); ba ca từ chối dùng patch: patch có xét đúng `permission_type`/user hay không; (5) mỗi khẳng định đỏ khi bỏ đúng hành vi nó khóa; tên test khớp điều kiểm; (6) `test_architecture` (không `ignore_permissions`/`set_user` trong `agent/tools`; một `doc.save()` HD Ticket ở `apply_route`).
