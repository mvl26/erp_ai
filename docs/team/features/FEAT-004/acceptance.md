Feature: FEAT-004
Stage: verify
Author-agent: qa
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Acceptance FEAT-004 (bản gộp, lượt chốt)

Commit kiểm: `ba89ab305d06270d646a6560cd69b8b741cefc25` (team/FEAT-004, worktree `.claude/worktrees/feat-004`; cây mã sạch, chỉ docs chưa commit).
Ba phần (`acceptance-part-1.md`, `-2.md`, `-3.md`) kiểm trên `abd2fa2`. Từ `abd2fa2` tới `ba89ab3` mã đổi đúng các commit rework `0ea548c` (T64, runner), `f0fefb4`, `7894f04` (T62, site_api) và merge `0558640`.

Cách chạy: `cmd.test_one` từ `/home/miyano/frappe-bench`, `env PYTHONPATH=<worktree>` (traceback trỏ vào file của worktree: `app.log` có 238 dòng `worktrees/feat-004`), bọc `flock -w 1800 .team/miyano-site.lock`. `bench run-tests` thoát 0 cả khi đỏ: bằng chứng là dòng `Ran`/`OK|FAILED` cộng số đếm junit (tests/failures/errors/skipped). Nguồn bằng chứng trên `ba89ab3` (scratchpad qa `v/`):

| lần chạy | dòng kết quả |
|---|---|
| `test_apply_job` cả module (18:56) | `Ran 117 tests in 178.351s` / `OK` |
| `test_agent_runner` cả module (18:58) | `Ran 85 tests in 36.358s` / `OK` |
| `test_agent_write_guard` cả module (18:59) | `Ran 5 tests in 1.226s` / `OK` |
| `cmd.test` cả app (19:18) | `Ran 1496 tests in 1079.598s` / `FAILED (failures=1, errors=128)` — junit: 128 error đều `QueryDeadlockError 1213`; 1 failure `test_erp_ai_log::test_no_role_can_write_or_delete` |
| `test_change_decision` (19:35) rồi 9 ca đỏ theo tên (19:37) | `Ran 10` / `FAILED (errors=9)` (9 × 1213), rồi `Ran 9 tests in 21.687s` / `OK` |
| chạy lại module có 1213 trong lần cả app (19:22–19:34, `v/rr/`) | `test_apply_job` 23 ca `OK`; `test_result_comment` `Ran 3` `OK`; `test_propose_change` `Ran 12` `OK`; `test_read` `Ran 15` `OK`; `test_write_ticket` `Ran 15` `OK`; `test_erp_ai_setting` `Ran 2` `OK`; `test_export_tickets` `Ran 1` `OK`; `test_erp_ai_log` `Ran 1` `OK`; còn đỏ: `test_route_ticket` (errors=4, 1213), `test_ticket_panel` (errors=1, 1213), `test_run_eval` (1213), `test_erp_ai_change_proposal` (`Ran 3` errors=2, 1213), `test_gateway` (1 × 1213 + `test_api_key_never_leaks` failure) |
| lượt chốt, mỗi module một lần (19:40–19:47, `v/rr3/`) | proposal `Ran 25` `OK`; run_eval `Ran 22` `OK`; gateway `Ran 65` `FAILED (failures=1)` (F-3); route_ticket errors=3, ticket_panel failures=1 errors=19 (1213) — mục "Chạy lại lượt chốt" |

Không có một lần `cmd.test` cả app nào ra `OK` trên `ba89ab3`. Lý do: site `miyano` dùng chung; lúc chạy lượt chốt `ps` vẫn thấy một `bench --site miyano run-tests --app erp_ai` khác (pid 851601) chạy ngoài khóa.

## Tiêu chí (trên ba89ab3)

