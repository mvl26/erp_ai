Feature: CHG-001
Stage: verify
Author-agent: qa
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Nghiệm thu CHG-001 (theo tham chiếu, KHÔNG chạy lại gì)

Commit đọc: `7a134ae` (`develop`, cây chính `/home/miyano/frappe-bench/apps/erp_ai`). qa không chạy test, không chạy lệnh site nào (khóa site đang dùng cho nghiệm thu FEAT-005, lệnh team-leader). Mọi kết quả test dưới đây là kết quả đã dán trong `docs/team/features/FEAT-004/acceptance*.md`; qa chỉ đọc file và chạy `git` chỉ-đọc.

**Phán quyết này dựa trên:** (1) nghiệm thu FEAT-004 (`acceptance.md` trên `ba89ab3`/`da00518`, `acceptance-part-3.md` trên `abd2fa2`, `acceptance-r4.md` trên `da00518`); (2) quyết định của người ngày 2026-11-14 "Chấp nhận với bằng chứng hiện có" (`FEAT-004/acceptance.md:209-215`). Không có gì được chạy lại cho CHG-001.

Đường dẫn trong bảng: `A` = `docs/team/features/FEAT-004/acceptance.md`, `P3` = `docs/team/features/FEAT-004/acceptance-part-3.md`, `R4` = `docs/team/features/FEAT-004/acceptance-r4.md`, `S` = `docs/team/features/FEAT-004/spec.md`.

## Bằng chứng còn áp dụng cho mã trên `develop` không

Lệnh chỉ-đọc, chạy lúc nghiệm thu này:

- `git merge-base --is-ancestor <c> 7a134ae` cho `ba89ab3`, `da00518`, `b8d3e74`, `4469287`: cả 4 → `yes`.
- `git diff --stat ba89ab3 7a134ae -- . ':!docs'` → `CHANGELOG.md | 6`, `README.md | 24`, `erp_ai/agent/tools/source.py | 30`, `erp_ai/agent/tools/test_source.py | 55`, `erp_ai/test_change_decision.py | 3` — `5 files changed, 102 insertions(+), 16 deletions(-)`.
- Kết luận: mã của các module phủ AC-24..AC-35 (`change_link`, `propose_change`, `change_decision`, `apply_job`, `result_comment`, `classification`/`prompts`, `site_api`, `registry`, `policy`, `runner`, `agent_write_guard`) trên `develop` @ `7a134ae` trùng `ba89ab3`. Hai chỗ khác: `source.py` (T69, logger tạo lúc dùng thay vì lúc import; không thuộc AC-24..35) và `test_change_decision.py` (T70, 1 hằng viết tay `BAD_LINK_REFUSAL` thay `change_decision.BAD_LINK`, chặt hơn) — lần chạy sau T70 là của tech-lead (`A:204`, `Ran 10 tests in 25.731s` / `OK`), không phải của qa.
- `git grep` trên `7a134ae`: các test phủ được nêu tên còn tồn tại, ví dụ `test_change_decision.py:374 test_link_approval_still_rechecked_at_apply`, `test_site_api.py:1258/1272/1296` (lọc dòng con, lọc trước cắt sau), `test_agent_runner.py:1606 test_six_large_deletes_keep_one_bounded_log_row`, `tests/test_architecture.py:3761` (cấm method GET gọi approve/reject/undo, AC-26 Amd-3).

## Tiêu chí (FEAT-004 AC-24..AC-35, bản có hiệu lực sau Amendment 3)

