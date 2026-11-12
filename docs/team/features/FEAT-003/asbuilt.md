Feature: FEAT-003
Stage: asbuilt
Author-agent: writer
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# As-Built FEAT-003 — Mô tả field cho 3 DocType ERP AI (phần 1) và khu vực "Hướng giải quyết & trao đổi với bot" (phần 2)

Người đọc: dev và người duyệt (`dev`). Verdict của acceptance: `accepted` (commit kiểm `7cb654f`, nhánh `team/FEAT-003`). G4 tắt (chế độ decide).

## 0. Nguồn so sánh

- Mã thật: `git diff 0051042 7cb654f -- erp_ai` (nền `team/BUG-002` = `0051042`): 11 file, +2572/-36. Đúng 11 touchpoint của design mục 7 (8 sửa, 3 mới), không file nào ngoài `erp_ai/`.
- **Lưu ý về `diff.patch`.** File `docs/team/features/FEAT-003/diff.patch` được tạo lại bằng `git diff 0051042 7cb654f -- erp_ai` (base `0051042`, đầu `7cb654f`; đã che email và khóa, 0 kết quả khớp còn lại), cùng khoảng với mọi so sánh dưới đây (`0051042..7cb654f`).
- Phạm vi đối chiếu: design mục 2.1, 3.1, 3.2, 5, 7 đọc đối chiếu trực tiếp với `erp_ai/ticket_panel.py`, `erp_ai/constants.py`, `erp_ai/agent/policy.py`, ba file JSON DocType (số Section Break), và một phần `agent_status_indicator.js` (ngưỡng, sự kiện, chuỗi chữ, Enter/`isComposing`). Phần bên trong JS còn lại (F1–F5 từng dòng) và nội dung 71 mô tả được xác nhận qua test tĩnh và đối chiếu AC-2 của qa trong `acceptance.md`; writer không đọc lại từng dòng.

## 1. Phần 1 — 71 mô tả field và nhóm (AC-1..AC-5, NFR-1, NFR-2)

| DocType | Field hiển thị có mô tả | Section Break | Mô tả dài nhất (≤ 400) |
|---|---|---|---|
| ERP AI Setting | 22/22 | 6 | 260 |
| ERP AI Credential | 18/18 | 4 | 182 |
| ERP AI Log | 31/31 | 6 | 331 |

(Số liệu của qa, `acceptance.md` AC-1, AC-3, NFR-1.) Chỉ `description` và Section Break được thêm; qa so JSON `0051042` với `7cb654f` cho cả 3 file: `nonbreak_field_diffs= []`, thứ tự field giữ nguyên (AC-5). Không có DocType hay field mới; `cmd.migrate` exit 0, ERP AI Setting trước = sau. Số Section Break của ERP AI Setting lệch design 1 nhóm: DEV-2.

## 2. Phần 2 — Khu vực "Trao đổi với bot" (AC-6..AC-15)

### 2.1 Vị trí: P2, và vì sao
- **Phương án dùng: P2.** Action "Trao đổi với bot" trên header trang phiếu; bấm 1 lần mở một ngăn gắn vào `document.body` (cố định, bên phải, `zIndex` 40). Tiêu đề ngăn "Hướng giải quyết & trao đổi với bot".
- **Vì sao không phải P1 (tab cạnh Activity/Emails/Comments):** research RQ-1 xác định các tab của `TicketActivityPanel.vue:78-110` viết cứng; thêm tab phải sửa Helpdesk (bị cấm, intake dòng 36) hoặc chèn vào cây DOM do Vue quản lý (dễ vỡ, `UNVERIFIED`). Điểm mở rộng có tài liệu là `actions` trả về từ `setupForm` (ADR-009 Bối cảnh, Quyết định 2). P2 là phương án khả thi đầu tiên theo thứ tự P1 → P3 của B-1.
- Chỉ desktop: `window.innerWidth < 640` (hằng `NARROW_SCREEN_PX = 640` trong `.js`, dòng 23) thì `setupForm` trả `actions: []`; đổi cỡ cửa sổ xuống dưới 640 thì ngăn đang mở bị đóng (ADR-009 Quyết định 3).
- Số lần bấm và xác nhận trên trình duyệt: chưa ghi, là bước J1.1 sau bàn giao (mục 6).

### 2.2 Hai method POST (`erp_ai/ticket_panel.py`, tầng Cửa vào, ADR-010)
Cả hai `@frappe.whitelist(methods=["POST"])`, không `allow_guest`. Allow-list `PANEL_METHODS` ở `erp_ai/constants.py`; `.js` chỉ gọi đúng hai chuỗi này qua `call`.

