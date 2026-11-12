# Review package FEAT-006 T8 (chọn người theo đầu mục; needs_task), vòng 1

Repo: `/home/miyano/frappe-bench/apps/erp_ai`. BASE=2851bca; head=team/FEAT-006-task-8 (69aa409).
Lệnh diff (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai diff 2851bca..team/FEAT-006-task-8`
Stat: erp_ai/agent/routing.py, erp_ai/agent/test_routing.py (đúng touchpoint).
Tiêu chí: dòng T8 của `tasks.md` (AC-6, AC-8, AC-14, D-13, A-7), design.md mục 3.2 (thuật toán chọn người) và 3.3, spec.
Điểm cần soi: (1) dev đổi một khẳng định cũ của T7 `TestDecideTeam::test_abcf_team_from_mapping` từ `decision.notes == ()` sang `_team_notes(decision) == []` vì A/B/C/F giờ có note `assignee`: kiểm đây là đổi kỳ vọng theo hành vi mới chứ không nới (STD-TEST-5). (2) Ứng viên đã chọn không hợp lệ thì để trống và ghi note, KHÔNG lùi sang `default`: đối chiếu với design 3.2. (3) câu lý do trong notes không chứa nội dung phiếu thô. (4) dev báo 7 biến thể đột biến đều làm test đỏ.
Bằng chứng dev: `cmd.test` 688 OK.
