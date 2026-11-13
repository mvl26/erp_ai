Feature: FEAT-001
Stage: build
Author-agent: reviewer
Date: 2026-11-11
Approved-by:

# Review 01 — FEAT-001 T1

- Diff: `git diff 34e4c8f..team/FEAT-001-task-1` (head 12e8c92); vòng 2 `git diff cfb160b..5449692`; vòng 3 `git diff 5449692..12e8c92`
- Vòng: 3 (max_rework=3)
- Verdict: approve

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major (vòng 1, ADDRESSED) | STD-DESIGN-2 | erp_ai/handlers.py:8-12 | try/except DoesNotExistError nuốt lỗi | thay bằng `frappe.db.exists("DocType", SETTING_DOCTYPE)` trước khi đọc; T31 gỡ guard |
| major (vòng 2, ADDRESSED) | STD-TEST-5 | erp_ai/test_handlers.py:99-111 | test không đi vào đường bật sau guard | patch `frappe.db.exists` như hai test kia; mutant gọi model đồng bộ làm test đỏ ("1 != 0") |

minor | — | — | 2 điểm nhỏ chưa làm (deferred): test nhánh `owner == AGENT_USER` (T31), tên tham số `kw`; gợi ý thêm assert enqueue trong test_saving_ticket_never_calls_the_model

## Review checklist (10)
1–10: đạt ở vòng 3.

## Bằng chứng
- test_handlers: `Ran 6 tests ... OK` (module `erp_ai.test_handlers`, trên team/FEAT-001 sau merge). lint `pre-commit run --all-files`: exit 0.
- `cmd.test` (`--app erp_ai`) chạy 0 test: lỗi của Frappe `_add_test` khi file test nằm ở gốc gói app. Cần quyết định (chuyển test vào `erp_ai/tests/` hoặc đổi cmd.test).

## Deferred
- STD-TEST-8 owner==AGENT_USER (T31), STD-NAME-6 `kw`.
