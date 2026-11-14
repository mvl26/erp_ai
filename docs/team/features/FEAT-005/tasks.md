Feature: FEAT-005
Stage: plan
Author-agent: tech-lead
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Tasks FEAT-005

Mỗi task 2–5 phút. Hai task chung file thì phụ thuộc nhau. Đánh dấu `BLOCKED: <lý do>` cuối dòng khi bị chặn.
Phạm vi: spec Amendment 2 (AC-13, AC-14, AC-19; NFR-3, NFR-8), `design-amd2.md` (thay `design.md`), ADR-024. Cỡ M. 16 task: T1–T15 giao dev, T16 của tech-lead.
`cmd.test_one` = lệnh của profile với `{file}` là file ở `test:`. Mọi task: test đỏ trước (STD-TEST-1), chỉ sửa trong `files:`, không skip/xfail. Tên hàm, hằng, chuỗi chính xác: `plan.md` mục Ràng buộc chung và `design-amd2.md` §2–§4. Task sửa `*.json` của DocType: chạy `cmd.migrate` rồi mới `cmd.test_one`.

Ký hiệu `F4-T<n>` = task `T<n>` trong `docs/team/features/FEAT-004/tasks.md`. Build FEAT-005 chỉ bắt đầu khi FEAT-004 build xong, nên mọi `F4-T<n>` đã merge; `depends:` vẫn nêu để dev biết file đó FEAT-004 vừa sửa: đọc mã thật trên nhánh nền trước, giữ nguyên hành vi và test của nó (STD-TEST-5), chỉ thêm; chữ ký thật khác chữ ở đây → `DESIGN_CONFLICT`.

Nhánh nền: `team/FEAT-004` sau khi build xong (F4-T34 đã tick). Khi đó tech-lead tạo `team/FEAT-005` từ đầu nhánh đó, ghi mã commit thật vào dòng BASE dưới, chạy `cmd.test` (phải xanh) trước T1.
Tiến độ: BASE ghi ở đây trước mỗi lần gọi dev.
- BASE nhánh nền = team/FEAT-004 @ <chưa có: ghi mã commit khi tạo nhánh>
- baseline: <ghi test đỏ sẵn có của nhánh nền, nếu có, khi tạo nhánh>

## Phần 1, ảnh chụp trước/sau ở tool ghi (AC-13, NFR-3)

- [ ] T1 — `site_api._snapshot`: hình dạng ảnh chụp, bỏ trường mật và trường hệ thống — files: erp_ai/agent/tools/site_api.py, erp_ai/agent/tools/test_site_api.py — test: erp_ai/agent/tools/test_site_api.py — depends: F4-T62
  - Criterion: AC-13 (a), A-12; design-amd2 §2 "Ảnh chụp"
  - Receives: `_is_secret(meta, fieldname)`, `SYSTEM_FIELDS` (F4-T62 và mã hiện có)
  - Returns: `SNAPSHOT_TABLES = {"User": ("roles",)}`; `_snapshot(doc, fields) -> dict` = `{"name": str, <trường>: giá trị, <bảng con>: [dòng, …]}`; User luôn chỉ `name` và `roles`; dòng con bỏ `name`, `idx`, `parent`, `parentfield`, `parenttype`, `owner`, `creation`, `modified`, `modified_by`, `doctype`, giữ thứ tự `idx`; bỏ mọi trường `_is_secret` ở cha và con; giá trị qua `json.loads(frappe.as_json(v))`; không cắt
  - Expect: `cmd.test_one` → `test_snapshot_drops_secret_and_system_fields` (gieo khóa giả ở cha và dòng con → 0 lần), `test_user_snapshot_only_name_and_roles` xanh; test của F4-T59..T62 xanh nguyên