| Method | Làm gì | Ghi gì |
|---|---|---|
| `get_panel_data(ticket)` | Trả `{ticket, ai_fields (4 mục), messages}`: 4 field AI dưới quyền người dùng (`apply_fieldlevel_read_permissions`), luồng tin B-5 (comment của bot hoặc có từ khóa, cũ → mới) qua `get_activity_timeline`, chữ thuần (`html_to_plain_text`) | Không gì (0 câu ghi SQL, đo bằng `transaction_writes`, AC-14) |
| `send_message(ticket, text)` | Cổng quyền, từ chối `AGENT_USER`, kiểm độ dài (≤ 2000), escape HTML, giữ ngắt dòng bằng `<br>`, thêm từ khóa ở cuối nếu chưa có, kiểm từ khóa trên dạng sẽ lưu (`sanitize_html(..., always_sanitize=True)`), rồi đúng 1 lời gọi `HD Ticket.new_comment` | Đúng 1 core `Comment`, `owner` = người gửi |

Cổng chung `_require_panel_access`: `is_agent()`, rồi quyền đọc phiếu, rồi (chỉ gửi) không phải `AGENT_USER`. `erp_ai/agent/policy.py` chỉ thêm `get_trigger_keyword()` (4 dòng); `contains_keyword` không đổi (AC-15).

### 2.3 Cập nhật trực tiếp
`.js` đăng ký `docinfo_update` (khi `key === "comments"` và đúng phiếu) và `doc_update` (đúng phiếu), mỗi sự kiện một lần cho mỗi socket, trong khối `if (state.socket !== socket)` có sẵn; mỗi sự kiện gọi `reload()`. `reload()` bỏ qua khi ngăn đóng nên ngăn đóng thì 0 lời gọi; không polling, không `setInterval`. Chỉ báo FEAT-002 được chuyển vào ngăn khi mở và trả về góc dưới phải khi đóng, luôn một chỉ báo. Hành vi thời gian thực chưa ai quan sát (J1.4).

### 2.4 Ngăn không bao giờ làm gì
- Không ghi field nào (4 mục AI chỉ đọc), không sửa/xóa tin, không đính kèm, không nhắc tên.
- Không đọc hay trả `trigger_keyword`, bật/tắt, mức quyền, nhóm loại trừ, `ai_opt_out`, ngân sách (AC-14, `test_read_never_returns_keyword_or_settings`).
- Không tự xét chốt agent (`is_enabled`, `can_send_ticket`, `effective_level`, ...): mọi chốt chạy ở `comment_after_insert` và runner như ô Comments (AC-10, ADR-010 Quyết định 8). Ngăn không báo lý do bot không trả lời; chỉ có dòng hướng dẫn cố định.
- Không `ignore_permissions`, `set_user`, `get_all`, `db.sql`; không gọi gateway hay hàng đợi; không `localStorage`/`sessionStorage`/cookie; không `innerHTML`, `eval`, không tạo `a`/`img`/`iframe`/`script` (chỉ `textContent`; AC-12, ADR-009).
- Không hiện cho HD Contact, Website User, Guest, trang di động; không đổi mã Helpdesk/Frappe (AC-6, B-11).

## 3. Bảng đối chiếu design ↔ thực tế

