Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review phần Amendment 2 (CHG-001) của code nhận từ ngoài quy trình

Chưa có task nào trong `tasks.md` cho phần này, nên đây là một file review cho cả ba nhóm (không phải review của một task). Căn cứ: `docs/team/features/FEAT-004/spec.md` mục "Amendment 2 — 2026-11-14", `docs/team/features/CHG-001/arch-impact.md` (biện pháp M1–M5), `docs/team/adr/ADR-023.md` — cả ba mới ở cây chính, chưa commit, `Approved-by:` còn trống (ADR-023 trạng thái proposed). Không có bằng chứng đỏ-rồi-xanh cho bất kỳ phần nào (STD-TEST-1 không tính được).

- Vòng: 1
- Verdict: request-changes cho cả ba nhóm (3 blocker, 9 major); không design-defect

## Nhóm F — liên kết duyệt một lần bấm (`git diff 7e90e5e..25be823 -- erp_ai/agent/change_link.py erp_ai/change_decision.py` và test)
Lớp 1: mã khớp chữ Amendment 2 (liên kết GET có chữ ký) nhưng trái phán quyết kiến trúc (ADR-023 QĐ 1 / M1).

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| blocker | STD-ERR-7 | erp_ai/change_decision.py:122-136 | `decide` là GET; `frappe/app.py:451-458` `sync_database` rollback mọi request không "unsafe"; `run_log.write_entry` đã commit "Đã duyệt" (run_log.py:56), sau đó `enqueue_after_commit=True` bị rollback cuối request xóa → đề xuất kẹt "Đã duyệt", không job áp dụng nào chạy | M1: method POST gọi từ form |
| blocker | STD-SEC-4 | erp_ai/change_decision.py:122, erp_ai/agent/change_link.py:35 | GET đổi trạng thái bỏ qua kiểm CSRF của Frappe: tải trước của trình duyệt/proxy, máy quét thư, hoặc `<img src=…approve…>` cùng origin trong comment phiếu (do agent không có role hoặc model chèn) duyệt thay người có role đang đăng nhập | M1 |
| major | STD-DESIGN-2 | erp_ai/agent/change_link.py:35; propose_change.py:92-99 | ADR-023 QĐ 1 / ADR-010: không whitelist GET nào đổi trạng thái; `decision_path` vẫn dựng `/api/method/…` | đường `/app/erp-ai-change-proposal/<name>?<đã ký>` |
| major | STD-TEST-2 | erp_ai/test_change_decision.py:173-175,210-223 | Test "đúng 1 job" (NFR-10, AC-25) đếm lời gọi trên `frappe.enqueue` đã patch trong `in_test`; vẫn xanh khi request thật mất job | test M1: POST, 1 job còn sau `frappe.app.sync_database`; GET → `PermissionError` |
| major | STD-TEST-8 | erp_ai/test_change_decision.py:247-251 | AC-5/AC-26 nêu 4 loại tài khoản bị từ chối; chỉ test user không role và Administrator | thêm tài khoản agent, Guest, agent được gán phiếu, người tạo phiếu |
| major | STD-TEST-2 | erp_ai/test_change_decision.py (cả file) | Không có test AC-12 (1 dòng nhật ký ghi đúng người mở liên kết) và AC-27 (kiểm lại lúc áp dụng khi duyệt qua liên kết) | thêm |

minor | — | — | 3 điểm nhỏ: `ticket` rỗng thì chuyển hướng tới `/helpdesk/tickets/None`; từ chối kiểm bằng `assertIn` một phần; `_refuse` hiện `str(exc)` thô | tùy dev

Chữ ký HMAC tự nó đứng vững (khóa `conf.secret` hoặc khóa mã hóa, so sánh thời gian hằng). M1: chưa phần nào có trong mã.

## Nhóm G — công cụ bản ghi `site_api.py` (`git diff 25be823..6d90e79 -- erp_ai/agent/tools/site_api.py erp_ai/agent/tools/test_site_api.py`)
Lớp 1: AC-30, AC-31, AC-32 phần lớn đạt; AC-33 không đạt; M3 và M5 chưa có.

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| blocker | STD-SEC-4 | erp_ai/agent/tools/site_api.py:62,118,159 | Các phép kiểm cấm DocType, role, user so chuỗi phân biệt hoa thường, MariaDB khớp tên không phân biệt: `{"role": "system manager"}` qua `FORBIDDEN_ROLES` rồi Frappe lưu thành "System Manager" (`frappe/model/document.py:2593`); `name="administrator"`, `doctype="erp ai setting"` tương tự (role: đã xác nhận; DocType/user: nghi vấn, chưa chạy) | tra tên đang lưu trước khi so; mỗi phép kiểm một test chữ thường |
| blocker | STD-SEC-4 | erp_ai/agent/tools/site_api.py:213-219 | Chế độ toàn quyền: `call_method` chỉ so chuỗi trên JSON ngoài cùng; vượt bằng chuỗi `doc` lồng có `S`, tên DocType chữ thường, hoặc `frappe.core.doctype.user.user.generate_keys` / `frappe.client.get_password` (trả khóa API, mật khẩu, không có tên DocType trong tham số) → trái AC-33 | M5 là ranh giới thật; phần hàm trả khóa cần người chọn theo ADR-023 QĐ 6, trước đó cấm hai hàm này |
| major | STD-DESIGN-2 | erp_ai/agent/tools/site_api.py:32-34 | Thiếu M3: hai tập cấm viết tay, không dẫn xuất từ `read.denied_doctypes()`; chế độ thường không cấm `DocType`, `Role` | làm M3 kèm ma trận test |
| major | STD-ERR-7 | erp_ai/agent/tools/site_api.py:127-136 | `_write` chỉ bắt `PermissionError`, `ValidationError`; `DuplicateEntryError`, `TypeError`, lỗi hook để savepoint không rollback không release (AC-30 "không để lại nửa chừng") | bắt phần còn lại, rollback về savepoint; test tên trùng |
| major | STD-TEST-5 | erp_ai/agent/tools/test_site_api.py:164-166 | Test Role Permission, Custom DocPerm, Salary Slip, Custom Role chỉ kiểm `ok=False`; vẫn xanh khi xóa danh sách cấm | kiểm lý do "không được phép", dùng DocType có thật |
| major | STD-TEST-2 | erp_ai/agent/tools/test_site_api.py (chưa có) | Nhánh chưa có test: từ chối đổi tên (`site_api.py:156`), Webhook luôn tắt, AC-33 gọi hàm quyết định bằng liên kết bot đọc được, AC-33 mật khẩu/khóa API ở chế độ toàn quyền | mỗi nhánh một test |

