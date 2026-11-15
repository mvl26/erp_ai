Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 34 — FEAT-007 T34

- Diff vòng 1: `git diff f2ab42ea931bfcb1ad4cc5a760a047f40249d153..55735df` (nhánh `team/FEAT-007-task-34`; 2 commit `54582fe` test, `55735df` mã; 3 file +140/−6, đều là touchpoint)
- Trần `max_rework` = 3
- File này do tech-lead ghi từ báo cáo của reviewer (vai reviewer không ghi file dưới `docs/`); chữ của reviewer giữ nguyên ý, finding giữ nguyên văn.

## Vòng 1 — request-changes

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED trên mã T33 (migrate exit 0): `Ran 14 tests`, `FAILED (failures=4, errors=2)`; `AttributeError: module 'erp_ai.agent.missed_scan' has no attribute 'scan_missed_tickets'` (2 test); `test_cron_declared_every_15_minutes` `AssertionError: None != ['erp_ai.agent.missed_scan.scan_missed_tickets']`; `test_candidate_window_keeps_the_newest` `Lists differ: ['43070', '43071', '43072', '43073'] != ['43071', '43072', '43073']`; `test_old_refused_tickets_do_not_starve_a_new_one` `AssertionError: 6 != 3`; `test_warns_once_when_candidate_limit_reached` `AssertionError: [] != [call('missed_scan: chạm trần %s ứng viên, phiếu cũ hơn không được xét', 3)]`. GREEN, một lần giữ khóa, `MIGRATE_EXIT=0`: test_missed_scan `Ran 14 tests OK`, test_architecture `Ran 183 tests OK`, test_install `Ran 56 tests OK`.

Findings:

- major | STD-ERR-4 | erp_ai/agent/missed_scan.py:79-89 | The task's Tiêu chí cites D-17. D-17 (`design.md:75`) says "Một dòng `frappe.logger("erp_ai")` mỗi lần chạy; lỗi → `frappe.log_error` có tiêu đề hằng". `scan_missed_tickets` has no error branch. If `can_send_ticket`, `runs_today` or `enqueue_agent_run` raises for one ticket, the whole run stops and the rest of the batch is never queued. That run writes no logger line and no constant-title `frappe.log_error`. If the same ticket raises every time, every 15-minute run fails on it and newer tickets are never queued (G1). There is also no error-path test (STD-TEST-8). | Wrap the run body the way `erp_ai/tasks.py:89-94` does: `except Exception as exc: frappe.log_error(TITLE_RUN_FAILED, f"missed_scan error={type(exc).__name__}")`. Keep exactly one logger line per run. Add a test that patches `queue.enqueue_agent_run` (or `policy.can_send_ticket`) to raise: assert one `log_error` with `TITLE_RUN_FAILED` and no exception out of the job. Whether each ticket should be isolated (log and continue) or the whole run fails once is for tech-lead or the designer to decide, because design 3.5.1 says nothing on it. | confirmed (the code is missing; the scope is in D-17, which T34 cites)
- minor | — | — | 3 small points: (1) `logger.info` uses an f-string at missed_scan.py:89 while the warning at :66 uses `%s` arguments, so two styles sit in one module (STD-STYLE-4); (2) the test file imports `call` as `unittest_call` but still uses `call` as a loop variable in `_queued_tickets` and in `test_two_scans_one_job_per_ticket`, which is confusing; (3) the `find_missed_tickets` docstring cites "Point 2" in English while the source document says "Điểm 2". | dev's call

Các phép kiểm đã đạt (reviewer):

1. SQL: `CANDIDATES_SQL` xếp `creation desc, name desc`, kết bằng `limit %(limit)s` (`missed_scan.py:34`); giá trị truyền bằng `"limit": SCAN_CANDIDATE_LIMIT` lúc gọi (`:61`); f-string chỉ chèn hằng module (`LOG_DOCTYPE`, `CLASSIFICATION_FIELDS`), không dữ liệu ngoài nào vào câu truy vấn (STD-SEC-3).
2. `find_missed_tickets`: duyệt `reversed(candidates)` (`:70`); bộ lọc, chỗ dừng `SCAN_BATCH`, chữ ký, đầu ra cũ nhất trước không đổi.
3. Cảnh báo trần: đúng một lần khi `len == SCAN_CANDIDATE_LIMIT`, không khi dưới; chữ và tham số khớp Điểm 2 mục 4.
4. `scan_missed_tickets`: agent tắt → một dòng info rồi trả về trước khi gọi `find_missed_tickets`; xếp hàng với `TRIGGER_TICKET_INSERT`; lần quét thứ hai trong cùng giao dịch trả False qua `PENDING_JOB_IDS_FLAG` của `queue.py`, log "xếp 0 phiếu".
5. Test: diff test chỉ thêm sau dòng 161, tám test của T33 không đổi; mỗi test mới đỏ khi hành vi bị trả lại (bỏ `limit` hoặc xếp tăng → [a,b,c,d] hay [a,b,c]; bỏ `reversed` → [d,c,b]; bỏ trần → 6 lời gọi `can_send_ticket`; cảnh báo ở dưới trần → bước hai phiếu đỏ; bỏ chống trùng → danh sách xếp hàng gấp đôi; sai trigger hay `job_id` → subTest đỏ); RED khớp 6 test mới; commit RED trước; không skip; test cô lập (rollback, chặn commit, cửa sổ `creation` năm 2099).
6. `hooks.py`: diff chỉ thêm khóa `cron` với `"*/15 * * * *"`. Touchpoint: đúng 3 file. Commit đúng STD-NAME-5, không dòng ghi công AI.

