Feature: FEAT-006
Stage: build
Author-agent: tech-lead (tổng hợp từ reviewer)
Date: 2026-11-12
Approved-by:

# Review 08 — FEAT-006 T8

- Diff: `git diff 2851bca..57fd5ca` (nhánh `team/FEAT-006-task-8`; merge `61e51f2`)
- Vòng: 2 (vòng 1 request-changes, vòng 2 scoped re-review approve)
- Verdict: approve

## Phát hiện vòng 1 (blocker/major)
| severity | STD | file:line | description | fix | vòng 2 |
|---|---|---|---|---|---|
| major | STD-TEST-8 | test_routing.py:178-181,215-227 | mọi tiền tố config viết thường; thiếu ca `[TraceCore]` với tiêu đề `[tracecore] x` | `test_config_prefix_casefolded` | ADDRESSED |
| major | STD-TEST-8 | test_routing.py:229-267 | thiếu D-13 "tiền tố khớp đầu tiên CÓ NGƯỜI" và ca ứng viên không hợp lệ không lùi sang `default` | thêm ca (a), (b) | ADDRESSED |
| major (suspected) | STD-ERR-2 | routing.py:91 | `candidate == AGENT_USER` so sánh chính xác | `strip().casefold()` + test HOA/khoảng trắng/Title | ADDRESSED |

## Deferred
- Minor dev đã làm: bỏ qua khóa tiền tố rỗng `""` (design 3.2/3.3 không nói; cần người xác nhận ở C2 là đúng ý spec); `# noqa: E731` thay bằng `def`.
- Đổi kỳ vọng cũ của T7 `test_abcf_team_from_mapping` từ `decision.notes == ()` sang `_team_notes(decision) == []` (A/B/C/F giờ có note `assignee`): reviewer chấp nhận, không nới.

## Bằng chứng chạy (dev)
- `cmd.test` vòng 1: 688 OK. Vòng 2: dev phá mã tạm cho từng test mới để chứng minh đỏ, rồi hoàn tác.
- `cmd.test` nối tiếp trên nền đã merge (61e51f2): chạy ở bước C2 (xem progress.md).

## Review checklist (10)
1–10: đạt (reviewer approve vòng 2).
