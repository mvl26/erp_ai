Feature: FEAT-007
Stage: build
Author-agent: tech-lead
Date: 2026-11-15

# Review T180 — Việc quét 15 phút cô lập lỗi từng phiếu

## Vòng 1 (2026-11-15, lượt build 18) — `request-changes`

- Lệnh diff (reviewer tự chạy): `git log --format='%h %s%n%b' ed341b9..6fd8189`, `git diff --stat ed341b9..6fd8189`, `git diff ed341b9..6fd8189`, `git show ed341b9:erp_ai/agent/test_missed_scan.py`, `git show 6fd8189:erp_ai/agent/{missed_scan,queue,policy}.py`, `git show --stat 4530648`. 2 file, đều là touchpoint; `hooks.py` không đổi. Reviewer dùng 10/18 lượt, không chạy test.
- Tầng 1: mã khớp hình dạng mã của `design-w1-fixes-17.md` Điểm 2 từng dòng (hằng, tham số chỉ-từ-khóa `failures`, trần ở cả hai vòng, một danh sách chung, một `log_error` và một `logger.error`, không dòng `info`, lối T34 cho lỗi cả lần chạy). Phiếu lỗi không vào `found` nên không tính vào `SCAN_BATCH`. Năm test của Expect có đủ, đúng chỗ vá và đúng chuỗi. Không test nào khác của file đổi.

Đối chiếu test bị xóa (STD-TEST-5; lý do xóa nằm trong commit `4530648`), bảng của reviewer:

| Test cũ / khẳng định | Nay được kiểm ở |
|---|---|
| enqueue_error: `log_error == [call(TITLE, "missed_scan error=RuntimeError")]` | `test_enqueue_error_on_one_ticket_still_queues_the_rest`, chữ `failed=1 error=RuntimeError` (đổi có chủ ý theo thiết kế) |
| enqueue_error: không `SECRET_TEXT`, không tên phiếu trong `log_error` | cùng test, qua `_assert_one_constant_title_error` |
| enqueue_error: logger `[error("lỗi %s, đã xếp %s phiếu","RuntimeError",1)]`, lần chạy dừng ở lỗi | cùng test: `[error("lỗi %s ở %s phiếu, …","RuntimeError",1,2)]`; phiếu thứ ba nay được xếp (đảo có chủ ý) |
| enqueue_error: không ngoại lệ thoát ra | ngầm trong `_scan_with_error`, giữ |
| policy_error: `log_error == [call(TITLE, "missed_scan error=RuntimeError")]` | `test_run_level_error_logged_once_and_swallowed` (ném từ `is_enabled`); dạng theo phiếu: `test_ticket_that_always_raises…` (`failed=1`), `test_per_ticket_failures_stop_at_the_cap` (`failed=2`) |
| policy_error: không `SECRET_TEXT`, không tên phiếu | cả ba test trên |
| policy_error: logger `[error("lỗi %s, đã xếp %s phiếu","RuntimeError",0)]`, không job nào | test lỗi cả lần chạy (đúng dòng đó); test trần có queued=0 |
| policy_error, ngầm: lỗi ném BÊN TRONG `find_missed_tickets` đi lối T34 | mất một phần: test lỗi cả lần chạy chỉ ném ở `is_enabled`; lỗi từ SQL ứng viên, `_agent_enabled_at`, đọc `max_runs` không còn test (minor (b)) |

Finding (nguyên văn):

