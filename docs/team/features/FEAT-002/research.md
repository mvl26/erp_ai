Feature: FEAT-002
Stage: research
Author-agent: researcher
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Research FEAT-002 — Hiện chỉ báo "Đang suy nghĩ… / Đang làm: <việc>…" trên trang phiếu agent Helpdesk 15.1.0 mà không sửa mã nguồn Helpdesk

Câu hỏi từ spec (mục "Chốt sau câu trả lời Q1", "Ảnh hưởng tới các artifact sau"):

| # | Câu hỏi con | Dạng câu trả lời |
|---|---|---|
| Q1 | Làm sao để mã giao diện do app `erp_ai` cung cấp chạy trên trang phiếu agent của Helpdesk 15.1.0 mà không sửa Helpdesk? | Có/không + các cách xếp hạng |
| Q2 | Worker phía server phát tín hiệu tới trang đang mở bằng cách nào? | API + phòng (room) + điều kiện |
| Q3 | Phía trang tự tắt sau 600 s, và không hiện lại khi tải lại trang, bằng cách nào? | Cơ chế |
| Q4 | Có test tự động được phần này không? | Phần test được / không test được, bằng lệnh nào |

## Câu trả lời ngắn
**Làm được, không cần sửa Helpdesk** → A-18 không kích hoạt. Cách khuyến nghị: app `erp_ai` cài một bản ghi **HD Form Script** (tính năng tùy biến chính thức của Helpdesk, chạy trên trang phiếu agent, không chạy trên trang khách) lúc `after_install`/`after_migrate`. Script lấy socket có sẵn của SPA, `doc_subscribe` vào phòng `doc:HD Ticket/<tên>` (Frappe tự kiểm quyền đọc), nghe một sự kiện riêng `erp_ai:agent_status`. Worker phát bằng `frappe.publish_realtime(..., room="doc:HD Ticket/<tên>")`. Trạng thái chỉ nằm trong bộ nhớ trang, kèm hẹn giờ 600 s, nên tự mất và không hiện lại khi tải lại trang. Phía server test tự động đầy đủ bằng `cmd.test_one`. Phía trang chỉ test tự động được nếu team-leader thêm một slot `cmd.*` cho `node --test`; nếu không thì AC-10/AC-11 là bước tay như spec đã định.
Độ tin cậy: **trung bình–cao**. Cơ chế nạp script, phòng realtime và đường phát đều đã đọc trong mã của đúng phiên bản đang cài và trong tài liệu chính thức. Riêng cách lấy socket qua `#app.__vue_app__` là chi tiết nội bộ của Vue, tài liệu không nêu (`UNVERIFIED` theo docs, đã kiểm trong mã và bundle đang chạy). Chưa chạy thử trên trình duyệt (`ui: false`, không có Playwright).

**Phát hiện trái với spec (cần analyst/designer biết):** Helpdesk 15.1.0 có `helpdesk/realtime/handlers.js` (`view_ticket`, `helpdesk_ticket_typing`…), nhưng Frappe 15 **không nạp** handler realtime của app khác. Chỉ Frappe v16/develop mới có bộ nạp đó. Trên bench này `realtime/index.js` chỉ `require("./handlers/frappe_handlers")` (`apps/frappe/realtime/index.js:28-31`). Hệ quả: phòng `open_doc:HD Ticket/<tên>` không có trang nào vào. Chỉ báo "is typing" có sẵn và sự kiện `helpdesk:ticket-update` (`hd_ticket.py:73-77`, phát vào `open_doc:`, `helpdesk/utils.py:94-95`) **không tới trình duyệt** trên `miyano`. Các dòng "Đã có câu trả lời sẵn" của Amendment 1 về chỉ báo đang gõ và tự tải lại trang vì thế sai với bench này. Phương án a cũ cũng sẽ không chạy. Thiết kế dưới đây **không** dựa vào handler của Helpdesk.

