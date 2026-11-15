Feature: FEAT-007
Stage: build
Author-agent: tech-lead
Date: 2026-11-15

# Review T52 — Việc bot làm hôm qua trong báo cáo 08:00

## Vòng 1 (2026-11-15, lượt build 18) — `design-defect`

- Lệnh diff (reviewer tự chạy): `git log ed341b9..22443a3`, `git diff --stat ed341b9..22443a3`, `git diff ed341b9..22443a3`, `git show --stat fa18524 22443a3`. 2 file, +162/−2, đều là touchpoint. Reviewer dùng 12/20 lượt, không chạy test.
- Mã nền reviewer đọc ở `ed341b9`: `erp_ai/agent/runner.py` (60-100, 296-335, 360-535, 700-790), `run_log.py`, `kpi.py:180-215`, `tools/write_ticket.py:100-135`, `constants.py:34`; `design.md:436-456`, `spec.md:225-226`; `design-w1-fixes-15.md` không nói gì về `bot_actions`.
- Tầng 1: mã làm đúng `design.md:451-454`. Thiết kế không cho ra số đếm theo loại của AC-51, vì tên tool nó ánh xạ không phải tên mã nền ghi vào `actions`.

Finding (nguyên văn):

- design-defect | STD-DESIGN-2 | design.md:451 vs runner.py:410-425,527 (ed341b9); daily_report.py:109-112 | "gán" is counted from a classify row with `predicted_assignee` and `applied`. But `applied` only means `apply_route` succeeded. The bot assigns only when the `assign_owner` action is ok (runner.py:423). If the ticket already has an owner (:410-414) or the assign step fails (:422-425), `predicted_assignee` stays set and "gán" goes up anyway. The ok `assign_owner` entry is also counted again under "khác". | Count "gán" from ok `assign_owner` actions. | confirmed
- design-defect | STD-DESIGN-2 | design.md:454 vs runner.py:69,463,481,499 + kpi.py:188-200 (ed341b9); daily_report.py:26 | `ACTION_KIND_BY_TOOL` only knows the reason-turn tools. Four problems: (1) Routed Tasks (`create_routed_task`) and routing comments (`post_routing_comment`) are counted as "khác", not Task/comment. (2) Every routed ticket's ok `apply_route` adds 1 to "khác". Each ok `propose_*` action also adds 1 to "khác" on top of its `propose` row. (3) `ANSWER_TOOL = "post_comment"`, so "trả lời" can never be told apart from "comment" and stays 0. (4) "đóng" is waiting for a tool that the design says "U6b adds later". The base already defines a bot close (an ok action whose `value_after.status` is Resolved/Closed, ADR-024, `kpi._bot_closed`). | Designer re-states the tool→kind map against every `"tool":` writer on the base, and defines trả lời and đóng from data that exists today. | confirmed
- major | STD-DESIGN-4 | erp_ai/agent/daily_report.py:123-131 | `_ok_actions` copies `kpi._actions` (kpi.py:203-211) almost line for line and only adds the `ok is True` filter. No import cycle stops reuse: kpi imports only classification, ops_data and constants. | Reuse the kpi parser and filter `ok` in daily_report. Making it public needs `kpi.py` as a touchpoint, so include it in the design fix. | confirmed
- minor | — | — | 5 small points: (a) test_daily_report.py: inside yesterday no non-classify row has `applied=1`, so dropping `row.entry_type == "classify"` (daily_report.py:109) stays green. (b) The cost case tells "round" from "no round" but not 6 digits from 7 or more, e.g. 0.0000004 would. (c) No case covers non-list JSON (`"{}"`, `"null"`), a non-dict entry, or truthy-but-not-True `ok`. (d) A day with no rows returns `cost_yesterday` as int `0`, not `0.0`, and no zero-day case exists (T53 covers it). (e) The `gán=1` expectation pins the rule that has the defect. | dev's call, re-test after the design fix.

Review checklist (10): 1 ✗ (design-defect) · 2 ✓ · 3 ✓ (thiếu vài ca nhỏ) · 4 ✓ · 5 ✓ · 6 ✓ · 7 ✓ (chỉ thêm khóa) · 8 ✗ (STD-DESIGN-4) · 9 ✓ · 10 ✓.

Tầng 2 (đạt): commit test `fa18524` trước commit mã `22443a3`; hai dòng RED đỏ đúng lý do; `REPORT_KEYS` đổi theo spec (`design.md:451-452`); test ghim `test_empty_due_field_logs_no_warning` (việc chuyển từ `review-179.md`) đúng và đỏ khi đột biến; cửa sổ "hôm qua" có ca biên, dữ liệu test tự tạo, truyền `anchor`; truy vấn có tham số; khóa mới chỉ mang số đếm và tổng chi phí; không import `erp_ai_agent.*`; commit đúng chuẩn, không dòng ghi công AI.

Không kiểm được từ diff:

- `cost_usd` có lưu đủ 6 chữ số thập phân hay không (precision của DocType).
- `creation` của ERP AI Log có cùng giờ site với `anchor` hay không.
- U6b có thêm tool trả lời riêng hay không (thiết kế nên chốt ngay).

