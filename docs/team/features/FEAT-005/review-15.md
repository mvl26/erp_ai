Feature: FEAT-005
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 15 — FEAT-005 T15

Tech-lead chép từ tin trả về của reviewer (reviewer không ghi file).

- Diff: `git diff 79ad5d0..863a303` (nhánh `team/FEAT-005-task-15`, 1 commit, `erp_ai/agent/test_agent_runner.py` +81); merge `7d85356`
- Vòng: 1
- Verdict: approve

## Vòng 1 — approve (`79ad5d0..863a303`)

Lớp 1: đạt Expect của T15 và design-amd2 §8. `test_role_change_via_record_tool_alarmed_once` (lớp `TestRunnerPrivilegeAlarmEndToEnd`) nằm trong file touchpoint duy nhất; một test, không sửa mã sản phẩm, không sửa test có sẵn.

- Dòng nhật ký do runner thật ghi: `_run("comment_mention")` đi qua `api_update_record` → `_record_snapshot` → `write_entry`; test khẳng định đúng một dòng `reason` và `actions == [("api_update_record","User",True)]`; chỉ đổi `creation` của dòng đó (bộ lọc thời gian của job).
- Phần bị patch: `erp_ai.alerts.send_alarm` và `frappe.log_error`. `send_alarm` thật ghi Error Log (MyISAM, rollback không xóa) trước khi gửi thư nên patch là cần cho cô lập, không phải lối tắt; chuỗi được khẳng định (runner → nhật ký → job → chữ cảnh báo) vẫn giữ. `log_error` không bao giờ reset nên `assert_not_called` bắt cả lần chạy runner lỗi và "lock busy".
- Cô lập (STD-TEST-6): user, role, dòng log, mốc được `RunnerTestBase` rollback; job không commit trong test (`frappe.flags.in_test`, `tasks.py:299`, thêm chốt commit ở `test_agent_runner.py:94`); mốc và `creation` đặt ở 2031 nên dòng đã commit trên site nằm ngoài cửa sổ; hai role là role lõi của Frappe, không thuộc `FORBIDDEN_ROLES`; khóa file theo site là khóa thật, bị giữ thì test đỏ rõ trong 60 s, không xanh giả.
- "Đúng 1" và "0 ở lần hai" có sức phân biệt: nội dung cảnh báo so bằng danh sách chuỗi đúng từng chữ (user, role, người ra lệnh, thời điểm); user đã có sẵn `Blogger` do người cấp và role đó không được xuất hiện; không tiến mốc thì lượt T+25h đỏ.

- Phát hiện blocker/major: không.
- minor | — | — | 3 điểm nhỏ: (a) `setUp` đăng ký `clear_cache(user=ALARM_USER)` sau `make_instructor` nên nó chạy TRƯỚC rollback, ngược thứ tự "rollback rồi mới xóa cache" mà `make_instructor` ghi; chưa thấy rò; (b) thời điểm cố định 2031 chỉ đụng dòng commit đúng 2031-11-15 08:00–09:05; (c) kết quả 0 ở T+25h không tách được cửa sổ theo mốc với cửa sổ cố định 24 giờ, đúng thiết kế: test T+49h/T+73h của T11 tách hai ca đó | tùy dev

- Bằng chứng của dev (task chỉ thêm test, đỏ bằng đột biến mã sản phẩm, đã trả lại): (1) `_record_snapshot` không ghi gì → `- ['Agent đã sửa bản ghi phân quyền: sửa User runner.alarm.once@example.com ' '(người ra lệnh runner.instructor@example.com, 2031-11-15 08:10), không có ' 'trước/sau']`; (2) không tiến mốc → `AssertionError: Lists differ: ['Agent đã sửa bản ghi phân quyền: thêm ro[124 chars]10)'] != []`; (3) mục bỏ người ra lệnh → `-  'runner.alarm.once@example.com (2031-11-15 08:10)']`; GREEN `Ran 1 test in 0.818s` / `OK`, cả module `Ran 109 tests in 28.988s` / `OK`.

## Tech-lead đã kiểm

- Sau merge `7d85356`, một lần giữ khóa `miyano-site.lock` 22:50:25–22:51:23 (migrate exit 0; hai cài đặt ghi lại `1` và 4 app, để trống, trả lại, đọc lại khớp): test_agent_runner `Ran 109 tests in 29.261s` / `OK`.
- `git diff --name-only 79ad5d0..863a303` = `erp_ai/agent/test_agent_runner.py` (đúng touchpoint).

## Không kiểm được từ diff

- Scheduler của bench trên `miyano` có thể chạy job hằng ngày cùng lúc và tranh khóa `erp_ai_privilege_alert`: nếu có thì test đỏ rõ trong 60 s. Lượt sau merge ở trên xanh; ghi debt.md cùng minor (c) của review-13.
- Cache mention/enabled-user của Frappe sau rollback: cùng mẫu `make_instructor` đã dùng trong bộ test nền → không có gì thiếu cho T15.

## deferred

- minor (a) → debt.md.
