# Review package FEAT-006 T20, vòng 2 (scoped re-review)

Repo: `/home/miyano/frappe-bench/apps/erp_ai`. FIX_BASE=581a6b3; head=team/FEAT-006-task-20-rework1 (d9fad65). BASE gốc của task: 77dce93.
Lệnh diff sửa (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai diff 581a6b3..team/FEAT-006-task-20-rework1 -- erp_ai`
Lệnh diff toàn task: `git -C /home/miyano/frappe-bench/apps/erp_ai diff 77dce93..team/FEAT-006-task-20-rework1 -- erp_ai`
Findings vòng 1 (nguyên văn): `/home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/feat-006/docs/team/features/FEAT-006/review-20-round1.md`.

Trả về với từng finding cũ (3 major, minor 1-3): ADDRESSED / NOT ADDRESSED. Ghi chú ngoài phạm vi vào `deferred`, không mở rộng vòng.
Rulings của tech-lead cho các mục "cannot verify" vòng 1:
- `decision.notes` không ghi vào `skipped_fields` khi (u1) bị từ chối hoặc ném lỗi: giữ nguyên (không có gì được áp dụng thì không có trường bị bỏ qua); không phải lỗi của T20.
- after_commit: dev kiểm, kết luận trong `docs/team/features/FEAT-006/dev-T20-r2.md` (nhánh rework1; đọc bằng `git show d9fad65:docs/team/features/FEAT-006/dev-T20-r2.md`): chỉ rò thông báo realtime/chỉ mục tìm kiếm tạm thời, không rò dữ liệu; không đổi mã. Nếu bạn đồng ý, ghi nhận; nếu không, finding mới nêu rõ callback.
Minor 4 (cc82977 để 5 test đỏ giữa chừng) và 5 (placeholder cho T21) đã được bỏ qua có chủ đích; đầu nhánh xanh (dev báo toàn app 807 OK).