## Phiên bản đang dùng
- Helpdesk @ **15.1.0** (từ `apps/helpdesk/helpdesk/__init__.py`: `__version__ = "15.1.0"`; git tag `v15.1.0`, commit `a185896`). SPA: `frappe-ui` 1.0.0-rc.1, `vue` ^3.5.14 (`apps/helpdesk/desk/package.json`), bản cài `vue` 3.5.31 (`desk/node_modules/vue/package.json`). Bundle đang phục vụ: `/assets/helpdesk/desk/assets/index-DNFwSy2e.js` (`helpdesk/www/helpdesk/index.html:201`).
- Frappe @ **15.126.1** (từ `apps/frappe/frappe/__init__.py`; nhánh `version-15`, commit `2e9ecdc03f`).
- Node @ v20.20.2 (`/home/miyano/frappe-bench/Procfile` dòng 9: `socketio: …/node/v20.20.2/bin/node apps/frappe/socketio.js`).
- Cache cũ `docs/team/research/helpdesk-ticket-fields@15.1.0.md` cùng phiên bản nhưng khác chủ đề (hiện/ẩn trường), không dùng lại.

## Bằng chứng theo câu hỏi

### Q1 — Đưa mã giao diện lên trang phiếu agent
1. **HD Form Script là điểm mở rộng chính thức.** Docs Helpdesk: script được áp cho "Agent's Ticket View" khi không chọn tùy chọn khác; "Apply to customer portal: Script will be applied to Ticket View of Customer" (docs.frappe.io/helpdesk/custom-actions, truy cập 2026-11-12). Mã 15.1.0:
   - Server trả script cho trang agent: `get_ticket_customizations()` → `get_form_script("HD Ticket")`, mặc định `is_customer_portal=False` (`helpdesk/helpdesk/doctype/hd_ticket/api.py:392-397`). Truy vấn lọc `enabled=1`, `apply_to="Form"`, `apply_on_new_page=0`, `apply_to_customer_portal=0` (`hd_form_script.py:61-84`).
   - Trang khách nhận script theo `is_customer_portal=not fields.is_agent` (`hd_ticket/api.py:58-60`). Một bản ghi có `apply_to_customer_portal=0` **không** chạy ở trang khách, đúng A-13.
   - SPA chạy script bằng `new Function(script + "\nreturn setupForm")()`, rồi `await scriptFn(obj)` (`desk/src/composables/formCustomisation.ts:92-99`). Hàm chạy ở phạm vi toàn cục, nên dùng được `window` và `document`.
   - Ngữ cảnh truyền vào: `doc, call, router, toast, $dialog, updateField, createToast` (`components/ticket-agent/TicketHeader.vue:318-326`; docs custom-actions liệt kê cùng tập). Không có socket.
   - `setupForm` được gọi lại trong `watchEffect` mỗi khi `doc` đổi (`TicketHeader.vue:329-338`). Script phải chạy lặp mà không đăng ký trùng, ví dụ dùng một cờ trên `window`.
   - Trang agent mobile cũng chạy script (`pages/ticket/MobileTicketAgent.vue:378`). A-19 không bắt buộc mobile; nếu chỉ báo dùng phần tử nổi gắn vào `body` thì mobile có luôn, không thêm việc.
2. **Đường lấy socket của SPA.** `main.js:100-103`: `app.config.globalProperties.$socket = socket; app.mount("#app")`. Vue gán `rootContainer.__vue_app__ = app` vô điều kiện khi mount (`desk/node_modules/@vue/runtime-core/dist/runtime-core.cjs.prod.js:3232`). Bundle production đang chạy có cả `d.__vue_app__=c` lẫn `$socket=`.
   - Vậy script đọc được `document.querySelector("#app").__vue_app__.config.globalProperties.$socket`. `globalProperties` là API công khai (vuejs.org, truy cập 2026-11-12). Riêng `__vue_app__` thì tài liệu Vue không nêu: `UNVERIFIED` theo docs, đã kiểm trong mã.
   - Rủi ro: Helpdesk đổi tên `$socket` khi nâng cấp. Script phải tự tắt êm khi không tìm thấy socket (AC-10 (g): không lỗi console mới).
