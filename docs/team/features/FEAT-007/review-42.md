Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 42 — FEAT-007 T42

- Diff: `git diff 58b667411121655d13f8d775710bcdcc44721311..eafb5a6` (đầu nhánh `team/FEAT-007-task-42` lúc review; merge vào `team/FEAT-007` là `66fc4af`)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve

## Vòng 1 — approve

- Range: `58b6674..eafb5a6` (1 commit, 3 file, +97/−13), đúng 3 file của touchpoints.
- Bằng chứng của dev: RED `erp_ai.agent.test_queue` `AssertionError: None != 1200` ở `test_each_job_shape`, `FAILED (failures=1)`; RED `erp_ai.tests.test_architecture` `AssertionError: Lists differ: ['agent/queue.py: expected exactly 5 enqueue calls, one per target, found 2'] != []` ở `TestArchitecture.test_single_enqueue_call_site`; GREEN `test_queue` `Ran 10 tests in 0.007s OK`; `test_architecture` `Ran 112 tests in 3.003s OK`; `TestScannersCatchViolations` 68 test trước, 68 test sau.

### Phát hiện (chỉ blocker/major)

Không có finding nào ở mức blocker hay major.

minor | — | — | 2 điểm nhỏ: (a) STD-NAME-6, `erp_ai/tests/test_architecture.py:2350`: `test_enqueue_call_shape_accepts_runner_and_change_job` nay kiểm cả 5 đích mà tên vẫn chỉ nêu hai đích cũ (đổi thành `..._accepts_one_call_per_target`); (b) STD-TEST-6: quy ước của `tasks.md` nói mọi lớp test mới gọi `keep_agent_settings(self)`, `TestEnqueueScheduledJobs` (`erp_ai/agent/test_queue.py:117`) không gọi; vô hại vì các hàm này không đọc cấu hình và `frappe.enqueue` được patch | tùy dev

### Ghi nhận của reviewer

- Ba hàm khớp bảng của `plan.md`: đích, `job_id`, `queue="long"`, `timeout=SCHEDULED_JOB_TIMEOUT_S`, `enqueue_after_commit=True`, `deduplicate=True`, không kwarg khác; đích là chuỗi, `queue.py` không import module job nào; `enqueue_agent_run`, `enqueue_change_job` không đổi.
- F-2, C-1: `ENQUEUE_TARGETS` 5 chuỗi; chữ lỗi và docstring theo F-2; `requires_each_target_once` (5 lời gọi, khẳng định "each of") và `rejects_target_outside_set` (4 đích đầu + 1 đích sai, khẳng định "first argument") đúng C-1.
- `test_each_job_shape` dùng `assert_called_once_with` với đích, `job_id`, `timeout=1200` viết thẳng: đỏ nếu thiếu lời gọi, thừa/thiếu kwarg, hoặc mã dùng `JOB_TIMEOUT_S` (600).
- Lý do đổi ghim (ADR-033 QĐ 6, STD-TEST-5) có trong commit.

### Review checklist (10)
1. đạt 2. đạt 3. đạt (RED cho cả hai module; không skip) 4. đạt (ghim cũ đổi vì quyết định ADR-033 QĐ 6) 5. đạt 6. đạt 7. đạt (chỉ thêm) 8. đạt (một tên test cũ, minor) 9. đạt 10. đạt (`feat(agent): ... (FEAT-007)`, không dòng ghi công AI)

## Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| Ba module đích (`daily_report`, `kpi`, `monthly_review`) chưa có; job xếp hàng lúc này sẽ lỗi import | Đúng kế hoạch: không gì gọi ba hàm này trước T44 (cron). Rủi ro "cron bật trước khi module có" đã ở `plan.md` mục Rủi ro (dòng Scheduled Job Type) và phải xét trước khi làm T44: T44 chỉ phụ thuộc T40, T42 trong khi ba module đích thuộc T47, T50, T53. Tech-lead nêu với team-leader trước khi gọi dev cho T44. |
| `cmd.test` cả bộ chưa chạy | Theo N-6: chạy ở mốc M1. |
| GREEN chưa được chạy lại | Sau merge, trên `team/FEAT-007` @ `66fc4af`: `erp_ai.agent.test_queue` `Ran 10 tests in 0.010s OK`; `erp_ai.tests.test_architecture` `Ran 112 tests in 3.178s OK`; `erp_ai.agent.test_hard_bans` `Ran 7 tests in 0.067s OK`. |
| `cmd.lint` | Chỉ nợ nền `erp_ai/test_change_decision.py` (xem `review-59.md`). |

## deferred

- (minor, tùy dev) tên test cũ ở `test_architecture.py:2350`: sửa ở T56 khi gộp file này, hoặc task kế tiếp chạm phần enqueue.
- (minor) `TestEnqueueScheduledJobs` không gọi `keep_agent_settings`.