| # | Mục design | Kết quả | Ghi chú |
|---|---|---|---|
| 1 | 2.1 Mô tả 71 field; 17 Section Break (7+4+6) | **lệch** | 71/71 mô tả khớp; Section Break thực tế 16 (6+4+6). DEV-2 |
| 2 | 2.2 Không dữ liệu mới | khớp | AC-14: `git diff --diff-filter=A -- '*.json'` rỗng |
| 3 | 3.1 `get_panel_data` (POST, 4 mục, B-5) | khớp | `ticket_panel.py:86-95`; trả `ticket`, `ai_fields`, `messages` |
| 4 | 3.1 Bảng lỗi | khớp một phần | Guest 403, non-agent/không quyền đọc `PermissionError`, `ticket` rỗng `ValidationError` khớp; `ticket` sai kiểu: DEV-1 |
| 5 | 3.2 `send_message` bước 1–5 | khớp | Thứ tự gate → AGENT_USER → text → dựng → sanitize → 1 `new_comment` (`ticket_panel.py:114-141`) |
| 6 | 3.2 Bảng lỗi, hàng `text` sai kiểu | **lệch** | DEV-1 |
| 7 | 3.2 bước 2 và 4: đọc từ khóa | lệch nhỏ | DEV-3 |
| 8 | 3.3 Chữ ký `setupForm({ doc, call, router })`, `actions`, ngưỡng 640, chữ cố định, Enter + `isComposing` | khớp | `agent_status_indicator.js`: `NARROW_SCREEN_PX` dòng 23, chuỗi chữ dòng 9-13, `keydown` dòng 206-208, `return { actions: [...] }` dòng 575-578 |
| 9 | 4 F3 Sự kiện `docinfo_update`, `doc_update`, resize | khớp | `.js:541-542`, `:573` |
| 10 | 5 Quyền, bảng tài khoản | khớp | AC-13: Guest `http=403`, `PermissionError`; đột biến M4/M4b bị test bắt |
| 11 | 5 Log (4 dòng) | khớp một phần | Có log `send`, `denied`, `keyword_not_storable`, `debug read`; không test nào kiểm dòng `denied method=send reason=no_read` (review-08 minor T10 (c)) |
| 12 | 6 Migration | khớp | `cmd.migrate` exit 0; ERP AI Setting và role ai.agent giống trước/sau; MD5 HD Form Script trên site = file repo |
| 13 | 7 Touchpoints 11 file | khớp | 11/11, 0 file ngoài; `install.py`, `handlers.py`, `runner.py` không đổi |
| 14 | 8 Test plan | khớp | `test_ticket_panel` 36 case, `test_architecture` 77, `test_doctype_descriptions` 10; 8/8 đột biến bị bắt |
| 15 | 8 D / AC-15 Không lùi | khớp | Một dòng `assertIn` đổi `function setupForm({ doc, router })` thành `({ doc, call, router })`, và bỏ `r"\bcall\b"` khỏi danh sách cấm (cả hai ADR-009 cho phép); `LAYER_RULES` thêm `erp_ai.ticket_panel` |

### Các chỗ lệch

- **DEV-1 — design 3.2, bảng lỗi, hàng "`text` sai kiểu hoặc rỗng sau `strip()` → `frappe.ValidationError` 'Nội dung tin trống.'".** Rỗng hoặc chỉ khoảng trắng vẫn là `ValidationError` "Nội dung tin trống.". Nhưng `text` **sai kiểu** (`None`, số) bị Frappe từ chối trước khi thân hàm chạy, bằng kiểm chú thích kiểu của `@frappe.whitelist` (`validate_argument_types`), và ném `frappe.FrappeTypeError` (HTTP 417, giống `ValidationError`), không phải `ValidationError`. 0 comment được tạo. Hệ quả: nhánh `not isinstance(text, str)` trong `_message_content` (`erp_ai/ticket_panel.py:101`) không bao giờ chạy với lời gọi HTTP. Test ghim: `erp_ai/tests/test_ticket_panel.py:394-397` (`assertRaises(frappe.FrappeTypeError)` với `None`, `5`, kèm 0 comment). Lý do: `review-T9-r1.md` ("Accepted: text=None/5 raising FrappeTypeError ... design 3.2 error table row 172 to be reworded at As-Built"). Bảng lỗi đúng sau As-Built:

  | Trường hợp | Lỗi | Comment tạo ra |
  |---|---|---|
  | `text` rỗng hoặc chỉ khoảng trắng sau `strip()` | `frappe.ValidationError` "Nội dung tin trống." | 0 |
  | `text` không phải chuỗi (`None`, số) | `frappe.FrappeTypeError` (417, do Frappe, trước thân hàm) | 0 |

  Cùng cơ chế áp dụng cho `ticket` sai kiểu ở cả hai method (design 3.1 và 3.2 ghi `ValidationError`); không test hay review nào ghi lại cho `ticket`: not recorded, suy ra từ cùng cơ chế, chưa kiểm.
- **DEV-2 — thiếu Section Break `section_reply` của ERP AI Setting.** Design 2.1 và touchpoint ghi 7 Section Break cho ERP AI Setting, gồm `section_reply` — "Chỉ báo và độ trễ trả lời" (đứng trước `thinking_text`). Thực tế `erp_ai_setting.json` có 6 (`grep -c '"Section Break"'` = 6, không có `section_reply`), nên `thinking_text`, `answer_delay_min_s`, `answer_delay_max_s` (dòng 160-174) nằm dưới `section_model` — "Model và từ khóa kích hoạt" (dòng 141). Credential 4 và Log 6 khớp design. Lý do: ruling D-1 của tech-lead trong `review-03.md`: `test_erp_ai_setting.py::test_status_fields_defaults` (không sửa được, STD-TEST-5) yêu cầu `thinking_text` đứng ngay sau `trigger_keyword` trong `meta.fields`, nên `section_reply` bị bỏ và các field gộp vào `section_model`. AC-3 (≥ 2 Break mỗi DocType) và AC-5 vẫn đạt. Việc còn lại, ghi ở `debt.md`: chỉ sửa chữ của design 2.1 cho khớp mã; `section_reply` không được thêm lại.
- **DEV-3 — `trigger_keyword` được đọc hai lần trong một lần gửi** (`get_trigger_keyword()` ở `ticket_panel.py:107` và `:130`); design 3.2 bước 2 và 4 chỉ nói "đọc" và không cấm. Reviewer ghi minor (b) ở review-08, không chặn. Hành vi không đổi.