Mục "không kiểm được từ diff" của reviewer:

- Chống trùng qua hai lần cron riêng (hai giao dịch): dựa vào `deduplicate=True` của RQ với `job_id`, chỉ chặn job còn trong hàng hay đang chạy; đó là ý đồ xếp lại sau lần chạy hỏng, nhưng diff không có test.
- Cách scheduler của Frappe ghi một lần cron hỏng (Scheduled Job Log, Error Log): ngoài diff.
- Ngân sách 300 s với khoảng 1000 ứng viên, `EXPLAIN` trên `tabHD Ticket.creation`: để `/team:verify` (Điểm 2 mục 5).
- Thứ tự chủ `hooks.py` T40 → T34 → T44: lần đổi cuối của `hooks.py` ở BASE là `42f1b45`, reviewer chưa xác nhận đó là T40.

## Kết luận của tech-lead (vòng 1)

- Finding major gửi nguyên văn cho dev (vòng sửa 2/3). Câu "cô lập từng phiếu hay cả lần chạy hỏng một lần": tech-lead không chọn thiết kế; D-17 chỉ đòi `frappe.log_error` có tiêu đề hằng, cách sửa reviewer đề nghị là mẫu có sẵn ở `erp_ai/tasks.py:89-94` (STD-DESIGN-4). Điểm "một phiếu luôn ném thì chặn phiếu mới ở mọi lần quét" chuyển designer qua team-leader, không chặn vòng sửa.

## Vòng 2 — approve (soát lại theo phạm vi)

- Diff vòng 2: `git diff 55735df..9446f28` (2 commit `a01fae5` test, `9446f28` fix; `missed_scan.py` +17/−8, `test_missed_scan.py` +62/−8; `hooks.py` không đổi). Cả task: `f2ab42e..9446f28`.
- Bằng chứng của dev: KHÔNG CÓ. Báo cáo của dev cho vòng sửa này (dòng RED/GREEN) đến một ngữ cảnh skill build tách riêng, ngữ cảnh đó kết thúc khoảng 13:18 mà không ghi lại gì. Lời giao reviewer nói rõ điều này; reviewer chấm bước đỏ bằng cách đọc commit. Tech-lead tự chạy phép đỏ trên `a01fae5` và test sau merge (xem "Kết luận của tech-lead (vòng 2)").

Finding vòng 1:

- major STD-ERR-4 (`missed_scan.py:79-89`): ADDRESSED ở `missed_scan.py:85-98`. Cả thân lần chạy nằm trong `try`; `except Exception` gọi `frappe.log_error(TITLE_RUN_FAILED, f"missed_scan error={type(exc).__name__}")` (`:95`), ghi một dòng `logger.error` với tên lớp lỗi và số phiếu đã xếp (`:96`), rồi trả về; không ngoại lệ nào ra khỏi job. `TITLE_RUN_FAILED` có sẵn ở `erp_ai/constants.py:57` trên `55735df` ("erp_ai: lần chạy lỗi"), `tasks.py:89-94`, `:321`, `:344` dùng cùng cách; chỉ thêm một dòng import nên vẫn trong `files:`. Số dòng logger mỗi lần chạy: lối tắt một `info`; lối thành công một `info` (`:98`); lối lỗi một `error`. Lỗi không bị nuốt im (STD-ERR-1). Chữ log chỉ có tên lớp lỗi và một con số, không có chữ của phiếu hay traceback (STD-SEC-6). Lựa chọn: cả lần chạy hỏng một lần ở lỗi đầu tiên, không cô lập từng phiếu.
- minor (1): giữ (`:98` còn f-string, dòng mới `:96` dùng `%s`). minor (2): ADDRESSED. minor (3): ADDRESSED.

Test mới (reviewer chấm bằng cách đọc mã, không chạy):

