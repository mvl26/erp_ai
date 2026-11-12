Feature: FEAT-003
Stage: plan
Author-agent: tech-lead
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Plan FEAT-003

- Nhánh feature: `team/FEAT-003` từ `team/BUG-002` (tạo lúc build; cây đang có As-Built BUG-001/BUG-002 chưa commit; `config.base_branch` = `main` chỉ dùng lúc PR). Chưa tạo nhánh trong bước plan.
- Số task: 15; song song tối đa: 2 (`limits.max_parallel_dev`)
- Cỡ L, gate áp dụng: G5 (G3 tắt trong `.team/config.json`). Lệnh test: `cmd.test_one`, `cmd.test`, `cmd.migrate` của profile.

## Ràng buộc chung (chép nguyên từ design/spec; mọi task kế thừa)
- Allow-list: `PANEL_METHODS = ("erp_ai.ticket_panel.get_panel_data", "erp_ai.ticket_panel.send_message")`, `PANEL_MAX_MESSAGE_CHARS = 2000`, đặt ở `erp_ai/constants.py`. Cả hai method `@frappe.whitelist(methods=["POST"])`, không `allow_guest`.
- Chữ ký: `get_panel_data(ticket: str) -> dict`; `send_message(ticket: str, text: str) -> dict` trả `{"comment": <tên>}`; JS `function setupForm({ doc, call, router })`; action "Trao đổi với bot".
- `policy.contains_keyword` không sửa; chỉ thêm `get_trigger_keyword() -> str`. Không `ignore_permissions`, `set_user`, `get_all`, `db.sql`, `commit` trong `erp_ai/ticket_panel.py`; đúng 1 `.new_comment(` và nằm trong `send_message`.
- Phần trang: chỉ `textContent`; không `innerHTML`/`outerHTML`/`insertAdjacentHTML`/`document.write`/`eval(`/`new Function`; không `localStorage`/`sessionStorage`/`document.cookie`; không `setInterval`; không dùng số `600`; một đối tượng `window.__erpAiAgentStatus`; `querySelector` chỉ với `#app`.
- Mô tả field (phần 1): tiếng Việt, ≤ 400 ký tự, không `sk-`, không email thật (chỉ `@congty.vn`/`@example.com`), không `miyano`, không giá trị đang lưu; field `read_only` có "Hệ thống tự ghi" và "không sửa được". Section Break: `fieldname` dạng `section_<chủ đề>`, chỉ có `fieldname`, `fieldtype`, `label`, nằm ngay trước field đầu của nhóm; thuộc tính khác của field giữ nguyên (AC-5). Bảng nhóm và `fieldname` đúng design mục 2.1.
- Tên log: `frappe.logger(LOGGER_NAME)`; không ghi nội dung tin, giá trị từ khóa, email.
- Test cũ không sửa assertion (STD-TEST-5); ngoại lệ duy nhất: các dòng ADR-009 cho phép ở `test_architecture.py`.

## Thứ tự
1. T1 rồi T2: walking skeleton phần 2 (server đọc, rồi action + ngăn tối thiểu đọc nó). Đây là đường rủi ro nhất (ADR-009/010, `call` POST). Không task phần 2 nào khác bắt đầu trước khi review T2 approve.
2. Phần 1 (T3 → T4 → T5) độc lập: không chung file nào với phần 2, nên đi song song với phần 2 ngay từ đầu (yêu cầu của team-leader; ngoại lệ có chủ ý của quy tắc "chưa task nào chạy trước review T1" vì phần 1 không chạm lớp nào của skeleton). Ba task xếp nối nhau vì chung `test_doctype_descriptions.py`.
3. Sau skeleton, hai nhánh phần 2: server (T6, T7 → T8 → T9 → T10 → T11) và trang (T12 → T13 → T14). T15 (luật tĩnh) cuối cùng vì kiểm cả hai.

## Nhóm song song (tối đa 2 dev cùng lúc, không chung file)
| Lúc | Hai task chạy cùng |
|---|---|
| 1 | T1 ∥ T3 |
| 2 | T2 ∥ T4 |
| 3 | T7 ∥ T5 (hoặc T6 ∥ T5) |
| 4 | T6 ∥ T8 hoặc T12 ∥ T8 |
| 5 | T9 ∥ T12 (nếu chưa xong) |
| 6 | T10 ∥ T13 |
| 7 | T11 ∥ T14 |
| 8 | T15 một mình |
Nhóm hợp lệ tổng quát: {T1→T2, T3→T4→T5, T6}; sau T2: {T7→T8→T9→T10→T11} ∥ {T12→T13→T14}; T6 chạy được bất cứ lúc nào trước T9. Tech-lead chọn theo dev rảnh, luôn ≤ 2.

