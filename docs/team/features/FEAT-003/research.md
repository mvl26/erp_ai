Feature: FEAT-003
Stage: research
Author-agent: researcher
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Research FEAT-003 (phần 2) — Khu vực "Hướng giải quyết & trao đổi với bot" trên trang phiếu agent Helpdesk, không sửa Helpdesk/Frappe (RQ-1..RQ-8)

## Câu trả lời ngắn
P1 (tab thật cạnh Activity/Emails/Comments) **không làm được** nếu không sửa Helpdesk. Danh sách tab là một `computed` viết cứng, không có slot hay registry nào. `setupForm` chỉ nhận `doc, call, router, toast, $dialog, updateField, createToast`, và trang agent chỉ đọc khóa `actions` từ giá trị trả về. Phương án khả thi đầu tiên là **P2**. Script thêm một nút action vào header bằng điểm mở rộng có tài liệu. Bấm nút (1 lần) mở một ngăn do `erp_ai` dựng bằng DOM an toàn và gắn vào `document.body`, không gắn vào cây DOM do Vue quản lý. Đọc và gửi đi qua 2 method whitelisted mới của `erp_ai`: một GET trả dữ liệu đã đổi sang chữ thường, một POST gọi lại `HD Ticket.new_comment`. Như vậy comment vẫn là core `Comment` do chính người gửi làm chủ, và hook `comment_after_insert` của FEAT-001 chạy y như khi gõ ở ô Comments. Cập nhật trực tiếp dựa vào `docinfo_update` và `doc_update` mà Frappe đã đẩy vào phòng `doc:HD Ticket/<id>`; không cần polling. Hướng này buộc architect sửa ADR-007 Quyết định 5–6. Độ tin cậy: **trung bình–cao**. Phần mã nguồn đã được đọc đúng phiên bản. Hành vi trên trình duyệt (DOM ngoài Vue, socket `__vue_app__`) chưa có POC, và được ghi `UNVERIFIED`.

## Phiên bản đang dùng
- Helpdesk @ 15.1.0, đọc từ `apps/helpdesk/helpdesk/__init__.py:1`; git `a185896` (tag `v15.1.0`, nhánh `version-15`).
- Frappe @ 15.126.1, đọc từ `apps/frappe/frappe/__init__.py:54`.
- frappe-ui trong bundle của Helpdesk: `apps/helpdesk/desk/node_modules/frappe-ui`. `@framework/ui` là symlink tới `apps/frappe/ui` (`desk/vite.config.js:97-99`). vue 3.5.31 (theo cache).
- Cache dùng lại: `docs/team/research/helpdesk-agent-live-indicator@15.1.0.md` (cùng phiên bản), `docs/team/features/FEAT-002/research.md`. Không đọc lại các ý đã có ở đó.
- Mã FEAT-002 hiện có: `erp_ai/public/js/agent_status_indicator.js` (195 dòng). Mã cài đặt đưa tệp này vào bản ghi HD Form Script `ERP AI Agent Status` (`erp_ai/install.py:20-23`, `:208-226`).

Các đường dẫn dưới đây tính từ `apps/helpdesk/desk/src` (SPA), `apps/helpdesk/helpdesk` (Python), `apps/frappe` và `apps/erp_ai/erp_ai`.

## Câu hỏi con và kết quả

