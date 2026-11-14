# Nghiệm thu FEAT-005 (Amendment 2)

- Commit kiểm: `03373f18af49bd77fd44eae0feea3d502367d41d` (nhánh `team/FEAT-005`, worktree `.claude/worktrees/feat-005`)
- Người kiểm: qa, `/team:verify FEAT-005 --decide`, 2026-11-14
- Cây làm việc lúc bắt đầu: chỉ `docs/team/adr/ADR-024.md`, `docs/team/features/FEAT-005/design-amd2.md` sửa chưa commit (chữ vòng 4, team-leader đã báo trước); không file nào dưới `erp_ai/` đổi.

## Bảng tiêu chí

Mọi lệnh dưới đây chạy trong **cùng một** lần giữ khóa (23:43:13–23:53:36), sau migrate lên 2, với Report `ERP AI Accuracy` tạm về JSON của nhánh và hai cài đặt để trống. Dạng lệnh: `cmd.test_one` có lọc theo tên, `PYTHONPATH=$W bench --site miyano run-tests --module <module> --test <tên> …`; log `…/scratchpad/qa5/named_<nhãn>.log`. "Ran N" = đúng số tên đã đưa nên từng test được chạy.

| Tiêu chí | Lệnh | Exit | Đầu ra | Test bao phủ | Kết luận |
|---|---|---|---|---|---|
| AC-13 (trước/sau gồm dòng con, hiệu bỏ/thêm, không cắt, riêng từng lời gọi) | `--module erp_ai.agent.test_agent_runner` + 6 `--test`; `--module erp_ai.agent.tools.test_site_api` + 4 `--test` | 0; 0 | `named ac13_runner … Ran 6 tests in 2.363s OK deadlock=0`; `named ac13_siteapi … Ran 4 tests in 1.361s OK deadlock=0` | runner: `test_create_user_snapshot_lists_both_roles` (1), `test_update_user_role_list_diff_shows_removed_and_added` (2, b), `test_holiday_list_missing_old_date_seen_in_diff` (3), `test_30000_char_field_stored_byte_identical` (4, c; biên 30.000 > 20.000), `test_two_calls_same_tool_one_turn_two_snapshots` (5, d), `test_snapshot_never_reaches_model` (c); site_api: `test_refused_or_failed_write_has_no_snapshot` (lỗi), `test_snapshot_drops_secret_and_system_fields`, `test_user_snapshot_only_name_and_roles`, `test_delete_and_submit_snapshot_shapes` (a) | **đạt** |
| AC-14 (một cảnh báo, chữ mỗi mục, `[QUẢN TRỊ]` đứng đầu, 5 mục + "…và N mục khác", 0 dòng cho ca người/không đổi role, ba điều kiện kia giữ nguyên, 0 khóa) | `--module erp_ai.tests.test_tasks` + 13 `--test`; `--module erp_ai.agent.test_runner_routing --test test_privilege_findings_unchanged`; `--module erp_ai.tests.test_architecture --test test_privilege_alert_reads_shared_generic_write_tools` | 0; 0; 0 | `named ac14_tasks … Ran 13 tests in 3.038s OK deadlock=0`; `named ac14_routing … Ran 1 test in 1.571s OK deadlock=0`; `named ac14_arch … Ran 1 test in 0.373s OK deadlock=0` | `test_bot_created_user_role_alarm_names_user_role_instructor` (1), `test_bot_removed_role_listed_as_removed` (2), `test_admin_role_marked_and_listed_first` (3), `test_lists_at_most_five_names` (4, biên 7), `test_five_names_have_no_overflow_text` (4, biên 5), `test_bot_resave_user_without_role_change_no_line` (5), `test_permission_record_modified_by_someone_else_does_not_alarm` (6), `test_alarm_on_permission_records_modified_by_agent`, `test_doctype_write_without_permissions_change_not_listed`, `test_record_action_without_snapshot_listed`, `test_broken_snapshot_json_listed_without_before_after` (fail-closed), `test_one_alarm_per_condition` (7), `test_fake_key_never_in_privilege_alarm` (8); FEAT-006 `test_privilege_findings_unchanged`; kiến trúc | **đạt** |
| AC-19 (báo đúng 1 lần: T+1h/T+25h, lỡ hai ngày T+49h/T+73h, thay đổi trước triển khai) | `--module erp_ai.tests.test_tasks` + 8 `--test`; `--module erp_ai.agent.test_agent_runner --test test_role_change_via_record_tool_alarmed_once`; `--module …erp_ai_setting.test_erp_ai_setting --test test_privilege_alert_watermark_restored_on_human_save`; `--module erp_ai.tests.test_architecture --test test_privilege_alert_watermark_and_clock_rules` | 0; 0; 0; 0 | `named ac19_tasks … Ran 8 tests in 1.772s OK deadlock=0`; `named ac19_runner … Ran 1 test in 0.747s OK deadlock=0`; `named ac19_setting … Ran 1 test in 0.116s OK deadlock=0`; `named ac19_arch … Ran 1 test in 0.568s OK deadlock=0` | `test_change_alarmed_on_next_run_only` (1), `test_change_after_two_missed_runs_alarmed_once` (2), `test_change_before_rollout_alarmed_on_first_run_only` (3), `test_empty_watermark_reads_from_the_start` (3, ba dạng mốc thô rỗng), `test_change_inside_settle_margin_waits_for_next_run` (biên 300 s), `test_failed_run_keeps_watermark_and_realarms_once` (lỗi), `test_busy_lock_skips_run_without_moving_watermark` (lỗi), `test_upper_not_after_watermark_keeps_it` (biên); đầu-cuối `test_role_change_via_record_tool_alarmed_once` | **đạt** |
| NFR-3 (100% lần ghi thành công có cặp trước/sau đầy đủ và người ra lệnh; lượt lỗi không để lại ghi không nhật ký) | `--module erp_ai.agent.test_agent_runner` + 7 `--test` (hoàn tác lượt); cộng 5 test bản ghi thật đỏ một lần sau merge T3 (dưới) | 0; 0 | `named nfr3_runner … Ran 7 tests in 3.298s OK deadlock=0`; `named t3five … Ran 5 tests in 3.779s OK deadlock=0` | `test_write_entry_failure_undoes_turn_role_change`, `test_snapshot_handling_failure_undoes_turn`, `test_lost_turn_savepoint_keeps_original_error`, `test_turn_writes_propose_rows_only_after_its_reason_row`, `test_propose_then_role_change_then_failure_undoes_both`, `test_role_change_then_propose_then_failure_undoes_both`, `test_propose_row_failure_after_reason_row_keeps_turn`; `test_record_tool_action_carries_before_after_and_instructor`; cộng hàng AC-13 | **đạt** |
| NFR-8 (0 sót, 0 báo hai lần qua các lần chạy liên tiếp, kể cả lịch lỡ; đo bằng "Test AC-19") | như hàng AC-19 (cùng lần chạy, `named ac19_tasks`, `named ac19_runner`) + đọc engine bảng: `engine.py` dưới khóa (23:55:22, chỉ đọc `information_schema`) | 0; 0 | `Ran 8 tests … OK`, `Ran 1 test … OK` (trên); `tabEmail Queue: InnoDB`, `tabERP AI Log: InnoDB`, `tabError Log: MyISAM`, `tabSingles: InnoDB` | các test AC-19; `test_failed_run_keeps_watermark_and_realarms_once` khẳng định sau lần chạy lỗi: thư 0, mốc giữ, rồi lần sau đúng 1 thư | **đạt** theo cách đo của spec (thư + mốc). Kênh Error Log sau một lần chạy **lỗi** có thể có dòng cảnh báo thứ hai: engine thật trên `miyano` xác nhận `tabError Log: MyISAM` (không rollback được). Đây là quyết định (decide) T13 đã ghi, design-amd2 §4.2 bước 5 và ADR-024 QĐ 3.5 (vòng 4) đã nói rõ; ghi ở "Rủi ro còn lại" R-1 để người thấy ở G4 |

