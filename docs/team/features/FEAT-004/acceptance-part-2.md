# Nghiệm thu FEAT-004 — phần 2/3 (AC-13..AC-23, NFR-5..NFR-9)

Commit kiểm: `abd2fa2ed110a014cf4fd6bcb0ee01041a0e4ead` (team/FEAT-004, worktree `.claude/worktrees/feat-004`). Lúc bắt đầu, `git status -sb` chỉ có `M docs/team/journal/FEAT-004.md`, không có file mã.
Người kiểm: qa, 2026-11-14, 18:01–18:18 (+07).

## Cách chạy

`cmd.test_one` cho từng module, chạy từ thư mục bench với `PYTHONPATH=<worktree>` và `--junit-xml-output`. Đã kiểm rằng `import erp_ai.agent.changes.apply_job` nạp đúng `.../worktrees/feat-004/erp_ai/agent/changes/apply_job.py`. Trên `miyano`, `bench run-tests` thoát 0 cả khi FAILED, nên kết luận dựa vào dòng `Ran N … OK/FAILED` và junit. Các module chạy tuần tự. Site `miyano` dùng chung với phiên khác (FEAT-007, phần 1/3) nên DB bị tranh khóa nặng: lỗi `QueryDeadlockError (1213)` và `Lock wait timeout (1205)` được xếp vào lỗi **môi trường** (BLOCKED), không phải lỗi mã.

Log và junit nằm ở `/tmp/claude-1000/-home-miyano-frappe-bench-apps-erp-ai/6c38287b-bf21-45d8-bbe6-babd0767ec62/scratchpad/p2/`.

| Module | Dòng kết quả | Ghi chú |
|---|---|---|
| agent.changes.test_apply_job (lần 1) | exit 1, 0 test | `before_tests` của hrms: `QueryTimeoutError … being modified by another user` (Holiday List) |
| agent.changes.test_apply_job (lần 2) | `Ran 117 tests in 405.447s` / `FAILED (errors=56)` | 56/56 lỗi là `QueryDeadlockError (1213)`; 0 failure assertion |
| agent.tools.test_propose_change | `Ran 32 tests in 64.004s` / `OK` | |
| tests.test_architecture | `Ran 177 tests in 13.341s` / `OK` | |
| agent.test_agent_runner | `Ran 78 tests` / `FAILED (failures=4, errors=1)` | 1 deadlock; 4 FAIL ở L1/site-admin (`assign_owner` thừa), không thuộc phần 2, xem dưới |
| agent.tools.test_registry | `Ran 41 tests` / `FAILED (errors=1)` | deadlock; chạy lại theo tên vẫn deadlock |
| test_change_decision | `Ran 10 tests` / 2 lỗi deadlock | chạy lại theo tên: `test_link_approval_still_rechecked_at_apply` `OK`; `test_refused_accounts` vẫn deadlock |
| erp_ai_change_proposal.test_erp_ai_change_proposal | `Ran 25 tests in 58.677s` / `OK` | |
| agent.changes.test_result_comment | `Ran 6 tests` / 1 lỗi deadlock | chạy lại theo tên: `Ran 1 test` `OK` |
| agent.test_run_log | `Ran 16 tests` / `OK` | |
| agent.tools.test_site_api | `Ran 60 tests` / `OK` | |
| agent.changes.test_process_runner | `Ran 17 tests` / `OK` | |
| agent.test_classification | `Ran 39 tests` / `OK` | |
| agent.tools.test_change_guard | `Ran 35 tests` / `OK` | |
| agent.test_change_text | `Ran 9 tests` / `OK` | |
| agent.tools.test_source | `Ran 110 tests in 4.615s` / `OK` | |
| agent.changes.test_transitions | `Ran 42 tests` / 1 lỗi `Lock wait timeout` | chạy lại theo tên: `Ran 1 test` `OK` |

Ngoài phần 2 (báo team-leader): khi chạy lại theo tên, `test_agent_runner::test_l1_empty_route_still_saves_ai_fields_applied_one` là **FAIL thật** (`Lists differ: … {'tool': 'assign_owner', …}] != […]`). Ba test L1/site-admin còn lại bị deadlock khi chạy lại nên chưa phân loại được. Các test này thuộc AC của phần 1/3, cần kiểm tiếp ở đó (có thể do dữ liệu site, ví dụ quy tắc phân công trên HD Ticket).

## Bảng tiêu chí

