# Helpdesk @ 15.1.0 trên Frappe @ 15.126.1 — khu vực riêng của app trên trang phiếu agent: vị trí, đọc/gửi comment, realtime, hiển thị an toàn (cache)

Ngày: 2026-11-12 · Phiên bản: helpdesk v15.1.0 (a185896), frappe 15.126.1, `@framework/ui` = `apps/frappe/ui`, frappe-ui trong `helpdesk/desk/node_modules` · Nguồn gốc: FEAT-003 research. Bổ sung cho `helpdesk-agent-live-indicator@15.1.0.md`.

- **Tab của trang phiếu agent viết cứng** (`desk/src/components/ticket-agent/TicketActivityPanel.vue:78-110`); không có slot hay registry. Không thêm được tab nếu không sửa Helpdesk.
- **Ngữ cảnh `setupForm` (desktop):** `doc, call, router, toast, $dialog, updateField, createToast` (`TicketHeader.vue:318-326`). Trang agent chỉ đọc `actions` từ giá trị trả về (`TicketHeader.vue:329-337`; `onChange` chỉ dùng ở `TicketNew.vue:262`). Script chạy lại mỗi khi `doc` đổi. Trang mount lại khi chuyển phiếu (`TicketAgent.vue:2` `:key`).
- **Bản di động** cũng chạy script, và dồn action vào menu ba chấm (`MobileTicketAgent.vue:367-398`). Ngưỡng di động: `innerWidth < 640` (`composables/screen.ts:23-24`).
- **Vị trí an toàn:** action trên header (có tài liệu) → ngăn của app gắn vào `document.body`. Không chèn vào cây DOM do Vue quản lý (`UNVERIFIED` nếu làm vậy).
- **`doc` của ngữ cảnh** có field permlevel 8 cho role Agent (`hd_ticket.json:606-608`), nhưng không nạp lại khi có `doc_update`: frappe-ui không nghe sự kiện này.
- **Agent không đọc được DocType `Comment`** (chỉ System Manager và Website Manager, `frappe/core/doctype/comment/comment.json:109-128`). Đường đọc có kiểm quyền: `frappe.desk.form.activity.get_activity_timeline` (`activity.py:26-64`; `author.email` = `owner`).
- **Gửi comment như ô Comments:** `run_doc_method` → `HD Ticket.new_comment` (`CommentTextEditor.vue:216-223`; `hd_ticket.py:616-629`, kiểm `is_agent()`) → `Document.add_comment` (insert `ignore_permissions`, `owner` = session user; `document.py:1608-1629`, `:716-727`). `Comment.validate` chạy `sanitize_html`. `doc_events` `Comment.after_insert` của app khác vẫn chạy.
- **CSRF:** `call` của frappe-ui = POST + `X-Frappe-CSRF-Token` từ `window.csrf_token` (`frappe-ui/src/utils/call.ts:24-34`, `frappeRequest.ts:117-118`); server kiểm ở `frappe/auth.py:90-106`.
- **Realtime khi có comment mới:** `docinfo_update` {doc, key:"comments", action:"add"} vào phòng `doc:`, `after_commit=True` (`comment.py:59-67`, `:85-103`). Khi field phiếu đổi qua `save()`: `doc_update` vào phòng `doc:` + `list_update` (`document.py:1370-1385`). Timeline của Helpdesk dùng đúng hai sự kiện này (`apps/frappe/ui/src/components/ActivityTimeline/liveUpdates.ts:106-111`). Không cần polling; nạp lại khi `connect` sau `disconnect`.
- **Phòng HD Ticket chỉ cho agent vào:** Helpdesk override `frappe.realtime.can_subscribe_doc` (`helpdesk/overrides/realtime.py:6-23`, `hooks.py:126-129`). `subscribeToDoc` gửi `doc_unsubscribe` khi người giữ cuối cùng nhả phòng (`apps/frappe/ui/src/socket.ts:66-73`).
- **Hiển thị:** script không có sẵn bộ lọc HTML (`dompurify` chỉ đóng gói trong bundle). `DOMParser` cho ra tài liệu trơ nhưng vẫn tải `<img>`/`<iframe>` (MDN). Đổi HTML sang chữ thường ở server bằng `frappe.core.utils.html_to_plain_text` (`frappe/core/utils.py:95-130`, giữ ngắt dòng), rồi gán bằng `textContent`.
- **Từ khóa của app trong ERP AI Setting:** chỉ System Manager đọc được, nên việc thêm từ khóa phải làm ở server.

## Sources
- https://docs.frappe.io/helpdesk/custom-actions (truy cập 2026-11-12)
- https://docs.frappe.io/framework/v15/user/en/api/realtime#available-rooms (truy cập 2026-11-12)
- https://docs.frappe.io/framework/v15/user/en/api/rest (truy cập 2026-11-12)
- https://docs.frappe.io/framework/v15/user/en/portal-pages (truy cập 2026-11-12)
- https://developer.mozilla.org/en-US/docs/Web/API/DOMParser/parseFromString (truy cập 2026-11-12)
