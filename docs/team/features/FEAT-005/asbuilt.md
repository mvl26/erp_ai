Feature: FEAT-005 (Amendment 2)
Stage: asbuilt
Author-agent: writer
Date: 2026-11-15
Approved-by:
<!-- Cổng: G4 tắt (config.gates.G4_uat = false); qa `Verdict: accepted` ở acceptance.md. Dòng Approved-by để trống. -->

<!-- G5: người điền `Approved-by-prod: <tên> <YYYY-MM-DD>` lên đầu file trước khi lên prod. -->
# As-Built FEAT-005 (Amendment 2): trước/sau đầy đủ trong nhật ký, cảnh báo role/phân quyền đúng một lần

Mã: `team/FEAT-005` @ `03373f1` (worktree `.claude/worktrees/feat-005`), `diff.patch` = `develop...team/FEAT-005`. Phần mã: 12 file dưới `erp_ai/`, `3574 insertions(+), 111 deletions(-)`; không file frontend, không file mới, không đụng `hooks.py` và `erp_ai_log`. Nguồn: `spec.md` (Amendment 2), `design-amd2.md` (vòng 1–4; `design.md` chỉ còn là lịch sử), `ADR-024`, `tasks.md` (17/17), `review-01..15, 17`, `acceptance.md`, `docs/team/debt.md`.

Phạm vi sau Amendment 2: FEAT-005 chỉ còn hai việc, **nhật ký trước/sau của những gì bot đã ghi** (AC-13) và **cảnh báo hằng ngày về role/phân quyền do bot đổi** (AC-14, AC-19). Các AC còn lại của bản gốc đã chuyển sang FEAT-004 hoặc bị rút (`spec.md`, bảng "AC cũ → giữ / rút / chuyển").

## 1. Trạng thái nghiệm thu

- qa: `Verdict: accepted` trên `03373f18…` (`acceptance.md`, dòng cuối). Năm tiêu chí AC-13, AC-14, AC-19, NFR-3, NFR-8 **đạt**, mỗi tiêu chí chạy theo tên test trong cùng một lần giữ khóa site `miyano` (23:43:13–23:53:36).
- **Lượt cả app (copy từ `acceptance.md`, mục "Lệnh chung"):** `cmd.test` = `PYTHONPATH=$W bench --site miyano run-tests --app erp_ai` (trong khóa, 23:44:29–23:52:39): exit 0, `Ran 1564 tests in 488.122s` / `OK`; `deadlock lines: 0`; không có ca đỏ nên không có lượt chạy lại.
- `cmd.lint` (`pre-commit run --all-files`, trên bản clone tạm ở `03373f18…`): exit 0, 12 hook `Passed`, 0 file bị sửa. `cmd.typecheck`: slot rỗng. `cmd.build`: không chạy (diff không có file frontend).
- Migrate lên/xuống/lên trên `miyano`: `has_field` True/False/True, `ERP AI Log` 42 = 42 = 42 = 42, 0 `ALTER TABLE`; múi giờ `Asia/Ho_Chi_Minh` không DST (`dst` 01-01 và 07-01 đều 0:00:00).
- 0 dấu skip/xfail mới; 5 dòng assert bị xóa đều có chỗ thay chặt hơn hoặc bằng (AC-14 viết lại theo STD-TEST-5, so nguyên chuỗi cảnh báo); 0 file trùng `protected_paths`.
- **Chưa tới lượt:** CI xanh. Nhánh chưa push (`git ls-remote --heads origin team/FEAT-005` rỗng), CI chạy khi push `develop` hoặc mở PR (`acceptance.md`, DoD).
- Chưa có bằng chứng thật trên `miyano` với email cảnh báo (R-5): bước đo của người sau merge (mục 6).

## 2. Đã xây gì, theo từng tiêu chí

