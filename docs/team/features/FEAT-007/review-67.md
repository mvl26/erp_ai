Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 67 — FEAT-007 T67

- Diff: `git diff aef271c7b12094afe23711003ee2d7a5fc32cbef..140c6d8` (nhánh `team/FEAT-007-task-67`; 3 commit `5e5d1f4`, `0d779c8`, `140c6d8`; 4 file +114/−19, đều là touchpoint)
- Vòng: 1 (trần `max_rework` = 3). Hai lần gọi dev: call 1 trả `DESIGN_CONFLICT` (round 74, chưa review), call 2 làm tiếp sau phán quyết `design-w1-fixes-1.md` Điểm 3 và quyết định 05:42 (a).
- Verdict: approve; merge `2b2a7df` trên `team/FEAT-007`
- File này do tech-lead viết từ báo cáo của reviewer (reviewer chỉ đọc, không ghi file).

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer):
  - RED của call 1 (round 74, `aef271c` + test): `AttributeError: module 'erp_ai.agent.policy' has no attribute 'month_spend_usd'` / `... 'is_over_budget'` / `TypeError: effective_level() got an unexpected keyword argument 'over_budget'`, `Ran 40 tests in 1.965s FAILED (errors=13)`.
  - RED test_agent_runner trên `5e5d1f4`: `FAIL: test_over_budget_l3_drops_change_tools` `AssertionError: 'L3' != 'L1'`; `FAIL: test_over_budget_l3_keeps_unrestricted_tools` `AssertionError: Lists differ: …`; `Ran 110 tests in 29.810s FAILED (failures=2)`. Lần chạy này dev lọc đầu ra qua `grep` (trái lời giao; các lần sau đọc đủ).
  - Test `test_policy` thêm ở call 2 KHÔNG đỏ trước (mã đã có ở `5e5d1f4`). Thay vào đó là hai bản đột biến không commit: `>` → `>=` trong `is_over_budget`: test_policy `Ran 44 tests in 1.665s FAILED (failures=2)` (`test_spend_equal_to_budget_is_not_over` `AssertionError: True is not False`; `test_effective_level_at_budget_does_not_lower` `AssertionError: 'L1' != 'L3'`), test_agent_runner `Ran 110 tests in 28.298s FAILED (failures=1)`; `creation < %s` → `<=` trong `month_spend_usd`: `AssertionError: 1010.0 != 10.0`, `Ran 44 tests in 1.683s FAILED (failures=3)`.
  - GREEN @ `140c6d8`, `MIGRATE_EXIT=0`: test_policy `Ran 44 tests in 1.688s OK`, test_agent_runner `Ran 110 tests in 29.450s OK`, test_architecture `Ran 181 tests in 15.498s OK`.
- Sáu điểm tech-lead yêu cầu phán, reviewer đều cho đạt:
  1. Phạm vi `test_agent_runner.py`: đúng một patcher ở `:119-122` (`patch("erp_ai.agent.policy.month_spend_usd", return_value=0.0)`, `start`, `addCleanup(stop)`, giữ ở `self.month_spend`); chỉ ba test `test_over_budget_*` đổi, chỉ ở dòng dựng (`:2791-2792`, `:2810-2811`, `:2844-2845`), mọi khẳng định cũ còn nguyên; `drops_change_tools` có `self.month_spend.assert_called()` (`:2799`). Cả 12 lớp test của file kế thừa `RunnerTestBase` và gọi `super().setUp()`.
  2. `runner.py:164` là dòng duy nhất đổi. `policy.py:86-88`: `is_over_budget` gọi `month_spend_usd(now)` qua tên toàn cục của module, không đọc `spent_this_month_usd`; đường nối được ghim ở `test_policy.py:508-510`.
  3. STD-TEST-5, ca cũ → ca mới, không ca nào bị bỏ hay làm yếu: `test_effective_level_over_budget_never_raises` (4 ca) → cùng tên `:157-162` với `over_budget=True`; `test_effective_level_at_budget_does_not_lower` → `:164-168` (chi vá 10.0, ngân sách 10, giữ L3) và `TestBudget::test_spend_equal_to_budget_is_not_over` trên dòng gieo; `test_effective_level_under_budget_unchanged` → `:170-172`. Helper `_settings` bỏ, không còn chỗ dùng.
  4. STD-TEST-6: `TestBudget` luôn dùng `now` cố định `2001-02-15 12:00`, dòng gieo đặt `creation` trực tiếp, hai dòng biên `2001-01-31 23:59:59` và `2001-03-01 00:00:00`, `settings` là `frappe._dict`, có chốt không-commit và rollback (`test_policy.py:465-471`). Giả định còn lại (site không có dòng tháng 2/2001) là tiền đề của chính phán quyết (điểm 5).
  5. STD-DESIGN-5: không gì vượt dòng task và phán quyết. Giữ `test_effective_level_at_budget_does_not_lower` là chuyển một ca cũ, không phải phạm vi mới; phép kiểm `TypeError` ở `:525-526` ghim dấu `*` của chữ ký.
  6. Bằng chứng đỏ-trước: nhận. RED mức API đã có ở call 1; reviewer đối chiếu bằng tay tám bản đột biến (bỏ đường nối, `>` → `>=`, `>=` → `>`, `<` → `<=`, đọc `spent_this_month_usd`, bỏ `now`, bỏ `or 0`, bỏ đặt lại giờ) và chỉ ra dòng test bắt từng bản.
