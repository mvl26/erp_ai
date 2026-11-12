# Review package FEAT-006 T18 (xóa `resolve_ticket_values`, chuyển ca test sang `test_routing.py`), vòng 1

Repo: `/home/miyano/frappe-bench/apps/erp_ai`. BASE=5718e2f; head=team/FEAT-006-task-18 (029890e).
Lệnh diff (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai diff 5718e2f..team/FEAT-006-task-18 -- erp_ai`
Commits: `git -C /home/miyano/frappe-bench/apps/erp_ai log --oneline 5718e2f..team/FEAT-006-task-18` (một commit 029890e).
`git -C /home/miyano/frappe-bench/apps/erp_ai diff --stat 5718e2f..team/FEAT-006-task-18 -- erp_ai`: classification.py -9; routing.py +/-13; test_classification.py -62/+; test_routing.py +56.
Touchpoint T18: erp_ai/agent/classification.py, erp_ai/agent/test_classification.py, erp_ai/agent/test_routing.py; mở rộng chấp nhận bởi tech-lead (vì `routing.py` import và gọi hàm bị xóa): erp_ai/agent/routing.py, chỉ thay lời gọi `resolve_ticket_values` bằng tra thẳng `mapping`, giữ hành vi `decide_route`.

Tiêu chí: dòng T18 của `docs/team/features/FEAT-006/tasks.md` (dòng 130-133): D-12 (R1-R5 chỉ ở một hàm), AC-3. Xóa `resolve_ticket_values`; chuyển `TestResolveTicketValues` thành ca của `TestDecidePriority`/`TestDecideTeam` (cùng giá trị kỳ vọng; không bỏ ca nào); `grep -rn resolve_ticket_values erp_ai/` rỗng.
Danh sách ca cũ để đối chiếu (`git show 5718e2f:erp_ai/agent/test_classification.py`, dòng 201-258, 8 test): test_values_come_from_mapping_not_from_model, test_missing_category_in_mapping_gives_none, test_missing_key_inside_entry_gives_none, test_empty_mapping, test_urgent_prefix_forces_urgent, test_urgent_prefix_overrides_empty_priority_and_missing_category, test_parse_deeply_nested_json_returns_none (đặt nhầm lớp, dev chuyển nguyên văn sang `TestParseClassification`), test_no_urgent_without_bracketed_tag.
Design: design.md cùng thư mục.

Điểm cần soi: (1) đối chiếu từng ca cũ với ca mới: cùng đầu vào và cùng giá trị kỳ vọng, không nới khẳng định (STD-TEST-5), không bỏ ca; (2) `routing.py`: hành vi `decide_route` không đổi (ticket_type, agent_group cho A/B/C/F; D/E dùng bộ phận); (3) không còn tham chiếu `resolve_ticket_values`; import thừa đã bỏ; (4) mỗi ca mới đỏ khi bỏ đúng hành vi nó khóa.
