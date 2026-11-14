**File này thay `design.md` cho việc build FEAT-005.** `design.md` (2026-11-12, 615 dòng) chỉ còn là lịch sử: không mục nào của nó có hiệu lực, kể cả §2.2, §2.5, §3.7, §4.6, §8. Ý nào còn dùng đã được chép lại dưới đây.

Feature: FEAT-005 · Stage: design · Author-agent: designer · Date: 2026-11-14 · Approved-by:

# Design FEAT-005 (Amendment 2): trước/sau đầy đủ trong nhật ký, cảnh báo role/phân quyền đúng một lần

Spec: Amendment 2 (AC-13, AC-14, AC-19; NFR-3, NFR-8; A-12, A-14..A-20). Mode decide, không có `questions.md`. Cỡ M, một chỗ nhớ mới (1 trường trên ERP AI Setting), đã có phán quyết ở **ADR-024**. Build sau khi FEAT-004 T62 và T64 (AC-35) đã merge vào `develop` (A-20).

**Sửa vòng 1 (ADR-024)** — chỉ các mục sau đổi; mục khác giữ như bản trước:
- §1: tuân theo ADR-024 (thay ADR-016 QĐ 5).
- §4.1: thêm hoàn tác cả lượt trong `runner._reason` khi ngoại lệ thoát ra sau khi tool đầu tiên đã chạy (ADR-024 QĐ 2); bỏ câu "thay đổi và dòng nhật ký luôn commit cùng nhau".
- §4.2 bước 3: tập tool ghi chung lấy từ `runner.GENERIC_WRITE_TOOLS`; ảnh chụp hỏng → mục "không có trước/sau", không bao giờ làm hỏng job (QĐ 1).
- §4.2 bước 1, 2, 5: mốc chỉ ghi bằng `set_single_value`; cửa sổ `(mốc, now − 300 s]`; mốc không lùi; cùng giao dịch với cảnh báo; `filelock` theo site (QĐ 3).
- §6: qa kiểm múi giờ của site không có giờ mùa hè (QĐ 3.6).
- §7: `runner.py` mang thêm phần hoàn tác và `GENERIC_WRITE_TOOLS`; thêm `test_architecture.py`; bỏ dòng ADR (đã có).
- §8: thêm 3 test được yêu cầu (write_entry lỗi, mã ảnh chụp lỗi, JSON hỏng) và 4 test của Ràng buộc ADR-024.
- D-1: viết lại rủi ro còn lại (hai khoảng trống được chấp nhận và ghi tài liệu). D-5: khóa theo site.

## 1. Bối cảnh
- **Vấn đề** (spec Amd-2, mục "Điều đã thấy"): (a) nhật ký chưa có trước/sau. (b) `before[name]` gom theo tên tool nên hai lời gọi đè nhau (`runner.py:686-687`). (c) Sửa bảng con bằng danh sách sẽ thay toàn bộ dòng (`site_api.py:164-169`). (d) Cảnh báo lấy mọi dòng có `modified_by = agent` mà không giới hạn thời gian (`tasks.py:84-90`), nên báo lặp mỗi ngày, báo nhầm do Frappe đóng dấu lại dòng con mỗi lần lưu (`frappe/model/document.py:729-731`), chỉ ghi `Has Role <mã dòng>`, và không thấy role bị gỡ.
- **Trong:** AC-13, AC-14, AC-19, NFR-3, NFR-8. **Ngoài:** như Out of scope của Amd-2: tool mới, bước duyệt, cảnh báo khi "Toàn quyền" bật, hoàn tác, sửa nhật ký cũ.
- **ADR tuân theo:** **ADR-024** (QĐ 1 nguồn = ERP AI Log, fail-closed; QĐ 2 hoàn tác lượt; QĐ 3 mốc; QĐ 4, 5 khoảng trống chấp nhận); ADR-004 (chỉ runner tạo nhật ký, tool trả trước/sau); ADR-018 QĐ 5 (với User chỉ ghi mã user và role); ADR-023 QĐ 5 (M5). ADR-016 QĐ 5 bị ADR-024 thay.
- **Đã đọc (thay cho Explore; đích đã biết):** `tasks.py:1-147`, `run_log.py:25-57`, `runner.py:60-120,570-700`, `site_api.py:30-171`, `alerts.py`, `erp_ai_setting.py:69-73`, `erp_ai_log.json` (`actions` Small Text; `value_before`/`value_after` Code), `test_tasks.py:216-456`, `test_architecture.py:55-115` (LAYER_RULES: `erp_ai.tasks` được import `erp_ai.agent.runner`, như `eval`), Frappe `synchronization.py:18` (`filelock(name, *, timeout, is_global=False)`), `version.py:28-33`, `document.py:519`. Kiểu lỗi: tool trả `ok=false` kèm lý do; job không ném lỗi mà `log_error(TITLE_RUN_FAILED)` (D-20). Test đặt cạnh mã, `test_<tên>.py`.

