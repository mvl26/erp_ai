# Acceptance FEAT-003

Commit kiểm: `7cb654fa1426558d37f8925be6f9ca806e292664` (team/FEAT-003, cây chính, `git status --porcelain -- erp_ai` rỗng). Nền diff: `team/BUG-002` = `0051042` (theo team-leader; `main` không có ở local). Ngày: 2026-11-12. Người kiểm: qa.

Viết tắt: `TP` = `erp_ai.tests.test_ticket_panel`, `DD` = `erp_ai.tests.test_doctype_descriptions`, `AR` = `erp_ai.tests.test_architecture`. "junit" = `cmd.test` chạy với `--junit-xml-output`, kết quả 658 testcase, 0 failure/error/skipped.

Lưu ý về exit code: `bench run-tests` trả exit 0 cả khi test đỏ (8 lần chạy đột biến bên dưới đều `exit=0` kèm `FAILED`). Vì vậy bằng chứng xanh là dòng `OK` và junit 0 lỗi, không phải exit code.

## Bảng tiêu chí

| Tiêu chí | Lệnh | Exit | Đầu ra | Test phủ | Kết luận |
|---|---|---|---|---|---|
| AC-1 | `cmd.test` (junit) + script chỉ đọc in field hiển thị của 3 JSON tại HEAD | 0 / 0 | `ERP AI Setting: visible=22 empty_desc=0`; `ERP AI Credential: visible=18 empty_desc=0`; `ERP AI Log: visible=31 empty_desc=0` (71/71). junit: `DD` 10 case, 0 lỗi | `DD::test_every_visible_field_has_description` | đạt |
| AC-2 | cùng script, in `doctype \| fieldname \| len \| description` cho 71 field (bảng đối chiếu ở mục "Đối chiếu AC-2") | 0 | `permission_level`: "L0: … L1: … L2 và L3 …"; 4 `price_*`: "USD cho 1 triệu token"; `excluded_teams`, `alert_recipients`: "Mỗi dòng …"; Credential `budget_month_usd`: "Nhập 0 là không giới hạn"; mọi field `ro=1` có "Hệ thống tự ghi" và "không sửa được" | `DD::test_required_phrases_present`, `::test_read_only_fields_say_system_writes` | đạt |
| AC-3 | cùng script | 0 | `sections=6 empty_sec_labels=0 ascii_only_labels=0` (Setting), `sections=4 …=0 …=0` (Credential), `sections=6 …=0 …=0` (Log) | `DD::test_section_breaks_labelled_in_vietnamese` | đạt |
| AC-4 | script đếm trên mô tả + so với giá trị đang lưu của ERP AI Setting và ERP AI Credential (đọc bằng `bench --site miyano mariadb`, không in giá trị) | 0 | `sk-: 0 miyano: 0 emails: ['canhbao@congty.vn']`; `tokens_checked= 10 hits(field,len)= [('name', 14), ('permission_level', 2), ('trigger_keyword', 3)]` | `DD::test_descriptions_have_no_sensitive_data`, `::test_descriptions_contain_no_stored_setting_values` | đạt. Ba lần trùng không phải lộ cấu hình: `name` là tên DocType "ERP AI Setting"; "L1" là nhãn lựa chọn mà AC-2 bắt buộc phải có; "@ai" là ví dụ do chính spec bắt buộc (spec dòng 65, "Ví dụ: @ai") |
| AC-5 | script chỉ đọc so JSON `git show 0051042:` với `7cb654f:` cho 3 DocType | 0 | cả 3 file: `nonbreak_field_diffs= [] order_same= True top_level_diffs= [] breaks_with_extra_props= [] field_order_consistent= True`. `cmd.test`: `Ran 658 tests in 118.339s` `OK`. `cmd.migrate`: `migrate_exit=0`, ERP AI Setting không đổi (mục Ảnh chụp site) | `DD::test_section_breaks_carry_only_label`, `::test_skipped_fields_still_follows_value_after` | đạt |
| AC-6 | `git -C ../helpdesk status --porcelain` + bước tay J1.1 | 0 | ` M desk/auto-imports.d.ts`, ` M desk/yarn.lock`, ` M yarn.lock`; mtime `2026-11-11 10:21–10:38`, trước commit FEAT-003 đầu tiên (`2026-11-12 16:07 3dd7358`), nên không do FEAT-003 tạo. Phần trình duyệt: NOT VERIFIABLE (`ui: false`, không có Playwright) | J1.1 | phần lệnh đạt; phần tay **sau bàn giao (người)** |
| AC-7 | `cmd.test` (junit) | 0 | `TP` 36 case, 0 lỗi | `TP::test_read_returns_ai_fields_as_stored_text`, `::test_read_empty_ai_fields_are_null`, `::test_read_ai_fields_use_hd_ticket_labels` | phần server đạt; J1.2 **sau bàn giao (người)** |
| AC-8 | `cmd.test` (junit) + đột biến M3 | 0 | M3 (trả HTML thô): `FAIL: test_thread_selects_b5_comments_in_creation_order … '<p>early @AI human</p>\n' != 'early @AI human'` | `TP::test_thread_selects_b5_comments_in_creation_order`, `::test_thread_ignores_non_comment_types`, `::test_thread_marks_bot_messages` | phần server đạt; J1.3 **sau bàn giao (người)** |
| AC-9 | `cmd.test` (junit) + đột biến M1 | 0 | M1 (`keyword_added = False`): `ERROR: test_send_appends_configured_keyword_when_missing`, `ERROR: test_send_creates_one_comment_owned_by_sender`, `ERROR: test_send_escapes_html`, … (cả 10 nhánh của test so cổng cũng đỏ) | `TP::test_send_empty_or_whitespace_is_rejected`, `::test_send_length_boundary`, `::test_send_appends_configured_keyword_when_missing`, `::test_send_escapes_html`, `::test_send_creates_one_comment_owned_by_sender`, `::test_send_keyword_with_special_chars_rejected` | phần server đạt; J1.3 **sau bàn giao (người)** |
| AC-10 | `cmd.test` (junit) + đột biến M2 | 0 | M2 (bỏ từ khóa trước `new_comment`): `FAIL: … (branch='agent_off')`, `(branch='level_L0')`, `(branch='excluded_group') … 'd: no_keyword' … != … 'd: not_sendable'`, `(branch='daily_limit')`, `(branch='turn_limit')`, `(branch='over_budget')` … | `TP::TestTicketPanelGateParity::test_send_matches_comments_box_in_every_gate_branch` | đạt (test bắt được đột biến) |
| AC-11 | `AR` tĩnh trong `cmd.test` | 0 | junit: `AR` 77 case, 0 lỗi (`test_status_script_socket_events_only_in_once_block` có mặt) | `AR::test_status_script_socket_events_only_in_once_block` (hỗ trợ) | NOT VERIFIABLE bởi qa: chỉ có bước tay J1.4, **sau bàn giao (người)** |
| AC-12 | `cmd.test` + đột biến M3, M6 + `grep -nE 'innerHTML\|outerHTML\|insertAdjacentHTML\|document\.write\|eval\(\|new Function'` trên JS | 0 / 1 (grep 0 dòng) | M3: `FAIL: test_read_strips_xss_payloads_to_text (is_bot=False) … '<img' unexpectedly found`; M6 (thêm `innerHTML` vào JS): `FAIL: test_status_script_static_rules … forbidden in script: innerHTML` | `TP::test_read_strips_xss_payloads_to_text`, `AR::test_status_script_static_rules` | phần tự động đạt; J1.5 **sau bàn giao (người)** |
| AC-13 | `cmd.test` + đột biến M4, M4b + POST Guest thật | 0 | M4 (bỏ `has_permission`): `FAIL: test_read_denied_for_agent_without_ticket_read … PermissionError not raised`, `FAIL: test_send_denied_for_same_accounts_creates_nothing (user='panel.noread@example.com')`. M4b (bỏ `is_agent`): `FAIL: test_read_denied_for_customer_who_can_read_the_ticket … PermissionError not raised`. Guest: `http=403`, `exc_type= PermissionError`, `has_data= False`, không ImportError | `TP::test_read_denied_for_non_agents_and_guest`, `::test_read_denied_for_agent_without_ticket_read`, `::test_inactive_hd_agent_denied`, `::test_send_denied_for_same_accounts_creates_nothing`, `::test_send_denied_for_agent_user` | (b)(c) đạt; (a) J1.6 **sau bàn giao (người)** |
| AC-14 | `cmd.test` + đột biến M5, M7 + `git diff --diff-filter=A --name-only 0051042..7cb654f -- '*.json'` + grep `localStorage\|sessionStorage\|document\.cookie` | 0 / 1 (grep 0 dòng) | M5 (thêm một `UPDATE` không đổi giá trị trong `get_panel_data`): `FAIL: test_read_writes_nothing_and_calls_no_gateway … 59 != 58`. M7 (thêm `localStorage`): `forbidden in script: localStorage`. JSON mới: rỗng | `TP::test_read_writes_nothing_and_calls_no_gateway`, `::test_read_never_returns_keyword_or_settings`, `AR::test_status_script_static_rules` | đạt |
| AC-15 | `cmd.test`, `cmd.migrate`, ảnh chụp site | 0 / 0 | `Ran 658 tests in 118.339s` `OK`; junit `failed/err/skipped []`; `migrate_exit=0`, không dòng `error`/`traceback` (đếm 0); ERP AI Setting và role của ai.agent giống hệt trước/sau | test FEAT-001/002 trong junit, không có assertion bị nới (mục Grep diff) | phần tự động đạt; J1.7 **sau bàn giao (người)** |
| NFR-1 | script AC-1 | 0 | `max_len=260` (Setting), `182` (Credential), `331` (Log), đều ≤ 400 | `DD::test_descriptions_at_most_400_chars` | đạt |
| NFR-2 | như AC-5 | 0 | JSON chỉ khác `description` + Section Break; `cmd.test` OK | như AC-5 | đạt |
| NFR-3 | — | — | chỉ đo bằng đồng hồ ở J1.4 | — | NOT VERIFIABLE bởi qa, **sau bàn giao (người)** |
| NFR-4 | như AC-10, AC-14 | 0 | M2, M5 bị bắt (xem trên) | `TP` parity + read-only | đạt |
| NFR-5 | như AC-12, AC-13 | 0 | M3, M4, M4b, M6 bị bắt; Guest 403 PermissionError | như AC-12, AC-13 | phần tự động đạt; J1.5–6 **sau bàn giao (người)** |

