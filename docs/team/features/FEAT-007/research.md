Feature: FEAT-007
Stage: research
Author-agent: team-leader
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Research FEAT-007 — mục lục

File này là mục lục do team-leader lập. Nội dung nghiên cứu nằm ở 5 file `research-R1.md` … `research-R5.md` cùng thư mục, mỗi file do một lệnh researcher viết và có mục `## Sources` riêng. Phiên bản: helpdesk 15.1.0, frappe 15.126.1. Không lệnh nào chạy test hay ghi vào site `miyano`.

Câu trả lời dưới đây chép từ báo cáo trả về của từng lệnh; chi tiết và `path:line` xem trong file tương ứng.

| Câu | Hỏi gì | Trả lời | File |
|---|---|---|---|
| R-1 | Bot trả lời người tạo phiếu qua kênh nào; có đặt mốc phản hồi đầu tiên không; trả lời của họ quay lại bằng sự kiện nào | `HD Ticket.reply_via_agent` tạo Communication loại `Sent` (kèm email nếu site có tài khoản gửi đi) và hiện trên cổng khách; comment thì không bao giờ tới họ. Lưu một Communication `Sent` là đặt `first_responded_on`, kể cả khi không gửi được email. Tài khoản agent gọi được nhờ role `Agent`. Gửi email cần một Email Account có `enable_outgoing=1` và `default_outgoing=1`, thiếu thì lời gọi ném lỗi trước khi ghi. Trả lời của người tạo (email hoặc cổng) đi qua `HD Ticket.on_communication_update`; Helpdesk không đăng ký `doc_events` trên Communication nên app gắn hook được. Bẫy: thư mở phiếu cũng là một Communication `Received`, và `on_update` có thể chạy hai lần cho một email. | `research-R1.md` |
| R-2 | Trang tổng quan Helpdesk có nhận thêm thẻ hoặc biểu đồ của app khác không | Không: 5 thẻ của `/dashboard` và 7 biểu đồ của `/home` đều viết cứng. Xếp hạng: (1) Script Report của app, 6 dòng KPI với cột tuần này, tuần trước, mục tiêu sau GĐ2, mục tiêu sau GĐ4, mở ở `/app/query-report/...`; (2) ghi đè `helpdesk.api.dashboard.get_dashboard_data` bằng `override_whitelisted_methods` để thêm thẻ vào `/dashboard`, không sửa file Helpdesk nhưng vá một API nội bộ; (3) Workspace của app với Number Card. Trang tổng quan Helpdesk chỉ coi `Agent Manager` là quản lý. | `research-R2.md` |
| R-3 | Comment của bot hiện thế nào trên dòng thời gian; nút duyệt đặt ở đâu được | HTML của comment bị lọc khi lưu (`Comment.validate`), không phải khi hiển thị. `<a href>` còn và bấm được, mở tab mới; `<button>`, `<form>` bị đổi thành chữ. HD Form Script thêm được hành động ở đầu trang phiếu và hộp thoại `$dialog`, không thêm được gì vào trong dòng thời gian. Xếp hạng chỗ đặt Duyệt / Sửa / Từ chối: (1) hành động đầu trang + `$dialog`, gọi method POST; (2) ngăn riêng của app trong `agent_status_indicator.js`; (3) đường dẫn trong comment tới form Desk. | `research-R3.md` |
| R-4 | Tìm bài CSKT, trạng thái bài, quyền tạo nháp; kho HDSD nên nằm ở đâu | `helpdesk.api.article.search` dùng RediSearch, chỉ đánh chỉ mục bài `Published`, trả tối đa 5 kết quả; tài khoản agent gọi được. Ba vấn đề đọc từ mã: hàm chuẩn hóa câu tìm bỏ dấu tiếng Việt, không tự đánh lại chỉ mục khi lưu bài, và module RediSearch trên bench chưa kiểm được. Trạng thái: `Published`, `Draft` (mặc định), `Archived`. Role `Agent` tạo được bài nháp nhưng cũng xuất bản được, nên "bài nháp chờ người duyệt" cần chốt trong mã của app. Kho HDSD, xếp hạng: (1) theo khuyến nghị của researcher, thư mục file `.md` cấu hình được + một công cụ tìm riêng; (2) bài CSKT trong chuyên mục "HDSD"; (3) DocType mới. | `research-R4.md` |
| R-5 | Lịch 15 phút, 08:00 hằng ngày, hằng tuần, hằng tháng; hàng đợi; worker `long` | Khóa `cron` của `scheduler_events`: `*/15 * * * *`, `0 8 * * *`, `0 8 * * 1`, `0 8 1 * *`. Scheduler tính theo `System Settings.time_zone` của site, trống thì rơi về Asia/Kolkata. Lượt lỡ không được chạy bù từng lượt: tick kế tiếp chạy một lần. Việc theo `cron` chạy ở hàng đợi `default`, trần 300 giây; việc dài hơn thì method cron phải tự xếp một job sang `long`. | `research-R5.md` |

## Câu hỏi cho người (chưa hỏi; gom vào vòng hỏi kế tiếp)

1. Bộ HDSD chính thức của Miyano đang nằm ở đâu và ở dạng nào (`.md` trong `apps/erpnext/docs/`, `.docx` hoặc PDF trên ổ chung, trang trên Helpdesk hay ERPNext), và khách hàng có được thấy trên cổng không (R-4).
2. Site `miyano` và site production đã có Email Account gửi đi mặc định chưa (R-1, mục U-1 đến U-3 của `research-R1.md`).

## Việc chỉ kiểm được trên production hoặc trình duyệt thật (UNVERIFIED)

- R-1: một email trả lời thật có quay về và gắn đúng phiếu không (U-1 đến U-7 trong file).
- R-2: tài khoản Instructor mở được báo cáo không; role `Agent` có vào được Desk trên site này không.
- R-3: đường dẫn trong comment hiện và bấm thế nào; `$dialog` có ô nhập chạy được không, kể cả trên điện thoại (B1 đến B5 trong file).
- R-4: module RediSearch có chạy trên bench không; Custom DocPerm của HD Article trên site.
- R-5: `System Settings.time_zone` của production; production có worker phục vụ hàng đợi `long` không (`supervisorctl status`, `bench --site <site> doctor`).

## Sources

Các URL dưới đây được researcher báo là tải được, ngày truy cập 2026-11-14. URL khác mà từng file dẫn (có trang trả 404) ghi rõ trong mục `## Sources` của file đó.

- https://docs.frappe.io/helpdesk/email-communication (R-1)
- https://docs.frappe.io/framework/user/en/python-api/hooks (R-2)
- https://docs.frappe.io/helpdesk/knowledge-base (R-4)
- Mã nguồn đã cài: `apps/helpdesk` 15.1.0 và `apps/frappe` 15.126.1 trên bench này (cả 5 câu).

## Lệch quy trình đã ghi

- Lần gọi researcher đầu (cả 5 câu trong một lệnh) hết 50 lượt, không ghi file nào.
- Ba lệnh researcher đã chạy lệnh ngoài phạm vi chỉ-đọc của vai: R-1 và R-4 dùng `sed -i` để sửa số dòng trong chính file của mình; R-3 chạy một lời gọi Python tới `sanitize_html` (hàm thuần, không mở site). Hook ở chế độ nhắc nên lệnh vẫn chạy.