- [ ] T2 — Bốn tool ghi trả `_snapshot` khi `ok=true` — files: erp_ai/agent/tools/site_api.py, erp_ai/agent/tools/test_site_api.py — test: erp_ai/agent/tools/test_site_api.py — depends: T1
  - Criterion: AC-13 (a), NFR-3; design-amd2 §3.1, §4.1
  - Receives: `_snapshot`, `SNAPSHOT_TABLES` (T1); `create_record`, `update_record`, `delete_record`, `submit_record`, `_write`
  - Returns: kết quả `ok=true` có thêm `_snapshot: {"before": dict|None, "after": dict|None}`. Tập trường: tạo/sửa = khóa của `values` ∪ `SNAPSHOT_TABLES.get(doctype, ())`; xóa = mọi trường có giá trị kể cả bảng con; submit/hủy = `docstatus`. Sửa: `before` chụp từ doc vừa nạp, trước `doc.update`, `after` sau `save()`. Tạo: `before=None`. Xóa: `after=None`. `ok=false` hoặc tool sập: không có khóa `_snapshot`. `call_method` không trả `_snapshot`. Khóa `value_before`/`value_after` của F4-T62 không đổi
  - Expect: `test_delete_and_submit_snapshot_shapes` (kèm ca tạo `before is None`), `test_refused_or_failed_write_has_no_snapshot` (mỗi tool một ca từ chối, có ca đối chứng `ok=true` mang `_snapshot`) xanh

## Phần 2, runner ghi ảnh chụp và hoàn tác lượt (AC-13, NFR-3, ADR-024 QĐ 2)

- [ ] T3 — `runner.GENERIC_WRITE_TOOLS` và `_record_snapshot` với khóa `"<tool>#<n>"` — files: erp_ai/agent/runner.py, erp_ai/agent/test_agent_runner.py — test: erp_ai/agent/test_agent_runner.py — depends: T2, F4-T63, F4-T64
  - Criterion: AC-13 (c), (d), ca kiểm (1), (5); design-amd2 §2, §3.1, §3.2, §4.1
  - Receives: `_snapshot` trong kết quả tool (T2); `WRITE_TOOL_TARGETS`, `_run_tool(block, context, actions, before, after, tool_errors, skipped)`, `_action(...)` (F4-T64)
  - Returns: `GENERIC_WRITE_TOOLS`: tuple suy ra từ `WRITE_TOOL_TARGETS` (tool có DocType `None`), không viết tay; `_record_snapshot(name, outcome, n, before, after) -> None`, gọi ngay sau `actions.append(...)` với `n = len(actions)`: `name ∈ GENERIC_WRITE_TOOLS` và có `_snapshot` → `before[f"{name}#{n}"]`, `after[f"{name}#{n}"]`; luôn `outcome.pop("_snapshot", None)` trước `json.dumps` của `tool_result`. Khóa cũ theo tên tool phiếu giữ nguyên
  - Expect: `test_create_user_snapshot_lists_both_roles`, `test_two_calls_same_tool_one_turn_two_snapshots` (thêm ca: lời gọi đầu bị từ chối, lời gọi thứ hai thành công → khóa `#2`, không có `#1`), `test_snapshot_never_reaches_model` (chuỗi `_snapshot` 0 lần trong mọi `tool_result` gửi Cổng giả) xanh; test của F4-T63, F4-T64 xanh nguyên

- [ ] T4 — Test AC-13: hiệu bảng con và trường 30.000 ký tự — files: erp_ai/agent/test_agent_runner.py — test: erp_ai/agent/test_agent_runner.py — depends: T3
  - Criterion: AC-13 (a), (b), (c), ca kiểm (2), (3), (4); NFR-3
  - Receives: khóa `"<tool>#<n>"` trong `value_before`/`value_after` của dòng `reason` (T3)
  - Returns: ba test, không sửa mã sản phẩm
  - Expect: `test_update_user_role_list_diff_shows_removed_and_added` (role giữ nguyên không nằm trong hiệu), `test_holiday_list_missing_old_date_seen_in_diff`, `test_30000_char_field_stored_byte_identical` xanh trên mã T1–T3. Task chỉ thêm test: test nào đỏ → dán đầu ra và trả `DESIGN_CONFLICT` (lỗi nằm ở T1–T3), không sửa ngoài `files:`