## Đột biến (worktree tạm, ngoài cây chính)

`git worktree add --detach <scratchpad>/wt 7cb654f`, mỗi đột biến: sửa 1 chỗ → `cd /home/miyano/frappe-bench && PYTHONPATH=<wt> bench --site miyano run-tests --module <module>` → `git checkout` file. Cuối cùng `git status --porcelain` trong worktree rỗng; `git worktree remove` + `prune` đã chạy (`wt_removed`). Cây chính không bị sửa.

| # | Chỗ sửa | Kết quả |
|---|---|---|
| M1 | `keyword_added = False` | đỏ: `ERROR` ở `test_send_appends_configured_keyword_when_missing` và 13 dòng khác |
| M2 | `.new_comment(content.replace(<từ khóa>, ""))` | đỏ: `FAIL` parity ở ≥ 7 nhánh |
| M3 | `"text": content` (bỏ `html_to_plain_text`) | `Ran 36` `FAILED (failures=5)` |
| M4 | `has_permission` luôn True | `Ran 36` `FAILED (failures=4)` |
| M4b | bỏ `is_agent()` | `Ran 36` `FAILED (failures=3)` |
| M5 | `frappe.db.sql("update `tabHD Ticket` set _user_tags=_user_tags …")` trong `get_panel_data` | `Ran 36` `FAILED (failures=1)`, `59 != 58` |
| M6 | `document.body.innerHTML += ""` trong JS | `Ran 77` `FAILED (failures=1)` |
| M7 | `window.localStorage.setItem(…)` trong JS | `Ran 77` `FAILED (failures=1)` |

