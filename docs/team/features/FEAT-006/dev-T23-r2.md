# Dev T23 round 2 (rework of review-23-round1)

Branch `team/FEAT-006-task-23-rework1` (from team/FEAT-006-task-23, which is checked out in another worktree). Only tests changed; no production code change (no real bug found).

| Finding | Change | Test | Mutation -> red -> revert -> green |
|---|---|---|---|
| major 1: E row unasserted, `team` equals department name, no merge case | Fixture: 3 departments, teams "Nhóm KT" (Kế toán, Mua hàng share it), "Nhóm Kho"; full D and E rows asserted (team dedup, `"; ".join` of 3 heads) | `test_classification.TestPrompts.test_routing_table_shows_configured_people` | `("D","E")` -> `== "D"`: FAIL on the E row. Dict key instead of `d["team"]`: FAIL on the D row. Reverted: 34 OK |
| major 2: `_config_users` prefixes/head not covered at runner level | Three `make_active_agent` users (A default, B prefix, department head); all three fake names in `system`, no raw email in a cell | `test_agent_runner.TestRunnerReasoning.test_reason_system_shows_configured_people` | Remove prefixes line: FAIL "Tên của <email> not found". Remove head line: same FAIL. Reverted: 57 OK |
| minor: C row | `| C | IT | - | Medium | 60 phút / 1440 phút |` | same test as major 1 | - |
| minor: `_cell` | New `test_routing_table_cell_escapes_pipe_and_newline` (`|` -> `/`, newline -> space, 6 pipes per row) | new test | - |
| minor: tight before/after | `table2 == table1.replace("Người A1", "Người Mới")` | same test as major 1 | - |

Final: `--app erp_ai` -> Ran 841 tests, OK. `pre-commit run --files` both files: all Passed.