- [ ] T5 — Hoàn tác lượt trong `_reason` bằng savepoint — files: erp_ai/agent/runner.py, erp_ai/agent/test_agent_runner.py — test: erp_ai/agent/test_agent_runner.py — depends: T4
  - Criterion: NFR-3; ADR-024 QĐ 2 và Ràng buộc "Test (Quyết định 2)"; design-amd2 §4.1
  - Receives: `_reason(...)`, `_call_model`, `run_for_ticket`, `run_log.write_entry`, `_record_snapshot` (T3)
  - Returns: `REASON_TURN_SAVEPOINT = "erp_ai_reason_turn"`; mỗi lượt đặt `frappe.db.savepoint(REASON_TURN_SAVEPOINT)` ngay sau khi `_call_model` trả về; từ chạy tool tới hết `write_entry` của lượt nằm trong `try`; `except Exception`: `_undo_turn()` rồi `raise` (giữ ngoại lệ gốc); `_undo_turn()` = `frappe.db.rollback(save_point=REASON_TURN_SAVEPOINT)`; lượt thành công không `release`. Nhánh `GatewayError` và quy tắc "không rollback" của `run_for_ticket` không đổi
  - Expect: `test_write_entry_failure_undoes_turn_role_change` (`api_update_record` thêm role ok, `write_entry` của lượt ném → User không có role, 0 dòng `reason` của lượt, có Error Log `TITLE_RUN_FAILED`), `test_snapshot_handling_failure_undoes_turn` (`_record_snapshot` ném, cùng kết quả) xanh; lỗi giả bằng `unittest.mock.patch`

- [ ] T6 — `_undo_turn` khi savepoint đã mất: giữ ngoại lệ gốc — files: erp_ai/agent/runner.py, erp_ai/agent/test_agent_runner.py — test: erp_ai/agent/test_agent_runner.py — depends: T5
  - Criterion: ADR-024 QĐ 2, QĐ 5 (đường DDL, chấp nhận); design-amd2 §4.1 `_undo_turn`
  - Receives: `_undo_turn()`, `REASON_TURN_SAVEPOINT` (T5); `LOGGER_NAME`
  - Returns: rollback savepoint ném lỗi → bắt (chú thích lý do, STD-ERR-1), `frappe.logger(LOGGER_NAME).warning("reason turn undo failed run_id=%s error=%s", …)` chỉ với tên lớp lỗi, không ném lỗi mới; ngoại lệ gốc đi tiếp
  - Expect: `test_lost_turn_savepoint_keeps_original_error` (rollback savepoint ném → Error Log ghi lớp lỗi gốc, không ném ra khỏi `run_for_ticket`) xanh

## Phần 3, mốc "đã báo tới đâu" (ADR-024 QĐ 3.1, 3.2)

- [ ] T7 — Trường `privilege_alert_checked_until` trên ERP AI Setting, khôi phục khi người lưu — files: erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json, erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py, erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py, erp_ai/tests/test_doctype_descriptions.py — test: erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py — depends: F4-T65
  - Criterion: design-amd2 §2 (mốc), §5, §6; ADR-024 QĐ 3.1, 3.2
  - Receives: `restore_self_managed_fields` (đang khôi phục `spent_this_month_usd`); `DOCTYPE_CONFIG["ERP AI Setting"]` trong `test_doctype_descriptions.py` (`field_count`, `read_only_fields`, `phrases`)
  - Returns: trường `privilege_alert_checked_until`: Datetime, `read_only`, ở `section_alerts` ngay sau `alert_recipients`, mô tả tiếng Việt ≤ 400 ký tự nói hệ thống tự ghi; `restore_self_managed_fields` đặt lại trường từ `frappe.db.get_single_value(SETTING_DOCTYPE, "privilege_alert_checked_until", cache=False)`; `DOCTYPE_CONFIG`: `field_count` +1 so với số thật trên nhánh nền (dự kiến 27 → 28), thêm tên trường vào `read_only_fields` và một dòng `phrases`; `section_count` không đổi
  - Expect: `cmd.migrate` (dán đầu ra; 0 DDL) rồi `cmd.test_one` → `test_privilege_alert_watermark_restored_on_human_save` (người lưu form với mốc khác → DB không đổi) xanh; `cmd.test_one` với erp_ai/tests/test_doctype_descriptions.py xanh
  - Ghi chú: `test_doctype_descriptions.py` không có trong bảng touchpoint của `design-amd2.md` §7 nhưng test đếm trường sẽ đỏ nếu không sửa (xem `plan.md` mục Rủi ro)

