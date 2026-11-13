Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 15 — FEAT-004 T15

- Diff: `git diff 78d9887..team/FEAT-004-task-15` (1 commit `0743636`; 3 file, +136/−23)
- Vòng: 1 (max_rework=3)
- Verdict: approve

## Vòng 1 — approve
Không có blocker/major.

minor | — | — | 2 điểm nhỏ: (a) `test_architecture.py:526` vế `not violations and` của kiểm trùng đích không có test (bỏ đi chỉ thêm một câu thừa, không che vi phạm); (b) `test_architecture.py:511` câu lỗi ghi cứng "two" trong khi điều kiện đếm `len(ENQUEUE_TARGETS)` | tùy dev

## Review checklist (10)
1–10 đạt. `enqueue_change_job` ném `ValueError` khi `action` hoặc `proposal_name` sai, trước `frappe.enqueue`; lời gọi thứ hai đúng hình dạng design 3.4; luật đòi đúng 2 lời gọi, mỗi đích một lời gọi, đủ 5 tham số. `check_single_enqueue_site` không cần đổi. `enqueue_agent_run` không có thay đổi; luật khác (gồm luật FEAT-006) không đổi. Test cũ `test_enqueue_call_shape_requires_five_parameters` bị thay là hợp lệ theo STD-TEST-5 vì ADR-013 QĐ 2 đổi luật từ 1 thành 2 lời gọi; mọi ca cũ còn ở dạng rộng hơn.

## Bằng chứng của dev
- RED: `test_queue` `AssertionError: Expected 'enqueue' to be called once. Called 0 times.` và `ValueError not raised` → `FAILED (failures=12)`; `test_architecture` `FAILED (failures=6, errors=1)`
- GREEN: `test_queue` `Ran 9 tests ... OK`; `test_architecture` `Ran 107 tests ... OK`; lint sạch
- Sau merge `8ddaa01`: `cmd.test` `Ran 1032 tests in 173.592s` / `OK`

## Không kiểm được từ diff (tech-lead xử lý)
- AC-6 "không trùng": `deduplicate` của Frappe tra RQ lúc gọi `enqueue`, trước commit (`background_jobs.py:93-103` so `168-170`), nên hai lần gọi trong một giao dịch đều xếp hàng. Design 3.4 không đòi cờ chống trùng cho job thay đổi; AC-6 dựa vào T14 (duyệt lần hai → `InvalidTransition`) và T18 (job thoát khi trạng thái khác `Đã duyệt`). Không phải thiếu sót của T15; kiểm lại bằng `test_second_approve_and_second_job_change_nothing` khi review T16/T18/T19.
- `erp_ai.agent.changes.apply_job.run_change` chưa có tới T18: không nơi gọi nào (T16) được ra prod trước khi T18 merge; cả hai đang chờ T4.

## deferred
- Có từ trước diff này: trong `queue.py`, lời gọi qua `from frappe import enqueue as x` không được `check_enqueue_call_shape` đếm và `check_single_enqueue_site` bỏ qua file đó.