8/8 đột biến bị bắt.

## Acceptance checklist (6)

1. Mỗi tiêu chí có lệnh, exit code, đầu ra chạy trên commit này: có (bảng trên). Bước tay J1 không chạy được bởi qa.
2. Biên/lỗi: chạy lại các test biên (rỗng, 2001 ký tự, từ khóa ký tự đặc biệt, Guest, agent không có quyền đọc) trong `cmd.test`, cộng POST Guest thật (`http=403`).
3. Chất lượng test: 8 đột biến đều làm test đỏ; giá trị kỳ vọng viết cứng (ví dụ `'early @AI human'`, `59 != 58`).
4. `cmd.test`: `Ran 658 tests` `OK`, junit 0 lỗi; mọi file `test_*.py` đều có testcase trong junit (chỉ `erp_ai.test_utils` không có, đó là file tiện ích). `cmd.lint` (chạy trong worktree sạch tại 7cb654f để không chạm file của phiên song song): 13 hook `Passed`, `lint_exit=0`. `cmd.typecheck`: slot rỗng. `cmd.build`: không chạy (JS được phục vụ qua HD Form Script; MD5 script trên site `cb5b7c51…` = MD5 file repo `cb5b7c51…`).
5. Grep diff `0051042..7cb654f -- '*.py'`: dấu skip thêm mới: 0 dòng (`added_skip_exit=1`). Dòng `self.assert` bị xóa: 1, `assertIn("function setupForm({ doc, router })")` đổi thành `({ doc, call, router })`, đúng chỗ ADR-009 cho phép. Ngoài ra chỉ bỏ `r"\bcall\b"` khỏi danh sách cấm (ADR-009 cho phép) và `LAYER_RULES` được siết thêm `erp_ai.ticket_panel`, không nới.
6. Migration: không có DocType hay field mới; `cmd.migrate` exit 0; ERP AI Setting trước = sau. DoD build: test + mã nằm trong touchpoints (11 file `erp_ai/`); không file nào ngoài `erp_ai/`, `docs/`; không chạm `protected_paths` (`protected_grep_exit=1`).

