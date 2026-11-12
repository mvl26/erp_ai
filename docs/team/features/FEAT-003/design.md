Feature: FEAT-003
Stage: design
Author-agent: designer
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Design FEAT-003 — Mô tả field cho 3 DocType ERP AI (phần 1) và khu vực "Hướng giải quyết & trao đổi với bot" trên trang phiếu (phần 2)

> **Lịch sử.**
> - 2026-11-12, bản đầu: designer báo hai DESIGN_CONFLICT. C-1: method đọc chỉ-GET không gọi được bằng `call` của frappe-ui (luôn POST). C-2: từ khóa có `<`, `>`, `&` không còn khớp `contains_keyword` sau khi `Comment.validate` sanitize.
> - 2026-11-12, bản sửa 1: architect chấp nhận cả hai đề xuất ở ADR-010 Amendment 1. Đã sửa: D-4, D-5 thành đã quyết; thêm D-9, D-10; sửa mục 1 (ADR), 3.1, 3.2, 5 (log), 7 (`policy.py`), 8 (AC-14, test từ khóa, luật tĩnh). Mỗi chỗ sửa có ghi *(Amendment 1)*, kèm nội dung bản trước khi có quyết định bị thay.

## 1. Bối cảnh
**Vấn đề (spec Mục tiêu, Amendment 1):**
- Phần 1: các field của `ERP AI Setting` (22 field hiển thị), `ERP AI Credential` (18), `ERP AI Log` (31) chưa có mô tả, chưa chia nhóm. Người quản trị phải đoán quy tắc (đơn vị, khoảng hợp lệ, ai ghi).
- Phần 2: nhân viên đang mở phiếu ở `/helpdesk/tickets/<id>` không có chỗ riêng để đọc hướng giải quyết AI, đọc các lần hỏi–đáp với bot và hỏi bot mà không phải nhớ từ khóa.

**Trong phạm vi:**
- Phần 1: thêm `description` cho 71/71 field hiển thị; thêm Section Break có label tiếng Việt (≥ 2 mỗi DocType). Không đổi thuộc tính nào khác (AC-5).
- Phần 2: phương án P2 của B-1 (ADR-009): action header "Trao đổi với bot" mở một ngăn trên `document.body` gồm 4 mục AI chỉ đọc, luồng B-5, dòng hướng dẫn B-8, ô gửi, chỉ báo FEAT-002. Hai method whitelisted ở server (ADR-010). Cập nhật trực tiếp qua `docinfo_update`/`doc_update`.

**Ngoài phạm vi (spec Amendment 1, dòng Out of scope):** bản di động; sửa mã Helpdesk/Frappe; tool L2/L3; sửa/xóa tin; đính kèm; nhắc tên; sửa hướng giải quyết; chi phí/ERP AI Log; báo lý do bot không trả lời; kênh riêng ngoài comment; trang khách; form Desk; report ERP AI Accuracy (A-1).

**ADR phải tuân (trích ID, không chép):**
- ADR-001 (module `ERP AI agent`, phân tầng; module ngăn có dòng `LAYER_RULES`).
- ADR-003 (handler xếp hàng sau commit; runner kiểm lại chốt) — không đổi.
- ADR-004 (bảng chủ ghi: comment của agent chỉ do `post_comment`) — không đổi, không nới.
- ADR-007 Quyết định 1–4 (một bản ghi HD Form Script, một tệp nguồn, chủ ghi là `install.py`, đặt lại khi migrate) — còn hiệu lực; Quyết định 5–6 được ADR-009 thay.
- ADR-008 (sự kiện `erp_ai:agent_status`, payload 7 khóa, phòng `doc:`) — không đổi phía phát.
- ADR-009 (kênh giao diện phần 2: ngăn P2, `call` chỉ tới allow-list, chỉ `textContent`, một chỉ báo, không polling, ẩn < 640 px). Quyết định 4 (chỉ `call`) giữ nguyên.
- ADR-010 kể cả Amendment 1 (module ngăn ở tầng Cửa vào, đúng 2 method, **cả hai `methods=["POST"]`**; đọc chỉ-đọc nhờ luật tĩnh và test, gồm `transaction_writes` không tăng; cổng `is_agent()` + quyền đọc phiếu; không `ignore_permissions`, không `set_user`; chữ thường ở server; gửi chỉ qua `HD Ticket.new_comment`, kiểm từ khóa trên dạng sẽ lưu trước khi gọi; không tự xét chốt agent). *(Amendment 1; bản trước: "trừ C-1, C-2".)*
- Giữ nguyên: ADR-002, ADR-005, ADR-006; mô hình thẩm quyền `ERP AI Instructor` (FEAT-001 AC-7, `erp_ai/agent/authority.py:45`); NFR-4 của FEAT-001; "khách không thấy dữ liệu AI". Không cần nới ADR nào trong số này.

**Cơ sở khảo sát (Explore E1, E2 + đọc trực tiếp, 2026-11-12, nhánh `team/BUG-002`):**
- `HD Ticket.new_comment(self, content: str, attachments: list[str] = [])` — `@frappe.whitelist()`, `apps/helpdesk/helpdesk/helpdesk/doctype/hd_ticket/hd_ticket.py:616-629`; kiểm `is_agent()` của phiên (`:618`, ném `frappe.PermissionError`), gọi `self.add_comment("Comment", content)` (`:622`) → `frappe/model/document.py:1608-1629` (`comment_email = frappe.session.user`, insert bên trong Frappe), trả `comment.name` (`:629`). **Không** kiểm quyền đọc phiếu → module ngăn phải tự kiểm trước.
- Ô Comments của Helpdesk gọi `run_doc_method` `new_comment` với HTML của TipTap (`apps/helpdesk/desk/src/components/CommentTextEditor.vue:217-223`).
- `Comment.validate` sanitize nội dung (`frappe/core/doctype/comment/comment.py:69-74`, `always_sanitize=True`; `&` thành `&amp;`, `<`/`>` trong chữ thành `&lt;`/`&gt;`, ADR-010 Amendment 1 C-2); `Comment.after_insert` → `notify_change("add")` → `publish_realtime("docinfo_update", {doc, key: "comments", action}, doctype, docname, after_commit=True)` (`comment.py:59-67, 85-104`), phòng `doc:` (`frappe/realtime.py:55-56`). Field phiếu đổi → `doc_update` (`frappe/model/document.py:1370-1385`, theo ADR-009 Bối cảnh).
- `call` của frappe-ui luôn gửi POST (`apps/helpdesk/desk/node_modules/frappe-ui/src/utils/call.ts:24-31`); Frappe từ chối HTTP method ngoài `methods=` (`frappe/handler.py:99-110`); request POST được commit, GET thì rollback (`frappe/app.py:451-458`); bộ đếm ghi `frappe.db.transaction_writes` (`frappe/database/database.py:437-438`) (ADR-010 Amendment 1 C-1).
- `is_agent(user: str | None = None) -> bool` — `apps/helpdesk/helpdesk/utils.py:42` (admin → True; có bản ghi HD Agent → `is_active`; không có → role Agent/Agent Manager).
- `html_to_plain_text(html: str) -> str` — `frappe/core/utils.py:95` (bỏ `script`/`style`, `<br>` và khối `p/div/li/tr/h*` → xuống dòng, BeautifulSoup giải thực thể).
- Permlevel: `Meta.get_permlevel_access(permission_type="read", parenttype=None, *, user=None)` (`frappe/model/meta.py:645`); `Document.apply_fieldlevel_read_permissions()` (`frappe/model/document.py:880`, bỏ field ngoài permlevel được đọc; Administrator thì bỏ qua); `frappe.has_permission(doctype, ptype, doc, user, throw)` (`frappe/__init__.py:1042`).
- Permlevel 8 của HD Ticket do Helpdesk cấp (đọc+ghi cho System Manager, Agent, Agent Manager trong `hd_ticket.json`; patch `helpdesk/patches/harden_hd_ticket_field_permissions.py:6`). erp_ai chỉ đặt `AI_PERMLEVEL = 8` cho field (`erp_ai/install.py:19,103`), không tự cấp quyền; FEAT-003 không cấp thêm (B-11).
- Đọc comment: DocType `Comment` chỉ cấp quyền cho System Manager/Website Manager, Agent dùng `get_list("Comment")` bị từ chối; timeline Helpdesk đọc qua `frappe.desk.form.activity.get_activity_timeline` (kiểm quyền đọc tài liệu, `frappe/desk/form/activity.py:26-33`; `author.email` = `owner`, `:254-271,331-337`) (research.md RQ-2). Vì vậy **không** tái dùng `authority.fetch_ticket_comments` (`erp_ai/agent/authority.py:27`, dùng `get_list` trên `Comment`, giới hạn 50, thuộc Lõi agent).
- `contains_keyword(content)` (`erp_ai/agent/policy.py:41-45`) đọc `trigger_keyword` bằng `frappe.db.get_single_value`, so casefold chuỗi con trên nội dung thô (không giải thực thể).
- Kiểu lỗi hiện có: `frappe.throw(_(...), frappe.PermissionError)` / `frappe.ValidationError`; method whitelisted duy nhất `check_keys` (`erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py:125`, `methods=["POST"]`), test bằng `frappe.allowed_http_methods_for_whitelisted_func` (`test_erp_ai_setting.py:384`). Log: `frappe.logger(LOGGER_NAME)` (`erp_ai/handlers.py:24`).
- Script trang: `erp_ai/public/js/agent_status_indicator.js` (195 dòng): `setupForm({ doc, router })` (`:1`), socket từ `#app.__vue_app__...$socket` (`:4-5`), state `window.__erpAiAgentStatus` (`:10-18`: `ticket, runs, finished, el, nameEl, textEl, socket`), `ensureElement` (`:20-72`, `div role=status` fixed phải-dưới, `document.body.appendChild` `:67`), `render/finish/reset/onStatus` (`:74-155`), `doc_subscribe` (`:161`), khối một-lần-mỗi-socket (`:163-190`: `EVENT`, `connect`, `router.afterEach`), trả `{ actions: [] }` (`:194`). Luật tĩnh: `STATUS_SCRIPT_FORBIDDEN` (`erp_ai/tests/test_architecture.py:98-118`), `STATUS_SCRIPT_REQUIRED` (`:121-132`), ghim chữ ký (`:1068-1075`), `LAYER_RULES` (`:36-64`) kiểm bằng `check_layer_imports` (`:326`, `test_layer_imports :993`). Cài vào bản ghi bằng `_ensure_agent_status_script` (`erp_ai/install.py:208-225`), gọi từ `after_install`/`after_migrate` (`erp_ai/hooks.py:86-87`).
- Test và helper: `erp_ai/tests/test_handlers.py` (`TestCommentHandler :246`, `HandlerTestCase._comment :102`); `erp_ai/tests/test_install.py` (bản ghi script `:311-411`); `erp_ai/agent/test_policy.py`; `erp_ai/test_utils.py` (`FakeGateway :32`, `record_status_signals :57`, `set_agent_settings :74`, `add_credential :80`); Helpdesk `helpdesk/test_utils.py` (`make_ticket :176`, `create_agent :344`, `create_user :655`).
- Profile: `structure.tests = colocated`, `naming.test_file = test_{name}.py`, `allowed_new_file_roots = [erp_ai, docs, .github]`, `protected_paths = [.env, .env.*, **/*.pem, **/*.key, license.txt]`, không có slot `cmd.test_js`, `ui: false`.

