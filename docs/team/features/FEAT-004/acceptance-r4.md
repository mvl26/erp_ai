# FEAT-004 — Nghiệm thu R-4: đối chiếu assert bị xóa/nới trong test

Commit kiểm: `da00518` (team/FEAT-004). Base: `develop` @ `5cfc0ec` (= `git merge-base develop da00518`). Chỉ đọc mã và tài liệu; không chạy test, không chạy bench, không ghi git.

## Cách đếm

- Lệnh: `git -C <worktree> diff -U0 develop...da00518 -- '*test_*.py' 'erp_ai/tests/'` (13 file, 12088 thêm / 1691 xóa), đọc bằng script chỉ-đọc trong scratchpad: dòng `-` có chữ `assert` hoặc `self.fail(`, so sau `strip()` với mọi dòng `+` của cùng file rồi của mọi file.
- Kết quả: **363** dòng assert bị xóa; **309** xuất hiện lại nguyên văn trong cùng file (298 của `test_architecture.py`, file này chỉ mất đúng 1 dòng không nguyên văn: `from typing import ClassVar`; 111 hàm `test_` bị xóa đều còn tên trong file mới); **2** xuất hiện lại nguyên văn ở file khác; **52** không xuất hiện lại.
- 52 = 47 dòng `self.assert…` (đúng con số R-4 của `acceptance.md`, đếm trên `ba89ab3`; từ `ba89ab3` tới `da00518` chỉ có T69 sửa `test_source.py`) + 5 dòng chữ `assert` không theo mẫu `self.assert…` (`def assertRefused`, `self.page.assert_called_once()` ×2, `self.page.assert_not_called()`, `logger.exception.assert_called_once()`).
- Bổ sung vì đếm theo dòng bỏ sót: giá trị kỳ vọng nằm ở dòng không có chữ `assert` (tuple lý do trong vòng lặp, assert nhiều dòng) — bảng B; hàm test bị xóa/đổi tên — bảng C.
- Skip marker (`test.skip_markers` của `.team/profile.json`: `@unittest.skip`, `@unittest.skipIf`, `@unittest.expectedFailure`, `.skipTest(`, thêm `skipUnless`, `pytest.mark.skip/xfail`): `git diff -U3 develop...da00518 -- '*test_*.py' 'erp_ai/tests/' | grep -nE '^\+.*(@unittest\.skip|skipIf|skipUnless|expectedFailure|\.skipTest\(|pytest\.mark\.(skip|xfail))'` → không dòng nào, `grep` exit 1. **0 marker mới.**

Căn cứ viết tắt: **Amd-2** = spec Amendment 2 (N-7); **ADR-023 QĐ1** = duyệt từ liên kết mở form rồi POST, không còn GET đổi trạng thái (`docs/team/adr/ADR-023.md:28-30`, trạng thái *proposed*); **D3.1/D3.2** = design.md §3.1 bảng tham số (`:207-263`) và bảng lý do git (`:360-368`); **D4.3/D4.4** = design.md bước áp dụng/hoàn tác (`:608-633`, `:667`); **DA-4** = design-addendum-4 QĐ-D1; **T69** = commit `cef90a3` (logger lấy lúc dùng, sửa F-3).

## A. 52 dòng assert bị xóa, không xuất hiện lại nguyên văn

Dòng cũ = số dòng trong file ở `develop`. Dòng mới = số dòng ở `da00518`.

