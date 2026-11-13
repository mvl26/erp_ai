Feature: FEAT-006
Stage: build
Author-agent: tech-lead (tổng hợp từ reviewer)
Date: 2026-11-12
Approved-by:

# Review 02 — FEAT-006 T2

- Diff: `git diff 686aa3f..60630c4` (nhánh `team/FEAT-006-task-2`; merge `8473884`)
- Vòng: 2 (vòng 1 request-changes, vòng 2 scoped re-review approve)
- Verdict: approve

## Phát hiện vòng 1 (blocker/major)
| severity | STD | file:line | description | fix | vòng 2 |
|---|---|---|---|---|---|
| major | STD-TEST-8 | test_utils.py:186-197 + tests/test_test_utils.py:40-63 | vòng thêm role còn thiếu trong `pin_agent_roles` không test nào chạy | thêm ca xóa `Agent`/`ERP AI Agent`, tập ghim đầy đủ, kiểm sau doCleanups | ADDRESSED |
| major (suspected) | STD-TEST-6 | `pin_agent_roles` | cache role agent không bị xóa khi `restore` lỗi giữa chừng | `addCleanup(frappe.clear_cache, user=AGENT_USER)` sau khôi phục, có ca kiểm | ADDRESSED |

Ghi chú: lần giao đầu của vòng 2 sai commit (bản sửa chưa nằm trong commit); giao lại bằng một commit squash `60630c4`, `git status` sạch.

## Deferred
- `PREFIX` trùng `test_agent_runner.py:36` (ngoài touchpoint T2). Minor: count check ở `restore`; tên `SLA_RESPONSE_HOURS_BY_PRIORITY`.

## Bằng chứng chạy (dev)
- `erp_ai.tests.test_test_utils`: 11 test OK; ca mới đỏ khi bỏ `addCleanup` (`Called 0 times`).
- `cmd.test` (dev, trên đầu nhánh task): 687 OK; Has Role của tài khoản agent 99 trước = 99 sau cả bộ.
- `cmd.test` nối tiếp trên nền đã merge: chạy ở bước C2 (xem progress.md).

## Review checklist (10)
1–10: đạt (reviewer approve vòng 2, 2026-11-12 19:55–19:58 theo runs.jsonl).
