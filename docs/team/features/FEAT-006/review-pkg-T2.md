# Review package FEAT-006 T2 (helper test: ghim role, dữ liệu Helpdesk tự tạo), vòng 1

Repo: `/home/miyano/frappe-bench/apps/erp_ai`. BASE=686aa3f; head=team/FEAT-006-task-2 (7388e1d).
Lệnh diff (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai diff 686aa3f..team/FEAT-006-task-2`
Commit: 7388e1d test(utils): pin_agent_roles and self-made Helpdesk data helpers (FEAT-006)
Stat: erp_ai/test_utils.py, erp_ai/tests/test_test_utils.py (đúng touchpoint).
Tiêu chí: dòng T2 của `tasks.md` (AC-17 ghim role và trả lại, A-13 test tự tạo dữ liệu), plan.md "Shared constraints" và rủi ro R-2 (site `miyano` dùng chung, Has Role của tài khoản agent phải đúng trước = sau), design.md.
Dev tự thêm hằng `PREFIX = "ERPAI-TEST-"` (task có nhắc "tiền tố `PREFIX`"; kiểm xem đã có hằng này ở nơi khác chưa, STD-DESIGN-4). `make_team(with_rule=False)` xóa rule bằng `frappe.db.delete` vì `HDTeam.on_trash` có commit: kiểm xem có để lại dữ liệu sau rollback không.
Bằng chứng dev: `cmd.test` 684 OK; Has Role của tài khoản agent 99 trước, 99 sau cả bộ.