### RQ-1. Thêm tab không sửa Helpdesk? `setupForm` có gì? DOM an toàn có chịu được việc Vue dựng lại không?
- **Tab viết cứng, không mở rộng được.** Tab là `computed` với 3 tab cố định, thêm Calls nếu bật gọi điện, rồi Analytics (`components/ticket-agent/TicketActivityPanel.vue:78-110`). Tab được render bằng `TabTrigger`/`TabPanel` của frappe-ui (dựa trên reka-ui Tabs) (`:11-36`). Không có slot, `provide` hay đọc cấu hình nào cho tab. Kết luận: P1 không khả thi.
- **Ngữ cảnh `setupForm` (desktop):** `{ doc: ticket.value.doc, call, router, toast, $dialog, updateField, createToast }` (`components/ticket-agent/TicketHeader.vue:318-326`). `call` là `call` của frappe-ui (`:107`). `updateField` gọi `setValue.submit` (`:185-191`). Script chạy bằng `new Function(script + "\nreturn setupForm")()`. Giá trị trả về chỉ được đọc ở `actions` và `onChange` (`composables/formCustomisation.ts:92-98`). Trên trang agent chỉ `actions` được dùng (`TicketHeader.vue:329-337`): action đơn render thành `Button` trên header (`:24-30`), action nhóm nằm trong dropdown (`:31-44`, `:107-117`). `onChange` chỉ được đọc ở `TicketNew.vue:262`; `applyFilters` chỉ có ở trang tạo phiếu (docs custom-actions). Không có socket trong ngữ cảnh (như cache).
- **Script chạy lại** mỗi khi `customizationCtx` đổi (`watchEffect`, `TicketHeader.vue:329-337`), tức là mỗi khi `doc` đổi. Toàn bộ trang phiếu được mount lại khi chuyển phiếu (`pages/ticket/TicketAgent.vue:2` `:key="ticketId"`), và bị ẩn hiện theo `feedReady` (`:2`, `:109-110`, `:184-190`).
- **Chèn DOM vào hàng tab** (một "tab giả" đặt trong `<div>` ở `TicketActivityPanel.vue:8-21`) có 3 vấn đề:
  1. Nút giả không thuộc nhóm `Tabs` của reka-ui. Nó không tắt được `TabPanel` đang mở, không vào được vòng focus bàn phím, nên phải tự che vùng panel.
  2. Nút sẽ mất mỗi lần `TicketAgent` mount lại, và phải dùng `MutationObserver` để gắn lại.
  3. Vue có giữ nguyên nút lạ trong một phần tử do nó quản lý khi patch hay không thì không có tài liệu: `UNVERIFIED`.
  Vì vậy không khuyến nghị.
- **Cách an toàn (P2):** dùng action trên header (có tài liệu: docs custom-actions, "A group lists its buttons under `options`") để mở một ngăn gắn vào `document.body`, `position: fixed`. FEAT-002 đã gắn chỉ báo theo đúng cách này (`agent_status_indicator.js:20-72`). Vue không bao giờ patch phần tử này. Script đóng ngăn khi rời phiếu (`router.afterEach`, như `agent_status_indicator.js:176-189`), và đổi nội dung khi `doc.name` đổi (`:157-160`). Mỗi lần `setupForm` chạy lại phải dùng lại cùng trạng thái trên `window`, để không đăng ký listener trùng (`:10-18`, `:163-165`). Hàm `onClick` của action phải đọc phiếu hiện tại từ trạng thái đó, không giữ `doc` cũ trong closure.

### RQ-2. Đọc 4 field AI và comment: có sẵn trong ngữ cảnh hay phải gọi server?
- `doc` có 4 field AI, vì role Agent đọc được permlevel 8 (`helpdesk/doctype/hd_ticket/hd_ticket.json:606-608`, ADR-006). Nhưng `doc` **không được nạp lại** khi bot ghi field trong worker. frappe-ui `createDocumentResource` (`composables/useTicket.ts:45-67`) không nghe `doc_update`: grep `doc_update` trong `node_modules/frappe-ui/src` không ra kết quả nào. Chỉ timeline nghe sự kiện này, và chỉ để nạp lại luồng hoạt động (`apps/frappe/ui/src/components/ActivityTimeline/liveUpdates.ts:88-92`). Muốn có AC-11 (e) thì phải đọc từ server.
- **Comment:** DocType `Comment` chỉ cấp quyền cho System Manager và Website Manager (`frappe/core/doctype/comment/comment.json:109-128`). Vì vậy Agent gọi `frappe.client.get_list("Comment")` sẽ bị từ chối. Helpdesk đọc comment qua `frappe.desk.form.activity.get_activity_timeline` (`apps/frappe/ui/src/components/ActivityTimeline/useActivityTimeline.ts:102`). Hàm này kiểm quyền đọc tài liệu (`frappe/desk/form/activity.py:26-33`) và trả `author.email` = `owner` (`:254-271`, `:331-337`, đúng D8), kèm `content` dạng HTML.
- Hai cách đọc ở bảng "Phương án — kênh dữ liệu" dưới đây. Cả hai đều phải gọi server, tức là trái ADR-007 Quyết định 5.

