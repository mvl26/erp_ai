Feature: FEAT-006
Stage: build
Author-agent: tech-lead (tổng hợp từ reviewer)
Date: 2026-11-12
Approved-by:

# Review 07 — FEAT-006 T7

- Diff: `git diff 686aa3f..3388d50` (nhánh `team/FEAT-006-task-7`; merge `2851bca`)
- Vòng: 2 (vòng 1 request-changes, vòng 2 scoped re-review approve)
- Verdict: approve

## Phát hiện vòng 1 (blocker/major)
| severity | STD | file:line | description | fix | vòng 2 |
|---|---|---|---|---|---|
| major | STD-TEST-2 | test_routing.py:87-96,128 | D/E bỏ qua dùng `DEFAULT_CATEGORY_MAPPING` có nhóm rỗng nên test không phát hiện việc lấy nhóm từ ánh xạ | ánh xạ mồi cho D/E | ADDRESSED |
| major | STD-TEST-2 | test_routing.py:104-106 | A/B/C/F chỉ chạy với `team_exists=True`, `is_excluded_team=False` | thêm ca ngược, ghim "như hiện nay" | ADDRESSED |

## Deferred
- Không có mục ngoài phạm vi. Minor dev đã làm: comment nguồn gốc `_normalize`; ca `test_de_config_key_case_and_spaces`.
- `RouteDecision.notes` đổi list → tuple theo design (dev tự làm, reviewer chấp nhận).

## Bằng chứng chạy (dev)
- `cmd.test` vòng 1 (nền đã gồm T4+T5): 679 test OK. Vòng 2: test mới đỏ khi phá mã tạm (dev báo), rồi xanh.
- `cmd.test` nối tiếp trên nền đã merge: chạy ở bước C2 (xem progress.md).

## Review checklist (10)
1–10: đạt (reviewer approve vòng 2).