- major | STD-TEST-8 | erp_ai/agent/missed_scan.py:113 (tests at erp_ai/agent/test_missed_scan.py:324-360) | The failure cap in the enqueue loop has no test. Only the find-loop cap (:82) is tested, and test_enqueue_error has a single failure. Deleting the `if len(failures) >= SCAN_MAX_FAILURES: break` at :113 keeps all 19 tests green. So does giving the enqueue loop its own list, which breaks the "one list for both loops" rule. | Add a test: patch `SCAN_MAX_FAILURES` to 2 with `create=True`, three tickets, `enqueue_agent_run` always raising. Expect exactly 2 `enqueue_agent_run` calls, `failed=2`, logger `(…,"RuntimeError",2,0)`. Optionally add a case where one predicate failure and one enqueue failure together reach the cap. | confirmed (mutation found by reading; not run)
- minor | — | — | 3 small points: (a) No test shows that failed tickets don't count toward `SCAN_BATCH`; a guard like `len(found)+len(failures)==SCAN_BATCH` would pass with 3 tickets and a batch of 50. (b) A run-level error raised inside `find_missed_tickets` (candidate SQL, `_agent_enabled_at`, `max_runs` read) has had no test since the policy_error test was deleted. (c) green.txt shows no commit hash or module name. | dev's call

Review checklist (10): 1 ok · 2 ok · 3 major (lối lỗi của trần ở vòng xếp job) · 4 ok · 5 ok · 6 ok · 7 ok · 8 ok · 9 n/a · 10 ok.

Lỗi và log (STD-ERR-1, STD-SEC-6): các `except` gom lỗi và báo một lần, docstring nêu lý do; chữ log chỉ có tên lớp lỗi và con số. `except Exception` rộng: không thành finding (phần theo phiếu chỉ đọc; `enqueue_agent_run` chỉ chạm `frappe.flags` và Redis sau commit; mất kết nối thì mọi phiếu lỗi, dừng ở trần 50, `log_error` cuối ném ra, scheduler rollback như T34).

RED/GREEN: RED đúng lý do, commit test trước commit mã. Lần GREEN của dev ghi vào file bằng chuyển hướng; reviewer tự đọc các dòng kết quả trong file đó và chỉ nhận là bằng chứng phụ (file không cho biết chạy trên commit nào).

Không kiểm được từ diff:

- Lần GREEN có chạy trên `6fd8189` hay không → chạy lại `cmd.test_one` của `erp_ai/agent/test_missed_scan.py` sau khi sửa.
- `frappe.enqueue(deduplicate=True)` có gọi Redis đồng bộ (có thể ném theo từng phiếu) hay không; reviewer không đọc mã Frappe.

Xử lý: vòng sửa 1/3, finding major chuyển nguyên văn cho dev (FIX_BASE=`6fd8189`). Test thêm nằm trong touchpoints và nhánh mã đó do chính hình dạng mã của thiết kế đòi, nên là `request-changes`, không phải `design-defect`.

## Vòng 2 (2026-11-15, lượt build 19) — soát hẹp trên diff sửa — `approve`

- Lệnh diff (reviewer tự chạy): `git log --format='%h %s%n%b' 6fd8189..5f3f515`, `git diff --stat 6fd8189..5f3f515`, `git diff 6fd8189..5f3f515`, `git show 5f3f515:erp_ai/agent/{missed_scan,test_missed_scan}.py`. Hai commit: `9ba45a6` (test), `5f3f515` (chỉ định dạng); 1 file `test_missed_scan.py` +86, không đổi mã. Reviewer dùng 7 lần gọi tool, không chạy test hay phép đột biến. Lần gọi dev vòng sửa đầu tiên (round 114, lượt 18) bị cắt bởi lần khởi động lại máy; bản dở chưa commit không được dùng, dev làm lại từ `6fd8189` (quyết định 17:50 (c)).
- major STD-TEST-8 `missed_scan.py:113`: ADDRESSED. `test_enqueue_failures_stop_at_the_cap` (`test_missed_scan.py:361-383`: trần 2, ba phiếu, `enqueue_agent_run` luôn ném → đúng 2 lời gọi, `failed=2`, logger `(…,"RuntimeError",2,0)`) bắt việc bỏ `break`; `test_predicate_and_enqueue_failures_share_one_cap` (`:385-415`: một lỗi ở vị từ cộng một lỗi lúc xếp job chạm trần 2 → lời gọi đúng `[tickets[1]]`) bắt việc tách danh sách riêng.
- minor (a) (phiếu lỗi không tính vào `SCAN_BATCH`): ADDRESSED, `test_failed_tickets_do_not_count_toward_the_batch` (`:417-435`). minor (b) (lỗi cả lần chạy ném bên trong `find_missed_tickets`): ADDRESSED một phần, `test_run_level_error_inside_find_logged_once_and_swallowed` (`:437-445`) ném từ `_agent_enabled_at`; lỗi từ SQL ứng viên và lần đọc `max_runs` vẫn chưa có test. minor (c) và mục "không kiểm được" của vòng 1 (GREEN chạy trên commit nào): ADDRESSED, dev nêu đầu nhánh `5f3f515`.
- Finding mới trong diff sửa: không có blocker hay major. Một minor: commit `5f3f515` riêng cho định dạng cho thấy `9ba45a6` tự nó chưa qua ruff format (STD-GIT-2); dev cũng tự báo loại `style` không nằm trong danh sách loại commit và hook đã cảnh báo. Review checklist (10) trên diff sửa: 1 ok · 2 ok · 3 ok · 4 ok · 5 ok · 6 ok · 7 n/a · 8 ok · 9 n/a · 10 ok.

