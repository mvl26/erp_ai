Feature: FEAT-003
Stage: plan
Author-agent: tech-lead
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Tasks FEAT-003

Mỗi task 2–5 phút. Hai task chung file thì phụ thuộc nhau. Đánh dấu `BLOCKED: <lý do>` cuối dòng khi bị chặn.
`cmd.test_one` = lệnh của profile với `{file}` là file ở `test:`. Mọi task: viết test đỏ trước (STD-TEST-1), chỉ sửa trong `files:`. Tên hàm, hằng, chuỗi chính xác: `plan.md` mục Ràng buộc chung và `design.md` mục 3.

Tiến độ: BASE ghi ở đây trước mỗi lần gọi dev.
- BASE T1=3dd7358 · BASE T3=3dd7358

## Phần 2, walking skeleton (T1 rồi T2; không task phần 2 nào khác bắt đầu trước khi review T2 là approve)

- [ ] T1 — Skeleton server: `get_panel_data` trả 4 mục AI qua cổng quyền — files: erp_ai/constants.py, erp_ai/ticket_panel.py, erp_ai/tests/test_ticket_panel.py, erp_ai/tests/test_architecture.py — test: erp_ai/tests/test_ticket_panel.py — depends: —
  - Criterion: AC-7 (4 mục đúng label/giá trị/null), AC-13 (đọc: từ chối non-agent, Guest, Agent không quyền đọc phiếu, HD Agent `is_active = 0`, phiếu không tồn tại), ADR-010 QĐ 2 (POST, không guest)
  - Receives: `AGENT_USER` (hiện có), `helpdesk.utils.is_agent`
  - Returns: `PANEL_METHODS`, `PANEL_MAX_MESSAGE_CHARS` (cả hai trong constants.py, đủ 2 chuỗi method ngay từ đây); `get_panel_data(ticket: str) -> dict` trả `{"ticket", "ai_fields": [4 phần tử], "messages": []}`; `_require_panel_access(ticket: str, *, forbid_agent_user: bool = False) -> None`; dòng `LAYER_RULES` cho `erp_ai.ticket_panel` (tầng Cửa vào)
  - Expect: `cmd.test_one` với erp_ai/tests/test_ticket_panel.py: `test_methods_whitelisted_post_without_guest` (chỉ kiểm `get_panel_data` ở task này), `test_read_returns_ai_fields_as_stored_text`, `test_read_empty_ai_fields_are_null`, `test_read_ai_fields_use_hd_ticket_labels`, `test_read_denied_for_non_agents_and_guest`, `test_read_denied_for_agent_without_ticket_read`, `test_inactive_hd_agent_denied` đạt; `test_architecture::test_layer_imports` vẫn xanh
- [ ] T2 — Skeleton trang: action "Trao đổi với bot" mở ngăn tối thiểu hiện 4 mục AI — files: erp_ai/public/js/agent_status_indicator.js, erp_ai/tests/test_architecture.py — test: erp_ai/tests/test_architecture.py — depends: T1
  - Criterion: AC-6 (≤ 1 lần bấm, tiêu đề ngăn), AC-7 (chữ "Chưa có"), AC-12 (chỉ `textContent`)
  - Receives: `PANEL_METHODS` (T1), khóa action `label`/`onClick` (đối chiếu `TicketHeader.vue:24-30`)
  - Returns: `function setupForm({ doc, call, router })` trả `{ actions: [{ label: "Trao đổi với bot", onClick }] }` (như cũ `{ actions: [] }` khi không socket hoặc `innerWidth < 640`); `state.call`; `togglePanel()`; `reload()` bản tối thiểu (gọi `state.call("erp_ai.ticket_panel.get_panel_data", { ticket })`, vẽ `ai_fields`); trong test_architecture.py: sửa `STATUS_SCRIPT_FORBIDDEN` (bỏ đúng `\bcall\b`, thêm các chuỗi cấm ADR-009 ở design mục 8 C dòng đầu) và ghim chữ ký mới; mọi chuỗi cấm cũ còn nguyên
  - Expect: `cmd.test_one` với erp_ai/tests/test_architecture.py → `test_status_script_static_rules` đạt, `erp_ai/tests/test_install.py` không đỏ (không sửa assertion). Bước tay J1 để sau

