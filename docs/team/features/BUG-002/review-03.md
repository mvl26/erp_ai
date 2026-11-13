Feature: BUG-002
Stage: review
Author-agent: tech-lead
Date: 2026-11-12
Approved-by:

# Review 03 — BUG-002 T3 (điều tra rò commit ngầm)

- Verdict: không có diff để review (điều tra không tái hiện rò; T3 kết thúc với diff rỗng, không commit, không merge). Tech-lead ghi nhận thay cho reviewer vì không có mã để chấm; bằng chứng dưới đây là thứ cần kiểm.
- Lệnh diff: `git diff 3baa88b..team/BUG-002-task-3` -> rỗng. Vòng làm lại: 0.
- Ảnh chụp site (ERP AI Setting đủ trường gồm `permission_level`, Has Role của agent = 99, số đếm ERP AI Log/`classify`/HD Team/HD Ticket/HD Form Script/Custom DocPerm/Server Script/Webhook/Error Log/Custom Field/Property Setter + băm nội dung): trước và sau từng module (test_handlers 31, test_install 22, test_tasks 34, accuracy 13, test_alerts 5, test_ticket_delete 2: tất cả OK) và sau toàn bộ suite: bằng nhau; chỉ `Comment` +2 mỗi lần chạy module (dòng `Deleted` của Email Account/Holiday List do bootstrap của test runner, không phải rò).
- Cơ chế bảo vệ (kiểm tĩnh): test_handlers vá `frappe.db.commit` (nổ nếu commit) và rollback ở cleanup; test_install vá `frappe.db.updatedb` thành no-op nên không có DDL tự commit; các `frappe.db.commit` trong tasks/run_log/runner nằm sau `if not frappe.flags.in_test`.
- Nguồn L0 lúc 13:49–13:51: không quy được cho lượt chạy test nào; giả thuyết (chưa chứng minh): người sửa tay `ERP AI Setting` hoặc `bench migrate`/`after_migrate` chạy `ensure_setup` với mặc định L0. Hiện site `permission_level = L3`.
- `cmd.test` toàn bộ trên nội dung `team/BUG-002` (3baa88b): `Ran 592 tests in 88.254s` ... `OK`.

## deferred
- Dữ liệu site cho người xử lý (ngoài phạm vi): tài khoản agent còn 99 role.