| tiêu chí | dòng nghiệm thu có lệnh + đầu ra (file:dòng) | đầu ra đã dán (nguồn dòng thô) | test phủ | kết quả |
|---|---|---|---|---|
| AC-24 | `A:55` (ba89ab3); `P3:33` (abd2fa2) | `A:23` `test_propose_change` `Ran 12` `OK` (chạy lại 12 ca 1213); `P3:12` `Ran 6 tests in 0.004s` / `OK`; `P3:14` `Ran 32 tests in 78.762s` / `OK`; change_link 6/0/0 junit cả app (`A:21`) | `test_change_link::test_signature_fits_only_its_own_proposal_and_action`, `test_propose_change::test_comment_of_each_tool_has_three_links_and_decisions_open_the_form` | đạt |
| AC-25 | `A:56`; `P3:34` | `A:22` `Ran 10` / `FAILED (errors=9)` (9 × 1213) rồi `Ran 9 tests in 21.687s` / `OK`; `P3:13` `Ran 10 tests in 19.965s` / `OK` | `test_change_decision::test_post_approve_sets_approved_and_one_job_survives_request_end`, `::test_form_script_posts_once_without_confirm_and_strips_params` | đạt phần tự động; **phần trình duyệt thật: NOT VERIFIABLE** — `S:484` đòi qa mở liên kết bằng trình duyệt thật và dán mô tả/ảnh ("chưa làm"); `P3:34`, `A:120`, O-11 |
| AC-26 | `A:57`; `P3:35` | như AC-25 (`A:22`, `P3:13`); sau T70: `A:204` `Ran 10 tests in 25.731s` / `OK` (tech-lead); phần kiến trúc: `A:46` test_architecture 177/0/0 | `test_change_decision::test_get_is_refused_and_changes_nothing`, `::test_refused_accounts`, `::test_post_bad_signature_changed_action_or_name_writes_nothing` | đạt |
| AC-27 | `A:58`; `P3:36` | `A:22` (như AC-25); `A:18` `test_apply_job` `Ran 117 tests in 178.351s` / `OK`; `P3:61` `test_rechecks_fail_without_writing` xanh ở lần chạy lại | `test_change_decision::test_link_approval_still_rechecked_at_apply` (5 subTest), `test_apply_job::test_rechecks_fail_without_writing` | đạt |
| AC-28 | `A:59`; `P3:37` | `A:23` `test_result_comment` `Ran 3` `OK`; `A:18` `Ran 117 tests in 178.351s` / `OK`; `P3:15` `Ran 6 tests in 10.343s` / `OK` | `test_apply_job::test_one_result_comment_per_outcome`, `::test_result_comment_has_no_remote_url_or_fake_token`, `test_result_comment::test_reason_with_url_email_or_token_is_masked` | đạt phần tự động; **dòng `Info` trên trang phiếu Helpdesk thật: NOT VERIFIABLE** (chỉ có đọc mã `P3:63-68`; rủi ro A-D1 của `CHG-001/design.md` giao qa kiểm lúc verify); O-12 |
| AC-29 | `A:60`; `P3:38` | `P3:20` `Ran 39 tests in 0.015s` / `OK`; 39/0/0 junit cả app (`A:21`) | `test_classification::test_act_now_block_only_with_action_tools` | đạt phần prompt; phép đo "hỏi lại 0 lần" với model thật: theo spec là việc sau G4 (`S:373`), không phải tiêu chí build; O-13 |
| AC-30 | `A:61`; `P3:39` | 67/0/0 junit cả app trên ba89ab3 (`A:21`, `A:61`; không có dòng `Ran` riêng của module trên ba89ab3); `P3:16` `Ran 60 tests in 53.437s` / `OK` trên abd2fa2 (trước T62) | `test_site_api::test_creates_user_with_an_allowed_role`, `::test_account_without_permission_is_refused_and_nothing_is_written` | đạt |
| AC-31 | `A:62`; `P3:40` | như AC-30 | `test_site_api::test_refuses_each_forbidden_role`, `::test_refuses_protected_users` | đạt |
| AC-32 | `A:63`; `P3:41` | `P3:17` `Ran 41 tests in 2.354s` / `OK`; `P3:21` `Ran 37 tests in 11.205s` / `OK`; site_api như AC-30 | `test_registry::test_unrestricted_enabled_defaults_to_zero_and_only_system_manager_can_set`, `test_site_api::test_assigns_any_role_and_edits_protected_accounts` | đạt |
| AC-33 | `A:64`; `P3:42` | `A:20` `test_agent_write_guard` `Ran 5 tests in 1.226s` / `OK` (đóng ca BLOCKED ở `P3:59`); site_api như AC-30 | `test_site_api::test_own_configuration_log_and_secrets_stay_closed`, `::test_decision_method_refused_even_with_valid_signed_link`, `test_agent_write_guard::test_every_guarded_hook_refuses_the_agent` | đạt theo chữ Amd-3 ("chặn ở mức cố gắng", `S:486`); 6 dạng còn lọt ghi ở spec |
| AC-34 | `A:65`; `P3:43` | `A:19` `test_agent_runner` `Ran 85 tests in 36.358s` / `OK` (sau T64); trên abd2fa2 `P3:22` `Ran 78` / `FAILED (failures=3)` (L1, ngoài phần này) và F-1 major `P3:76` | `test_agent_runner::test_unrestricted_actions_are_logged`, `::test_six_large_deletes_keep_one_bounded_log_row`, `::test_one_byte_over_the_bound_replaces_the_largest_values_by_the_marker` | đạt theo chữ Amd-3 (`S:487`: có trần, ca cực đoan bỏ mục cuối) |
| AC-35 | `A:66`; `P3:44` | site_api 67/0/0 (`A:21`, `A:66`); F-2 `P3:77` sửa ở T62 | `test_site_api::test_before_after_never_carry_secret_fields`, `::test_deleted_values_scrub_child_rows`, `::test_child_row_held_as_document_is_scrubbed` | đạt theo chữ Amd-3 (`S:488`: bản tóm tắt; bản đầy đủ thuộc FEAT-005 AC-13) |