Bằng chứng của dev (nguyên văn dòng kết quả): RED trên `fa18524`: `AttributeError: module 'erp_ai.agent.daily_report' has no attribute 'ACTION_KIND_BY_TOOL'`, `Items in the second set but not the first: 'cost_yesterday' 'bot_actions'`, `Ran 12 tests in 4.837s` / `FAILED (failures=1, errors=1)`. GREEN trên `22443a3`, `MIGRATE_EXIT=0`: test_daily_report `Ran 12 tests in 4.703s` OK; test_architecture `Ran 185 tests in 28.150s` OK; `pre-commit run --all-files` `LINT_EXIT=0`.

## Kết luận của tech-lead

DỪNG riêng chuỗi T52 → T53 → T54 (lời giao lượt 18: `design-defect` chỉ dừng chuỗi của task đó; tech-lead không bổ sung dòng task, không thiết kế lại). KHÔNG merge, KHÔNG tick. Nhánh `team/FEAT-007-task-52` @ `22443a3` giữ. Cần designer: nêu lại ánh xạ tool → loại theo mọi nơi ghi `"tool":` trên mã nền; nguồn của "gán", "trả lời", "đóng"; thêm `erp_ai/agent/kpi.py` vào `files:` nếu dùng lại hàm đọc `actions`.

## Vòng 2 (2026-11-15, lượt build 20) — `design-defect` (vế chi phí của dòng Expect không thể đạt), kèm 1 major cho dev

- Lệnh diff: `git diff 69a56cf..7b5461b` (BASE = `git merge-base team/FEAT-007 team/FEAT-007-task-52` = `69a56cf`; nhánh task đã merge `team/FEAT-007` thành `ac1a958`, không xung đột; đầu nhánh `7b5461b`; commit vòng 2: `bb6ff64` test, `46b7bf7` mã, `7b5461b` test); diff riêng vòng 2: `ac1a958..7b5461b`; 3 file, đều trong touchpoint. Số vòng: 2 (trần `max_rework` = 3). Review checklist (10): 10/10.
- Điểm của vòng 1: (a) nguồn của "gán" — ADDRESSED (`daily_report.py:117-131`, chỉ từ `assign_owner` ok; `predicted_assignee` ra khỏi phép đếm và `fields`; ghim bởi `test_assign_counted_from_ok_assign_owner_only`); (b) ánh xạ tool, "trả lời", "đóng" — ADDRESSED (`create_routed_task` → Task, `post_routing_comment` → comment, `apply_route` không đếm; "trả lời" 0 trên mã nền theo Điểm 2.3; "đóng" qua `kpi.is_bot_close` trước bảng tool, `daily_report.py:136-145`); (c) STD-DESIGN-4 — ADDRESSED (`_ok_actions` đã bỏ; `kpi.log_actions` thân giữ nguyên, `kpi.py:208-216`; `git grep` trên `7b5461b` không còn `_actions`, `_ok_actions` dưới `erp_ai/`; `_bot_closed` hành vi không đổi).
- Đã kiểm thêm: `is_bot_close` (`kpi.py:197-205`) đúng Returns; `ACTION_KIND_BY_TOOL`, `TOOLS_COUNTED_ELSEWHERE` đúng chữ Returns, `{"apply_route", *runner.PROPOSE_TOOLS}` bằng `TOOLS_COUNTED_ELSEWHERE` (`runner.py:100`); thứ tự phân loại đúng Returns; STD-TEST-6: mọi `creation` là mốc cố định năm 2002, cửa sổ từ mốc neo cố định, có test biên, mỗi test xóa phần dư của cửa sổ trước khi gieo và rollback sau.
- Ca chi phí của `TestBuild::test_bot_actions_and_cost_yesterday`: cột `cost_usd` là Float `precision: "6"` (`erp_ai_log.json:184-189`) → `decimal(21,6)` (`frappe/database/schema.py:346-353`), nên dòng `cost_usd=0.0000004` lưu thành 0.0 và không góp vào tổng; mọi giá trị lưu có nhiều nhất 6 chữ số thập phân nên không cách gieo nào làm phép làm tròn 6 chữ số khác 7 chữ số; lối dự phòng ở `design-w1-fixes-18.md:170` cũng không thể đạt. Khẳng định `== 0.300001` (`test_daily_report.py:554`) vẫn xanh khi bỏ `round(…, 6)` (reviewer tính tay IEEE-754, chưa chạy). Phán của reviewer: không phải finding về mã hay test (mã đúng Returns, chú thích `:498-499` của dev đúng); là lỗi thiết kế của dòng Expect. Gợi ý cho designer: bỏ dòng 0.0000004 và chữ "6 so với 7 chữ số", thay bằng ca chỉ `round` mới qua (hai dòng hôm qua `cost_usd` 0.1 và 0.2, không chi phí khác, `cost_yesterday == 0.3`; thiếu `round` ra 0.30000000000000004).

### Findings

