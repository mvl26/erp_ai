Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 57 — FEAT-004 T57

- Diff: `git diff b792fb8..8a808f9` (nhánh `team/FEAT-004-task-57`, xếp chồng trên T56 `b792fb8`; 1 commit `feat(changes): change job writes the result line on the ticket after every outcome (FEAT-004)`, 2 file, +249/−4)
- Diff vòng 2: `git diff 8a808f9..23fc928` (1 commit `test(changes): check the final status is committed before the result line, lock-timeout failure case (FEAT-004)`, 1 file, +42/−13)
- Vòng: 2
- Verdict: approve (vòng 1: request-changes; vòng 2: approve)

Tech-lead chép từ tin trả về của reviewer. Reviewer không chạy test (site dùng chung).

## Vòng 1 — request-changes

Lệnh reviewer đã chạy (chỉ đọc): `git log --oneline b792fb8..team/FEAT-004-task-57`, `git diff --stat …`, `git diff …`; đọc thêm Frappe `background_jobs.execute_job` (commit sau khi job trả về).

Bằng chứng của dev: RED `AssertionError: False is not true : erp_ai change proposal=%s action=%s outcome=%s duration_ms=%d commit=%s` (mọi subTest), `AssertionError: 0 != 3 : []`; GREEN test_apply_job `Ran 117 tests in 207.085s` / `OK`, test_result_comment `Ran 6 tests in 5.283s` / `OK`, test_architecture `Ran 177 tests in 20.457s` / `OK`.

### Lớp 1 — khớp spec

- Đủ mọi mục Returns: `post_result` gọi đúng một chỗ trong `run_change`, chỉ khi kết cục khác `OUTCOME_SKIPPED`; thành công → commit; lỗi → rollback, `log_error` đúng tiêu đề và nội dung, không ném lại, lý do ghi ở chú thích chỗ bắt; dòng log thêm `comment=<tên>|-|error`. Đủ bốn test của Expect; chỉ hai file touchpoint.
- Phép kiểm có sẵn bị đổi ở `test_one_log_line_with_the_commit_and_no_content` (`test_apply_job.py:1431-1435`): nhận theo STD-TEST-5, vì design CHG-001 mục 4 bước 4 đổi spec (thêm `comment=`); các trường cũ vẫn được ghim.

### Phát hiện (chỉ blocker/major)

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-8 | erp_ai/agent/changes/test_apply_job.py:3314 (cả :3158, :3261) | confirmed. Test nói trạng thái cuối sống sót qua rollback ở chỗ bắt, nhưng không gì kiểm rằng trạng thái cuối đã commit trước khi `post_result` chạy. `frappe.db.commit` và `frappe.db.rollback` đều là mock, nên `state == status` đúng bất kể job làm gì. Test lỗi comment cũng thiếu ca khóa hết giờ. Xóa `frappe.db.commit()` ở `apply_job.py:148` (đường khóa hết giờ) hoặc `:195` (cuối `_run_in_lock`) thì mọi test T57 vẫn xanh. Từ T57, commit đó là thứ duy nhất che trạng thái cuối khỏi rollback ở `apply_job.py:122` (STD-ERR-7, design 4 bước 3). | Trong `run_job`, cho mock commit một side effect ghi `(call_count, change_status)` mỗi lần gọi; trong `post`, kiểm commit cuối đã thấy trạng thái cuối, cho cả sáu kết cục; thêm subTest khóa hết giờ vào `test_comment_failure_keeps_final_status_and_logs`. |

minor | — | — | 1 điểm nhỏ: chú thích ở `test_apply_job.py:3218` nói trạng thái "không đọc từ hằng" trong khi chỉ lý do được viết tay | tùy dev

### Không kiểm được từ diff (vòng 1)

- Ca "sai người chạy job": dòng `Info` ghi dưới user phiên vừa bị M2 từ chối (Administrator trong test). Design mục 4 giả định user phiên là người duyệt "M2 đã kiểm", nhưng test plan mục 8 cũng đòi +1 dòng ở ca này. → tech-lead: làm đúng chữ test plan; ghi cho designer/architect xem lại, không chặn.
- Chưa chạy cả `test_apply_job` để xem test có sẵn nào khác ghim commit ở `:148`/`:195` không.
- Dòng `Info` hiện trên trang phiếu Helpdesk thật (A-D1): qa sau G4.

## Vòng 2 — approve

Lệnh reviewer đã chạy (chỉ đọc): `git log --oneline 8a808f9..team/FEAT-004-task-57`, `git diff --stat …`, `git diff …`, `git diff --stat b792fb8..team/FEAT-004-task-57`.

Bằng chứng của dev (đột biến): xóa commit ở `apply_job.py:148` → 2 failures, chỉ subTest `[lock timeout]`: `AssertionError: None != (7, 'Lỗi')` / `AssertionError: None != (15, 'Lỗi')`; xóa commit ở `:195` → 7 failures, vd `AssertionError: Tuples differ: (1, 'Đang áp dụng') != (1, 'Đã áp dụng')`, `(3, 'Đang áp dụng') != (3, 'Lỗi')`; `apply_job.py` trả về như cũ (diff rỗng); GREEN test_apply_job `Ran 117 tests in 206.649s` / `OK`.

- major STD-TEST-8: **ADDRESSED** (`test_apply_job.py:3160-3164` mock commit ghi `(call_count, change_status)`, gỡ side effect trong `finally` `:3178-3179`; `:3167` giữ commit cuối trước `post_result`; `:3277` kiểm cho sáu kết cục; `:3345` cho ba subTest lỗi; `:3318-3333` subTest khóa hết giờ).
- minor (chú thích `:3218`): **ADDRESSED** (`test_apply_job.py:3232-3233`).
- Phát hiện mới: không có. Checklist 10/10 đạt; không skip/xfail, không nới phép kiểm nào.

### Không kiểm được từ diff (vòng 2)

- 117 test xanh và `apply_job.py` nguyên vẹn: tech-lead chạy lại sau merge `ac5518d`: test_apply_job `Ran 117 tests in 142.497s` / `OK`; worktree dev sạch khi gỡ.

## Deferred

- Ca "sai người chạy job" ghi dòng dưới user bị M2 từ chối: chờ designer/architect.