## 2. Mô hình dữ liệu
### 2.1 Phần 1 — siêu dữ liệu của 3 DocType (không có cột mới)
**Quy tắc mô tả.** Nội dung của từng `description` = các ý bắt buộc trong bảng "Dữ liệu" của spec (dòng 56-80) **nguyên văn về nghĩa**, cộng 5 ý chung (spec dòng 47-52) cho mọi field. Design không chép lại 71 dòng; dev viết từ bảng spec, QA đối chiếu theo AC-2. Ràng buộc chung cho mọi mô tả:
- tiếng Việt, ≤ 400 ký tự (NFR-1), là chữ thường (không HTML);
- field `read_only = 1` hoặc hệ thống tự quản: có cụm "Hệ thống tự ghi" và "không sửa được";
- không có `sk-`, không email thật (ví dụ chỉ dùng `@congty.vn` hoặc `@example.com`), không `miyano`, không giá trị đang lưu trên site (AC-4).

**Ngoại lệ và quyết định thêm (chỉ những chỗ bảng spec không nói):**
| DocType.field | Quyết định |
|---|---|
| Credential `api_key` | Nói "khóa bí mật do nhà cung cấp cấp, lưu mã hóa, sau khi lưu không hiện lại, không bao giờ ghi vào Log". Không nêu tiền tố khóa (AC-4 cấm `sk-`) |
| Credential `label`, `provider`, `enabled`, `note`; Setting `credentials` | Chỉ 5 ý chung; `label` nhắc "không trùng, không phân biệt hoa thường" (lấy từ dòng `credentials` của bảng spec) |
| Setting `trigger_keyword` | Ví dụ "@ai" theo bảng spec. Quy tắc "không có giá trị đang lưu" của AC-4 được test kiểm với giá trị chuỗi ≥ 4 ký tự (xem 8), nên ví dụ 3 ký tự của spec không bị tính |
| Setting `alert_recipients` | Ví dụ `canhbao@congty.vn` |
| Log (31 field) | Mỗi mô tả kết thúc bằng câu cố định "Hệ thống tự ghi khi agent chạy, không sửa được." Riêng `human_corrected_to/by/at` thay câu đó bằng nội dung của bảng spec dòng 79 (vẫn có "Hệ thống tự ghi" và "không sửa được") |
| Section Break | Không có mô tả (tùy chọn ở AC-3; bỏ để form gọn) |

**Chia nhóm (Section Break có label, A-5, AC-3).** Mỗi Section Break là một field `fieldtype: "Section Break"`, `fieldname` dạng `section_<chủ đề>` (snake_case, `naming.*`), chỉ có `label`; chèn vào `fields` và `field_order` **ngay trước** field đầu của nhóm. Thứ tự tương đối của mọi field không phải Break giữ nguyên (AC-5). Hiện cả 3 DocType chưa có Section/Column Break nào.

| DocType | Section Break (`fieldname` — label) | Field của nhóm, theo thứ tự hiện có |
|---|---|---|
| ERP AI Setting (7 nhóm) | `section_activation` — "Bật và mức quyền" | `enabled`, `permission_level` |
| | `section_limits` — "Giới hạn mỗi lần chạy" | `max_turns_per_run`, `max_runs_per_ticket_per_day`, `max_keys_per_call`, `request_timeout_s` |
| | `section_budget` — "Ngân sách và đơn giá" | `monthly_budget_usd`, `spent_this_month_usd`, `price_input_per_mtok`, `price_cache_write_per_mtok`, `price_cache_read_per_mtok`, `price_output_per_mtok` |
| | `section_model` — "Model và từ khóa kích hoạt" | `model_classify_default`, `trigger_keyword` |
| | `section_reply` — "Chỉ báo và độ trễ trả lời" | `thinking_text`, `answer_delay_min_s`, `answer_delay_max_s` |
| | `section_routing` — "Phân loại và nhóm loại trừ" | `excluded_teams`, `category_mapping`, `prompt_digest` |
| | `section_alerts` — "Cảnh báo và khóa API" | `alert_recipients`, `credentials` |
| ERP AI Credential (4 nhóm) | `section_key` — "Khóa và model" | `label`, `provider`, `api_key`, `model_classify`, `model_reason` |
| | `section_usage` — "Thứ tự thử và ngân sách" | `try_order`, `purpose`, `budget_month_usd`, `spent_month_usd`, `enabled` |
| | `section_state` — "Trạng thái khóa" | `status`, `paused_until`, `tokens_remaining`, `limit_reset_at`, `error_count`, `last_error`, `last_success_at` |
| | `section_note` — "Ghi chú" | `note` |
| ERP AI Log (6 nhóm) | `section_run` — "Lần chạy" | `ticket`, `run_id`, `entry_type`, `turn`, `trigger`, `instructor`, `model` |
| | `section_usage` — "Token, chi phí và khóa" | `input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`, `cost_usd`, `credential_label`, `keys_tried`, `latency_ms`, `stop_reason` |
| | `section_changes` — "Tool và thay đổi trên phiếu" | `tools_called`, `actions`, `value_before`, `value_after`, `skipped_fields` (**không** có Break giữa `value_after` và `skipped_fields`, spec dòng 87) |
| | `section_prediction` — "Dự đoán phân loại" | `predicted_category`, `predicted_confidence`, `predicted_ticket_type`, `predicted_agent_group`, `predicted_priority`, `applied` |
| | `section_correction` — "Người sửa sau dự đoán" | `human_corrected_to`, `human_corrected_by`, `human_corrected_at` |
| | `section_error` — "Lỗi" | `error` |

Mọi label nhóm có ít nhất một chữ có dấu tiếng Việt (để test AC-3 kiểm được "tiếng Việt"). Không label nhóm nào chứa "(USD)" (test hiện có chỉ bám label của field).

**Ràng buộc không đổi (AC-5, A-2):** với mọi field không phải Break — `fieldname`, `fieldtype`, `label`, `options`, `default`, `read_only`, `read_only_depends_on`, `reqd`, `precision`, `in_list_view`, `search_index`, `permlevel`, `hidden`, `depends_on` giữ nguyên; quyền (`permissions`) của DocType giữ nguyên. Chỉ đổi: `description` (thêm), Section Break (thêm), `modified` (tăng để `cmd.migrate` nhập lại JSON).

