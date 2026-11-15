Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 71 — FEAT-007 T71

- Diff: `git diff caa555a7158708ed8ff377c864da338ea7a9464a..5bd64f0` (nhánh `team/FEAT-007-task-71`; 3 commit `5bb8e4e` test, `cf9ffa7` test, `5bd64f0` mã; 3 file +228/−4, đều là touchpoint)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve; merge `e09454c` trên `team/FEAT-007`
- File này do tech-lead ghi từ báo cáo của reviewer (vai reviewer không ghi file dưới `docs/`); chữ finding của reviewer giữ nguyên.

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED lần đầu (`5bb8e4e`), `MIGRATE_EXIT=0`: `FAIL: test_counts_only_run_limit_triggers … AssertionError: 5 != 2`, test_policy `Ran 57 tests in 2.775s FAILED (failures=1)`; `FAIL: test_run_limit_triggers_subset_of_log_triggers … Lists differ: ['agent/policy.py: RUN_LIMIT_TRIGGERS missing'] != []`, test_architecture `Ran 183 tests in 16.105s FAILED (failures=1)`. Lần giữ khóa hai (đã có mã, trước commit test thứ hai): test_policy `AssertionError: 3 != 2`, `Ran 57 tests in 2.924s FAILED (failures=1)`. RED đo lại trên `cf9ffa7`: `AssertionError: 4 != 2`, `Ran 57 tests in 2.670s FAILED (failures=1)`; `RUN_LIMIT_TRIGGERS missing`, `Ran 183 tests in 15.804s FAILED (failures=1)`. GREEN @ `5bd64f0`, `MIGRATE_EXIT=0`: test_policy `Ran 57 tests in 2.609s OK`, test_architecture `Ran 183 tests in 15.971s OK`, test_agent_runner `Ran 110 tests in 29.809s OK`, test_runner_status `Ran 39 tests in 10.044s OK`.

Theo từng mục checklist (10):

1. Phạm vi (STD-DESIGN-5, STD-TEST-2): đạt. Đúng Returns: `RUN_LIMIT_TRIGGERS = (TRIGGER_TICKET_INSERT, TRIGGER_COMMENT_MENTION)` import từ `constants.py`, không chuỗi viết tay (phán quyết 2); một vế lọc `"trigger": ("in", RUN_LIMIT_TRIGGERS)`; vế `entry_type` giữ. Hai test của Expect có mặt. Ca C-3 (dòng `reason` có trigger ngoài tập không được đếm) là dòng `change-reason`. Không gì ngoài Returns.
2. Touchpoint (STD-DESIGN-1, STD-STRUCT-1/2): đạt. Chỉ 3 file khai báo, không file mới.
3. Test trước (STD-TEST-1/8/4): đạt. RED đúng lý do ở cả ba lần đo. Bỏ vế lọc cho 4; thu về một trigger cho 1; thêm `change_action` vào tập thì ghim tuple đỏ. Không skip/xfail.
4. Sửa test và độc lập (STD-TEST-5/6): đạt. `TestPolicy._log` nay đặt `trigger=TRIGGER_TICKET_INSERT` tường minh, đúng giá trị Frappe vốn lưu (option đầu của Select, điền cho None), không kỳ vọng nào đổi. `cf9ffa7` bỏ dòng `trigger=None`: dòng đó không bao giờ lưu được None, đây là sửa fixture, không uốn khẳng định theo mã. `TestRunsToday` dùng phiếu mới, chốt chặn commit và rollback từng test.
5. Lỗi và biên (STD-ERR-1/2/5): không áp dụng.
6. Bảo mật (STD-SEC-1/3/4/6): đạt. Giá trị lọc đi qua dict của `frappe.get_all`; không bí mật, không `protected_paths`.
7. Hợp đồng (STD-DESIGN-3, STD-OPS-2): đạt. Chữ ký không đổi, không schema, không migrate. Ở `5bd64f0` mọi dòng `classify`/`reason` do `run_log.write_entry` tạo, hàm này từ chối trigger ngoài `TRIGGERS` (`run_log.py:125-127`); dòng change dùng `change_action` với `entry_type="change"`. Nên số đếm hôm nay không đổi với mọi nơi gọi: `runner.py:160`, `missed_scan.py:55`, `test_runner_status.py:283`.
8. Tên, cấu trúc, style (STD-NAME-1/2, STD-STYLE-4/5): đạt.
9. Phụ thuộc (STD-DEP-1/3/5): không thêm.
10. Commit, nhánh, tài liệu (STD-NAME-4/5, STD-GIT-1/8, STD-DOC-2): đạt. Ba commit đúng dạng `type(scope): … (FEAT-007)`, không dòng ghi công AI.

