Feature: FEAT-006
Stage: build
Author-agent: tech-lead (tổng hợp từ reviewer)
Date: 2026-11-12
Approved-by:

# Review 10 — FEAT-006 T10

- Diff: `git diff 7fa9ad9..2f0b871` (nhánh `team/FEAT-006-task-10`; merge ghi ở progress.md)
- Vòng: 1
- Verdict: approve

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| — | — | — | không có | — |

minor | — | — | `config: dict` nhưng chấp nhận `None` (nên `dict | None`); cách viết làm tròn lên `-(-x // 60)` kém dễ đọc hơn `math.ceil` (docstring có giải thích).

## Quy tắc làm tròn (tasks.md không nêu, dev chọn, reviewer xác nhận khớp spec AC-12 và design 4.2)
`actual_min = ceil(resolution_s / 60)`; chỉ coi là chậm khi `resolution_s > expected_min * 60`, nên thông điệp "xử lý a phút > mong đợi b phút" luôn có a > b. Hai test ghim: `test_boundary_equal_is_not_lag_one_second_over_is`, `test_seconds_round_up_to_whole_minutes`.

## Deferred
- T13/T20: đơn vị `site_facts.applied_sla(...).resolution_s` phải là giây (reviewer không kiểm được từ diff này).

## Bằng chứng chạy (dev)
- RED: Ran 44 tests, FAILED (errors=13), `AttributeError: module 'erp_ai.agent.routing' has no attribute 'sla_lag'`.
- GREEN `erp_ai.agent.test_routing`: Ran 44 tests, OK. `cmd.test` trên đầu nhánh task 2f0b871: Ran 723 tests, OK. Lint: passed.
- 11 đột biến (bỏ từng bảo vệ, đổi `<=` thành `<`, ceil thành floor, sắp xếp tên) đều đỏ rồi hoàn tác.
- Sau merge: `git diff --stat 2f0b871 HEAD -- . ':!docs'` rỗng; `git diff --name-only 7fa9ad9..2f0b871` chỉ gồm 2 file touchpoint.

## Review checklist (10)
1–10: đạt (reviewer approve vòng 1).
