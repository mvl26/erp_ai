Feature: FEAT-001
Stage: verify
Author-agent: qa
Date: 2026-11-11
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Acceptance FEAT-001

Commit kiểm (lần 2, có hiệu lực): `533180a348ac842e486d7efab885247b12f2d24f` (nhánh `team/FEAT-001`, `git rev-parse HEAD` đầu và cuối lượt kiểm lại, không đổi). Xem mục "Kiểm lại 2026-11-11 trên 533180a".
Commit kiểm lần 1: `95a499055698f3d033003593bf9be3ae4a1806ce` (kết luận design-defect, giữ lại bên dưới làm lịch sử).
Base cho diff: `develop` (`2932a2b`, = merge-base); `config.base_branch = "main"` không tồn tại cục bộ (theo chỉ dẫn team-leader).
Cây làm việc: chỉ bẩn ở `docs/team/journal/FEAT-001.md`, `docs/team/metrics/*.jsonl` (M) và file chưa track `.github/CODEOWNERS`, `.github/ISSUE_TEMPLATE/`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/workflows/team-*.yml`, `.claude/agent-memory/`; không file nào dưới `erp_ai/` → không ảnh hưởng test. `pre-commit` không sửa file nào (status trước = sau).
`team.py status FEAT-001` → `built READY` (exit 0). `.team/current.json` không ghi: vai qa chỉ được ghi acceptance.md và memory.

## Kiểm lại 2026-11-11 trên 533180a

Commit mới so với lần 1: `cc29060` (design amendment hàng 8–11), T41 `0a57502` (đổi tên test runner + luật kiến trúc), T42 `e1ac63f` (`ERP AI Log.skipped_fields`), T43 `2357ba1` (runner chép `skipped`), `533180a` (tick). Diff mã: `git diff 95a4990..533180a --stat -- erp_ai` → 5 file (`runner.py`, `test_runner.py => test_agent_runner.py`, `erp_ai_log.json`, `test_erp_ai_log.py`, `test_architecture.py`), 167 thêm / 15 xóa.

| Mục | Lệnh | Exit | Đầu ra | Kết luận |
|---|---|---|---|---|
| DD-2 / cmd.test | `bench --site miyano run-tests --app erp_ai --junit-xml-output <sp>/app.xml` | 0 | `Ran 507 tests in 71.169s` `OK` | đạt |
| DD-2 / tổng theo module | `run-tests --module <m> --junit-xml-output` cho mọi `erp_ai/**/test_*.py` (25 module) | 0 ×25 | tổng 507 (`test_agent_runner` 56, `test_architecture` 42, `test_erp_ai_log` 7, còn lại như lần 1); so junit: `app 507 modules 507 in_modules_not_app 0 in_app_not_modules 0` | đạt — `cmd.test` = tổng theo module (amendment hàng 10) |
| DD-2 / số tĩnh | `grep -c 'def test_'` trên `git ls-files 'erp_ai/*test_*.py'` | 0 | `static def test_: 507` | đạt |
| DD-2 / tên file | `ls erp_ai/agent/test_runner.py` | 2 | `No such file or directory`; `test_architecture.py:113` `FRAPPE_SKIPPED_TEST_FILENAMES = ("test_runner.py",)`; `::test_no_test_file_named_like_frappe_skips`, `::test_frappe_skipped_test_name_check_catches_any_depth` có trong junit `--app`, OK | đạt |
| DD-1 / AC-10 mã | đọc `runner.py:213-230`, `:288-305`, `:337` | — | `if result.get("ok") and result.get("skipped"): updates["skipped_fields"] = json.dumps(result["skipped"], ...)` ở bước phân loại (độc lập với `after`, nên ghi cả khi `after` rỗng, `applied` giữ 0); vòng lập luận gom `skipped.extend(outcome.get("skipped") or [])` vào `skipped_fields` của dòng `reason`; `ok=false` không ghi | khớp amendment hàng 8 |
| DD-1 / trường | `migrate` rồi `show columns from tabERP AI Log like 'skipped_fields'`; đọc JSON | 0 / 0 | `migrate exit 0`; cột `skipped_fields text`; JSON `('skipped_fields', 'Small Text', read_only 1, permlevel 0)` | đạt |
| DD-1 / test | junit `--app` (ở trên) | 0 | 5 test mới có mặt và OK: `test_agent_runner.py::test_l1_missing_value_reason_logged_on_classify_entry` (giá trị cứng `[{"field": "ticket_type", "reason": "giá trị không tồn tại trên hệ thống"}]`, `applied = 1`, `ticket_type` không đổi), `::test_l1_all_fields_skipped_reasons_logged_applied_zero` (biên: mọi trường bị bỏ → `applied = 0`, vẫn có lý do), `::test_apply_failure_leaves_skipped_fields_empty` (lỗi), `::test_reason_turn_logs_skipped_fields_of_set_classification`, `test_erp_ai_log.py::test_skipped_fields_is_read_only_small_text` | đạt |
| Dấu skip / assert xóa trong phần mới | `git diff 95a4990..533180a -- '*.py' \| grep -nE '^\+.*(@unittest\.skip\|…\|\.skipTest\()\|^-[^-].*assert'` | 1 | rỗng | đạt |
| cmd.lint | `pre-commit run --all-files` | 0 | 12 dòng `Passed`, 0 dòng khác; `git status` không thêm file sửa | đạt |
| cmd.migrate | `bench --site miyano migrate` | 0 | `migrate exit 0` | đạt |

Dữ liệu `miyano` (trước 18:57:04 → sau 19:01:41): HD Team 4→4, HD Ticket 3→3, User 8→8, ERP AI Log 0→0, Email Queue 9→9, Task 0→0, ToDo 49→49; Error Log 207→208 (+1 `helpdesk.search.build_index` do `after_migrate`); Comment 119926→119976 (+50 = 25 `Deleted` trên `Email Account` + 25 trên `Holiday List`, một cặp mỗi lần chạy `run-tests` theo module, như lần 1). `ERP AI Setting` không chạm: `permission_level = L2`, `excluded_teams = "\n  \n"`, `modified = 2026-11-11 15:26:16` (vẫn là E-1, người phải đặt lại trước khi bật).

Kết luận lần 2: DD-1 và DD-2 đã đóng. AC-10 **đạt**. AC-3, AC-6, AC-9, AC-15 và NFR-4 phía runner nay chạy trong `cmd.test`. Các tiêu chí còn lại không có mã đổi; hồi quy toàn bộ xanh (507/507). AC-19 (bấm nút) và AC-20 là việc người làm sau G4 theo DoD của spec ("Sau G4"), còn pending-human, không phải phần build. Mục DoD "CI xanh trên nhánh feature" không kiểm được: feature cấm push (intake `:28`) nên workflow chưa chạy bao giờ. Bước test tương đương của CI (`run-tests --app erp_ai`, `ci.yml:110`) xanh tại chỗ, 507 test. Chủ: devops/người ở `/team:pr`/`/team:release`. ADR-003:37 đã ghi nhận là rủi ro/debt cho architect (amendment hàng 11).

## Kết luận lần 1 (95a4990, lịch sử)

Hai lỗi nằm ở design (mã làm đúng design, nhưng design không thỏa tiêu chí/DoD):
- **DD-1 (AC-10):** spec AC-10 đòi "đầu mục ánh xạ tới giá trị không tồn tại → không ghi trường đó, **lý do vào nhật ký**". `set_classification` trả `skipped[{field, reason}]` (`erp_ai/agent/tools/write_ticket.py:25-57`), nhưng runner bỏ nó (`erp_ai/agent/runner.py:213-230` chỉ ghi `applied/value_before/value_after/actions` khi `ok` và `after` khác rỗng; vòng lập luận `runner.py:330-334` cũng chỉ lấy `after`). Design 2.3 không có trường cho lý do, 4.3 bước 6 không bảo ghi `skipped`. Không test nào kiểm dòng `ERP AI Log` có lý do (`test_write_ticket.py:160-170` chỉ kiểm kết quả tool). Đây đúng là khoảng trống review-36 đã nêu, chưa có quyết định.
- **DD-2 (DoD "AC-1..AC-19 có test tự động; `cmd.test` xanh", CI):** design §7/§8 đặt test runner ở `erp_ai/agent/test_runner.py`. Frappe v15 bỏ qua mọi file tên này: `apps/frappe/frappe/test_runner.py:160` `... and filename != "test_runner.py"`. Kết quả: `cmd.test` (và CI `ci.yml:110` `run-tests --app erp_ai`) chạy 448 test, **thiếu toàn bộ 52 test** của `erp_ai.agent.test_runner` (so junit: 52/52 vắng trong lần chạy `--app`, mọi module khác 0 vắng). Các test này xanh khi chạy theo module (3/3 lần, 52 OK), nhưng AC-6, AC-9, một phần AC-3/AC-10/AC-15, NFR-4 (runner), ADR-003(b) không có ai canh trong `cmd.test`/CI.

## Tiêu chí

Mọi lệnh chạy từ `/home/miyano/frappe-bench` sau khi ghim commit. `cmd.test_one` = `bench --site miyano run-tests --module <m> --junit-xml-output <scratchpad>` (thêm cờ junit chỉ để lấy tên test).

| criterion | command | exit | output excerpt | covering test | verdict |
|---|---|---|---|---|---|
| AC-1 | `run-tests --module erp_ai.eval.test_run_eval` | 0 | `Ran 13 tests ... OK` | `test_run_eval.py::test_metrics_twelve_ticket_sample` (hard-code 12 nhãn, 10 đúng, `"70–85%"`, từng ô ma trận), `::test_verdict_thresholds_at_85_and_70` (biên 85,0/70,0/69,9) | đạt |
| AC-2 | `run-tests --module erp_ai.eval.test_export_tickets` | 0 | `Ran 11 tests ... OK` | `::test_export_skips_excluded_team` (3 phiếu → 2 dòng, 6 khóa), `::test_export_skips_opt_out_and_runs_when_disabled`, lỗi `::test_export_refuses_path_inside_repo` | đạt |
| AC-3 | `--module erp_ai.agent.test_classification`; `--module erp_ai.eval.test_run_eval`; `--module erp_ai.agent.test_runner` | 0 / 0 / 0 | `Ran 30 ... OK`; `Ran 13 ... OK`; `Ran 52 ... OK` | `test_run_eval.py::test_eval_and_runner_share_classify_request` (so `system`/`messages`/`max_tokens` hai đường với `build_classify_request`), `test_classification.py::test_parse_rejects_non_json_and_bad_values`, `test_runner.py::test_unparseable_classification_logged_run_continues` (không có trong `cmd.test`, DD-2) | đạt (hành vi); phần runner chỉ chạy theo module |
| AC-4 | `bench --site miyano migrate`; `--module erp_ai.tests.test_install`; `--module erp_ai.tests.test_handlers`; SQL đọc `tabUser`/`tabHas Role`/`tabRole`/`tabSingles`/`tabCustom Field` | 0 / 0 / 0 / 0 | migrate: `Updating DocTypes for erp_ai ... 100%`, `Executing after_migrate hooks...`; `Ran 13 ... OK`; `Ran 31 ... OK`; site: user `ai.agent@miyano.com.vn` enabled, roles = `Agent`, `ERP AI Agent` (không System Manager); 2 role có; 6 trường `ai_*` permlevel 8; `enabled = 0` | `test_install.py::test_agent_user_has_exact_roles_without_system_manager`, `::test_default_settings_disabled_level_l0`, `::test_ai_fields_permlevel_8_and_template_rows_agents_only`, `::test_setup_twice_is_idempotent`, `test_handlers.py::test_disabled_agent_new_ticket_no_job_no_model_call` | đạt (xem ghi chú môi trường E-1) |
| AC-5 | `--module erp_ai.tests.test_handlers`; `--module erp_ai.agent.test_queue` | 0 / 0 | `Ran 31 ... OK`; `Ran 5 ... OK` | (a) `::test_new_unclassified_ticket_enqueues_one_job`, (b) `::test_prefilled_ticket_no_job`, (c) `::test_agent_created_ticket_and_comment_no_job`, (d) `::test_comment_keyword_case_insensitive`, biên `::test_comment_on_other_doctype_or_type_no_job`, (e) `::test_opt_out_or_excluded_team_no_job_no_model_call`, (f) `test_queue.py::test_duplicate_trigger_same_transaction_one_job` | đạt |
| AC-6 | `--module erp_ai.agent.test_runner` (3 lần) | 0 ×3 | `Ran 52 tests in 6.634s OK` / `6.592s OK` / `7.085s OK` | `test_runner.py::test_wrong_session_user_stops_before_model` (`set_user` vô hiệu → `log_error(TITLE_WRONG_USER, "Sai tài khoản: Administrator")`, 0 lời gọi, 0 đọc HD Ticket), biên `::test_missing_agent_user_stops`, `::test_disabled_agent_user_stops` | đạt khi chạy theo module; **không có trong `cmd.test`/CI (DD-2)** |
| AC-7 | `--module erp_ai.agent.test_authority` | 0 | `Ran 16 tests ... OK` | 6 ca bảng + biên `::test_closed_cancelled_or_reassigned_todo_is_data`, `::test_never_authority_accounts_even_with_role_or_assignment`, lỗi `::test_spoofed_comment_author_fields_ignored` | đạt |
| AC-8 | `--module erp_ai.agent.tools.test_registry`; `--module erp_ai.agent.tools.test_write_ticket` | 0 / 0 | `Ran 24 ... OK`; `Ran 33 ... OK` | `::test_tool_names_per_level_and_authority`, `::test_no_write_tool_accepts_doctype_or_field`, lỗi `::test_write_without_permission_returns_ok_false_unchanged`, `::test_create_task_requires_instructor` | đạt |
| AC-9 | `--module erp_ai.agent.test_runner` | 0 | `Ran 52 ... OK` | `::test_l0_logs_prediction_ticket_unchanged`, biên `::test_l0_comment_mention_skipped_no_call`, `::test_l0_still_does_not_apply` | đạt khi chạy theo module; **không có trong `cmd.test`/CI (DD-2)** |
| AC-10 | `--module erp_ai.agent.test_runner`; `--module erp_ai.agent.tools.test_write_ticket`; `--module erp_ai.agent.test_classification`; đọc mã `runner.py:179-236`, `:312-336` | 0 / 0 / 0 | `Ran 52 ... OK`; `Ran 33 ... OK`; `Ran 30 ... OK`; runner: `if result.get("ok") and result.get("after"):` → chỉ ghi `applied`, `value_before`, `value_after`, `actions`; `skipped` không được ghi ở đâu | ghi theo ánh xạ/độ tin cậy/`status` không đổi: `test_runner.py::test_l1_applies_mapping_confidence_and_hint`; người đã phân loại: `::test_l1_human_classified_not_overwritten`; `[GẬP]`: `test_classification.py::test_urgent_prefix_forces_urgent`; bỏ trường: `test_write_ticket.py::test_mapping_to_missing_value_skips_field` (chỉ kiểm kết quả tool). **Không có test nào cho "lý do vào nhật ký"** | lần 1: không đạt (DD-1). **Lần 2 (533180a): đạt** — `skipped_fields` trên dòng `classify`/`reason`, 4 test runner mới + 1 test trường, xem mục kiểm lại |
| AC-11 | `--module erp_ai.tests.test_handlers` | 0 | `Ran 31 ... OK` | `::test_human_correction_updates_latest_log` (biên: sửa 2 lần), `::test_agent_correction_not_recorded` | đạt |
| AC-12 | `--module erp_ai.erp_ai_agent.report.erp_ai_accuracy.test_erp_ai_accuracy` | 0 | `Ran 13 tests ... OK` | `::test_accuracy_ten_log_sample` (10 bản ghi, đáp số tính tay; biên 7 ngày; mẫu 0 → trống) | đạt — `accuracy_pct = None` khi mẫu = 0 (`erp_ai_accuracy.py:_accuracy_pct`) đúng design 3.8 "mẫu = 0 → để trống"; spec không định số cho ca này |
| AC-13 | `--module erp_ai.agent.tools.test_source`; `--module erp_ai.agent.tools.test_registry` | 0 / 0 | `Ran 28 ... OK`; `Ran 24 ... OK` | `::test_path_escape_refused`, `::test_secret_names_and_extensions_refused`, biên `::test_read_capped_at_400_lines` (401 từ chối), `::test_search_capped_at_40_hits`, `::test_git_show_and_diff_refused`, `::test_git_missing_returns_not_installed`, `test_registry.py::test_git_source_schema_only_log_and_blame` | đạt (git thu về `log`/`blame` theo journal D4, amendment 2) |
| AC-14 | `--module erp_ai.agent.tools.test_read`; `--module erp_ai.gateway.test_gateway` | 0 / 0 | `Ran 27 ... OK`; `Ran 61 ... OK` | `test_read.py::test_denied_doctypes_refused` (subTest từng DocType), `::test_password_fields_never_returned`, `test_gateway.py::test_api_key_never_leaks` (thành công + 401 + ngoại lệ lạ; tìm chuỗi khóa trong ERP AI Log/Comment/Error Log/email/`last_error`) | đạt |
| AC-15 | `--module erp_ai.agent.test_runner`; `--module erp_ai.agent.test_run_log`; `--module erp_ai.gateway.test_gateway` | 0 / 0 / 0 | `Ran 52 ... OK`; `Ran 8 ... OK`; `Ran 61 ... OK` | `test_runner.py::test_stops_after_max_turns` (8 lượt, `["tool_use"]*7 + ["max_turns"]`), `::test_run_over_setting_limit_same_day_no_call`, `::test_last_run_within_setting_limit_still_calls` (biên), `::test_turn_log_fields`; chi phí tính tay `test_gateway.py::test_cost_uses_four_token_prices` (`(1000*3 + 4000*3.75 + 10000*0.3 + 2000*15)/1e6 = 0.051`) | đạt khi chạy theo module; phần runner **không có trong `cmd.test`/CI (DD-2)** |
| AC-16 | `--module erp_ai.tests.test_tasks`; `--module erp_ai.agent.test_policy` | 0 / 0 | `Ran 33 ... OK`; `Ran 21 ... OK` | `test_tasks.py::test_recompute_spend_from_log`, biên `::test_month_start_resets_to_zero`, `test_policy.py::test_effective_level_over_budget_never_raises` (L3/L2→L1, L1→L1, L0→L0, đúng bằng ngân sách → không lui) | đạt |
| AC-17 | `--module erp_ai.gateway.test_breaker`; `--module erp_ai.gateway.test_gateway` | 0 / 0 | `Ran 6 ... OK`; `Ran 61 ... OK` | `test_breaker.py::test_breaker_table` (subTest 9 hàng, 529 trần 600 s), `test_gateway.py::test_selection_filters_and_order`, `::test_reason_requires_model_reason`, lỗi `::test_bad_request_does_not_switch_key`, `::test_no_usable_key_alarm`, biên `::test_max_keys_per_call`, `::test_low_tokens_pause_until_reset_and_missing_headers_ignored` (19 999 / 20 000) | đạt |
| AC-18 | `--module erp_ai.tests.test_tasks`; `--module erp_ai.tests.test_alerts` | 0 / 0 | `Ran 33 ... OK`; `Ran 5 ... OK` | `::test_reprobe_only_exhausted_keys`, `::test_alarm_on_role_drift`, `::test_alarm_on_permission_records_modified_by_agent`, `::test_alarm_on_enabled_server_script_or_webhook_by_agent`, biên `::test_alarm_on_enabled_key_without_secret` | đạt |
| AC-19 | `--module erp_ai.erp_ai_agent.doctype.erp_ai_setting.test_erp_ai_setting` | 0 | `Ran 16 tests ... OK` | lỗi `::test_hd_agent_cannot_read_or_write_settings`, `::test_self_managed_fields_restored_on_human_save`, `::test_human_can_move_key_error_to_active_only`, `::test_check_keys_system_manager_only_and_per_key_result` | phần tự động đạt; **phần người bấm "Kiểm tra khóa": pending-human** (sau G4, spec AC-19) |
| AC-20 | `--module erp_ai.tests.test_install`; SQL `tabCustom Field` (permlevel 8) | 0 / 0 | `Ran 13 ... OK`; 6 trường `ai_*` permlevel 8 | `test_install.py::test_ai_fields_permlevel_8_and_template_rows_agents_only` (phần tự động) | **pending-human** — chụp màn hình HD Agent / HD Contact sau G4 (`ui: false`); không đánh giá thay người |

### Ba điểm team-leader yêu cầu xét

1. **review-36 / AC-10 `skipped`/`reason` không vào dòng classify:** xác nhận còn nguyên ở HEAD (bằng chứng ở hàng AC-10). Mã khớp design 2.3/4.3 → **design-defect DD-1**. Đề xuất cho designer (một trong hai): ghi `skipped` vào `error` của dòng `classify` (ví dụ `SKIPPED: ticket_type=giá trị không tồn tại trên hệ thống`) hoặc thêm khóa `skipped` vào `value_after`; áp cả khi `after` rỗng và cả cho `set_classification` ở vòng lập luận; kèm test kiểm dòng `ERP AI Log`. Task build: runner (vùng T29/T30) + `test_runner` (sau khi đổi tên, DD-2).
2. **ADR-003:37 vs `erp_ai_setting.py:4` `from erp_ai import gateway`:** ADR-003:37 viết "controller DocType không import `erp_ai.gateway` (nhắc lại ADR-001)", nhưng ADR-001 không có câu đó: ADR-001:24 xếp "method whitelist trong controller DocType" vào tầng Cửa vào, và ADR-001:36 chỉ cấm file handler `doc_events`. Design 3.6 định rõ `check_keys` trả `gateway.probe_credential`. Kết luận: mã đúng ADR-001 và design 3.6; lời văn ADR-003:37 sai khi trích ADR-001. Không làm hỏng tiêu chí nào. `minor | STD-DOC-4 | docs/team/adr/ADR-003.md:37 | ràng buộc trích sai ADR-001, mâu thuẫn design 3.6 | architect sửa thành "handler doc_events không import gateway; controller chỉ gọi gateway qua method whitelist"`. Gộp vào lần sửa design/ADR của DD-1/DD-2.
3. **T39 trả `accuracy_pct = None` cho dòng mẫu 0:** đúng design 3.8 ("mẫu = 0 → để trống") và test plan AC-12; Frappe hiển thị ô trống. Không phải lỗi. Còn treo câu hỏi thiết kế của review-43 (`_parse_corrected_to` gặp JSON hỏng thì trả `{}` → tính là "sửa" khi dự đoán không rỗng): minor, không thuộc AC-12.

## Kiểm chung

- `cmd.test` (`bench --site miyano run-tests --app erp_ai`): exit 0, `Ran 448 tests in 66.868s` `OK` (chạy lại có junit: `Ran 448 tests in 65.633s` `OK`, exit 0). 0 failure, 0 error. **Thiếu 52 test `erp_ai.agent.test_runner` (DD-2).** Tổng theo module: 500 test, tất cả OK. Nhiễu trong đầu ra: dòng `ERROR PropertyValue: ... box-shadow:0 3px 6px #0000001a` của bộ inline CSS email (cssutils), không phải lỗi test, exit vẫn 0.
- `cmd.lint` (`pre-commit run --all-files`): exit 0; mọi hook `Passed` (ruff import sorter, ruff linter, ruff formatter, prettier, eslint, check json/toml/yaml/ast, debug statements…); không file nào bị sửa.
- `cmd.typecheck`: slot rỗng trong profile → không áp dụng.
- `cmd.build` (`bench build --app erp_ai`): exit 0, `DONE Total Build Time: 92.375ms`, `Compiling translations for erp_ai`.
- Dấu skip mới trong diff: `git diff develop...95a4990 -- '*.py' | grep -nE '^\+.*(@unittest\.skip|@unittest\.skipIf|@unittest\.expectedFailure|\.skipTest\()'` → rỗng (grep exit 1). Diff toàn bộ có 6 dòng khớp, đều là tài liệu nêu luật: `.claude/rules/tests.md`, `.team/profile.json`, `docs/team/profile-proposal.md`, `docs/team/features/FEAT-001/diff.patch`.
- Assertion bị xóa: `git diff develop...95a4990 | grep -nE '^-[^-].*(assert|self\.assert)'` → rỗng (exit 1). File bị sửa (không phải thêm) so với develop: `.github/workflows/ci.yml`, `.gitignore`, `erp_ai/hooks.py`, `pyproject.toml`.
- Migration lên/xuống: diff không có patch (`patches.txt` không đổi; chỉ DocType JSON thêm mới + custom field qua `ensure_setup`). `cmd.migrate` exit 0. Chiều xuống trong Frappe = `uninstall-app`, sẽ xóa dữ liệu site → **không chạy** theo luật dữ liệu của team-leader. Hoàn tác: `ignore_links_on_delete` và custom field do `ensure_setup` tạo, idempotent (`test_setup_twice_is_idempotent`).