### RQ-3. Gửi tin: endpoint nào, CSRF, quyền, có kích hoạt `@ai` không? Từ khóa lấy ở đâu?
- **Ô Comments của Helpdesk** gọi `run_doc_method` với `dt="HD Ticket"`, `method="new_comment"`, `args={content, attachments}` (`components/CommentTextEditor.vue:216-223`). Phía server:
  - `frappe/handler.py:317-361`: `get_doc` → `doc.has_permission("read")` → `is_whitelisted` → gọi method.
  - `HD Ticket.new_comment` (`helpdesk/doctype/hd_ticket/hd_ticket.py:616-629`): kiểm `is_agent()`, gọi `self.add_comment("Comment", content)`, rồi chuyển tệp đính kèm sang comment.
  - `Document.add_comment` (`frappe/model/document.py:1608-1629`): tạo `Comment` với `comment_email = session.user`, `.insert(ignore_permissions=True)`. `owner = session.user` được đặt ở `document.py:716-727`.
  - Chốt của Helpdesk: `before_insert` chặn người không phải agent (`helpdesk/extends/comment.py:15-22`). `Comment.validate` chạy `sanitize_html` (`frappe/core/doctype/comment/comment.py:69-74`).
  - `doc_events["Comment"]["after_insert"]` = `erp_ai.handlers.comment_after_insert` (`erp_ai/hooks.py:148-150`, `erp_ai/handlers.py:100-120`). Đây là chính đường mà `post_comment` của bot đi qua (`erp_ai/agent/tools/write_ticket.py:73-83` → `new_comment`). FEAT-001 đã dựa vào việc hook này chạy trên đường đó (nhánh `written_by_agent`, `handlers.py:107`).
  - Kết luận: gọi `new_comment` dưới phiên của người sẽ tạo đúng 1 `Comment` có `owner` là người đó, và hook FEAT-001 chạy.
- **CSRF:** `call` của frappe-ui luôn gửi POST (`node_modules/frappe-ui/src/utils/call.ts:24-34`) và gắn header `X-Frappe-CSRF-Token` lấy từ `window.csrf_token` (`utils/frappeRequest.ts:117-118`). Trang `/helpdesk` đặt token này (`helpdesk/www/helpdesk/index.py:37`). Server kiểm token ở `frappe/auth.py:90-106`. Script không phải tự xử lý CSRF, miễn là gọi qua `call` của ngữ cảnh.
- **Từ khóa:** ERP AI Setting chỉ cấp quyền cho System Manager (`erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json:182`). Nhân viên không đọc được `trigger_keyword`, nên việc tự thêm từ khóa (B-6) phải làm ở server. Server dùng lại `policy.contains_keyword` (`erp_ai/agent/policy.py:41-45`).
- **`frappe.desk.form.utils.add_comment`** (`frappe/desk/form/utils.py:27-50`) cũng tạo Comment của người gửi. Nhưng nó bỏ qua `is_agent()` của `new_comment` (chỉ còn chốt `before_insert`), không chuyển tệp đính kèm, và bắt truyền `comment_email`/`comment_by` từ client. Không khuyến nghị.
- **Method `erp_ai` riêng (khuyến nghị S-B):** `@frappe.whitelist(methods=["POST"])` (dạng đã có ở `erp_ai_setting.py:125`) làm các bước sau:
  1. Kiểm chữ khác rỗng và độ dài tối đa (designer chọn số).
  2. Escape bằng `frappe.utils.escape_html` để `<`, `>`, `&` hiện đúng như người gõ (AC-9).
  3. Thêm từ khóa nếu chữ chưa chứa.
  4. Gọi `frappe.get_doc("HD Ticket", ticket)`, kiểm `has_permission("read")` như `run_doc_method`, rồi gọi `ticket.new_comment(content)`. Như vậy dùng lại chốt `is_agent()` và đi đúng đường hook.
  5. Có thể thêm `frappe.rate_limiter.rate_limit` (`frappe/rate_limiter.py:105-111`).
  Comment tạo ra giống comment của ô Comments, nên AC-10 "giống hệt" chỉ phụ thuộc vào nội dung.
