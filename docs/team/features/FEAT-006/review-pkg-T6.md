# Review package FEAT-006 T6 (ưu tiên R1-R5), vòng 1

Repo: `/home/miyano/frappe-bench/apps/erp_ai`. BASE=4cfd68f; head=team/FEAT-006-task-6 (712b8b7).
Lệnh diff (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai diff 4cfd68f..team/FEAT-006-task-6`
Commit: `git log --oneline 4cfd68f..team/FEAT-006-task-6` → 712b8b7 feat(routing): priority rules R1-R5 in decide_route (FEAT-006)
Stat: erp_ai/agent/routing.py, erp_ai/agent/test_routing.py (mới), erp_ai/agent/test_runner_routing.py (đổi đúng 1 khẳng định).
Touchpoint: dòng T6 của `tasks.md` + MỞ RỘNG 1 file do tech-lead (`erp_ai/agent/test_runner_routing.py`): test T1 mã cứng giá trị giả `priority == "High"` cho phân loại A + importance 3 trong khi R4/AC-3 đòi `Urgent`; kiểm rằng chỉ đúng dòng khẳng định đó đổi, giá trị mới `Urgent` đúng spec (AC-3, R4).
Tiêu chí: T6 (AC-3 36 ca mẫu spec, AC-4 đọc `importance_priority` từ cấu hình, A-2, A-11), design.md mục 3.2/3.3, spec AC-3/AC-4. Phần nhóm/người vẫn giả; `resolve_ticket_values` chưa xóa (T18).