## Ảnh chụp site (mariadb chỉ đọc)

| Mốc | setting (27 field, MD5) | role ai.agent | HD Ticket | ERP AI Log | Comment | HD Form Script MD5 |
|---|---|---|---|---|---|---|
| trước `cmd.test` | 4afdc94b… | 99, 9c8eb830… | 7 | 54 | 120839 | 424673e7… |
| sau `cmd.test` | 4afdc94b… | 99, 9c8eb830… | 8 | 58 | 120840 | 424673e7… |
| sau đột biến | 4afdc94b… | 99, 9c8eb830… | 8 | 58 | 120856 | 424673e7… |
| sau `cmd.migrate` | 4afdc94b… | 99, 9c8eb830… | 8 | 58 | 120856 | 424673e7… |

- +1 HD Ticket / +4 ERP AI Log / +1 Comment trong lúc chạy `cmd.test`: phiếu thật 43071 "Thêm 1 người dùng" (tạo 17:54:44, người gửi không thuộc `example.com`), rồi agent đang bật trên site phân loại và trả lời phiếu đó. Đây là hoạt động thật trên site, không phải test để sót. qa không xóa.
- +16 Comment sau 8 lần chạy module: `comment_type=Deleted` cho `Email Account` (8) và `Holiday List` (8), do phần chuẩn bị test của Frappe/ERPNext tạo. Đây là nhiễu đã biết ("+2 mỗi lần chạy module", `dev-notes.md`). qa không xóa; team-leader quyết định có dọn hay không.
- Không có thay đổi nào ở ERP AI Setting, role ai.agent, HD Team, HD Form Script, ToDo, Task, User.

