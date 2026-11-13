Feature: FEAT-006
Stage: intake
Author-agent: team-leader
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Intake FEAT-006 — Bot tự chia nhóm, gán người làm và SLA theo độ phức tạp, độ quan trọng của phiếu

- Yêu cầu gốc: "con bot đã có thể dựa theo yêu cầu đầu vào của ticket để chia nhóm và gán người làm chưa, dựa vào các thông tin để tự động chia việc, gán sla dựa theo độ phức tạp và độ quán trọng", rồi "dựa theo yêu cầu này làm đi, gọi skill để làm".
- Nguồn: hội thoại (2026-11-12)
- Loại việc: feature
- Playbook: new-feature
- Size: L
- Mode: decide
- Lý do chọn playbook/cỡ: hành vi mới cho hệ thống đang chạy. Cỡ L vì đụng nhiều module (phân loại, tool ghi phiếu và registry, prompt, ERP AI Setting, có thể thêm trường trên HD Ticket), có thay đổi dữ liệu và quyền (gán người tạo ToDo, gửi thông báo), ước tính hơn 5 ngày công. Bằng chứng:
  - Bot chỉ ghi `ticket_type`/`agent_group`/`priority` lấy từ bảng ánh xạ cố định theo đầu mục: `erp_ai/agent/classification.py:15-22` và `:116-122`, `erp_ai/agent/tools/write_ticket.py:39-57`.
  - Chỉ có 4 tool ghi phiếu, không tool nào gán người: `erp_ai/agent/tools/write_ticket.py:113,133,147,161`.
  - Người mặc định và SLA chỉ là chữ trong prompt, không có code nào ghi xuống phiếu: `erp_ai/agent/prompts.py:135-145`.
  - Mức ưu tiên chỉ theo đầu mục và tag `[GẤP]` (`classification.py:116-122`). Không có bước chấm độ phức tạp hay độ quan trọng.
- Skill tạm: không cần cho bước phân tích. Ghi chú cho plan: chưa thấy cần.
- Ngân sách: max_agents_per_feature = 10; feature_budget_usd = không giới hạn

## Quyết định của team-leader (decide mode, người bảo "làm đi" thay cho câu hỏi về nguồn SLA)
| # | Chọn | Vì | Phương án khác | Sai thì hoàn tác |
|---|---|---|---|---|
| QĐ-1 | Mức SLA mặc định lấy theo bảng routing hướng dẫn 16.2 (`prompts.py:135-145`), đưa vào cấu hình sửa được. Thời hạn phản hồi/xử lý thật do Helpdesk tính (HD Service Level Agreement theo `priority` và `condition`). Bot không tự tính `response_by`/`resolution_by`. | Bảng 16.2 là tài liệu nghiệp vụ đã có. Tái dùng bộ tính SLA của Helpdesk, có giờ làm việc và ngày nghỉ (STD-DESIGN-5). | Bot tự tính và ghi thẳng hạn chót; dựng ma trận SLA mới từ đầu | Sửa cấu hình, hoặc change-request đổi nguồn SLA |
| QĐ-2 | "Chia việc" = chọn nhóm, người phụ trách và (đầu mục C/D) tạo Task giao người. Bot không tự tách phiếu. | Giữ quy ước 4 "một phiếu một việc, agent không tự tách" (`prompts.py:152`) và quy ước 3 (C/D phải có Task) | Bot tự tách phiếu gộp thành nhiều phiếu mới | Change-request: cho tách sau khi người tạo xác nhận |
| QĐ-3 | Không ghi đè việc của người: phiếu đã có người gán do con người, hoặc đã được người phân loại (`write_ticket.py:43`), thì bot không đổi nhóm/người. Phiếu `Chỉ đạo BGĐ` luôn có người phụ trách là con người (`prompts.py:150`). | Bot chỉ là trợ lý; tránh giành việc đã chia | Bot luôn chia lại theo điểm mới | Bỏ điều kiện trong tool |
| QĐ-4 | Danh sách người mặc định theo nhóm/đầu mục nằm trong cấu hình, không viết tên người vào code. | STD-DESIGN-7. Nhân sự đổi thì sửa cấu hình, không deploy lại. | Viết tên cứng như bảng prompt | Không cần |
| QĐ-5 | FEAT-006 không ghi cấu hình Helpdesk (HD Team, Assignment Rule, HD Service Level Agreement). Chỉ ghi giá trị trên phiếu và việc gán. Site thiếu bản ghi SLA thì bot báo, không tự tạo. | Ghi DocType cấu hình là phạm vi FEAT-005 (`docs/team/features/FEAT-005/intake.md`) | Gộp tạo SLA vào feature này | Change-request sau khi FEAT-005 xong |

## Điểm phải giải trong spec/design
- **Chấm độ phức tạp và độ quan trọng:** dùng thang nào, bước nào chấm (classify hay reason), và kết hợp với các ngoại lệ trong bảng 16.2 thế nào để ra `priority`. Các ngoại lệ đó là: "Urgent nếu chặn nghiệp vụ kế toán/kho", "High nếu có hạn trong 24h", D "High nếu có Hạn hoàn thành". Lưu điểm và lý do vào đâu để người xem lại.
- **Chọn người:** Helpdesk đã có Assignment Rule cho từng HD Team (`apps/helpdesk/helpdesk/helpdesk/doctype/hd_team/hd_team.py:23-24,63-81`) và tự gỡ người khi đổi nhóm (`hd_ticket.py:428-481`). Cần chốt: tái dùng rule của nhóm, hay bot chọn người cụ thể theo cấu hình cộng tải việc (số phiếu mở). Cách gán: `assign_agent` (`hd_ticket.py:483-487`, có gửi thông báo/email).
- **SLA:** Helpdesk chọn SLA mỗi lần lưu phiếu theo `priority` và `condition` (`hd_ticket.py:101,112,970-999`; `hd_service_level_agreement/utils.py:12-42`). Cần biết site `miyano` đã có bản ghi SLA nào. Nếu muốn SLA khác theo độ phức tạp thì `condition` cần một trường trên phiếu để dựa vào, tức là có thay đổi dữ liệu.
- **Quyền tài khoản agent:** cần quyền gán (ToDo, thông báo) mà không đổi role (ADR-006). Nội dung phiếu là dữ liệu không tin cậy (STD-SEC-5): người tạo phiếu không được tự chỉ định người làm hay SLA cho mình qua nội dung phiếu.
- **Đụng feature khác:** FEAT-003/004/005 cùng sửa registry, `prompts.py` (mục GIỚI HẠN) và `write_ticket.py`. Một phiên khác đang build FEAT-003 trên worktree chính (`team/FEAT-003`, `.team/active-build`), nên FEAT-006 phải làm nhánh `team/FEAT-006` trong worktree riêng, không checkout ở worktree chính.
- **Đo:** dùng bộ eval offline sẵn có (`erp_ai/eval/`) để đo độ đúng của điểm chấm trên phiếu cũ.

## Đổi cỡ (nếu có)
- Không có.
