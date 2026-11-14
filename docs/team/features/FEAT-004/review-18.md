Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 18 — FEAT-004 T18

- Diff: vòng 1 `git diff 7e90e5e..25be823 -- erp_ai/agent/changes/` (mã nhận từ ngoài quy trình); vòng 2 `git diff a742cd8..62448cf` (1 commit, 2 file, +323/-57)
- Vòng: 2 (max_rework=3)
- Verdict: approve

## Vòng 1 — request-changes (review C, mã nhận về)

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-ERR-1 | erp_ai/agent/changes/apply_job.py:72 | Hết hạn khóa thì `LockTimeoutError` thoát khỏi `run_change`; đề xuất kẹt `Đã duyệt`, 0 dòng nhật ký, job raise | bắt `LockTimeoutError` → `finish(Đã duyệt → Lỗi, …)` |
| major | STD-SEC-4 | erp_ai/agent/changes/apply_job.py:112-125 | Chỉ có 3/7 điều kiện kiểm lại của bảng 4.3 (công tắc, digest, bộ chặn); thiếu `session.user == decided_by`, người duyệt còn role, `sha256(content_after) == after_hash`, thông điệp thật khớp `commit_message` | thêm 4 kiểm với đúng chữ lý do |
| major | STD-OPS-5 | erp_ai/agent/changes/apply_job.py:68-109 | Không có `deadline`; không có dòng `frappe.logger("erp_ai").info(... commit=%s)` | thêm cả hai |

Thiếu test của Expect: ca role, user phiên, `commit_message` của `test_rechecks_fail_without_writing`; `test_lock_timeout_fails_without_writing`; `test_applying_state_committed_before_rechecks_run` cho nhánh code.

## Vòng 2 — approve (`git diff a742cd8..62448cf`)
- Phát hiện 1: ADDRESSED (`apply_job.py:120-127`; đọc trạng thái trước khi lấy khóa như bước 2 của design)
- Phát hiện 2: ADDRESSED (`apply_job.py:182-222`; đủ 7 dòng theo thứ tự bảng, đúng chữ design, hằng ở `:41-46`; bản xem trước `commit_message` dựng như `_set_commit_message` của controller)
- Phát hiện 3: ADDRESSED (`apply_job.py:87-100`; `deadline` tính đầu tiên; một dòng log có `commit=%s`, không có nội dung file)
- Test thiếu: ADDRESSED (`test_apply_job.py:284-395`; đủ 7 dòng; ca `commit_message` và `after_hash` sửa trước khi duyệt nên digest không bắt hộ; `test_approver_who_never_carries_authority_fails`; khóa thật được giữ trong test hết hạn khóa; job lặp không lấy khóa)
- Assertion cũ bị sửa (STD-TEST-5): đều theo chữ design, không sửa theo hành vi sai: "công tắc đang tắt", "nội dung đề xuất đã bị sửa sau khi duyệt" (bảng 4.3); `"RuntimeError"` (bước 5, `reason=type(exc).__name__`); người chạy test đổi từ Administrator sang user có `ERP AI Instructor` vì Administrator thuộc `NEVER_AUTHORITY` (`authority.py:12`)
- Phát hiện mới: không có blocker/major

minor | — | — | 4 điểm nhỏ: exception từ `begin_apply`, `get_doc`, `finish` trong handler hay commit cuối vẫn có thể thoát khỏi `run_change` (`apply_job.py:131-140`, nghi vấn); test "commit trước kiểm lại" ghi trạng thái ở dòng công tắc (dòng 3) nên dời commit xuống sau dòng 1–2 vẫn xanh; thứ tự bảng kiểm lại chưa được ghim; dòng log ghi `Lỗi` cả khi `finish` không còn khớp | tùy dev

## Review checklist (10)
Đã phủ 10/10.

## Bằng chứng của dev
- RED: `test_lock_timeout_fails_without_writing: ERROR`, `LockTimeoutError` thoát khỏi `apply_job.py:72 run_change`; `[role lost] ('Đã áp dụng', None) != ('Lỗi', 'người duyệt không còn quyền')`; `('Đã áp dụng', None) != ('Lỗi', 'sai người chạy job')`; `Expected 'filelock' to not have been called. Called 1 times.`
- GREEN: `Ran 33 tests in 21.497s` / `OK`

## Không kiểm được từ diff (tech-lead xử lý)
- `queue.enqueue_change_job` có chạy job dưới user phiên của người duyệt không: `arch-impact.md` của CHG-001 (dòng 12, 19) đã đọc `background_jobs.py:168-170` và kết luận job xếp từ controller chạy dưới user đã xếp; ca "job xếp ngoài controller chạy dưới user khác" chính là ca kiểm lại này chặn. Ghi cho T21/T34 kiểm bằng một lần duyệt thật trên dev.
- `frappe.utils.file_lock.LockTimeoutError` có đúng là lớp `synchronization.filelock` ném: test giữ khóa thật và xanh (dòng GREEN).

## deferred
- T21: `apply_job.py:347` tính `int(deadline - time.monotonic())`, nhánh `limit < 1` do T21 làm (phụ lục 2 QĐ-A3).
- 4 điểm nhỏ ở trên: xét lại ở T45 (bọc exception) và T34.
