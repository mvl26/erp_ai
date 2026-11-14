Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 68 — FEAT-004 T68

Tech-lead chép từ tin trả về của reviewer (reviewer không ghi file ở lượt này).

- Diff vòng 1: `git diff 06d3643..ec511e0` (nhánh `team/FEAT-004-task-68b`, 1 commit, 1 file `erp_ai/tests/test_architecture.py`, +651/−0)
- Diff vòng 2: `git diff ec511e0..109970f` (nhánh `team/FEAT-004-task-68c`, 1 commit, cùng file, +146/−4)
- Vòng: 2
- Verdict: approve (vòng 1: request-changes)

## Vòng 1 — request-changes
- Layer 1: 4 trong 5 luật được thêm, mỗi luật có ca bị bắt, ca sạch và test trên cây thật; luật cũ không đổi (diff không xóa dòng nào); chỉ sửa trong touchpoint.

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-8 | erp_ai/tests/test_architecture.py:3855-3868, 3877 | Luật coi "một hàm cấp" là "một hàm đọc `GRANT_TABLE`": thân `_unrestricted_specs` của `6d90e79` (lọc `_all_specs()` theo `spec.group`, không đọc bảng) dưới tên mới lọt; phần runner chỉ bắt khi tên lời gọi có chữ "schema"; `execute_tool` không được kiểm dù ADR-023 QĐ 4 ghi "runner và execute_tool chỉ gọi một hàm" | `_all_specs()` chỉ được gọi trong hàm đọc `GRANT_TABLE` duy nhất; `get_tool_schemas`, `_grants_group`, `execute_tool` chỉ tới spec qua hàm đó; thêm ca bị bắt bằng thân cũ dưới tên mới |
| major | STD-TEST-8 | erp_ai/tests/test_architecture.py:3824 (dùng ở 3839, 3906) | `_node_texts` trả cả chuỗi và luật so bằng tuyệt đối, nên tên ở dạng đường dẫn có chấm (`frappe.get_attr("erp_ai.agent.agent_write_guard.allow_agent_write")`, mục `hooks.py`) lọt; ADR-023 ghi "grep tên cờ ở nơi khác → finding" | Khớp khi tên là một đoạn của chuỗi có chấm; thêm ca "opener as dotted path", "removed name as dotted path" |

minor | — | — | 3 điểm nhỏ: `_string_shape` không theo `"/".join`, `.format`, `%`; phần loại trừ docstring chưa có fixture; phép thử `"schema" in name.lower()` có thể bắt nhầm sau này | dev's call

### Không kiểm được từ diff (vòng 1)
- Luật 3 (`check_site_api_has_no_handwritten_app_doctype_set`) không có dưới tên đó; dev dựa vào `_site_api_deny_violations` trong `check_tool_never_saves_proposal` (T59), có ca bị bắt và ca sạch. Tech-lead phán (round 75): nhận việc dùng lại (STD-DESIGN-4), không cần hàm bọc.
- RED/GREEN chỉ từ lời dev: RED 4 luật stub `Ran 177 tests ... FAILED (failures=46)`; GREEN `Ran 177 tests ... OK`.

## Vòng 2 — approve (chỉ diff sửa)
| Phát hiện vòng 1 | Trạng thái | Chứng cứ |
|---|---|---|
| major STD-TEST-8 (một hàm cấp) | ADDRESSED | `test_architecture.py:3845-3880, 3896-3899, 3928-3929`; ca "6d90e79 _unrestricted_specs body under a new name" (`:7185-7192`), "execute_tool skips", "_grants_group skips", "execute_tool missing", "tool modules read outside the spec source", "spec source reached from the runner", "spec source imported elsewhere" |
| major STD-TEST-8 (chuỗi có chấm) | ADDRESSED | `test_architecture.py:3829`; ca "removed name as dotted path" (`:7180`), "opener as dotted path" (`:7291`), "opener as hooks.py entry" (`:7295`); 2 ca sạch ghim loại trừ docstring |

- Bằng chứng của dev: RED (ca mới trên luật cũ) `Ran 177 tests ... FAILED (failures=11)` (9 ca hàm cấp + 2 ca cờ ghi); GREEN `Ran 177 tests in 20.227s OK`.
- Phát hiện mới (blocker/major): không có.

minor | — | — | 3 điểm nhỏ: phép kiểm `TOOL_MODULES` (`:3866`) cho `owner is None` nên một bộ liệt kê spec trong thân lớp lọt; nhánh "hàm đọc không lấy spec từ `_all_specs()`" (`:3858-3859`) chưa có ca bị bắt; docstring `:3883-3886` chưa nhắc luật mới | dev's call

### Không kiểm được từ diff (vòng 2)
- Reviewer không chạy test. Tech-lead đã chạy sau merge `b545bab`: `cmd.test_one` test_architecture `Ran 177 tests in 20.166s` / `OK` → `load_product_sources()` đúng là bỏ file test (nếu không `test_registry.py` đã làm luật đỏ).

## Deferred
- Import thẳng `TOOLS` của một module tool (ví dụ `from erp_ai.agent.tools.site_api import TOOLS` trong `runner.py`) tới được spec mà không qua tên nào được canh; Ràng buộc ADR-023 không nêu dạng này. Cho architect cân nhắc.
- 3 minor vòng 2 ở trên.
