Feature: CHG-002
Stage: architect
Author-agent: architect
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Phán quyết kiến trúc 3: khóa trả về của `confirm_restart` và luật trường trạng thái ADR-012 (T24)

Đầu vào đã đọc (2026-11-15, chỉ đọc):
- `tasks.md:263-269` (T24), `:271-276` (T25).
- `df35ac6:erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py`:
  - `approve`/`reject`/`undo` trả `{"name": name, "status": …}` (dòng 158, 165, 174);
  - `confirm_restart` dòng 180-202, bốn dòng bị bắt: 189, 198, 200, 202.
- `df35ac6:…/erp_ai_change_proposal.js:55-100`: các lời gọi POST hiện có chỉ `frm.reload_doc()`, chưa đọc khóa nào của `r.message`.
- `df35ac6:…/test_erp_ai_change_proposal.py`: `TestConfirmRestart` (từ dòng 1092), các assertion so cả dict ở 1172, 1195, 1207, 1253, 1283, 1317, 1348; dòng 1127, 1336 là dữ liệu đặt vào DB trong test (test không bị luật quét).
- `990d7b3:erp_ai/tests/test_architecture.py`: `STATE_FIELDS` (1993-2014), `_state_field_writes` (2096-2127, phép dò khóa dict 2112-2115), `check_change_state_fields_written_only_in_changes` (2130-2141), test 4814, ca tự kiểm `test_state_field_writes_caught_outside_changes` (7074, bảng `shapes`).
- `design-addendum-1.md:120-144` (A-2); `design-addendum-5.md:102-115` (P-4, `confirm_restart(sent_at=)`); `design.md:326` (§3.3).
- `spec.md:68` (AC-46), `:77` (AC-55): không nêu tên khóa trả về.
- `docs/team/adr/ADR-012.md` (Ràng buộc dòng 52); `docs/team/adr/ADR-040.md` (C-1..C-3).

Không gọi Explore (lệnh của team-leader: đọc đúng các chỗ trên).

Đây là quyết định kiến trúc (cách hiểu phạm vi một dòng Ràng buộc của ADR-012, và một quy ước cho mọi method whitelisted về sau), nên được ghi thành **Phán quyết C-4** ở cuối `docs/team/adr/ADR-040.md`. Thân ADR-012 không sửa.

---

## Nguyên nhân thật
Cả luật và hợp đồng đều đúng với chữ của mình, nhưng hợp đồng A-2.1 chọn tên khóa trùng tên một trường trạng thái. Luật ADR-012 không biết (và không nên biết) một dict sẽ đi đâu: cùng một dict chữ có thể là giá trị trả về cho form, hoặc là đối số của `set_value`/`update`/`get_doc`. Ba method anh em trong cùng file đã tránh chuyện này bằng khóa `status` (không phải `change_status`). A-2.1 không theo quy ước đó.

## Chọn
**Đổi khóa của hợp đồng, giữ luật nguyên vẹn.** `confirm_restart` trả `{"name", "status"}`, cùng hình dạng với `approve`/`reject`/`undo`. Giá trị của `status` là giá trị của trường `restart_status` (`Đã gửi`, `Đã xác nhận`, `Chưa xác nhận`, `Lỗi khởi chạy`, hoặc rỗng), không đổi so với mã `df35ac6`.

Quy ước (ADR-040 C-4 Quyết định 2): mọi method whitelisted ngoài `agent/changes/` trả trạng thái nó vừa đọc hoặc vừa chuyển bằng khóa `status`; không khóa nào trong giá trị trả về trùng tên một trường của `STATE_FIELDS`.

## Vì
- **Phê chuẩn cái mã đã làm.** Ba method POST của form đã trả `{"name", "status"}`. Chọn khóa `status` không thêm quy ước mới, chỉ bỏ một ngoại lệ của A-2.1.
- **Vành đai không yếu đi.** Luật không đổi dòng nào, nên không ca nào nó bắt hôm nay bị lọt ngày mai.
- **Không mở lại task đã tick.** `transitions.confirm_restart(name, value, *, sent_at) -> bool` (T17, T52) giữ nguyên.
- **AC không đổi.** AC-46 (c) và AC-55 nói về quyền và kết luận, không nói tên khóa.

## Phương án khác
| Phương án | Vì sao không chọn |
|---|---|
| Luật bỏ qua dict là giá trị `return` (kể cả bản hẹp: chỉ `return {…}` trực tiếp trong method whitelisted của controller) | Mở đúng đường lách mà luật đang chặn: `def _fields(): return {"change_status": v}` rồi `frappe.db.set_value(D, n, _fields())` hay `doc.update(_fields())`. Bản hẹp vẫn thêm một ngoại lệ có điều kiện cú pháp vào luật vành đai (N-1) chỉ để giữ một tên khóa; người sửa sau dễ nới tiếp. |
| Dựng giá trị trả về trong `agent/changes/` (một hàm `transitions` trả dict) | Đưa việc trình bày vào máy trạng thái; mở lại T17/T52 đã tick; hai nhánh chỉ đọc (không ở `Đã gửi`, không có kết luận, dòng 189 và 198) cũng phải đi qua đó, tức thêm API cho một nơi dùng (STD-DESIGN-5). Thực chất là miễn trừ theo vị trí cho mã không ghi gì. |
| Khóa khác, ví dụ `restart` | Qua luật, nhưng tạo hình dạng thứ hai giữa bốn method POST của cùng form. |
| Dựng dict vòng (`dict(restart_status=…)`, khóa là biến, gán dần) | Né luật, không sửa nguyên nhân; `dict(...)` có từ khóa trạng thái vẫn bị bắt (`STATE_KEYWORD_CALLS`). Cấm. |