| tiêu chí | lệnh | exit | đầu ra | test phủ | kết luận |
|---|---|---|---|---|---|
| AC-1 | `cmd.test_one` test_registry, test_classification, test_agent_runner | 0 | registry 41/0/0 và classification 39/0/0 (junit cả app); runner `Ran 85` `OK` | test_registry::test_switch_off_tool_names_match_base_for_all_levels_and_authority; test_agent_runner::test_switch_off_run_sends_base_tools_and_prompt | đạt |
| AC-2 | như AC-1 | 0 | registry 41/0/0; runner `Ran 85` `OK` | test_registry::test_change_group_only_when_switch_l3_and_instructor; test_agent_runner::test_over_budget_l3_drops_change_tools, ::test_over_budget_edge_spent_equal_to_budget_keeps_change_tools | đạt |
| AC-3 | `cmd.test_one` test_propose_change | 0 | cả app: 20 xanh + 12 × 1213; chạy lại 12 ca `Ran 12` `OK` | test_propose_change::test_file_change_creates_pending_proposal_and_comment_without_touching_disk | đạt |
| AC-4 | `cmd.test_one` test_change_guard, test_propose_change | 0 | guard 35/0/0; propose như AC-3 | test_change_guard::test_refuses_* (7 nhóm); test_propose_change::test_each_guard_refusal_creates_zero_proposals | đạt |
| AC-5 | `cmd.test_one` proposal, change_decision, install | 0 | install 33/0/0; decision 1 + 9 `OK`; proposal `Ran 25 tests in 74.421s` `OK` | test_erp_ai_change_proposal::test_methods_refuse_agent_admin_guest_and_user_without_role; test_change_decision::test_refused_accounts | đạt |
| AC-6 | `cmd.test_one` test_apply_job | 0 | `Ran 117` `OK` | test_apply_job::test_apply_writes_exact_approved_bytes, ::test_target_changed_after_proposal_becomes_stale, ::test_two_proposals_same_file_second_is_stale | đạt |
| AC-7 | như AC-6 | 0 | `Ran 117` `OK` | test_apply_job::test_undo_restores_previous_bytes, ::test_undo_removes_created_file, ::test_undo_refused_when_file_changed_after_apply | đạt |
| AC-8 | như AC-6; process_runner | 0 | `Ran 117` `OK`; process_runner 17/0/0 | test_apply_job::test_approved_command_runs_once_with_exact_args | đạt |
| AC-9 | như AC-6; change_guard | 0 | `Ran 117` `OK`; guard 35/0/0 | test_apply_job::test_approved_command_tampered_to_denied_is_blocked_at_apply | đạt |
| AC-10 | như AC-8 | 0 | `Ran 117` `OK` | test_apply_job::test_command_timeout_fails_with_reason | đạt |
| AC-11 | `cmd.test_one` test_agent_runner, test_registry | 0 | runner `Ran 85` `OK`; registry 41/0/0 | test_agent_runner::test_injection_without_instructor_gets_no_change_tools_and_no_proposal | đạt (khoảng trống test ghi ở phần 1 vẫn còn: không có kịch bản câu chèn khi ô Toàn quyền bật) |
| AC-12 | `cmd.test_one` transitions, run_log, change_decision | 0 | transitions 42/0/0; run_log 16/0/0; decision `OK` | test_transitions::test_each_step_writes_exactly_one_change_row; test_change_decision::test_decide_logs_exactly_one_row_with_the_caller_as_actor | đạt |
| AC-13 | như AC-6 | 0 | `Ran 117` `OK` | test_apply_job::test_fake_key_never_in_proposal_result_log_comment | đạt |
| AC-14 | `cmd.test_one` test_classification | 0 | 39/0/0 | test_classification::test_reason_system_with_change_tools_adds_approval_block | đạt (phần khóa gateway: xem Phát hiện F-3) |
| AC-15 | `cmd.test_one` test_architecture | 0 | 177/0/0 | test_architecture | đạt |
| AC-16 | `cmd.test_one` change_guard, propose | 0 | guard 35/0/0; propose `OK` | test_change_guard::test_core_apps_allowed_only_when_listed | đạt |
| AC-17 | như AC-6 | 0 | `Ran 117` `OK` | test_apply_job::test_new_file_is_created_and_committed | đạt |
| AC-18 | như AC-6 | 0 | `Ran 117` `OK` | test_apply_job::test_index_lock_fails_fast | đạt |
| AC-19 | như AC-6 | 0 | `Ran 117` `OK` | test_apply_job::test_commit_failure_restores_file_and_index, ::test_new_file_failed_commit_removes_the_file_and_unstages_it | đạt |
| AC-20 | như AC-6 | 0 | `Ran 117` `OK` | test_apply_job::test_undo_refused_on_git_precheck | đạt |
| AC-21 | `cmd.test_one` change_text, propose, source | 0 | change_text 9/0/0; source 110/0/0; propose `OK` | test_change_text::test_notes_branch_upstream_and_core_warning | đạt |
| AC-22 | `cmd.test_one` proposal | 0 | `Ran 25 tests in 74.421s` `OK` | test_erp_ai_change_proposal::test_form_data_per_state | đạt (tự động); xem form bằng mắt: việc của người sau merge |
| AC-23 | như AC-6; architecture | 0 | `Ran 117` `OK`; 177/0/0 | test_apply_job::test_remote_refs_and_other_branches_unchanged_after_apply_and_undo | đạt |
| AC-24 | `cmd.test_one` change_link, propose | 0 | change_link 6/0/0; propose `OK` | test_change_link::test_signature_fits_only_its_own_proposal_and_action | đạt |
| AC-25 | `cmd.test_one` test_change_decision | 0 | `Ran 10` (1 xanh) + `Ran 9` `OK` | test_change_decision::test_post_approve_sets_approved_and_one_job_survives_request_end | đạt (tự động); trình duyệt thật: việc của người sau merge |
| AC-26 | như AC-25 | 0 | 1 + 9 `OK` | test_change_decision::test_get_is_refused_and_changes_nothing, ::test_refused_accounts | đạt |
| AC-27 | như AC-25; apply_job | 0 | 1 + 9 `OK`; `Ran 117` `OK` | test_change_decision::test_link_approval_still_rechecked_at_apply; test_apply_job::test_rechecks_fail_without_writing | đạt |
| AC-28 | `cmd.test_one` result_comment, apply_job | 0 | result_comment `Ran 3` `OK` (3 ca 1213 của lần cả app); `Ran 117` `OK` | test_apply_job::test_result_comment_has_no_remote_url_or_fake_token, ::test_one_result_comment_per_outcome; test_result_comment::test_reason_with_url_email_or_token_is_masked | đạt (tự động); dòng `Info` trên trang phiếu thật: việc của người sau merge |
| AC-29 | `cmd.test_one` test_classification | 0 | 39/0/0 | test_classification::test_act_now_block_only_with_action_tools | đạt (prompt); đo với model thật: sau G4 |
| AC-30 | `cmd.test_one` test_site_api | 0 | 67/0/0 (junit cả app) | test_site_api::test_creates_user_with_an_allowed_role | đạt |
| AC-31 | như AC-30 | 0 | 67/0/0 | test_site_api::test_refuses_each_forbidden_role | đạt |
| AC-32 | registry, site_api, policy | 0 | 41/0/0; 67/0/0; 37/0/0 | test_registry::test_unrestricted_enabled_defaults_to_zero_and_only_system_manager_can_set | đạt |
| AC-33 | site_api, agent_write_guard | 0 | 67/0/0; write_guard `Ran 5` `OK` | test_agent_write_guard::test_every_guarded_hook_refuses_the_agent; test_site_api::test_own_configuration_log_and_secrets_stay_closed | đạt |
| AC-34 | `cmd.test_one` test_agent_runner | 0 | `Ran 85` `OK` | test_agent_runner::test_unrestricted_actions_are_logged, ::test_six_large_deletes_keep_one_bounded_log_row, ::test_one_byte_over_the_bound_replaces_the_largest_values_by_the_marker | đạt (F-1 sửa ở T64; giới hạn còn lại đã được nhận bằng quyết định, journal) |
| AC-35 | `cmd.test_one` test_site_api | 0 | 67/0/0 | test_site_api::test_before_after_never_carry_secret_fields, ::test_deleted_values_scrub_child_rows, ::test_child_row_held_as_document_is_scrubbed | đạt (F-2 sửa ở T62) |
| NFR-1 | như AC-3, AC-8 | 0 | `OK` | test_propose_change::test_command_proposal_makes_zero_subprocess_calls; test_apply_job::test_repeated_job_does_nothing | đạt |
| NFR-2 | như AC-6 | 0 | `Ran 117` `OK` | test_apply_job::test_apply_writes_exact_approved_bytes | đạt |
| NFR-3 | process_runner, apply_job | 0 | 17/0/0; `Ran 117` `OK` | test_process_runner::test_limit_comes_from_deadline_and_kills_group | đạt |
| NFR-4 | process_runner | 0 | 17/0/0 | test_process_runner::test_output_cut_to_400_lines | đạt |
| NFR-5 | như AC-13 | 0 | `Ran 117` `OK` | test_apply_job::test_fake_key_never_in_proposal_result_log_comment | đạt |
| NFR-6 | như AC-6 | 0 | `Ran 117` `OK` | test_apply_job::test_apply_and_undo_rows_carry_commit_sha | đạt |
| NFR-7 | như AC-23 | 0 | `Ran 117` `OK` | test_apply_job::test_remote_refs_and_other_branches_unchanged_after_apply_and_undo | đạt |
| NFR-8 | như AC-6 | 0 | `Ran 117` `OK` | test_apply_job::test_commit_metadata_has_no_email_url_or_token | đạt |
| NFR-9 | so HEAD/status 4 repo lõi (phần 2); test_source | 0 | `diff` rỗng 4 lần; source 110/0/0 | test_source::test_git_sandbox_redirects_apps_root | đạt |
| NFR-10 | như AC-25 | 0 | 1 + 9 `OK` | test_change_decision::test_form_script_posts_once_without_confirm_and_strips_params | đạt |
| NFR-11 | như AC-34 | 0 | `Ran 85` `OK` | test_agent_runner::test_six_large_deletes_keep_one_bounded_log_row | đạt |