3. **Các đường khác đã loại:**
   - `app_include_js` chỉ chèn vào `desk.html` (Desk `/app`), và `web_include_js` chỉ chèn vào `web.html` (docs hooks v15, truy cập 2026-11-12). SPA `/helpdesk` là `index.html` riêng, không kế thừa hai template đó (`helpdesk/www/helpdesk/index.html:1-219`). Loại.
   - Ghi đè trang `www/helpdesk` trong `erp_ai`: phải chép `index.html` có tên tài sản băm (`index-DNFwSy2e.js`), nên vỡ ở mỗi lần build Helpdesk. Thực chất là fork Helpdesk. Loại.
   - Hook `after_request` sửa HTML trả về `/helpdesk` để chèn `<script>`: hook có thật (`frappe/app.py:206-211`), nhưng tài liệu không cam kết việc sửa thân phản hồi HTML (`UNVERIFIED`). Script sẽ chạy trên mọi trang Helpdesk, kể cả trang khách, nên phải tự lọc. Giữ làm phương án dự phòng (D3).

### Q2 — Worker phát tín hiệu tới trang đang mở
- API: `publish_realtime(event=None, message=None, room=None, user=None, doctype=None, docname=None, task_id=None, after_commit=False)` (`apps/frappe/frappe/realtime.py:23-41`; github frappe version-15 cùng nội dung; docs v15 Realtime chỉ có ví dụ `frappe.publish_realtime('event_name', data={...})`, truy cập 2026-11-12).
  - Với `after_commit=False`, hàm gọi `emit_via_redis` ngay: publish lên kênh redis `events` (`realtime.py:83`, `:100-115`). Tiến trình socketio đọc kênh này rồi `io.of("/"+site).to(room).emit(...)` (`apps/frappe/realtime/index.js:44-57`). Vì vậy phát từ worker RQ chạy được, không cần request HTTP.