## Acceptance checklist (6) — chấm lại trên 533180a
1. Mỗi tiêu chí có lệnh thật + đầu ra: **đạt** (STD-TEST-2). AC-1..AC-18 đạt; AC-19 phần tự động đạt. Bấm nút AC-19 và AC-20 là kiểm của người sau G4 theo DoD của spec, ghi pending-human.
2. `cmd.test`, `cmd.lint`, `cmd.typecheck`: **đạt** (STD-TEST-3, STD-STYLE-2): `Ran 507 tests OK` exit 0, khớp tổng theo module; lint exit 0; typecheck không có slot.
3. Không dấu skip mới: **đạt** (STD-TEST-4); grep `*.py` trên `develop...95a4990` và `95a4990..533180a` đều rỗng.
4. Migration: **đạt** (STD-OPS-2/3). Chỉ có thay đổi schema thêm vào: DocType JSON và cột `skipped_fields` cho phép NULL; không có patch dữ liệu. Migrate exit 0 hai lần, số bản ghi khớp. Hoàn tác = revert JSON + migrate (cột NULL để lại không hại gì). Chưa chạy `uninstall-app` vì lệnh đó xóa dữ liệu site.
5. Phần build của DoD: **đạt**, chỉ trừ mục chạy CI thật. Mục này không làm được vì cấm push (intake `:28`); bước test tương đương của CI xanh tại chỗ. Chủ: `/team:pr`.
6. Không chạm `protected_paths`, không bí mật: **đạt** (STD-SEC-1): `git diff --name-only develop...95a4990 | grep -E '(^|/)\.env($|\.)|\.pem$|\.key$|(^|/)license\.txt$'` → rỗng; 5 file đổi ở lần 2 đều dưới `erp_ai/`.