| Tiêu chí | Đã xây (chỗ trong mã) | Test bao phủ (đạt, `acceptance.md`) |
|---|---|---|
| **AC-13** trước/sau gồm dòng con, hiệu bỏ/thêm, không cắt, riêng từng lời gọi | Mỗi tool ghi chung thành công trả thêm `_snapshot {before, after}` (`erp_ai/agent/tools/site_api.py:251,298`). Runner ghi mỗi lời gọi vào `value_before`/`value_after` của dòng `reason` dưới khóa `"<tool>#<n>"` (n = vị trí của mục trong `actions`), nên hai lời gọi cùng tool không đè nhau; `pop` trước khi dựng `tool_result` nên ảnh chụp không vào ngữ cảnh model và không chịu trần 20.000 ký tự (`erp_ai/agent/runner.py:734-770`). Bảng con đi cùng: User chỉ có `name` và `roles` (A-12). Bỏ trường bí mật; không cắt. Tập tool dùng chung `GENERIC_WRITE_TOOLS` suy từ `WRITE_TOOL_TARGETS` (`runner.py:87`) | `test_create_user_snapshot_lists_both_roles`, `test_update_user_role_list_diff_shows_removed_and_added`, `test_holiday_list_missing_old_date_seen_in_diff`, `test_30000_char_field_stored_byte_identical` (biên 30.000 > 20.000), `test_two_calls_same_tool_one_turn_two_snapshots`, `test_snapshot_never_reaches_model`; `test_site_api`: `test_refused_or_failed_write_has_no_snapshot`, `test_snapshot_drops_secret_and_system_fields`, `test_user_snapshot_only_name_and_roles`, `test_delete_and_submit_snapshot_shapes` |
| **AC-14** một cảnh báo, chữ mỗi mục, `[QUẢN TRỊ]` đứng đầu, 5 mục + "…và N mục khác", 0 dòng cho ca người/không đổi role | `tasks._privilege_changes_by_agent(lower, upper)` (`erp_ai/tasks.py:182`) đọc dòng `reason` của `ERP AI Log` (không còn đọc `modified_by` của dòng `Has Role`), so `roles` trước/sau theo tên role (mỗi role thêm hoặc gỡ ra một mục), bản ghi phân quyền ra một mục; ảnh chụp không dùng được thì vẫn ra một mục `, không có trước/sau` (fail-closed). Dòng quản trị mang `[QUẢN TRỊ] ` (6 role của AC-14) và xếp trước; vẫn tối đa 5 mục qua `_list_names` (`tasks.py:94`). Ba điều kiện cảnh báo còn lại giữ nguyên | `test_bot_created_user_role_alarm_names_user_role_instructor`, `test_bot_removed_role_listed_as_removed`, `test_admin_role_marked_and_listed_first`, `test_lists_at_most_five_names` (biên 7), `test_five_names_have_no_overflow_text` (biên 5), `test_bot_resave_user_without_role_change_no_line`, `test_permission_record_modified_by_someone_else_does_not_alarm`, `test_alarm_on_permission_records_modified_by_agent`, `test_doctype_write_without_permissions_change_not_listed`, `test_record_action_without_snapshot_listed`, `test_broken_snapshot_json_listed_without_before_after`, `test_one_alarm_per_condition`, `test_fake_key_never_in_privilege_alarm`; FEAT-006 `test_privilege_findings_unchanged`; test kiến trúc |
| **AC-19** báo đúng một lần (T+1h/T+25h; lỡ hai ngày T+49h/T+73h; thay đổi trước triển khai) | Chỗ nhớ "đã báo tới đâu": trường `privilege_alert_checked_until` (Datetime, chỉ đọc) trên `ERP AI Setting` (`erp_ai_setting.json:265`), Single nên 0 DDL; một hàm đọc `read_privilege_watermark()` (`erp_ai_setting.py:62`), một hàm ghi `_advance_privilege_watermark` (`tasks.py:254`). Cửa sổ `(mốc, now − 300 s]` nối tiếp nhau; mốc chỉ tiến cùng giao dịch có cảnh báo, không bao giờ lùi; mốc rỗng thì đọc cả lịch sử một lần (`tasks.py:259-312`). Khóa `filelock` theo site (60 s) bao cả job. Người lưu form không dời được mốc (`erp_ai_setting.py:106`) | `test_change_alarmed_on_next_run_only`, `test_change_after_two_missed_runs_alarmed_once`, `test_change_before_rollout_alarmed_on_first_run_only`, `test_empty_watermark_reads_from_the_start` (3 dạng mốc thô rỗng), `test_change_inside_settle_margin_waits_for_next_run` (biên 300 s), `test_failed_run_keeps_watermark_and_realarms_once`, `test_busy_lock_skips_run_without_moving_watermark`, `test_upper_not_after_watermark_keeps_it`; đầu-cuối `test_role_change_via_record_tool_alarmed_once`; `test_privilege_alert_watermark_restored_on_human_save`; test kiến trúc |
| **NFR-3** 100% lần ghi thành công có cặp trước/sau và người ra lệnh; lượt lỗi không để lại ghi không nhật ký | Lượt của runner có savepoint `erp_ai_reason_turn` (`runner.py:111,647`); lỗi trước khi dòng `reason` commit thì `_undo_turn(run_id)` hoàn tác mọi ghi của lượt và bỏ callback commit của chúng (`runner.py:684`, ADR-024 QĐ 2). Dòng `propose` của FEAT-004 nay ghi **sau** dòng `reason` (`_write_propose_rows`, `runner.py:714`) để không commit giữa lượt | `test_write_entry_failure_undoes_turn_role_change`, `test_snapshot_handling_failure_undoes_turn`, `test_lost_turn_savepoint_keeps_original_error`, `test_turn_writes_propose_rows_only_after_its_reason_row`, `test_propose_then_role_change_then_failure_undoes_both`, `test_role_change_then_propose_then_failure_undoes_both`, `test_propose_row_failure_after_reason_row_keeps_turn`; `test_record_tool_action_carries_before_after_and_instructor` |
| **NFR-8** 0 sót, 0 báo hai lần qua các lần chạy liên tiếp, kể cả lịch lỡ | Cách làm như AC-19. Thư (Email Queue) và mốc cùng một giao dịch: lỗi thì rollback cả hai, lần sau thư gửi đúng một lần | Các test AC-19; `test_failed_run_keeps_watermark_and_realarms_once`. **Đạt theo cách đo của spec (thư + mốc); kênh Error Log có một khe, xem R-1** |