- **Input cho architect (ADR-007):** Quyết định 5 phải cho phép script dùng tham số `call` của ngữ cảnh, chỉ để gọi đúng các method whitelisted của `erp_ai` có trong danh sách (đọc: GET; gửi: POST). Tiếp tục cấm `fetch`/`XMLHttpRequest`/`frappe.call`/`updateField`/`localStorage`. Ràng buộc "tham số `call` không được dùng" phải đổi thành "`call` chỉ được gọi với các chuỗi method trong danh sách". Quyết định 6: nội dung từ phiếu, comment hay model vẫn chỉ đi qua `textContent`; server đổi HTML sang chữ thường trước khi trả về (RQ-5). Ràng buộc mới cho mọi method mới: `is_agent()` + quyền đọc HD Ticket kiểm ở server (STD-SEC-4).

### RQ-4. Sự kiện realtime nào tới trang khi có comment mới hoặc field phiếu đổi? Có cần polling không?
- **Comment mới:** `Comment.after_insert` → `notify_change("add")` → `publish_realtime("docinfo_update", {doc, key: "comments", action: "add"}, doctype, docname, after_commit=True)` (`frappe/core/doctype/comment/comment.py:59-67`, `:85-103`). Sự kiện đi vào phòng `doc:` (`frappe/realtime.py:53-54`). `doc` trong payload là toàn bộ `as_dict()` của Comment: `owner`, `content` HTML, `comment_type`, `reference_name`.
- **Field phiếu đổi** (bot `set_resolution_hint` → `doc.save()`, `write_ticket.py:60-68`): `notify_update` phát `doc_update` vào phòng `doc:` sau commit, và `list_update` vào phòng DocType (`frappe/model/document.py:1370-1385`).
- Đây là cơ chế mà FEAT-002 AC-10 (h) dựa vào. Timeline của Helpdesk nghe `docinfo_update` và `doc_update` (`apps/frappe/ui/src/components/ActivityTimeline/liveUpdates.ts:106-111`, `components/ticket-agent/timeline/TicketTimeline.vue:509-510`). `helpdesk:ticket-update` và `ticket_update` (`TicketAgent.vue:219-230`) không tới được trên Frappe 15 (cache).
- **Phòng:** trang vào phòng qua `subscribeToDoc` (`apps/frappe/ui/src/socket.ts:48-74`). Khi người giữ cuối cùng nhả phòng thì trang gửi `doc_unsubscribe` (`:71-72`), ví dụ khi chuyển phiếu. Script FEAT-002 gọi `doc_subscribe` lại ở mỗi lần `setupForm` chạy, nên vẫn đúng phiếu (`agent_status_indicator.js:161`). Từ Helpdesk 15.1.0, chỉ agent vào được phòng HD Ticket (`helpdesk/overrides/realtime.py:6-23`, `helpdesk/hooks.py:126-129`, socket gọi `frappe.realtime.can_subscribe_doc` ở `apps/frappe/realtime/handlers/frappe_handlers.js:48-58`, `:167-170`). Như vậy câu "Hệ quả xấu" của ADR-008 về việc khách nhận payload đã không còn đúng; xem ghi chú cho architect.
- **Polling:** không cần. Thay vào đó: nạp lại khi mở ngăn; khi có `docinfo_update` mà `key === "comments"` và `reference_name` trùng phiếu đang xem; khi có `doc_update` của đúng phiếu; và khi socket `connect` lại sau một `disconnect`. Timeline của Helpdesk làm đúng như vậy (`liveUpdates.ts:94-104`). Script thêm listener bằng hàm có tên. Helpdesk gỡ `docinfo_update` kèm handler cụ thể (`TicketTimeline.vue:516-517`), nên không gỡ nhầm listener của `erp_ai`. Script không bao giờ `off` sự kiện của người khác. Mỗi sự kiện tốn 1 GET, chỉ khi ngăn đang mở. Không ghi DB, nên AC-14 vẫn đạt.

