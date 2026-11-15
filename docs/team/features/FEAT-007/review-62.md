Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 62 — FEAT-007 T62

- Diff: `git diff cbca448f126fcefadf0dc6609ccae2469e497346..b2f594b08ef8a4a1ad42cd0ebb264cf2cdc77d9d` (đầu nhánh task khi merge)
- Vòng: 2 (trần `max_rework` = 3)
- Verdict: approve (vòng 1 request-changes, vòng 2 approve)

## Vòng 1 — request-changes

- Range: `cbca448..886fcb8` (1 commit, 2 file, +35/−3), đúng 2 file của touchpoints.
- Bằng chứng của dev: RED (`erp_ai.agent.test_classification`) `FAIL: test_caps_at_ten`: `- Phiếu này có vẻ gồm 10 yêu cầu:` / `+ Phiếu này có vẻ gồm 11 yêu cầu:` / `+ … và 1 yêu cầu khác không liệt kê.`; `FAIL: test_cut_applies_after_collapsing`; `FAIL: test_newline_inside_request_collapsed`: `+ 1. x 2. y` / `- 1. x` / `- 2. y`; `Ran 52 tests in 0.241s`, `FAILED (failures=3)`. GREEN `test_classification` `Ran 52 tests in 0.223s OK`; `test_architecture` `Ran 112 tests in 5.438s OK`.
- Kết luận của reviewer: mã theo 5b từng vế, trong touchpoints; chuỗi khớp 5b từng ký tự (`…` là U+2026 ở thiết kế, mã và test); chữ ký không đổi; `test_four_requests`, `test_single_request_none` không bị sửa.

### Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-8 | erp_ai/agent/test_classification.py:568 (`test_caps_at_ten`) | Chỉ một test sinh ra dòng thêm: 11 yêu cầu khác rỗng, không có yêu cầu rỗng. Khi đó "n sau khi bỏ rỗng" và "số thô" đều là 11, nên đổi `classification.py:123` thành `len(classification.requests) - SPLIT_MAX_REQUESTS` (đếm cả rỗng) vẫn giữ 52 test xanh. Tiêu đề và trần 10 đã được ghim sau khi bỏ rỗng, nhưng lần dùng n thứ ba này thì chưa. | Thêm một ca n > 10 có yêu cầu rỗng nằm trong 10 mục đầu, ví dụ 12 thật + 2 rỗng → `"gồm 12 yêu cầu"`, mục 1–10 là 10 yêu cầu thật đầu, `"… và 2 yêu cầu khác không liệt kê."`, so cả chuỗi. |

minor | — | — | 1 điểm nhỏ: docstring của `TestSplitComment` (`test_classification.py:520`) còn dẫn `design.md:409`, dòng mà 5b đã thay | tùy dev

### Ba điều tech-lead hỏi
1. `test_cap_applies_after_dropping_empty` xanh từ trước khi sửa mã: không phải finding. 5b nêu tên test này, nó ghim một vế của 5b và đỏ dưới các lỗi dễ gặp của mã mới (tiêu đề đếm cả rỗng ra "13"; áp trần trước khi bỏ rỗng chỉ liệt kê 7 mục).
2. Test thêm `test_cut_applies_after_collapsing`: nhận. Là test, không phải tính năng; ghim vế "cắt 200 ký tự sau khi gộp khoảng trắng" mà không test được nêu tên nào phủ; đã đỏ trước.
3. Commit: đạt STD-NAME-5 và STD-GIT-8. Dòng tiêu đề đúng dạng; Expect của task đòi ghi lý do sửa `test_caps_at_ten` nên thân nhiều dòng là bắt buộc; không trailer.

### Review checklist (10)
1. đạt 2. đạt 3. trượt (STD-TEST-8 ở trên); không skip 4. đạt 5. đạt 6. đạt 7. đạt 8. đạt (trừ minor) 9. đạt 10. đạt

## Vòng 2 — approve (scoped re-review)

- Range sửa: `git diff 886fcb88783f554ad74fc2ee43acf6a17c78836d..b2f594b08ef8a4a1ad42cd0ebb264cf2cdc77d9d` (1 commit `test(agent): … (FEAT-007)`, 1 file `test_classification.py`, +12/−1); `classification.py` không nằm trong range sửa.
- Bằng chứng của dev: RED dưới đột biến (`classification.py:123` tạm thành `len(classification.requests) - SPLIT_MAX_REQUESTS`): `FAIL: test_overflow_line_counts_after_dropping_empty (...TestSplitComment.test_overflow_line_counts_after_dropping_empty)`, `- … và 4 yêu cầu khác không liệt kê.` / `+ … và 2 yêu cầu khác không liệt kê.`, `Ran 53 tests in 4.438s`, `FAILED (failures=1)`. GREEN `test_classification` `Ran 53 tests in 0.235s OK`; `test_architecture` `Ran 112 tests in 5.424s OK`.

| # | Finding vòng 1 | Kết quả | Bằng chứng |
|---|---|---|---|
| 1 | major STD-TEST-8: số của dòng thêm chưa được ghim sau khi bỏ rỗng | ADDRESSED | `test_classification.py:587-596`, test mới `test_overflow_line_counts_after_dropping_empty`: 12 yêu cầu thật + 2 rỗng (`""`, `"  \n "`) nằm trong 10 mục thô đầu; so cả chuỗi |
| 2 | minor: docstring dẫn `design.md:409` | ADDRESSED | `test_classification.py:520` nay dẫn `design-w0-fixes-2.md 5b` |

Finding mới trong diff sửa: không có. Ngoài phạm vi: reviewer kiểm thêm điều kiện `len(requests) > SPLIT_MAX_REQUESTS` (`classification.py:122`): nếu đếm cả rỗng thì `test_cap_applies_after_dropping_empty` nhận dòng `… và 0 …` và đỏ; cả ba lần dùng n đều có test.

## Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| Reviewer không chạy test | Xem dòng progress của T62 trong `tasks.md` (tech-lead chạy từ worktree `feat-007` sau merge). |

## deferred

- Không có.