**Năm test bản ghi thật đỏ một lần sau merge T3** (review-03, round 6 của tasks.md), chạy lại theo tên trên commit này: `--module erp_ai.agent.test_agent_runner --test test_fake_secret_never_in_actions_column --test test_position_counts_every_action_not_only_the_same_tool --test test_record_tool_action_carries_before_after_and_instructor --test test_record_tool_runs_for_real_and_the_log_names_the_record --test test_two_calls_same_tool_one_turn_two_snapshots` → exit 0, `Ran 5 tests in 3.779s OK deadlock=0`. Cả năm cũng nằm trong lượt cả app `OK` dưới. Không lặp lại.

**Chất lượng test (đọc mã test, không sửa):** các test bao phủ khẳng định bằng giá trị viết cứng và so nguyên khối: `test_create_user_snapshot_lists_both_roles` so `value_before == {"api_create_record#1": None}`, khóa của ảnh chụp đúng `["name", "roles"]`, danh sách role đúng thứ tự; `test_30000_char_field_stored_byte_identical` so từng byte UTF-8 của trước và sau và khẳng định `LONG_FIELD_CHARS > TOOL_RESULT_MAX_CHARS`; `test_lists_at_most_five_names` so nguyên chuỗi cảnh báo; `test_change_after_two_missed_runs_alarmed_once` khẳng định `[1, 0]` và mốc `= next_run − 300 s`. Bỏ hành vi thì các khẳng định này đỏ; nhật ký build ghi các lượt đột biến đỏ của từng task (tasks.md round 1–31). Không thấy test nào không thể đỏ.

