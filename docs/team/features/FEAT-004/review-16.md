Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 16 — FEAT-004 T16

- Diff: `git diff 0aaf3fb..team/FEAT-004-task-16` (1 commit `66a0bab`; 2 file, +354/-1)
- Vòng: 1 (max_rework=3)
- Verdict: approve

## Vòng 1 — approve
Lớp 1: AC-5, AC-7 (từ chối hoàn tác lệnh bench ở cả 9 trạng thái, thay đổi code ở 8 trạng thái khác `Đã áp dụng`), AC-12 (đúng 1 dòng log duyệt/từ chối, 0 dòng lúc xin hoàn tác) đạt. Đủ 7 test Expect và 2 test thêm. Chỉ 2 file touchpoint. Method không có git hay subprocess (ADR-022 QĐ 3).

Các điểm đã chấm:
- (a) Chữ ký: Frappe 15 bọc mọi hàm whitelist bằng `validate_argument_types`; với `name: str`, giá trị 123/None/list bị từ chối trước thân hàm bằng `FrappeTypeError` (HTTP 417), trái dòng lỗi design 3.3 (`name` không phải chuỗi → `DoesNotExistError`). Dev bỏ chú thích kiểu để kiểm `isinstance` trong thân hàm cho đúng 404; test gọi qua lớp bọc và đỏ nếu thêm lại `name: str`. Mâu thuẫn nằm trong design 3.3 và Returns của T16, không chặn task.
- (b) Thứ tự kiểm: role → name → chuyển trạng thái → xếp job (`erp_ai_change_proposal.py:64-82`), đúng design 4.2; người không có role gửi tên không tồn tại nhận cùng câu 403. Chuyển trước xếp job được ghim bằng `status_at_enqueue`.
- (c) `test_ok_comment_by_instructor_keeps_pending` xanh từ trước (không gọi 3 method); vẫn đỏ được nếu `comment_after_insert` đổi đề xuất. Các test Expect khác đều đỏ trước (AttributeError).
- (d) Patcher: `start()` kèm `addCleanup(stop)` ngay; không có phát hiện STD-TEST-6.

Phát hiện blocker/major: không có.

minor | — | — | 3 điểm nhỏ: (1) `frappe.db.exists` và `name.strip()` ở `_decider` (`:80`) trùng việc với `transitions._lock`; (2) test comment "ok" chưa kiểm comment có từ khóa bot xếp job agent mà không xếp `run_change`; (3) POST thiếu `name` rơi vào `TypeError` của Python (HTTP 500) thay vì 404; `name=None` mặc định sẽ đưa về `DoesNotExistError` | tùy dev

## Review checklist (10)
1–10 đạt.

## Bằng chứng của dev
- RED: `AttributeError: module '…erp_ai_change_proposal' has no attribute 'approve'`; `Ran 20 tests in 36.620s` / `FAILED (failures=1, errors=84)`
- GREEN: `Ran 20 tests in 18.031s` / `OK`; test_architecture `Ran 108 tests in 1.519s` / `OK`; lint sạch

## Không kiểm được từ diff (tech-lead xử lý)
- Đường HTTP thật (`/api/method/…` với `{"name": 123}`): test đi qua `in_test`; để qa kiểm ở `/team:verify`.
- `cmd.test` sau merge: xem tasks.md.

## deferred
- Designer: design 3.3 cột chữ ký ghi `approve(name: str)` trái dòng lỗi "`name` không phải chuỗi → DoesNotExistError" (Frappe 15 trả 417 khi có chú thích kiểu) → sửa thành `approve(name)` kèm lý do.
- Minor (3): POST thiếu `name` → 500.