Lệnh và đầu ra từng dòng nằm ở `acceptance.md`; không chép lại ở đây ngoài dòng cả app ở mục 1.

## Differences from design

So với `design-amd2.md` bản hiện hành (đã gộp các sửa vòng 1–4). Mỗi hàng một mục thiết kế hoặc touchpoint; `file:dòng` là dòng trên `03373f1`. "Lý do" chỉ lấy từ `review-NN`, `tasks.md`, `debt.md`; không có thì "không ghi". Cách làm: writer đối chiếu tên file trong `diff.patch`, tên hàm và hằng bằng `grep` trên cây, và đọc các hunk `tasks.py`, `runner.py:640-770`, `site_api.py:251-363`; không đọc từng dòng của 5702 dòng diff, nhất là các file test.

### 3.1 Theo mục thiết kế

| Mục thiết kế | Thực tế | file:dòng | Lý do |
|---|---|---|---|
| 1. Bối cảnh, phạm vi | đúng; 0 file ngoài danh sách touchpoint trừ một file test phụ (mục 3.2) | `git diff --stat develop...HEAD -- erp_ai`: 12 file | — |
| 2. Dữ liệu: trường mốc, mốc rỗng = chưa báo lần nào, một hàm đọc | đúng | `erp_ai_setting.json:265`; `erp_ai_setting.py:62`; `tasks.py` không còn `datetime(1`, `EMPTY_DATETIME` (grep: 0 dòng) | vòng 2 của thiết kế (review-08) |
| 2. Dữ liệu: ảnh chụp, khóa `"<tool>#<n>"`, User chỉ `name` + `roles`, không cắt | đúng | `site_api.py:83,251`; `runner.py:765-770` | — |
| 3.1 `_snapshot` trong kết quả tool, runner `pop` | đúng | `site_api.py:298`; `runner.py:755` | — |
| 3.2 `GENERIC_WRITE_TOOLS` suy từ bảng; dòng `propose` ghi sau dòng `reason` | đúng | `runner.py:87,714` | vòng 3 của thiết kế (review-05, `design-defect` STD-ERR-7) |
| 3.3 Chữ mỗi mục cảnh báo, `[QUẢN TRỊ]`, `không rõ`, 5 mục | đúng; mã thêm hằng và hàm phụ không nêu tên trong thiết kế (`CHANGE_VERBS`, `PRIVILEGE_CHANGE_VERBS`, `NO_BEFORE_AFTER`, `UNKNOWN_INSTRUCTOR`, `_usable_snapshots`, `_role_changes`, `_is_permission_change`), không đổi hợp đồng chữ | `tasks.py:38-46,146,160-178` | không ghi (chi tiết cài đặt; test so đúng chữ đạt) |
| 3.4 `_privilege_changes_by_agent(lower, upper)` | đúng chữ ký; đọc `reason`, `creation` trong `(lower, upper]` | `tasks.py:182` | — |
| 3.5 `read_privilege_watermark()` | đúng | `erp_ai_setting.py:62` | — |
| 4.1 Ghi nhật ký, savepoint lượt, `_undo_turn` | đúng; chữ ký `_undo_turn(run_id)` khớp thiết kế đã sửa vòng 4 (bản đầu viết `_undo_turn()`) | `runner.py:647,684` | review-06 minor (1): `run_id` cần cho dòng warning (`debt.md`) |
| 4.1 `_undo_turn`: callback `after_rollback` ném lỗi | thiết kế chỉ nói "như `frappe.db.rollback()`"; mã chạy `frappe.db.after_rollback.run()` nên dừng ở callback đầu tiên ném lỗi, các callback rollback xếp sau không chạy. Thiết kế không nói có chạy tiếp phần còn lại hay không | `runner.py:703-709` | review-06; `debt.md` dòng FEAT-005 "điểm thiết kế hoãn (review-06, T6)" |
| 4.2 bước 1–4, 6 (khóa, cận trên, mốc rỗng, đọc dòng, fail-closed, log) | đúng | `tasks.py:259-312` | — |
| 4.2 bước 5: Email Queue, mốc và Error Log "cùng một giao dịch" | **khác**: `tabError Log` là MyISAM nên dòng Error Log cảnh báo không rollback; chỉ Email Queue và mốc rollback cùng nhau. Thiết kế đã sửa chữ ở vòng 4 cho khớp mã (mã không đổi, quyết định của tech-lead, không thêm task bù) | `tasks.py:245-251` (`_raise_alarm` → `alerts.send_alarm`, ghi Error Log trước khi gửi thư); `error_log.json:6` của Frappe; engine đọc thật `tabError Log: MyISAM` (`acceptance.md`, NFR-8) | review-13 `design-defect`; `tasks.md` round 24–25; `debt.md` |
| 4.2 đoạn "Vì sao báo đúng một lần" | **chưa khớp**: đoạn này nói mốc chỉ tiến cùng giao dịch có cảnh báo và đua không loại trừ được thì báo lặp, nhưng **không nói** dòng Error Log nằm ngoài giao dịch nên cũng có thể lặp sau một lần chạy lỗi. Chỗ đúng đã nằm ở bước 5 ngay trên đó; đoạn này chưa theo | `design-amd2.md:92` (so với `:90`) | không ghi (sót khi sửa vòng 4); cần designer sửa một câu |
| 5. Quyền | đúng: mốc chỉ job ghi, form khôi phục; bot không sửa được nhật ký | `erp_ai_setting.py:106` | — |
| 6. Migration | đúng: 0 DDL; up/down/up đạt; múi giờ không DST | `acceptance.md` mục "Migration" | — |
| 8. Test plan | đúng: mọi test của AC-13/14/19, NFR-3/8 chạy theo tên và đạt; test hoàn tác vòng 3 (callback) nằm trong lượt cả app `OK` | `acceptance.md` | — |
| Mục User có ảnh chụp không dùng được (§3.3) | thiết kế chưa quyết: dòng `sửa User <user> (…), không có trước/sau` không mang `[QUẢN TRỊ]` (không biết role) nên xếp sau nhóm quản trị và có thể bị đẩy vào "…và N mục khác" | `tasks.py:182-223` | review-12; `debt.md` (R-2) |
| D-8 bước phân loại (FEAT-006) | ngoài phạm vi thiết kế: `ROUTE_SAVEPOINT`/`ROUTE_UNIT_SAVEPOINT` vẫn rò callback commit | `runner.py:355-370,392-401` | review-05; `debt.md` (STD-ERR-7) |

