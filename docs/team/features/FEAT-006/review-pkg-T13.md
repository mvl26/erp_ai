# Review package FEAT-006 T13 (`site_facts`: 5 phép đọc hệ thống chỉ-đọc), vòng 1

Repo: `/home/miyano/frappe-bench/apps/erp_ai`. BASE=5688f13; head=team/FEAT-006-task-13 (fc10afc).
Lệnh diff (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai diff 5688f13..team/FEAT-006-task-13`

Commit: `fc10afc feat(agent): site_facts read-only system facts (FEAT-006)`

Stat:
```
 erp_ai/agent/site_facts.py      |  42 +++++++++++++++
 erp_ai/agent/test_site_facts.py | 112 ++++++++++++++++++++++++++++++++++++++++
 2 files changed, 154 insertions(+)
```
Touchpoint T13: đúng 2 file trên (cả hai mới).

Tiêu chí: dòng T13 của `docs/team/features/FEAT-006/tasks.md` (AC-6/AC-7a vị từ "đã có người"; AC-13 đã có Task; AC-11/AC-12 SLA đang áp; ADR-019 QĐ 5; ADR-021 QĐ 4) và design.md.
Returns: `ticket_assignments`, `has_linked_task`, `is_active_agent`, `team_exists`, `applied_sla`; module không nằm trong `agent/tools/`, không ToolSpec.
Expect: `TestSiteFacts::test_assignments_include_closed_exclude_cancelled`, `test_has_linked_task_sees_other_owners_task`, `test_is_active_agent_flags`, `test_applied_sla_none_without_sla`, `test_facts_work_under_pinned_agent_roles` ("role `Agent` không đọc được SLA mà hàm vẫn đọc được").

Điểm cần soi: (1) lọc ToDo (Closed gồm, Cancelled loại, đúng reference_type); (2) `has_linked_task` thấy Task của người khác; (3) `applied_sla` đọc đúng hàng HD Service Level Priority theo `priority` của phiếu, None khi không có `sla`; (4) mọi phép đọc qua `frappe.db`/`get_all`, không rò quyền hay đổi trạng thái; (5) test có thật sự khóa được từng hành vi (đột biến nhẩm), và ca ghim role có chứng minh được tiêu chí "Agent không đọc SLA".