## DoD
Phần build:
- [x] AC-1..AC-19 có test tự động, `cmd.test` xanh — lần 2: `Ran 507 tests OK`, = tổng theo module (lần 1 thiếu AC-10 và 52 test runner, đã đóng).
- [x] `cmd.migrate` exit 0 trên `miyano`.
- [x] `cmd.lint` sạch; không dấu skip.
- [ ] CI xanh trên nhánh feature — không kiểm được trước PR: feature cấm push (intake `:28`), workflow chưa chạy lần nào. Bước test của CI (`ci.yml:110` `run-tests --app erp_ai`) xanh tại chỗ, nay gồm cả test runner. Chủ: `/team:pr`, `/team:release` kiểm lại.
- [x] Không khóa/mật khẩu/dữ liệu cá nhân trong diff (grep protected paths rỗng; `test_api_key_never_leaks` OK).
- [x] Commit chỉ trên `team/FEAT-001*`; không có remote ref (`git branch -a` không có `origin/*`).

Sau G4 (chủ: writer, `/team:asbuilt`; `/team:release` kiểm lại bằng `ls docs/team/features/FEAT-001/asbuilt.md CHANGELOG.md` và đọc README):
- [ ] As-Built  - [ ] README/tài liệu  - [ ] CHANGELOG — không tính là trượt ở bước này.
- [ ] AC-19 bấm "Kiểm tra khóa" và AC-20 chụp màn hình — pending-human.