## Bảng mỗi file một chủ
| File | Chủ | Task khác chạm | Thứ tự |
|---|---|---|---|
| erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json | T3 | — | — |
| erp_ai/erp_ai_agent/doctype/erp_ai_credential/erp_ai_credential.json | T4 | — | — |
| erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json | T5 | — | — |
| erp_ai/tests/test_doctype_descriptions.py | T3 | T4, T5 | T3 → T4 → T5 |
| erp_ai/constants.py | T1 | — | — |
| erp_ai/agent/policy.py, erp_ai/agent/test_policy.py | T6 | — | — |
| erp_ai/ticket_panel.py, erp_ai/tests/test_ticket_panel.py | T1 | T7, T8, T9, T10, T11 (T11 chỉ test) | T1 → T7 → T8 → T9 → T10 → T11 |
| erp_ai/public/js/agent_status_indicator.js | T2 | T12, T13, T14 | T2 → T12 → T13 → T14 |
| erp_ai/tests/test_architecture.py | T1 | T2, T12, T13, T14, T15 | T1 → T2 → T12 → T13 → T14 → T15 |

Touchpoint của design (11) → task: setting.json T3; credential.json T4; log.json T5; test_doctype_descriptions.py T3/T4/T5; ticket_panel.py T1/T7-T10; test_ticket_panel.py T1/T7-T11; constants.py T1; policy.py T6; test_policy.py T6; agent_status_indicator.js T2/T12-T14; test_architecture.py T1/T2/T12-T15. 11/11, không hàng trống.

AC → task: AC-1..AC-5 T3-T5; AC-6 T2, T12 và J1.1; AC-7 T1, T2, T12; AC-8 T7, T12; AC-9 T6, T9, T10, T13; AC-10 T11; AC-11 T12-T14 và J1.4; AC-12 T7, T2, T15; AC-13 T1, T9; AC-14 T8, T14, T15; AC-15 T6, T11, T15 và checkpoint cuối. 15/15. NFR-1 T3-T5; NFR-2 checkpoint; NFR-3 T14 và J1.4; NFR-4 T8, T11; NFR-5 T7, T12, T15.

## Checkpoint (`cmd.test` xanh trên `team/FEAT-003`, dán đầu ra)
1. Sau T2 (hết skeleton): `cmd.test` xanh; `get_panel_data` gọi được và `setupForm` trả action; review T1, T2 approve.
2. Sau T5 (hết phần 1): `cmd.test` xanh; `cmd.migrate` thành công trên `miyano`; ERP AI Setting trước và sau như nhau.
3. Sau T11 (hết server): `cmd.test` xanh; 9 nhánh chốt khớp ô Comments.
4. Sau T15 (hết): `cmd.test` xanh, `cmd.lint` sạch, không dấu skip; `cmd.migrate` OK; `git diff --stat` từ nhánh nền: không JSON DocType mới ngoài 3 tệp phần 1; `diff.patch`. Rồi `/team:verify FEAT-003`; J1 (7 bước tay) do QA và người làm trên `miyano` (không có `cmd.test_js`, `ui: false`).

## Rủi ro
| Rủi ro | Dấu hiệu | Cách xử lý |
|---|---|---|
| `call` của frappe-ui là POST nên đọc có thể ghi ngầm | `transaction_writes` tăng khi gọi `get_panel_data` | T8 đo; nếu tăng: tìm lệnh ghi phụ của `get_activity_timeline`/`get_doc`, báo `design-defect`, không thêm `ignore` |
| Từ khóa có `<`, `>`, `&` không giữ được sau sanitize | `contains_keyword(stored)` False | T10 từ chối trước `new_comment`; test `a&b`, `a<b` |
| Sửa `test_architecture.py` làm lỏng luật cũ | diff gỡ chuỗi cấm ngoài `\bcall\b` | Reviewer đối chiếu STD-TEST-5 từng task T1, T2, T12-T15 |
| Khóa mục của `get_activity_timeline` khác dự kiến | KeyError ở T7 | Dev đọc `activity.py:254-271,331-337` và ghim bằng test AC-8; lệch thiết kế → `DESIGN_CONFLICT` |
| Sửa JS rồi `install.py` đặt lại bản ghi | `test_install.py` đỏ | Mỗi task JS chạy test_install; `install.py` không chạm |
| Section Break làm lệch test field hiện có | `test_erp_ai_log.py`, `test_erp_ai_setting.py` đỏ | Không sửa test cũ; chỉnh vị trí Break; không có Break giữa `value_after` và `skipped_fields` |

## Tiêu điểm review (≤ 5 đầu vào lỗi, mỗi cái có test ở task chủ)
1. Từ khóa `a&b` / `a<b`: T10.
2. XSS trong comment và hint: T7 (`test_read_strips_xss_payloads_to_text`), T15 (không `innerHTML`).
3. Đọc không ghi (`transaction_writes`): T8.
4. Biên 2000 / 2001 ký tự và rỗng: T9.
5. `skipped_fields` ngay sau `value_after`: T5.

## Walking skeleton (cỡ L)
T1 + T2 chạy đầu-cuối: server (`get_panel_data` có cổng quyền, 4 mục AI, `LAYER_RULES`) và trang (action "Trao đổi với bot" → ngăn tối thiểu → `call` POST → vẽ 4 mục bằng `textContent`). Chứng cứ: `cmd.test_one` của T1 (đọc đúng/null/từ chối) và của `test_architecture.py` (T2, luật tĩnh gồm allow-list `call`). Phần đi qua trình duyệt chỉ kiểm tay được (J1.1, J1.2), không có `cmd.test_js`. Lõi agent, gateway và `send_message` chưa đụng tới trong skeleton; đó là rủi ro đã biết, đi vào T9-T11.