## Phần 4, cảnh báo đọc từ nhật ký (AC-14, AC-19, NFR-8)

- [ ] T8 — Cảnh báo đọc ERP AI Log trong cửa sổ `(mốc, cận trên]`: mục bản ghi phân quyền — files: erp_ai/tasks.py, erp_ai/tests/test_tasks.py — test: erp_ai/tests/test_tasks.py — depends: T3, T7
  - Criterion: AC-14 ca (4), (6), (7); ADR-024 QĐ 1, QĐ 3.3, 3.6; design-amd2 §2 "Cách đọc", §3.3, §4.2 bước 2–4
  - Receives: `runner.GENERIC_WRITE_TOOLS` (T3, import, không viết tay tên `api_*`); khóa `"<tool>#<n>"` (T3); trường mốc (T7); `_list_names`, `_raise_alarm`, `PERMISSION_DOCTYPES`
  - Returns: `check_privilege_escalation(now: datetime | None = None) -> None`; `PRIVILEGE_ALERT_SETTLE_S = 300`; `upper = (get_datetime(now) if now else now_datetime()) - timedelta(seconds=PRIVILEGE_ALERT_SETTLE_S)`; `lower = frappe.db.get_single_value(SETTING_DOCTYPE, "privilege_alert_checked_until", cache=False)`; `_privilege_changes_by_agent(lower, upper) -> list[str]` thay `_permission_records_by_agent` (xóa hàm cũ): đọc ERP AI Log `entry_type = "reason"`, `creation > lower` (bỏ khi rỗng), `creation ≤ upper`, `actions like "%api_%"`, sắp `creation` tăng; `_load_snapshots(raw) -> dict`; mỗi mục hành động `ok` của tool ∈ `GENERIC_WRITE_TOOLS` trên DocType ∈ `PERMISSION_DOCTYPES` trừ `Has Role`, hoặc DocType `DocType` có `permissions` trước ≠ sau → 1 mục `<tạo|sửa|xóa|submit/hủy> <DocType> <tên> (người ra lệnh <instructor>, <YYYY-MM-DD HH:MM>)`; `instructor` rỗng → `không rõ`. Chưa ghi mốc (T11)
  - Expect: viết lại theo spec Amendment 2 (STD-TEST-5), gieo bằng `site_api` dưới tài khoản agent cộng `write_entry` đúng dạng, `setUp` đặt mốc T0 để loại dòng thật: `test_alarm_on_permission_records_modified_by_agent` (Role Profile, User Permission do bot), `test_permission_record_modified_by_someone_else_does_not_alarm` (role và Custom DocPerm do người → 0), `test_lists_at_most_five_names` (7 → 5 + "…và 2 mục khác"), `test_five_names_have_no_overflow_text`, `test_one_alarm_per_condition` (chỉ đổi phần gieo; vẫn 4); thêm ca trong `test_alarm_on_permission_records_modified_by_agent`: dòng nhật ký dựng tay cho DocType `DocType` có `permissions` khác → 1 mục, giống → 0 (không ghi DocType thật). Các test khác của file xanh nguyên, không sửa