Luật kiến trúc: không bắt nhầm mã đã merge (khẳng định đầu chạy trên `self.sources`, GREEN có trong bằng chứng); mẫu tuân thủ qua `assertRuleSamples`; tám ca vi phạm đều bị bắt (hằng không có trong log, chuỗi không có trong log, log bỏ một trigger giới hạn, thiếu tuple giới hạn, thiếu `TRIGGERS` của log, tuple tính toán, hằng lạ, thiếu file policy); hai biến thể được phép qua (log thêm `kb_draft`, log gọi tên hằng).

Findings:

- Không blocker, không major.
- minor | — | — | 3 small points, dev's call: (a) STD-TEST-8, `test_policy.py:821-828`: the test pins the tuple's value and the count, but not that the filter reads the constant. Writing the two literals straight into the filter stays green, which breaks ADR-033's "defined once" and U6b's one-line extension. Fix: add a `patch.object(policy, "RUN_LIMIT_TRIGGERS", (TRIGGER_TICKET_INSERT,))` case expecting 1. (b) STD-STYLE-5, `test_policy.py:799-800`: the class comment still says "(or none)" after `cf9ffa7` dropped the None row. A `trigger=""` row does persist (`_validate_selects` skips empty values), so the clause could be kept by seeding `""`; otherwise drop the words. (c) STD-TEST-8, `test_architecture.py:4505-4517` and `:4905-4931`: every not-logged case puts the missing trigger last in the tuple, so checking only `limited[-1:]` stays green. There is also no violating case for a missing `run_log.py` or `constants.py`. Fix: put the missing trigger first in one case and add two file-missing samples. | dev's call

Mục "không kiểm được từ diff" của reviewer:

- Dòng ERP AI Log cũ có `trigger` NULL hoặc rỗng tạo trong ngày sẽ thôi được đếm; chỉ có nghĩa nếu có dòng ghi trước khi `write_entry` bắt buộc `trigger`; cần truy vấn site.
- `find_missed_tickets` chưa có nơi enqueue; ADR-033 QĐ 4 nói lần chạy của việc quét tính là `ticket_insert`; kiểm khi việc quét nối vào `enqueue_agent_run`.
- Lần chạy do người yêu cầu trả lời chưa được đếm như NFR-2 chờ; phán quyết (2) để cho U6b (thêm `TRIGGER_REQUESTER_REPLY` cùng commit, đổi luật thành `set(TRIGGERS) - set(RUN_LIMIT_TRIGGERS) == {TRIGGER_KB_DRAFT}`).
- Reviewer không chạy test.

## Kết luận của tech-lead

- Chạy test: xem dòng progress của T71 trong `tasks.md` (một lần giữ khóa sau merge, có `migrate`; gồm cả `test_missed_scan` vì `missed_scan.py:55` gọi `runs_today` và T33 vừa merge).
- Dòng log cũ có `trigger` rỗng: không phải chỗ hở của T71 trên site dev (mọi dòng `classify`/`reason` đi qua `write_entry`, hàm đã từ chối trigger ngoài `TRIGGERS`); chuyển `/team:verify` đo trên dữ liệu thật trước khi lên prod. Không chặn tick.
- Hai mục còn lại thuộc T34/T44 (nối việc quét) và U6b; ghi vào dòng DỪNG lượt 15 cho team-leader.
- minor (a), (b), (c): không mở vòng sửa; (a) nên dọn ở task kế chạm `test_policy.py`.