## Phần 1, mô tả field (độc lập với phần 2; đi song song được)

- [ ] T3 — Mô tả và nhóm cho ERP AI Setting (22 field, 7 Section Break) — files: erp_ai/tests/test_doctype_descriptions.py, erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json — test: erp_ai/tests/test_doctype_descriptions.py — depends: —
  - Criterion: AC-1, AC-2, AC-3, AC-4, AC-5, NFR-1 (phạm vi ERP AI Setting)
  - Receives: bảng "Dữ liệu" của spec (dòng 56-80), bảng chia nhóm design mục 2.1
  - Returns: file test mới có hằng `DOCTYPE_CONFIG` (khóa theo tên DocType: số field kỳ vọng, cụm bắt buộc, tên Section Break) và các test `test_every_visible_field_has_description`, `test_descriptions_at_most_400_chars`, `test_required_phrases_present`, `test_read_only_fields_say_system_writes`, `test_section_breaks_labelled_in_vietnamese`, `test_descriptions_have_no_sensitive_data`, `test_descriptions_contain_no_stored_setting_values`, `test_section_breaks_carry_only_label` lặp bằng `subTest` trên `DOCTYPE_CONFIG`; T3 chỉ đăng ký ERP AI Setting
  - Expect: đỏ (trước): thiếu 21/22 mô tả; xanh (sau): `cmd.test_one` OK; `test_erp_ai_setting.py` hiện có xanh
- [ ] T4 — Mô tả và nhóm cho ERP AI Credential (18 field, 4 Section Break) — files: erp_ai/tests/test_doctype_descriptions.py, erp_ai/erp_ai_agent/doctype/erp_ai_credential/erp_ai_credential.json — test: erp_ai/tests/test_doctype_descriptions.py — depends: T3
  - Criterion: AC-1..AC-5, NFR-1 (phạm vi ERP AI Credential; `budget_month_usd` có "0" và "không giới hạn"; `api_key` không có `sk-`)
  - Receives: `DOCTYPE_CONFIG` (T3)
  - Returns: mục mới của `DOCTYPE_CONFIG` cho ERP AI Credential
  - Expect: đỏ rồi xanh với `cmd.test_one`; `test_erp_ai_credential.py` hiện có xanh
- [ ] T5 — Mô tả và nhóm cho ERP AI Log (31 field, 6 Section Break) — files: erp_ai/tests/test_doctype_descriptions.py, erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json — test: erp_ai/tests/test_doctype_descriptions.py — depends: T4
  - Criterion: AC-1..AC-5, NFR-1 (phạm vi ERP AI Log; `skipped_fields` ngay sau `value_after`, không Break giữa hai field; mọi field có "Hệ thống tự ghi" và "không sửa được")
  - Receives: `DOCTYPE_CONFIG` (T4)
  - Returns: mục mới của `DOCTYPE_CONFIG` cho ERP AI Log; test `test_skipped_fields_still_follows_value_after`
  - Expect: đỏ rồi xanh với `cmd.test_one`; `test_erp_ai_log.py` và `test_gateway.py` (chống lộ khóa) xanh

## Phần 2, server và policy

- [ ] T6 — `get_trigger_keyword()` trong policy — files: erp_ai/agent/policy.py, erp_ai/agent/test_policy.py — test: erp_ai/agent/test_policy.py — depends: —
  - Criterion: AC-9, AC-15 (`contains_keyword` không sửa một dòng)
  - Receives: cách `contains_keyword` đọc `trigger_keyword` (`policy.py:41-45`)
  - Returns: `get_trigger_keyword() -> str` (chỉ đọc `trigger_keyword`; rỗng → `""`)
  - Expect: `cmd.test_one` với erp_ai/agent/test_policy.py → `test_get_trigger_keyword_matches_contains_keyword` đạt; test cũ của `contains_keyword` không đổi