Mục rà thêm (review-chg001): M1 đạt, M2 đạt (`Ran 117` `OK`), M3 đạt, M4 đạt, M5 đạt (`Ran 5` `OK`).

## Chạy lại lượt chốt

Mỗi module một lần, nối tiếp, `flock -w 1800 /home/miyano/frappe-bench/apps/erp_ai/.team/miyano-site.lock env PYTHONPATH=<worktree> bench --site miyano run-tests --module <m> --junit-xml-output v/rr3/<m>.xml` (exit 0 cả 5 lần). Cùng lúc ngoài khóa có `run-tests --app erp_ai` (pid 851601) của phiên khác.

| module | bắt đầu | dòng kết quả | phân loại |
|---|---|---|---|
| `erp_ai.agent.tools.test_route_ticket` | 19:40:24 | `Ran 29 tests in 51.694s` / `FAILED (errors=3)` — 3 × 1213 | môi trường; nhưng `test_sla_chosen_by_complexity_condition` đỏ 1213 ở cả 3 lần (cả app, rr, rr3) — F-5 |
| `erp_ai.tests.test_ticket_panel` | 19:41:22 | `Ran 36 tests in 55.310s` / `FAILED (failures=1, errors=19)` — 18 × 1213, 1 error `Could not find Allocated To: panel.agent@example.com`, 1 failure `[] is not true` (subTest `instructor_role`), cả hai là hệ quả của fixture bị 1213 | môi trường; `test_thread_ignores_non_comment_types` đỏ 1213 ở cả 3 lần — F-5. Cả app trên `ba89ab3`: 35/36 xanh |
| `erp_ai.erp_ai_agent.doctype.erp_ai_change_proposal.test_erp_ai_change_proposal` | 19:42:26 | `Ran 25 tests in 74.421s` / `OK` | đạt → AC-5, AC-22 (phần tự động) |
| `erp_ai.eval.test_run_eval` | 19:46:49 | `Ran 22 tests in 2.930s` / `OK` | đạt |
| `erp_ai.gateway.test_gateway` | 19:46:59 | `Ran 65 tests in 4.722s` / `FAILED (failures=1)` — chỉ `test_api_key_never_leaks` (`'frappe.logger' : success`) | F-3 (lần thứ 4 cùng thông điệp: rr gateway2, gateway3, develop, rr3) |

