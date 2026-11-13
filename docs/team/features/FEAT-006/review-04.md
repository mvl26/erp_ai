Feature: FEAT-006
Stage: build
Author-agent: tech-lead (tổng hợp từ reviewer)
Date: 2026-11-12
Approved-by:

# Review 04 — FEAT-006 T4

- Diff: `git diff b1af21f..a7db04d` (nhánh `team/FEAT-006-task-4`; merge `6ebb766`)
- Vòng: 1
- Verdict: approve

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| — | — | — | không có | — |

minor | — | — | 2 điểm nhỏ: `prompts.py:13` còn comment `# Guide 16.4, verbatim` dù prompt đã thêm bảng điểm và 4 khóa; test chỉ ghim tên khóa, chưa ghim đủ dòng 3.1

## Deferred
- Hai điểm nhỏ trên; truyền `departments` thật từ runner/eval ở T19/T25.

## Bằng chứng chạy (dev)
- RED: `'"do_phuc_tap"' not found` và `TypeError: build_classify_request() takes 2 positional arguments but 3 were given` (thiếu hành vi).
- GREEN: `erp_ai.agent.test_classification` Ran 36 tests, OK. Lint passed.
- `cmd.test` trên nhánh task: 674 test, lần 2 không còn failure nhưng 45 error `QueryDeadlockError 1213` ở module khác, do dev T5 chạy `cmd.test` đồng thời trên site dùng chung. Chưa có lần chạy riêng sạch cho T4; sẽ có ở lần chạy nối tiếp của T7 trên nền đã merge T4+T5 (đầu ra dán vào review-07.md). Nếu đỏ do T4/T5 thì gỡ merge.

## Review checklist (10)
1–10: đạt (reviewer approve; bảng thang điểm chép đúng spec.md:52-56).