### 3.2 Theo touchpoint (§7)

| Touchpoint | Thực tế | Ghi chú |
|---|---|---|
| `erp_ai/agent/tools/site_api.py` | đúng | 76 dòng đổi (`diff --stat`) |
| `erp_ai/agent/runner.py` | đúng | 134 dòng đổi; `_run_tool` không còn gọi `write_entry` cho `propose` (vòng 3) |
| `erp_ai/tasks.py` | đúng | 205 dòng đổi; `_permission_records_by_agent` bị xóa (grep: 0 dòng còn gọi) |
| `erp_ai_setting.json` / `erp_ai_setting.py` | đúng | 10 và 15 dòng đổi |
| `test_site_api.py`, `test_agent_runner.py`, `test_tasks.py`, `test_erp_ai_setting.py`, `test_architecture.py` | đúng | đều có trong diff |
| `erp_ai/agent/test_runner_routing.py` (FEAT-006) | đúng: chỉ `TestRoutingPermissions`, cùng commit xóa helper | 32 dòng đổi; luật thay ở design §8 |
| `erp_ai/tests/test_doctype_descriptions.py` | **thêm, ngoài danh sách §7**: 5 dòng, `field_count` của `ERP AI Setting` 27 thành 28, thêm `privilege_alert_checked_until` vào cụm từ bắt buộc của mô tả và vào danh sách trường chỉ đọc | hệ quả của trường mới (test đếm field của FEAT-003); review-07 ghi `test_doctype_descriptions` chạy xanh sau merge T7 |