`git diff --stat develop...HEAD` trên `route_ticket.py`, `test_route_ticket.py`, `ticket_panel.py`, `test_ticket_panel.py`, `hooks.py`: rỗng — F-5 không do diff của nhánh.

## Kiểm chung

| kiểm | lệnh | kết quả |
|---|---|---|
| `cmd.test` | `bench --site miyano run-tests --app erp_ai` (PYTHONPATH worktree) | `Ran 1496 tests in 1079.598s` / `FAILED (failures=1, errors=128)`; không có lần nào `OK` |
| `cmd.lint` | `pre-commit run --all-files` trên `ba89ab3` (`v/lint.log`) | 12 hook `Passed`, 0 `Failed` |
| `cmd.typecheck`, `cmd.build` | — | profile không có slot |
| skip marker | `git diff develop...HEAD -- '*.py' \| grep -cE '^\+.*(@unittest\.skip\|skipIf\|skipUnless\|expectedFailure\|\.skipTest\(\|pytest\.mark\.(skip\|xfail))'` | `0` |
| assert bị xóa | `git diff develop...HEAD -- '*.py'`: dòng `-self.assert…` 357, dòng `+self.assert…` 1423; 47 dòng xóa không xuất hiện lại nguyên văn (297/357 là `test_architecture.py`, viết lại nguyên văn) | 47 dòng thuộc đổi hợp đồng Amd-2 (đường quyết định GET → POST từ form: `test_change_decision` 11 dòng; script form `test_erp_ai_change_proposal` 3; kết quả `site_api` thêm trường 6; câu lý do `test_apply_job` 3; `test_propose_change` 23 dòng đổi chỗ). Chưa đối chiếu từng dòng với dòng thay — rủi ro còn lại R-4 |
| protected_paths | `git diff --name-only develop...HEAD` (73 file) đối chiếu `.env`, `.env.*`, `**/*.pem`, `**/*.key`, `license.txt` | 0 file khớp |
| migration | `cmd.migrate` | không chạy ở lượt này (lệnh cấm); DocType mới/đổi đã chạy qua `migrate` của phiên khác (`v/migrate.log`), up-down-up chưa làm — xem R-3 |
| cài đặt site | `bench --site miyano mariadb -e "SELECT field, value FROM tabSingles WHERE doctype='ERP AI Setting' AND field IN (...)"` | đọc lại 19:47 sau lượt chốt: `auto_assign_enabled` = `1`; `code_change_apps` = `frappe\nerpnext\nhelpdesk\nhrms`. qa không ghi cài đặt nào ở lượt này |