| # | File:dòng cũ | Test cũ | Assert bị xóa (rút gọn) | Thay bằng (file:dòng mới :: test — assert mới) | Căn cứ | Kết luận |
|---|---|---|---|---|---|---|
| 1 | test_apply_job.py:174 | TestApplyCode (test file đích đổi → stale) | `failure_reason == "file đã đổi từ lúc đề xuất"` | test_apply_job.py:252 — `== "file đích đã đổi kể từ lúc đề xuất"` (cùng test) | D4.3 bước 3.1 (`design.md:614`), nguyên văn | có căn cứ, giữ độ chặt |
| 2 | test_apply_job.py:238 | TestApplyCode (commit lỗi) | `== "git commit lỗi, file đã được trả lại như cũ"` | :323 — `== f"{GIT_COMMIT_FAILED_TEXT}: fatal"` (hằng viết tay :66 = câu D3.2) | D3.2 `GIT_COMMIT_FAILED` (`design.md:366`) + DA-4 (thêm dòng git đã làm sạch) | có căn cứ, chặt hơn |
| 3 | test_apply_job.py:347 | TestNewFileAndUndo (hoàn tác khi file đã đổi) | `== "file đã đổi sau khi áp dụng, không hoàn tác tự động được"` | :1534 — `== "file đã đổi sau khi áp dụng, không hoàn tác"`; thêm :1628 | D4.4 bước 3 (`design.md:667`), nguyên văn | có căn cứ |
| 4 | test_propose_change.py:107 | test_file_change_creates_a_pending_proposal_and_touches_nothing | `result["ok"] == True` | test_propose_change.py:169-171 :: test_file_change_creates_pending_proposal_and_comment_without_touching_disk — `(ok, status, branch) == (True, "Chờ duyệt", "feature/propose")` + :168 tập khóa đúng | D3.1 (tham số `find`/`replace`, kết quả có `branch`), design D-6 (`:1024`) | chặt hơn |
| 5 | test_propose_change.py:108 | như #4 | `result["status"] == CHANGE_STATUS_PENDING` | như #4 (:170) | như #4 | chặt hơn |
| 6 | test_propose_change.py:119 | như #4 | `(target_branch, upstream_ref, is_core_app) == ("main","",0)` | :182 — `== ("feature/propose","",0)` trên nhánh khác mặc định | như #4 | chặt hơn (nhánh viết cứng không qua được) |
| 7 | test_propose_change.py:126 | như #4 | `rev-parse HEAD == head` | :189 — `git_snapshot() == git_before` (HEAD + `status --porcelain --untracked-files=all`) + :188 hash file | như #4 | chặt hơn |
| 8 | test_propose_change.py:127 | như #4 | `status --porcelain == ""` | như #7 | như #4 | chặt hơn |
| 9 | test_propose_change.py:130 | như #4 | `assertIn(doc.name, comment)` | :195-196 — comment `startswith` đoạn đầu viết tay có link + mã + "đang chờ duyệt: sửa <code>…</code>" | Amd-2 AC-24, AC-22 [changed] | chặt hơn |
| 10 | test_propose_change.py:131 | như #4 | `assertIn("Chờ duyệt", comment)` | như #9 | như #9 | chặt hơn |
| 11 | test_propose_change.py:133 | như #4 | `assertIn('<a href="{link}">', comment)` | như #9; thêm :224 link "Xem nội dung thay đổi" == form | như #9 | chặt hơn |
| 12 | test_propose_change.py:139 | như #4 | `assertIn("bench restart", comment)` | :202 — `assertIn("<p>Sau khi áp dụng cần người chạy bench restart.</p>")`; :383 file `.md` không có câu này | Amd-2 AC-22 [changed] | chặt hơn |
| 13 | test_propose_change.py:155 | test_file_change_refusals_create_nothing | `assertFalse(result["ok"])` (vòng 9 ca) | :264 :: test_edit_errors_create_nothing — `== {"ok": False, "reason": <câu D3.1>}` 11 ca; :325 :: test_each_guard_refusal_creates_zero_proposals — 10 ca dict đúng | D3.1 bảng lỗi (`design.md:259-263`), D-6 | chặt hơn (so cả dict) |
| 14 | test_propose_change.py:156 | như #13 | `assertIn(phrase, reason)` | như #13 | như #13 | chặt hơn |
| 15 | test_propose_change.py:158 | như #13 | `change(["x = 1"]) == {"ok":False,"reason":"tham số không hợp lệ: edits"}` | :266-279 — 4 ca schema `tham số không hợp lệ: find/replace`; dạng cũ `edits` → `…: find` | D3.1 (`edits` thay bằng `find`/`replace`, `design.md:226-227`) | có căn cứ |
| 16 | test_propose_change.py:173 | test_dirty_target_and_too_long_file_are_refused | `assertFalse(dirty["ok"])` | :344, :357 :: test_git_refusal_creates_zero_proposals — `== {"ok": False, "reason": "file đích có thay đổi chưa commit"}` | D3.2 `GIT_DIRTY` (`design.md:362`) | chặt hơn |
| 17 | test_propose_change.py:174 | như #16 | `assertIn("chưa commit", reason)` | như #16 | như #16 | chặt hơn |
| 18 | test_propose_change.py:177 | như #16 | `assertFalse(big["ok"])` | :317 `"file lớn hơn 1 MiB"` (dict đúng) + biên :328 test_file_of_exactly_one_mib_is_read; :270 `replace` 20001 ký tự → `tham số không hợp lệ: replace` | D3.1 `TOO_LARGE`, `PROPOSAL_TEXT_MAX_CHARS` (`design.md:207-208,260`) | chặt hơn (thêm biên) |
| 19 | test_propose_change.py:178 | như #16 | `assertIn("vượt", reason)` | như #18 | như #18 | chặt hơn |
| 20 | test_propose_change.py:192 | test_new_file_proposal_and_its_refusals | `assertFalse(doc.content_before)` | :407 :: test_new_file_proposal_does_not_create_file — `(content_before, base_hash) == ("", "")` | D3.1 `propose_new_file` (`design.md:234`) | chặt hơn |
| 21 | test_propose_change.py:202 | như #20 | `assertFalse(refused["ok"], path)` | :432 :: test_new_file_errors_exists_and_no_parent — `== {"ok": False, "reason": …}` 7 ca | D3.1 `EXISTS`/`NO_PARENT` (`design.md:259`) | chặt hơn |
| 22 | test_propose_change.py:203 | như #20 | `assertIn(phrase, reason)` (vd. "thư mục chứa file chưa tồn tại") | như #21 (`"thư mục cha chưa có"`) | như #21 | chặt hơn |
| 23 | test_propose_change.py:204 | như #20 | `len(proposals()) == 1` | :433 `assert_nothing_created()` (0 đề xuất, 0 comment, file nguyên) — ca hợp lệ tách sang #20 | tách test | giữ độ chặt |
| 24 | test_propose_change.py:241 | test_not_granted_without_switch_instructor_or_l3 | `change(edits, change_enabled=False) == NOT_GRANTED` | :610 cùng test — `change(*edit, change_enabled=False) == NOT_GRANTED` | đổi chữ ký gọi (D3.1) | giữ nguyên |
| 25 | test_propose_change.py:242 | như #24 | `… instructor=None …` | :611 | như #24 | giữ nguyên |
| 26 | test_propose_change.py:243 | như #24 | `… effective_level="L2" …` | :612 | như #24 | giữ nguyên |
| 27 | test_registry.py:557 | test_every_real_handler_runs_without_committing | `results.pop(name)["reason"] == APP_NOT_ALLOWED` (2 tool file) | test_registry.py:607 cùng test — 2 tool file nay phải `ok=True` (`allowed_apps=(SANDBOX_APP,)` :590, repo tạm GitSandbox); câu từ chối vẫn được giữ ở test_change_guard.py:118, test_propose_change.py:307, :427 | Amd-2 AC-2 (tool chạy thật ở L3); D3.1 | chặt hơn (handler chạy tới cuối) |
| 28 | test_site_api.py:115 | test_creates_user_with_an_allowed_role | `result == {"ok":True,"doctype":"User","name":NEW_USER}` | test_site_api.py:165-168 cùng test — 4 khóa `ok, doctype, name, value_before=None` + :169 tập khóa `value_after` | Amd-2 AC-35 (giá trị trước/sau) | có căn cứ; nới nhẹ: không so cả dict, giá trị `value_after` không ghim (xem O-1) |
| 29 | test_site_api.py:239 | test_update_changes_only_the_given_fields | `== {"ok":True,"doctype":"Note","name":…}` | :580-589 cùng test — dict đúng có `value_before {"content":"cũ"}`, `value_after {"content":"mới"}` | Amd-2 AC-35 | chặt hơn |
| 30 | test_site_api.py:379 | test_assigns_any_role_and_edits_protected_accounts | `created == {"ok":True,"doctype":"User","name":NEW_USER}` | :778-781 — 4 khóa như #28 + :782 vai trò đúng | Amd-2 AC-35 | như #28 (O-1) |
| 31 | test_site_api.py:436 | test_delete_removes_the_record_through_permissions | `== {"ok":True,"doctype":"Note","name":…}` | :845+ cùng test — dict đúng có `value_before` đủ trường bản ghi | Amd-2 AC-35 | chặt hơn |
| 32 | test_site_api.py:467 | test_submit_and_cancel_call_the_document | `== {"ok":True,…}` (submit/cancel) | :954-965 cùng test — dict đúng `value_before/after {"docstatus":…}` + docstatus trong DB + `called.assert_called_once()` | Amd-2 AC-35 | chặt hơn |
| 33 | test_site_api.py:478 | test_call_method_runs_whitelisted_methods_only | `== {"ok":True,"method":…,"result":{"email":BOSS}}` | :975-988 cùng test — dict đúng thêm `value_before None`, `value_after {method, argument_keys}` | Amd-2 AC-35 | chặt hơn |
| 34 | test_source.py:113 | test_unexpected_error_is_refused_and_logged | `logger.exception.assert_called_once()` | test_source.py:115 cùng test — `get_logger.return_value.exception.assert_called_once()` | T69 (sửa F-3 của `acceptance.md`: logger lấy lúc dùng) | giữ nguyên độ chặt |
| 35 | test_erp_ai_change_proposal.py:965 | test_form_script_static_rules | `source.count("frm.reload_doc()") == 1` | test_erp_ai_change_proposal.py:974 — `body.count(...) == 1` (trong helper 3 nút) + :980-988 subTest khối tự POST | ADR-023 QĐ1 (form có thêm một lời gọi POST `decide`) | có căn cứ; phạm vi đếm hẹp lại (O-2) |
| 36 | …:966 | như #35 | `source.count("frappe.call(") == 1` | :975 `body.count == 1` + :982 `outside.count == 1` (tổng vẫn = 2, ghim đủ) | ADR-023 QĐ1 | giữ độ chặt |
| 37 | …:967 | như #35 | `source.count('type: "POST"') == 1` | :976 `body.count == 1` + `assertIn('type: "POST",', call)` ở khối ngoài | ADR-023 QĐ1 | có căn cứ (O-2) |
| 38 | test_change_decision.py:61 | (helper) `def assertRefused(self, phrase)` | helper cũ | test_change_decision.py:173 — helper mới: `assertRaises(PermissionError)`, kiểu đúng, thông điệp đúng, trạng thái + số dòng nhật ký + job không đổi | ADR-023 QĐ1 (lỗi là exception của whitelist, không còn trang web) | chặt hơn |
| 39 | test_change_decision.py:64 | helper cũ | `self.page.assert_called_once()` | như #38 | ADR-023 QĐ1 | chặt hơn |
| 40 | test_change_decision.py:65 | helper cũ | `assertIn(phrase, page.call_args…)` | như #38 (`str(exc) == message`) | ADR-023 QĐ1 | chặt hơn |
| 41 | test_change_decision.py:66 | helper cũ | `response.type != "redirect"` | như #38 (exception, không có response) | ADR-023 QĐ1 | có căn cứ |
| 42 | test_change_decision.py:79 | test_approve_link_approves_queues_the_job_and_returns_to_the_ticket | `response["type"] == "redirect"` | không có tương đương; người ở lại form: :290 test_form_script_posts_once_without_confirm_and_strips_params (`frm.reload_doc()` sau `frappe.call`, `history.replaceState` trước) | ADR-023 QĐ1 ("Người bấm thấy ngay diff và trạng thái mới trên form") | có căn cứ ADR; **spec AC-25 chưa sửa chữ** (F-R4-1) |
| 43 | test_change_decision.py:80 | như #42 | `location == "/helpdesk/tickets/<ticket>"` | như #42 | như #42 | như #42 (F-R4-1) |
| 44 | test_change_decision.py:81 | như #42 | `self.page.assert_not_called()` | :219 :: test_post_approve_sets_approved_and_one_job_survives_request_end — `result == {"ok":True,"status":"Đã duyệt"}`, `decided_by`, 0 job trước khi kết thúc request, đúng 1 job sau, `user` của job | ADR-023 QĐ1 + M1 (`ADR-023.md:60`) | chặt hơn |
| 45 | test_change_decision.py:88 | test_reject_link_rejects_without_a_job | `location == "/helpdesk/tickets/<ticket>"` | :239 :: test_post_reject_zero_jobs — kết quả dict đúng, trạng thái, 0 job | ADR-023 QĐ1 | có căn cứ ADR (F-R4-1) |
| 46 | test_change_decision.py:94 | test_wrong_or_missing_signature_changes_nothing | `assertRefused("không hợp lệ")` | :196 :: test_post_bad_signature_changed_action_or_name_writes_nothing — 6 ca, `assertRefused(..., change_decision.BAD_LINK)` | ADR-023 QĐ1 | ca phủ rộng hơn; **giá trị kỳ vọng lấy từ hằng của mã** (F-R4-2) |
| 47 | test_change_decision.py:99 | test_signature_of_another_proposal_is_refused | `assertRefused("không hợp lệ")` | như #46 (ca "name changed", "signed for the other name…") | như #46 | như #46 (F-R4-2) |
| 48 | test_change_decision.py:103 | test_unknown_action_is_refused | `assertRefused("không hợp lệ")` | như #46 (ca "unknown action") | như #46 | như #46 (F-R4-2) |
| 49 | test_change_decision.py:109 | test_user_without_role_and_administrator_are_refused_with_a_valid_link | `assertRefused("ERP AI Instructor")` | :264 :: test_refused_accounts — 6 tài khoản × 2 hành động, thông điệp đúng `ROLE_REFUSAL` (viết tay :51) / thông điệp Guest | Amd-2 AC-26; ADR-023 QĐ1 | chặt hơn |
| 50 | test_change_decision.py:116 | test_second_click_reports_the_state_and_queues_nothing_more | `self.page.assert_called_once()` | :246 :: test_replay_keeps_state_and_enqueues_nothing — `ValidationError` với câu viết tay "Đề xuất đang ở trạng thái Đã duyệt, không duyệt/từ chối được", trạng thái, dòng nhật ký, 1 job | Amd-2 AC-25 (lần mở lại); ADR-023 QĐ1 | chặt hơn |
| 51 | test_change_decision.py:117 | như #50 | `assertIn(CHANGE_STATUS_APPROVED, page…)` | như #50 | như #50 | chặt hơn |
| 52 | test_change_decision.py:122 | test_method_is_get_only_and_never_guest | `allowed_http_methods[fn] == ["GET"]` | :185 :: test_method_is_post_only_and_never_guest — `== ["POST"]`; :191 test_get_is_refused_and_changes_nothing | ADR-023 QĐ1 ("Không còn method GET đổi trạng thái"), plan.md:213 | đảo ngược có chủ ý; **spec AC-26 vẫn viết "chỉ nhận GET"** (F-R4-1) |

