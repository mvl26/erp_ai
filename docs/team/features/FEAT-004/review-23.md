Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 23 — FEAT-004 T23

- Diff: `git diff 3aa363f..team/FEAT-004-task-23` (2 commit `992a489`, `3154fac`; 5 file)
- Vòng: 2 (max_rework=3)
- Verdict: approve (vòng 1: request-changes)

## Vòng 1 — request-changes (`git diff 3aa363f..992a489`)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-2 | erp_ai/agent/tools/test_registry.py:299 (cùng registry.py:78-80) | design 3.6 và ADR-011 QĐ 3/6: `grants_change_tools` tính từ `_granted_specs`, không có nơi thứ hai quyết định cấp; không test nào kiểm điều đó (viết lại điều kiện trực tiếp thì mọi test vẫn xanh) | thêm ca dưới patch `_specs` mặc định (không có spec `change_propose`): `grants_change_tools("L3", True, True)` là `False`, `get_tool_schemas("L3", True, True)` không có tool đổi |

minor | — | — | 1 điểm nhỏ: bảng cấp là `GRANT_TABLE` cấp module, design ghi "trong `_granted_specs`"; vẫn một nơi | tùy dev

## Vòng 2 — approve (re-review theo phạm vi, `git diff 992a489..team/FEAT-004-task-23`)
- Phát hiện 1: ADDRESSED (`test_grants_change_tools_follows_granted_specs_not_conditions`, `test_registry.py:333-338`; `registry.py` không đổi)
- Phát hiện mới: không có.

## Review checklist (10)
1–10 đạt sau vòng 2. Test FEAT-006 chỉ đổi hình dạng lời gọi (thêm `, False`).

## Bằng chứng của dev
- Vòng 1 RED: `FAILED (failures=1, errors=23)`: `TypeError: ToolContext.__init__() got an unexpected keyword argument 'change_enabled'`, `TypeError: get_tool_schemas() takes 2 positional arguments but 3 were given`; GREEN: `test_registry` `Ran 31 tests … OK`, `test_run_status` `Ran 9 tests … OK`, `test_agent_runner` `Ran 57 tests in 12.200s OK`
- Vòng 2 RED (điều kiện viết lại tạm thời): `AssertionError: True is not False`; GREEN: `Ran 32 tests in 1.092s` / `OK`

## Không kiểm được từ diff (tech-lead xử lý)
- AC-2 phần vượt ngân sách (hạ về L1): nối ở runner, T29.
- `test_run_status` cần kiểm nhãn với công tắc bật khi T28 đăng ký tool: đưa vào handoff T28.

## deferred
- Không có.