- [ ] T7 — `get_panel_data` trả luồng tin theo B-5 — files: erp_ai/ticket_panel.py, erp_ai/tests/test_ticket_panel.py — test: erp_ai/tests/test_ticket_panel.py — depends: T1
  - Criterion: AC-8, AC-12 (phía server)
  - Receives: `get_activity_timeline` (`frappe/desk/form/activity.py`, khóa mục dev đọc ở dòng 254-271,331-337), `policy.contains_keyword`, `AGENT_USER`, `html_to_plain_text`
  - Returns: `messages`: danh sách `{name, author, is_bot, created_at, text}`, cũ → mới; không khóa email
  - Expect: `cmd.test_one` → `test_thread_selects_b5_comments_in_creation_order` (5 tin), `test_thread_ignores_non_comment_types`, `test_thread_marks_bot_messages`, `test_read_strips_xss_payloads_to_text` đạt
- [ ] T8 — Đọc chỉ-đọc: log quan sát và test không ghi — files: erp_ai/ticket_panel.py, erp_ai/tests/test_ticket_panel.py — test: erp_ai/tests/test_ticket_panel.py — depends: T7
  - Criterion: AC-14, NFR-4, STD-OPS-5 (phần đọc)
  - Receives: `get_panel_data` đầy đủ (T7), `LOGGER_NAME` (như `handlers.py:24`)
  - Returns: log `debug` "erp_ai panel read ticket=<tên> messages=<n>" và `info` "erp_ai panel denied method=get ticket=<tên> reason=<not_agent|no_read>"
  - Expect: `cmd.test_one` → `test_read_writes_nothing_and_calls_no_gateway` (gồm `frappe.db.transaction_writes` bằng nhau trước/sau, phiên agent thường), `test_read_never_returns_keyword_or_settings`, test log đọc/từ chối (không nội dung, không email) đạt
- [ ] T9 — `send_message`: kiểm đầu vào, dựng nội dung, gọi `new_comment` — files: erp_ai/ticket_panel.py, erp_ai/tests/test_ticket_panel.py — test: erp_ai/tests/test_ticket_panel.py — depends: T6, T8
  - Criterion: AC-9 (rỗng, biên 2000, thêm từ khóa cuối tin, từ khóa viết hoa khác, escape HTML, ngắt dòng, đúng 1 Comment `owner` = người gửi, từ khóa rỗng), AC-13 (gửi: non-agent, Guest, không quyền đọc, `AGENT_USER` → `PermissionError`, 0 Comment)
  - Receives: `policy.get_trigger_keyword`, `policy.contains_keyword` (T6), `_require_panel_access(..., forbid_agent_user=True)` (T1), `PANEL_MAX_MESSAGE_CHARS`
  - Returns: `send_message(ticket: str, text: str) -> dict` (`@frappe.whitelist(methods=["POST"])`) trả `{"comment": <tên>}`; đúng 1 lời gọi `frappe.get_doc("HD Ticket", ticket).new_comment(content)`; chưa có bước sanitize (T10)
  - Expect: `cmd.test_one` → `test_methods_whitelisted_post_without_guest` (nay cả 2 method), `test_send_empty_or_whitespace_is_rejected`, `test_send_length_boundary`, `test_send_appends_configured_keyword_when_missing`, `test_send_keeps_text_when_keyword_present_other_case`, `test_send_escapes_html`, `test_send_multiline_keeps_line_breaks`, `test_send_creates_one_comment_owned_by_sender`, `test_send_with_empty_keyword_creates_comment_without_keyword`, `test_send_denied_for_same_accounts_creates_nothing`, `test_send_denied_for_agent_user` đạt
