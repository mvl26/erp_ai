# FEAT-007 R-1: kênh trả lời tới người tạo phiếu không có role Agent, mốc phản hồi đầu tiên, sự kiện khi người tạo trả lời

Câu hỏi: spec `## Câu hỏi kỹ thuật` R-1 (AC-40, AC-41, KPI 1). Ngày: 2026-11-14. Researcher, chỉ đọc mã nguồn cài trên bench, không chạy gì trên site `miyano`.
Không áp dụng lại: `audit-A5.md` A5-4b, A5-6; `audit-A8.md` A8-2a.

## Phiên bản đang dùng
| Thành phần | Phiên bản | Nguồn |
|---|---|---|
| Helpdesk | 15.1.0 | `/home/miyano/frappe-bench/apps/helpdesk/helpdesk/__init__.py` (`__version__`) |
| Frappe | 15.126.1 | `/home/miyano/frappe-bench/apps/frappe/frappe/__init__.py` (`__version__`) |

Đường dẫn rút gọn: `H` = `/home/miyano/frappe-bench/apps/helpdesk/helpdesk`, `F` = `/home/miyano/frappe-bench/apps/frappe/frappe`, `T` = `H/helpdesk/doctype/hd_ticket/hd_ticket.py`.

## Trả lời ngắn
| | Câu | Đáp |
|---|---|---|
| (a) | Kênh nào tới được người tạo phiếu không có role Agent | Có: `HD Ticket.reply_via_agent` (Communication `Sent`). Cổng khách hiện nó; email đi kèm nếu có tài khoản email gửi đi. Comment thì không bao giờ tới. |
| (b) | Có đặt `first_responded_on` không | Có, ngay khi Communication `Sent` được lưu (cả khi không gửi email), trừ loại `Automated Message`. |
| (c) | `ai.agent@miyano.com.vn` dùng được không, site cần gì | Dùng được về mặt mã (role `Agent` là đủ); cần 1 Email Account `enable_outgoing=1` để có email; phần dữ liệu thực của site là UNVERIFIED (kiểm ở mục 5). |
| (d) | Sự kiện khi người tạo trả lời | `HD Ticket.on_communication_update(c)`, gọi từ `Communication.on_update`, cho cả email lẫn cổng; Helpdesk không có `doc_events` nào trên Communication, nên app khác móc được `doc_events["Communication"]`. |

## (a) Kênh tới người tạo phiếu không có role Agent

Xếp hạng:
1. **`reply_via_agent` (Communication `Sent`, medium Email)**: dùng được. Khuyến nghị.
2. **Cổng khách chỉ là nơi hiển thị**, không phải kênh gửi riêng: hiện mọi Communication của phiếu.
3. **Comment (`new_comment` / `add_comment`)**: không tới được người tạo. Đã kết luận ở A5-6; xác nhận lại bằng mã dưới.

Bằng chứng:
- `reply_via_agent` là `@frappe.whitelist()` (`T:667`), chặn bằng `is_agent()` (`T:677-680`). Tạo `Communication` `communication_type="Communication"`, `sent_or_received="Sent"`, `reference_doctype="HD Ticket"`, `recipients=to` (`T:698-716`), `insert(ignore_permissions=True)` (`T:737`).
- Email chỉ gửi khi `skip_email_workflow` = 0 và `HD Settings.enable_reply_email_via_agent` = 1 (`T:723-725`). Mặc định cả hai cho phép gửi: `skip_email_workflow` default 0, `enable_reply_email_via_agent` default 1, `instantly_send_email` default 0 (`H/helpdesk/doctype/hd_settings/hd_settings.json`, đọc bằng JSON: các trường cùng tên). Nếu một trong hai chặn thì hàm trả về ở `T:748-749`: Communication vẫn có, email không đi.
- Gửi bằng `frappe.sendmail(... recipients=recipients, reference_doctype="HD Ticket", reference_name=self.name ...)` (`T:777-796`); `delayed=True` trừ khi `instantly_send_email`=1 (`T:769-774`), tức vào hàng đợi Email Queue và scheduler gửi (`F/hooks.py` mục `"all"`: `frappe.email.queue.flush`).
- Cổng khách: `get_one` (`H/helpdesk/doctype/hd_ticket/api.py:31-61`) trả `communications` từ `get_communications` (`api.py:83-112`): mọi Communication của phiếu, cả `Sent` lẫn `Received`, kiểm quyền đọc phiếu (`api.py:84`). Người tạo (`doc.raised_by`) được đọc phiếu (`T:1356`). Comment không có trong danh sách này; Comment còn bị chặn tạo và đọc với người không phải agent (`H/extends/comment.py:15-22, 57-79`, đã có ở A5-6).
- Dấu vết trong mã gọi: `erp_ai/agent/tools/write_ticket.py:102-112` hiện chỉ gọi `doc.new_comment(...)`. Chưa có chỗ nào trong erp_ai gọi `reply_via_agent` (không tìm thấy trong `erp_ai/agent/tools/`; kiểm lại bằng grep khi viết design).