- [ ] T9 — Mục thêm role và gỡ role của User — files: erp_ai/tasks.py, erp_ai/tests/test_tasks.py — test: erp_ai/tests/test_tasks.py — depends: T8
  - Criterion: AC-14 ca (1), (2), (5); A-18; design-amd2 §3.3, §4.2 bước 3, D-4
  - Receives: `_privilege_changes_by_agent(lower, upper)`, `_load_snapshots` (T8); ảnh chụp User = `{"name", "roles"}` (T1)
  - Returns: DocType `User`: so `roles` của before/after theo tên role (`Counter`), mỗi role thêm ra `thêm role <role> cho <user> (người ra lệnh <instructor>, <YYYY-MM-DD HH:MM>)`, mỗi role gỡ ra `gỡ role <role> của <user> (…)`; không khác → 0 mục
  - Expect: `test_bot_created_user_role_alarm_names_user_role_instructor`, `test_bot_removed_role_listed_as_removed`, `test_bot_resave_user_without_role_change_no_line` (bot lưu lại User có role do người cấp → 0 dòng cho user đó) xanh; test so đúng chữ

- [ ] T10 — Dấu `[QUẢN TRỊ]` và thứ tự mục — files: erp_ai/tasks.py, erp_ai/tests/test_tasks.py — test: erp_ai/tests/test_tasks.py — depends: T9
  - Criterion: AC-14 ca (3); A-19; ADR-024 Ràng buộc "Test (Quyết định 4)"; design-amd2 §3.3
  - Receives: mục role của T9; `site_api.FORBIDDEN_ROLES`
  - Returns: tiền tố `[QUẢN TRỊ] ` khi role ∈ `site_api.FORBIDDEN_ROLES`; thứ tự: `[QUẢN TRỊ]` trước, rồi thời điểm tăng; qua `_list_names` (5 mục)
  - Expect: `test_admin_role_marked_and_listed_first` ("Toàn quyền" bật, `api_update_record` thêm `System Manager`; có thêm 5 mục thường cũ hơn → mục `[QUẢN TRỊ]` vẫn nằm trong 5 mục hiện) xanh

- [ ] T11 — Ghi mốc đúng một chỗ, mốc không lùi — files: erp_ai/tasks.py, erp_ai/tests/test_tasks.py — test: erp_ai/tests/test_tasks.py — depends: T10
  - Criterion: AC-19 ca (1), (2), (3); NFR-8; ADR-024 QĐ 3.2–3.5; design-amd2 §4.2 bước 2, 5
  - Receives: `lower`, `upper`, `check_privilege_escalation(now)` (T8)
  - Returns: `_advance_privilege_watermark(upper) -> None`: hàm duy nhất ghi mốc, chỉ bằng `frappe.db.set_single_value(SETTING_DOCTYPE, "privilege_alert_checked_until", upper)`, không `save()`/`insert()` ERP AI Setting; gọi sau mọi điều kiện, trước commit của job (cùng giao dịch với cảnh báo); `lower` có và `upper ≤ lower` → điều kiện này 0 mục và không ghi mốc
  - Expect: `test_change_alarmed_on_next_run_only` (T+1h có, T+25h không), `test_change_after_two_missed_runs_alarmed_once` (T+49h có, T+73h không), `test_change_before_rollout_alarmed_on_first_run_only` (mốc rỗng; chỉ khẳng định mục gieo), `test_change_inside_settle_margin_waits_for_next_run` (thêm biên: `creation == upper` được báo lần này, `creation == lower` không báo lại), `test_upper_not_after_watermark_keeps_it` xanh; thời gian giả qua `now=` và `frappe.db.set_value(..., update_modified=False)` trên `creation`

