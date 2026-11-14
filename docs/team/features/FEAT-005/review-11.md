Feature: FEAT-005
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 11 — FEAT-005 T11

Tech-lead chép từ tin trả về của reviewer (reviewer không ghi file).

- Diff: `git diff 71fcce6..eed36f2` (nhánh `team/FEAT-005-task-11`, 3 commit; vòng 1 `71fcce6..0d17d0e` 2 file +122/−1, vòng 2 `0d17d0e..eed36f2` 2 file +15/−2); merge `ab94a57`
- Vòng: 2
- Verdict: approve (vòng 2); vòng 1 request-changes

## Vòng 2 — approve (`0d17d0e..eed36f2`, chấm lại có phạm vi)

- major STD-TEST-2: ADDRESSED. `erp_ai/tests/test_tasks.py:665-680`: với `in_test=False`, `frappe.db.commit` đã patch ghi lại `len(watermark_writes())`, test khẳng định `[1]`; dời lệnh ghi ra sau commit (`[0]`), bỏ commit (`[]`), commit hai lần đều đỏ. Docstring `erp_ai/tasks.py:203-205` khớp mã `:219-224`.
- An toàn cho site dùng chung: đã xác nhận. Không commit thật nào chạy được (patch của test nằm trên `commit_guard` của setUp; `frappe.log_error`, `alerts.send_alarm` đã patch); `addCleanup` lưu giá trị `in_test` gốc trước khi đặt `False` và chạy trên mọi đường.
- minor (b) STD-DOC-7: ADDRESSED. minor (a) STD-GIT-2 và (c): thuộc lịch sử commit, không sửa được nếu không viết lại; không chặn.
- Phát hiện mới: không.
- Bằng chứng của dev vòng 2: đột biến dời `_advance_privilege_watermark(upper)` ra sau `frappe.db.commit()`: `test_tasks.py:678 self.assertEqual(writes_at_commit, [1])` → `AssertionError: Lists differ: [0] != [1]`; GREEN cả module `migrate=0`, `Ran 55 tests in 6.460s` / `OK`.

## Vòng 1 — request-changes (`71fcce6..0d17d0e`)

Lớp 1: AC-19 ca (1), (2), (3), luật "không lùi" và "sau mọi điều kiện" có mã và có test. `lower is None or upper > lower` khớp §4.2 bước 2 và 5. Tên trường mốc chỉ ở `_advance_privilege_watermark` (`tasks.py:192`); `tasks.py` không `save()`/`insert()`. Đúng touchpoint.

- major | STD-TEST-2 | erp_ai/tests/test_tasks.py:658-670 (mã tasks.py:219-222) | Tiêu chí "gọi … trước commit của job" chưa có test. Mọi test ở đây patch `commit` để ném và chạy với `in_test`, nên nhánh commit không bao giờ chạy. Nếu lệnh ghi dời ra sau `frappe.db.commit()`, cảnh báo và mốc rơi vào hai giao dịch (trái ADR-024 QĐ 3.5) mà mọi test vẫn xanh. Các test dự kiến của T13 (lỗi giữa job, khóa bận) cũng không bắt được | trong `test_watermark_written_once_after_all_conditions`, đặt `frappe.flags.in_test=False` (trả lại bằng addCleanup), patch `frappe.db.commit` với side_effect ghi `len(watermark_writes())`, rồi khẳng định `[1]`
- STD-TEST-5, dòng `:527` (`test_job_reads_watermark_and_settled_upper_bound`): ĐẠT. Chữ T8 ghi "Chưa ghi mốc (T11)", nên `(WATERMARK, …)` cũ của lần gọi thứ hai kiểm trạng thái tạm của T8. T11/AC-19 đổi spec: lần chạy thứ hai phải đọc `upper` của lần đầu. Giá trị mới 08:55 đúng hợp đồng đó, test mạnh hơn.
- minor | — | — | 3 điểm nhỏ: (a) STD-GIT-2: `09f5aad` đứng riêng làm đỏ dòng 527 và đưa lại bản cũ của test T10 `test_admin_items_first_each_group_by_time` (dòng 874-905); `0d17d0e` trả lại, thay đổi ròng bằng 0; (b) STD-DOC-7: docstring `check_privilege_escalation` chưa nói job ghi mốc; (c) `test_upper_not_after_watermark_keeps_it` xanh từ trước khi có mã (đúng với test "không ghi"; đỏ nếu mã luôn ghi) | tùy dev
- FEAT-006 `TestRoutingPermissions`, xét từ mã: T11 không đổi được kết quả. setUp ghim mốc `since = now−1s`, cả hai lần gọi job không đối số có `upper = now−300s < since` nên lệnh ghi mới bị bỏ và cửa sổ phân quyền rỗng; `role_drift` chỉ đọc `Has Role` (`tasks.py:93-100`).