## Dữ liệu site `miyano` (trước → sau, SQL đọc)
| Bảng | 18:13 (trước) | 18:27 (sau) |
|---|---|---|
| HD Team | 4 | 4 |
| HD Ticket | 3 | 3 |
| User | 8 | 8 |
| ERP AI Log | 0 | 0 |
| Error Log | 202 | 203 (+1 `helpdesk.search.build_index`, do `after_migrate` xếp lại chỉ mục tìm kiếm, như team-leader đã báo trước) |
| Email Queue | 9 | 9 |
| Task | 0 | 0 |
| ToDo | 49 | 49 |
| Comment | 119848 | 119900 (+52: `comment_type = Deleted`, 26 trên `Email Account` + 26 trên `Holiday List`, owner Administrator, 18:17:48–18:22:46, tức một cặp cho mỗi lần chạy `run-tests` theo module; do phần dựng bản ghi test của framework/app khác tạo và xóa, không phải bản ghi erp_ai) |

## Ghi chú môi trường (không phải lỗi mã ở HEAD)
- **E-1:** `ERP AI Setting` trên `miyano` đang `permission_level = L2`, `excluded_teams = "\n  \n"` (rỗng), `modified = 2026-11-11 15:26:16` bởi Administrator. Giá trị khớp `test_policy` bản cũ (setUp `permission_level="L2"`, `test_blank_excluded_teams_excludes_nobody`) đã commit nhầm lúc 15:26 (journal dòng 66; đã sửa ở T20b/T20c). Bộ test ở HEAD không đổi bản ghi này (`modified` vẫn 15:26 sau mọi lần chạy). `ensure_setup` cố ý không ghi đè giá trị đã lưu, nên migrate không đưa về mặc định. `enabled = 0` nên chưa nguy hiểm; **trước khi người bật agent hoặc làm AC-19/AC-20 trên `miyano`**, người phải đặt lại `permission_level = L0` và `excluded_teams = "Nhân sự & Hành chính\nTài chính Kế toán"` trên form, nếu không phiếu nhóm loại trừ sẽ được gửi lên API (NFR-4). Còn sót HD Team "IT", "Nhân sự & Hành chính" (15:26, journal dòng 66).