- [ ] T10 — `send_message`: kiểm từ khóa trên dạng sẽ lưu và log gửi — files: erp_ai/ticket_panel.py, erp_ai/tests/test_ticket_panel.py — test: erp_ai/tests/test_ticket_panel.py — depends: T9
  - Criterion: AC-9 (bất biến: nội dung lưu phải vượt qua `contains_keyword`), ADR-010 Amendment 1 (QĐ 7), STD-OPS-5 (phần gửi)
  - Receives: `frappe.utils.html_utils.sanitize_html(content, always_sanitize=True)` (đối chiếu tham số với `frappe/core/doctype/comment/comment.py:69-74`, không tự viết bộ escape)
  - Returns: từ khóa không rỗng mà `contains_keyword(stored)` False → `frappe.ValidationError` (thông báo của design 3.2, không chứa từ khóa), không gọi `new_comment`; log `info` "erp_ai panel send ticket=… comment=… keyword_added=…", "erp_ai panel denied method=send … reason=<not_agent|no_read|agent_user>", "erp_ai panel send rejected ticket=… reason=keyword_not_storable"
  - Expect: `cmd.test_one` → `test_send_stored_content_passes_contains_keyword` (đọc lại từ DB bằng `frappe.db.get_value`), `test_send_keyword_with_special_chars_rejected` (`a&b`, `a<b`; patch đếm `new_comment` = 0; lỗi không chứa từ khóa), `test_send_logs_without_content_or_email` đạt
- [ ] T11 — Test so đường ngăn với ô Comments qua 9 nhánh chốt — files: erp_ai/tests/test_ticket_panel.py — test: erp_ai/tests/test_ticket_panel.py — depends: T10
  - Criterion: AC-10, NFR-4
  - Receives: `send_message` (T10), `ticket.new_comment`, `FakeGateway`, cách bắt job như `erp_ai/tests/test_handlers.py`
  - Returns: `test_send_matches_comments_box_in_every_gate_branch` (9 `subTest`: agent tắt; L0; nhóm loại trừ; `ai_opt_out`; đủ lượt/ngày; vượt ngân sách; `ERP AI Instructor`; người được giao; người còn lại; từ khóa thường; nhóm loại trừ và opt-out: 0 lời gọi gateway). Không thêm mã sản xuất; bằng chứng đỏ-đúng-lý-do: dev dán kết quả khi tạm làm đường ngăn lệch (đột biến, không commit)
  - Expect: `cmd.test_one` → 9 nhánh đạt

## Phần 2, trang (JS; không có `cmd.test_js`, kiểm bằng luật tĩnh và bước tay J1)

- [ ] T12 — Ngăn đầy đủ: luồng tin, đóng/mở, chuyển chỉ báo, chống kết quả cũ — files: erp_ai/public/js/agent_status_indicator.js, erp_ai/tests/test_architecture.py — test: erp_ai/tests/test_architecture.py — depends: T2, T7
  - Criterion: AC-6 (nút Đóng, một chỉ báo), AC-7, AC-8 (nhãn "Bot", dòng hướng dẫn B-8, "Chưa có tin nào."), AC-11 (d)(g)
  - Receives: hợp đồng `messages` (T7), bảng chữ cố định design 3.3, F1 và `reload()` của design mục 4
  - Returns: `panel` = `{ el, open, slotEl, aiListEl, threadEl, errorEl, inputEl, sendEl, seq, sending }`; `togglePanel()` chuyển `state.el` vào `panel.slotEl` khi mở và trả về `document.body` khi đóng; `reload()` bỏ kết quả khi `seq`, `ticket` hoặc trạng thái mở đã đổi, lỗi → "Không tải được dữ liệu của khu vực. Hãy đóng rồi mở lại."; test_architecture.py: giữ các luật tĩnh xanh, thêm chuỗi vào `STATUS_SCRIPT_REQUIRED` chỉ khi có trong JS ở task này
  - Expect: `cmd.test_one` với erp_ai/tests/test_architecture.py đạt (không `innerHTML`, không số `600`, không `setInterval`)