## Lệnh chung (cmd.*)

| Lệnh | Exit | Đầu ra |
|---|---|---|
| `cmd.test` = `PYTHONPATH=$W bench --site miyano run-tests --app erp_ai` (trong khóa, 23:44:29–23:52:39) | 0 | `Ran 1564 tests in 488.122s` / `OK`; `deadlock lines: 0`; không có ca đỏ nên không có lượt chạy lại |
| `cmd.lint` = `pre-commit run --all-files`, trên bản clone tạm ở `03373f18…` (`…/scratchpad/qa5/lint`, để không hook nào sửa file của worktree) | 0 | 12 hook `Passed` (check merge conflicts, check json, check python ast, check toml, check yaml, debug statements, eslint, prettier, ruff formatter, ruff import sorter, ruff linter, trim trailing whitespace); `git status --porcelain` của bản clone rỗng (không file nào bị sửa) |
| `cmd.typecheck` | — | slot rỗng trong `.team/profile.json`, không áp dụng |
| `cmd.build` = `bench build --app erp_ai` | không chạy | diff không có file frontend (`public/`, `.js`, `.vue`: 0); lệnh build chạy trên cây chính (`develop`), không phải commit này, nên không chứng minh gì cho nhánh |

**Trả lại site sau lần giữ khóa (đọc lại):**
- `MATCH report: recorded={"roles": ["System Manager", "ERP AI Instructor"], "modified": "2026-11-14 12:00:02", …} now={… giống hệt …}`
- `MATCH auto_assign_enabled: recorded={"api": 1, "raw": "1"} now={"api": 1, "raw": "1"}`
- `MATCH code_change_apps: recorded={"api": "frappe\nerpnext\nhelpdesk\nhrms", …} now={… giống hệt …}`
- `RESTORE MATCH`; `erp_ai/ working-tree changes: feat-005=0 feat-007=0 main=0`; `LOCK RELEASE` 23:53:36.
- Không trả lại (ngoài phạm vi ba mục): lược đồ site ở trạng thái FEAT-005 (`has_field: true`; trước lần giữ khóa là `false`, trạng thái `develop`); hai DocType của FEAT-007 bị migrate xóa như "Orphaned" (xem mục Migration). Error Log tăng 1027 → 1070 (3 dòng do ba lần migrate, 40 dòng do lượt test; `tabError Log` MyISAM nên dòng do test ghi ở lại, đã có ở debt.md dòng FEAT-005 "minor hoãn").

## Migration lên/xuống/lên

Một lần giữ khóa `flock -w 1800 .team/miyano-site.lock`, bắt đầu `2026-11-14 23:43:13`, script `/tmp/claude-1000/-home-miyano-frappe-bench-apps-erp-ai/6c38287b-bf21-45d8-bbe6-babd0767ec62/scratchpad/qa5/hold.sh` (chép từ `t16/hold.sh` của tech-lead, thêm đọc mốc qua `read_privilege_watermark()`, đếm Error Log, bước múi giờ, các lượt chạy theo tên). Log: `…/scratchpad/qa5/hold.log`. Kiểm trước khi đổi gì: `off-lock check 1: <none>`, cây chính `develop 7a134ae` sạch dưới `erp_ai/`, `feat-005 erp_ai/ changes: 0`.

Số mong đợi (design-amd2 §6): ERP AI Log trước = sau; `has_field` True/False/True; mốc thô không có dòng hoặc rỗng, `read_privilege_watermark()` là `None`; 0 DDL (Single).

| Bước | Lệnh | Exit | `has_field` | ERP AI Log | mốc thô | `read_privilege_watermark()` |
|---|---|---|---|---|---|---|
| Ghi lại (trước) | `site.py state` | 0 | `false` | 42 | `<no row>` | `<ValidationError>` (trường chưa có) |
| Lên 1 (worktree feat-005) | `PYTHONPATH=$W bench --site miyano migrate` (`cmd.migrate`) | 0 | `true` | 42 | `<no row>` | `None` |
| Xuống (cây chính `develop`) | `env -u PYTHONPATH bench --site miyano migrate` | 0 | `false` | 42 | `<no row>` | `<ValidationError>` |
| Lên 2 (worktree feat-005) | `PYTHONPATH=$W bench --site miyano migrate` | 0 | `true` | 42 | `<no row>` | `None` |