Hành vi trong diff nằm ngoài spec: không thấy. Hai thay đổi người dùng có thể thấy mà spec Amd-2 chỉ nêu gián tiếp đều có chỗ trong thiết kế: thứ tự dòng `propose` (D-7) và hoàn tác lượt khi lỗi (QĐ 2).

## 4. Rủi ro còn lại (từ `acceptance.md`, nói thẳng)

- **R-1 Error Log có thể lặp sau một lần chạy lỗi.** Thư cảnh báo thì đúng một lần: thư và mốc cùng một giao dịch, lỗi thì mất cả hai, lần sau gửi lại đúng một thư. Nhưng dòng cảnh báo trong **Error Log** nằm ngoài giao dịch đó (`tabError Log` là MyISAM, đọc thật trên `miyano`), nên sau một lần chạy lỗi dòng ấy ở lại, và lần chạy sau ghi thêm một dòng: cùng một thay đổi hiện hai lần trong Error Log (lặp, không sót). NFR-8 đạt theo cách đo của spec (thư + mốc); nếu người coi Error Log cũng là kênh cần "0 báo hai lần" thì cần amendment. Đây là quyết định (decide) của tech-lead ở T13; architect đã nêu.
  - **Tài liệu thiết kế chưa theo hết:** `design-amd2.md` §4.2 đoạn "Vì sao báo đúng một lần" (`:92`) chưa nói dòng Error Log nằm ngoài giao dịch. Bước 5 ngay trên đó đã nói. Cần designer thêm một câu.
- **R-2 Mục User có ảnh chụp không dùng được.** Nó không biết role, nên không có dấu `[QUẢN TRỊ]`, xếp sau nhóm quản trị và có thể bị đẩy vào "…và N mục khác" dù có thể che một lần cấp role quản trị. Thiết kế chưa quyết. Đầy đủ vẫn tra được ở `ERP AI Log`.
- **R-3 Nợ còn mở trong `docs/team/debt.md`:** (a) `_undo_turn` dừng ở callback `after_rollback` đầu tiên ném lỗi; (b) chữ ký `_undo_turn(run_id)` ở design §4.1 (chữ đã sửa vòng 4; As-Built ghi đúng); (c) `ROUTE_SAVEPOINT`/`ROUTE_UNIT_SAVEPOINT` của FEAT-006 vẫn rò callback commit; (d) khe Error Log của R-1; (e) R-2; (f) minor test hoãn (ca `{"role": ""}`, docstring `_real_alarms`, một luật kiến trúc còn lọt); (g) test của cảnh báo dùng khóa file thật `erp_ai_privilege_alert`: scheduler chạy cùng lúc thì test chờ 60 s rồi đỏ "lock busy", trông như chập chờn.
- **R-4 Site dùng chung.** Migrate từ một nhánh xóa DocType của nhánh khác ("Orphaned": `ERP AI User Template`, `ERP AI Catalog Rule` của FEAT-007) và để lại lược đồ của nhánh đó; mỗi lượt test để lại dòng Error Log (+40 lần verify này, vì `tabError Log` là MyISAM). Không phải lỗi mã FEAT-005; migrate kế tiếp của FEAT-007 tạo lại hai DocType.
- **R-5 Chưa có bằng chứng thật với email cảnh báo trên `miyano`** (spec "Success" sau G4). Việc của người, mục 6.
- **Khoảng trống chấp nhận theo thiết kế (D-1, ADR-024 QĐ 4, 5):** (1) khi "Toàn quyền" bật, đổi role qua `api_call_method` không có trong cảnh báo hằng ngày; (2) commit do mã ngoài `erp_ai` chạy bên trong một tool (DDL ngầm, controller tự commit, hàm whitelist) cố định các ghi trước nó; lượt lỗi sau đó để lại thay đổi không có dòng nhật ký.
- **Hoàn tác lượt có giá:** lượt lỗi mất cả các ghi khác của lượt, kể cả đề xuất và comment của nó (ADR-024 Hệ quả). Tiến trình chết hay `write_entry` dòng `propose` lỗi giữa commit dòng `reason` và dòng `propose` thì đề xuất có, mục hành động của nó có trong `actions` của dòng `reason`, nhưng thiếu dòng `propose` (D-7).

