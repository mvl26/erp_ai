# dev-R2: rework 1, mục 2 + 5 + 6 (FEAT-006, T21)

Nhánh `team/FEAT-006-rw1-r2` (từ `team/FEAT-006` 91d8903). Chỉ sửa `erp_ai/agent/test_runner_routing.py`. Không đổi mã sản xuất (mọi phá hoại đã hoàn tác bằng `git checkout`).

## Mục 2 (AC-11): 4 ca không-SLA của `TestRoutingSla`
- Thay đổi: thêm helper `_assert_saved_with_priority` (priority phiếu == "Urgent" viết cứng: đầu mục A, quan trọng 3, A-11; và `entry.applied == 1`) và đếm `HD Service Level Agreement` trước = sau. Thêm vào cả 4 ca (`test_no_sla_one_warning_one_comment`, `test_no_sla_one_action_one_warning_and_one_line_gathered`, `test_no_sla_and_assign_request_share_one_comment`, `test_switch_off_no_sla_still_one_comment`).
- Đỏ (tạm thêm vào `runner._check_sla`, nhánh không SLA, `frappe.db.set_value(..., "priority", "Low")`): 4 ca FAIL, `AssertionError: 'Low' != 'Urgent'`.
- Đỏ (tạm thêm vào cùng chỗ một bản sao SLA `frappe.copy_doc(...).insert()`): 4 ca FAIL, `AssertionError: 3 != 2` (đếm SLA).
- Xanh sau hoàn tác: 61 tests OK.

## Mục 5 (AC-7(c)): `TestRoutingNoOverride::test_switch_off_no_todo_no_task`
- Thay đổi: thêm `apply_route["ok"]` True, và `agent_group == self.team`, `priority == "Urgent"` trên phiếu.
- Đỏ (tạm thêm `values.pop("priority", None)` vào `route_ticket.apply_route`): FAIL `Tuples differ: (team, 'Medium') != (team, 'Urgent')`.
- Xanh sau hoàn tác: OK.

## Mục 6 (AC-14): `TestRoutingAssign::test_changed_default_person_assigned_next_run`
- Thay đổi: mapping có A và B cùng về `self.team`; chỉ người mặc định của B đổi (A giữ `self.person`); phiếu kế tiếp được phân loại `CLASSIFY_B2` (đầu mục B); khẳng định phiếu 2 gán `other`, phiếu 1 vẫn `self.person`, phiếu 2 về đúng nhóm.
- Đỏ (tạm sửa `routing._category_assignee` để B lấy người của A): FAIL `Lists differ: ['...ad43334b...'] != ['...5f888a4e...']`; chỉ đúng ca này đỏ.
- Xanh sau hoàn tác: OK.

## Kiểm tra cuối
- `bench --site miyano run-tests --module erp_ai.agent.test_runner_routing`: Ran 61 / OK.
- `bench --site miyano run-tests --app erp_ai`: Ran 883 / OK.
- `pre-commit run --files erp_ai/agent/test_runner_routing.py`: tất cả Passed (ruff import, lint, format).
- Không skip/xfail; không đụng mã sản xuất.
