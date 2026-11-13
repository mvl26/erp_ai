# Review 23 — FEAT-001 T20b (test_policy không để lại trạng thái Redis)

- Verdict: approve (vòng 1, 0 vòng rework)
- Diff: `git diff 3b412e7..team/FEAT-001-task-20b` (head 6c52cbf); merge 2706f13
- Nguyên nhân: `_ensure_team("IT")` tạo HD Team thật → Assignment Rule "IT - Support Rotation" vào Redis `assignment_rule_map`; rollback DB không xóa Redis → 7 lỗi ở test_handlers/test_install/test_ticket_delete khi chạy `--app erp_ai`
- Bằng chứng dev: RED trong lần chạy đầy đủ nhánh chưa sửa: Ran 186 FAILED (errors=7); GREEN sau clear-cache: `--app erp_ai` hai lần liên tiếp "Ran 186 tests OK"; pre-commit exit 0

## Findings
Không có blocker/major, không có minor.

## Deferred
- Chưa có test tự động kiểm `assignment_rule_map` sạch sau lớp test; chứng cứ duy nhất là chạy đầy đủ hai lần.
