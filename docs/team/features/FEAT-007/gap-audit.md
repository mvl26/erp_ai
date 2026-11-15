Feature: FEAT-007
Stage: intake
Author-agent: team-leader
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Bảng đối chiếu tổng hợp — app `erp_ai` so với "Chiến lược AI Agent Helpdesk Miyano"

## Kết luận

App chưa đáp ứng đủ tài liệu chiến lược. Phần lõi đã có: 6 đầu mục, phân loại, routing theo cấu hình, 4 mức quyền, giới hạn lượt và ngân sách, nhật ký, tài khoản agent riêng. Phần vận hành gần như chưa có: báo cáo cho COO, KPI, việc chạy theo lịch, bài CSKT, trả lời người tạo phiếu, đóng phiếu. Ngoài ra có 9 dòng đối chiếu cho thấy app đang làm điều tài liệu cấm hoặc buộc phải qua duyệt; chúng đến từ code viết theo lệnh trực tiếp ngày 2026-11-13 và từ FEAT-004.

## Cách làm và giới hạn

- Mốc: `develop` @ `7cc37bb` (2026-11-14), cộng cấu hình đang lưu trên site dev `miyano`.
- 8 lệnh Explore chỉ-đọc, mỗi lệnh một nhóm yêu cầu; kết quả ở `audit-A1.md` … `audit-A8.md`, có `file:line` cho từng dòng. Team-leader tự đọc lại `prompts.py`, `policy.py`, `classification.py`, `handlers.py`, `route_ticket.py`, `site_api.py:1-300`, `registry.py:1-112` để soát các dòng nặng nhất.
- Không chạy test, không chạy thử hành vi nào. Những chỗ ghi "chưa chạy thử" là đọc mã mà kết luận.
- Chưa kiểm được: site production `erp.miyano.com.vn` (các trường "Nguồn phát sinh", "Hạn hoàn thành", "Tính chất phiếu" có hay không, tên trường là gì); Server Script lưu trong cơ sở dữ liệu; đường dẫn Duyệt hiện thế nào trên trình duyệt thật.
- Một yêu cầu có thể được soát ở hơn một nhóm, nên số dòng dưới đây lớn hơn số yêu cầu.

## Số liệu

| Nhóm | MET | PARTIAL | MISSING | CONTRADICTS | DECIDED-DIFFERENTLY | NOT-APP | Tổng |
|---|---|---|---|---|---|---|---|
| A1 Phân loại và điền trường | 2 | 6 | 1 | 0 | 1 | 2 | 12 |
| A2 Phân luồng, SLA, Task | 1 | 8 | 2 | 0 | 1 | 0 | 12 |
| A3 Vòng lặp, mức tự chủ, duyệt | 0 | 9 | 0 | 1 | 2 | 0 | 12 |
| A4 Công cụ | 4 | 11 | 1 | 1 | 4 | 0 | 21 |
| A5 Tri thức, dữ liệu nhạy cảm | 2 | 5 | 2 | 1 | 2 | 0 | 12 |
| A6 Kiến trúc, cấu hình | 1 | 7 | 0 | 1 | 2 | 1 | 12 |
| A7 Guardrail, chi phí | 0 | 5 | 0 | 5 | 0 | 1 | 11 |
| A8 Báo cáo, KPI, lịch chạy | 0 | 4 | 10 | 0 | 2 | 1 | 17 |
| Tổng | 10 | 55 | 16 | 9 | 14 | 5 | 109 |

## 1. Đã đúng (MET)

- Phân loại đúng 6 đầu mục và ghi vào Loại phiếu từ L1 (A1-1); dấu hiệu nhận biết có trong prompt phân loại (A1-2).
- Cấu hình routing sửa được không cần deploy, không có tên người trong mã (A2-12).
- Công cụ: đọc phiếu, tìm phiếu đã Resolved, comment, tạo Task liên kết (A4-1, A4-2, A4-9, A4-11).
- Không gửi file đính kèm hay email lên API (A5-3b, A5-7).
- Trường AI, chỉ báo trạng thái và ngăn trao đổi trên trang phiếu (A6-12).