### RQ-5. Hiện HTML (comment bot, `ai_resolution_hint`) thành chữ thường an toàn
- Script không có sẵn bộ lọc HTML nào. `dompurify` chỉ được đóng gói bên trong bundle (`desk/vite.config.js:122-126`). `src/` không gán nó vào `window` (grep `window.DOMPurify` không ra kết quả). Việc không có đường nào khác để lấy nó trong runtime: `UNVERIFIED`.
- `DOMParser.parseFromString(..., "text/html")` cho ra tài liệu trơ: script không chạy, handler không chạy. Nhưng tài liệu đó "can download resources specified in `<iframe>` and `<img>`" (MDN). Nghĩa là dữ liệu gieo `<img src=x>` vẫn tạo request ra ngoài.
- Frappe có sẵn `frappe.core.utils.html_to_plain_text` (`frappe/core/utils.py:95-130`): BeautifulSoup bỏ `script`/`style`, đổi `br`/`p`/`div`/`li`/`h*` thành xuống dòng. Bên cạnh đó có `strip_html` (`frappe/utils/data.py:1532`) và `html2text` (markdown, `core/utils.py:90-92`).
- Khuyến nghị **T-A**: method đọc của server trả chữ thường đã qua `html_to_plain_text`; script gán bằng `textContent`, với CSS `white-space: pre-wrap`. Không có parser HTML nào trong trình duyệt, nên AC-12 kiểm được bằng test Python với dữ liệu gieo XSS.

### RQ-6. Trang khách; kiểm quyền cho đường server mới
- `get_form_script` lọc theo `apply_to_customer_portal == is_customer_portal` (`helpdesk/doctype/hd_form_script/hd_form_script.py:61-84`). Endpoint của trang agent không truyền cờ portal (`helpdesk/doctype/hd_ticket/api.py:392-397`), còn đường của khách thì có (`api.py:58`). Bản ghi có `apply_to_customer_portal=0` nên không về trang `/my-tickets` (như FEAT-002). Thêm vào đó, router đưa người không phải agent khỏi `TicketAgent` (`router/index.ts:234-238`).
- **Server (STD-SEC-4):** mỗi method mới gọi `helpdesk.utils.is_agent()` (`helpdesk/utils.py:42-57`; kiểm HD Agent `is_active`, hoặc role Agent/Agent Manager), rồi `frappe.has_permission("HD Ticket", "read", doc=ticket, throw=True)`. Helpdesk có sẵn một hàm làm đúng việc này: `helpdesk.extends.comment.can_see_ticket_comments` (`helpdesk/extends/comment.py:72-79`). Chỉ đọc bằng `frappe.get_doc` hoặc `get_activity_timeline` dưới phiên người dùng; không dùng `ignore_permissions`. Method gửi đi qua `new_comment`, nên có thêm chốt `is_agent()` của Helpdesk (`hd_ticket.py:618-621`, `extends/comment.py:15-22`).

