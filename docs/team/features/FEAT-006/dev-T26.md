# dev-T26 — Luật kiến trúc ADR-019..021 và 2 bảo vệ tĩnh (FEAT-006)

Nhánh `team/FEAT-006-task-26` từ `team/FEAT-006` (BASE 2cd3ba3). Chỉ sửa `erp_ai/tests/test_architecture.py`; mã sản xuất không đổi (`git status` sạch ngoài file này).

## Thay đổi
- `POLICY_FIELDS` thêm `auto_assign_enabled`. `check_policy_fields_only_in_policy` miễn cho `policy.auto_assign_enabled(...)` (tên đã phân giải về `erp_ai.agent.policy.<tên>`); đọc trường (`settings.auto_assign_enabled`, `getattr`, `.get`, hằng chuỗi) vẫn bị bắt. Lý do: runner gọi hàm của policy trùng tên trường.
- Hàm quét mới: `check_route_module_is_not_a_tool`, `check_route_module_single_ticket_save`, `check_assign_to_only_in_route_module`, `check_no_share_bypass`, `check_no_assign_column_for_decisions`, `check_feature_never_assigns_sla_dates`, `check_no_default_people_in_agent_python`, `check_entry_types_unchanged`.
- 10 test trong `TestArchitecture` đúng tên yêu cầu; 10 ca trong `TestScannersCatchViolations` (bắt vi phạm + không báo nhầm).
- Hai quyết định cần người duyệt biết:
  1. `_assign`: `agent/authority.py:53` (FEAT-002, "ai được ra lệnh") đọc `_assign`, có từ trước định tuyến, không quyết định route. Cho vào `ASSIGN_FIELD_ALLOWED_FILES = (AUTHORITY_FILE,)`; test khóa danh sách này đúng một phần tử.
  2. Tên người: quét theo ranh giới từ trong hằng chuỗi (kể cả docstring). Trùng chữ được loại bằng cụm: "Việt Nam", "Tiếng Việt" (prompts.py) và "Thư mục" (`tools/source.py:153`, "Thư mục nằm ngoài mã nguồn cho phép": cũng là trùng chữ, ngoài hai cụm dặn trước). `ai.agent` khớp khi đứng riêng (không khớp `erp_ai.agent.*`). Không quét comment `#` và tên biến.

## Đỏ đúng lý do (tạm phá mã sản xuất, chạy `--test`, tự khôi phục file; không commit)
Script: scratchpad `red_proof.py`. Lệnh mỗi ca: `PYTHONPATH=<worktree> bench --site miyano run-tests --module erp_ai.tests.test_architecture --test <tên>`.

| Luật | Phá | Đầu ra đỏ |
|---|---|---|
| route_module_not_in_tool_modules | thêm `erp_ai.agent.tools.route_ticket` vào `TOOL_MODULES` | `registry.py:35: the registry lists route_ticket (ADR-019)` |
| (cùng test) | `TOOLS = []` trong route_ticket.py | `route_ticket.py:112: TOOLS in the routing module (ADR-019)` |
| route_module_single_ticket_save | thêm `doc.save()` thứ hai | `found 2 .save() calls, exactly one ticket save (ADR-020)` |
| assign_to_only_in_route_module | `assign_to.add` trong routing.py | `routing.py:299: imports frappe.desk.form.assign_to outside agent/tools/route_ticket.py` + `routing.py:303: assigns people outside ...` |
| no_share_bypass | `assign_to._add(` trong routing.py | `routing.py:303: frappe.desk.form.assign_to._add bypasses sharing rules (ADR-021)` |
| (cùng test) | `ignore_share_permission=True` trong route_ticket.py | `route_ticket.py:109: ignore_share_permission bypasses sharing rules (ADR-021)` |
| auto_assign_switch_only_in_policy | `bool(settings.auto_assign_enabled)` ở runner (giữ cả lời gọi policy) | `runner.py:128: reads auto_assign_enabled outside agent/policy.py` |
| entry_types_unchanged | thêm `"route"` vào `ENTRY_TYPES` | `ENTRY_TYPES is ('classify','reason','skip','route'), expected ('classify','reason','skip')` |
| assign_field_not_used_for_decision | `get_value(..., '_assign')` trong routing.py | `routing.py:301: reads _assign (decide from ToDo, ADR-019)` |
| route_module_bypass_rules_apply | `doc.save(ignore_permissions=True)` trong route_ticket.py | `route_ticket.py:63: ignore_permissions= in a tool` |
| feature_never_assigns_sla_dates | `doc.response_by = None` trong routing.py | `routing.py:301: assigns an SLA date (AC-10)` |
| no_default_people_in_agent_python | hằng `'Hiếu'` trong routing.py | `routing.py:299: hard-coded person 'Hiếu' (AC-14)` |

Lần phá đầu của ca auto_assign (thay hẳn lời gọi policy) đỏ ở khẳng định "runner phải gọi `policy.auto_assign_enabled(`" chứ không phải ở bộ quét, nên tôi phá lại bằng cách giữ lời gọi và thêm đọc trường: đỏ ở bộ quét (dòng bảng trên).

## Xanh
- `bench ... --module erp_ai.tests.test_architecture` → `Ran 97 tests ... OK` (trước: 77).
- `bench --site miyano run-tests --app erp_ai` (một mình) → `Ran 880 tests in 164.615s ... OK`.
- `pre-commit run --files erp_ai/tests/test_architecture.py`: ruff linter, import sorter, formatter Passed (lần đầu formatter tự sửa file, chạy lại Passed; sau đó chạy lại 97 OK).
- typecheck: profile không có bước riêng ngoài pre-commit.

## Seen but not touched
- Không có.