| AC | Test | Lệnh + dòng kết quả | Kết luận | Ghi chú |
|---|---|---|---|---|
| AC-13 | test_apply_job.py::test_fake_key_never_in_proposal_result_log_comment; test_process_runner.py::test_env_is_allowlist_only | test_apply_job lần 2: testcase này pass (junit); test_process_runner `Ran 17 … OK` | đạt | Test có đối chứng âm: gieo khóa vào env, nhánh, ghi chú thì bộ dò bắt được (`stores <= leaked`) → test sẽ đỏ nếu mất lớp lọc |
| AC-14 | test_classification.py::test_reason_system_with_change_tools_adds_approval_block; test_agent_runner.py::test_prompt_variant_follows_grant_result | test_classification `Ran 39 … OK`; trong junit test_agent_runner, testcase này pass | đạt | Không cấp tool thì so `system == self._base_system()` (trùng hệt) |
| AC-15 | test_architecture.py (cả lớp); ADR | `Ran 177 tests … OK`; `grep -c ADR-005`: ADR-011=6, ADR-012=1, ADR-013=2, ADR-022=1; ADR-022 ghi "commit local", "không push, không fetch, không đổi nhánh, không sửa lịch sử" và có "Hoàn tác quyết định" | đạt | Bốn ADR đều ở `proposed`. Việc chấp nhận ADR do người làm ở G4 |
| AC-16 | test_change_guard.py::{test_core_apps_allowed_only_when_listed, test_erp_ai_refused_even_when_listed_in_temp_root, test_running_erp_ai_package_repo_refused, test_non_core_app_has_no_core_flag}; test_propose_change.py::test_core_app_proposal_created_when_listed | test_change_guard `Ran 35 … OK`; test_propose_change `Ran 32 … OK` | đạt | |
| AC-17 | test_apply_job.py::test_apply_creates_one_commit_with_only_target_path (pass); ::test_new_file_is_created_and_committed (lỗi deadlock); test_process_runner.py::test_git_write_argv_shapes (pass); test_change_text.py::test_apply_message_template_and_preview (pass) | junit test_apply_job lần 2 | BLOCKED (môi trường) | Test chính đạt. Nhánh "file mới" chưa có kết quả vì deadlock. Test kế hoạch `test_apply_new_file_commit_adds_only_that_path` không tồn tại; `test_new_file_is_created_and_committed` thay vào, kiểm `show --name-only HEAD == [NEW_REL]` |
| AC-18 | test_source.py::{test_read_git_state_refusals, test_read_git_state_other_dirty_file_does_not_block}; test_propose_change.py::test_git_refusal_creates_zero_proposals; test_apply_job.py::{test_git_precheck_fails_at_apply_without_write_or_commit, test_branch_changed_after_approval_becomes_stale, test_other_dirty_files_do_not_block_apply} (pass); ::test_index_lock_fails_fast (deadlock) | test_source `Ran 110 … OK`; junit test_apply_job | BLOCKED (môi trường) | Còn thiếu kết quả nhánh "khóa git đang bị giữ" (NFR-3) |
| AC-19 | test_apply_job.py::{test_repo_hooks_never_run, test_postcheck_mismatch_keeps_commit_and_fails, test_undo_commit_failure_restores_applied_bytes} (pass); ::{test_commit_failure_restores_file_and_index, test_commit_timeout_restores_file, test_commit_reported_failed_but_head_moved_goes_to_postcheck, test_commit_failed_while_human_commit_moved_head_restores} (deadlock) | junit test_apply_job lần 2 | BLOCKED (môi trường) | (c) hook không chạy: đạt. (a)/(b) cho bước áp dụng: chưa có kết quả |
| AC-20 | test_apply_job.py::{test_undo_creates_one_commit_restoring_previous_bytes, test_undo_new_file_removes_from_disk_and_tree, test_undo_refused_when_apply_commit_not_ancestor} (pass); ::test_undo_refused_on_git_precheck (deadlock) | junit test_apply_job lần 2 | BLOCKED (môi trường) | |
| AC-21 | test_change_text.py::test_notes_branch_upstream_and_core_warning; test_propose_change.py::{test_comment_shows_branch_upstream_ahead_and_core_warning, test_non_core_app_comment_has_no_core_warning}; test_source.py::test_upstream_with_url_like_name_is_masked | test_change_text `Ran 9 … OK`; test_propose_change `Ran 32 … OK`; test_source `Ran 110 … OK` | đạt | |
| AC-22 | test_erp_ai_change_proposal.py::{test_form_data_per_state, test_form_layout_git_sections} | `Ran 25 tests in 58.677s` / `OK` | NOT VERIFIABLE (bước người xem) | Phần tự động: đạt. Bước "qa mở form trên miyano, dán ảnh hoặc mô tả": `SELECT COUNT(*) FROM tabERP AI Change Proposal` = 0, các cột git đã có (`target_branch`, `is_core_app`, `commit_message`, `apply_commit_sha`, `undo_commit_sha`). qa không có trình duyệt (`ui: false`, không có Playwright) và không được tạo dữ liệu mẫu trên site dùng chung → NEEDS_ANSWER: cần người gửi ảnh form ở 3 trạng thái |
| AC-23 | test_architecture.py::{test_git_subcommands_only_allowed_sets_per_file, test_no_forbidden_git_operations_in_product} (pass); test_apply_job.py::test_remote_refs_and_other_branches_unchanged_after_apply_and_undo (deadlock) | `Ran 177 … OK`; junit test_apply_job | BLOCKED (môi trường) | Luật kiến trúc: đạt. Phép so ref remote trước/sau: chưa có kết quả |
| NFR-5 | như AC-13 | như AC-13 | đạt | |
| NFR-6 | test_transitions.py::test_each_step_writes_exactly_one_change_row (pass); test_apply_job.py::test_apply_and_undo_rows_carry_commit_sha (deadlock) | test_transitions `Ran 42`, lỗi duy nhất `Lock wait timeout` ở test khác, chạy lại theo tên `OK` | BLOCKED (môi trường) | Còn thiếu kết quả phần mã commit trong dòng nhật ký |
| NFR-7 | test_apply_job.py::{test_apply_creates_one_commit_with_only_target_path, test_undo_creates_one_commit_restoring_previous_bytes, test_repo_hooks_never_run} (pass); ::test_remote_refs_and_other_branches_unchanged_after_apply_and_undo (deadlock) | junit test_apply_job lần 2 | BLOCKED (môi trường) | |
| NFR-8 | test_change_text.py::test_safe_person_name; test_source.py::test_git_env_has_no_home_and_ignores_global_config (pass); test_apply_job.py::test_commit_metadata_has_no_email_url_or_token (deadlock) | test_change_text `OK`, test_source `OK` | BLOCKED (môi trường) | Test chính (metadata commit) chưa có kết quả |
| NFR-9 | test_source.py::test_git_sandbox_redirects_apps_root (pass); quan sát trực tiếp | Ghi `rev-parse HEAD`, nhánh, md5 của `status --porcelain` và `for-each-ref` cho frappe/erpnext/helpdesk/hrms trước lượt chạy đầu (18:01) và sau mỗi lượt (18:07, 18:09, 18:16, 18:17): `diff` rỗng cả 4 lần (`CORE_UNCHANGED`…`CORE_UNCHANGED4`). HEAD: frappe 2e9ecdc (version-15), erpnext 8cf5d66 (develop), helpdesk a185896 (version-15), hrms e1f22e4 (feat/timesheet-and-payroll) | đạt | Thay đổi chưa commit có sẵn của người ở frappe/erpnext/helpdesk giữ nguyên (md5 không đổi). Ghi chú: trong test_apply_job, chỉ `TestCommitCrossChecks` dùng `RealCoreReposUntouchedMixin`; design ghi "mọi lớp dùng GitSandbox". Đây là lệch nhỏ so với kế hoạch test và đã được quan sát trực tiếp ở trên bù lại |