## 2. Lệch có quyết định ghi lại (DECIDED-DIFFERENTLY)

Các điểm này app làm khác tài liệu vì hướng dẫn 2.2 (`docs/HuongDan_TrienKhai_erp-ai.md:1474-1490`), một spec hoặc một ADR đã chọn khác. FEAT-007 giữ nguyên, trừ điểm nào người quyết đổi.

| Điểm | Tài liệu | App | Quyết định |
|---|---|---|---|
| Kiến trúc (A6-1, A6-2, A4-21) | Dịch vụ Python riêng, REST, webhook, systemd, Claude Agent SDK | Job nền trong bench, `doc_events`, SDK `anthropic` | Hướng dẫn `:1480`, ADR-002, ADR-003 |
| L0 (A1-7, A3-2) | Điền trường, không comment | Chỉ ghi dự đoán vào log | Hướng dẫn `:1485`, FEAT-001 A-3 |
| Duyệt hành động (A3-1, A8-8, A8-9) | Danh mục trắng + nút Duyệt/Sửa/Từ chối cho từng hành động | Thẩm quyền theo người ra lệnh | Hướng dẫn `:1481` |
| Đọc bản ghi (A4-3) | `get_doc` bất kỳ DocType | Danh sách cho phép 6 DocType + danh sách cấm | Hướng dẫn `:1482` |
| Server Script (A4-18) | Chỉ site test | Viết trên production, luôn tắt | Hướng dẫn `:1483` |
| Gán người (A4-12, A2-2 phần F) | Tool `assign`; F giao cho Bot | Runner gán theo cấu hình; không gán cho tài khoản bot | FEAT-006 AC-9, A-7; ADR-021 |
| SLA và Assignment Rule (A2-5) | Cấu hình sẵn theo bảng | App không tạo bản ghi cấu hình Helpdesk | FEAT-006 QĐ-5 |
| Nhóm nhạy cảm (A5-3a) | Không trích vào CSKT, không gửi file | Không xử lý phiếu của nhóm loại trừ | Hướng dẫn 13.2 |
| Trả lời người tạo (A5-6) | `reply_to_user` | Chỉ comment nội bộ | Hướng dẫn `:34` và 13.3 |
| Cài 6 Loại phiếu (A1-1) | Thay bộ giá trị cũ | App không tạo bản ghi, coi là việc GĐ0 | FEAT-001 A-8 |

## 3. Trái tài liệu (CONTRADICTS): cần người quyết

| # | App đang làm gì | Tài liệu nói gì | Nguồn | Dòng đối chiếu |
|---|---|---|---|---|
| C1 | Công tắc "Toàn quyền (khẩn cấp)": xóa bản ghi, sửa phân quyền (bot tự thêm được System Manager cho chính nó), hủy chứng từ đã submit, gọi mọi hàm whitelist. Chạy từ L1, vẫn còn khi vượt ngân sách. Mặc định tắt. | "Cấm tuyệt đối: xóa bản ghi, sửa Role Permission, … thao tác trên Purchase Invoice/Payment Entry đã submit" | Lệnh trực tiếp 13/11 | A4-20, A7-1, A7-7 |
| C2 | Công cụ bản ghi chung (`site_api.py`): tạo/sửa mọi DocType không nằm trong danh sách cấm, thẳng trên site đang chạy, không qua duyệt (Custom Field, Client Script, Workflow, User…) | "Danh sách DocType được ghi là danh mục trắng, mặc định cấm"; "chạy trên site test trước, dev duyệt rồi mới đưa lên" | Lệnh trực tiếp 13/11 | A7-1, A7-2, A6-7 |
| C3 | Khối prompt "LÀM LUÔN, KHÔNG HỎI LẠI": ghi bản ghi ngay, không chờ xác nhận | L1 chỉ đề xuất; L2 làm sau khi người phụ trách bấm Duyệt | Lệnh trực tiếp 13/11 (CHG-001, chưa có bản ghi được duyệt) | A3-11, A7-10 |
| C4 | Sửa code trong `apps/` và chạy `bench migrate` trên site đang chạy sau một lần bấm; không gì phân biệt site production | "Cấm tuyệt đối: chạy migrate/deploy production"; code chỉ trên site test | FEAT-004 (quy trình thường, người yêu cầu) | A4-20, A7-7, A7-9 |
| C5 | Đường dẫn Duyệt là một lần GET đổi trạng thái, không hộp xác nhận, không hết hạn | Người phụ trách bấm duyệt (tài liệu không nói cách) | Lệnh trực tiếp 13/11; trái ADR-012 QĐ 4 | A7-9 |
| C6 | Công cụ bản ghi chung đọc được phiếu của nhóm loại trừ và phiếu có cờ không dùng AI | Dữ liệu nhóm Nhân sự & HC / Kế toán phải được bảo vệ | Hệ quả không ai yêu cầu của code 13/11; trái NFR-4 của FEAT-001 và `README.md:39` | A5-3c |