Bằng chứng của dev ở vòng này (nguyên văn dòng kết quả; migrate rồi chạy trong một lần giữ khóa, `MIGRATE_EXIT=0`): đột biến (1) bỏ `break`, trên `9ba45a6`: `FAIL: test_enqueue_failures_stop_at_the_cap` `AssertionError: 3 != 2`, `FAIL: test_predicate_and_enqueue_failures_share_one_cap` `Lists differ: ['43071', '43072', '43073'] != ['43071']`, `Ran 23 tests in 10.109s` / `FAILED (failures=2)`; đột biến (2) vòng xếp job có danh sách riêng: `FAIL: test_predicate_and_enqueue_failures_share_one_cap` `Lists differ: ['43071', '43072'] != ['43071']`, `Ran 23 tests in 11.251s` / `FAILED (failures=1)`; sau khi trả lại file (`git diff --stat` của `missed_scan.py` rỗng): `Ran 23 tests in 11.183s` / `OK`, test_architecture `Ran 185 tests in 16.374s` / `OK`; đầu nhánh `5f3f515`: `Ran 23 tests in 10.331s` / `OK`; `pre-commit run --all-files` mọi hook Passed, `LINT_EXIT=0`. Dev tự báo: một lần chạy trên `5f3f515` không `migrate` trước ra `FAILED (failures=1)` ở `test_cron_declared_every_15_minutes` (`None != ('Cron', '*/15 * * * *')`) vì nhánh khác vừa `migrate` site dùng chung; chạy lại có `migrate` trong cùng lần giữ khóa thì `OK`. Lint chạy cùng lúc với lần chạy đột biến nên ruff định dạng lại file test giữa chừng; đầu nhánh cuối chạy riêng vẫn `OK`.

Không kiểm được từ diff (tech-lead xử lý trước tick):

- Các lần chạy đột biến và lần xanh trên `5f3f515` chỉ là bằng chứng trong lời giao → lần chạy sau merge của tech-lead chạy lại cả file.
- `test_failed_tickets_do_not_count_toward_the_batch` (`:417`) không gọi `_enable_agent`; chỉ xanh nếu `policy.can_send_ticket` thật không xét cờ bật của agent → lần chạy `Ran 23 tests … OK` trên `5f3f515` và lần chạy sau merge cho thấy test xanh với vị từ thật; không phải chỗ hở.

deferred (không chặn): (1) mọi lỗi trong mọi test đều là `RuntimeError`, nên đổi `failures[0]` thành `failures[-1]` ở `missed_scan.py:120-121` vẫn xanh; thiết kế muốn báo lỗi đầu tiên → cho vị từ và lần xếp job ném hai lớp lỗi khác nhau ở test `:385` và chờ `error=ValueError`; (2) lỗi từ SQL ứng viên và lần đọc `max_runs` chưa có test; (3) loại commit `style` của `5f3f515` (STD-GIT-2), lịch sử không viết lại.

Số vòng: 2 (vòng sửa 1/3). Verdict cuối: `approve`.