### 2.2 Phần 2 — không có dữ liệu mới
- Không DocType, field hay bản ghi mới (AC-14; ADR-010 Quyết định 5). Trạng thái ngăn chỉ nằm trong bộ nhớ trang (đối tượng `window.__erpAiAgentStatus`, ADR-009 Quyết định 6); không `localStorage`/`sessionStorage`/cookie.
- **Đọc** (dưới phiên người dùng, ADR-010 Quyết định 4): 4 field AI của HD Ticket (`ai_resolution_hint` Text Editor, `ai_confidence`, `ai_classified_by`, `ai_updated_at`; permlevel 8, `erp_ai/install.py:114-151`); các core `Comment` của phiếu qua `get_activity_timeline`; `trigger_keyword` chỉ qua hàm của `erp_ai/agent/policy.py`.
- **Ghi:** đúng 1 core `Comment` mỗi lần gửi, qua `HD Ticket.new_comment`, `owner` = người gửi (ADR-010 Quyết định 7). Bảng chủ ghi ADR-004 không đổi.
- **Chủ của dữ liệu:** comment của người — người đó (qua method Helpdesk); comment của bot — `post_comment` (ADR-004); field AI — tool của agent (ADR-004). Ngăn không ghi field nào.
- Không phân trang, không cache (B-13, STD-DESIGN-5).

## 3. API / hợp đồng
**Phiên bản:** hợp đồng nội bộ script ↔ server, phiên bản 1 (ADR-010). Mọi thay đổi sau này chỉ được **thêm** khóa; script bỏ qua khóa lạ. **Không có thay đổi phá vỡ** hợp đồng có sẵn: `erp_ai:agent_status` (ADR-008), `check_keys`, hàm xếp hàng (ADR-003) không đổi. Hợp đồng duy nhất bị đổi là phạm vi script trên trang (ADR-009) — nội bộ app, cùng tệp, cùng bản ghi.

**Module:** `erp_ai/ticket_panel.py` (tầng Cửa vào, cạnh `erp_ai/handlers.py`; ADR-010 Quyết định 1). **Danh sách method (allow-list, định nghĩa một lần ở Python):** `erp_ai/constants.py`
```python
PANEL_METHODS = (
    "erp_ai.ticket_panel.get_panel_data",
    "erp_ai.ticket_panel.send_message",
)
PANEL_MAX_MESSAGE_CHARS = 2000
```
Tệp `.js` dùng đúng 2 chuỗi literal này trong `call(`; test so hai tập (ADR-009 Ràng buộc).

### 3.1 `get_panel_data(ticket: str) -> dict` — đọc
- **Khai báo:** `@frappe.whitelist(methods=["POST"])` (ADR-010 Quyết định 2, Amendment 1: `call` của frappe-ui luôn gửi POST; POST còn được Frappe kiểm CSRF). Không `allow_guest`, không khai thêm `"GET"`. *(Amendment 1; bản trước: chờ architect, ADR ghi `["GET"]`.)*
- **Đầu vào:** `ticket` — tên HD Ticket, kiểu `str`, không rỗng sau `strip()`. Sai kiểu/rỗng → `frappe.ValidationError`.
- **Đầu ra** (mọi chuỗi là chữ thường, không HTML; `null` khi trống):
```json
{
  "ticket": "123",
  "ai_fields": [
    {"fieldname": "ai_resolution_hint", "label": "Hướng giải quyết (AI)", "text": "Dòng 1\nDòng 2"},
    {"fieldname": "ai_confidence",      "label": "Độ tin cậy (AI)",       "text": "Cao"},
    {"fieldname": "ai_classified_by",   "label": "Phân loại bởi",         "text": null},
    {"fieldname": "ai_updated_at",      "label": "AI cập nhật lúc",       "text": "12-11-2026 10:05"}
  ],
  "messages": [
    {"name": "c1a2b3", "author": "Nguyễn Văn A", "is_bot": false, "created_at": "12-11-2026 10:00", "text": "Phiếu này xử lý sao? @ai"},
    {"name": "d4e5f6", "author": "ERP AI",       "is_bot": true,  "created_at": "12-11-2026 10:01", "text": "Bạn kiểm tra..."}
  ]
}
```
  - `ai_fields`: luôn đúng 4 phần tử, thứ tự cố định như trên. `label` lấy từ meta (`frappe.get_meta("HD Ticket").get_label(fieldname)`), nên label chỉ có một nguồn (`install.py`). `text`: Text Editor → `html_to_plain_text`; Datetime → `frappe.utils.format_datetime`; loại khác → `frappe.utils.cstr`; giá trị rỗng hoặc field bị bỏ do permlevel → `null` (script hiện "Chưa có", AC-7).
  - `messages`: theo B-5 (ADR-010 Quyết định 5): mục của `get_activity_timeline` là core `Comment` có `comment_type == "Comment"`, và (`owner == AGENT_USER`) hoặc (`policy.contains_keyword(content)`). Sắp theo `creation` tăng dần (cũ trên, mới dưới; AC-8). `author` = `frappe.utils.get_fullname(owner)`; `is_bot` = `owner == AGENT_USER`; `created_at` = `format_datetime(creation)`; `text` = `html_to_plain_text(content)`. Không trả email, không trả nhãn "chỉ thị/dữ liệu" (B-14). Khóa cụ thể của từng mục timeline (loại mục, `comment_type`, `author.email`, `content`, `creation`, `name`) dev đọc ở `frappe/desk/form/activity.py:254-271,331-337` và ghim bằng test AC-8.
  - **Không bao giờ trả:** `trigger_keyword` hay bất kỳ giá trị nào của ERP AI Setting/Credential/Log; bật/tắt, mức quyền, nhóm loại trừ, `ai_opt_out`, ngân sách, trạng thái lần chạy (ADR-010 Quyết định 5; ADR-008 Quyết định 1).
- **Tác dụng phụ:** không có. Không tạo/sửa/xóa bản ghi, không `commit`, không cache, không gọi gateway/runner/hàng đợi (ADR-010 Quyết định 5; AC-14). Vì method là POST nên Frappe commit mọi lệnh ghi trong request (`frappe/app.py:451-455`); bảo đảm thay thế: hàm đọc và mọi hàm nó gọi phát **0 câu lệnh ghi SQL**, đo bằng `frappe.db.transaction_writes` (mục 8 B, AC-14), cộng luật tĩnh "hàm đọc không có `.new_comment(`" và danh sách cấm của module (mục 8 C). *(Amendment 1.)*
- **Lỗi:**

| Trường hợp | Lỗi | HTTP (Frappe) |
|---|---|---|
| Guest | chặn bởi `@frappe.whitelist` không `allow_guest` | 403 |
| Không phải agent (`is_agent()` False: HD Contact, Website User, HD Agent `is_active = 0`) | `frappe.PermissionError` | 403 |
| Agent không có quyền đọc phiếu, hoặc phiếu không tồn tại | `frappe.PermissionError` (cùng thông báo, không lộ phiếu có tồn tại hay không) | 403 |
| `ticket` sai kiểu/rỗng | `frappe.ValidationError` | 417 |
| Gọi bằng GET | Frappe từ chối (method ngoài `methods=`, `frappe/handler.py:99-110`) *(Amendment 1)* | 403 |
| Thiếu/sai CSRF token (POST) | Frappe từ chối trước khi vào hàm (`frappe/auth.py`); `call` tự gắn token *(Amendment 1)* | 400 |

Thông báo lỗi server (tiếng Việt, `_()`): "Bạn không có quyền xem khu vực này của phiếu." / "Thiếu mã phiếu.". Script **không** hiện thông báo của server; nó hiện câu cố định của mục 3.3.

### 3.2 `send_message(ticket: str, text: str) -> dict` — gửi
- **Khai báo:** `@frappe.whitelist(methods=["POST"])`. Không `allow_guest`.
- **Đầu vào:** `ticket` như 3.1. `text` — kiểu `str`, chữ người gõ đúng như gõ (ADR-009 Quyết định 5). Sau `strip()`: rỗng → lỗi; dài hơn `PANEL_MAX_MESSAGE_CHARS` (2000) → lỗi.
- **Dựng nội dung (vị trí chèn từ khóa = cuối tin, B-6):**
  1. `lines = text.strip().splitlines()`; `body = "<br>".join(html.escape(line, quote=False) for line in lines)` → `<`, `>`, `&` thành thực thể (AC-9; ADR-010 Quyết định 7), ngắt dòng giữ được ở tab Comments của Helpdesk.
  2. Nếu `policy.contains_keyword(body)` False và từ khóa đang cấu hình không rỗng: `body = body + " " + html.escape(policy.get_trigger_keyword(), quote=False)`. Hàm mới `get_trigger_keyword() -> str` trong `erp_ai/agent/policy.py` chỉ đọc `trigger_keyword` (giữ luật "trường cấu hình chỉ đọc trong policy"). **`policy.contains_keyword` giữ nguyên, không sửa một dòng nào** (ADR-010 Quyết định 7, AC-15). *(Amendment 1; bản trước: `contains_keyword` đổi sang dùng `get_trigger_keyword`.)*
  3. `content = "<p>" + body + "</p>"`.
  4. **Kiểm trên dạng sẽ được lưu, trước `new_comment`** *(Amendment 1, C-2)*: `stored = sanitize_html(content, always_sanitize=True)` (`frappe.utils.html_utils.sanitize_html`, đúng lời gọi `Comment.validate` dùng ở `frappe/core/doctype/comment/comment.py:69-74`; dev đối chiếu tham số khi viết, không tự viết bộ escape tương đương — D-9). Từ khóa không rỗng mà `policy.contains_keyword(stored)` False → `frappe.ValidationError`, **không gọi `new_comment`**, 0 comment. Thực tế chỉ xảy ra khi từ khóa có `<`, `>` hoặc `&`. Thông báo không chứa từ khóa (B-8).
  5. Từ khóa rỗng → gửi `content` không có từ khóa (giống ô Comments: comment được tạo, handler không xếp hàng, như `test_comment_with_empty_keyword_setting_no_job`).