## 2. Dữ liệu
- **ERP AI Setting, thêm 1 trường:** `privilege_alert_checked_until`, Datetime, `read_only`, ở `section_alerts` sau `alert_recipients`, mô tả ≤ 400 ký tự. Single nên nằm trong `tabSingles`, không DDL. Chỉ một hàm của job ghi (`frappe.db.set_single_value`). `restore_self_managed_fields` khôi phục giá trị khi người lưu form, như `spent_this_month_usd`. Rỗng = chưa báo lần nào.
- **ERP AI Log, dòng `reason`: không thêm trường.** `value_before`/`value_after` (Code, longtext) nhận thêm khóa `"<tool>#<n>"` cho mỗi lời gọi tool ghi chung thành công. `n` là vị trí (đếm từ 1) của mục hành động của lời gọi trong `actions` của cùng dòng. Khóa cũ `<tên tool phiếu>` giữ nguyên.
- **Ảnh chụp (snapshot)** = `{"name": str, <trường>: giá trị, <bảng con>: [dòng, …]}`.
  - Tập trường: tạo/sửa lấy khóa của `values` ∪ `SNAPSHOT_TABLES.get(doctype, ())`; xóa lấy mọi trường có giá trị, kể cả bảng con; submit/hủy lấy `docstatus`.
  - **User (A-12):** luôn chỉ có `name` và `roles`.
  - Dòng con bỏ `name`, `idx`, `parent`, `parentfield`, `parenttype`, `owner`, `creation`, `modified`, `modified_by`, `doctype`; giữ thứ tự `idx`.
  - Bỏ mọi trường `site_api._is_secret` ở cha và con. Giá trị qua `json.loads(frappe.as_json(v))`. **Không cắt.** `before` của tạo là `None`; `after` của xóa là `None`.
- **Cách đọc của cảnh báo:** ERP AI Log `entry_type = "reason"`, `creation > mốc` (bỏ khi mốc rỗng), `creation ≤ cận trên`, `actions like "%api_%"`, sắp theo `creation` tăng. Không thêm index (ít dòng mỗi ngày; lần đầu đọc cả lịch sử một lần).