- Checklist (10): 10/10 đạt; commit theo `type(scope): description (FEAT-007)`, không dòng ghi công AI, không skip.

### Findings

Không có blocker, không có major.

- minor | — | — | 2 điểm nhỏ: (a) phần đặt lại phút, giây, micro giây trong `month_spend_usd` (`policy.py:77`) không có test vì `now` cố định đã bằng 0 ở các phần đó; (b) dev lọc một lần chạy RED qua `grep` | dev's call

### Không kiểm được từ diff — tech-lead giải

- Reviewer không chạy test. Tech-lead chạy sau merge trên `team/FEAT-007` @ `2b2a7df`, một lần giữ khóa site, `MIGRATE_EXIT=0`: test_policy `Ran 44 tests in 1.756s OK`, test_agent_runner `Ran 110 tests in 28.529s OK`, test_ticket_panel `Ran 36 tests in 17.456s OK`, test_runner_routing `Ran 62 tests in 31.696s OK`, test_architecture `Ran 181 tests in 15.597s OK`.
- Bản đột biến của dev không được chạy lại; reviewer đã đối chiếu bằng tay (điểm 6). Nhận.
- `cmd.lint`: `pre-commit run --all-files` trên `team/FEAT-007` @ `2b2a7df`, mọi hook `Passed`.

## Module test khác chạm `policy.is_over_budget` mà không vá số chi (quyết định 05:42 (c); reviewer chỉ kê, không sửa)

- `erp_ai/tests/test_ticket_panel.py::TestTicketPanelGateParity`: phụ thuộc thật. `_decision` chạy `runner.run_for_ticket` (`:717`) → `_run` → `policy.is_over_budget(settings)` → `month_spend_usd()` của tháng hiện tại; lớp nền `FrappeTestCase`, không vá. Mọi nhánh đặt `monthly_budget_usd: 0` (`:607`), nên tổng chi sống của tháng > 0 thì các nhánh L2 (`instructor_role`, `assignee`) tụt về L1. Nhánh `over_budget` (`:668-669`) vẫn dựng vượt ngân sách bằng `spent_this_month_usd: 2` so với `monthly_budget_usd: 1`, trường không còn được đọc: nhánh chỉ vượt khi tổng chi sống > 1, không còn kiểm đúng điều tên nó nói.
- `erp_ai/eval/test_run_eval.py::TestRunEvalRun::test_eval_and_runner_share_classify_request` (`:363-370`), `::test_eval_uses_runner_route_function` (~`:516-535`): chạy `runner.run_for_ticket` ở L0, không đặt ngân sách; truy vấn sống có chạy nhưng không đổi kết quả (L0 không bị nâng).
- `erp_ai/tests/test_handlers.py::TestTicketHandlers::test_run_for_ticket_calls_classify_once` (`:231-236`): như trên, ở L0.
- Đã được phủ qua `RunnerTestBase`: `test_runner_routing.py`, `test_runner_status.py`.
- Tech-lead đo ngày 2026-11-15 (không sửa): cả ba module xanh trên nhánh task trước merge (test_ticket_panel `Ran 36 tests in 16.494s OK`, test_run_eval `Ran 23 tests in 0.527s OK`, test_handlers `Ran 31 tests in 5.999s OK`) và test_ticket_panel xanh sau merge. Phụ thuộc dữ liệu sống vẫn còn: chuyển team-leader mở task riêng.
