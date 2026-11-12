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
- 2026-11-12 analyze --amend --decide → analyst | spec.md Amendment 1: phần 2 AC-6..AC-15, NFR-3..NFR-5, B-1..B-14; AC-1..AC-5 giữ nguyên, 12 dòng cũ gắn `[changed]` | SPECIFIED | — | good | vị trí P1 tab → P2 khối HD Form Script → P3 trang riêng → P4 tab Desk; tin = core Comment của chính người (tái dùng FEAT-001); RQ-1..RQ-8 cho research; ADR-007 QĐ 5–6 cần architect xem lại; không ghi current.json (FEAT-002 verify giữ)
- 2026-11-12 research → researcher | research.md RQ-1..RQ-8 + cache helpdesk-agent-ticket-panel@15.1.0.md | RESEARCHED | — | good | P1 không khả thi (tab viết cứng) → khuyến nghị P2 (action header + ngăn trên body) + 2 method erp_ai (GET đọc chữ thường, POST gọi HD Ticket.new_comment) + realtime docinfo_update/doc_update, không polling; architect phải sửa ADR-007 QĐ 5–6; không POC, không ghi current.json (FEAT-002 verify giữ)
- 2026-11-12 design (sửa theo ADR-010 Amendment 1) → designer | design.md: bỏ banner xung đột và nhãn C-1/C-2; D-4 (đọc POST) và D-5 (từ chối từ khóa có `<`,`>`,`&`) đã quyết; thêm D-9 (kiểm trên `sanitize_html` của Comment.validate trước new_comment), D-10 (thông báo hướng về quản trị viên); test AC-14 thêm `transaction_writes` không tăng; test từ khóa `a&b`/`a<b` và đọc lại Comment.content từ DB; `contains_keyword` không sửa | DESIGNED | — | good | 11 touchpoint giữ nguyên; không ghi current.json
- 2026-11-12 plan (--decide) → tech-lead | skill /team:plan: plan.md + tasks.md, 15 task (T1-T2 walking skeleton phần 2, T3-T5 phần 1, T6-T15 phần 2) | PLANNED | — | good | chưa tạo nhánh team/FEAT-003 (tạo lúc build từ team/BUG-002); không ghi current.json; phần 1 chạy song song được với phần 2 vì không chung file