Hai dòng xuất hiện lại nguyên văn ở file khác: test_propose_change.py:165-166 (`assertFalse(result["ok"])`, `assertIn("erp_ai", result["reason"])`, test_erp_ai_is_refused_even_when_listed). Chỗ trùng ở test_site_api.py là test khác (gọi hàm quyết định qua `api_call_method`), không phải chỗ thay. Chỗ thay thật: test_propose_change.py:308 + :321-325 — `allowed_apps=(APP, "erp_ai")`, dict đúng `"không được sửa app erp_ai hoặc kho git của nó"`. Căn cứ D3.1; chặt hơn.

## B. Giá trị kỳ vọng bị đổi ở dòng không có chữ `assert`

| File:dòng cũ | Test | Cũ → mới | Căn cứ | Kết luận |
|---|---|---|---|---|
| test_apply_job.py:~156 | test_branch_changed_since_proposal_is_stale → test_branch_changed_after_approval_becomes_stale (:267) | "nhánh đang checkout đã đổi từ lúc đề xuất" → "…đã đổi kể từ lúc đề xuất"; thêm 4 assert (ref main/other, worktree sạch, bước) | D3.2 `GIT_BRANCH_CHANGED` (`design.md:364`) | chặt hơn |
| test_apply_job.py:~167 | test_switch_off_or_app_removed_fails_without_writing | "công tắc sửa code đã tắt" → "công tắc đang tắt" | D4.3 (`design.md:608`) | có căn cứ |
| test_apply_job.py:~174 | (nội dung sửa sau duyệt) | "nội dung đề xuất đã đổi sau khi duyệt" → "…đã bị sửa sau khi duyệt" | D4.3 (`design.md:177,609`) | có căn cứ |
| test_apply_job.py:~215 | test_crash_ends_as_failed_with_the_exception_class_only (:362) | `"job lỗi: RuntimeError"` → `"RuntimeError"` | D4.3 bước 5 (`design.md:633`: `reason=type(exc).__name__`) | có căn cứ, vẫn so đúng |
| test_apply_job.py:2189-2193 | test_failed_timed_out_and_missing_command_end_as_failed (bị xóa) | "lệnh thoát với mã 2" / "lệnh chạy quá giờ…" / "không tìm thấy lệnh bench" → :2470 test_nonzero_exit_and_missing_bench_fail ("lệnh trả mã 2", "không tìm thấy bench trên máy chủ", thêm exit_code/duration/output/dòng nhật ký) + :2566 test_command_timeout_fails_with_reason ("quá thời gian", 3 ca) | D4.3 bước 4 (`design.md:627-632`) | chặt hơn |
| test_registry.py:~60 | (danh sách tham số hàm cấp) | `["effective_level","has_instructor","change_enabled"]` → thêm đầu vào thứ tư | ADR-023 (thêm đầu vào cho hàm cấp của ADR-011 QĐ2), Amd-2 AC-2 | có căn cứ |
| test_site_api.py:~160 | (DocType bị đóng) | bỏ `"Role Permission"`, thêm `"Employee"`, `"GL Entry"`; thêm `assertTrue(frappe.db.exists("DocType", …))` và `assertIn("không được phép", …)` | `Role Permission` không phải DocType của Frappe (`apps/frappe/frappe/core/doctype/` chỉ có `custom_docperm`, `docperm`, `role_permission_for_page_and_report`): ca cũ đi qua vì DocType không tồn tại | chặt hơn |
| test_agent_runner.py:1241-1337 | TestRunnerSiteAdminTools (3 test) | mục nhật ký thêm `value_before`, `value_after`, `instructor`; `latest_instructor` từ `"Administrator"` → `INSTRUCTOR` thật | Amd-2 AC-34, AC-35; Administrator thuộc `NEVER_AUTHORITY` | chặt hơn |
| test_change_link.py:~18 | (hằng `PREFIX`) | `/api/method/erp_ai.change_decision.decide?` → `/app/erp-ai-change-proposal/{NAME}?`; thêm test_decision_path_opens_desk_form_not_api_method | ADR-023 QĐ1 | có căn cứ |