- Dòng trong log migrate: `migrate_up1: Orphaned=1 ALTER=0 Traceback=0`, `migrate_down: Orphaned=0 ALTER=0 Traceback=0`, `migrate_up2: Orphaned=0 ALTER=0 Traceback=0` → 0 `ALTER TABLE` (đúng "0 DDL").
- Dòng "Orphaned" ở lên 1: `Orphaned DocType(s) found: ERP AI User Template, ERP AI Catalog Rule` — hai DocType của `team/FEAT-007` (`git ls-tree` thấy 6 file ở `team/FEAT-007`, 0 ở `develop` và `team/FEAT-006`), có mặt trên site vì phiên FEAT-007 đã migrate trước. Lần T16 của tech-lead cũng có đúng dòng này. Đây là hiệu ứng site dùng chung, không phải mã FEAT-005; migrate kế tiếp của FEAT-007 tạo lại.
- Đối chiếu: ERP AI Log 42 = 42 = 42 = 42. Lên/xuống/lên: **đạt**.
- Múi giờ (design-amd2 §6, ADR-024 QĐ 3.6): `System Settings.time_zone='Asia/Ho_Chi_Minh' year=2026 dst(01-01)=0:00:00 dst(07-01)=0:00:00` → `TZ NO-DST`. **Đạt** (cả hai là 0).

## Grep diff so với develop

Lệnh: `git diff develop...HEAD -- erp_ai` (merge-base `eda2c9d`; `develop` = `7a134ae`). 12 file, `3574 insertions(+), 111 deletions(-)`.

- Dấu skip (`test.skip_markers`) trên dòng thêm: `git diff develop...HEAD -- erp_ai | grep -nE '^\+.*(@unittest\.skip|@unittest\.skipIf|@unittest\.expectedFailure|\.skipTest\()'` → không dòng nào, exit 1. **0 dấu skip mới.**
- Dòng assert bị xóa: 5; dòng assert thêm: 269. Năm dòng xóa:
  - `test_runner_routing.py`: `-self.assertEqual(self._findings(), before)` → thay bằng `self.assertEqual(after["privilege_changes"], [])` rồi `self.assertEqual(after, before)` (vẫn so cả dict, thêm một khẳng định). Không nới.
  - `test_tasks.py` (helper `_permission_records_by_agent` cũ, AC-14 viết lại theo STD-TEST-5): `assertIn(name, …)`, `assertEqual(sum(name in message …), 5)` + `assertIn("…và 2 mục khác", …)`, `assertNotIn("mục khác", …)` → thay bằng `assertEqual` so **nguyên chuỗi** cảnh báo (5 mục + " …và 2 mục khác"; đúng 5 mục không có phần đuôi). Chặt hơn, không nới.
- `protected_paths` trong diff: `git diff --name-only develop...HEAD | grep -E '(^|/)\.env|\.pem$|\.key$|license\.txt$'` → không dòng nào, exit 1.
- File frontend (`public/`, `.js`, `.vue`) trong diff: không có (exit 1).

## DoD (bản có hiệu lực, Amendment 2) và checklist nghiệm thu

| Mục DoD | Bằng chứng | Trạng thái |
|---|---|---|
| AC-13, AC-14, AC-19 đạt, đầu ra dán ở đây; NFR-3, NFR-8 đạt | bảng tiêu chí | đạt |
| FEAT-004 AC-35 đạt trước test AC-13 (A-20) | `docs/team/features/FEAT-004/acceptance.md:66` hàng AC-35 "đạt", dòng cuối `Verdict: accepted` | đạt |
| Mỗi AC có ≥ 1 test tự động; không skip/xfail; test cũ của ba điều kiện kia xanh nguyên | bảng tiêu chí; grep skip 0 dòng; `test_one_alarm_per_condition` và lượt cả app `OK` | đạt |
| `cmd.test` xanh; `cmd.lint` sạch | `Ran 1564 tests in 488.122s` / `OK`; lint exit 0, 12 `Passed` | đạt |
| Diff không chạm `protected_paths`, không bí mật | grep `protected_paths` 0 dòng; grep chuỗi khóa/mật khẩu dạng gán literal trên dòng thêm: 0 dòng | đạt |
| Trạng thái ADR-014..018 | `grep -n 'Trạng thái' docs/team/adr/ADR-01[4-8].md` → ADR-014, 015, 017 "bị thay"; ADR-016, 018 "một phần" | đạt |
| CI xanh | `git ls-remote --heads origin team/FEAT-005` → rỗng (nhánh chưa push); `gh run list --branch team/FEAT-005` → không lần chạy nào. `ci.yml` chạy khi push `develop` / PR | **chưa tới lượt**: CI chạy khi tech-lead merge vào `develop` và push; chủ: tech-lead. Lệnh CI chạy (`run-tests`, `pre-commit`) đã xanh tại chỗ trên commit này |
| Sau G4: As-Built, README/tài liệu người dùng, CHANGELOG | — | việc sau G4, chủ: writer (`/team:asbuilt`); không tính là lỗi |