Tiêu chí không có bằng chứng: **không có**. Cả 12 tiêu chí có một dòng nghiệm thu của qa FEAT-004 mang lệnh và đầu ra. Hai tiêu chí còn một phần NOT VERIFIABLE: AC-25 (trình duyệt thật), AC-28 (dòng `Info` trên trang phiếu thật).

Giới hạn của bằng chứng: lần cả app (`A:21`, `A:148`) chưa lần nào ra `OK`; số đếm 67/0/0, 39/0/0, 41/0/0, 37/0/0, 6/0/0 lấy từ junit của lần cả app `FAILED (failures=1, errors=128)` trên `ba89ab3`, không có dòng `Ran` riêng của module trên commit đó.

## Checklist nghiệm thu (6), theo tham chiếu

| mục | bằng chứng | kết quả |
|---|---|---|
| 1. Mỗi tiêu chí: lệnh + đầu ra | bảng trên (12 dòng, của qa FEAT-004) | đạt theo tham chiếu; không chạy lại |
| 2. `cmd.test`, `cmd.lint`, `cmd.typecheck` | lint 12 `Passed` 0 `Failed` (`A:100`, `A:177`); `cmd.test` tốt nhất `Ran 1499 tests in 802.131s` / `FAILED (failures=2, errors=12)` (`A:148`, `A:213`); typecheck: không có slot | KHÔNG ĐẠT (`cmd.test` chưa `OK`); người miễn cho FEAT-004 (`A:211-214`) |
| 3. Không skip marker | `A:102` → `0`; `R4:12` → không dòng; đoạn sau bằng chứng: `git diff ba89ab3 7a134ae -- '*.py' \| grep -nE '^\+.*(@unittest\.skip\|skipIf\|skipUnless\|expectedFailure\|\.skipTest\(\|pytest\.mark\.(skip\|xfail))'` → rỗng, `grep exit 1`; dòng `-…assert` trong đoạn đó: 1 (T70, đổi kỳ vọng sang câu viết tay, chặt hơn) | đạt |
| 4. Migration up → down → up | qa chưa chạy (`A:105`, `A:171`, O-9 `A:230`); chỉ có bằng chứng của tech-lead/dev ở T34 | KHÔNG ĐẠT; người nhận rủi ro cho FEAT-004 (`A:215`) |
| 5. DoD phần build | `CHG-001/tasks.md` soi T53–T68 16/16 `[x]`; `team.py`: built 16/16 (journal); README, CHANGELOG đã có trên `develop` (diff trên); As-Built FEAT-004 đã viết | đạt; As-Built/README/CHANGELOG: owner writer, sau G4 |
| 6. Không đụng `protected_paths` | `A:104` → 0 file; đoạn sau bằng chứng: `git diff --name-only ba89ab3 7a134ae \| grep -E '(^\|/)\.env\|\.pem$\|\.key$\|license\.txt'` → rỗng, `exit 1` | đạt |

## Rủi ro còn lại (từ nghiệm thu FEAT-004, chạm AC-24..AC-35)

