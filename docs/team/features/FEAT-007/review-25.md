Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 25 — FEAT-007 T25

- Diff: `git diff aff309d4d44b6ca7dc387eafd8b90f5d2971ee45..5fcf2d48636af5e2f4097b55b0def8b413ed7415` (đầu nhánh task khi merge; merge `9e99f44` trên `team/FEAT-007`)
- Vòng: 1 (trần `max_rework` = 3). Lần gọi dev đầu (round 15) trả `DESIGN_CONFLICT` với 0 commit; lần này làm từ đầu theo `design-w0-fixes-3.md` phán quyết 1.
- Verdict: approve

## Vòng 1 — approve

- Range: `aff309d..5fcf2d4` (1 commit, 2 file, +108/−1), đúng 2 file của touchpoints; `test_routing.py` chỉ thêm ở cuối, không test hay hàm phụ sẵn có nào bị sửa.
- Bằng chứng của dev: RED (`erp_ai.agent.test_routing`) `AttributeError: 'RouteDecision' object has no attribute 'watcher'` (21 lần), `AttributeError: module 'erp_ai.agent.routing' has no attribute 'D_WATCHER_MISSING_NOTE'`, `Ran 68 tests in 0.174s`, `FAILED (errors=22)`; GREEN `test_routing` `Ran 68 tests in 2.530s OK`, `test_architecture` `Ran 112 tests in 5.347s OK`. Tech-lead chạy trên đầu nhánh task: `test_runner_routing` `Ran 62 tests in 94.424s OK`, `test_run_eval` `Ran 23 tests in 5.553s OK`.
- Kết luận của reviewer: mọi dòng của bảng phán quyết 1 nằm ở `routing.py:100-109` (`_watcher`), không hành vi nào ngoài phán quyết. Ba trạng thái phân biệt bằng `d_watcher is None` và `d_watcher.strip() == ""`, không dùng phép thật/giả; kiểm "chỉ D" đứng trước mọi lời gọi `is_active_agent`; ghi chú người theo dõi không hoạt động cùng chữ với ghi chú `assignee`; không đường nào thêm quá một mục `watcher`. Chữ ký `decide_route` không đổi; `RouteDecision.watcher` mặc định `None` nên các chỗ dựng ở `test_route_ticket.py:90` vẫn chạy. Ba nơi gọi của mã sản phẩm (`runner.py:281`, `write_ticket.py:50`, `run_eval.py:198`) không truyền `d_watcher`, nhận `watcher=None`, `priority` và `notes` như trước (`design-w0-fixes-2.md:73` giữ).
- Kiểm đột biến (vế → test đỏ): bỏ `category != "D"` hoặc nới thành D/E → `test_other_category_none`; đổi `is None` thành `not d_watcher` → `test_d_unconfigured_note` ca `""`; bỏ `.strip()` → cùng test ca `"  "`; gọi `is_active_agent` ngoài D hoặc khi rỗng → các `assertNotIn`; thêm mục thứ hai hoặc mục ở nhánh hoạt động → phép so cả danh sách; bỏ kiểm `is_active_agent` → `test_inactive_watcher_none`; D có ghi chú khi `None` → `test_old_call_shape_no_watcher_note`. Giá trị mong đợi viết thẳng, không đọc từ hằng.

## Phát hiện (chỉ blocker/major)

Không có.

minor | — | — | 2 điểm nhỏ: (1) phép so kiểu gọi cũ cho D (`test_routing.py:903`) so hai lời gọi giống hệt vì mặc định là `None`; thiết kế đòi vậy, lưới chắn thật là vòng `_decide("D", 1)`; (2) `test_constant` thêm ngoài 5 test được nêu, vô hại | tùy dev

## Review checklist (10)
1. đạt (đủ 5 test của Expect) 2. đạt 3. đạt (RED là thiếu thuộc tính và thiếu hằng; không skip) 4. đạt (không sửa test có sẵn; `keep_agent_settings`, `NOW` cố định, hàm giả tạo mới mỗi subTest) 5. đạt (hàm thuần, không I/O) 6. đạt 7. đạt (trường mới có mặc định, chữ ký và kết quả nơi gọi không đổi) 8. đạt 9. đạt (không thêm) 10. đạt (`feat(agent): … (FEAT-007)`, không trailer)

## Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| Reviewer không chạy test; nơi gọi còn xanh chỉ dựa vào lần chạy của dev và tech-lead | Sau merge `9e99f44`, tech-lead chạy từ worktree `feat-007`: `test_routing` `Ran 68 tests in 0.128s OK`; `test_architecture` `Ran 112 tests in 5.375s OK`; `test_run_eval` lần 1 `FAILED (errors=2)` đều `QueryDeadlockError`, lần 2 `Ran 23 tests in 1.107s OK`; `test_runner_routing` lần 1 `FAILED (errors=6)`, lần 2 `FAILED (errors=3)` đều `QueryDeadlockError` (không dòng `FAIL:`), lần 3 `Ran 62 tests in 86.712s OK`. `cmd.lint`: chỉ nợ nền `erp_ai/test_change_decision.py`. |
| Phía U4b (`d_watcher=settings.d_ticket_watcher or ""` ở runner) ngoài T25 | Việc của đợt 1; đã ghi ở `plan.md` mục "Chèn 3". |

## deferred

- (minor, tùy dev) 2 điểm nhỏ ở trên.
- (đợt 1, U4b) `design-addendum-1-U4b-U8.md:245` đổi `or None` thành `or ""`, thêm `test_d_watcher_unconfigured_logged`.