- `test_enqueue_error_logged_once_and_swallowed`: đỏ trên `55735df` (không có `try`, `RuntimeError` của lời gọi `enqueue_agent_run` thứ hai thoát khỏi job); xanh trên `9446f28` (lời gọi đầu trả True, lời gọi hai ném: một `log_error(TITLE_RUN_FAILED, "missed_scan error=RuntimeError")`, `method_calls == [call.error(..., "RuntimeError", 1)]`).
- `test_policy_error_logged_once_and_swallowed`: đỏ trên `55735df` (`policy.can_send_ticket` được tra như thuộc tính module ở `:72`, bản vá có hiệu lực, lỗi thoát ra); xanh trên `9446f28` (đếm 0, một `log_error`, một dòng `error`).
- Cả hai kiểm chữ bí mật và tên phiếu không có trong chữ log. Không dấu skip. Tám test của T33 không đổi chữ; trong phần vòng 1 chỉ `_queued_tickets` và `test_two_scans_one_job_per_ticket` đổi tên biến lặp `call` thành `queued` và gập lại một dòng, cùng docstring `_cap`; khẳng định như cũ (STD-TEST-5 giữ).

Hồi quy trong diff sửa (STD-DESIGN-5): không thấy. Bản sửa không gọi `frappe.db.rollback()` như `tasks.py:90`; job này chỉ đọc, rollback sẽ bỏ các job đã xếp mà dòng lỗi đang đếm; không phải finding.

Checklist (10): 10/10 đạt. Commit: hai tiêu đề đúng `type(scope): description (FEAT-007)`, commit test trước, thân rỗng, không dòng ghi công AI.

Findings mới: không.

Mục "không kiểm được từ diff" của reviewer (vòng 2):

- Đầu ra RED/GREEN của vòng này không có; tech-lead chạy `cmd.test_one` cho `erp_ai/agent/test_missed_scan.py` và `erp_ai/tests/test_architecture.py` sau merge.
- `frappe.log_error` và các job đã xếp có được commit khi job trả về bình thường sau lỗi hay không: tùy cách scheduler của Frappe commit và việc `enqueue_agent_run` có hoãn tới sau commit không; reviewer không đọc hai chỗ đó.
- Cho tech-lead hoặc designer: lần chạy dừng ở lỗi đầu tiên nên một phiếu luôn ném vẫn chặn phiếu mới (G1); nay nó hiện thành một Error Log mỗi 15 phút. Thiết kế 3.5.1 và D-17 không nói.
- Ngoài phạm vi: lần đọc `tasks.md:457-478` của reviewer có thấy dòng `progress:` của T34, reviewer không dùng làm bằng chứng. Reviewer dùng 8/12 lượt.

## Kết luận của tech-lead (vòng 2)

- Verdict cuối: approve ở vòng 2 (trần 3); merge `09b5438` trên `team/FEAT-007`.
- Phép đỏ thay cho báo cáo dev đã mất: tech-lead chạy `cmd.migrate` rồi `cmd.test_one` của `erp_ai/agent/test_missed_scan.py` trên commit test `a01fae5` (worktree tách, một lần giữ khóa site, `MIGRATE_EXIT=0`): `ERROR: test_enqueue_error_logged_once_and_swallowed`, `ERROR: test_policy_error_logged_once_and_swallowed`, cả hai `RuntimeError: ERPAI-TEST nội dung phiếu bí mật`, `Ran 16 tests in 8.720s`, `FAILED (errors=2)`. Đỏ đúng lý do reviewer đọc ra (lỗi thoát khỏi job), 14 test còn lại xanh.
- Chạy test sau merge `09b5438`, một lần giữ khóa site, `MIGRATE_EXIT=0`: test_missed_scan `Ran 16 tests in 8.847s OK`, test_install `Ran 56 tests in 21.203s OK`, test_architecture `Ran 185 tests in 16.653s OK`; mọi `TEST_EXIT=0`.
- Commit sau lối lỗi và việc một phiếu luôn ném chặn phiếu mới: thiết kế 3.5.1 và D-17 không nói; tech-lead không chọn thiết kế. Chuyển designer qua team-leader (dòng DỪNG lượt 16), không chặn merge: hành vi sau sửa đúng chữ D-17 (một dòng logger mỗi lần chạy, lỗi → `frappe.log_error` có tiêu đề hằng).

## deferred

- minor (1) vòng 1 (hai kiểu định dạng chữ log trong một module) → `/team:clean`.
- Chống trùng qua hai lần cron riêng, ngân sách 300 s với 1000 ứng viên, `EXPLAIN` trên `creation` → `/team:verify`.
- Cô lập từng phiếu hay cả lần chạy hỏng một lần; commit sau lối lỗi → designer.