## Kiểm tra trực tiếp sau migrate

`curl -X POST -H "Host: miyano" -d ticket=43071 http://localhost:8000/api/method/erp_ai.ticket_panel.get_panel_data` (Guest) → `http=403`, `exc_type= PermissionError`, không ImportError. gunicorn khởi động `Thu Nov 12 17:41:57 2026`, sau commit cuối của `ticket_panel.py` (`17:28:02`). Không cần khởi động lại.

## Đối chiếu AC-2 (71 dòng)

Toàn bộ 71 dòng `doctype | fieldname | len | ro | description` đã in và đối chiếu với bảng Dữ liệu của spec: 71/71 đạt. Các chuỗi kiểm tối thiểu đều có (xem dòng AC-2). Mô tả dài nhất là `ERP AI Log.instructor` với 331 ký tự.

## Bước tay J1 cho người (desktop, site `miyano`, sau bàn giao)

Chuẩn bị: một tài khoản role Agent (HD Agent active), một tài khoản HD Contact, mức quyền L1, agent bật. Ghi kết quả từng bước vào cuối file này.

1. **AC-6.** Mở `/helpdesk/tickets/<id>`, bấm 1 lần nút "Trao đổi với bot", thấy tiêu đề "Hướng giải quyết & trao đổi với bot". Gõ câu hỏi rồi nhấn Enter, tin hiện trong luồng. Ghi phương án vị trí (P2) và số lần bấm. Thu hẹp cửa sổ < 640 px hoặc mở bản di động: không có nút, console không có lỗi `erp_ai`. Các tab Activity, Emails, Comments, Analytics chạy như cũ.
2. **AC-7.** Mở 1 phiếu có đủ 4 giá trị AI và 1 phiếu chưa có giá trị nào. Đối chiếu với thanh bên. Mục trống hiện "Chưa có". Không có ô sửa.
3. **AC-8, AC-9.** Gieo comment như test AC-8, thấy đúng 5 tin, tin bot có nhãn "Bot", dòng hướng dẫn hiện. Gửi tin rỗng thì có thông báo. Gửi `<b>x</b>` thì thấy đúng chữ đó ở khu vực và ở tab Comments. Ngắt mạng rồi gửi: có thông báo thất bại, chữ đã gõ còn nguyên.
4. **AC-11 (a)–(g), NFR-3.** Mở hai phiên A và B, bấm đồng hồ. (a) Chỉ báo hiện trong khu vực. (b) Câu trả lời hiện ≤ 10 s. (c) Chỉ báo mất ≤ 10 s, và tự mất sau 600 s nếu không có tín hiệu kết thúc. (d) Chỉ một chỉ báo trên cả trang, khi khu vực mở cũng như khi đóng. (e) 4 mục AI đổi ≤ 10 s. (f) Tin có từ khóa của phiên B hiện ở phiên A ≤ 10 s. (g) Chuyển sang phiếu Q thì không thấy tin hay chỉ báo của phiếu P.
5. **AC-12.** Gieo 3 mẫu XSS của spec vào comment bot và vào hướng giải quyết. Chúng hiện dạng chữ. Console: `window.__erp_ai_xss` là `undefined`. Không có phần tử `img`, `script`, `a` mới trong khu vực.
6. **AC-13 (a).** HD Contact mở `/helpdesk/my-tickets/<id>`: không có nút, khu vực, 4 mục AI hay luồng.
7. **AC-15 (FEAT-002 AC-10 (h)(i)).** Khi khu vực đóng, chỉ báo ở vị trí FEAT-002 chạy như cũ. Timeline tự cập nhật khi có comment mới. Mỗi lần chạy chỉ có một chỉ báo.

## DoD

