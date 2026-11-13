# Review T21 vòng 1 — request-changes (nguyên văn từ reviewer)

BASE=b6d3504, head 8de1908 (`team/FEAT-006-task-21`).

- major | STD-TEST-8 | erp_ai/agent/test_runner_routing.py:643,667 (runner.py:344) | Both failure tests use a mock that raises before writing anything, and neither checks that the (u1) ticket fields survive. So two mutations stay green: removing the rollback to `erp_ai_route_unit`, or rolling back to the outer `erp_ai_route` instead (which loses (u1) while the log still says `applied=1`). That leaves tech-lead's point (2) unproven. | Give the mock a side_effect that first calls the real `assign_to.add`, then raises. Assert ToDo == [], the ticket's `agent_group`/`priority` are still the (u1) values, and `applied == 1`.
- major | STD-TEST-2 | erp_ai/agent/test_runner_routing.py:611 (runner.py:470) | `comment=` in the info line is only ever asserted as 0, here and in the old test, so hard-coding `comment=0` stays green. | Assert the info line in a test that posts a comment (for example agent account or NO_SLA) and expect `comment=1`.
- major | STD-TEST-2 | erp_ai/agent/test_runner_routing.py:626 | AC-6 Amendment requires the log to carry the rule name, but the test only does `assertTrue(action["rule"])`. Writing any non-empty value (the user, the ticket name) stays green. | `assertEqual(action["rule"], frappe.db.get_value("HD Team", team, "assignment_rule"))`
- minor | — | — | 2 small points: design 4.2 says each unit uses the savepoint name `erp_ai_route`, but the code uses a separate nested name `erp_ai_route_unit`. That is correct, since MariaDB replaces a savepoint of the same name, so design.md should be updated. Also, `test_team_rule_assigns_bot_does_not` and `test_rule_assignment_in_route_save_kept` mostly duplicate each other.

Cannot verify (tech-lead xử lý):
- Rollback về savepoint đơn vị không hủy callback `after_commit`/realtime mà `assign_to.add` đăng ký; assign lỗi có thể vẫn gửi notify/realtime sau commit. Dev kiểm `frappe/desk/form/assign_to.py` và `notification_log`/`notify`, báo kết luận một dòng; chỉ sửa mã nếu có rò dữ liệu/ToDo ma và sửa nằm trong touchpoint.
- Test chưa chạy bởi reviewer; dev dán đầu ra.

Rulings tech-lead: minor savepoint lồng: giữ mã (đúng kỹ thuật); ghi vào deferred "design 4.2 cần ghi tên `erp_ai_route_unit`" cho team-leader/designer, không sửa design.md ở đây. Minor trùng test: dev tùy ý, không bắt buộc.