## 3. Hợp đồng
1. **Kết quả tool ghi** (`site_api`, nội bộ): khi `ok=true` có thêm `_snapshot: {"before": dict|None, "after": dict|None}`. Runner `pop` khóa này trước khi dựng `tool_result`, nên không vào ngữ cảnh model và không chịu trần 20.000 ký tự. `ok=false` hoặc tool sập thì không có. Khóa tóm tắt của T62 (FEAT-004) không đổi.
2. **ERP AI Log:** như §2. Chỉ thêm. **`runner.GENERIC_WRITE_TOOLS`** (hằng mới, nội bộ): tuple tên tool trong `WRITE_TOOL_TARGETS` có DocType `None` (model chọn DocType); suy ra từ bảng, không viết tay. Hôm nay = 4 tool `api_*_record`; `api_call_method` (DocType `"Method"`) không thuộc tập.
3. **`tasks.check_privilege_escalation(now: datetime | None = None) -> None`:** thêm tham số tùy chọn như `recompute_monthly_spend`; scheduler gọi không đối số (`hooks.py:161`, không sửa); không ném lỗi (D-20). Tiêu đề giữ "Agent đã sửa bản ghi phân quyền". Chữ mỗi mục là hợp đồng, test so đúng chữ:
   - Thêm role: `thêm role <role> cho <user> (người ra lệnh <instructor>, <YYYY-MM-DD HH:MM>)`. Gỡ: `gỡ role <role> của <user> (…)`. Tiền tố `[QUẢN TRỊ] ` khi role ∈ `site_api.FORBIDDEN_ROLES` (6 role của AC-14).
   - Bản ghi phân quyền: `<tạo|sửa|xóa|submit/hủy> <DocType> <tên> (người ra lệnh …, …)`. Không có ảnh chụp dùng được thì thêm `, không có trước/sau`. `instructor` rỗng → `không rõ`. Thời điểm = `creation` của dòng nhật ký.
   - Cột `actions` của dòng không đọc được: `ERP AI Log <tên dòng>, không có trước/sau`.
   - Thứ tự: `[QUẢN TRỊ]` trước, rồi theo thời điểm tăng. Qua `_list_names` hiện có (5 mục, rồi "…và N mục khác").
4. Không có mã lỗi mới, không breaking change. Ba điều kiện cảnh báo còn lại giữ nguyên chữ và hành vi.

## 4. Luồng
**4.1 Ghi nhật ký (AC-13, NFR-3) và hoàn tác lượt (ADR-024 QĐ 2).**
- `site_api`: sửa: chụp `before` từ doc vừa nạp, trước `doc.update`; `after` sau `save()`. Tạo: `after` sau `insert()`. Xóa: `before` trước `delete_doc`. Submit/hủy: `docstatus` trước và sau.
- `runner._run_tool`: sau `actions.append(...)`, gọi `_record_snapshot(name, outcome, len(actions), before, after)`: nếu `name ∈ GENERIC_WRITE_TOOLS` và `outcome` có `_snapshot` thì ghi `before["<name>#<n>"]`, `after["<name>#<n>"]` và `pop("_snapshot")` trước `json.dumps`. Hàm riêng để test làm nó ném lỗi.
- `runner._reason`, mỗi lượt: ngay sau khi `_call_model` trả về (đã commit trạng thái khóa của Cổng ngoài test) đặt `frappe.db.savepoint(REASON_TURN_SAVEPOINT)` (`"erp_ai_reason_turn"`). Bọc từ chờ trả lời/chạy tool tới hết `write_entry` của lượt trong `try`; `except Exception`: gọi `_undo_turn()` rồi `raise` (giữ ngoại lệ gốc) để `run_for_ticket` ghi `TITLE_RUN_FAILED` như cũ.
  - `_undo_turn()`: `frappe.db.rollback(save_point=REASON_TURN_SAVEPOINT)`. Nếu chính lệnh này lỗi (savepoint mất vì DDL đã commit ngầm trong lượt — ADR-024 QĐ 5, chấp nhận) thì bắt, ghi `frappe.logger(LOGGER_NAME).warning("reason turn undo failed run_id=%s error=%s", …)` (chỉ tên lớp lỗi), không ném lỗi mới; ngoại lệ gốc vẫn đi tiếp.
  - Thành công thì không `release`: `write_entry` commit (ngoài test) đã xóa savepoint. Trong test không có commit; savepoint trùng tên được MariaDB thay mới mỗi lượt.
  - Bao trùm: lỗi trong `_record_snapshot`, `transitions.log_step`, `_call_fields`, `write_entry` (kể cả tràn 64 KB của `actions`), `JobTimeoutException` của RQ. Lỗi của chính tool đã được `execute_tool`/`_write` rollback (không đổi).
  - Đánh đổi có chủ ý (ADR-024 Hệ quả): lượt lỗi mất cả các ghi khác của lượt (bình luận, phân loại). Quy tắc "không rollback" của `run_for_ticket` giữ nguyên; nhánh `GatewayError` (chưa có tool chạy) không đổi.
