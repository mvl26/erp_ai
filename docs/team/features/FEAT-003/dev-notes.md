# Ghi chú môi trường cho dev (FEAT-003)

Áp dụng cho mọi task. Đọc cùng `plan.md` (Ràng buộc chung) và `design.md`.

## Nhánh và worktree
- Làm trong worktree của chính bạn; tạo nhánh `team/FEAT-003-task-N` từ `team/FEAT-003` tại sha BASE ghi trong handoff. Không chạm worktree khác. Không push.
- Chỉ sửa trong touchpoints của task; cần sửa ngoài → trả `DESIGN_CONFLICT`, không tự sửa. Không sửa Helpdesk/Frappe source, `.team/config.json`, `.team/profile.json`.
- Commit theo `type(scope): description (FEAT-003)` + dòng `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Chỉ `git add` theo đường dẫn cụ thể, không `-A`/`.`.
- Không skip/xfail/only (STD-TEST-4); không sửa assertion test cũ (STD-TEST-5).

## Chạy test trong worktree
- Một module: `cd /home/miyano/frappe-bench && PYTHONPATH="<đường dẫn worktree>" bench --site miyano run-tests --module <dotted.module>` (ví dụ `erp_ai.tests.test_ticket_panel`). Dán đầu ra ĐỎ (đúng lý do: thiếu hành vi, không phải import/syntax) rồi XANH.
- Đổi JSON DocType: chạy `PYTHONPATH="<worktree>" bench --site miyano migrate` trước test dựa trên meta. Trước và sau migrate, chụp ERP AI Setting (mọi field trừ password) và báo bằng/khác; không được làm đổi giá trị người dùng đã cấu hình.
- Chạy toàn bộ `bench --site miyano run-tests --app erp_ai` chỉ khi handoff ghi `FULL=yes`; tại một thời điểm chỉ một dev chạy (chạy song song sẽ deadlock MariaDB). Trước và sau mỗi lần chạy toàn bộ, chụp và so: ERP AI Setting (không password), tập `Has Role` của ai.agent@miyano.com.vn (hiện 99 role, KHÔNG được đổi), số bản ghi HD Team / HD Ticket / ERP AI Log / HD Form Script / Comment (Comment +2 mỗi lần chạy module là nhiễu đã biết). Khác biệt khác = rò rỉ: khôi phục đúng ảnh chụp trước rồi báo.
- Không in khóa API; không ghi email thật vào artifact/test (chỉ `@example.com`, `@congty.vn`); không xóa dữ liệu site.
- Lint file đã sửa: `pre-commit run --files <file>` (từ thư mục worktree).

## Báo cáo
- Báo cáo chi tiết ở file ghi trong handoff; thư trả ≤ 10 dòng, dòng đầu là trạng thái (DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED / DESIGN_CONFLICT), kèm tên nhánh, sha head, đầu ra đỏ rồi xanh.
