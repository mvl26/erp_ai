Feature: FEAT-002
Stage: analyze
Author-agent: analyst
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

**Đội `team` cần bạn trả lời trước khi làm tiếp `FEAT-002`** (Amendment 1, vòng 1/2)

Bối cảnh: bạn chọn bỏ comment tạm và thay bằng chỉ báo trực tiếp "đang suy nghĩ / đang làm". Phía server đã chốt xong: tín hiệu bắt đầu, đổi việc, kết thúc ở mọi nhánh; không tạo, sửa hay xóa bản ghi nào, nên ADR-004 giữ nguyên (spec Amendment 1, AC-2..AC-9). Còn một việc cần bạn quyết: chỉ báo hiện trên trang phiếu Helpdesk bằng cách nào. Mã và tài liệu không trả lời được câu này, vì nó tùy bạn có chấp nhận thêm mã giao diện hay không. Đã kiểm `helpdesk/desk/src/components/TypingIndicator.vue`, `composables/realtime.ts`, `components/ticket-agent/TicketHeader.vue:320-327`.

1. Chỉ báo hiện trên trang phiếu Helpdesk theo cách nào?
   - a) **Dùng chỉ báo "đang gõ" có sẵn của Helpdesk, không thêm mã giao diện.** Dưới khung soạn sẽ hiện `<tên tài khoản agent> is typing` kèm ba chấm động.
     - Hậu quả: không có đoạn mã giao diện nào, không sửa Helpdesk, ít việc nhất, giữ cỡ M.
     - Nhưng chữ là tiếng Anh cố định "is typing". **Không** hiện được "Đang suy nghĩ…" hay "Đang làm: <việc>…" (mục câu chữ trên form chỉ còn vai trò bật/tắt).
     - Nếu worker bị giết giữa chừng, chỉ báo nằm tới khi người tải lại trang.
     - Researcher vẫn phải xác nhận server phát được tín hiệu này.
   - b) **Chỉ báo riêng bằng tiếng Việt.** Hiện câu chữ cấu hình ("Đang suy nghĩ…") và "Đang làm: <việc>…", kèm tên agent. Cần một đoạn mã giao diện nhỏ chạy trên trang phiếu agent, do app `erp_ai` cung cấp hoặc cài vào site (ví dụ một HD Form Script). Đoạn mã này **trong phạm vi** FEAT-002, nhưng **không sửa mã nguồn Helpdesk**.
     - Hậu quả: đúng ý "như Claude"; tự mất sau tối đa 600 s kể cả khi worker chết (AC-11).
     - Thêm việc: researcher tìm cách làm, có thể cần ADR cho lớp giao diện, thêm JavaScript vào dự án, kiểm giao diện bằng tay.
     - Có thể đẩy cỡ lên L.
     - Nếu researcher thấy không làm được khi không sửa Helpdesk, đội quay về a và báo lại bạn.
   - c) **Làm a ngay trong FEAT-002, để b thành một feature riêng sau.**
     - Hậu quả: có chỉ báo sớm, FEAT-002 giữ cỡ M. Chữ tiếng Việt và "Đang làm" đến sau.
     - Phía server làm một lần dùng cho cả hai, vì tín hiệu ở AC-9 đã mang sẵn trạng thái và nhãn việc.
   - Khuyến nghị: **b**, vì bạn nói rõ muốn thấy chữ "đang suy nghĩ, đang làm". Cách a chỉ báo được là "có người đang gõ". Nếu bạn muốn chắc giữ cỡ M và có kết quả sớm, chọn **c**.
   - Câu trả lời đổi phần nào: b → thêm `/team:research` trước `/team:design`, AC-11 áp dụng, có thể đổi cỡ. a/c → bỏ AC-11, AC-1 câu chữ chỉ còn bật/tắt, AC-10 kiểm dòng "is typing".

Các điểm khác đội đã tự quyết, ghi trong spec Amendment 1 kèm cách sửa nếu sai:
- A-11: chỉ báo áp dụng cả lần chạy phân loại phiếu mới, nhưng chỉ trễ câu trả lời của `@ai`.
- A-13: khách không thấy chỉ báo.
- A-15: nhãn việc cố định bằng tiếng Việt.
- A-17: không có chỉ báo lúc job còn chờ hàng đợi.

Trả lời bằng một dòng, ví dụ:
```
A1: option b
```

## Câu trả lời của người (2026-11-12)

- Kênh: team-leader hỏi qua AskUserQuestion, 2026-11-12.
- Trả lời: `A1: option b`
- Ý người: chỉ báo riêng bằng tiếng Việt; mã giao diện nằm trong app `erp_ai`; không sửa mã nguồn Helpdesk.
- Đội ghi vào: spec.md, mục `### Chốt sau câu trả lời Q1 (2026-11-12)` trong Amendment 1. Vòng hỏi đóng (1/2). Không còn câu hỏi mở.