- **Ghi:** đúng 1 lời gọi `frappe.get_doc("HD Ticket", ticket).new_comment(content)` — không `attachments`, không `comment_email`/`comment_by`, không `frappe.desk.form.utils.add_comment` (ADR-010 Quyết định 7). `Comment.validate` vẫn sanitize như mọi comment; kết quả trùng `stored` ở bước 4.
- **Bất biến** (ADR-010 Amendment 1): khi từ khóa không rỗng, mọi comment ngăn tạo ra có `Comment.content` đã lưu qua được `policy.contains_keyword`, nên handler của FEAT-001 thấy tin đúng như comment `@ai` gõ tay.
- **Đầu ra:** `{"comment": "<tên Comment mới>"}`. Script tự nạp lại luồng bằng `get_panel_data` (không có hình dạng tin thứ hai để giữ đồng bộ).
- **Không làm:** không gọi `is_enabled`, `can_send_ticket`, `effective_level`, `runs_today`, `enqueue`; không đọc `permission_level`, `excluded_teams`, `ai_opt_out` (ADR-010 Quyết định 8). Mọi chốt chạy ở `comment_after_insert` và runner như ô Comments (AC-10). Kiểm từ khóa ở bước 4 không phải chốt agent: chỉ xét nội dung tin (ADR-010 Quyết định 8).
- **Giới hạn tần suất:** **không thêm** `frappe.rate_limiter`. Lý do: spec không đòi (STD-DESIGN-5); chi phí đã bị chặn bởi `max_runs_per_ticket_per_day` và chống trùng job (ADR-003); giới hạn tần suất sẽ làm đường ngăn khác ô Comments ở test AC-10 khi gửi liên tiếp.
- **Idempotency:** không có khóa chống trùng ở server — giống ô Comments (mỗi lần bấm là một tin của người, không phải tích hợp ngoài). Phía trang chặn bấm lặp khi đang gửi (mục 4, F2).
- **Lỗi:**

| Trường hợp | Lỗi | Comment tạo ra |
|---|---|---|
| Guest | chặn bởi whitelist | 0 |
| Không phải agent / không có quyền đọc phiếu / phiếu không tồn tại | `frappe.PermissionError` (như 3.1) | 0 |
| Phiên là `AGENT_USER` | `frappe.PermissionError` "Tài khoản agent không được gửi tin từ khu vực này." (ADR-010 Quyết định 3) | 0 |
| `text` sai kiểu hoặc rỗng sau `strip()` | `frappe.ValidationError` "Nội dung tin trống." | 0 |
| `text` > 2000 ký tự sau `strip()` | `frappe.ValidationError` "Tin dài quá 2000 ký tự." | 0 |
| Từ khóa đang cấu hình không giữ được sau sanitize (có `<`, `>`, `&`) | `frappe.ValidationError` "Từ khóa kích hoạt trong ERP AI Setting có ký tự không dùng được. Quản trị viên cần đổi từ khóa này." (không nhắc giá trị từ khóa; không khuyên dùng tab Comments, vì ô Comments cũng không kích hoạt được bot với từ khóa đó) *(Amendment 1; bản trước: "…hãy dùng tab Comments.")* | 0 |
| `new_comment` ném lỗi (ví dụ `is_agent()` của Helpdesk) | lỗi của Helpdesk truyền nguyên | 0 (Frappe rollback request) |

Như 3.1, script hiện câu cố định "Không gửi được tin…" của mục 3.3 cho mọi lỗi gửi; thông báo server ở trên là chữ của `ValidationError` (thấy trong phản hồi và Error Log), không phải chữ script tự hiện.

### 3.3 Hợp đồng phía trang (`erp_ai/public/js/agent_status_indicator.js`, ADR-009)
- Chữ ký: `function setupForm({ doc, call, router })`. Trả `{ actions: [{ label: "Trao đổi với bot", onClick: togglePanel }] }`; trả `{ actions: [] }` khi không có socket/`doc.name` (như hiện nay) hoặc khi `window.innerWidth < 640` (ADR-009 Quyết định 3). Khóa của action (`label`, `onClick`) dev đối chiếu `apps/helpdesk/desk/src/components/ticket-agent/TicketHeader.vue:24-30`.
- `call` chỉ với đối số đầu là một trong 2 chuỗi của `PANEL_METHODS`; `call` trả thẳng `message` (`call.ts:16`). `call` luôn gửi POST và tự gắn CSRF token (ADR-010 Amendment 1).
- Câu chữ tiếng Việt cố định (chỉ một nơi, trong tệp `.js`):

| Chỗ | Chữ |
|---|---|
| Action header | "Trao đổi với bot" |
| Tiêu đề ngăn | "Hướng giải quyết & trao đổi với bot" |
| Nút đóng | "Đóng" |
| Tiêu đề phần (1) / (2) | "Hướng giải quyết của AI" / "Trao đổi với bot" |
| Mục AI trống | "Chưa có" |
| Luồng trống | "Chưa có tin nào." |
| Nhãn tin của bot | "Bot" (đặt trước tên người viết) |
| Dòng hướng dẫn B-8 | "Bot có thể không trả lời khi đang tắt, đang ở chế độ chỉ ghi nhận, phiếu không dùng AI hoặc thuộc nhóm loại trừ, hoặc đã hết lượt hôm nay." |
| Ô nhập (placeholder) | "Nhập câu hỏi cho bot. Enter để gửi, Shift+Enter để xuống dòng." |
| Nút gửi / đang gửi | "Gửi" / "Đang gửi…" |
| Gửi rỗng (không gọi server) | "Hãy nhập nội dung trước khi gửi." |
| Quá dài (không gọi server) | "Tin dài quá 2000 ký tự." |
| Gửi thất bại | "Không gửi được tin. Chữ bạn gõ vẫn còn, hãy thử lại." |
| Tải thất bại | "Không tải được dữ liệu của khu vực. Hãy đóng rồi mở lại." |

## 4. Luồng
Mọi hàm xử lý phía trang nằm trong `try { … } catch (…) {}` như FEAT-002; lỗi của ngăn không làm hỏng chỉ báo hay trang (ADR-009 Quyết định 4).

**Trạng thái mở rộng** (cùng đối tượng `window.__erpAiAgentStatus`, ADR-009 Quyết định 6): thêm `call` (gán lại mỗi lần `setupForm` chạy), `panel` = `{ el, open, slotEl, aiListEl, threadEl, errorEl, inputEl, sendEl, seq, sending }`, `resizeBound`. Phần tử chỉ báo vẫn là `state.el` duy nhất.

**F1 — Mở/đóng ngăn (AC-6, AC-7, AC-8).**
1. Bấm action "Trao đổi với bot" → `togglePanel()` đọc `state.ticket` (không dùng `doc` trong closure).
2. Mở: dựng ngăn một lần (`document.createElement` cho `div`/`span`/`strong`/`textarea`/`button`; gắn `document.body.appendChild`), `position: fixed`, phải 24 px, trên 72 px, rộng 380 px, cao tối đa `calc(100vh - 120px)`, cuộn dọc, `zIndex` 40. Không dùng số `600` ở bất cứ đâu (luật cấm hiện có; dùng `fontWeight: "bold"`).
3. Chuyển `state.el` (chỉ báo) vào `panel.slotEl`, đổi style sang tĩnh (không fixed). Đóng: trả `state.el` về `document.body` với style FEAT-002 cũ (ADR-009 Quyết định 6; AC-11 (d), AC-15).
4. `reload()`.

**`reload()`** — chỉ khi `panel.open` và `state.ticket` có giá trị: `seq = ++panel.seq`; `t = state.ticket`; `state.call("erp_ai.ticket_panel.get_panel_data", { ticket: t })` (POST) → khi xong, bỏ qua nếu `seq !== panel.seq` hoặc `t !== state.ticket` hoặc ngăn đã đóng (chống hiện dữ liệu phiếu cũ, AC-11 (g)); ngược lại vẽ lại bằng `replaceChildren()` + `textContent` (mục AI: label + `text ?? "Chưa có"`; tin: dòng đầu "Bot · <tên> · <giờ>" hoặc "<tên> · <giờ>", thân `text` với `whiteSpace: "pre-wrap"`; tin bot có nền khác). Lỗi → "Không tải được dữ liệu…" trong `panel.errorEl`.
- Server: cổng quyền (mục 5) → `get_doc` + `apply_fieldlevel_read_permissions()` → 4 field → `get_activity_timeline` → lọc B-5 → `html_to_plain_text` → trả. Không ghi gì (0 câu ghi SQL, dù request POST được commit).