- major | STD-TEST-2 | erp_ai/agent/kpi.py:200 | Vế "`ticket` khác rỗng" của `is_bot_close` (Returns) chưa có test: không dòng gieo nào có `ticket` rỗng/None đi cùng mục `name` None, `doctype` HD Ticket, `value_after.status` Closed; bỏ vế `ticket and` thì `None == None` qua và mọi test vẫn xanh. | Thêm một ca trong `TestBotActions`: dòng `reason` không có `ticket` với mục `api_update_record` (HD Ticket, `name` None, ok, `value_after={"status": "Closed"}`), mong `đóng` 0 và `khác` 1; dán đỏ của đột biến bỏ `ticket and`. | confirmed (đọc; không test nào chạm đường này)
- minor | — | — | 2 điểm nhỏ: (1) không test nào gieo mục vừa là bot đóng vừa thuộc `TOOLS_COUNTED_ELSEWHERE`, đổi chỗ bước 1 và 2 vẫn xanh (mã nền không tool nào ghi được mục như vậy); (2) thân commit `bb6ff64` nói dòng 0.0000004 "checks the 6-digit rounding (0.3000014 -> 0.300001)", sai; `7b5461b` chỉ sửa chú thích trong test. | dev's call

### Ngoài phạm vi

Không có.

### Không kiểm được từ diff

- 18 / 7 / 187 test xanh và `LINT_EXIT=0`: chạy lại `test_daily_report`, `test_kpi`, `test_architecture` dưới khóa site sau merge.
- `test_layer_imports` chấp nhận `daily_report → kpi`: cùng lần chạy đó.
- Phép tính float ở trên là tính tay: bỏ `round` với dữ liệu gieo hiện tại mà `TestBuild::test_bot_actions_and_cost_yesterday` vẫn xanh thì xác nhận.
- MariaDB lưu 0.0000004 thành 0 không báo lỗi ở chế độ strict: dòng GREEN của dev ngụ ý có.

### Bằng chứng của dev (nguyên văn, kèm trong lời giao review)

- RED trên `bb6ff64` (sau `MIGRATE_EXIT=0`; dev tự báo lần chạy lại này lọc dòng `Enqueuing HelpdeskSearch` bằng `grep -v`, lần đầu không lọc lỗi khắp nơi `TypeError: unsupported type for timedelta hours component: str` trước khi migrate): `test_assign_counted_from_ok_assign_owner_only` `'gán': 3` / `'khác': 4`; `test_routing_task_and_comment_kinds` `'Task': 0`, `'comment': 0`, `'khác': 4`; `test_propose_counted_once` `AttributeError: module 'erp_ai.agent.daily_report' has no attribute 'TOOLS_COUNTED_ELSEWHERE'`; `test_close_reply_and_classification_kinds` `'đóng': 0`, `'khác': 5`; `test_empty_day_zero_float` `AssertionError: 0 is not an instance of <class 'float'>`; `TestBuild::test_bot_actions_and_cost_yesterday` `{'create_task': 'Task', 'post_comment': 'comment'} != {...}`; `Ran 18 tests in 2.990s` / `FAILED (failures=5, errors=1)`.
- Đột biến (test ghim, không commit): bỏ `entry_type == "classify"` → `'phân loại': 1` so với 0, `FAILED (failures=1)`; đổi `is not True` thành `not action.get("ok")` → `'Task': 1` so với 0, `FAILED (failures=1)`.
- GREEN trên `7b5461b`, một lần giữ khóa, `MIGRATE_EXIT=0` (dev tự báo đầu ra đi vào file nháp): test_daily_report `Ran 18 tests in 3.080s` OK; test_kpi `Ran 7 tests in 4.379s` OK; test_architecture `Ran 187 tests in 16.785s` OK. `pre-commit run --all-files`: `LINT_EXIT=0`.
- Hai điểm designer chưa chạy (quyết định 17:53 (b)): (i) giờ của `creation` so với `anchor` — xác nhận (múi giờ site Asia/Ho_Chi_Minh, cả hai là datetime không múi giờ theo giờ site; dòng gieo `2002-07-01 10:00` đọc lại không đổi và nằm trong cửa sổ `[2002-07-01, 2002-07-02)`); (ii) cột làm tròn khi lưu, 0.0000004 thành 0.0, lối dự phòng của thiết kế không đạt được; dev giữ giá trị gieo như Expect, không chọn lối ra.

## Kết luận của tech-lead (vòng 2)

DỪNG riêng chuỗi T52 → T53 → T54 lần hai (`design-defect`: báo lên, không thiết kế lại, không sửa dòng task). KHÔNG merge, KHÔNG tick. Nhánh `team/FEAT-007-task-52` @ `7b5461b` giữ. Cần designer: viết lại vế chi phí của dòng Expect T52 (`tasks.md:649`, `design-w1-fixes-18.md` Điểm 4 và `:170`). Finding major STD-TEST-2 (`kpi.py:200`) còn mở, chuyển nguyên văn cho dev ở vòng 3/3 cùng với dòng Expect mới. Vòng 3 là vòng cuối trong trần `max_rework`.
