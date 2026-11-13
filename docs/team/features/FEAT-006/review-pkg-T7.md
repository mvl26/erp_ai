# Review package FEAT-006 T7 (chọn nhóm A/B/C/F theo ánh xạ, D/E theo bộ phận), vòng 1

Repo: `/home/miyano/frappe-bench/apps/erp_ai`. BASE=686aa3f; head=team/FEAT-006-task-7 (cb7c008).
Lệnh diff (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai diff 686aa3f..team/FEAT-006-task-7`
Commit: cb7c008 feat(routing): chọn nhóm theo ánh xạ (A/B/C/F) và bộ phận (D/E) (FEAT-006)
Stat: erp_ai/agent/routing.py, erp_ai/agent/test_routing.py (đúng touchpoint).
Tiêu chí: dòng T7 của `tasks.md` (AC-5, A-14), design.md mục 3.2 (thuật toán chọn nhóm; thứ tự lý do bỏ qua; câu cố định), spec AC-5. Ngoài yêu cầu dev tự làm: `RouteDecision.notes` đổi từ list sang tuple theo design 3.2; A/B/C/F với nhóm ánh xạ rỗng giờ trả `agent_group=None`; A/B/C/F không gọi `team_exists`/`is_excluded_team`, chỉ D/E kiểm. Hãy đối chiếu ba điểm này với design.md 3.2/AC-5 (đúng/sai spec?).
`cmd.test` của dev: 679 test, OK (nền đã gồm T4+T5).