- **Phòng nên dùng: `doc:HD Ticket/<tên>`.** Docs v15, bảng "Available rooms": `doc:{doctype}/{name}` — "Only users with document permission may join". Client vào phòng bằng `socket.emit("doc_subscribe", doctype, docname)`; server kiểm `can_subscribe_doc` → `frappe.has_permission(doctype, doc=docname, throw=True)` rồi mới `join` (`frappe/realtime/handlers/frappe_handlers.js:48-58`, `frappe/realtime.py:118-121`).
  - Trang phiếu agent đã vào phòng này sẵn: bundle frappe-ui đếm người giữ (`holders`) rồi `emit("doc_subscribe",…)`, và vào lại khi `connect` (chunk `useActiveTabManager-kO4BfM4A.js`). Đó là đường `docinfo_update` làm comment mới hiện ngay (`TicketTimeline.vue:509-510`).
  - Script vẫn nên tự `doc_subscribe` mỗi lần `setupForm` chạy và mỗi khi `connect`. Lý do: "Upon disconnection, sockets leave all the channels they were part of automatically" (socket.io/docs/v4/rooms/#disconnection, truy cập 2026-11-12).
  - **Không** được `doc_unsubscribe`. Phòng tính theo socket, không đếm người giữ, nên rời phòng sẽ cắt luôn `docinfo_update` của Helpdesk. Sự kiện của phiếu khác thì lọc bằng `ticket_id`.
- Không dùng `open_doc:` (không ai vào trên Frappe 15, xem phát hiện ở trên). Không dùng phòng `all` vì phát tới mọi System User.
- **Luôn truyền `room=` tường minh** (dùng `frappe.realtime.get_doc_room("HD Ticket", name)`). Nếu không có `room` mà `frappe.local.task_id` tồn tại thì tín hiệu bị chuyển sang phòng task (`realtime.py:45-63`). Trên v15 job RQ không đặt `task_id`, chỉ đặt `frappe.local.job` (`utils/background_jobs.py:212`), nhưng truyền tường minh thì khỏi phụ thuộc.
- **Dùng `after_commit=False` cho mọi tín hiệu.** Với `after_commit=True`, tín hiệu nằm chờ commit và bị xóa khi rollback (`realtime.py:73-81`, `:95-97`). Nhánh lỗi sẽ mất tín hiệu kết thúc, trái AC-4. Runner đã tự commit ở `runner.py:68` và `:236`. Designer đặt tín hiệu kết thúc sau commit của câu trả lời, để chỉ báo không tắt trước khi comment hiện (NFR-5).
- `emit_via_redis` tự nuốt `redis.ConnectionError` (`realtime.py:108`). Lỗi kết nối redis vì thế không ném ra; các lỗi khác vẫn có thể ném, nên vẫn cần bọc theo AC-7.
- Tên sự kiện phải riêng (đề xuất `erp_ai:agent_status`). Lý do: Helpdesk gọi `$socket.off("<tên>")` không kèm handler, gỡ mọi listener của tên đó (`composables/realtime.ts:137-138`, `TicketTimeline.vue:515`). Dùng tên riêng thì không bị gỡ nhầm.
- Payload (NFR-4'): `{ticket_id, run_id, agent_user, agent_name, state: "thinking"|"working"|"done", text}`. Phòng `doc:` cho mọi người có quyền đọc phiếu vào được, kể cả khách là chủ phiếu nếu họ tự gửi `doc_subscribe` bằng tay. Trang khách không chạy script nên không hiện gì, nhưng payload vẫn có thể tới socket của họ. Vì vậy payload chỉ được mang đúng các mục NFR-4' cho phép.

### Q3 — Tự tắt sau 600 s, không hiện lại khi tải lại trang
- Trạng thái chỉ nằm trong bộ nhớ của script (một đối tượng trên `window`), không ghi `localStorage`, không ghi server.
  - Nhận `thinking`/`working` → hiện và (đặt lại) hẹn giờ `setTimeout` 600 000 ms tính từ tín hiệu bắt đầu của `run_id` đó. Nhận `done` cùng `run_id` → ẩn ngay và xóa hẹn giờ. Hết hẹn giờ → ẩn (AC-11).
  - Tải lại trang làm mất bộ nhớ JS, nên chỉ báo không hiện lại. Tín hiệu cũ không phát lại, vì socket.io không lưu sự kiện cho người vào sau (socketio chỉ `emit` tới người đang trong phòng, `realtime/index.js:44-57`).
  - Người mở trang giữa chừng thấy chỉ báo từ tín hiệu kế tiếp, đúng A-12.
- Số 600 nên được server gửi kèm trong payload (`expires_in_s = JOB_TIMEOUT_S`, `constants.py:24`) thay vì viết cứng trong JS, để một nguồn duy nhất (STD-DESIGN-7).
- Đổi phiếu trong SPA: `router` có trong ngữ cảnh (`TicketHeader.vue:321`). Script ẩn chỉ báo khi `doc.name` đổi ở lần `setupForm` kế tiếp, hoặc qua `router.afterEach`, nên không để chỉ báo của phiếu A hiện trên phiếu B.
- Hiển thị: tạo phần tử bằng `document.createElement` và gán chữ bằng `textContent`, không dùng `innerHTML` → AC-10 (f), STD-SEC-3. Phần tử nổi gắn vào `document.body` thì không phụ thuộc cấu trúc DOM của Helpdesk. Vị trí và kiểu dáng do designer quyết (A-20).

### Q4 — Test tự động
| Phần | Test được? | Cách |
|---|---|---|
| Runner phát tín hiệu (AC-2, AC-4, AC-5, AC-7, AC-9, NFR-4') | Có | `cmd.test_one`: `unittest.mock.patch` `frappe.publish_realtime` tại module phát (hoặc một hàm bọc `emit_status`), ghi lại chuỗi `(event, message, room)`; kiểm thứ tự, `room == "doc:HD Ticket/<tên>"`, khóa payload đúng danh sách cho phép, chuỗi đánh dấu trong tham số tool không xuất hiện. Không cần redis/socketio. |
| Bản ghi HD Form Script được cài | Có | `cmd.test_one`: sau `ensure_setup()` có đúng 1 bản ghi tên cố định, `dt="HD Ticket"`, `apply_to="Form"`, `enabled=1`, `apply_to_customer_portal=0`, `apply_on_new_page=0`, `script` = nội dung tệp `.js` trong app. Gọi `ensure_setup()` lần hai không nhân bản. |
| Script không dùng `innerHTML`, có kiểm `$socket` vắng | Một phần | Test Python đọc tệp `.js`, kiểm chuỗi tĩnh. Rẻ nhưng yếu. |
| Logic phía trang: lọc `ticket_id`, đổi trạng thái, `done` ẩn, hẹn giờ 600 s, đổi phiếu (AC-11) | Chỉ khi có slot mới | Node 20 có test runner ổn định: "Stability: 2 - Stable", chạy bằng `node --test` (nodejs.org v20 test.html, truy cập 2026-11-12). Viết script sao cho `setupForm` nhận được socket/đồng hồ/`document` giả, rồi nạp tệp bằng `vm` trong test. **Cần team-leader thêm slot `cmd.test_js` vào `.team/profile.json`**, vì researcher/dev chỉ chạy `cmd.*`. Không có slot thì không test tự động được. |
| Hiển thị thật trên trình duyệt (AC-10 a–g) | Không | `ui: false`, không có Playwright/Cypress trong profile. Bước tay như spec. |

## Phương án
Hai trục độc lập: **D** (cách đưa script lên trang) và **C** (kênh tín hiệu). Bảng cuối là phương án kiểm thử **J**.

| Phương án | Ưu | Nhược | Rủi ro | Chi phí |
|---|---|---|---|---|
| **D1** HD Form Script, bản ghi tên cố định, `ensure_setup()` (`after_install`/`after_migrate`) upsert từ tệp `erp_ai/public/js/<tên>.js` | Điểm mở rộng chính thức có docs; chỉ chạy trang agent (cờ portal = 0); JS là tệp thật nên `cmd.format`/`cmd.lint` chạy được; không sửa Helpdesk; mã cài đặt được phép theo ADR-004 "Ràng buộc" và ADR-006 | Bản ghi nằm trong DB: quản trị viên sửa tay thì lần migrate sau bị ghi đè, trái docstring "never overwrite" của `ensure_setup` (`install.py:31`); cần `before_uninstall` xóa bản ghi | Helpdesk đổi chữ ký `setupForm` hoặc bỏ HD Form Script ở bản sau | Thấp: ~1 hàm cài + 1 tệp JS |
| D2 Như D1 nhưng qua `fixtures` trong `hooks.py` | Cơ chế chuẩn ("records that are synced using JSON files", docs hooks v15) | Script nằm thành chuỗi trong JSON, không lint được như `.js`; xuất fixture ghi đè mỗi lần migrate | Như D1 | Thấp |
| D3 `after_request` chèn `<script src="/assets/erp_ai/…">` vào HTML `/helpdesk` | Tệp JS phục vụ như asset; không bản ghi DB | Tài liệu không cam kết sửa thân phản hồi (`UNVERIFIED`); chạy trên mọi trang Helpdesk kể cả khách, phải tự lọc vai trò; chạm mọi request | Vỡ khi Frappe đổi luồng phản hồi; lộ script cho khách | Trung bình |
| **C1** Socket của SPA qua `#app.__vue_app__.config.globalProperties.$socket`; `doc_subscribe` phòng `doc:HD Ticket/<tên>`; sự kiện riêng `erp_ai:agent_status`; server `publish_realtime(room=…, after_commit=False)` | Đẩy ngay (đạt NFR-5); không thêm request; dùng phòng có kiểm quyền của Frappe; vào lại khi `connect` | Phụ thuộc chi tiết nội bộ `__vue_app__` (`UNVERIFIED` theo docs) và tên `$socket` của Helpdesk | Nâng cấp Helpdesk đổi tên → chỉ báo im lặng (script phải tự tắt êm) | Thấp |
| C2 Polling: script gọi `call("erp_ai.….get_agent_status", {ticket})` mỗi ~3 s; server giữ trạng thái trong redis cache `frappe.cache.set_value(key, val, expires_in_sec=600)` (`utils/redis_wrapper.py:52`) | Chỉ API có tài liệu (`call` có trong docs custom-actions); TTL 600 s tự lo AC-11; người mở giữa chừng thấy ngay (tốt hơn A-12) | ~20 request/phút cho mỗi tab phiếu agent đang mở, kể cả khi không có lần chạy; thêm endpoint whitelisted (phải kiểm quyền, STD-SEC-4); ghi redis lúc chạy (architect xét có tính là "ghi" theo A-14 không) | Tải server tăng theo số tab mở | Trung bình |
| C3 C1, khi không thấy `$socket` thì lùi về C2 | Bền khi Helpdesk đổi tên | Gộp mã và chi phí của cả hai | Như C2 khi lùi | Trung bình–cao |
| J1 Python test (server + bản ghi cài) + bước tay AC-10/AC-11 | Không cần slot mới; đủ cho AC-2..AC-9 | AC-11 chỉ kiểm tay | Lỗi logic JS chỉ lộ ở bước tay | Thấp |
| J2 J1 + `node --test` cho logic JS, slot `cmd.test_js` mới | Có test tự động cho AC-11 và lọc phiếu (spec mong muốn) | Thêm slot profile, thêm quy ước đặt tên test JS (profile chỉ có `test_{name}.py`), JS phải viết dạng nạp được bằng `vm` | Thấp | Thấp–trung bình; cần team-leader sửa profile |

## Khuyến nghị
**D1 + C1 + J2 (lùi về J1 nếu team-leader không thêm slot).** Đang chờ architect quyết.
- D1: là điểm mở rộng chính thức, có docs, đã giới hạn sẵn trang agent. Việc ghi đè bản ghi lúc migrate là đúng chủ ý (app sở hữu bản ghi này). Architect cần ghi rõ ngoại lệ so với docstring `ensure_setup`, và xác nhận bản ghi cài đặt không thuộc bảng chủ ghi lúc chạy của ADR-004 (spec "Ràng buộc mới").
- C1: đạt NFR-5 không tốn request nền. Rủi ro `__vue_app__` được khoanh lại bằng: kiểm tồn tại rồi tự tắt êm; bước tay AC-10 (g); và một dòng trong As-Built "kiểm lại sau mỗi lần nâng Helpdesk".
- J2: là cách duy nhất có test tự động cho AC-11, như spec mong muốn ("nếu researcher tìm được cách").
- Cách nào cũng phải có: tên sự kiện riêng; `room` tường minh; `after_commit=False`; không `doc_unsubscribe`; `textContent`; chống đăng ký trùng khi `setupForm` chạy lặp; `before_uninstall` xóa bản ghi.

## POC (nếu có)
Không làm POC. Tài liệu và mã của đúng phiên bản đang cài trả lời được Q1–Q4. Phần duy nhất chưa kiểm khi chạy là hiển thị trên trình duyệt. POC không kiểm được phần đó: `ui: false`, không có công cụ trình duyệt, và researcher chỉ chạy được `cmd.*`. Bước tay AC-10 là nơi kiểm. Không tạo worktree.

## Nháp ADR (nếu có)
*(Không đánh số; architect đánh số.)*
- **Bối cảnh:** FEAT-002 (Q1 = b) cần chỉ báo trạng thái trực tiếp bằng tiếng Việt trên trang phiếu agent Helpdesk 15.1.0. Mã giao diện nằm trong `erp_ai`; không sửa Helpdesk; không ghi bản ghi nghiệp vụ lúc chạy (A-14). Đây là lớp giao diện đầu tiên của app. Frappe 15 không nạp handler realtime của Helpdesk, nên không dùng được các sự kiện/phòng `open_doc:` của Helpdesk.
- **Phương án:** D1/D2/D3 × C1/C2/C3 như bảng trên.
- **Khuyến nghị:** D1 + C1.
  - Lớp giao diện của `erp_ai` trên Helpdesk chỉ đi qua một bản ghi HD Form Script do app sở hữu. Bản ghi được cài/cập nhật bởi mã cài đặt và gỡ khi uninstall.
  - Kênh tín hiệu là `frappe.publish_realtime` vào `doc:HD Ticket/<tên>`, với `after_commit=False` và sự kiện `erp_ai:agent_status`.
  - Script không đọc hay ghi dữ liệu nào ngoài việc nghe sự kiện này.
- **Hệ quả:**
  - (+) Không fork Helpdesk; không thêm request nền; chỉ báo không để lại bản ghi.
  - (−) Phụ thuộc `HD Form Script`/`setupForm` và `$socket` của Helpdesk, nên mỗi lần nâng Helpdesk phải chạy lại bước tay AC-10.
  - (−) Bản ghi cài đặt bị ghi đè lúc migrate (có chủ ý).
  - (−) Thêm `javascript` vào `profile.language`. Nếu chọn J2, thêm slot `cmd.test_js`.
  - Khi lên Frappe v16, có thể xét chuyển sang handler realtime của app; ghi vào debt nếu cần.

## Sources
- https://docs.frappe.io/helpdesk/custom-actions — Helpdesk: Custom actions / HD Form Script, `setupForm` context, "Apply to customer portal" (truy cập 2026-11-12)
- https://docs.frappe.io/framework/v15/user/en/api/realtime#frappe-publish-realtime — Frappe v15 Realtime: `publish_realtime`, bảng "Available rooms" `doc:{doctype}/{name}` (truy cập 2026-11-12)
- https://docs.frappe.io/framework/v15/user/en/python-api/hooks — Frappe v15 hooks: `app_include_js` ("inject JS / CSS in `desk.html`"), `web_include_js`, `after_install`, `after_migrate`, `fixtures` (truy cập 2026-11-12)
- https://github.com/frappe/frappe/blob/version-15/frappe/realtime.py — chữ ký đầy đủ `publish_realtime`, `after_commit` (truy cập 2026-11-12; trùng `apps/frappe/frappe/realtime.py:23-121` bản 15.126.1)
- https://github.com/frappe/frappe/blob/version-15/realtime/handlers/frappe_handlers.js — `doc_subscribe` + `can_subscribe_doc` (truy cập 2026-11-12)
- https://github.com/frappe/frappe/blob/version-15/realtime/index.js — v15 chỉ nạp `frappe_handlers` (truy cập 2026-11-12)
- https://github.com/frappe/frappe/blob/develop/realtime/index.js — develop/v16 nạp `../../${app}/realtime/handlers.js` (truy cập 2026-11-12)
- https://github.com/frappe/frappe/pull/25592 — "feat: Extensible SocketIO", nguồn gốc bộ nạp handler của app (truy cập 2026-11-12)
- https://github.com/frappe/helpdesk/pull/2537 — Helpdesk thêm `realtime/handlers.js` (viewers/typing) (truy cập 2026-11-12)
- https://socket.io/docs/v4/rooms/#disconnection — "Upon disconnection, sockets leave all the channels they were part of automatically" (truy cập 2026-11-12)
- https://vuejs.org/api/application.html#app-config-globalproperties — `app.config.globalProperties` (truy cập 2026-11-12)
- https://nodejs.org/docs/latest-v20.x/api/test.html#running-tests-from-the-command-line — Node 20 test runner, "Stability: 2 - Stable", `node --test` (truy cập 2026-11-12)
- Mã đã đọc tại chỗ (cùng phiên bản đang cài, 2026-11-12): `apps/helpdesk/desk/src/composables/formCustomisation.ts:92-99`; `components/ticket-agent/TicketHeader.vue:318-338`; `helpdesk/helpdesk/doctype/hd_form_script/hd_form_script.py:61-84`; `helpdesk/helpdesk/doctype/hd_ticket/api.py:58-60,392-397`; `desk/src/main.js:100-103`; `desk/node_modules/@vue/runtime-core/dist/runtime-core.cjs.prod.js:3232`; `sites/assets/helpdesk/desk/assets/index-DNFwSy2e.js`, `useActiveTabManager-kO4BfM4A.js`; `desk/src/composables/realtime.ts:137-138`; `helpdesk/utils.py:94-95`; `apps/frappe/realtime/index.js:28-57`; `apps/frappe/frappe/app.py:206-211`; `apps/frappe/frappe/utils/background_jobs.py:212`.
- `UNVERIFIED`: (1) `rootContainer.__vue_app__` không có trong tài liệu Vue, chỉ kiểm bằng mã/bundle; (2) việc sửa thân HTML trong hook `after_request` (D3) không có trong tài liệu Frappe.