C6 là lỗ rò không nằm trong lệnh nào, nên được vá bất kể người chọn phương án nào cho C1–C5.

## 4. Còn thiếu hoặc mới làm một phần

Chia theo mức đụng chạm với các file mà phiên FEAT-004/005 đang sửa. Đây là gợi ý cho bước spec và plan, chưa phải quyết định phạm vi.

### 4.1 Phần thêm mới, chủ yếu file mới

| # | Việc | Dòng đối chiếu |
|---|---|---|
| G1 | Quét bù định kỳ (Hình 2: "mỗi 15 phút") cho phiếu chưa phân loại và lần chạy lỗi; đo mốc 5 phút | A1-4 |
| G2 | Báo cáo hằng ngày 8h cho COO: phiếu mới, phiếu sắp quá hạn, việc bot đã làm; người nhận cấu hình được | A8-1, A8-12 |
| G3 | 6 KPI tính hằng tuần và đưa lên trang tổng quan | A8-2a..f |
| G4 | Nhắc hạn (D, E), tổng hợp tiến độ cho COO; kiểm và nhắc mốc Task 3 ngày (C, D), BA note 24 giờ | A8-4, A8-5, A2-7 |
| G5 | Task xong thì phiếu Resolved (#1770) | A2-8, A8-6 |
| G6 | Phiếu F tự đóng sau 3 ngày im lặng; không bao giờ với Chỉ đạo BGĐ và đầu mục E | A8-3, A5-4c, A2-6 |
| G7 | Soạn bài CSKT nháp khi phiếu đóng, có chốt nhóm nhạy cảm | A5-2, A8-7 |
| G8 | Tìm CSKT theo nội dung; kho HDSD và công cụ tìm; phiếu cũ trả về cách giải quyết thật | A4-6, A4-7, A5-1, A5-8 |
| G9 | Công cụ đọc riêng: chạy báo cáo, đọc Error Log | A4-4, A4-5 |
| G10 | Trả lời tới người tạo phiếu; nhận trả lời của họ qua email/cổng | A4-10, A5-4b, A5-6 |
| G11 | Hỗ trợ rà ngẫu nhiên 10 phiếu mỗi tháng | A7-4, A8-10 |
| G12 | Cửa L0 → L1 đo được: kết luận 85%, tối thiểu 30 phiếu, ghi nhãn người gõ lúc tạo; Instructor xem được báo cáo | A1-8, A8-13 |
| G13 | Chi phí theo phiếu và theo lần chạy; báo khi vượt ngân sách hoặc chạm giới hạn ngày | A6-9, A7-6 |

### 4.2 Phần điều chỉnh, đụng `registry.py`, `policy.py`, `prompts.py`, `runner.py`, `routing.py`, `handlers.py`, ERP AI Setting

| # | Việc | Dòng đối chiếu |
|---|---|---|
| H1 | Bot không ghi đè lựa chọn người đã điền lúc tạo phiếu (kể cả điền một phần) | A1-5, A2-3, A2-11 |
| H2 | Độ tin cậy thấp thì chỉ hỏi, không ghi, không hành động; mỗi đề xuất nêu độ tin cậy và bằng chứng | A1-12, A3-7, A7-3 |
| H3 | Mọi hành động của bot có một comment trên phiếu (routing thành công, kết quả áp dụng, bỏ qua, lỗi) | A3-8, A3-6 |
| H4 | L2 thật sự "làm sau duyệt" cho hành động ghi ERP; L3 chỉ cho danh mục trắng; mức theo đầu mục; đếm số lần duyệt theo loại việc | A3-4, A3-5, A3-9, A3-12 |
| H5 | Danh mục trắng DocType/hành động nằm trong cấu hình, mặc định cấm; công cụ riêng cho việc B (tài khoản theo mẫu, thêm người vào nhóm, ngày nghỉ, Item Group, Custom Field) | A7-1, A6-5, A4-13..17 |
| H6 | Vá rò dữ liệu nhạy cảm: phiếu chưa có nhóm; công cụ bản ghi chung | A5-3a, A5-3c, A7-5 |
| H7 | Vượt ngân sách thì mọi nhóm công cụ ghi đều lui | A7-6 |
| H8 | Nhật ký hành động đủ cho mọi lần ghi (đích, giá trị trước/sau, người ra lệnh) | A6-8 |
| H9 | Prompt sửa được trong cấu hình | A6-5 |
| H10 | Khái niệm site test/production và chốt theo nó | A6-7, A7-2 |
| H11 | Dùng các trường sẵn có của phiếu khi site có (Nguồn phát sinh, Hạn hoàn thành, Tính chất phiếu, Phân hệ ERP…) | A1-3, A2-6 |
| H12 | Ngoại lệ ưu tiên và mốc SLA phản hồi được kiểm bằng mã; D/E "theo Hạn hoàn thành"; IT theo dõi phiếu D; đề xuất tách phiếu gộp | A2-3, A2-4, A2-10, A2-9 |
| H13 | Đầu mục C: BA note, nhiều Task có ước lượng, Project | A3-10 |
| H14 | Tái dùng khung cho bot đơn hàng và bot CRM | A6-6 |

## 5. Việc tổ chức hoặc dữ liệu site (NOT-APP)

- GĐ0 trên site: 6 Loại phiếu thay bộ cũ, bắt buộc Nhóm + Ưu tiên, SLA và Assignment Rule theo bảng mục 3, gán tay lại phiếu cũ.
- Chốt ngân sách tháng, người giữ khóa, người được cấp ERP AI Instructor.
- Hiện trạng site dev `miyano` (đọc 2026-11-14): đủ 6 Loại phiếu mới nhưng còn 4 loại cũ; 4 HD Team (thiếu Kế toán, Mua hàng, Marketing, Kho vận); 2 SLA đều không theo bảng; Assignment Rule chỉ có bản mặc định; 2 phiếu; 1 bài CSKT nháp. Tài khoản agent đang mang rất nhiều role, kể cả `ERP AI Instructor` (cài đặt chỉ cấp 2 role; BUG-002 đã ghi nguồn gốc).

## 6. Điểm cần architect phán

1. Bot gán phiếu cho ai thì người đó thành "người ra lệnh" trên phiếu ấy (`erp_ai/agent/authority.py:52-69`); mở tool Task và, ở L3, tool bản ghi.
2. Tool ghi được cấp theo người ra lệnh gần nhất trong 30 comment, không theo người vừa gõ `@ai` (`erp_ai/agent/runner.py:171`, `authority.py:72-77`).
3. Chốt "luôn đóng" của `api_call_method` là so chuỗi con (`erp_ai/agent/tools/site_api.py:213-219`); đọc mã thì thấy lách được bằng ký tự thoát trong JSON lồng. Chưa chạy thử.
4. Job áp dụng thay đổi chạy dưới tên người duyệt và không kiểm lại role của người đó lúc áp dụng (ADR-012 QĐ 7 đòi kiểm).
5. Mọi ADR đang "proposed", `Approved-by` trống; ADR-014..018 (FEAT-005) trên thực tế bị `site_api.py` thay thế.
