Feature: FEAT-006
Stage: build
Author-agent: tech-lead (tổng hợp từ reviewer)
Date: 2026-11-12
Approved-by:

# Review 06 — FEAT-006 T6

- Diff: `git diff 4cfd68f..712b8b7` (nhánh `team/FEAT-006-task-6`; merge `b8d2607`)
- Vòng: 1 (sau 1 lượt dev làm tiếp do DESIGN_CONFLICT được tech-lead giải, xem dưới)
- Verdict: approve

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| — | — | — | không có | — |

minor | — | — | 3 điểm nhỏ: `assertEqual(count, 36)` luôn đúng theo cấu trúc; `subject` của `_priority` thiếu kiểu; `notes=[]` lệch kiểu tuple ghi trong design (từ T1)

## Đổi touchpoint (tech-lead, ghi ở progress.md)
Dev báo DESIGN_CONFLICT: test T1 `test_l1_scores_written_to_ticket` mã cứng giá trị giả `priority == "High"` cho A + importance 3, R4/AC-3 đòi `Urgent`. Tech-lead mở rộng T6 đúng 1 file `erp_ai/agent/test_runner_routing.py`, đổi đúng 1 khẳng định (dòng 69-70) sang `Urgent` (STD-TEST-5: kỳ vọng của bản giả, không nới). Báo người ở lần dừng để xác nhận.

## Deferred
- Hai đường ghi lệch nhau (A + quan trọng 3) cho tới T17 (`set_classification` còn gọi `resolve_ticket_values`); runner truyền cấu hình `{}` tới T19/T20. Đã có trong plan.

## Bằng chứng chạy (dev)
- RED trước khi viết mã: 14 failure + 1 error ở `test_routing` (ví dụ `'' != None` cho E, `'Medium' != 'High'` cho B với quan trọng 2).
- GREEN: `erp_ai.agent.test_routing` OK (36 subtests ma trận + `test_spec_samples`).
- `cmd.test` (`--app erp_ai`): Ran 668 tests in 114.566s, OK (lần đầu có 37 error do tranh chấp site chạy song song với T3; không lặp lại khi chạy một mình). Lint: passed.
- Sau merge: `git diff --stat 712b8b7 HEAD` ngoài file của T3/docs chỉ có 3 file của T6 (cây mã = hợp của hai nhánh đã chạy xanh).

## Review checklist (10)
1–10: đạt (reviewer approve; đối chiếu 36 ô ma trận với spec).
