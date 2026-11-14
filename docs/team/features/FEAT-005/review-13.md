Feature: FEAT-005
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 13 — FEAT-005 T13

Tech-lead chép từ tin trả về của reviewer (reviewer không ghi file).

- Diff: `git diff 67f926b..f773c40` (nhánh `team/FEAT-005-task-13`, 1 commit, `erp_ai/tasks.py` +30, `erp_ai/tests/test_tasks.py` +241; 2 file +265/−6); merge `79ad5d0`
- Vòng: 1
- Verdict: approve (code) + design-defect (một vế của tiêu chí, thuộc ADR-024 / design-amd2, không thuộc mã)

## Vòng 1 — approve (code) + design-defect (clause) (`67f926b..f773c40`)

Lớp 1: design-amd2 §4.2 bước 1, bước 5 (trừ vế Error Log) và bước 6 đạt; mục hoãn từ review-11 (dòng Error Log cảnh báo ghi trước commit của job) đạt. Chỉ sửa trong touchpoint; `test_error_is_logged_and_rolled_back_not_raised` không đổi.

Vế mở "rollback cả Error Log cảnh báo":

1. Không tới được như design viết: `send_alarm` ghi dòng cảnh báo qua `frappe.log_error` (`alerts.py:18`), bảng khai MyISAM (`frappe/core/doctype/error_log/error_log.json:6`), bỏ qua rollback và rollback savepoint. "Một giao dịch, rollback cả ba" không thể xảy ra từ `tasks.py` hay `test_tasks.py`. Hai lối ra, chưa lối nào được thiết kế: xóa bù dòng đó ở nhánh `except` (nhưng `send_alarm` không trả tên dòng, phải tìm theo tiêu đề và thời gian, có thể đua với cảnh báo khác); hoặc chỉ ghi Error Log sau commit (trái luật "ghi trước commit" mà review-11 đòi ghim). Designer chọn, không phải dev.
2. Mọi phần tới được đều đúng và có test: khóa bao cả lần chạy kể cả commit (thứ tự sự kiện ghim bằng chính hàm `filelock` thật, tên khóa, `timeout=60`, không `is_global`); khóa bận ghi đúng dòng "lock busy", 0 điều kiện chạy, mốc không ghi, 0 thư, lượt đối chứng cùng dữ liệu gieo ra 4 cảnh báo; tại lần commit duy nhất test ghi nhận Error Log cảnh báo = 1, thư = 1, mốc = UPPER; lỗi ở điều kiện cuối hoặc ở commit rollback thư và mốc, lần chạy lại gửi một thư, hôm sau không gửi thêm; dòng log kiểm theo từng tên logger: đối số đúng từng chữ, `changes` chỉ đếm mục phân quyền, không tên user/role, `None` khi chưa có mốc.
3. `design-defect`: có. Nằm ở ADR-024 QĐ 3.5, dòng "Test (Quyết định 3)", gạch đầu dòng bằng chứng ("cùng một giao dịch", bỏ sót engine) và design-amd2 §4.2 bước 5. Lần chạy lỗi để lại một dòng Error Log cảnh báo, lần sau ghi thêm một dòng: báo lặp, không sót, khớp QĐ 3.8 nhưng lệch NFR-8 "0 báo hai lần" ở kênh Error Log. Việc sửa thuộc designer hoặc người: viết lại vế thành "Error Log có thể lặp một lần (3.8)" hoặc thêm task xóa bù.

- Phát hiện blocker/major: không.
- minor | — | — | 3 điểm nhỏ: (a) STD-TEST-6 `test_tasks.py:1366`: docstring `_real_alarms` nói dòng "rolled back with the test" nhưng dòng Error Log của nó ở lại site dùng chung, mỗi lượt module để lại khoảng 11 dòng "erp_ai: CẢNH BÁO" / `TITLE_RUN_FAILED` thật trên `miyano`; (b) STD-TEST-8 `test_tasks.py:1516-1536`: thêm phép đếm dòng Error Log theo dấu (1 và 2 sau hai lần lỗi, 3 sau lần chạy lại, vẫn 3 hôm sau) để ghim việc lặp đã biết; (c) STD-TEST-6: mọi test `_run` khác nay lấy khóa site thật, có tiến trình khác giữ khóa thì chờ 60 s rồi "lock busy", `assert_not_called` đỏ, trông như chập chờn | tùy dev

- Bằng chứng của dev: RED `AssertionError: None is not <function filelock …>`, `[call('erp_ai: CẢNH BÁO', …)] != [call('erp_ai: lần chạy lỗi', 'check_privilege_escalation lock busy')]`, `AssertionError: [] != [call('check_privilege_escalation window=%[96 chars], 2)]`, `Ran 66 tests in 7.976s` / `FAILED (failures=6)`; GREEN `Ran 66 tests in 8.106s` / `OK`. Trạng thái dev: `DESIGN_CONFLICT` ở đúng vế Error Log, phần còn lại đã commit.

## Tech-lead đã kiểm

- `frappe/core/doctype/error_log/error_log.json:6` = `"engine": "MyISAM"` (đọc trực tiếp); dev báo `information_schema` trên `miyano`: `tabError Log` MyISAM, Email Queue và `tabSingles` InnoDB (đầu ra của dev, tech-lead không chạy lại).
- Quyết định (decide) T13 trong journal 2026-11-14: không dừng build; nhận phần làm được, báo `design-defect` lên team-leader, ghi debt.md. Tick T13 theo quyết định đó, KHÔNG phải vì vế Error Log đạt.
- Sau merge `79ad5d0`, một lần giữ khóa `miyano-site.lock` (migrate exit 0): test_tasks `Ran 66 tests in 7.832s` / `OK`.
- `git diff --name-only 67f926b..f773c40` = `erp_ai/tasks.py`, `erp_ai/tests/test_tasks.py` (đúng touchpoint).

## Không kiểm được từ diff

- Engine thật của `tabError Log` trên `miyano` (JSON chỉ áp khi tạo bảng): theo đầu ra của dev là MyISAM → qa (verify) đọc lại `information_schema`.
- Ở production khóa bận ghi 2 dòng Error Log: `filelock` của Frappe tự ghi "Filelock: Failed to aquire <path>" (`synchronization.py:43`); test stub `filelock` nên chỉ thấy một. Không phải lỗi; ghi cho qa và As-Built.

## deferred

- `design-defect` vế Error Log → team-leader / designer (debt.md).
- minor (a), (b), (c) → debt.md.