## Phát hiện

| mức | STD | file:dòng | mô tả | sửa |
|---|---|---|---|---|
| major | STD-TEST-6 | `erp_ai/gateway/test_gateway.py:871,895-903` + `erp_ai/agent/tools/source.py:13` + `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py:9` | **F-3.** `TestApiKeyLeak::test_api_key_never_leaks` đỏ khi chạy riêng module, cả trên `team/FEAT-004` (`rr/gateway3.log`) và trên `develop` (`rr/gateway_develop.log`): `AssertionError: Items in the first set but not the second: 'frappe.logger' : success`. Chẩn đoán bằng đọc mã (không chạy script dò): test vá `frappe.logger` rồi kiểm `self.logger.called`; ca `success` gọi `add_credential` → `frappe.get_single("ERP AI Setting")` → nạp controller, mà từ commit `2ab30f9` (FEAT-004, có trên cả `develop`) controller `import source`, và `source.py:13` gọi `frappe.logger("erp_ai.source")` ở mức module. Chạy riêng thì lần nạp đầu rơi vào lúc logger đang bị vá → "logger được dùng"; chạy cả app thì module đã nạp trước nên xanh (17:20, 17:55). Đối số của lời gọi là tên logger, không phải khóa: không có rò khóa; vị trí khóa giả trong log: chỉ dòng traceback mang tên subTest, không chép giá trị | test: nạp controller/`source` trước khi vá, hoặc chỉ coi là "dùng" khi có lời gọi ghi (`.warning/.info/...`); hoặc `source.py` lấy logger lúc dùng. Owner: dev, task mới (đề xuất T65) |
| major | STD-TEST-6 | `erp_ai/erp_ai_agent/doctype/erp_ai_log/test_erp_ai_log.py:119-122` | **F-4.** `test_no_role_can_write_or_delete` đỏ trong lần cả app (`Items in the first set but not the second: 'ERP AI Instructor'`), xanh khi chạy riêng (`rr/…test_erp_ai_log.log` `Ran 1` `OK`). Mã ứng dụng không cấp quyền `ERP AI Instructor` trên `ERP AI Log` (grep `LOG_DOCTYPE`/`ERP AI Log` + perm/instructor: 0 chỗ cấp) → một test chạy trước để lại quyền/meta cache. Chưa tìm được test gây ra | tìm test để lại DocPerm/cache (`cmd.test` cả app, rồi cắt đôi danh sách module). Owner: dev, task mới (đề xuất T66) |
| minor | STD-TEST-7 | `erp_ai/agent/tools/test_route_ticket.py` (`test_sla_chosen_by_complexity_condition`), `erp_ai/tests/test_ticket_panel.py` (`test_thread_ignores_non_comment_types`) | **F-5.** Hai test này đỏ `QueryDeadlockError 1213` ở cả 3 lần trên `ba89ab3` (cả app 19:18, rr 19:26/19:32, rr3 19:40/19:41), trong khi các ca 1213 khác đổi tên giữa các lần. File của chúng và `hooks.py` không đổi so với `develop` → không thuộc diff FEAT-004; chưa có lần xanh nào trên site dùng chung | ghi `docs/team/debt.md` (STD-TEST-7), chạy lại khi site độc quyền; nếu vẫn đỏ thì tìm kết nối thứ hai trong test. Owner: team-leader xếp (ngoài FEAT-004) |
| info | — | site `miyano` | 128 error 1213 ở lần cả app và các ca 1213 còn lại ở "Chạy lại lượt chốt" là môi trường (chạy test song song trên một site); không có assert sai nào trong các ca đó | một lần `cmd.test` khi không phiên nào khác chạy test |