- [ ] T13 — Ô nhập và gửi tin trong ngăn — files: erp_ai/public/js/agent_status_indicator.js, erp_ai/tests/test_architecture.py — test: erp_ai/tests/test_architecture.py — depends: T12
  - Criterion: AC-9 (rỗng/quá 2000 không gọi server; giữ chữ khi lỗi), AC-11 (g)
  - Receives: `panel.inputEl`, `panel.sendEl`, `reload()` (T12); chữ cố định design 3.3; F2 design mục 4
  - Returns: `submit()` (Enter không Shift và `event.isComposing` false, hoặc nút Gửi) gọi `state.call("erp_ai.ticket_panel.send_message", { ticket: state.ticket, text: value })`; `panel.sending` chặn bấm lặp; thành công xóa ô và `reload()`; lỗi hiện "Không gửi được tin. Chữ bạn gõ vẫn còn, hãy thử lại." và giữ chữ
  - Expect: `cmd.test_one` với erp_ai/tests/test_architecture.py đạt
- [ ] T14 — Cập nhật trực tiếp, đặt lại khi đổi phiếu, ẩn khi màn hẹp — files: erp_ai/public/js/agent_status_indicator.js, erp_ai/tests/test_architecture.py — test: erp_ai/tests/test_architecture.py — depends: T13
  - Criterion: AC-11 (a)(b)(c)(e)(f)(g), NFR-3, AC-14 (không storage, không polling)
  - Receives: `reload()`, `panel` (T12), F3 và F4 design mục 4; khóa payload `docinfo_update` (`comment.py:59-67,85-104`) và `doc_update` (`document.py:1370-1385`)
  - Returns: hàm có tên `onDocinfo`, `onDocUpdate` đăng ký bằng `socket.on` trong khối `if (state.socket !== socket)`; `connect` thêm `if (state.panel.open) reload()`; `reset()` mở rộng (đóng ngăn, trả chỉ báo, xóa nội dung và ô nhập, `panel.seq++`); `onResize` đóng ngăn khi `innerWidth < 640`, cờ `state.resizeBound`; `STATUS_SCRIPT_REQUIRED` thêm `"docinfo_update"`, `"doc_update"`
  - Expect: `cmd.test_one` với erp_ai/tests/test_architecture.py đạt; `erp_ai/tests/test_install.py` xanh

## Phần 2, luật tĩnh cuối

- [ ] T15 — Luật tĩnh cho module ngăn và `call` của trang — files: erp_ai/tests/test_architecture.py — test: erp_ai/tests/test_architecture.py — depends: T10, T14
  - Criterion: ADR-009, ADR-010 (Amendment 1), AC-12, AC-14, AC-15
  - Receives: `ticket_panel.py` (T10), `agent_status_indicator.js` (T14), `PANEL_METHODS` (T1)
  - Returns: `test_status_script_calls_only_panel_methods`, `test_status_script_queries_only_app_root`, `test_status_script_has_one_window_state`, `test_status_script_socket_events_only_in_once_block`, `test_whitelisted_methods_declare_http_methods_without_guest`, `test_ticket_panel_has_exactly_two_whitelisted_methods`, `test_ticket_panel_forbidden_calls`, `test_ticket_panel_does_not_evaluate_agent_gates`, mở rộng `LAYER_RULES` chiều ngược từ `erp_ai.agent`/`erp_ai.gateway`, và trong `TestScannersCatchViolations`: `test_call_allow_list_scanner_catches_unlisted_method`, `test_socket_on_scanner_catches_outside_once_block`
  - Expect: `cmd.test_one` với erp_ai/tests/test_architecture.py đạt, kể cả test bắt mẫu vi phạm
