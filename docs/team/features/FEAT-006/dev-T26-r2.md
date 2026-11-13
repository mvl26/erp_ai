# dev T26 vòng sửa 2/3 (FEAT-006)

Nhánh `team/FEAT-006-task-26-rework1` (từ 4ad5b17; `team/FEAT-006-task-26` đang checkout ở worktree khác). Chỉ sửa `erp_ai/tests/test_architecture.py`; mã sản xuất không đổi.

## Đỏ trước khi sửa máy quét (đúng lý do: máy quét bỏ sót)

Thêm ca tự kiểm trước, chạy `erp_ai.tests.test_architecture`: `Ran 97 tests` `FAILED (failures=24)`, tất cả `AssertionError: 0 not greater than 0 : scanner missed the violation`, ví dụ:
- `doc.assign_agent('u')`, `frappe.get_doc('HD Ticket', t).assign_agent(u)`, `getattr(doc, 'assign_agent')`
- `doc.db_update()` trong route_ticket.py (cả ngoài lẫn trong `apply_route`)
- `doc.set('response_by', 1)`, `F = 'resolution_by'`, `FIELDS = ('response_by', 'x')`, `F = 'response_by'; doc.set(F, v)`
- `frappe.get_doc('ToDo').insert()`, `handler=apply_route` trong module tool khác, `_assign` trong authority.py ngoài hàm cho phép.

## Finding -> thay đổi -> test phủ

| Finding | Thay đổi | Test phủ |
|---|---|---|
| major 1 | `ASSIGN_CALL_SUFFIXES` thêm `assign_agent`; thêm cờ hằng chuỗi `"assign_agent"` (getattr) | `test_assign_to_scanner_catches_every_way_to_call_it_outside_route_module` |
| major 2 | `check_route_module_single_ticket_save` cấm mọi `db_update` trong route_ticket.py; `TOOL_FORBIDDEN_CALL_SUFFIXES` thêm `db_update` | `test_route_single_save_scanner_catches_second_and_misplaced_saves`, `test_tools_bypass_catches_every_forbidden_call` |
| major 3 | `SLA_WRITE_CALLS` thêm `set`; cờ hằng chuỗi tên trường SLA ở vế phải Assign/AnnAssign/AugAssign (trực tiếp hoặc phần tử Tuple/List/Set) | `test_sla_dates_scanner_catches_each_way_to_write_them` (cả ca đọc `x = doc.get('resolution_by')` không bị cờ) |
| minor a | miễn `_assign` chỉ trong hàm `_assigned_by_other` của authority.py (`ASSIGN_FIELD_ALLOWED_FILE/FUNCTION`) | `test_assign_column_scanner_catches_reads_and_allows_authority` (ca cùng file, hàm khác) |
| minor b | ca không import module: `a.assign_to.add_multiple({})`, `a.assign_to.add({})` | cùng test major 1; bỏ `assign_to.add_multiple` khỏi hậu tố thì đỏ |
| minor c | ca biên: `ai_assign`, `9_assign`, `_assigned`, `_assign_to`, `_assign9`, `x_assign_y` sạch; `(_assign)`, ` _assign `... bị bắt; tiền tố tên người `ThanhLan`, `ThiHà`, `AnhChi`, `2Thư`, `ai_Việt`, `xHiếu`, `NhàTiến` sạch | `test_assign_column_scanner_...`, `test_default_people_scanner_matches_whole_words_only` |
| minor d | máy quét cấm tạo ToDo thủ công (`get_doc('ToDo')`, `get_doc({'doctype': 'ToDo'})`, `new_doc('ToDo')`) ngoài route_ticket.py; fixture sạch bỏ ca insert ToDo | `test_assign_to_scanner_...` |
| minor f | `check_route_module_is_not_a_tool` cờ `handler=` (hoặc đối số thứ 4 của `ToolSpec`) trỏ tới `apply_route/assign_owner/post_routing_comment/create_routed_task` ở module tool khác | `test_route_module_scanner_catches_registry_listing_and_tool_names` |
| minor e | bỏ qua theo chỉ đạo (đã ghi nhận) | - |

## Đột biến mã sản xuất (thêm tạm, chạy cả module, hoàn tác, không commit)

| Đột biến | Kết quả đỏ |
|---|---|
| `agent/runner.py`: `doc.assign_agent('u')` | `test_assign_to_only_in_route_module`: `agent/runner.py:647: assigns people outside ... (ADR-021)` |
| `agent/tools/route_ticket.py`: `doc.db_update()` | `test_route_module_single_ticket_save`: `route_ticket.py:113: db_update in the routing module (ADR-020)`; thêm `test_tools_never_bypass_permissions`, `test_route_module_bypass_rules_apply` |
| `agent/routing.py`: `doc.set('response_by', x)` | `test_feature_never_assigns_sla_dates`: `routing.py:300: writes an SLA date (AC-10)` |
| `agent/routing.py`: `F = 'resolution_by'` | `test_feature_never_assigns_sla_dates`: `routing.py:299: holds the name of an SLA date (AC-10)` |
| `agent/runner.py`: `frappe.get_doc('ToDo').insert()` | `test_assign_to_only_in_route_module`: `creates a ToDo outside ...` |
| `agent/authority.py`: hàm khác đọc `_assign` | `test_assign_field_not_used_for_decision`: `authority.py:92: reads _assign` |
| `agent/tools/write_ticket.py`: `ToolSpec(..., handler=apply_route)` | `test_route_module_not_in_tool_modules_and_has_no_tools`: `apply_route is a tool handler (ADR-019)` |
| Máy quét: bỏ `assign_to.add_multiple` khỏi hậu tố | `test_assign_to_scanner_...` đỏ ở ca `a.assign_to.add_multiple({})` (không còn do import guard) |

Sau mỗi đột biến, `git status` chỉ còn `test_architecture.py` sửa.

## Xanh

- `bench --site miyano run-tests --module erp_ai.tests.test_architecture`: `Ran 97 tests ... OK`
- `bench --site miyano run-tests --app erp_ai` (chạy một mình): `Ran 880 tests in 161.216s` `OK`
- `pre-commit run --files erp_ai/tests/test_architecture.py`: tất cả Passed (ruff-format sửa tự động một lần rồi Passed).
- Không skip/xfail/only.

## Nhìn thấy nhưng không đụng

- Đã ghi trong review: `deferred` cho ADR-019 tên bộ phận (designer), `runner._route` không có `.save()` (ngoài phạm vi quét T26).