minor | — | — | 5 điểm nhỏ: `_VALUES_NOTE` (dòng 305) nói không gán được System Manager, sai ở chế độ toàn quyền; docstring dòng 5 nói quá; trường mật/hệ thống trong dòng con không được kiểm (dòng 108); `strip_html(str(exc))` lộ chi tiết nội bộ (dòng 134); một commit gộp ba tính năng | tùy dev

AC-34, NFR-11 không nằm trong hai file; AC-35 chưa có mã (spec đã ghi).

## Nhóm H — ô "Toàn quyền", nhóm `site_admin`, khối prompt, test cũ bị sửa (`git diff 25be823..6d90e79` cho `registry.py`, `policy.py`, `prompts.py`, `erp_ai_setting.json` và 4 file test)
Lớp 1: hành vi khớp AC-2 (a/b/c), AC-14, AC-29, AC-32; cấu trúc không theo ADR-023 QĐ 4; thiếu test cho AC-1, AC-2, AC-32.

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-DESIGN-2 | erp_ai/agent/tools/registry.py:84-96,166-169 | `_unrestricted_specs`, `get_unrestricted_tool_schemas` là đường cấp thứ hai ngoài `GRANT_TABLE`; ADR-023 QĐ 4 và ADR-011 QĐ 6 không chấp nhận | M4: `unrestricted` là đầu vào thứ tư của `_granted_specs`/`get_tool_schemas`/`execute_tool`; bỏ hai tên cũ |
| major | STD-TEST-2 | erp_ai/agent/tools/test_registry.py:303,395 | Thiếu ma trận AC-1 (32 tổ hợp) và AC-2 (sửa code × toàn quyền × 4 mức × người ra lệnh × vượt ngân sách); không ca L0/mức lạ cho toàn quyền; không ca `execute_tool` từ chối `api_delete_record` khi không được cấp; AC-32 thiếu test mặc định 0 và quyền đặt ô | ma trận viết tay so với ảnh chụp kết quả cấp ở `6d90e79`; test mặc định và quyền của `unrestricted_enabled` |

minor | — | — | 4 điểm nhỏ: AC-14 chưa ghim "đừng tự viết lại đường dẫn duyệt" và "trong comment đề xuất trên phiếu"; AC-29 chưa ghim "ok", "một câu"; `SITE_ADMIN_TOOLS_BLOCK` nêu 4 role cấm, AC-31 có 6; `grants_site_admin_tools` không có test trực tiếp | tùy dev

Phán về 6 điểm đỗ từ review E (round 48):
1. `test_registry.py:393` số tool 11 → 21: hết, theo N-3 mục 18–19 (spec:320-321): 11 + 3 + 4 + 3
2. `test_classification.py:384,397` `ACT_NOW_BLOCK` khi `change_tools=True`: hết, theo AC-29 (spec:370) và A-19 (spec:383)
3. `prompts.py:162-163` chữ `CHANGE_TOOLS_BLOCK`: hết, theo AC-14 [changed] (spec:357)
4. `test_doctype_descriptions.py:269-272` mô tả `code_change_enabled`: hết, theo N-4 (spec:327) và A-24 (spec:388)
5. Hàm cấp thứ hai trái ADR-011 QĐ 6: CÒN (major M4 ở trên)
6. Ô toàn quyền cấp ở L1/L2 và sống qua hạ mức do ngân sách: hết về hành vi, theo AC-2(c) (spec:353), AC-32 (spec:373), ADR-023 QĐ 4; chưa có test (thuộc major STD-TEST-2)

## Không kiểm được từ diff (tech-lead xử lý)
- Hành vi HTTP thật trên `miyano` (đề xuất kẹt "Đã duyệt"), bộ lọc Helpdesk có giữ `<img>` trong comment không, role của tài khoản agent trên `miyano`: cần qa/người kiểm trên site; tech-lead không tự kiểm được.
- ADR-023 và `arch-impact.md` còn `Approved-by:` trống: phán quyết đã ràng buộc chưa là việc của team-leader và người.

## deferred
- Việc tiếp: `/team:plan --insert` cho M1–M5 và các phát hiện trên (cần designer chốt các điểm ở mục "Để designer quyết" của `arch-impact.md` và người trả lời 3 câu hỏi cuối file đó). Tech-lead không giao dev khi chưa có task.
- `runner.py`: 5 dòng `api_*` của `WRITE_TOOL_TARGETS`, `_action` đọc doctype, lời gọi `get_unrestricted_tool_schemas` (`runner.py:587-598`) đi cùng task M4.