Lưu ý cho design:
- `to` bắt buộc do người gọi đưa vào (`T:687`); với phiếu có `raised_by`, dùng đúng giá trị đó. `to` rỗng thì Communication vẫn lưu nhưng `frappe.sendmail` không có người nhận: UNVERIFIED hành vi chính xác, kiểm bằng test trên site thử (không phải `miyano`) có `to=None`.
- `from_email=None` thì `sender = frappe.session.user` (`T:686`) và tài khoản gửi lấy theo `sender_email()` (`T:596-609`): (i) email account của Communication gần nhất nếu `enable_outgoing` (`T:582-594`), (ii) tài khoản `default_outgoing=1` có IMAP folder `append_to="HD Ticket"` (`H/helpdesk/utils/email.py:27-40`), (iii) bất kỳ tài khoản `default_outgoing=1` (`H/helpdesk/utils/email.py:14-24`). Địa chỉ hiện ở thư là địa chỉ của tài khoản đó, không phải `ai.agent@` (`T:753, 790-791`).
- `reply_via_agent` có tham số `from_email` để ép tài khoản (`T:530-539`); nhánh này cần `Email Account` có tên đó (`T:535-536`).
- Phiếu qua cổng (`via_customer_portal`) dùng mẫu email `reply_via_agent_email_content` (`T:755-767`), phiếu qua email thì gửi nội dung thẳng.

## (b) `first_responded_on`

Có. Đường đặt:
- `Communication.on_update` gọi `parent.on_communication_update(self)` (`F/core/doctype/communication/communication.py:277-285`).
- Với `sent_or_received == "Sent"` và không phải `Automated Message`, `first_responded_on = first_responded_on or now` và `last_agent_response = now` (`T:1084-1092`); sau đó `self.save()` (`T:1112`). `reply_via_agent` tạo `communication_type="Communication"` (`T:703`) nên không bị loại.
- Điều này đúng kể cả khi email không đi (medium rỗng, `T:682`), vì chỉ xét `sent_or_received`.
- Đường khác của `set_first_responded_on` (`T:373-389`) chỉ đặt khi status category chuyển `Paused` hoặc `Open` sang `Resolved`; Comment không tạo Communication nên không đi vào `on_communication_update` (xem A8-2a: nhận định "Comment không tính là phản hồi đầu tiên" đúng, do `T:1062-1092` chỉ chạy từ Communication).
- Hệ quả KPI: thẻ "Avg. First Response" chỉ đếm phiếu có `sla` và `first_responded_on` (A8-2a, `H/api/dashboard.py:221-237`, grep xác nhận `dashboard.py:223`). Phiếu không có SLA thì `first_responded_on` vẫn được đặt nhưng không vào thẻ đó. Phản hồi đầu tiên có thể bị đặt bởi bất kỳ Communication `Sent` nào (kể cả của agent người), nên KPI "do bot" cần tự tính từ Communication, không dựa vào trường này: đề xuất, architect quyết.
- Rủi ro: `self.save()` ở `T:1112` chạy bằng quyền người gọi; `ai.agent` cần `write` HD Ticket (role `Agent` có, `hd_ticket.json` quyền `Agent`: read/write/create) và qua `has_permission` (`T:1352-1396`): nếu `restrict_tickets_by_agent_group` bật thì tài khoản phải thuộc nhóm hoặc được giao phiếu (`T:1372-1396`).