Checklist nghiệm thu 6/6: (1) mọi tiêu chí có lệnh, exit, đầu ra trên commit đã ghi; (2) có ca biên/lỗi (30.000 ký tự, 5/7 mục, 300 s, lỡ hai ngày, lần chạy lỗi, khóa bận, mốc rỗng ba dạng); (3) chất lượng test đã đọc; (4) `cmd.test`, `cmd.lint` exit 0 (`typecheck` rỗng, `build` không áp dụng); (5) grep skip/assert/`protected_paths` đã dán; (6) migrate lên/xuống/lên và đối chiếu số dòng. `ui: false` nên không có mục UI.

## Rủi ro còn lại

- **R-1 NFR-8 ở kênh Error Log sau một lần chạy lỗi.** Thư (Email Queue) và mốc rollback cùng nhau nên thư đúng một lần; dòng Error Log "Agent đã sửa bản ghi phân quyền" của lần chạy lỗi ở lại vì `tabError Log: MyISAM` (đọc thật trên `miyano`, 23:55:22), lần sau ghi thêm một dòng → cùng thay đổi xuất hiện hai lần trong Error Log (lặp, không sót; ADR-024 QĐ 3.8). Theo quyết định (decide) T13; architect đã nêu: nếu người coi NFR-8 gồm cả Error Log thì cần amendment. Người xem ở G4; As-Built ghi lại.
- **R-2 design-amd2 §3.3, mục User có ảnh chụp không dùng được.** Dòng `sửa User <user> (…), không có trước/sau` không mang `[QUẢN TRỊ]` (không biết role) nên xếp sau nhóm quản trị và có thể bị đẩy vào "…và N mục khác" dù có thể che một lần cấp role quản trị. Thiết kế chưa quyết (debt.md dòng FEAT-005 review-12). Đầy đủ vẫn tra được ở nhật ký.
- **R-3 Các dòng FEAT-005 còn mở trong `docs/team/debt.md`:** (a) `_undo_turn` dừng ở callback `after_rollback` đầu tiên ném lỗi (review-06); (b) chữ ký `_undo_turn(run_id)` ở design §4.1 (vòng 4 đã sửa chữ, As-Built ghi đúng); (c) `ROUTE_SAVEPOINT`/`ROUTE_UNIT_SAVEPOINT` của FEAT-006 vẫn rò callback commit (review-05); (d) `design-defect` Error Log của review-13 = R-1; (e) R-2; (f) minor test hoãn (review-12..15: `{"role": ""}`, docstring `_real_alarms`, luật kiến trúc còn lọt); (g) test của cảnh báo dùng khóa file thật `erp_ai_privilege_alert`, scheduler chạy cùng lúc thì test chờ 60 s rồi đỏ "lock busy" (trông như chập chờn).
- **R-4 Site dùng chung.** Migrate từ một nhánh xóa DocType của nhánh khác ("Orphaned": `ERP AI User Template`, `ERP AI Catalog Rule` của FEAT-007) và để lại lược đồ của nhánh đó; mỗi lượt test để lại dòng Error Log (+40 lần này). Không phải lỗi mã FEAT-005.
- **R-5 Chưa có bằng chứng thật trên `miyano` với email cảnh báo** (spec "Success" sau G4: bot gán role cho user thử, thư hôm sau, hôm sau nữa không lặp) — phần đo thực tế của người sau G4.

## Kết luận

Năm tiêu chí của Amendment 2 đạt trên `03373f1` bằng lệnh chạy lại trong một lần giữ khóa; cả app `OK`, lint sạch, 0 dấu skip, assert không bị nới, migrate lên/xuống/lên khớp, múi giờ không DST. Khoảng hở Error Log của NFR-8 (R-1) là quyết định đã ghi, nằm ngoài cách đo của spec, và được nêu để người thấy ở G4; CI chạy khi merge.

Verdict: accepted