**F2 — Gửi (AC-9, AC-10).**
1. Enter (không Shift, và `event.isComposing` = false để không gửi giữa lúc gõ tiếng Việt bằng bộ gõ) hoặc bấm "Gửi".
2. Phía trang: `value.trim()` rỗng → "Hãy nhập nội dung…", không gọi; dài > 2000 → "Tin dài quá 2000 ký tự.", không gọi; `panel.sending` = true thì bỏ qua (chống bấm lặp); đặt nút "Đang gửi…", khóa nút.
3. `state.call("erp_ai.ticket_panel.send_message", { ticket: state.ticket, text: value })` — gửi đúng chữ đã gõ, không thêm từ khóa (ADR-009 Quyết định 5).
4. Server: cổng quyền → từ chối `AGENT_USER` → kiểm `text` → dựng nội dung (3.2 bước 1–3) → kiểm từ khóa trên dạng sẽ lưu (3.2 bước 4; không qua → `ValidationError`, dừng) → `new_comment` → log → trả `{comment}`.
5. Sau commit (Frappe, không phải mã mới): `Comment.after_insert` → `handlers.comment_after_insert` (`erp_ai/handlers.py:100-120`) xét `comment_type` → `is_enabled` → `owner` → `contains_keyword` → `can_send_ticket` → xếp hàng `TRIGGER_COMMENT_MENTION`; runner xét `not_sendable`, `daily_limit`, `effective_level`, `level_L0`; `authority.py` lấy `owner` làm tác giả. `docinfo_update` phát vào phòng `doc:` sau commit.
6. Trang thành công: xóa ô nhập, xóa lỗi, `reload()`. Thất bại (403/417/mạng/timeout): "Không gửi được tin. Chữ bạn gõ vẫn còn…", chữ giữ nguyên. Cuối cùng: mở khóa nút.

**F3 — Cập nhật trực tiếp (AC-11, NFR-3).** Đăng ký trong khối `if (state.socket !== socket)` hiện có, mỗi socket một lần, hàm có tên, không bao giờ gỡ (ADR-009 Quyết định 4):
- `socket.on("docinfo_update", onDocinfo)`: chỉ khi `msg.key === "comments"`, `msg.doc.reference_doctype === "HD Ticket"`, `String(msg.doc.reference_name) === state.ticket` → `reload()`.
- `socket.on("doc_update", onDocUpdate)`: chỉ khi `msg.doctype === "HD Ticket"` và `String(msg.name) === state.ticket` → `reload()` (field AI do bot ghi, AC-11 (e)). Khóa payload dev đối chiếu `frappe/model/document.py:1370-1385`.
- Handler `connect` hiện có: giữ `doc_subscribe`, thêm `if (state.panel.open) reload()` (nối lại socket).
- Sự kiện `erp_ai:agent_status` và logic chỉ báo theo `run_id` không đổi (ADR-008); chỉ báo hiện trong ngăn vì phần tử đã được chuyển vào (F1.3).
- `reload()` tự bỏ qua khi ngăn đóng → ngăn đóng thì 0 lời gọi (NFR-4). Không `setInterval`, không polling.

**F4 — Đổi phiếu, rời trang, màn hẹp (AC-11 (g), B-2).**
- `doc.name` đổi (`:157-160`) và `router.afterEach` rời phiếu (`:176-189`) đều gọi `reset()`; `reset()` mở rộng thêm: đóng ngăn, trả chỉ báo về `document.body`, xóa nội dung, xóa ô nhập, `panel.seq++` (hủy kết quả đang chờ).
- `window.addEventListener("resize", onResize)` đăng ký một lần (cờ `state.resizeBound`): `innerWidth < 640` → đóng ngăn. Lần `setupForm` sau trả `actions: []`.

**F5 — Không có socket / lỗi lạ.** Như FEAT-002: trả `{ actions: [] }`, không ném lỗi (FEAT-002 AC-10 (g)). Dữ liệu trả về lạ (không phải object, thiếu mảng) → coi như lỗi tải.

**Lời gọi ra ngoài và timeout (STD-ERR-5).** Server không có lời gọi mạng nào mới (chỉ DB của site; Claude API vẫn chỉ qua runner, ADR-002). Trình duyệt → server qua `call`: frappe-ui không có tham số timeout; thời gian bị chặn bởi timeout request của tiến trình web. Kết quả: thành công → F2.6; thất bại → thông báo, giữ chữ; **không rõ** (timeout nhưng comment có thể đã tạo) → hiện thông báo thất bại, giữ chữ; nếu comment đã tạo thật thì `docinfo_update` sẽ đưa nó vào luồng, người thấy và không cần gửi lại (giống ô Comments).

## 5. Quyền
**Cổng chung** `_require_panel_access(ticket)` chạy đầu tiên trong cả hai method (ADR-010 Quyết định 3; STD-SEC-4; cùng ngữ nghĩa `can_see_ticket_comments` của Helpdesk):
1. `helpdesk.utils.is_agent()` (phiên hiện tại) False → `frappe.PermissionError`.
2. `ticket` không tồn tại, hoặc `frappe.has_permission("HD Ticket", "read", doc=ticket)` False → `frappe.PermissionError` (cùng thông báo).
3. Riêng `send_message`: `frappe.session.user == AGENT_USER` → `frappe.PermissionError`.

Cả hai method là POST nên Frappe kiểm CSRF trước khi vào hàm (ADR-010 Hệ quả, Amendment 1).

**Đọc dưới quyền người dùng (ADR-010 Quyết định 4):** field AI qua `doc.apply_fieldlevel_read_permissions()` (permlevel 8 do Helpdesk cấp cho Agent/Agent Manager/System Manager; không suy từ tên role); comment qua `get_activity_timeline` (tự kiểm quyền đọc tài liệu). Không `ignore_permissions`, không `frappe.flags.ignore_permissions`, không `frappe.set_user`, không `get_all`/`db.sql` trên `Comment`. Không cấp quyền mới cho role nào (B-11).

**Gửi:** `new_comment` của Helpdesk kiểm `is_agent()` lần nữa (`hd_ticket.py:618`), `Comment.before_insert` của Helpdesk chặn người không phải agent (`helpdesk/extends/comment.py:15-22`), `Comment.validate` sanitize nội dung. Ngăn không cho làm điều gì mà ô Comments không cho (NFR-5): không đính kèm, không sửa/xóa, không nhắc tên.

| Tài khoản | Thấy ngăn | `get_panel_data` | `send_message` |
|---|---|---|---|
| Agent / Agent Manager có quyền đọc phiếu | Có (desktop) | Dữ liệu | Tạo 1 Comment, `owner` = mình |
| `ERP AI Instructor`, người được giao phiếu | Có | Dữ liệu | Như trên; thẩm quyền do `authority.py` xét (B-14) |
| Agent không có quyền đọc phiếu | Có action, ngăn hiện lỗi tải | `PermissionError` | `PermissionError` |
| HD Agent `is_active = 0` | Trang agent không mở được | `PermissionError` | `PermissionError` |
| HD Contact, Website User | Không (`apply_to_customer_portal = 0`, `erp_ai/install.py:23-30`; phòng `doc:` chỉ cho agent) | `PermissionError` | `PermissionError` |
| Guest | Không | chặn bởi whitelist | chặn bởi whitelist |
| `AGENT_USER` | — | theo quyền của nó | `PermissionError` |

**Phía trang (NFR-5, AC-12):** chỉ `textContent`; không phân tích HTML, không escape/unescape, không tạo `a`/`img`/`iframe`/`script`, không gán `src`/`href`; `querySelector` chỉ cho `#app`; không ghi storage. Nội dung từ server coi là không tin cậy.

**Quan sát (STD-OPS-5), không dữ liệu nhạy cảm (STD-SEC-6):** dùng `frappe.logger(LOGGER_NAME)` như `erp_ai/handlers.py:24`:
- `send_message` thành công: `info` "erp_ai panel send ticket=<tên> comment=<tên> keyword_added=<true|false>";
- bị từ chối: `info` "erp_ai panel denied method=<get|send> ticket=<tên> reason=<not_agent|no_read|agent_user>";
- từ khóa không giữ được sau sanitize: `info` "erp_ai panel send rejected ticket=<tên> reason=keyword_not_storable" *(Amendment 1)*;
- `get_panel_data`: `debug` "erp_ai panel read ticket=<tên> messages=<n>".
Không ghi nội dung tin, giá trị từ khóa, email hay tên người.

