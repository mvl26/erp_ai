Feature: FEAT-003
Stage: any
Author-agent: team-leader
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Journal FEAT-003

<!-- Mỗi lần bàn giao: 3–5 dòng, đúng định dạng dưới; trần journal.max_lines_per_entry. -->
- 2026-11-12 intake → team-leader | new-feature, S, decide | intake.md | — | good | thêm `description` cho field 3 DocType (setting 1/22, credential 0/18, log 0/31 hiện có); chờ FEAT-002 verify vì cùng sửa erp_ai_setting.json
- 2026-11-12 analyze → analyst | spec.md AC-1..AC-5 (71 field có mô tả, section có tiêu đề) | SPECIFIED | — | good | không ghi current.json (FEAT-002 build giữ)
- 2026-11-12 intake (gộp) → team-leader | new-feature, S → L, decide | intake.md: thêm yêu cầu 2 "tab riêng cho hướng giải quyết và trao đổi với bot" | — | good | tab Helpdesk viết cứng (TicketActivityPanel.vue:78-109), ADR-007 cấm script gọi server/ghi HTML → cần research + ADR; người đồng ý mọi đề xuất