- Bằng chứng của dev vòng 1: RED 5 ca, `AssertionError: None != datetime.datetime(2031, 11, 15, 8, 55)`, `Lists differ: [1, 1] != [1, 0]`; GREEN trên `0d17d0e` `Ran 55 tests in 6.582s` / `OK`; 7 đột biến đỏ; `--case TestRoutingPermissions` `Ran 2 tests in 3.831s` / `FAILED (failures=1)` tại `assertEqual(before["role_drift"], [])`, chạy lại `FAILED (errors=2)` (`QueryDeadlockError`).

## Tech-lead đã kiểm

- Phán `--decide` trước review (journal "quyết định (decide) T11"): lần gọi dev 1 trả `DESIGN_CONFLICT` chỉ vì handoff cấm sửa mọi test có sẵn; cho sửa đúng dòng `:527`. Reviewer chấm dòng đó đạt STD-TEST-5.
- `09f5aad` do tech-lead commit từ việc chưa commit của lần gọi dev 1 (chỉ `git add`/`git commit`, không sửa mã) để lần gọi sau tiếp tục được trên nhánh task.
- Sau merge `ab94a57`, một lần giữ khóa `miyano-site.lock` (0 lệnh `run-tests`/`migrate` ngoài khóa, migrate exit 0): test_tasks `Ran 55 tests in 10.093s` / `OK`; `test_runner_routing --case TestRoutingPermissions` `Ran 2 tests in 1.820s` / `FAILED (errors=2)`, cả hai là `QueryDeadlockError (1213)` ở `setUp` → `test_utils.set_agent_settings`; chạy lại theo tên một lần (lần giữ khóa kế tiếp, hai cài đặt để trống rồi trả lại đúng): `Ran 2 tests in 3.535s` / `OK`, 0 deadlock; lỗi `role_drift` dev thấy trước đó không còn.
- `git diff --name-only 71fcce6..eed36f2` = `erp_ai/tasks.py`, `erp_ai/tests/test_tasks.py` (đúng touchpoint).

## Không kiểm được từ diff

- `test_change_before_rollout_alarmed_on_first_run_only` đọc cả lịch sử nhật ký của site (`lower=None`): một dòng `reason` thật có `actions` hỏng sẽ làm nó đỏ cho tới T12 (test T8 `test_empty_watermark_reads_from_the_start` đã có rủi ro này) → T12 đóng; qa lưu ý.
- Lúc chạy thật có đường mã Frappe nào khác phụ thuộc `in_test` (enqueue, cache) bị chạm trong test đổi cờ hay không: chưa kiểm khi chạy → qa.

## deferred

- Chưa có gì ghim việc dòng Error Log của cảnh báo được ghi trước commit (chỉ mốc được ghim) → đưa vào handoff T13 (test lỗi giữa job).
- minor (a) STD-GIT-2 của `09f5aad`: không squash (lệnh "không amend/reset"); merge `--no-ff` `ab94a57` đưa cả ba commit vào nhánh cùng lúc.
- review-10 minor (a) (thứ tự nhóm `[QUẢN TRỊ]` trùng thứ tự chữ cái): dev lần gọi 1 đã sửa, lần gọi 3 trả lại theo phán "chỉ một dòng" → còn mở, đưa vào handoff T12.
