Feature: FEAT-003
Stage: intake
Author-agent: team-leader
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Intake FEAT-003 — Mô tả rõ cho field của DocType mới + tab riêng "Hướng giải quyết & trao đổi với bot" trên phiếu

- Yêu cầu gốc:
  1. (2026-11-12) "viết thêm các chú thích và mô tả rõ ràng cho các feild của doctype mới tạo, vd ERP AI Setting"
  2. (2026-11-12, gộp vào FEAT-003 theo lời người: "cho nào vào feat 003") "thêm 1 tab rành riêng cho hường giải quyết và trao đổi với bot cho user dễ sử dụng"
- Nguồn: hội thoại
- Loại việc: feature (giao diện cấu hình dễ hiểu + giao diện làm việc với bot trên phiếu)
- Playbook: new-feature
- Size: L
- Mode: decide
- Lý do chọn playbook/cỡ: Hành vi mới cho hệ thống đang chạy, không khớp dòng nào khác của bảng playbook → `new-feature`. Cỡ L vì yêu cầu 2 chạm nhiều module và cần quyết định kiến trúc: (a) danh sách tab trên trang phiếu của Helpdesk 15.1.0 viết cứng trong `apps/helpdesk/desk/src/components/ticket-agent/TicketActivityPanel.vue:78-109` (Activity, Emails, Comments, Calls, Analytics) — không có điểm mở rộng cho app, mà FEAT-002 đã chốt không sửa mã nguồn Helpdesk → cần research; (b) "hướng giải quyết" hiện là field chỉ đọc `ai_resolution_hint` (Text Editor) trong section "ERP AI" ở thanh bên (`erp_ai/install.py:117-127`, hiện cho Agents qua HD Ticket Template `install.py:154-175`); (c) "trao đổi với bot" hiện là comment có `@ai` (`erp_ai/handlers.py:100-120`) và bot trả lời bằng `post_comment` (`erp_ai/agent/tools/write_ticket.py:73`); (d) một tab có ô gửi tin cho bot trái ADR-007 Quyết định 5–6 (script trên trang không gọi server, không ghi HTML — `docs/team/adr/ADR-007.md:28-29,37`) → cần ADR mới/sửa ADR; (e) NFR mới: an toàn (XSS, quyền, khách không thấy), chi phí/giới hạn lượt chạy của kênh mới. Phần 1 (mô tả field, đã có spec AC-1..AC-5) giữ nguyên.
- Skill tạm: không cần
- Ngân sách: max_agents_per_feature = 10; feature_budget_usd = không giới hạn

## Điểm analyst phải làm rõ — phần 2 (không tự giả định ngoài các mặc định người đã đồng ý)
- **Tab nằm ở đâu:** trang phiếu của nhân viên trong Helpdesk (`/helpdesk/tickets/<id>`, cạnh Activity/Emails/Comments) — đúng chỗ người dùng đang làm việc nhưng không có điểm mở rộng; hay tab trên form Desk (`/app/hd-ticket/<id>`, Tab Break custom field — dễ làm, nhưng nhân viên ít dùng Desk); hay trang riêng mở từ phiếu. Bản di động (`MobileTicketAgent.vue` có danh sách tab riêng) trong hay ngoài phạm vi.
- **Nội dung tab:** (1) hướng giải quyết + độ tin cậy + phân loại bởi + cập nhật lúc (đọc từ field AI hiện có); (2) luồng trao đổi với bot: lịch sử hỏi–đáp, ô nhập để gửi câu hỏi/yêu cầu cho bot.
- **Tin trao đổi lưu ở đâu:** vẫn là comment trên phiếu (ô nhập tự thêm `@ai`, bot trả lời bằng comment như hiện nay — tái dùng toàn bộ luồng FEAT-001) hay kênh riêng không hiện trong timeline (DocType mới). Ràng buộc ADR-004 (một người ghi mỗi bản ghi; chỉ `post_comment` tạo comment của agent; agent không xóa bản ghi) và D8 (tác giả comment lấy từ `owner`).
- **An toàn & quyền:** kênh mới đi qua đúng mô hình thẩm quyền (ERP AI Instructor), `policy.can_send_ticket` (nhóm loại trừ, opt-out), giới hạn lượt chạy/ngày, ngân sách, mức quyền (L0 không trả lời); khách (HD Contact) không thấy tab; nội dung bot hiển thị dạng an toàn (không chèn HTML thô).
- **Ghép với FEAT-002:** chỉ báo "Đang suy nghĩ… / Đang làm: …" và độ trễ 3–5 s hiện trong tab.

## Mặc định người đã đồng ý (2026-11-12: "tôi đồng ý mọi đề xuất", "làm sao để có thể cho team chạy hoàn thiện xong cả f002 và 003 luôn")
- Đội chọn phương án khuyến nghị cho mọi điểm trên và ghi lại (chọn / vì / phương án khác / hoàn tác). Chỉ hỏi lại người khi phương án buộc phải sửa mã nguồn Helpdesk, nới một quy tắc an toàn đã có (ADR-004, mô hình thẩm quyền, NFR-4 nhóm loại trừ), hoặc đụng production/bí mật.

## Điểm analyst phải làm rõ — phần 1 (đã chốt trong spec.md, giữ)
- Phạm vi mô tả field: 3 DocType (`ERP AI Setting`, `ERP AI Credential`, `ERP AI Log`) + 3 field FEAT-002; Section Break có tiêu đề; ngoài: report `ERP AI Accuracy`, bản dịch, đổi label, sửa hành vi.

## Ràng buộc của người yêu cầu
- Như FEAT-001/FEAT-002: commit local trên `team/FEAT-003`, không push, không đụng `develop`/`main`; G1–G4 tắt, G5 bật; không đổi giá trị `ERP AI Setting` trên `miyano`; không sửa mã nguồn Helpdesk (người chọn ở FEAT-002 Q1 = b).
- **Phụ thuộc FEAT-002:** FEAT-002 đang build trên `team/FEAT-002` (cùng sửa `erp_ai_setting.json`, cùng lớp giao diện HD Form Script của ADR-007). FEAT-003 chỉ bắt đầu `/team:build` sau khi FEAT-002 được verify; nhánh nền `team/FEAT-002`.
- `.team/current.json` đang do tech-lead FEAT-002 giữ (stage build) nên intake này không ghi đè nó.

## Đổi cỡ (nếu có)
- 2026-11-12: S → L — gộp yêu cầu 2 (tab riêng cho hướng giải quyết và trao đổi với bot) theo lời người; lý do ở dòng "Lý do chọn playbook/cỡ".