### RQ-7. Một chỉ báo mỗi lần chạy
- Nếu có 2 bản ghi HD Form Script thì cả hai đều chạy (`formCustomisation.ts:52-59`), và mỗi bản ghi đăng ký `socket.on` riêng. Muốn chắc chỉ có một chỉ báo thì: **mở rộng đúng bản ghi và tệp của FEAT-002** (ADR-007 Quyết định 1: một kênh), hoặc gom thành 1 tệp nguồn; giữ một trạng thái chung `window.__erpAiAgentStatus` (`agent_status_indicator.js:10-18`); giữ **một** phần tử chỉ báo, `appendChild` vào ngăn khi ngăn mở và trả về `document.body` khi ngăn đóng. `appendChild` chuyển chỗ phần tử chứ không sao chép, nên cả trang chỉ có một chỉ báo. Tên sự kiện ADR-008 giữ nguyên.

### RQ-8. P3/P4 (chỉ khi cần)
- P3 không cần, vì P2 khả thi. Nếu sau này phải dùng: một trang `www` của `erp_ai` có `get_context` và `no_cache = 1` (docs portal-pages). Tài liệu không nói cách giới hạn theo role, nên trang tự `raise frappe.PermissionError` khi Guest hoặc `not is_agent()`, và kiểm quyền đọc phiếu. Trang này vẫn phải dùng lại đúng 2 method ở trên. Mở từ trang phiếu bằng action `onClick` → `window.open("/erp-ai-bot?ticket=…")`. Nhược điểm: phải dựng lại socket/realtime (trang `www` không có `$socket` của SPA, `UNVERIFIED`), và rời ngữ cảnh phiếu.
- P4 (Tab Break trên `/app/hd-ticket`) cần thêm Custom Field Tab Break vào HD Ticket. Việc này trái ràng buộc "không thêm field vào HD Ticket" của Amendment 1, và trái intake dòng 23. Loại.

### Bản di động (ngoài phạm vi, chỉ xác nhận)
- `MobileTicketAgent.vue` cũng gọi `setupCustomizations` với cùng ngữ cảnh (`pages/ticket/MobileTicketAgent.vue:367-379`), và dồn mọi action vào menu ba chấm (`:383-398`). Vậy action của P2 **sẽ hiện trên di động** nếu script không lọc. Bản di động được chọn khi `window.innerWidth < 640`, lúc router dựng route (`composables/screen.ts:23-24`, `router/index.ts:212-214`). Script nên trả `actions: []` khi `window.innerWidth < 640`, và ngăn tự đóng khi màn hình hẹp. Ngưỡng có thể lệch khi người đổi kích thước cửa sổ sau khi đã vào trang: `UNVERIFIED`, phải kiểm bằng bước tay AC-6.

## Phương án — vị trí (B-1)
| Phương án | Ưu | Nhược | Rủi ro | Chi phí |
|---|---|---|---|---|
| P1 tab thật trong `TicketActivityPanel` | Đúng ý người nhất | Không làm được nếu không sửa Helpdesk (`TicketActivityPanel.vue:78-110`) | — | Bị cấm (FEAT-002 Q1) |
| P1' "tab giả" chèn DOM vào hàng tab + `MutationObserver` | Trông như một tab | Không thuộc reka-ui Tabs; phải tự che panel; bị gỡ khi Vue mount lại; chạy trong cây DOM của Vue | Cao: hành vi patch của Vue không có tài liệu (`UNVERIFIED`); dễ vỡ ở mỗi lần nâng Helpdesk | Trung bình, khó test |
| **P2 nút action trên header (có tài liệu) → ngăn của `erp_ai` gắn vào `document.body`** | Điểm mở rộng có tài liệu; 1 lần bấm; Vue không đụng tới ngăn; cùng kiểu với chỉ báo FEAT-002 | Không nằm trong hàng tab; ngăn đè lên một phần trang; phải lọc trên di động | Thấp–trung bình: phụ thuộc ngữ cảnh `setupForm` và `$socket` (`UNVERIFIED`, như FEAT-002) | Thấp: 1 tệp JS + 2 method Python |
| P3 trang `www` riêng mở bằng action | Cách ly hoàn toàn khỏi SPA | Rời ngữ cảnh phiếu; phải tự dựng realtime; thêm route và kiểm quyền trang | Trung bình | Trung bình–cao |
| P4 Tab Break trên form Desk | Có sẵn trong Frappe | Cần field mới trên HD Ticket (trái ràng buộc); nhân viên ít dùng Desk | — | Loại |