## Luật kiến trúc
- **Không dòng luật nào đổi.** `STATE_FIELDS`, `STATE_WRITE_CALLS`, `STATE_KEYWORD_CALLS`, `_state_field_writes`, `check_change_state_fields_written_only_in_changes`, test 4814 giữ nguyên từng dòng.
- **Thêm hai ca tự kiểm** vào bảng `shapes` của `test_state_field_writes_caught_outside_changes` (`990d7b3:erp_ai/tests/test_architecture.py:7074`), cùng nguồn `{"change_decision.py": source}` và cùng `assertCaught(…, "change_decision.py", "ADR-012")`:
  - `"return dict"`: `"def f(n, v):\n\treturn {'name': n, 'restart_status': v}\n"` → bắt. Ghim cách đọc của C-4 Quyết định 1, để không ai "sửa" luật bằng cách bỏ qua `return`.
  - `"helper dict to a write"`: `"def f(v):\n\treturn {'change_status': v}\n\nfrappe.db.set_value(D, n, f(v))\n"` → bắt. Đây là vi phạm thật (ghi `change_status` ngoài `agent/changes/`) mà phương án "bỏ qua `return`" sẽ để lọt.
  - Cả hai ca xanh ngay trên luật hiện có (luật đã bắt chúng); chúng là ca ghim, không phải RED của task. RED của task là `test_change_state_fields_written_only_in_changes` đỏ với bốn dòng 189/198/200/202 đã dán ở progress T24, cộng các assertion `TestConfirmRestart` đổi khóa trước khi sửa mã (dưới).

## Dev phải sửa trên `df35ac6` (nhánh `team/CHG-002-task-24`)
1. **Test trước.** `test_erp_ai_change_proposal.py`, `TestConfirmRestart`: bảy assertion ở dòng 1172, 1195, 1207, 1253, 1283, 1317, 1348 đổi `{"name": name, "restart_status": X}` thành `{"name": name, "status": X}`; giá trị X giữ nguyên. Chạy `cmd.test_one` → đỏ (dict khác), dán đầu ra. Dòng 1127 và 1336 (dữ liệu đặt vào DB) không đổi.
2. **Mã.** `erp_ai_change_proposal.py` dòng 189, 198, 200, 202: khóa `"restart_status"` thành `"status"`. Không đổi giá trị, thứ tự đọc, `_decider`, `sent_at=`, logger. Docstring (dòng 180-185) nếu nêu khóa trả về thì nói `status`.
3. **Ca tự kiểm.** Thêm hai mục ở trên vào `shapes` của `test_state_field_writes_caught_outside_changes`.
4. **Không được:** dựng dict bằng `dict(...)`, khóa là biến, hay dict gán dần để né luật; thêm ngoại lệ vào luật; sửa `transitions.py`.
5. **Xanh phải dán:** `test_erp_ai_change_proposal` OK (gồm toàn bộ `TestConfirmRestart` của T24), `test_architecture` OK (`test_change_state_fields_written_only_in_changes` và `test_state_field_writes_caught_outside_changes` xanh), `test_transitions` OK.

## T24, T25 đổi gì trong `tasks.md` (tech-lead sửa)
- **T24:**
  - `files`: thêm `erp_ai/tests/test_architecture.py` (chỉ hai ca tự kiểm).
  - `Returns (A-2.1)`: `confirm_restart(name=None) -> {"name", "restart_status"}` thành `confirm_restart(name=None) -> {"name", "status"}`, `status` = giá trị trường `restart_status` (ADR-040 C-4). Mọi nhánh trả (không ở `Đã gửi`, `restart_sent_at` rỗng, không có kết luận, `transitions.confirm_restart` trả `False`, có kết luận) cùng khóa `status`.
  - `Expect`: thêm `ARCH::TestArchitecture::test_change_state_fields_written_only_in_changes`, `test_state_field_writes_caught_outside_changes` (ca `return dict`, `helper dict to a write`) xanh.
  - `progress`: ghi "phán ở `arch-ruling-3.md` (C-4)".
- **T25:**
  - `Returns`: form đọc `r.message.status` (không phải `r.message.restart_status`) từ `confirm_restart`, so với `frm.doc.restart_status`, khác thì `frm.reload_doc()`. Các điều kiện còn lại (chỉ khi `restart_status = Đã gửi` và `frappe.user.has_role("ERP AI Instructor")`, một lần lúc mở) không đổi.
  - `Expect`: `test_calls_confirm_restart_only_when_sent` khẳng định thêm callback đọc `message.status`; không thêm test mới.
- **Design:** `design-addendum-1.md:124` và `design.md:326` còn chữ `{"name", "restart_status"}`; C-4 thay chữ đó. Designer đưa vào addendum sau; architect không sửa design.

## Tự kiểm (hai task tuân mọi ADR mà vẫn xung đột?)
- T24 trả `status`, T25 đọc `restart_status` → xung đột. Chặn bằng dòng Returns mới của T25 và assertion `message.status` trong `test_calls_confirm_restart_only_when_sent`.
- Một method whitelisted mới về sau trả `{"change_status": …}` → luật hiện có bắt, ca `return dict` ghim lại cách đọc đó.

## Sai thì hoàn tác
Đổi lại khóa ở bốn dòng controller, bảy assertion của `TestConfirmRestart` và lời đọc trong JS; gỡ hai ca tự kiểm. Khi đó luật lại đỏ, nên phải có phán quyết mới chọn một trong các phương án đã bác ở trên. Không có dữ liệu nào phải di trú (giá trị trả về không lưu ở đâu).