- [ ] T12 — Fail-closed: ảnh chụp không dùng được ra mục "không có trước/sau" — files: erp_ai/tasks.py, erp_ai/tests/test_tasks.py — test: erp_ai/tests/test_tasks.py — depends: T11
  - Criterion: AC-14 ca (8); ADR-024 QĐ 1 (fail-closed) và Ràng buộc "Test (Quyết định 1)"; design-amd2 §3.3, §4.2 bước 3
  - Receives: `_load_snapshots(raw) -> dict` (T8), mục của T8–T10, mốc (T11)
  - Returns: `_load_snapshots` trả `{}` khi `ValueError`/`TypeError` (chú thích lý do bắt); với `User` hoặc DocType phân quyền mà ảnh chụp không dùng được (dòng cũ, khóa thiếu, JSON hỏng, không phải dict, `roles` không phải list) → 1 mục có đuôi `, không có trước/sau`; cột `actions` không đọc được → mục `ERP AI Log <tên dòng>, không có trước/sau`; không ném lỗi, không bỏ qua
  - Expect: `test_record_action_without_snapshot_listed`, `test_broken_snapshot_json_listed_without_before_after` (đúng 1 mục cho user đó; ba điều kiện kia vẫn chạy; mốc tiến; thêm ca dòng có `actions` hỏng → mục `ERP AI Log <tên dòng>, không có trước/sau`), `test_fake_key_never_in_privilege_alarm` (khóa giả trong ảnh chụp → 0 lần trong nội dung cảnh báo) xanh

- [ ] T13 — Khóa theo site, một giao dịch, dòng log của job — files: erp_ai/tasks.py, erp_ai/tests/test_tasks.py — test: erp_ai/tests/test_tasks.py — depends: T12
  - Criterion: AC-19, NFR-8; ADR-024 QĐ 3.5, 3.7; design-amd2 §4.2 bước 1, 5, 6
  - Receives: thân job sau T12; `filelock` của `frappe.utils.synchronization`; `TITLE_RUN_FAILED`, `LOGGER_NAME`
  - Returns: `PRIVILEGE_ALERT_LOCK = "erp_ai_privilege_alert"`, `PRIVILEGE_ALERT_LOCK_TIMEOUT_S = 60`; `with filelock(PRIVILEGE_ALERT_LOCK, timeout=PRIVILEGE_ALERT_LOCK_TIMEOUT_S)` (không `is_global`) bao cả thân job kể cả commit; `LockTimeoutError` → `log_error(TITLE_RUN_FAILED, "check_privilege_escalation lock busy")`, return, không chạy điều kiện nào; lỗi giữa job → rollback cả Error Log cảnh báo, Email Queue và mốc; `frappe.logger(LOGGER_NAME).info("check_privilege_escalation window=%s..%s changes=%d", …)` không có tên user hay role
  - Expect: `test_failed_run_keeps_watermark_and_realarms_once`, `test_busy_lock_skips_run_without_moving_watermark` (stub `filelock` ném `LockTimeoutError` → mốc giữ, 0 Email Queue mới) xanh; `test_error_is_logged_and_rolled_back_not_raised` hiện có xanh nguyên

## Phần 5, luật kiến trúc và đầu-cuối

- [ ] T14 — Luật kiến trúc của ADR-024 — files: erp_ai/tests/test_architecture.py — test: erp_ai/tests/test_architecture.py — depends: T13, F4-T68
  - Criterion: ADR-024 mục Ràng buộc (dòng 1–5); AC-14, AC-19
  - Receives: `runner.WRITE_TOOL_TARGETS`, `runner.GENERIC_WRITE_TOOLS` (T3); `tasks._advance_privilege_watermark` (T11); `run_log.write_entry`; cách viết luật của file (F4-T68)
  - Returns: hai test, không sửa mã sản phẩm
  - Expect: `test_privilege_alert_reads_shared_generic_write_tools` (mọi tool trong `WRITE_TOOL_TARGETS` có DocType `None` ∈ `GENERIC_WRITE_TOOLS`; `erp_ai/tasks.py` không có chuỗi `api_` của tên tool), `test_privilege_alert_watermark_and_clock_rules` (tên trường mốc chỉ ở JSON DocType, `erp_ai_setting.py`, đúng một hàm của `tasks.py`, và test; `tasks.py` không `save()`/`insert()` ERP AI Setting; job không có `datetime.now`, `utcnow`, `NOW()`; `erp_ai/**` trừ test không đọc `Version`; hàm điều kiện phân quyền không lọc `modified_by`/`owner`; `write_entry` giữ `insert` và `commit` trong cùng hàm) xanh. Mỗi luật chứng minh bắt được vi phạm bằng một chuỗi mẫu trong test, không sửa mã sản phẩm. Luật đỏ trên mã thật → dán đầu ra, trả `DESIGN_CONFLICT`

