# Review package FEAT-006 T5 (policy: nhóm bị loại trừ, công tắc tự gán), vòng 1

Repo: `/home/miyano/frappe-bench/apps/erp_ai`. BASE=b1af21f; head=team/FEAT-006-task-5 (0f84aff).
Lệnh diff (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai diff b1af21f..team/FEAT-006-task-5`
Commit: 0f84aff feat(policy): is_excluded_team and auto_assign_enabled (FEAT-006)
Stat: erp_ai/agent/policy.py, erp_ai/agent/test_policy.py (đúng touchpoint).
Tiêu chí: dòng T5 của `tasks.md` (AC-5 `excluded_teams` cùng chuẩn hóa, AC-7c công tắc, ADR-019 QĐ 6), design.md. `can_send_ticket` được tái cấu trúc gọi `is_excluded_team`: kiểm hành vi cũ không đổi (test cũ nguyên văn). Công tắc chỉ đọc ở policy.