## Chỉ người quan sát được sau merge

- AC-22: xem form duyệt thật ở từng trạng thái (app, đường dẫn, diff, nhánh, thông điệp commit, cảnh báo, cờ hoàn tác; mã commit sau áp dụng/hoàn tác).
- AC-25: mở liên kết Duyệt/Từ chối bằng trình duyệt thật khi đang đăng nhập, xem chuyển về trang phiếu, không có hộp xác nhận.
- AC-28: dòng `Info` kết quả trên trang phiếu Helpdesk thật (theo mã: hiện như dòng hoạt động mang tên người duyệt, phần 3).
- AC-29: đo "hỏi lại 0 lần" với model thật (sau G4).
Theo tiền lệ FEAT-002/003, các bước này không chặn phán quyết; bench phục vụ `develop`, `ui: false`, không có Playwright.

## Rủi ro còn lại (cho As-Built)

- R-1: Giới hạn đã được nhận (journal, quyết định rework T62/T64): mục vượt 60000 byte chỉ còn dấu `[đã cắt]`; lượt có quá nhiều lệnh ghi bỏ các mục cuối. Bản đầy đủ chờ FEAT-005 AC-13.
- R-2: Đọc khóa qua `api_call_method` (`frappe.client.get_list` với `fields` lạ) chỉ được chặn bởi Frappe @ `2e9ecdc` (probe (c) phần 3); nâng Frappe thì chạy lại.
- R-3: Migration của DocType mới chưa được qa kiểm up → down → up (lượt này cấm migrate).
- R-4: 47 dòng assert bị xóa chưa đối chiếu từng dòng với dòng thay.
- R-5: AC-11 thiếu kịch bản câu chèn khi ô Toàn quyền bật.
- R-6: Cả app chưa có lần `OK` trên `ba89ab3`.

## Checklist nghiệm thu (6)

1. Mọi tiêu chí có lệnh + exit + đầu ra trên commit đã ghi: đạt (46 dòng = 35 AC + 11 NFR).
2. Ca biên/lỗi ngoài đường thuận: đạt (stale, tamper, timeout, index lock, byte bound +1, bảng con có khóa).
3. Test phủ khẳng định giá trị viết tay: đạt cho các test chính (phần 1–3); F-3 là test phụ thuộc thứ tự.
4. `cmd.test`/`cmd.lint` xanh: KHÔNG ĐẠT — lint xanh; `cmd.test` không có lần `OK`, còn F-3, F-4 (thuộc FEAT-004) và F-5 (ngoài diff).
5. Không skip marker, không assert bị nới: đạt một phần — 0 marker; R-4 chưa đối chiếu xong.
6. DoD build + không đụng protected_paths: đạt (0 file khớp); As-Built/CHANGELOG: owner writer, sau G4.

## Phán quyết

`rework`: tiêu chí AC/NFR đạt trên `ba89ab3`, nhưng checklist mục 4 không đạt.
- F-3 — tái hiện: `flock -w 1800 .team/miyano-site.lock env PYTHONPATH=<worktree> bench --site miyano run-tests --module erp_ai.gateway.test_gateway --test test_api_key_never_leaks` → `FAILED (failures=1)`; task mới T65 (dev).
- F-4 — tái hiện: `cmd.test` cả app → `test_erp_ai_log::test_no_role_can_write_or_delete` failure; task mới T66 (dev).
- Sau đó: một lần `cmd.test` độc quyền trên site rồi `/team:verify FEAT-004`.

Verdict: rework