## Phương án — kênh dữ liệu (đọc/gửi)
| Phương án | Ưu | Nhược | Rủi ro | Chi phí |
|---|---|---|---|---|
| R-A đọc bằng `get_activity_timeline` + gửi bằng `run_doc_method new_comment`, lọc B-5 và thêm từ khóa ở trình duyệt | Không có mã server mới | Từ khóa không đọc được ở client (Setting chỉ cho System Manager); HTML phải xử lý ở trình duyệt (không có bộ lọc, `<img>` vẫn tải); AC-8 và AC-12 chỉ kiểm được bằng tay (không có slot test JS) | Cao về AC-9 và AC-12 | Thấp về mã, cao về kiểm |
| **R-B 2 method `erp_ai`: GET đọc (4 field + luồng B-5, chữ thường) + POST gửi (kiểm, escape, thêm từ khóa, gọi `new_comment`)** | Kiểm quyền ở server (STD-SEC-4); B-5, B-6, AC-7..AC-10, AC-12, AC-13 test được bằng Python; không lộ cấu hình; cùng đường hook FEAT-001 | Phải sửa ADR-007 Quyết định 5; thêm bề mặt API cần test quyền | Thấp | Trung bình |
| R-C đọc bằng R-B, gửi bằng `run_doc_method` sau khi GET trả cả từ khóa | Không có method POST mới | Thêm từ khóa ở client, escape `<` ở client; AC-9 không test được bằng Python | Trung bình | Thấp |

## Khuyến nghị
Khuyến nghị **P2 + R-B + T-A**, gộp vào **đúng tệp và bản ghi HD Form Script của FEAT-002** (dùng chung trạng thái và một phần tử chỉ báo, RQ-7). Lý do: đây là phương án đầu tiên khả thi theo B-1. Mọi kiểm tra an toàn (quyền, từ khóa, escape, đổi sang chữ thường, lọc B-5) nằm ở Python và có test được. Tin gửi đi tạo đúng 1 core `Comment` qua `HD Ticket.new_comment` dưới phiên người dùng, nên ADR-004, D8 và mô hình thẩm quyền không đổi. Cập nhật trực tiếp chỉ nghe các sự kiện có sẵn của Frappe, không polling. Đây là quyết định kiến trúc, **chờ architect quyết**: phải sửa ADR-007 Quyết định 5–6 và có thể cả Ràng buộc của ADR-008 (một bên nghe thêm ở phía trang).

## POC (nếu có)
Không làm POC. Toàn bộ kết luận lấy từ việc đọc mã nguồn đúng phiên bản và tài liệu chính thức. Các điểm chỉ thấy được trên trình duyệt có ghi `UNVERIFIED` và chuyển thành bước tay AC-6, AC-11, AC-12. Không tạo worktree. Không đổi dữ liệu site `miyano`.

## Nháp ADR (nếu có)
- **Bối cảnh:** FEAT-003 phần 2 cần một khu vực trên trang phiếu agent, có đọc, gửi và cập nhật trực tiếp, mà không sửa Helpdesk. Tab viết cứng. ADR-007 Quyết định 5 cấm script gọi server, Quyết định 6 bắt hiện bằng `textContent`. Agent không đọc được `Comment` (DocType) hay ERP AI Setting.
- **Phương án:** P1' (tab giả), P2 (action + ngăn trên body), P3 (trang `www`); kênh R-A, R-B, R-C (bảng trên).
- **Khuyến nghị:** P2 + R-B + T-A. Sửa ADR-007:
  - (a) Quyết định 5: `call` của ngữ cảnh được dùng, chỉ với danh sách method của `erp_ai`. Ràng buộc kiểm bằng test Python đọc tệp JS: mọi chuỗi method trong `call(` thuộc danh sách.
  - (b) Quyết định 6 giữ nguyên `textContent`, thêm "server trả chữ thường (`html_to_plain_text`)".
  - (c) Ràng buộc mới: method whitelisted của `erp_ai` cho SPA kiểm `is_agent()` + quyền đọc HD Ticket, không `ignore_permissions` khi đọc. Gửi chỉ qua `HD Ticket.new_comment`, `methods=["POST"]`.
  - (d) Script vẫn là một bản ghi duy nhất (Quyết định 1). Script chỉ thêm `socket.on` bằng hàm có tên cho `docinfo_update`/`doc_update`/`connect`/`disconnect`, không bao giờ `off`.
  - (e) Ghi chú cho ADR-008: Helpdesk 15.1.0 chỉ cho agent vào phòng HD Ticket (`helpdesk/overrides/realtime.py:6-23`), nên dòng "Khách … tự gửi `doc_subscribe` vẫn nhận payload" có thể bỏ.
