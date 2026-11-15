Feature: FEAT-007
Stage: intake
Author-agent: team-leader
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Đối chiếu A8 — Báo cáo, KPI và việc chạy theo lịch

Mốc: `develop` @ `7cc37bb`, đọc ngày 2026-11-14 bằng một lệnh Explore chỉ-đọc. Team-leader đã tự kiểm `erp_ai/hooks.py:141-161` và danh sách file của app (`git ls-files erp_ai`: 4 DocType, 1 báo cáo). Trạng thái và quy ước đường dẫn: xem đầu `audit-A1.md`. `H/` = `apps/helpdesk/helpdesk/`.

| Mã | Yêu cầu của tài liệu | Trạng thái | Bằng chứng | Thiếu hoặc khác; dữ liệu đã có |
|---|---|---|---|---|
| A8-1 | Mục 5 GĐ4: báo cáo hằng ngày 8h cho COO (phiếu mới, phiếu sắp quá hạn, việc bot đã làm) | MISSING | `erp_ai/hooks.py:159-162` chỉ có `hourly` (dò lại khóa) và `daily` (chi tháng, kiểm nâng quyền); "daily" của Frappe là 00:00, app không có khóa `cron`. | Không có job, nội dung, người nhận COO. Dữ liệu có sẵn: `HD Ticket.creation`; `response_by`, `resolution_by`, `agreement_status`; `ERP AI Log.actions`, `value_before`, `value_after`, `tools_called`. |
| A8-2a | KPI thời gian phản hồi đầu tiên (< 15 phút, rồi < 5 phút) | PARTIAL (của Helpdesk, không phải của app) | Thẻ "Avg. First Response" của Helpdesk tính theo giờ (`H/api/dashboard.py:221-237`), chỉ đếm phiếu có SLA và `first_responded_on`. | App không tính gì. Bot trả lời bằng Comment nội bộ (`erp_ai/agent/tools/write_ticket.py:102-112`), Helpdesk không tính là phản hồi đầu tiên và người tạo phiếu không thấy. Đơn vị giờ một chữ số thập phân không kiểm được mốc 5 phút. |
| A8-2b | KPI tỷ lệ phiếu có đủ đầu mục/nhóm/ưu tiên | MISSING | Không gì tính. | Dữ liệu có: `ticket_type`, `agent_group`, `priority`, `ai_classified_by`. |
| A8-2c | KPI tỷ lệ phiếu đóng không cần người làm (10%, rồi 30%) | MISSING | Không tool nào bot tự dùng ghi `status` (`write_ticket.py:68-148`, `erp_ai/agent/tools/route_ticket.py:42-74`); FEAT-001 để "đổi status, đóng phiếu" ngoài phạm vi (`docs/team/features/FEAT-001/spec.md:23,56`). | KPI bằng 0% do thiết kế cho tới khi có quyết định cho bot đóng phiếu. Dữ liệu có: `status_category`, `resolution_date`, bản ghi Version của HD Ticket (ai đổi trạng thái). |
| A8-2d | KPI thời gian xử lý trung bình đầu mục B (< 4 giờ, rồi < 1 giờ) | MISSING | Thẻ "Avg. Resolution" của Helpdesk tính theo ngày, chỉ lọc theo nhóm hoặc agent (`H/api/dashboard.py:239-254`). | Không có số theo đầu mục. Dữ liệu có: `resolution_time`, `resolution_date`, `creation`; đầu mục suy từ `ticket_type` hoặc `ERP AI Log.predicted_category`. |
| A8-2e | KPI phiếu C có Task liên kết trong 3 ngày | MISSING | Không gì tính. | Dữ liệu có: `Task.ai_ticket` (`erp_ai/install.py:213-233`), `Task.creation`, `HD Ticket.creation`. Task người tạo mà không điền `ai_ticket` sẽ không được đếm. |
| A8-2f | KPI số phiếu tồn > 5 ngày | MISSING | Không gì tính. | Dữ liệu có: `status_category`, `creation`. |
| A8-3 | Phiếu F tự đóng sau 3 ngày im lặng; không bao giờ với Chỉ đạo BGĐ và đầu mục E | MISSING | Không mã nào của app đặt trạng thái phiếu; prompt chỉ trích quy tắc (`erp_ai/agent/prompts.py:150`). | Không có lịch đóng. Trường "Nguồn phát sinh" không có trên site dev. Rủi ro: bật `close_tickets_after_n_days` của Helpdesk (`H/helpdesk/doctype/hd_ticket/hd_ticket.py:1492-1538`) sẽ đóng cả phiếu E và phiếu BGĐ. |
| A8-4 | Nhắc hạn (D, E) và tổng hợp tiến độ cho COO | MISSING | Không có. | Site dev không có trường "Hạn hoàn thành". Dữ liệu dùng được: `resolution_by`, `agreement_status`, `Task.exp_end_date`. |
| A8-5 | Phiếu C, D có Task trong 3 ngày; C: BA note 24h, kế hoạch Task 3 ngày | PARTIAL | Routing tạo 1 Task cho C/D lúc tạo phiếu (`erp_ai/agent/routing.py:72`, `erp_ai/agent/runner.py:345-348,419-454`), cần L1+, `auto_assign_enabled` và chính bot gán người. SLA mong đợi của C đặt 24 giờ (`routing.py:25`). | Không có kiểm tra hay nhắc theo lịch ở mốc 24 giờ hay 3 ngày. |
| A8-6 | #1770: Task xong thì phiếu Resolved | MISSING | `hooks.py:141-151` không có sự kiện Task; app khác trên bench chỉ có hrms xử lý Task cho onboarding. | Chưa có trong mã ở đâu dưới `apps/`. Server Script trong DB: chưa kiểm. Trường liên kết `Task.ai_ticket` đã có sẵn cho việc này. |
| A8-7 | Bot soạn bài CSKT nháp sau mỗi phiếu đóng | MISSING | `ticket_on_update` chỉ ghi lần sửa của người (`erp_ai/handlers.py:84-97`); `HD Article` chỉ được đọc (`erp_ai/agent/tools/read.py:24`). | Không có kích hoạt khi đóng, không có soạn nháp. |
| A8-8 | Cửa L3: ≥ 20 lần L2 liên tiếp được duyệt không sửa cho từng loại việc; 0 sự cố do bot | DECIDED-DIFFERENTLY | Hướng dẫn mục 17 bỏ duyệt từng hành động (`docs/HuongDan_TrienKhai_erp-ai.md:1481`); bước 10 đặt cửa L3 là "0 sự cố trong 2 tuần L2" (`:1287`). | Không gì tính thống kê theo loại việc hay sự cố. Chỉ suy được số duyệt/từ chối của đề xuất code và bench (`change_status`, `change_step`). |
| A8-9 | Cửa GĐ2: ≥ 70% đề xuất được duyệt không sửa hoặc sửa nhỏ | DECIDED-DIFFERENTLY | Hướng dẫn `:1286` thay bằng "≥ 70% việc làm xong không phải sửa lại". | Chỉ số thay thế cũng chưa được đo. |
| A8-10 | Mỗi tháng rà ngẫu nhiên 10 phiếu bot đã làm | NOT-APP (app hỗ trợ được) | Việc rà là của người. | App không có lấy mẫu, báo cáo hay job hỗ trợ. |
| A8-12 | Kênh gửi và người nhận COO | PARTIAL | Chỉ email: `frappe.sendmail(delayed=True)` tới `alert_recipients` (`erp_ai/alerts.py:6-14`), mặc định `info@miyano.com.vn`. | Một danh sách người nhận dùng chung với cảnh báo khóa và nâng quyền; không có người nhận COO. Site có tài khoản gửi mail hay chưa: chưa kiểm. |
| A8-13 | Ghi dự đoán vào log riêng; cửa ≥ 85% trên ≥ 30 phiếu mới | PARTIAL | Dòng `classify` với `predicted_*` (`runner.py:296-318`); báo cáo cho số lượng và % theo đầu mục trong khoảng ngày chọn (`erp_ai/erp_ai_agent/report/erp_ai_accuracy/erp_ai_accuracy.py:14-54`). | % có thể cao hơn thật ở L0 (xem `audit-A1.md` dòng A1-8). Không kiểm "≥ 30". Chỉ System Manager chạy được; ERP AI Instructor (role dành cho COO) không chạy được. |

## Những gì app đang có

- Job theo lịch (3): `reprobe_exhausted_keys` mỗi giờ; `recompute_monthly_spend` và `check_privilege_escalation` mỗi ngày lúc 00:00 (`erp_ai/tasks.py:23-65,122-163`).
- Báo cáo (1): ERP AI Accuracy, Script Report trên ERP AI Log, lọc từ ngày/đến ngày, cột Đầu mục / Dự đoán / Bị sửa / Chờ / % đúng, chỉ System Manager.
- Dashboard, number card, biểu đồ, workspace, Notification, Auto Email Report: không có cái nào.

## Điểm đáng chú ý

- Không việc chạy theo lịch nào phục vụ vận hành; cả ba đều là bảo trì (khóa, chi phí, quyền). Báo cáo 8h cần thêm khóa `cron`.
- KPI "phiếu đóng không cần người" và việc tự đóng phiếu F bị chặn bởi thiết kế: phải có quyết định cho bot đổi trạng thái phiếu.
- KPI phản hồi đầu tiên không phản ánh được bot chừng nào bot còn trả lời bằng Comment nội bộ.
- Kiểm site production trước khi dựng A8-3, A8-4: hai trường "Nguồn phát sinh" và "Hạn hoàn thành" không có trên site dev.