- **Commit:** thay đổi của tool và dòng `reason` của lượt vào cùng lần commit của `write_entry` (`run_log.py:55-56`), **trừ** khi trong lượt có một lần lưu gây DDL (commit ngầm); đường đó xem D-1. `write_entry` giữ `insert` + `commit` trong cùng lời gọi (Ràng buộc ADR-024).

**4.2 Cảnh báo (AC-14, AC-19, NFR-8).**
1. `with filelock(PRIVILEGE_ALERT_LOCK, timeout=PRIVILEGE_ALERT_LOCK_TIMEOUT_S)` (`"erp_ai_privilege_alert"`, 60 s; mặc định theo site, **không** `is_global`) bao cả thân job, kể cả commit. `LockTimeoutError` → `log_error(TITLE_RUN_FAILED, "check_privilege_escalation lock busy")`, return: mốc không đổi, không chạy điều kiện nào, không gửi gì.
2. `upper = (get_datetime(now) if now else now_datetime()) - timedelta(seconds=PRIVILEGE_ALERT_SETTLE_S)` (300 s; không dùng `datetime.now`/`utcnow`/`NOW()`). `lower = frappe.db.get_single_value(SETTING_DOCTYPE, "privilege_alert_checked_until", cache=False)`. `lower` có và `upper ≤ lower` → điều kiện này 0 mục và **không ghi mốc** (không lùi).
3. Đọc dòng theo §2. Với mỗi mục hành động `i` (đếm từ 1) có `tool ∈ GENERIC_WRITE_TOOLS` (import từ `runner`, không viết tay tên tool) và `ok` đúng:
   - DocType `User`: so `roles` của before/after `"<tool>#<i>"` theo tên role (Counter), mỗi role thêm/gỡ ra một mục; không khác → 0 mục.
   - DocType ∈ `PERMISSION_DOCTYPES` trừ `Has Role`, hoặc DocType `DocType` có `permissions` trước ≠ sau → 1 mục bản ghi.
   - **Fail-closed:** với `User` hoặc DocType phân quyền mà ảnh chụp không dùng được (dòng cũ, khóa thiếu, JSON hỏng, không phải dict, `roles` không phải list) → 1 mục "không có trước/sau". Đọc bằng `_load_snapshots(raw) -> dict` trả `{}` khi `ValueError`/`TypeError` (chú thích lý do bắt, STD-ERR-1); `actions` hỏng → mục theo §3.3. Không ném lỗi, không bỏ qua.
4. Có ≥ 1 mục → `_raise_alarm(subject, lines)` (không sửa). Ba điều kiện kia chạy như cũ.
5. Sau mọi điều kiện, nếu không rơi vào ca "không lùi" ở bước 2: `_advance_privilege_watermark(upper)` — hàm **duy nhất** ghi mốc, chỉ bằng `frappe.db.set_single_value`, không bao giờ `save()`/`insert()` ERP AI Setting. Rồi commit (ngoài test). Error Log cảnh báo, Email Queue (`delayed=True`) và mốc cùng **một** giao dịch: lỗi ở đâu → rollback cả ba (như hiện nay), lần sau báo lại đúng một lần.
6. `frappe.logger(LOGGER_NAME).info("check_privilege_escalation window=%s..%s changes=%d", …)`, không tên user/role (STD-OPS-5, STD-SEC-6).
- **Vì sao báo đúng một lần:** cửa sổ `(mốc, cận trên]` nối tiếp, không chồng; mốc chỉ tiến cùng giao dịch có cảnh báo; lịch lỡ N ngày thì cửa sổ dài ra (A-16). Khoảng lắng 300 s che khe insert→commit của `write_entry` và lệch đồng hồ giữa tiến trình. Đua không loại trừ được (người lưu form đúng lúc job commit) → báo **lặp**, không bao giờ **sót** (ADR-024 QĐ 3.8).
- **Gọi ra ngoài:** chỉ email qua Email Queue như hiện nay; không lời gọi mạng mới.

