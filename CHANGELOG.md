# Changelog

Mọi thay đổi đáng chú ý của app `erp_ai` được ghi ở đây. Định dạng theo [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Agent AI cho Helpdesk, cài xong ở trạng thái tắt, mức `L0`: `L0` chỉ ghi dự đoán phân loại vào `ERP AI Log`; `L1` ghi loại phiếu, nhóm, ưu tiên, độ tin cậy, hướng giải quyết và comment lên phiếu, không đổi `status`, không ghi đè phân loại của người, ghi lý do bỏ qua trường vào `ERP AI Log` (FEAT-001)
- Thẩm quyền theo người (role `ERP AI Instructor`, người được giao phiếu), chặn phiếu thuộc nhóm loại trừ hoặc có cờ "không dùng AI", giới hạn lượt/lần chạy/ngày, ngân sách USD theo tháng và lui về `L1` khi vượt ngân sách (FEAT-001)
- Form `ERP AI Setting`: quản lý nhiều khóa API (cầu dao theo loại lỗi, hạn mức, nghỉ/dò lại khóa mỗi giờ), nút "Kiểm tra khóa" cho System Manager, báo động khi tài khoản agent bị nâng quyền (FEAT-001)
- Báo cáo `ERP AI Accuracy` và nhật ký `ERP AI Log`: độ chính xác phân loại theo đầu mục A–F dựa trên phân loại do người sửa trong 7 ngày (FEAT-001)
- Bộ đánh giá offline `erp_ai.eval.export_tickets` và `erp_ai.eval.run_eval`: xuất phiếu đã gán nhãn (bỏ nhóm loại trừ) và in độ chính xác tổng, theo đầu mục, ma trận nhầm lẫn, kết luận theo ngưỡng 85%/70% (FEAT-001)
