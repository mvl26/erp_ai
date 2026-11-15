Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 16 — CHG-002 T16

- Diff: `git diff f0b737c..5c15cdd` (nhánh `team/CHG-002-task-16`, 1 commit, 2 file, +116/−4; merge vào `team/CHG-002` ở `a83923b`)
- Vòng: 1 (max_rework = 3)
- Verdict: approve (0 blocker, 0 major)

## Vòng 1 — approve
`request_undo` nhận `Lỗi` chỉ khi đủ: loại `Thay đổi code`, có `apply_commit_sha`, `undo_commit_sha` rỗng (`transitions.py:238-245`); điều kiện viết `row.change_kind == CHANGE_KIND_CODE` (A3 RQ-7); kiểm lệnh bench vẫn chạy trước nên khối chỉ có lệnh nhận `Lệnh bench không hoàn tác được`; `_lock` đọc thêm hai trường SHA; câu từ chối và chữ ký `finish`, `log_step`, `content_digest` không đổi. 5 test của Expect có đủ, dev thêm 3 (`test_from_failed_with_undo_sha_refused`, `test_other_statuses_refused_even_with_apply_sha`, `test_lock_reads_status_kind_and_both_commit_shas`). Mỗi vế của điều kiện có test riêng: bỏ một vế bất kỳ thì một test đỏ.

Test cũ `test_request_undo_refused_for_code_outside_applied` giữ nguyên và vẫn xanh (đề xuất mẫu không có `apply_commit_sha`); phần "vẫn từ chối mọi trạng thái khác" do test mới phủ, có SHA ở mọi trạng thái khác. L-1: 0 là nhất quán (test chỉ sửa khi đỏ).

minor | — | — | 2 điểm nhỏ (xem deferred) | tùy dev

## Review checklist (10)
1. Đạt. 2. Đạt. 3. Đạt (RED 3 lỗi đúng câu từ chối cũ; SHA `None`/`""`, có undo SHA, loại thứ ba, khối lệnh; không skip). 4. Đạt (không assertion cũ nào đổi). 5. Đạt (`frappe.throw` với `InvalidTransition` như cũ). 6. Đạt (phân quyền không đổi, người gọi ở `erp_ai_change_proposal.py:139`). 7. Đạt (`_lock` trả tập lớn hơn; không chữ ký công khai nào đổi). 8. Đạt. 9. Đạt. 10. Đạt (`feat(changes): … (CHG-002)`, không dòng AI).

## Không kiểm được từ diff, tech-lead đã xử lý
- `test_erp_ai_change_proposal` (vòng lặp `:694-705` chờ `Lỗi` bị từ chối) và `test_apply_job` (các lời gọi `request_undo` đi qua `Đã áp dụng`): đợt merge 3 (`a83923b`, 06:15–06:24) chạy cả app `Ran 1602 tests in 500.711s` / `FAILED (failures=6)`, đúng 6 test của dòng `baseline:`; `test_transitions` `Ran 59 tests in 27.320s` / `OK`.
- Câu hỏi thiết kế (không phải lỗi của T16): loại thứ ba ở `Đã áp dụng` vẫn được nhận hoàn tác qua nhánh cũ `!= CHANGE_STATUS_APPLIED` (`transitions.py:246`); RQ-7 chỉ nói về `Lỗi`. Khi loại bản ghi của FEAT-007 (ADR-031 QĐ 6) tới được `Đã áp dụng`, designer cần phán cạnh đó có so `== CHANGE_KIND_CODE` hay không → báo team-leader.

## deferred
1. STD-NAME-6 `test_transitions.py:510`: tên `test_request_undo_refused_for_code_outside_applied` nay nói quá (code ở `Lỗi` có SHA được nhận).
2. STD-TEST-8 `test_transitions.py:593`: `test_two_callers_one_wins` gọi nối tiếp, không tạo tranh chấp thật; khóa dòng chỉ được ghim ở test khóa.
