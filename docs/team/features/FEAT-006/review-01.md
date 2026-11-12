Feature: FEAT-006
Stage: build
Author-agent: tech-lead (tổng hợp từ reviewer)
Date: 2026-11-12
Approved-by:

# Review 01 — FEAT-006 T1

- Diff: `git diff d8fb3e9..a759792` (nhánh `team/FEAT-006-task-1`; merge `2393337` vào `team/FEAT-006`)
- Vòng: 2 (max_rework=3)
- Verdict: approve

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-5 | erp_ai/agent/test_agent_runner.py:550 | vòng 1: ca bị nới (assertNotIn) | vòng 2 ADDRESSED: khớp chính xác `value_after` và `actions` |
| major | STD-NAME-6 | erp_ai/agent/test_agent_runner.py:537,572 | vòng 1: tên nói applied_zero, assertion applied == 1 | vòng 2 ADDRESSED: đổi tên |
| major | STD-GIT-2 | commit 57f7d4a | vòng 1: commit `wip` ghi "còn đỏ" | vòng 2 ADDRESSED: squash thành `a759792` |

minor | — | — | 3 điểm nhỏ (đã xử lý/để lại có chủ): đổi comment ADR; `_route` chưa có `auto_assign, subject` (T19/T20 thêm); trùng `LINKED_DOCTYPES` (T16)

## Deferred
- `test_agent_runner.py:578-598` chỉ kiểm tập khóa `value_after`, trùng setup với ca ở dòng 537: gộp hoặc làm chính xác ở T16.
- Chữ ký `_route(..., auto_assign, subject)` thêm ở T19/T20.

## Bằng chứng chạy (dev, trên a759792; tech-lead không chạy được bench do role-policy chặn `cmd.*` có `PYTHONPATH=`)
- `cmd.test` toàn bộ (`--app erp_ai`, PYTHONPATH worktree): `Ran 660 tests in 112.067s`, `OK`; trước sửa 3 file test cũ: 660 test, 8 failure (kỳ vọng cũ đối nghịch hành vi mới).
- 2 test T1 (`test_l1_scores_written_to_ticket`, `test_l0_ticket_unchanged_scores_zero_not_null`): RED rồi GREEN ở lần dev 1, `Ran 2 tests, OK`.
- `pre-commit run --files <touchpoint>`: mọi hook Passed/Skipped.
- Sau merge: `git diff --stat a759792 team/FEAT-006 -- . ':!docs'` rỗng (cây mã trên `team/FEAT-006` đúng bằng cây đã chạy xanh; chỉ khác file docs).

## Review checklist (10)
1–10: đạt (reviewer vòng 2: approve; vòng 1 request-changes đã ADDRESSED). Mục "không kiểm được từ diff": output đỏ-trước của STD-TEST-1 cho 3 file test cũ (không áp dụng: chỉ đổi kỳ vọng); `check_tools_never_bypass_permissions` phủ `route_ticket.py` (tech-lead xác nhận trong `cmd.test` xanh, gồm `test_architecture`).
