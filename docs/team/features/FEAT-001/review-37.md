# Review 37 — FEAT-001 T37 (Eval: xuất phiếu đã gán nhãn)

Verdict: approve (sau 1 vòng rework)
Vòng: 2 (vòng 1 request-changes; vòng 2 scoped re-review approve)
Diff: `git diff b63a667..team/FEAT-001-task-37` (head 62c3460; vòng 2: `git diff 07cea99..team/FEAT-001-task-37`)

## Vòng 1 (review-raw-T37.md)
- major STD-DESIGN-5: filter đòi đủ 3 trường nhãn, spec/design không yêu cầu. Phán quyết tech-lead: "đã gán nhãn" = `ticket_type` được đặt (cùng định nghĩa với `compute_metrics`).
- major STD-DESIGN-4: danh sách trường chính sách chép tay thay vì `policy.SEND_POLICY_FIELDS` (fail-open NFR-4).
- minor STD-TEST-6: test tạo File công khai vật lý, rollback không xóa.

## Vòng 2
Cả ba ADDRESSED (filter chỉ `ticket_type`; query dùng `SEND_POLICY_FIELDS`, test `test_export_queries_every_send_policy_field` đỏ khi bỏ guard — dev chạy mutation; File `is_private=1` + cleanup chỉ xóa file của test). Không finding mới ở mức blocker/major.

## Bằng chứng dev
Vòng 1: RED 9 tests (failures=4, errors=5) -> GREEN 9 OK. Vòng 2: Ran 11 tests OK; counts HD Team/HD Ticket/User/ERP AI Log/Error Log/File = 4/3/8/0/196/543 trước = sau. Dev gặp deadlock 1213 thoảng qua khi chạy song song T30 (STD-TEST-7, chưa lập lại khi chạy một mình).

## Deferred
- minor STD-TEST-6 test_export_tickets.py:151: nếu Frappe tái dùng file private cùng hash thì cleanup xóa file chung (khả năng thấp).
- Kiểm: dev báo `find sites/miyano -name 'ERPAI-TEST*'` rỗng nên không có file rò từ lượt 1; reviewer nêu khả năng có, báo người kiểm tay nếu cần.
- Không kiểm được: HTML `description` có thể nhúng ảnh base64/link file riêng (AC-2/NFR-4 chỉ nói về File đính kèm) — cho team-leader/designer cân nhắc.