## 5. Quyền
- Job chạy dưới Administrator (scheduler).
- Bot không dời được mốc: ERP AI Setting ∈ `ALWAYS_DENIED_DOCTYPES` (`site_api.py:34`) và M5. Người lưu form không dời được: giá trị được khôi phục.
- Bot không sửa/xóa được dòng nhật ký (`ALWAYS_DENIED`, M5); bot tạo dòng giả qua `write_entry` chỉ gây báo thừa.
- Ảnh chụp đọc dưới phiên của tool, chỉ bản ghi tool vừa ghi.
- Mục cảnh báo chỉ dựng từ tên role, mã user, DocType, tên bản ghi, người ra lệnh, thời điểm → 0 byte khóa, mật khẩu, token.
- ERP AI Log chỉ System Manager đọc (A-12).

## 6. Migration và rollback
- **Up:** `cmd.migrate` đồng bộ JSON của ERP AI Setting: 0 DDL (Single), 0 dòng dữ liệu đổi. Mốc rỗng nên lần chạy đầu báo một lần mọi thay đổi trong lịch sử (AC-19 ca 3); dòng cũ ra "không có trước/sau".
- **Down:** revert mã và JSON, `cmd.migrate`. Dòng `privilege_alert_checked_until` thừa trong `tabSingles` vô hại. Cảnh báo quay về kiểu cũ (báo lặp).
- **Đối chiếu:** số dòng ERP AI Log trước = sau khi up; `frappe.get_meta("ERP AI Setting").has_field("privilege_alert_checked_until")` là True, giá trị None. qa chạy up/down/up trên `miyano`.
- **Múi giờ (ADR-024 QĐ 3.6, UNVERIFIED):** qa đọc `System Settings.time_zone` của `miyano` và dán kết quả `ZoneInfo(tz).dst()` tại 01-01 và 07-01 năm hiện tại: cả hai phải là 0 (vd. Asia/Ho_Chi_Minh). Khác 0 → báo team-leader trước G4.
- **Khi nào down:** 2 ngày đầu, cảnh báo không tới khi có thay đổi thử, hoặc tới lặp.

