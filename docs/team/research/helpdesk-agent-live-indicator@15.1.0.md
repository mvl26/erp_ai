# Helpdesk @ 15.1.0 trên Frappe @ 15.126.1 — đưa mã giao diện + tín hiệu realtime lên trang phiếu agent (cache)

Ngày: 2026-11-12 · Phiên bản: helpdesk v15.1.0 (commit a185896), frappe 15.126.1 (version-15, 2e9ecdc03f), vue 3.5.31, frappe-ui 1.0.0-rc.1 · Nguồn gốc: FEAT-002 research.

- Frappe 15 KHÔNG nạp `apps/<app>/realtime/handlers.js`; chỉ v16/develop có bộ nạp này (PR frappe#25592). Vì vậy `helpdesk/realtime/handlers.js` (`view_ticket`, typing, `open_doc:` relay) không chạy trên v15. Chỉ báo "is typing" và `helpdesk:ticket-update` (phòng `open_doc:`) không tới trình duyệt.
- Mã giao diện của app khác lên trang phiếu agent mà không sửa Helpdesk: dùng bản ghi HD Form Script (`dt=HD Ticket`, `apply_to=Form`, `enabled=1`, `apply_to_customer_portal=0`). Script chạy bằng `new Function(script+"\nreturn setupForm")` ở phạm vi toàn cục, và `setupForm` bị gọi lại mỗi khi `doc` đổi. Ngữ cảnh: `doc, call, router, toast, $dialog, updateField, createToast`; không có socket.
- `app_include_js` (desk.html) và `web_include_js` (web.html) không chạy trên SPA `/helpdesk`.
- Socket của SPA: `document.querySelector("#app").__vue_app__.config.globalProperties.$socket`. `__vue_app__` không có trong tài liệu Vue, chỉ kiểm bằng mã.
- Phòng dùng được trên v15: `doc:HD Ticket/<tên>` qua `doc_subscribe` (kiểm quyền đọc). Trang agent đã vào sẵn qua frappe-ui. Vào lại khi `connect`, vì socket.io rời mọi phòng khi mất kết nối. Không `doc_unsubscribe`, vì Helpdesk cũng dùng phòng đó.
- Phát từ worker: `frappe.publish_realtime(event, message, room=get_doc_room(...), after_commit=False)`. Truyền `room` tường minh. `after_commit=True` bị xóa khi rollback.
- Dùng tên sự kiện riêng, vì Helpdesk gọi `$socket.off("<tên>")` không kèm handler.
- Test JS: Node 20 có `node --test` (Stable), nhưng profile không có slot `cmd.*` cho nó.

## Sources
- https://docs.frappe.io/helpdesk/custom-actions (truy cập 2026-11-12)
- https://docs.frappe.io/framework/v15/user/en/api/realtime#frappe-publish-realtime (truy cập 2026-11-12)
- https://docs.frappe.io/framework/v15/user/en/python-api/hooks (truy cập 2026-11-12)
- https://github.com/frappe/frappe/blob/version-15/realtime/index.js (truy cập 2026-11-12)
- https://github.com/frappe/frappe/blob/develop/realtime/index.js (truy cập 2026-11-12)
- https://github.com/frappe/frappe/pull/25592 (truy cập 2026-11-12)
- https://socket.io/docs/v4/rooms/#disconnection (truy cập 2026-11-12)
- https://vuejs.org/api/application.html#app-config-globalproperties (truy cập 2026-11-12)
- https://nodejs.org/docs/latest-v20.x/api/test.html#running-tests-from-the-command-line (truy cập 2026-11-12)
