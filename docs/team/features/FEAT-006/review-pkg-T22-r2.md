# Review package FEAT-006 T22, vòng 2 (scoped re-review)

Repo: `/home/miyano/frappe-bench/apps/erp_ai`. FIX_BASE=ada855c; head=team/FEAT-006-task-22-rework1 (3db98bf). BASE gốc: 1b79b96.
Lệnh diff sửa (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai diff ada855c..team/FEAT-006-task-22-rework1 -- erp_ai`
Lệnh diff toàn task: `git -C /home/miyano/frappe-bench/apps/erp_ai diff 1b79b96..team/FEAT-006-task-22-rework1 -- erp_ai`
Findings vòng 1: `/home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/feat-006/docs/team/features/FEAT-006/review-22-round1.md`.
Báo cáo dev: `git -C /home/miyano/frappe-bench/apps/erp_ai show 3db98bf:docs/team/features/FEAT-006/dev-T22-r2.md`.

Trả về từng finding cũ (2 major): ADDRESSED / NOT ADDRESSED. Chỉ test đổi (runner.py không đổi); xác nhận bằng đọc mã rằng đột biến "luôn thêm câu" (`if True:` ở nhánh `len(errors) > failures`) làm đỏ test mới và test (i) đếm ToDo theo `self.person` thật sự độc lập với ToDo Task còn sót trên site.
Rulings tech-lead về "cannot verify": (a) bị từ chối không ném: giữ, không thêm câu sai lý do; (b) câu comment đúng chữ design: deferred cho designer; (c) ca đầu mục D không bắt buộc. Ghi chú ngoài phạm vi vào `deferred`.