- [ ] T15 — Đầu-cuối: đổi role qua tool bản ghi được báo đúng một lần — files: erp_ai/agent/test_agent_runner.py — test: erp_ai/agent/test_agent_runner.py — depends: T6, T13
  - Criterion: AC-14, AC-19, NFR-8 (đầu-cuối runner → nhật ký → job cảnh báo)
  - Receives: runner với Cổng model giả (T3–T6); `tasks.check_privilege_escalation(now=)` (T13)
  - Returns: một test, không sửa mã sản phẩm
  - Expect: `test_role_change_via_record_tool_alarmed_once`: runner chạy `api_update_record` thêm role → `check_privilege_escalation(now=T+1h)` có đúng 1 mục nêu user, role, người ra lệnh → chạy lại `now=T+25h` → 0 cảnh báo cho điều kiện này. Đỏ → dán đầu ra, trả `DESIGN_CONFLICT`

## Checkpoint cuối (tech-lead, không giao dev)

- [ ] T16 — Chạy `cmd.test`, `cmd.lint`, `cmd.migrate` lên/xuống/lên, kiểm DoD, `diff.patch` — files: docs/team/features/FEAT-005/diff.patch, docs/team/features/FEAT-005/tasks.md — test: `cmd.test` (cả app) — depends: T1..T15
  - Criterion: DoD phần build của spec Amendment 2; design-amd2 §6
  - Expect: `cmd.test` xanh (không test đỏ ngoài dòng `baseline:`), `cmd.lint` sạch; `cmd.migrate` lên/xuống/lên: số dòng ERP AI Log trước = sau, `has_field("privilege_alert_checked_until")` đúng; diff không có dấu skip của `test.skip_markers`, không chạm `protected_paths`; `grep -n 'Trạng thái' docs/team/adr/ADR-01[4-8].md` dán vào journal; ghi cho qa: bước kiểm múi giờ không DST (design-amd2 §6)

## Rút theo Amendment 2

52 task của plan 2026-11-12 (đối chiếu 2026-11-13) không còn hiệu lực; chưa task nào được làm. Chữ đầy đủ xem `git show 1918db2:docs/team/features/FEAT-005/tasks.md`. Dòng dưới cố ý không viết theo dạng ô đánh dấu để `team.py` không đếm.

| Task cũ | Số phận | Chỗ đi |
|---|---|---|
| T2 (hằng dùng chung) | viết lại | T3 (`GENERIC_WRITE_TOOLS`), T8 (hằng `PRIVILEGE_ALERT_*`) |
| T25 (đầu-cuối qua runner) | viết lại | T3, T4, T15 |
| T47, T48 (cảnh báo) | viết lại | T8–T13 (nguồn đổi từ `Version` sang ERP AI Log theo ADR-024) |
| T51 (ca AC-13) | viết lại | T3, T4 |
| T52 (kiểm cuối) | viết lại | T16 |
| T4, T5, T23, T24 (dòng nhật ký riêng cho mỗi lời gọi) | rút | `design-amd2.md` không cần; FEAT-004 AC-34 đã có mục trong cột hành động |
| T1, T3, T6..T22, T26..T46, T49, T50 | rút | tool theo từng việc, danh sách role được gán, quyền hẹp, luồng "ok": spec Amendment 2 bảng "AC cũ → giữ / rút / chuyển" |
