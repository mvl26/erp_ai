# Review package FEAT-006 T14 (`apply_route` đầy đủ: quyền, từ chối, before/after, SLA do Helpdesk chọn), vòng 1

Repo: `/home/miyano/frappe-bench/apps/erp_ai`. BASE=b74303f; head=team/FEAT-006-task-14 (2f639c0).
Lệnh diff (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai diff b74303f..team/FEAT-006-task-14`

Commit: `2f639c0 feat(route): apply_route bỏ trường thiếu quyền, test quyền/từ chối/SLA Helpdesk (FEAT-006)`

Stat:
```
 erp_ai/agent/tools/route_ticket.py      |   6 +-
 erp_ai/agent/tools/test_route_ticket.py | 294 ++++++++++++++++++++++++++++++++
 2 files changed, 299 insertions(+), 1 deletion(-)
```
Touchpoint T14: đúng 2 file trên (`test_route_ticket.py` mới). Bản khung `apply_route` có từ T1 (đọc `git show team/FEAT-006:erp_ai/agent/tools/route_ticket.py`).

Tiêu chí: dòng T14 của `docs/team/features/FEAT-006/tasks.md` (AC-2 user `Agent` đọc được 3 trường; AC-10 SLA theo `condition`, ca `>=` ở `L0` và phiếu mới; AC-7b từ chối khi người đã phân loại; AC-16 before/after, `ok=false` kèm lý do; NFR-2), design.md và plan.md#shared-constraints (một `doc.save()` HD Ticket; `route_ticket.py` không `TOOLS`/`ToolSpec`).
Returns: kiểm `doc.has_permission("write")` và `has_permlevel_access_to(field, "write")` từng trường; thiếu quyền ghi phiếu hoặc `ai_classified_by` là người -> `ok=false`; thiếu quyền một trường -> bỏ trường, ghi `skipped`; `priority`/`agent_group`/`ticket_type` chỉ ghi giá trị có trên site; `before`/`after` đúng các trường đã đổi; luôn một `doc.save()` kể cả khi E không có nhóm/ưu tiên; không bắt ngoại lệ của `save`.
Expect: `TestApplyRoute::test_scores_written_readable_by_agent_role_user`, `test_human_classified_refused`, `test_missing_field_permission_skipped`, `test_e_ticket_still_saved_with_scores`; `TestSlaFromHelpdesk::test_sla_chosen_by_complexity_condition`, `test_ge_condition_saves_l0_and_new_ticket`. Ca thành công chạy dưới `pin_agent_roles`; test SLA chạy qua Helpdesk thật.

Điểm cần soi: (1) toàn bộ hợp đồng `apply_route` đối chiếu với tiêu chí, không chỉ 6 dòng đổi: `before`/`after` chỉ trường đã đổi, `skipped` có lý do không lộ nội dung, thứ tự kiểm quyền; (2) cách xử lý thiếu quyền ở hai trường dấu `ai_classified_by`/`ai_updated_at` (từ chối cả lần ghi) so với trường điểm/định tuyến (bỏ qua trường): có khớp tiêu chí và design không; (3) mỗi test có khóa được hành vi (đột biến nhẩm), nhất là các ca bật tới ngay ở lần chạy đầu vì khung T1 đã có hành vi đó; (4) ca `test_missing_field_permission_skipped` vá `has_permlevel_access_to` thay vì dùng role thật: có chấp nhận được; (5) SLA có thật sự do Helpdesk chọn (không giả lập), ca `>=` ở `L0` và phiếu mới.