## 7. Touchpoints
| Đường dẫn | Loại | Vì sao |
|---|---|---|
| `erp_ai/agent/tools/site_api.py` | edit | `SNAPSHOT_TABLES = {"User": ("roles",)}`, `_snapshot(doc, fields)`; mỗi tool ghi trả `_snapshot` (§3.1, §4.1) |
| `erp_ai/agent/runner.py` | edit | `GENERIC_WRITE_TOOLS`; `_record_snapshot` (khóa `"<tool>#<n>"`, `pop`); **hoàn tác lượt** trong `_reason`: `REASON_TURN_SAVEPOINT`, `_undo_turn` (§3.2, §4.1) |
| `erp_ai/tasks.py` | edit | bỏ `_permission_records_by_agent`; thêm `_privilege_changes_by_agent(lower, upper)`, `_load_snapshots`, `_advance_privilege_watermark`, khóa, cửa sổ, tham số `now`, hằng `PRIVILEGE_ALERT_*` (§4.2) |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json` | edit | trường `privilege_alert_checked_until` (§2) |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py` | edit | `restore_self_managed_fields` khôi phục trường mới |
| `erp_ai/agent/tools/test_site_api.py` | edit | test ảnh chụp |
| `erp_ai/agent/test_agent_runner.py` | edit | test AC-13 qua runner, hoàn tác lượt, đầu-cuối cảnh báo |
| `erp_ai/tests/test_tasks.py` | edit | AC-14, AC-19, fail-closed; viết lại 5 test "bản ghi phân quyền" (spec đổi, STD-TEST-5) |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py` | edit | test khôi phục mốc |
| `erp_ai/tests/test_architecture.py` | edit | Ràng buộc ADR-024 (tập dùng chung, một hàm ghi mốc, không Version, không `datetime.now`) |

Đường dẫn mới: **0** (so với `allowed_new_file_roots`: không có gì để so). **0 trong `protected_paths`** (`.env`, `.env.*`, `**/*.pem`, `**/*.key`, `license.txt`). Không sửa: `hooks.py`, `alerts.py`, `run_log.py`, `constants.py`, `docs/team/adr/ADR-024.md` (của architect).
**Thứ tự phụ thuộc:** FEAT-004 T62, T64 merge vào `develop` (cùng `site_api.py`, `runner.py`) → ảnh chụp `site_api` + `_record_snapshot`, `GENERIC_WRITE_TOOLS` (AC-13) → hoàn tác lượt → trường Setting → `tasks.py` → test kiến trúc, đầu-cuối.

## 8. Test plan
Chạy `cmd.test_one` theo file, `cmd.test` trước khi merge. Thời gian giả: truyền `now=`, đặt `creation` của dòng gieo bằng `frappe.db.set_value(..., update_modified=False)`, setUp đặt mốc T0 để loại dòng thật (STD-TEST-6). Dòng gieo dựng bằng `site_api` dưới tài khoản agent cộng `write_entry` đúng dạng §2. Lỗi giả bằng `unittest.mock.patch` lên hàm của module (`run_log`/`runner`), không sửa mã sản phẩm.

| Tiêu chí | `file::test` | Loại | Biên / lỗi |
|---|---|---|---|
| AC-13 (1) | `erp_ai/agent/test_agent_runner.py::test_create_user_snapshot_lists_both_roles` | runner + Cổng giả | |
| AC-13 (2), (b) | `…test_agent_runner.py::test_update_user_role_list_diff_shows_removed_and_added` | runner | role giữ nguyên không nằm trong hiệu |
| AC-13 (3) | `…test_agent_runner.py::test_holiday_list_missing_old_date_seen_in_diff` | runner | |
| AC-13 (4), (c) | `…test_agent_runner.py::test_30000_char_field_stored_byte_identical` | runner | biên > 20.000 |
| AC-13 (5), (d) | `…test_agent_runner.py::test_two_calls_same_tool_one_turn_two_snapshots` | runner | |
| AC-13 (c) | `…test_agent_runner.py::test_snapshot_never_reaches_model` | runner | |
| NFR-3, QĐ 2 | `…test_agent_runner.py::test_write_entry_failure_undoes_turn_role_change` | runner | `api_update_record` thêm role ok, `write_entry` lượt ném → User không có role, 0 dòng `reason` của lượt, có Error Log `TITLE_RUN_FAILED` |
| NFR-3, QĐ 2 | `…test_agent_runner.py::test_snapshot_handling_failure_undoes_turn` | runner | `_record_snapshot` ném sau khi role đã thêm → cùng kết quả |
| QĐ 2 | `…test_agent_runner.py::test_lost_turn_savepoint_keeps_original_error` | runner | rollback savepoint ném → Error Log ghi lớp lỗi gốc, không ném ra khỏi `run_for_ticket` |
| AC-13, NFR-3 | `erp_ai/agent/tools/test_site_api.py::test_refused_or_failed_write_has_no_snapshot` | unit | lỗi |
| AC-13, A-12 | `…test_site_api.py::test_snapshot_drops_secret_and_system_fields` | unit | gieo khóa giả → 0 |
| AC-13, A-12 | `…test_site_api.py::test_user_snapshot_only_name_and_roles` | unit | |
| AC-13 (a) | `…test_site_api.py::test_delete_and_submit_snapshot_shapes` | unit | `None` ở hai đầu |
| AC-14 (1) | `erp_ai/tests/test_tasks.py::test_bot_created_user_role_alarm_names_user_role_instructor` | integration | |
| AC-14 (2) | `…test_tasks.py::test_bot_removed_role_listed_as_removed` | integration | |
| AC-14 (3) | `…test_tasks.py::test_admin_role_marked_and_listed_first` | integration | "Toàn quyền" bật, `api_update_record` thêm `System Manager` |
| AC-14 (4) | `…test_tasks.py::test_lists_at_most_five_names` (viết lại) | integration | biên 7 → 5 + "…và 2 mục khác" |
| AC-14 (4) | `…test_tasks.py::test_five_names_have_no_overflow_text` (viết lại) | integration | biên đúng 5 |
| AC-14 (5) | `…test_tasks.py::test_bot_resave_user_without_role_change_no_line` | integration | lưu lại User, Frappe đóng dấu lại |
| AC-14 (6) | `…test_tasks.py::test_permission_record_modified_by_someone_else_does_not_alarm` (viết lại) | integration | role và Custom DocPerm do người → 0 |
| AC-14 | `…test_tasks.py::test_alarm_on_permission_records_modified_by_agent` (viết lại) | integration | Role Profile, User Permission do bot |
| AC-14 | `…test_tasks.py::test_record_action_without_snapshot_listed` | integration | dòng cũ |
| AC-14, QĐ 1 | `…test_tasks.py::test_broken_snapshot_json_listed_without_before_after` | integration | `value_before`/`value_after` JSON hỏng trên `User` → đúng 1 mục "không có trước/sau"; 3 điều kiện kia vẫn chạy; mốc tiến |
| AC-14 (7) | `…test_tasks.py::test_one_alarm_per_condition` (viết lại phần gieo); `test_alarm_on_role_drift`, `test_alarm_on_enabled_server_script_or_webhook_by_agent`, `test_alarm_on_enabled_key_without_secret`, `test_message_never_contains_key_text` không đổi | integration | |
| AC-14 (8) | `…test_tasks.py::test_fake_key_never_in_privilege_alarm` | integration | khóa giả trong ảnh chụp → 0 |
| AC-14, AC-19 | `erp_ai/agent/test_agent_runner.py::test_role_change_via_record_tool_alarmed_once` | đầu-cuối | |
| AC-19 (1), NFR-8 | `…test_tasks.py::test_change_alarmed_on_next_run_only` | integration | T+1h có, T+25h không |
| AC-19 (2), NFR-8 | `…test_tasks.py::test_change_after_two_missed_runs_alarmed_once` | integration | T+49h có, T+73h không |
| AC-19 (3) | `…test_tasks.py::test_change_before_rollout_alarmed_on_first_run_only` | integration | mốc rỗng; chỉ khẳng định mục gieo |
| AC-19, NFR-8 | `…test_tasks.py::test_change_inside_settle_margin_waits_for_next_run` | integration | biên 300 s |
| AC-19, NFR-8 | `…test_tasks.py::test_failed_run_keeps_watermark_and_realarms_once` | integration | lỗi giữa job → mốc giữ, Error Log cảnh báo và Email Queue cũng mất; lần sau báo 1 lần |
| AC-19, NFR-8 | `…test_tasks.py::test_busy_lock_skips_run_without_moving_watermark` | integration | stub `filelock` ném `LockTimeoutError` → mốc giữ, 0 Email Queue mới |
| AC-19, NFR-8 | `…test_tasks.py::test_upper_not_after_watermark_keeps_it` | integration | mốc > `now − 300 s` → 0 mục, mốc không lùi |
| §2 mốc | `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py::test_privilege_alert_watermark_restored_on_human_save` | integration | người lưu với mốc khác → DB không đổi |
| AC-14, QĐ 1 | `erp_ai/tests/test_architecture.py::test_privilege_alert_reads_shared_generic_write_tools` | kiến trúc | mọi tool trong `WRITE_TOOL_TARGETS` có DocType `None` ∈ `GENERIC_WRITE_TOOLS`; `tasks.py` không có chuỗi `api_*` |
| AC-19, QĐ 3 | `…test_architecture.py::test_privilege_alert_watermark_and_clock_rules` | kiến trúc | tên trường mốc chỉ ở JSON, `erp_ai_setting.py`, một hàm `tasks.py`, test; không `datetime.now`/`utcnow`/`NOW()` trong job; `erp_ai/**` không đọc `Version` |

Bước kiểm của qa (không phải test): múi giờ không DST (§6).
AC trong spec Amd-2: AC-13, AC-14, AC-19; NFR-3, NFR-8. Trong test plan: AC-13, AC-14, AC-19; NFR-3, NFR-8. Khớp nhau. 36 dòng: 31 test mới, 5 viết lại.

## Assumptions decided by the team
- **D-1 Nguồn của cảnh báo là ERP AI Log (A-17)** — ADR-024 QĐ 1 chấp nhận.
  - Chọn: ảnh chụp của AC-13 + `instructor` trên dòng nhật ký; fail-closed khi ảnh chụp hỏng.
  - Vì: người ra lệnh chỉ có trong nhật ký; Version không có khi tạo User, bị bỏ trong test. Thay đổi và dòng nhật ký cùng commit (nay có hoàn tác lượt giữ điều này ở đường ngoại lệ); bot chỉ ghi nhật ký qua `write_entry` (M5).
  - Phương án khác: Version của User (ADR-016 QĐ 5). Sai thì: đọc thêm Version rồi nối với nhật ký.
  - **Rủi ro còn lại, chấp nhận và ghi tài liệu (ADR-024 QĐ 4, 5):**
    - **Khoảng trống 1:** khi "Toàn quyền" bật, đổi role qua `api_call_method` (hàm whitelist, không ảnh chụp, không thuộc `GENERIC_WRITE_TOOLS`) không được báo. Đổi role qua tool bản ghi khi "Toàn quyền" bật vẫn được báo (AC-14 ca 3). Tài liệu người dùng (DoD sau G4) ghi: "Khi bật Toàn quyền, thay đổi role qua gọi hàm không có trong cảnh báo hằng ngày." Thu hẹp nếu người chọn ADR-023 QĐ 6 (a); đóng hẳn chỉ bằng amendment.
    - **Khoảng trống 2, đường DDL:** một lần lưu gây DDL (Custom Field, DocType) trong cùng lượt, sau một đổi role/phân quyền, làm MariaDB commit ngầm; tiến trình chết (SIGKILL, OOM, restart worker) hoặc ngoại lệ sau đó, trước `write_entry`, để lại thay đổi không dòng nhật ký (savepoint đã mất nên `_undo_turn` chỉ ghi warning). Đường ngoại lệ không DDL đã đóng bằng §4.1. Mở lại chỉ bằng amendment (dòng "chưa áp dụng", spec `:265` đã rút).
- **D-2 Mốc "đã báo tới đâu" trên ERP AI Setting** — ADR-024 QĐ 3.1, 3.2.
  - Vì: tiền lệ `spent_this_month_usd`; bot không ghi được; Single nên không DDL.
  - Phương án khác: `set_global`; dò Error Log cũ; cửa sổ 24 giờ. Sai thì: đổi chỗ lưu trong một hàm đọc và `_advance_privilege_watermark`.
- **D-3 Ảnh chụp đầy đủ ở cột Code; tóm tắt của T62 giữ ở `actions`.**
  - Vì: `actions` là Small Text (64 KB), không chứa bản đầy đủ (AC-13 c); chỉ thêm. Sai thì: gộp sau khi đổi kiểu cột `actions`.
  - Ghi cho chủ FEAT-004: T64 có thể tràn 64 KB; nay tràn → hoàn tác cả lượt (§4.1), không mất dòng nhật ký.
- **D-4 So role theo tên, không theo `name` của dòng.** Vì: sửa bằng danh sách tạo dòng mới cho cả role được giữ. Sai thì: đổi khóa so trong một hàm.
- **D-5 Khoảng lắng 300 s; khóa `filelock` theo site, 60 s; savepoint lượt tên `erp_ai_reason_turn`.**
  - Vì: che khe insert→commit và lệch đồng hồ; chặn chạy chồng. Hằng ngày nên chậm 5 phút không đáng kể. Khóa theo site chỉ chặn trên cùng thư mục site; worker nhiều máy không chung thư mục (chưa có, `deploy.staging = ""`) → có thể báo lặp, không sót.
  - Phương án khác: khóa dòng DB (`FOR UPDATE`). Sai thì: sửa hằng hoặc thay khóa trong một chỗ.
