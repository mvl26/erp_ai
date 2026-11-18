# Defects

| ID | Ngày | Mô tả | Nguồn | Trạng thái |
|---|---|---|---|---|
| BUG-001 | 2026-11-12 | 400 `Your credit balance is too low…` bị xếp `bad_request` thay vì `quota`/`Hết hạn mức` (`erp_ai/gateway/breaker.py:57`, trái guide `:797`) | hội thoại, tái hiện trên `miyano` | đã sửa (team/BUG-001) |
| BUG-002 | 2026-11-12 | Test FEAT-001 (test_tasks.TestCheckPrivilegeEscalation, erp_ai_accuracy TestAccuracyTenLogSample) phụ thuộc dữ liệu sống của site: 19 test đỏ khi site có role/log/khóa thật | acceptance FEAT-002, tái hiện trên miyano | đã sửa (team/BUG-002) |
| BUG-003 | 2026-11-13 | Chỉ báo 3 chấm của bot luôn hiện trên trang phiếu dù không có lần chạy: style inline `display: "flex"` đè thuộc tính `hidden` (`erp_ai/public/js/agent_status_indicator.js:77-88`, trái FEAT-002 AC-10) | hội thoại, suy từ mã và CSS Helpdesk (chưa quan sát trên trình duyệt) | mới |
| BUG-004 | 2026-11-15 | Câu trả lời classify của phiếu dài dừng ở trần `CLASSIFY_MAX_TOKENS = 600` (`erp_ai/agent/runner.py:62`), JSON bị cắt, phiếu mất cả phân loại; log ghi `unparseable` đè lý do dừng thật (`runner.py:331`) | hội thoại; `ERP AI Log` phiếu 43068 lúc 23:27, `output_tokens = 600` | mới |
