# Changelog

Mọi thay đổi đáng chú ý của app `erp_ai` được ghi ở đây. Định dạng theo [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Agent AI cho Helpdesk, cài xong ở trạng thái tắt, mức `L0`: `L0` chỉ ghi dự đoán phân loại vào `ERP AI Log`; `L1` ghi loại phiếu, nhóm, ưu tiên, độ tin cậy, hướng giải quyết và comment lên phiếu, không đổi `status`, không ghi đè phân loại của người, ghi lý do bỏ qua trường vào `ERP AI Log` (FEAT-001)
- Thẩm quyền theo người (role `ERP AI Instructor`, người được giao phiếu), chặn phiếu thuộc nhóm loại trừ hoặc có cờ "không dùng AI", giới hạn lượt/lần chạy/ngày, ngân sách USD theo tháng và lui về `L1` khi vượt ngân sách (FEAT-001)
- Form `ERP AI Setting`: quản lý nhiều khóa API (cầu dao theo loại lỗi, hạn mức, nghỉ/dò lại khóa mỗi giờ), nút "Kiểm tra khóa" cho System Manager, báo động khi tài khoản agent bị nâng quyền (FEAT-001)
- Báo cáo `ERP AI Accuracy` và nhật ký `ERP AI Log`: độ chính xác phân loại theo đầu mục A–F dựa trên phân loại do người sửa trong 7 ngày (FEAT-001)
- Bộ đánh giá offline `erp_ai.eval.export_tickets` và `erp_ai.eval.run_eval`: xuất phiếu đã gán nhãn (bỏ nhóm loại trừ) và in độ chính xác tổng, theo đầu mục, ma trận nhầm lẫn, kết luận theo ngưỡng 85%/70% (FEAT-001)
- Chỉ báo trạng thái trực tiếp trên trang phiếu của HD Agent: "Đang suy nghĩ…" rồi "Đang làm: <việc>…" khi `@ai` chạy, tự mất khi lần chạy kết thúc kể cả lỗi hoặc hết thời gian; không tạo comment, task hay bản ghi nào; không hiện trên cổng khách (FEAT-002)
- Ba trường mới trên `ERP AI Setting`: `thinking_text` (chữ chỉ báo, để trống để tắt chỉ báo), `answer_delay_min_s` và `answer_delay_max_s` (0 đến 30 giây, min không lớn hơn max), có kiểm khi lưu (FEAT-002)
- Bản ghi HD Form Script `ERP AI Agent Status` do app sở hữu: tạo hoặc đặt lại từ `erp_ai/public/js/agent_status_indicator.js` mỗi lần cài hoặc `bench migrate` (sửa tay trên site bị ghi đè), xóa khi gỡ app (FEAT-002)
- Mô tả (`description`) cho cả 71 field hiển thị của `ERP AI Setting` (22), `ERP AI Credential` (18) và `ERP AI Log` (31): đơn vị, khoảng hợp lệ, ý nghĩa từng mức quyền, ví dụ, field nào do hệ thống tự ghi và không sửa được; cùng các Section Break có nhãn tiếng Việt để chia form thành nhóm (6, 4 và 6 nhóm). Không đổi tên, kiểu, thứ tự hay quyền của field nào; không có field hay DocType mới (FEAT-003)
- Nút "Trao đổi với bot" trên header trang phiếu của HD Agent (chỉ desktop, từ 640 px trở lên) mở khu vực "Hướng giải quyết & trao đổi với bot": 4 mục AI chỉ đọc (hướng giải quyết, độ tin cậy, phân loại bởi, AI cập nhật lúc; "Chưa có" khi trống), luồng tin giữa người và bot (comment của bot và comment có từ khóa kích hoạt, cũ ở trên), dòng giải thích khi nào bot không trả lời, ô gửi câu hỏi (Enter gửi, Shift+Enter xuống dòng, tối đa 2000 ký tự) và chỉ báo "Đang suy nghĩ…" của FEAT-002; tự cập nhật khi có comment hoặc khi bot đổi field AI, không polling (FEAT-003)
- Hai method whitelisted `erp_ai.ticket_panel.get_panel_data` và `erp_ai.ticket_panel.send_message`, đều chỉ POST, không cho Guest: chỉ HD Agent đang hoạt động có quyền đọc phiếu mới dùng được; đọc không ghi gì; gửi tạo đúng 1 comment của người gửi qua `HD Ticket.new_comment`, tự thêm từ khóa kích hoạt khi người gõ chưa có, escape HTML, rồi để handler FEAT-001 xét mọi chốt như khi gõ `@ai` ở tab Comments. Khu vực không hiện cho khách và không bao giờ trả từ khóa hay cấu hình agent (FEAT-003)

### Changed
- Câu trả lời đầu tiên của comment `@ai` được giữ lại một khoảng ngẫu nhiên 3–5 giây (mặc định, chỉnh được) kể từ lúc chỉ báo bắt đầu; không có độ trễ cho phiếu mới, và không vượt hạn chót của lần chạy (FEAT-002)
- Script của bản ghi HD Form Script `ERP AI Agent Status` nay cũng dựng khu vực trao đổi với bot; khi khu vực mở, chỉ báo trạng thái nằm trong khu vực, khi đóng nó về góc dưới phải như cũ (FEAT-003)
- `erp_ai.agent.policy` có thêm `get_trigger_keyword()`; `contains_keyword` không đổi (FEAT-003)

### Fixed
- Lỗi 400 "Your credit balance is too low" (tổ chức hết credit) giờ được nhận là hết hạn mức: khóa chuyển `Hết hạn mức`, chuyển sang khóa kế tiếp, gửi tin báo và được dò lại mỗi giờ, thay vì bị coi là `bad_request` và để khóa ở `Hoạt động` (BUG-001)
- Bộ test không còn đỏ trên site có dữ liệu thật (role của tài khoản agent, `ERP AI Log`): test tự dựng trạng thái trong transaction và không để lại thay đổi trên site; không đổi hành vi sản phẩm (BUG-002)