- O-11 (AC-25): chưa mở liên kết Duyệt/Từ chối bằng trình duyệt thật (`A:232`, `S:484`).
- O-23 (AC-25): chưa kiểm ba người duyệt mở được Desk (`A:236`).
- O-12 (AC-28): chưa xem dòng `Info` trên trang phiếu Helpdesk thật; theo mã hiện là dòng hoạt động mang tên người duyệt (`P3:68`).
- O-13 (AC-29): đo "hỏi lại 0 lần" với model thật, sau G4.
- O-18 (AC-25, AC-26, AC-33): ADR-023 còn *proposed*.
- R-1 / O-14 / O-19 (AC-34, AC-35): mục vượt 60000 byte chỉ còn `[đã cắt]`; ca cực đoan bỏ mục cuối; chưa thử end-to-end một lượt runner > 64 KB (`P3:81`).
- O-20 (AC-35): người xác nhận bản tóm tắt đủ dùng hoặc chờ FEAT-005 AC-13 (A-27) trước khi deploy.
- `R4:102` O-1 (AC-30, AC-35): hai test của User chỉ so tập khóa của `value_after`, không ghim giá trị.
- R-2 / O-15 (AC-33): chặn đọc khóa qua `frappe.client.get_list` dựa vào Frappe @ `2e9ecdc` (`P3:78`); 6 dạng còn lọt ở `S:486`.
- O-21, O-22 (AC-32, AC-33): chữ "agent không có System Manager" trái quyết định giữ; chưa có bằng chứng agent trên `miyano` đã gỡ `ERP AI Instructor` — điều kiện để "bot không tự duyệt" của AC-33 đứng được trên site.
- R-3 / O-9 (AC-32: ô `unrestricted_enabled` mới trên ERP AI Setting): migration up/down/up chưa do qa kiểm.
- R-5 / O-16 (AC-11, liên quan AC-32): thiếu kịch bản câu chèn khi ô Toàn quyền bật.
- R-6 / O-17: không có lần cả app `OK`; O-1..O-8 (8 test `test_runner_routing`/`test_runner_status` còn 1213; O-8 chưa phân loại) không thuộc AC-24..35 nhưng nằm trong cùng lần cả app.
- O-24: cột "Mã nhận về" của N-7 là ảnh chụp lịch sử.

## Phán quyết

Ý kiến riêng của qa, đọc từ bằng chứng trên: cả 12 tiêu chí đều có bằng chứng tự động xanh của qa FEAT-004 trên mã trùng với `develop` @ `7a134ae`; không tiêu chí nào thiếu bằng chứng, không tiêu chí nào đỏ vì mã. Nhưng theo luật nghiệm thu, qa không ghi `accepted` khi còn: (1) phần NOT VERIFIABLE của AC-25 (trình duyệt thật) và AC-28 (dòng `Info` trên trang phiếu thật); (2) checklist mục 2 (`cmd.test` chưa lần nào `OK`) và mục 4 (migration up/down/up chưa do qa chạy). Cùng bằng chứng này, qa FEAT-004 cũng giữ `rework` (`A:188-194`).

Không có task dev nào phải làm lại. Việc cần làm và chủ:

- `cmd.test` cả app ra `OK`: `flock -w 1800 .team/miyano-site.lock bench --site miyano run-tests --app erp_ai` khi site độc quyền — team-leader giữ site, qa chạy.
- Migration up → down → up (`r3_updown.sh`, `A:171`) — qa, khi site rảnh.
- AC-25: mở liên kết Duyệt/Từ chối trên `miyano` bằng trình duyệt thật; AC-28: chụp dòng `Info` trên trang phiếu — người (gửi ảnh chụp/mô tả), qua team-leader.

Phán quyết này dựa hoàn toàn vào nghiệm thu FEAT-004 và quyết định của người ngày 2026-11-14; không có gì được chạy lại. Quyết định đó ("Chấp nhận với bằng chứng hiện có") đã miễn mục 2 và mục 4 cho FEAT-004, gồm cả AC-24..AC-35; nếu người mở rộng quyết định đó cho CHG-001 thì đó là chấp nhận của người, không phải nghiệm thu sạch của qa.

Verdict: rework
