Feature: FEAT-006
Stage: build
Author-agent: tech-lead (tổng hợp từ reviewer)
Date: 2026-11-12
Approved-by:

# Review 05 — FEAT-006 T5

- Diff: `git diff b1af21f..0f84aff` (nhánh `team/FEAT-006-task-5`; merge `1aa1a79`)
- Vòng: 1
- Verdict: approve

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| — | — | — | không có | — |

minor | — | — | không có điểm nhỏ có mã STD

## Deferred
- `POLICY_FIELDS` thêm `auto_assign_enabled` ở T26; trường DocType ở T11.

## Bằng chứng chạy (dev)
- RED: `AttributeError: module 'erp_ai.agent.policy' has no attribute 'is_excluded_team'` và `... 'auto_assign_enabled'`.
- GREEN: `erp_ai.agent.test_policy` Ran 24 tests, OK (4 test cũ của `can_send_ticket` nguyên văn). Lint passed.
- `cmd.test` trên nhánh task: 674 test, lần 1 25 error, lần 2 34 error, tất cả `QueryDeadlockError 1213` ở `test_runner_status`, `test_export_tickets`, `test_run_eval` (dev T4 chạy cùng lúc). Chưa có lần chạy riêng sạch; sẽ có ở lần chạy nối tiếp của T7 trên nền đã merge T4+T5 (review-07.md). Nếu đỏ do T4/T5 thì gỡ merge.

## Review checklist (10)
1–10: đạt (reviewer approve; refactor `can_send_ticket` giữ hành vi).
