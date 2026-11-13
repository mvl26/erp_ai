# Review 14 — FEAT-001 T11b (D7: ignore_links_on_delete)

- Verdict: approve (vòng 1, 0 vòng rework)
- Diff: `git diff 7415abd..team/FEAT-001-task-11b` (head 4f302e2); merge vào team/FEAT-001 (cbaf7c7 chứa cả T14)
- Đối chiếu: D7 trong journal (thay design.md); touchpoints đúng 2 file
- Bằng chứng dev: RED `LinkExistsError` khi xóa phiếu có ERP AI Log; GREEN `Ran 2 tests OK`; cmd.test sau merge T11b+T14: `Ran 116 tests ... OK`, pre-commit exit 0

## Findings
Không có blocker/major.

## Deferred
- minor: tên test thực tế `test_ticket_with_log_can_be_deleted_and_log_survives` (khác tasks.md Expect, chấp nhận).
- minor STD-TEST-8: `test_log_doctype_still_has_no_delete_permission` chạy trống nếu DocType không có quyền nào; nên thêm assert danh sách quyền không rỗng.
- Cần người xem: `ignore_links_on_delete` áp cho cả liên kết ERP AI Log -> User (`instructor`, `human_corrected_by`); xóa User không còn bị log chặn.
- Cho task sau (T32): cập nhật dòng log của phiếu đã xóa phải dùng `db.set_value`, không `doc.save()` (link treo).
