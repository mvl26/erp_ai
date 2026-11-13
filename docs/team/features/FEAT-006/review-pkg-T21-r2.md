# Review package FEAT-006 T21, vòng 2 (scoped re-review)

Repo: `/home/miyano/frappe-bench/apps/erp_ai`. FIX_BASE=8de1908; head=team/FEAT-006-task-21-rework1 (9dc0ca8). BASE gốc: b6d3504.
Lệnh diff sửa (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai diff 8de1908..team/FEAT-006-task-21-rework1 -- erp_ai`
Lệnh diff toàn task: `git -C /home/miyano/frappe-bench/apps/erp_ai diff b6d3504..team/FEAT-006-task-21-rework1 -- erp_ai`
Findings vòng 1: `/home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/feat-006/docs/team/features/FEAT-006/review-21-round1.md`.
Báo cáo dev: `git -C /home/miyano/frappe-bench/apps/erp_ai show 9dc0ca8:docs/team/features/FEAT-006/dev-T21-r2.md`.

Trả về từng finding cũ (3 major): ADDRESSED / NOT ADDRESSED. Ghi chú ngoài phạm vi vào `deferred`.
Chỉ có test được sửa (runner.py không đổi): các test mới xanh ngay trên mã đúng, dev chứng minh đỏ bằng đột biến (bỏ rollback đơn vị; rollback về savepoint ngoài; hard-code `comment=0`; ghi tên user vào `rule`); hãy xác nhận bằng đọc mã rằng các đột biến đó thật sự làm đỏ các assertion đã nêu.
Ruling tech-lead về "cannot verify": after_commit/realtime của `assign_to.add` không bị hủy bởi rollback savepoint; callback đăng ký ở bước cuối `notify_assignment`, nên thông báo ma chỉ khi `assign_to.add` ném lỗi sau bước đó (rất hiếm, không rò dữ liệu phiếu); không sửa mã (sửa phải đụng `CallbackManager._functions` riêng tư). Ghi vào concerns/deferred. Minor tên savepoint `erp_ai_route_unit` đã chuyển cho designer (deferred).