## C. Hàm test bị xóa hoặc đổi tên (ngoài `test_architecture.py`)

17 tên `def test_` bị xóa không còn ở đâu (trừ một trùng tên ở file khác). Mỗi tên đã gắn với chỗ thay ở bảng A/B: test_apply_job 4 (`…other_dirty_files…` → `test_other_dirty_files_do_not_block_apply` :214, `…branch_changed…` → :267, `…failed_timed_out…` → :2470 + :2566, `test_state_is_committed_before_the_command_runs` → `test_applying_state_committed_before_subprocess` :2643, thân giữ nguyên); test_propose_change 5 (#4–#23); test_change_decision 8 (#38–#52). Không test nào biến mất mà không có chỗ thay.

## Phát hiện

| mức | STD | file:dòng | mô tả | sửa |
|---|---|---|---|---|
| minor | STD-TEST-5 | `docs/team/features/FEAT-004/spec.md:366-367` ↔ `erp_ai/test_change_decision.py:185,191` và #42–#45, #52 | **F-R4-1.** Test bỏ đường GET + chuyển về trang phiếu, thay bằng form + POST, theo ADR-023 QĐ1. AC-15 [changed] của spec cho phép sửa test cũ khi có ADR, nên thay đổi có căn cứ. Nhưng chữ của AC-25 ("trình duyệt được chuyển về trang phiếu", "trang báo trạng thái hiện tại") và AC-26 ("Đường liên kết chỉ nhận GET") chưa được sửa, và ADR-023 vẫn ở trạng thái *proposed*. Test hiện đúng với ADR nhưng trái chữ của spec | analyst `analyze --amend` sửa chữ AC-25/AC-26 theo ADR-023 QĐ1; architect chuyển ADR-023 sang accepted (hoặc ghi phán quyết). Không phải sửa mã |
| minor | STD-TEST-2 | `erp_ai/test_change_decision.py:213` | **F-R4-2.** Ca chữ ký sai/đổi hành động/đổi tên/hành động lạ so thông điệp với `change_decision.BAD_LINK`, tức hằng của chính mã đang kiểm. Bản cũ ghim cụm viết tay "không hợp lệ" mà AC-26 đòi ("trang báo 'không hợp lệ'"). Nếu hằng bị đổi thành câu khác thì test vẫn xanh. Giá trị hiện tại (`change_decision.py:13` = "Đường dẫn duyệt không hợp lệ hoặc đã bị sửa.") vẫn đúng AC | dev: viết tay câu kỳ vọng trong test (như `ROLE_REFUSAL` ở :51), hoặc thêm `assertIn("không hợp lệ", BAD_LINK)`. Owner: dev, 1 task nhỏ |

Ghi nhận, không thành phát hiện (không trái STD):
- O-1: test_site_api.py:165-169, :778-781 so 4 khóa và tập khóa của `value_after` thay cho so cả dict. Giá trị `value_after` của User không được ghim ở hai test này. Các công cụ ghi còn lại (#29, #31–#33) so cả dict.
- O-2: test_erp_ai_change_proposal.py:974-976 chuyển phép đếm từ cả file sang thân helper 3 nút. `frappe.call(` vẫn được ghim đủ (1 + 1). Tổng `frm.reload_doc()` và `type: "POST"` của cả file không còn được ghim, nhưng khối tự POST có assert riêng (:980-988).

## Kết quả

Đã đếm 52 dòng assert bị xóa không trở lại nguyên văn (47 dòng mẫu `self.assert…` của R-4, cộng 5 dòng khác) và 2 dòng đã chuyển sang test khác. Cả 52 + 2 đều có chỗ thay và có căn cứ: Amd-2 AC-2/22/24/25/26/35, ADR-023 QĐ1, design §3.1/§3.2/§4.3/§4.4, phụ lục 4, T69. 0 dòng không có căn cứ. 0 skip marker mới. 0 assert bị nới mà không có căn cứ. Còn 2 phát hiện minor: F-R4-1 (chữ spec trễ hơn ADR-023) và F-R4-2 (giá trị kỳ vọng lấy từ hằng của mã).

R-4 open with 2 findings