## 6. Migration và rollback
Không có thay đổi dữ liệu (không cột, không bản ghi, không di trú). Chỉ có siêu dữ liệu DocType và nội dung bản ghi HD Form Script do `install.py` làm chủ (ADR-007 Quyết định 3–4).
- **Lên:** sửa 3 tệp JSON DocType (mô tả + Section Break, tăng `modified`) → `cmd.migrate` nhập lại JSON (Section Break và `description` không tạo cột) → `after_migrate` → `_ensure_agent_status_script` (`erp_ai/install.py:208-225`) đặt lại bản ghi "ERP AI Agent Status" từ tệp `.js` mới. Module Python mới cần khởi động lại tiến trình web để method whitelisted được nạp (site dev `miyano`; production là việc của người, G5).
- **Xuống:** `git revert` các commit FEAT-003 trên `team/FEAT-003`, tăng lại `modified` của 3 tệp JSON (giá trị cũ nhỏ hơn giá trị trong DB nên Frappe có thể bỏ qua khi nhập — dev kiểm khi chạy lên/xuống/lên), rồi `cmd.migrate` → mô tả và Section Break mất, bản ghi script trở về bản FEAT-002. Comment đã gửi từ ngăn là comment bình thường của người (như ô Comments) → giữ nguyên, không xóa.
- **Đối soát (QA chạy lên/xuống/lên):**
  1. Script chỉ đọc của AC-5: so JSON 3 DocType với nhánh nền (`team/BUG-002`, chứa FEAT-002) → 0 khác biệt ngoài `description`, Section Break mới, `modified`.
  2. Bản ghi ERP AI Setting trước và sau migrate giống nhau (bỏ `modified`).
  3. Đúng 1 HD Form Script tên "ERP AI Agent Status", `script` = nội dung tệp, `apply_to_customer_portal = 0` (test hiện có `erp_ai/tests/test_install.py:311-360`).
  4. Số bản ghi `Comment`, `HD Ticket`, `ERP AI Log` không đổi qua migrate.
- **Điều kiện rollback:** `cmd.migrate` lỗi; `test_install.py` đỏ; console trang phiếu có lỗi mới do `erp_ai`; chỉ báo FEAT-002 hỏng (FEAT-002 AC-10 (h)(i)). **Thành công:** `cmd.migrate` OK và đối soát 1–4 đạt.
- Không có bảng lớn, không cần chạy theo lô.

