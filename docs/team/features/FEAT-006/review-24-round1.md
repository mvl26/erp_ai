# Review T24 vòng 1 — request-changes

Diff: `git -C /home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/feat-006 diff 9135b85..team/FEAT-006-task-24` (8439972). Mã sản xuất không đổi. Checklist 10/10; lớp 1: đủ 8 test, trong touchpoint; AC-9 và AC-16 đạt; NFR-4 và AC-17 chưa đủ.

## Findings (nguyên văn từ reviewer)

1. major | STD-TEST-2 | erp_ai/agent/test_runner_routing.py:314 | confirmed
   - Problem: the NFR-4 test puts the fake key only in a credential row. Nothing in this run reads that row. `RunnerTestBase` patches `erp_ai.gateway.call_model` (test_agent_runner.py:94), and no agent code reads credentials (grep for `get_password|api_key|CREDENTIAL_DOCTYPE` in erp_ai/agent finds nothing). The test can only go red if someone writes code that reads credentials. The mutations in dev-T24 paste the key as a literal into constants, which does not reflect a real leak.
   - Uncovered risk: design 3.6 says the comment and log must not contain raw configuration. The run does read `routing_rules` (runner.py:115) and passes it through `ctx.routing_config`. If code echoes `routing_rules` or a value from it into the comment, `skipped_fields`, `error` or the Task, the test stays green.
   - Fix: also put FAKE_KEY into inputs the run really reads, for example a key in `assignees.*.prefixes` and a broken-`routing_rules` case (the `BAD_ROUTING_ERROR` path, which writes the `error` column). Capture `frappe.logger(LOGGER_NAME)` (the route info line and the SLA warning, "nhật ký") plus the `self.log_error` mock, and assertNotIn on each.

2. major | STD-TEST-2 | erp_ai/agent/test_runner_routing.py:638 (AssignTestBase.setUp), 693, 727, 846 | confirmed
   - Problem: AC-17 (spec, and design line 424) says every success case of AC-2..AC-13 runs under the pinned roles. The new test only covers a C ticket plus a comment ticket. `AssignTestBase` and `RoutingTestBase` do not call `pin_agent_roles`, so TestRoutingAssign, TestRoutingNoOverride, TestRoutingSla, TestRoutingUnit and the old TestRoutingEndToEnd/TestRoutingLog tests still run with the site's ~99 roles, System Manager included.
   - Concrete gap: the Assignment Rule path (`test_team_rule_assigns_bot_does_not`, AC-6) and the SLA check have no success case under pinned roles.
   - Fix: call `pin_agent_roles(self)` in `AssignTestBase.setUp`, or in `RoutingTestBase.setUp` after the rollback cleanup, and run the file again. If you decide this belongs to the earlier tasks, open a separate task, but AC-17 cannot be accepted until it is done.

minor (dev tự quyết):
- (a) STD-DESIGN-4: `_configure_c` mức module (dòng 106) nhân đôi `TestRoutingTask._configure_c` (dòng 930); khác duy nhất `auto_assign_enabled=1` mà `AssignTestBase.setUp` đã đặt → xóa method, gọi hàm module.
- (b) Dòng 1264 so lý do với `REASON_TASK_EXISTS` nhập từ runner (mã đang test) → kiểm literal.
- (c) AC-9: `if stored_at:` (dòng 1326) khiến kiểm SLA phụ thuộc site có SLA mặc định; `sla` ("SLA do Helpdesk chọn") không được khẳng định.
- (d) `_schema_keys` (test_registry.py:94) không đi qua `anyOf`/`oneOf`/`additionalProperties`/`enum` (khoảng trống cho tool tương lai).
- (e) AC-9: priority "High" vừa là mapping vừa là kết quả R-rule nên không phân biệt được nguồn.

## Cannot verify (tech-lead xử lý)

- Site `miyano` có SLA mặc định Helpdesk không (nếu không, kiểm ngày dòng 1326 không kiểm gì) → dev phải khẳng định điều kiện tiên quyết (không dùng `if stored_at:` im lặng).
- `value_before` chỉ có `"ticket"` còn design 3.5 liệt kê `assign`/`task` cho cả before và after: mã (runner.py:481) coi thiếu khóa là "trống trước" — câu hỏi thiết kế, ghi cho designer.
- Hàng test-plan design 493 ("gieo vào credential") nên mở rộng thành "mọi đầu vào cấu hình mà lần chạy đọc" → designer.