## Kiểm tra khác

- `cmd.lint` (`pre-commit run --all-files`) chạy trên bản xuất `git archive abd2fa2` trong scratchpad, không chạm repo: exit 0, 12 hook `Passed`, 0 file bị hook sửa.
- Skip marker (`test.skip_markers` + `pytest.mark.skip/xfail`) trong `git diff f039112 HEAD -- '*.py'` (BASE theo tasks.md): **0 dòng** (kết quả rỗng).
- Assertion bị xóa: `self.assert` −252 / +2525 dòng. Trong 252 dòng xóa, 246 có lại nguyên văn (test_architecture được sắp lại). 6 dòng không có lại, đều có lý do:
  - 3 assert của `test_enqueue_call_shape_requires_five_parameters` được thay bằng 4 test chặt hơn (`requires_exactly_two_calls`, `requires_each_target_once`, `rejects_target_outside_set`, `requires_five_parameters_on_each_call`), theo ADR-013 QĐ 2 (thêm job áp dụng).
  - `len(_all_specs()) == 11` → `21` (tool mới theo spec).
  - `cache_control` của `get_tool_schemas("L1", False)` chuyển sang `test_agent_runner.py:890` với chữ ký 3 tham số.
  - `f"{spec.name}"` → `f"{name}"`: chỉ đổi thông điệp.
  - Không có test bị làm yếu.
- Test bị xóa: chỉ `test_enqueue_call_shape_requires_five_parameters`, đã được thay như trên.

## Tổng phần 2

Đạt 7 (AC-13, AC-14, AC-15, AC-16, AC-21, NFR-5, NFR-9) · Trượt 0 · BLOCKED do môi trường 8 (AC-17, AC-18, AC-19, AC-20, AC-23, NFR-6, NFR-7, NFR-8: tổng 10 test chính bị `QueryDeadlockError`, 0 assertion fail) · NOT VERIFIABLE 1 (AC-22, bước xem form).

Để tiếp tục: khi site `miyano` không còn phiên test khác, chạy lại theo tên 10 test sau trong `erp_ai.agent.changes.test_apply_job`: test_new_file_is_created_and_committed, test_index_lock_fails_fast, test_commit_failure_restores_file_and_index, test_commit_timeout_restores_file, test_commit_reported_failed_but_head_moved_goes_to_postcheck, test_commit_failed_while_human_commit_moved_head_restores, test_undo_refused_on_git_precheck, test_remote_refs_and_other_branches_unchanged_after_apply_and_undo, test_apply_and_undo_rows_carry_commit_sha, test_commit_metadata_has_no_email_url_or_token.

Kết luận phần 2: BLOCKED (môi trường, DB của site dùng chung bị deadlock). Chưa có verdict cho phần này: 0 tiêu chí trượt, nhưng 8 tiêu chí chưa có bằng chứng đầy đủ và 1 tiêu chí cần ảnh từ người. File `acceptance.md` ghép từ ba phần sẽ mang dòng `Verdict:`.