## 5. Post-G4 debt (việc "owner: writer, after G4" của `acceptance.md` và DoD của spec)

| Việc | Trạng thái | Chỗ |
|---|---|---|
| As-Built | đóng | file này |
| CHANGELOG, mục `[Unreleased]` | đóng | `CHANGELOG.md` (Added, Changed; mỗi mục kết thúc `(FEAT-005)`) |
| README: cách đọc trước/sau và hoàn tác bằng tay; cảnh báo nói gì, dòng quản trị, vì sao 5 mục; khoảng trống "Toàn quyền" | đóng | `README.md`, mục "Nhật ký trước/sau và cảnh báo phân quyền hằng ngày" |
| Release notes, PR body | đóng | `release-notes.md`, `pr-body.md` cùng thư mục |
| Sửa `design-amd2.md` §4.2 "Vì sao báo đúng một lần" | **mở**, không phải việc của writer (writer không sửa `design-amd2.md`) | designer; mục 3.1, R-1 |
| Kiểm lại README bằng grep trước release | cho `/team:release` kiểm | `grep -n "privilege_alert_checked_until\|Agent đã sửa bản ghi phân quyền\|QUẢN TRỊ" README.md` |

## 6. Việc chỉ người làm được

Writer và đội không làm thay được các việc dưới đây (không lệnh site, không push, không prod).

1. **Migrate và restart trên site.** `cd ../.. && bench --site miyano migrate` (`cmd.migrate`), rồi `bench restart` (lệnh của bench, không phải slot `cmd.*`). Migrate đồng bộ trường `privilege_alert_checked_until`, 0 DDL. Nếu site còn lược đồ của nhánh khác (R-4), migrate xóa hai DocType của FEAT-007 như "Orphaned"; báo phiên FEAT-007.
2. **Kiểm `alert_recipients`** có ít nhất một địa chỉ trước khi deploy (không có thì cảnh báo chỉ có ở Error Log). Mặc định `info@miyano.com.vn` (README).
3. **Chạy thử trên dev** (spec "Success", R-5): cho bot gán 1 role cho một user thử; email hôm sau nêu user, role, người ra lệnh; hôm sau nữa không lặp; đọc trước/sau trong `ERP AI Log` và đổi lại bằng tay; rồi gỡ user thử. Lần chạy đầu sau triển khai báo một lần mọi thay đổi cũ của bot (ra "không có trước/sau"): bình thường, không phải lỗi.
4. **Quyết định NFR-8 và Error Log (R-1):** chấp nhận khe Error Log, hoặc yêu cầu amendment.
5. **CI sau khi push** `develop` (tech-lead merge `team/FEAT-005`): mục "CI xanh" của DoD còn trống tới khi CI chạy (`ci.yml` chạy khi push `develop` hoặc PR).
6. **Lên prod cần `Approved-by-prod:`** của người (G5, STD-CI-6). Writer không viết dòng đó, cũng không viết `Released:`.

<!-- devops thêm dòng sau khi lên prod thành công: Released: <tag> <YYYY-MM-DD> -->