## (c) Tài khoản `ai.agent@miyano.com.vn`

- `is_agent()` (`H/utils.py:42-57`): không có bản ghi HD Agent thì `active is None`, xét role `Agent`/`Agent Manager`: role `Agent` → True. Vậy `reply_via_agent` không ném `PermissionError` về mặt role. Nếu sau này có bản ghi HD Agent với `is_active=0` thì False (`utils.py:52-55`).
- Job chạy dưới tài khoản này: `erp_ai/agent/runner.py:128` (`frappe.set_user(AGENT_USER)`; `erp_ai/constants.py:1`), nên `frappe.session.user` đúng cho `is_agent()`.
- Site cần có (để có email): ít nhất 1 `Email Account` với `enable_outgoing=1` và `default_outgoing=1` (cách an toàn nhất: `find_outgoing`/`find_default_outgoing`, `F/email/doctype/email_account/email_account.py:406-425`, ném `OutgoingEmailError` nếu không có và không có cấu hình trong site_config). Không cần tài khoản email riêng cho `ai.agent@`, trừ khi muốn thư đi từ địa chỉ đó (`from_email`).
- Không có tài khoản gửi đi: `reply_via_agent` ném lỗi "Unable to send email. Please setup default outgoing email account." trước khi ghi (`T:727-735`) khi `should_send_email` đúng. Đây là đường lỗi cần ghi vào AC.
- Gửi thật: Email Queue + scheduler (`F/hooks.py`, `frappe.email.queue.flush`); scheduler phải bật, và nếu `instantly_send_email`=0 thì thư chờ vòng flush.
- Docs chính thức: Helpdesk cần ít nhất một Email Account mặc định cho gửi đi và một cho nhận (nguồn 1).

## (d) Sự kiện khi người tạo trả lời

| Đường | Mã | Ghi chú |
|---|---|---|
| Email | `InboundMail._build_communication_doc` tạo `Communication` (`F/email/receive.py:703-730`, `insert` tại `:730`), sau đó `communication.save()` lại (`receive.py:738`). Gắn vào phiếu qua In-Reply-To/References (`H/overrides/email_account.py:57-100`). | `Communication.on_update` chạy ở cả insert lẫn save, nên sự kiện có thể tới 2 lần cho một thư. Mail tự động (bounce, auto-submitted) bị đưa sang Unhandled Email, không tạo Communication (`H/overrides/email_account.py:13-35, 141-169, 187`). |
| Cổng khách | SPA gọi `run_doc_method` → `HD Ticket.create_communication_via_contact` (`desk/src/pages/ticket/TicketCustomer.vue:290`; `T:809-838`): đặt lại status, `self.save`, rồi `Communication` `Received` `save` | Cùng `on_communication_update` |
| Cả hai | `T:1062-1112`: `Received` thì status = `ticket_reopen_status` nếu từng có agent trả lời (`has_agent_replied`, `T:398-406`) ngược lại `default_open_status`; đặt `last_customer_response`; `self.save()` | Hook `doc_events` của Helpdesk không có `Communication` (`H/hooks.py:76-108`) |

