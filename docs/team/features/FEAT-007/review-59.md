Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 59 — FEAT-007 T59

- Diff: `git diff 58b667411121655d13f8d775710bcdcc44721311..e98a818` (đầu nhánh `team/FEAT-007-task-59` lúc review; merge vào `team/FEAT-007` là `47a487b`)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve

## Vòng 1 — approve

- Range: `58b6674..e98a818` (1 commit, 1 file `erp_ai/agent/test_agent_runner.py`, +11/−0); `erp_ai/agent/test_runner_routing.py` 0 dòng đổi, đúng dự kiến của kế hoạch.
- Bằng chứng của dev: RED `AssertionError: 1 != 0` ở `TestRunnerBaseSettings.test_setup_overrides_stored_auto_assign`, `Ran 67 tests in 13.847s FAILED (failures=4)` (test mới + 3 test `TestRunnerL1Classification` của dòng `baseline:`); GREEN `erp_ai.agent.test_agent_runner` `Ran 67 tests in 13.583s OK`; `erp_ai.agent.test_runner_routing` `Ran 62 tests in 32.699s OK`.

### Phát hiện (chỉ blocker/major)

Không có finding nào ở mức blocker, major hay minor.

### Test có đỏ khi thiếu hành vi không

Có. `setUp` của lớp con ghi 1 trước khi `setUp` của lớp nền chạy; bỏ dòng `auto_assign_enabled=0` (`test_agent_runner.py:90`) thì test đọc lại 1. Giá trị đọc là giá trị mới, không phải cache: `set_single_value` xóa `value_cache` và cache tài liệu (`apps/frappe/frappe/database/database.py:829-832`), `rollback` xóa `value_cache` (`:1214`). Kết quả không phụ thuộc giá trị site đang lưu.

### Review checklist (10)
1. đạt — đúng A-18 (bản sửa tối thiểu), không thừa
2. đạt — chỉ 1 file trong touchpoints, không file mới
3. đạt — RED trước; không skip/xfail/only
4. đạt — không phép khẳng định sẵn có nào đổi (STD-TEST-5, NFR-8)
5. không áp dụng (diff chỉ có test)
6. đạt
7. đạt — không đổi hợp đồng nào
8. đạt
9. đạt — không dependency mới
10. đạt — `test(agent): runner test base pins auto_assign_enabled to 0 (FEAT-007)`, không dòng ghi công AI

## Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| `cmd.test` cả bộ chưa chạy cho task này; test ngoài `RunnerTestBase` dựa vào `auto_assign_enabled` của site vẫn còn hở; dòng `baseline:` chỉ viết lại được sau lần chạy cả bộ | Theo N-6 (`docs/team/journal/FEAT-007.md`) cả bộ chỉ chạy ở mốc M1–M6. Sau merge, tech-lead chạy trên `team/FEAT-007` @ `47a487b`: `erp_ai.agent.test_agent_runner` `Ran 67 tests in 13.581s OK`, `erp_ai.agent.test_runner_routing` `Ran 62 tests in 31.264s OK`, `erp_ai.tests.test_architecture` `Ran 112 tests in 3.047s OK` (5 test của dòng `baseline:` đều xanh). Dòng `baseline:` viết lại ở M1. |
| `team/FEAT-004` sửa cùng file; dòng 90 phải còn sau khi gộp | Đã ghi sẵn trong T56 (`files:` có `test_agent_runner.py`, "dòng `auto_assign_enabled=0` của T59 không mất"). |
| Cache tài liệu mà test nền nạp trong lúc chạy không được `rollback` dọn | Có từ trước diff này (7 khóa của `RunnerTestBase`), ngoài phạm vi T59; đưa vào `deferred`. |
| `cmd.lint` | `pre-commit run --all-files` trên `team/FEAT-007` @ `47a487b`: `ruff-format` đỏ vì định dạng lại `erp_ai/test_change_decision.py` (file của commit `25be823` FEAT-004 trên `develop`, FEAT-007 không sửa). Mọi hook khác `Passed`. Không do T59; ghi là nợ lint của nền, báo team-leader. |

## deferred

- (ngoài phạm vi) cache tài liệu của ERP AI Setting sau `rollback` trong `RunnerTestBase`.
- (nền, không thuộc FEAT-007) `erp_ai/test_change_decision.py` chưa qua `ruff-format` trên `develop`.