- **Hệ quả:** tốt: đúng B-11, test được ở server, không có field hay DocType mới. Xấu: thêm 2 endpoint phải giữ quyền; vẫn phụ thuộc ngữ cảnh `setupForm`, `__vue_app__.$socket` và ngưỡng 640 px của Helpdesk, nên phải chạy lại bước tay sau mỗi lần nâng Helpdesk; ngăn trên body không phải tab thật (ghi vào tài liệu người dùng).

## Độ tin cậy
Trung bình–cao. Mọi kết luận về luồng dữ liệu, quyền, hook và realtime được đọc trực tiếp từ mã của Helpdesk 15.1.0, Frappe 15.126.1 và `@framework/ui` đang cài. Các điểm `UNVERIFIED` (chưa có POC trên trình duyệt):
1. Lấy socket qua `#app.__vue_app__` (từ cache).
2. Vue giữ nguyên DOM lạ trong hàng tab (chỉ ảnh hưởng P1').
3. Không có `dompurify` nào ở runtime mà script dùng được.
4. Ngưỡng 640 px khi người đổi kích thước cửa sổ.
5. Từ khóa có ký tự `&`/`<` sau khi escape vẫn khớp `contains_keyword`.
6. P3: trang `www` không có socket của SPA.

## Sources
- https://docs.frappe.io/helpdesk/custom-actions — Helpdesk Custom Actions (ngữ cảnh `setupForm`, `actions`, "Apply to customer portal") (truy cập 2026-11-12)
- https://docs.frappe.io/framework/v15/user/en/api/realtime#available-rooms — Frappe v15 Realtime, "Available rooms", phòng `doc:{doctype}/{name}` (truy cập 2026-11-12)
- https://docs.frappe.io/framework/v15/user/en/api/rest — Frappe v15 REST API (session/cookie; method sửa DB dùng POST) (truy cập 2026-11-12)
- https://docs.frappe.io/framework/v15/user/en/portal-pages — Frappe v15 Portal Pages (`www`, `get_context`, `no_cache`) (truy cập 2026-11-12)
- https://developer.mozilla.org/en-US/docs/Web/API/DOMParser/parseFromString — MDN DOMParser.parseFromString (tài liệu trơ nhưng vẫn tải `<img>`/`<iframe>`) (truy cập 2026-11-12)
- Từ cache `docs/team/research/helpdesk-agent-live-indicator@15.1.0.md`: https://github.com/frappe/frappe/blob/version-15/realtime/index.js (truy cập 2026-11-12); https://github.com/frappe/frappe/pull/25592 (truy cập 2026-11-12); https://socket.io/docs/v4/rooms/#disconnection (truy cập 2026-11-12); https://vuejs.org/api/application.html#app-config-globalproperties (truy cập 2026-11-12)
- Mã nguồn đã cài (bằng chứng chính, file:line ở trên): `apps/helpdesk` @ v15.1.0 (a185896), `apps/frappe` @ 15.126.1, `apps/frappe/ui` (`@framework/ui`), `apps/helpdesk/desk/node_modules/frappe-ui` (đọc 2026-11-12)