## 7. Touchpoints
| file | change | ghi chú |
|---|---|---|
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json` | sửa | 22 mô tả + 7 Section Break, `modified` (AC-1..AC-5) |
| `erp_ai/erp_ai_agent/doctype/erp_ai_credential/erp_ai_credential.json` | sửa | 18 mô tả + 4 Section Break, `modified` |
| `erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json` | sửa | 31 mô tả + 6 Section Break, `modified`; `skipped_fields` ngay sau `value_after` |
| `erp_ai/tests/test_doctype_descriptions.py` | mới | Test AC-1..AC-4, NFR-1, phần thứ tự của AC-5 |
| `erp_ai/ticket_panel.py` | mới | Module ngăn tầng Cửa vào: `get_panel_data`, `send_message` (cả hai POST), cổng quyền, kiểm từ khóa trên dạng sẽ lưu (ADR-010, Amendment 1) |
| `erp_ai/tests/test_ticket_panel.py` | mới | Test AC-7..AC-10, AC-12..AC-14 phía server, gồm `transaction_writes` và test từ khóa đặc biệt |
| `erp_ai/constants.py` | sửa | `PANEL_METHODS`, `PANEL_MAX_MESSAGE_CHARS` (allow-list định nghĩa một lần) |
| `erp_ai/agent/policy.py` | sửa | Chỉ thêm `get_trigger_keyword()`; `contains_keyword` **không sửa** (AC-15) *(Amendment 1; bản trước: `contains_keyword` dùng hàm mới)* |
| `erp_ai/agent/test_policy.py` | sửa | Thêm test `get_trigger_keyword`; test cũ của `contains_keyword` không sửa |
| `erp_ai/public/js/agent_status_indicator.js` | sửa | Action, ngăn, `call`, `docinfo_update`/`doc_update`, chuyển chỉ báo, ẩn < 640 px (ADR-009) |
| `erp_ai/tests/test_architecture.py` | sửa | Danh sách cấm/bắt buộc của `.js` (bỏ đúng `\bcall\b`, thêm chuỗi cấm ADR-009), chữ ký `setupForm`, luật allow-list `call`, `LAYER_RULES` cho `erp_ai.ticket_panel`, luật whitelist (cả hai `["POST"]`), luật ghi duy nhất `new_comment` (hàm đọc không có) |

Không chạm: `erp_ai/install.py`, `erp_ai/handlers.py`, `erp_ai/agent/runner.py`, `erp_ai/agent/authority.py`, `erp_ai/agent/tools/**`, `erp_ai/gateway/**`, `erp_ai/hooks.py`, `apps/helpdesk/**`, `apps/frappe/**`. Tài liệu người dùng (DoD phần 2) do writer viết ở `/team:asbuilt`, dưới `docs/`.

**Tổng:** 11 touchpoint (8 sửa, 3 mới). Amendment 1 không thêm hay bớt touchpoint.

**Đối chiếu đường mới ↔ `structure.allowed_new_file_roots` = `["erp_ai", "docs", ".github"]`:**
```
erp_ai/tests/test_doctype_descriptions.py  -> erp_ai   (khớp)
erp_ai/ticket_panel.py                     -> erp_ai   (khớp)
erp_ai/tests/test_ticket_panel.py          -> erp_ai   (khớp)
```
**Đối chiếu `protected_paths` = `[".env", ".env.*", "**/*.pem", "**/*.key", "license.txt"]`:** không đường nào (11/11) tên `.env*`, đuôi `.pem`/`.key` hay `license.txt` → **0 in protected_paths**. Tên test theo `naming.test_file` (`test_{name}.py`); test đặt cạnh mã hoặc ở `erp_ai/tests/` như hiện có (`structure.tests = colocated`).

## 8. Test plan
Lệnh chạy: `cmd.test_one` với `{file}` là tệp test; toàn bộ: `cmd.test`; migrate: `cmd.migrate`. Phía trang không có `cmd.test_js` → luật tĩnh Python + bước tay J1 (dưới bảng). Test đổi người dùng bằng `frappe.set_user` trong test (cấm chỉ trong module ngăn). Gateway dùng `erp_ai/test_utils.py::FakeGateway`; phiếu/agent dùng `helpdesk/test_utils.py` (`make_ticket`, `create_agent`).

**A. `erp_ai/tests/test_doctype_descriptions.py` (mới)**
| Tiêu chí | Test | Loại | Biên / lỗi |
|---|---|---|---|
| AC-1 | `test_every_visible_field_has_description` | unit | Mô tả chỉ có khoảng trắng tính là thiếu; in `DocType.fieldname` thiếu; khẳng định đếm 22/18/31 |
| AC-2, NFR-1 | `test_descriptions_at_most_400_chars` | unit | Đúng 400 đạt, 401 đỏ (đo `len` sau `strip`) |
| AC-2 | `test_required_phrases_present` | unit | `permission_level` có L0/L1/L2/L3; 4 `price_*` có "USD" và "triệu token"; `excluded_teams`, `alert_recipients` có "mỗi dòng"; Credential `budget_month_usd` có "0" và "không giới hạn" |
| AC-2 | `test_read_only_fields_say_system_writes` | unit | Mọi field `read_only = 1` có "Hệ thống tự ghi" và "không sửa được" |
| AC-3 | `test_section_breaks_labelled_in_vietnamese` | unit | ≥ 2 Section Break mỗi DocType; 0 label rỗng; label có ít nhất một ký tự không phải ASCII |
| AC-4 | `test_descriptions_have_no_sensitive_data` | unit | Không `sk-`, không `miyano`; email chỉ khớp `congty.vn`/`example.com` |
| AC-4 | `test_descriptions_contain_no_stored_setting_values` | integration (đọc site) | Giá trị chuỗi đang lưu của ERP AI Setting, tách theo dòng, ≥ 4 ký tự, không xuất hiện trong mô tả nào |
| AC-5 | `test_section_breaks_carry_only_label` | unit | Section Break không có thuộc tính nào ngoài `fieldname`, `fieldtype`, `label` |
| AC-5 | `test_skipped_fields_still_follows_value_after` | unit | Kèm test hiện có `erp_ai/erp_ai_agent/doctype/erp_ai_log/test_erp_ai_log.py` (không sửa) |
| AC-5, NFR-2 | QA: script chỉ đọc so JSON với `team/BUG-002` + `cmd.test` + `cmd.migrate` + so ERP AI Setting trước/sau | acceptance | 0 khác biệt ngoài `description`, Section Break, `modified` |

**B. `erp_ai/tests/test_ticket_panel.py` (mới)**
| Tiêu chí | Test | Loại | Biên / lỗi |
|---|---|---|---|
| ADR-010 QĐ 2 (Amendment 1) | `test_methods_whitelisted_post_without_guest` | unit | Cả hai trong `frappe.whitelisted`, `allowed_http_methods == ["POST"]` (đúng một phần tử, không `"GET"`), không trong `frappe.guest_methods` |
| AC-7 | `test_read_returns_ai_fields_as_stored_text` | integration | Hint HTML nhiều dòng → chữ giữ ngắt dòng; Datetime đã định dạng |
| AC-7 | `test_read_empty_ai_fields_are_null` | integration | Phiếu chưa có giá trị → 4 `text` là `null` |
| AC-7 | `test_read_ai_fields_use_hd_ticket_labels` | integration | 4 label đúng chữ của `install.py`, đúng thứ tự |
| AC-8 | `test_thread_selects_b5_comments_in_creation_order` | integration | Gieo 3 comment người có từ khóa (1 viết hoa khác), 2 không từ khóa, 2 của `AGENT_USER`, 1 có từ khóa ở phiếu khác → đúng 5 tin, cũ → mới |
| AC-8 | `test_thread_ignores_non_comment_types` | integration | Comment `Info`/`Like` có từ khóa không hiện |
| AC-8 | `test_thread_marks_bot_messages` | integration | `is_bot` đúng; không có khóa email |
| AC-9 | `test_send_empty_or_whitespace_is_rejected` | integration | `""`, `"   \n"` → `ValidationError`, 0 Comment |
| AC-9 | `test_send_length_boundary` | integration | 2000 ký tự → OK; 2001 → `ValidationError`, 0 Comment |
| AC-9 | `test_send_appends_configured_keyword_when_missing` | integration | Từ khóa gieo lạ (không phải `@ai`) → nội dung lưu có từ khóa ở cuối, qua `contains_keyword` |
| AC-9 | `test_send_keeps_text_when_keyword_present_other_case` | integration | Chữ có từ khóa viết hoa khác → không thêm lần nữa |
| AC-9, ADR-010 Ràng buộc (Amendment 1) | `test_send_stored_content_passes_contains_keyword` | integration | Từ khóa thường gieo lạ (không có `<`, `>`, `&`); `subTest` tin chưa có từ khóa và tin đã có từ khóa (viết hoa khác): đọc lại `Comment.content` **từ DB** (`frappe.db.get_value("Comment", name, "content")`, không dùng biến trong bộ nhớ) → `policy.contains_keyword` True *(Amendment 1)* |
| AC-9, AC-12 | `test_send_escapes_html` | integration | Gõ `<b>x</b> & y` → nội dung lưu không có thẻ `b`; `get_panel_data` trả đúng chữ `<b>x</b> & y` |
| AC-9 | `test_send_multiline_keeps_line_breaks` | integration | 2 dòng → đọc lại có `\n` |
| AC-9 | `test_send_creates_one_comment_owned_by_sender` | integration | Đúng +1 Comment, `comment_type = "Comment"`, `owner` = người gửi ≠ `AGENT_USER` |
| AC-9 | `test_send_with_empty_keyword_creates_comment_without_keyword` | integration | Từ khóa rỗng → 1 Comment, không job |
| AC-9, ADR-010 QĐ 7 + Ràng buộc (Amendment 1) | `test_send_keyword_with_special_chars_rejected` | integration | `subTest` từ khóa `a&b` và từ khóa có `<` (ví dụ `a<b`): `frappe.ValidationError`; 0 `Comment` mới; `HD Ticket.new_comment` không được gọi (patch đếm lời gọi, chứng minh kiểm **trước** `new_comment`); chuỗi lỗi (`str(exc)` và `frappe.message_log`) **không chứa** từ khóa *(Amendment 1; bản trước: chỉ `a&b`, chỉ kiểm lỗi và 0 Comment)* |
| AC-10, NFR-4 | `test_send_matches_comments_box_in_every_gate_branch` | integration | `subTest` 9 nhánh (agent tắt; L0; nhóm loại trừ; `ai_opt_out`; đủ lượt/ngày; vượt ngân sách → L1; `ERP AI Instructor`; người được giao; người còn lại). Mỗi nhánh so đường ngăn với `ticket.new_comment(<cùng nội dung>)`: quyết định xếp hàng + lý do bỏ qua, bản ghi ERP AI Log (`entry_type`, `stop_reason`, `instructor`), bộ tool, số lời gọi `FakeGateway`; nhóm loại trừ và opt-out: 0 lời gọi. Bắt job xếp hàng như `erp_ai/tests/test_handlers.py` rồi chạy đồng bộ. Cả 9 nhánh dùng từ khóa thường |
| AC-12, NFR-5 | `test_read_strips_xss_payloads_to_text` | integration | 3 mẫu XSS của spec trong comment bot và trong hint → kết quả không còn `<img`, `<script`, `<a `, `onerror`, `javascript:` ở dạng thẻ |
| AC-13, NFR-5 | `test_read_denied_for_non_agents_and_guest` | integration | HD Contact, Website User, Guest → `PermissionError`, không dữ liệu |
| AC-13 | `test_read_denied_for_agent_without_ticket_read` | integration | User có HD Agent `is_active = 1` nhưng đã gỡ role Agent/Agent Manager; khẳng định tiền đề (`is_agent()` True, `has_permission` False) rồi → `PermissionError` |
| AC-13 | `test_inactive_hd_agent_denied` | integration | HD Agent `is_active = 0` → `PermissionError` ở cả hai |
| AC-13 | `test_send_denied_for_same_accounts_creates_nothing` | integration | Các tài khoản trên → `PermissionError`, 0 Comment |
| AC-13 | `test_send_denied_for_agent_user` | integration | Phiên `AGENT_USER` → `PermissionError`, 0 Comment |
| AC-14, NFR-4 | `test_read_writes_nothing_and_calls_no_gateway` | integration | Dưới phiên agent thường (không Administrator). Đếm `Comment`, `HD Ticket.modified`, `ERP AI Log`, `ToDo`, `Task` trước/sau 3 lần gọi đọc: không đổi; `FakeGateway` 0 lời gọi; **`frappe.db.transaction_writes` đọc ngay trước và ngay sau mỗi lần gọi `get_panel_data` → bằng nhau** (POST được Frappe commit, nên đọc phải phát 0 câu `INSERT`/`UPDATE`/`DELETE`, kể cả lệnh ghi phụ của hàm được gọi như `_seen`/View Log; `frappe/database/database.py:437-438`) *(Amendment 1)* |
| AC-14, B-8 | `test_read_never_returns_keyword_or_settings` | integration | Gieo từ khóa lạ và giá trị Setting lạ; chuỗi JSON kết quả không chứa chúng (trừ trong nội dung comment đã lưu) |
| STD-OPS-5 | `test_send_logs_without_content_or_email` | unit | Dòng log có `comment=`, không có nội dung tin hay email; dòng `keyword_not_storable` không có giá trị từ khóa |

**C. `erp_ai/tests/test_architecture.py` (sửa/thêm) và `erp_ai/agent/test_policy.py`**
| Tiêu chí | Test | Loại | Biên / lỗi |
|---|---|---|---|
| AC-12, AC-14, NFR-5 | `test_status_script_static_rules` (sửa theo ADR-009 Ràng buộc: chữ ký `function setupForm({ doc, call, router })`; bỏ đúng `\bcall\b`; thêm `DOMParser`, `createContextualFragment`, `setInterval`, `MutationObserver`, `.off(`, `removeListener`, `removeAllListeners`, `createElement("a"`, `createElement("img"`, `createElement("iframe"`, `createElement("script"`, `.src =`, `.href =`, `innerText =`; REQUIRED thêm `"docinfo_update"`, `"doc_update"`) | static | Mọi chuỗi cấm cũ còn nguyên (reviewer đối chiếu STD-TEST-5) |
| ADR-009 | `test_status_script_calls_only_panel_methods` | static | Mọi `call(` có literal đầu; tập literal == `PANEL_METHODS`; mỗi đường trỏ tới hàm `@frappe.whitelist` |
| ADR-009 | `test_status_script_queries_only_app_root` | static | `querySelector`/`getElementById`/`getElementsBy*` chỉ với `#app` |
| ADR-009 | `test_status_script_has_one_window_state` | static | Đúng một định danh `window.__erpAi…` |
| ADR-009, AC-11 (d) | `test_status_script_socket_events_only_in_once_block` | static | Mọi `socket.on(` trong khối `if (state.socket !== socket)`; tên sự kiện ⊆ {hằng ADR-008, `docinfo_update`, `doc_update`, `connect`, `disconnect`} |
| ADR-010 | `test_whitelisted_methods_declare_http_methods_without_guest` | static | Mọi `@frappe.whitelist` trong `erp_ai/**` có `methods=`, không `allow_guest` |
| ADR-010 (Amendment 1) | `test_ticket_panel_has_exactly_two_whitelisted_methods` | static | Đúng 2, tập đường == `PANEL_METHODS`; cả hai `methods=["POST"]` đúng một phần tử, không có `"GET"` |
| ADR-010 (Amendment 1) | `test_ticket_panel_forbidden_calls` | static | Không `ignore_permissions`, `set_user`, `get_all`, `db.get_values`, `db.sql`, `set_value`, `db_set`, `.insert(`, `.save(`, `delete`, `commit`, `rollback`, `frappe.cache`, `publish_realtime`; đúng 1 `.new_comment(`, nằm trong `send_message`; thân `get_panel_data` không có `.new_comment(` |
| ADR-010, AC-10 | `test_ticket_panel_does_not_evaluate_agent_gates` | static | Không `is_enabled`, `can_send_ticket`, `effective_level`, `runs_today`, `enqueue`, `permission_level`, `excluded_teams`, `ai_opt_out` |
| ADR-001 | `test_layer_imports` (hiện có, thêm dòng `LAYER_RULES` cho `erp_ai.ticket_panel` và chiều ngược từ `erp_ai.agent`/`erp_ai.gateway`) | static | Scanner tự kiểm: `test_layer_imports_catches_each_forbidden_direction` (hiện có) phủ dòng mới |
| ADR-009 | `TestScannersCatchViolations::test_call_allow_list_scanner_catches_unlisted_method`, `::test_socket_on_scanner_catches_outside_once_block` | static | Mẫu vi phạm phải bị bắt |
| AC-9 | `erp_ai/agent/test_policy.py::test_get_trigger_keyword_matches_contains_keyword` | unit | Từ khóa rỗng → `""`, `contains_keyword` False |

**D. Không lùi (AC-15)** — `cmd.test` toàn bộ xanh, không sửa assertion nào ngoài dòng ADR-009 cho phép; đặc biệt `erp_ai/tests/test_install.py::test_status_script_installed_once_matching_repo_file`, `::test_status_script_reset_when_changed_on_site`, `::test_status_script_served_to_agent_page_only`, `erp_ai/tests/test_handlers.py::TestCommentHandler`, `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py`, `erp_ai/gateway/test_gateway.py`, các test hiện có của `contains_keyword` trong `erp_ai/agent/test_policy.py` (không sửa); `cmd.migrate` OK; ERP AI Setting trước = sau; AC-1..AC-5 (bảng A) vẫn đạt; `git diff --stat` từ nhánh nền không có JSON DocType mới (AC-14). Reviewer đối chiếu diff `erp_ai/agent/policy.py`: chỉ thêm `get_trigger_keyword`, thân `contains_keyword` không đổi *(Amendment 1)*.

**J1 — bước tay trên `miyano` (desktop, sau bàn giao; ghi vào `acceptance.md`):**
1. **AC-6:** Agent mở `/helpdesk/tickets/<id>` → 1 lần bấm "Trao đổi với bot" → thấy tiêu đề ngăn; gõ câu hỏi + Enter → tin hiện. Ghi "P2", số lần bấm. Thu hẹp < 640 px / mở bản di động → không có action, không lỗi console. Các tab Activity/Emails/Comments/Analytics chạy như cũ. Dán `git -C ../helpdesk status --porcelain` (0 dòng do FEAT-003).
2. **AC-7:** 1 phiếu đủ 4 giá trị, 1 phiếu chưa có → đối chiếu với thanh bên; mục trống hiện "Chưa có"; không có ô sửa.
3. **AC-8, AC-9 (phần tay):** dữ liệu gieo như test AC-8 → đúng 5 tin, tin bot có nhãn "Bot"; dòng hướng dẫn B-8 hiện. Gửi rỗng → thông báo; gửi `<b>x</b>` → hiện đúng chữ ở ngăn và ở tab Comments; ngắt mạng rồi gửi → thông báo thất bại, chữ còn.
4. **AC-11 (a)–(g), NFR-3:** hai phiên (A, B), mức L1, đồng hồ bấm giờ: (a) chỉ báo trong ngăn; (b) trả lời ≤ 10 s; (c) chỉ báo mất ≤ 10 s, và tự mất sau thời hạn FEAT-002 khi không có tín hiệu kết thúc; (d) chỉ một chỉ báo trên cả trang (ngăn mở và đóng); (e) 4 mục AI đổi ≤ 10 s; (f) tin có từ khóa của phiên B hiện ≤ 10 s ở phiên A; (g) chuyển sang phiếu Q → không có tin/chỉ báo của P.
5. **AC-12:** dữ liệu gieo XSS → hiện dạng chữ, console `window.__erp_ai_xss` là `undefined`, không có `img`/`script`/`a` mới trong ngăn.
6. **AC-13 (a):** HD Contact mở `/helpdesk/my-tickets/<id>` → không có action, ngăn, 4 mục AI hay luồng.
7. **AC-15 / FEAT-002 AC-10 (h)(i):** ngăn đóng → chỉ báo ở vị trí FEAT-002 chạy như cũ; timeline Helpdesk vẫn tự cập nhật khi có comment mới (h); một lần chạy chỉ một chỉ báo (i).

**Đối chiếu danh sách tiêu chí:**
- Spec: AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15; NFR-1, NFR-2, NFR-3, NFR-4, NFR-5.
- Test plan: AC-1, AC-2, AC-3, AC-4, AC-5 (A); AC-6 (J1.1); AC-7, AC-8, AC-9, AC-10 (B, J1.2–3); AC-11 (J1.4, C `socket_events_only_in_once_block`); AC-12, AC-13, AC-14 (B, C, J1.5–6); AC-15 (D, J1.7); NFR-1 (A), NFR-2 (A/QA, D), NFR-3 (J1.4), NFR-4 (B AC-10/AC-14), NFR-5 (B, C, J1.5). Khớp 15/15 AC, 5/5 NFR.
- AC chỉ kiểm được bằng tay ở trình duyệt: AC-6, AC-11 (và phần tay của AC-7, AC-8, AC-9, AC-12, AC-13 (a)) — vì không có `cmd.test_js`, `ui: false` (spec DoD phần 2).

## Assumptions decided by the team
- **D-1. Độ dài tối đa 2000 ký tự.** Vì sao: đủ cho một câu hỏi dài, giữ prompt và comment gọn; spec để designer chọn (B-6, ADR-010 QĐ 7). Thay thế: 1000; 5000. Sai thì: đổi `PANEL_MAX_MESSAGE_CHARS` và chữ thông báo, test biên đi theo.
- **D-2. Từ khóa chèn ở cuối tin, cách một dấu cách.** Vì sao: chữ người gõ đứng đầu, đọc tự nhiên ở tab Comments. Thay thế: đầu tin. Sai thì: đổi một dòng trong `send_message`.
- **D-3. Không giới hạn tần suất gửi.** Lý do ở 3.2. Thay thế: `frappe.rate_limiter.rate_limit`. Sai thì: thêm decorator, kiểm lại AC-10.
- **D-4. Method đọc là POST** — **đã quyết** theo ADR-010 Amendment 1 (Quyết định 2): `get_panel_data` dùng `methods=["POST"]`, vì `call` của frappe-ui luôn gửi POST, và POST còn được Frappe kiểm CSRF. Tính chỉ-đọc được bảo đảm bằng luật tĩnh (mục 8 C) và test, gồm `transaction_writes` không tăng (mục 8 B, AC-14). Hoàn tác: theo ADR-010 Amendment 1 C-1. *(Bản trước: "chờ architect".)*
- **D-5. Từ khóa có `<`, `>`, `&` → từ chối gửi** — **đã quyết** theo ADR-010 Amendment 1 (Quyết định 7): kiểm `contains_keyword` trên dạng sẽ lưu, trước `new_comment`; không qua → `ValidationError`, 0 comment, thông báo không lộ từ khóa; `policy.contains_keyword` không đổi. *(Bản trước: "chờ architect".)*
- **D-6. Không tái dùng `authority.fetch_ticket_comments`.** Vì sao: dùng `get_list` trên `Comment` (Agent không có quyền), giới hạn 50, thuộc Lõi agent; ADR-010 QĐ 4 đòi đường timeline có kiểm quyền. Thay thế: thêm hàm đọc vào `authority.py`. Sai thì: đổi nguồn đọc trong `get_panel_data`, test AC-8 giữ nguyên.
- **D-7. Nhãn 4 mục AI lấy từ meta ở server**, không viết lại trong `.js`. Vì sao: một nguồn (`install.py`). Thay thế: viết cứng ở `.js`. Sai thì: thêm 4 chuỗi vào bảng 3.3.
- **D-8. Section Break không có mô tả; label có dấu tiếng Việt; tên `section_<chủ đề>`.** Vì sao: AC-3 cho tùy chọn; test kiểm được. Sai thì: thêm mô tả, không ảnh hưởng AC-5.
- **D-9. "Dạng sẽ được lưu" = gọi đúng `sanitize_html(..., always_sanitize=True)` mà `Comment.validate` dùng**, không tự viết bộ escape tương đương (ADR-010 Hệ quả "Phải làm thêm"). Vì sao: một nguồn sự thật với Frappe; nâng Frappe đổi cách sanitize thì kiểm vẫn khớp. Thay thế: escape tương đương tự viết. Sai thì: đổi một dòng ở 3.2 bước 4; test `test_send_stored_content_passes_contains_keyword` (đọc lại từ DB) bắt lệch. *(Amendment 1.)*
- **D-10. Thông báo khi từ khóa không dùng được hướng về quản trị viên**, không khuyên dùng tab Comments và không nhắc giá trị từ khóa (B-8). Vì sao: ô Comments cũng không kích hoạt được bot với từ khóa đó (ADR-010 Amendment 1 C-2). Sai thì: đổi một chuỗi ở bảng lỗi 3.2. *(Amendment 1.)*
- Câu hỏi nghiệp vụ: 0.