## Pending-human (không giả lập)
- AC-19: người bấm "Kiểm tra khóa" trên `/app/erp-ai-setting` site dev, chụp kết quả.
- AC-20: người mở 1 phiếu bằng HD Agent và 1 bằng HD Contact, chụp màn hình.

## Chưa kiểm
- Lần chạy CI workflow thật (`.github/workflows/ci.yml`) — không chạy được cục bộ.
- Chiều xuống của migration (`uninstall-app`) — bị cấm vì xóa dữ liệu site.
- Scheduler thật nhận mục hourly/daily trên `miyano` (review-45 deferred) — chỉ có test kiểm `hooks.py`.

## Việc tiếp theo (sau lần 2)
1. G4 (người): đặt lại `ERP AI Setting` trên `miyano` (E-1), làm AC-19 (bấm "Kiểm tra khóa") và AC-20 (chụp màn hình).
2. Sau G4: `/team:asbuilt FEAT-001` (As-Built, README, CHANGELOG), `/team:pr` (lần chạy CI thật đầu tiên).
3. Debt cho architect: sửa lời văn ADR-003:37 (amendment hàng 11).

## Việc tiếp theo (lần 1, đã làm)
1. `/team:design FEAT-001` (amend): DD-1 — thêm chỗ ghi `skipped`/lý do trên dòng `classify` (2.3, 4.3 bước 6 và 8, test plan AC-10); DD-2 — đổi `erp_ai/agent/test_runner.py` thành tên Frappe tìm thấy (ví dụ `erp_ai/agent/test_agent_runner.py`) ở §7/§8, thêm vào test kiến trúc luật "không file test nào tên `test_runner.py`"; sửa lời văn ADR-003:37 (architect).
2. `/team:plan FEAT-001 --insert`: một task `git mv` file test runner, một task runner ghi lý do bỏ trường + test đỏ trước.
3. `/team:build` các task mới, rồi `/team:verify FEAT-001`.

Verdict: accepted
