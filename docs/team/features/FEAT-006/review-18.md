Feature: FEAT-006
Stage: build
Author-agent: tech-lead (tổng hợp từ reviewer)
Date: 2026-11-12
Approved-by:

# Review 18 — FEAT-006 T18 (xóa `resolve_ticket_values`, chuyển ca test sang `test_routing.py`)

- Diff: `git diff 5718e2f..029890e -- erp_ai` (nhánh `team/FEAT-006-task-18`, commit 029890e; merge `efba510`)
- Vòng: 1
- Verdict: approve

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| — | — | — | không có | — |

minor | — | — | `test_routing.py:92-104` dựng `decide_route` trực tiếp với `config={}` thay vì dùng `_decide`; `test_urgent_prefix_forces_urgent` trùng một phần `test_urgent_tag_variants_casefold` (giữ cả hai vì tiêu chí "không bỏ ca nào").

## Điểm reviewer đã kiểm
- D-12: `resolve_ticket_values` đã xóa; `git grep resolve_ticket_values 029890e -- erp_ai` rỗng. 8 ca cũ còn đủ: 7 chuyển sang `TestDecidePriority` cùng giá trị kỳ vọng và cùng đầu vào hiệu lực (importance 0); ca JSON lồng nhau chuyển nguyên văn sang `TestParseClassification` (đặt nhầm lớp từ trước).
- `routing.py` giữ hành vi: `entry.get("ticket_type")`, `entry.get("agent_group") or None`; ưu tiên vẫn từ `_priority`. Mỗi ca chuyển đỏ khi bỏ điều nó khóa.
- Touchpoint `routing.py` ngoài danh sách T18 do tech-lead mở rộng (ghi ở progress.md); design mục 7 giao việc đổi chỗ gọi này cho công việc này.

## Mục "không kiểm được từ diff" và phán quyết
- Đầu ra chạy (56/29/783 OK, đột biến, lint) nằm trong `dev-T18.md` (dòng 23-24): đã đọc; chấp nhận, vì `cmd.test` toàn app của dev trên đầu nhánh task 029890e là bằng chứng và cây mã sau merge trùng (`git diff --stat 029890e HEAD -- . ':!docs'` rỗng).

## Deferred
- Minor ở trên (dọn test khi gộp).

## Bằng chứng chạy (dev)
- Test mới xanh khi hàm cũ còn: `test_routing` Ran 56 OK. Đột biến bỏ kiểm tag khẩn: 21 failures (gồm `test_urgent_prefix_forces_urgent`, `test_urgent_prefix_overrides_empty_priority_and_missing_category`), hoàn tác. Sau xóa: `test_routing` 56 OK, `test_classification` 29 OK.
- `cmd.test` đầu nhánh task 029890e: `Ran 783 tests in 132.653s`, `OK` (số test trước = sau = 783); lint pre-commit 4 file Passed; `grep -rn resolve_ticket_values erp_ai/` rỗng.

## Review checklist (10)
1–10: đạt (reviewer approve vòng 1).