## 4. Đối chiếu AC (tự động / sau bàn giao)

| Tiêu chí | Tự động | Sau bàn giao (người) |
|---|---|---|
| AC-1..AC-5, NFR-1, NFR-2, NFR-4 | đạt | — |
| AC-10, AC-14 | đạt (đột biến M2, M5 bị bắt) | — |
| AC-6, AC-7, AC-8, AC-9, AC-12, AC-13 (a), AC-15 | phần server/tĩnh đạt | J1.1, J1.2, J1.3, J1.5, J1.6, J1.7 |
| AC-11, NFR-3 | chỉ có test tĩnh hỗ trợ | J1.4 (hai phiên, đồng hồ) |

Suite cuối: `Ran 658 tests in 118.339s` `OK`, junit 0 lỗi; `cmd.lint` 13 hook `Passed`; 0 dấu skip thêm mới (acceptance.md).

## 5. Minor hoãn (review-08, review-09)
Đã ghi vào `docs/team/debt.md`, mục "Nên làm" (đánh dấu "FEAT-003, minor hoãn"): T10 (a)(b)(c); T13 pin `formEl.append(inputEl, sendEl)`, `"keydown"`, cuối thân `onSendFailed`, minor 1/3/5; T14 pin `NARROW_SCREEN_PX = 640`; T11 `TITLE_RUN_FAILED`/`self.log_error` không dùng, `call_count` thừa, `decisions` đúng 1 phần tử; T15 vòng tự kiểm của scanner, thiếu mẫu chuỗi thuần, các cách lách `socket.once(`, `call (`, `doc.add_comment(`.

## 6. Post-G4 debt (từ `acceptance.md` mục "Sau bàn giao")
Owner: người, trước mọi lần lên prod (G5). Kịch bản ở `acceptance.md` "Bước tay J1". Ghi kết quả vào cuối `acceptance.md`; bước hỏng thì `/team:intake` một BUG mới.

- [ ] J1.1 — AC-6: nút, tiêu đề, gửi bằng Enter, ghi P2 và số lần bấm, màn hẹp/di động, các tab cũ.
- [ ] J1.2 — AC-7: 4 mục AI, "Chưa có", không sửa được.
- [ ] J1.3 — AC-8, AC-9: luồng 5 tin, nhãn "Bot", tin rỗng, `<b>x</b>`, ngắt mạng.
- [ ] J1.4 — AC-11 (a)–(g), NFR-3: hai phiên, đo bằng đồng hồ.
- [ ] J1.5 — AC-12: 3 mẫu XSS, `window.__erp_ai_xss` là `undefined`.
- [ ] J1.6 — AC-13 (a): HD Contact không thấy gì của ngăn.
- [ ] J1.7 — AC-15: hồi quy FEAT-002 AC-10 (h)(i).
- [ ] Tùy chọn, người quyết: dọn 16 Comment `comment_type=Deleted` (`Email Account` 8, `Holiday List` 8) do phần chuẩn bị test tạo.
- [x] CHANGELOG phần 1 + phần 2 (`CHANGELOG.md`, mục `[Unreleased]`).
- [x] Tài liệu người dùng phần 2 (STD-DOC-2): `README.md`, mục "Khu vực trao đổi với bot trên trang phiếu".
- [x] As-Built ghi P2 và lý do (mục 2.1).
- [ ] CI xanh trên nhánh: for /team:release to check (writer không chạy được CI).
- [ ] Sau mỗi lần nâng cấp Helpdesk hoặc Frappe: chạy lại J1 AC-6 và AC-11 (README ghi việc này).
- [ ] Môi trường khác `miyano`: khởi động lại tiến trình web để method whitelisted mới được nạp, và chạy `bench migrate` để bản ghi HD Form Script lấy bản `.js` mới (design mục 6; việc của người, G5).