- Đạt: AC-1..AC-5 và phần tự động của AC-6..AC-15 (đầu ra ở trên); `cmd.test` xanh, `cmd.lint` sạch, 0 dấu skip; `cmd.migrate` OK, Setting không đổi; helpdesk không có dòng nào do FEAT-003 tạo; commit local, không push; kịch bản J1 đã viết (DoD phần 2, dòng 347).
- Việc sau G4, không tính là lỗi. Owner: team-leader → tech-writer (`/team:asbuilt`). Gồm: As-Built (ghi P2 và lý do), tài liệu người dùng phần 2 (STD-DOC-2, bắt buộc), CHANGELOG phần 1 + phần 2, CI xanh trên nhánh.
- Minor để lại (review-08, review-09): ghi nhận, không chặn.

## Kết luận

Mọi tiêu chí kiểm được bằng lệnh đều đạt trên `7cb654f`, và 8/8 đột biến bị test bắt. Còn lại các bước tay J1 (AC-6 phần tay, AC-7/8/9/12/13(a)/15 phần tay, AC-11, NFR-3). qa không chạy được các bước này (`ui: false`, không có Playwright).

### Lần gọi thứ 2 (2026-11-12): ghi verdict

Kiểm lại trước khi ghi:
- `git rev-parse --short team/FEAT-003` → `7cb654f` (không đổi).
- `git status --porcelain -- erp_ai` → rỗng (code không đổi).
- Do đó không chạy lại test. Mọi đầu ra ở trên vẫn đúng với commit này.

Quyết định của team-leader (journal FEAT-003, chế độ decide, 2026-11-12): các bước tay J1 là việc của người sau bàn giao. Căn cứ: spec dòng 174 (Success: "Sau bàn giao (việc của người)") và DoD phần 2 dòng 347 (chỉ đòi có kịch bản, ghi ai làm và khi nào). Cách làm giống tiền lệ FEAT-002 AC-10/AC-11 (acceptance FEAT-002 dòng 170-181). Vì vậy J1 không phải `NOT VERIFIABLE` của bước build, và không chặn verdict build.

Hai chỗ lệch với tiêu chuẩn QA chặt, ghi rõ để người có thể bác:
- AC-11 và NFR-3 chỉ có test tĩnh hỗ trợ ở bước build. Hành vi thời gian thực chưa được ai quan sát.
- Phần trình duyệt của AC-6/7/8/9/12/13(a)/15 chưa chạy.

## Sau bàn giao

Owner: người. Khi nào: sau bàn giao, trước mọi lần lên prod (G5). Kịch bản ở mục "Bước tay J1" phía trên. Ghi kết quả vào cuối file này.

- [ ] J1.1 — AC-6: nút, tiêu đề, gửi bằng Enter, P2, màn hẹp/di động, các tab cũ.
- [ ] J1.2 — AC-7: 4 mục AI, "Chưa có", không sửa được.
- [ ] J1.3 — AC-8, AC-9: luồng 5 tin, nhãn "Bot", tin rỗng, `<b>x</b>`, ngắt mạng.
- [ ] J1.4 — AC-11 (a)–(g), NFR-3: hai phiên, đo bằng đồng hồ.
- [ ] J1.5 — AC-12: 3 mẫu XSS, `window.__erp_ai_xss` là `undefined`.
- [ ] J1.6 — AC-13 (a): HD Contact không thấy gì của panel.
- [ ] J1.7 — AC-15: hồi quy FEAT-002 AC-10 (h)(i).
- [ ] Tùy chọn, người quyết định: dọn 16 Comment `comment_type=Deleted` (`Email Account` 8, `Holiday List` 8) do phần chuẩn bị test tạo ra. Hiện chưa ai xóa.

Bước J1 nào hỏng → mở `/team:intake` một BUG mới (bug-fix, viết test đỏ trước nếu kiểm được), ghi kết quả J1 vào file này và sửa verdict. G5 vẫn chỉ người duyệt.

Verdict: accepted