Với app erp_ai, điểm móc có thể (không quyết, để architect): `doc_events["Communication"]` (`after_insert` hoặc `on_update`) lọc `reference_doctype == "HD Ticket"` và `sent_or_received == "Received"`; đọc `H/hooks.py:76-108` xác nhận Helpdesk không tranh chấp. Cạm bẫy cần đưa vào thiết kế:
- Tin đầu của phiếu cũng là Communication `Received`: `after_insert` của phiếu gọi `create_communication_via_contact(description, new_ticket=True)` (`T:185-190`), và phiếu email tạo qua `_create_reference_document` (`receive.py:716`). Cần loại bằng cách chỉ xét khi phiếu đã có Communication `Sent` hoặc đã có comment bot (xem `has_agent_replied`, `T:398-406`).
- `on_update` bắn nhiều lần cho cùng Communication: cần khoá idempotent (ví dụ theo `communication.name`).
- Phiếu đã gộp: `T:1063-1068` chuyển Communication sang phiếu đích; hook phải đọc `reference_name` sau khi `db_set`, dùng `on_update` cuối cùng.
- Trả lời qua email phụ thuộc một Email Account nhận (IMAP/POP) có `append_to="HD Ticket"` và job kéo thư chạy: UNVERIFIED trên site (mục 5).
- Người tạo trả lời không bật được bot qua `handlers.py:111-112` (A5-4b), nên đường này mới cần hook mới.

## 5. UNVERIFIED (cần kiểm trên site/production/trình duyệt)
| # | Việc | Cách kiểm |
|---|---|---|
| U-1 | Site `miyano` có Email Account gửi đi và `default_outgoing=1` | `bench --site miyano console`: `frappe.get_all("Email Account", filters={"enable_outgoing": 1}, fields=["name","default_outgoing","email_id"])`; production: Desk > Email Account |
| U-2 | `ai.agent` hiện có `write` HD Ticket, `restrict_tickets_by_agent_group` | `frappe.db.get_single_value("HD Settings","restrict_tickets_by_agent_group")`; `frappe.has_permission("HD Ticket","write",doc=<ticket>,user="ai.agent@miyano.com.vn")` |
| U-3 | Giá trị `HD Settings` thật: `skip_email_workflow`, `enable_reply_email_via_agent`, `instantly_send_email` | `frappe.db.get_single_value("HD Settings", <field>)` (mặc định trong JSON là 0/1/0) |
| U-4 | Cổng khách hiện đúng Communication `Sent` của bot với người tạo thật | Trong trình duyệt, đăng nhập user HD Customer, mở `/helpdesk/my-tickets/<ID>` sau khi gọi `reply_via_agent` trên phiếu thử |
| U-5 | Thư trả lời thật quay về và gắn đúng phiếu (IMAP có `append_to=HD Ticket`, job kéo thư chạy) | Production: gửi thư trả lời vào hộp hỗ trợ, đối chiếu `Communication.reference_name` |
| U-6 | `reply_via_agent` khi `to` rỗng | Test trên site thử khác `miyano` |
| U-7 | Thực tế `first_responded_on` được ghi khi gọi `reply_via_agent` dưới `ai.agent` (không phải chỉ đọc mã) | Phiếu thử: gọi, sau đó `frappe.db.get_value("HD Ticket", ID, "first_responded_on")` |

## Tuyên bố ngược nhau (docs với mã)
Không thấy mâu thuẫn. Tài liệu Helpdesk chỉ mô tả mức giao diện ("Reply" gửi email, cần tài khoản mặc định gửi đi); chi tiết trên lấy từ mã và gắn nhãn bằng `path:line`.

## Sources
1. Helpdesk, Email Communication: https://docs.frappe.io/helpdesk/email-communication, truy cập 2026-11-14. Nói: cần ít nhất một tài khoản email gửi đi mặc định và một tài khoản nhận mặc định; agent bấm Reply để gửi email tới người nhận. Không nói cơ chế gắn thư trả lời vào phiếu (nên (d) lấy từ mã).
2. Helpdesk, Settings (qua kết quả tìm kiếm, chưa mở trang): https://docs.frappe.io/helpdesk/settings, truy cập 2026-11-14. Mô tả Enable Outgoing và Default Outgoing; UNVERIFIED chi tiết vì chưa đọc trang.
3. Mã cài trên bench: Helpdesk 15.1.0 (`/home/miyano/frappe-bench/apps/helpdesk/`), Frappe 15.126.1 (`/home/miyano/frappe-bench/apps/frappe/`), các dòng ghi trong thân.
4. Hai URL docs thử mở ra 404 và không dùng: `https://docs.frappe.io/helpdesk/email-setup`, `https://docs.frappe.io/framework/user/en/api/communication`.
