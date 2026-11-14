Feature: FEAT-004 (kèm CHG-001, task T53–T70)
Stage: asbuilt
Author-agent: writer
Date: 2026-11-14
Approved-by:
<!-- Cổng: G4 tắt. Người chấp nhận bằng lời ngày 2026-11-14 ("Chấp nhận với bằng chứng hiện có", acceptance.md mục "Quyết định của người"); dòng Approved-by của acceptance.md do người điền. -->

<!-- G5: người điền `Approved-by-prod: <tên> <YYYY-MM-DD>` lên đầu file trước khi lên prod. -->
# As-Built FEAT-004 — bot sửa code, chạy lệnh bench, ghi bản ghi trực tiếp; người duyệt bằng một lần bấm

Mã: `team/FEAT-004` @ `b8d3e74` (worktree `.claude/worktrees/feat-004`), `diff.patch` = `f039112...team/FEAT-004`, 205 file, trong đó 59 file dưới `erp_ai/`. Nguồn: `spec.md` (Amendment 1–3), `design.md` + phụ lục 2–4, `docs/team/features/CHG-001/{spec,arch-impact,design}.md`, ADR-011/012/013/022/023, `acceptance.md`, `acceptance-r4.md`, `tasks.md`, `docs/team/debt.md`.

## 1. Trạng thái nghiệm thu, nói thẳng

- Người chấp nhận FEAT-004 ngày 2026-11-14 với bằng chứng đang có ("Chấp nhận với bằng chứng hiện có"; bỏ điều kiện một lần chạy cả app sạch). `acceptance.md` kết thúc bằng `241:Verdict: accepted` (grep `^Verdict` → một dòng) và `Approved-by:` vẫn trống. Chính `acceptance.md` ghi: đây là chấp nhận theo quyết định của người, **không phải nghiệm thu sạch của qa**; phán quyết riêng của qa vẫn là `rework`, DoD "`cmd.test` xanh" và checklist mục 4, 6 được người miễn, không được qa đánh dấu đạt; 24 mục mở (O-1..O-24).
- **Chưa có lần `cmd.test` cả app nào ra `OK`.** Lần tốt nhất (qa, một lần giữ khóa site, 20:19–20:32, trên `da00518`): `Ran 1499 tests in 802.131s` / `FAILED (failures=2, errors=12)`. Nguyên nhân là deadlock `QueryDeadlockError 1213` do nhiều phiên cùng chạy test trên site `miyano` dùng chung. 14 test đỏ chạy lại theo tên: 6 xanh, 8 vẫn 1213 (trong đó `test_runner_status::test_done_last_when_answered` đỏ một failure `0 != 1` ở lần cả app, lần chạy lại chết 1213 trước khi tới assert, nên chưa phân loại được; không có bằng chứng đó là lỗi thật). Lần trước (`ba89ab3`): `Ran 1496 tests in 1079.598s` / `FAILED (failures=1, errors=128)`.
- Chưa có lần chạy riêng `test_gateway::test_api_key_never_leaks` xanh do qa (F-3): lần chạy riêng chết 1213 trong `setUp`. Bằng chứng xanh duy nhất là của dev/reviewer (`Ran 65 tests` OK, review-69).
- Chưa làm: migrate lên/xuống/lên do qa (R-3). Qa chạy `cmd.migrate` chiều lên (20:18, exit 0); bằng chứng xuống/lên là của tech-lead/dev ở T34 và chiều "gỡ mã" không chạy vì sẽ xóa DocType `ERP AI Change Proposal` (acceptance.md O-9). STD-OPS-2 chưa đạt; người nhận rủi ro.
- Đạt trên `ba89ab3` theo qa: 46/46 tiêu chí (35 AC + 11 NFR) từng module chạy xanh, `cmd.lint` 12 hook `Passed`, 0 skip marker mới, 0 file trùng `protected_paths`, NFR-9 (HEAD và `status` 4 repo lõi trước = sau `cmd.test`, `diff` rỗng).
- 52 dòng assert bị xóa không trở lại nguyên văn (R-4) đã được đối chiếu ở `acceptance-r4.md`: đều có chỗ thay và căn cứ, 0 assert bị nới không căn cứ.
- Dấu vết: commit `789d524` có dòng `Co-Authored-By` (STD-GIT-8); journal ghi "không amend". Còn 21 `Comment` mồ côi trên HD Ticket vì `DELETE` bị MariaDB từ chối (`ERROR 1175`), 0 dòng bị xóa (`acceptance.md`, lượt `da00518`).

## 2. Bot làm được gì, với công tắc nào (hiện trạng của mã)

Hai ô trên `ERP AI Setting`, mặc định tắt, chỉ System Manager đặt (`erp_ai_setting.json:36` `code_change_enabled`, `:64` `unrestricted_enabled`). Bảng cấp tool: `erp_ai/agent/tools/registry.py:55-79`.

| Trạng thái | Bot được cấp | Điều kiện |
|---|---|---|
| Cả hai ô tắt | Như bản trước: danh sách tool và prompt trùng bản nền (AC-1) | — |
| `code_change_enabled` bật | 3 tool đề xuất (sửa file, tạo file, chạy lệnh `bench`) và 4 công cụ bản ghi (`api_list_records`, `api_get_record`, `api_create_record`, `api_update_record`) | mức hiệu lực `L3` và có người ra lệnh (`registry.py:61-63`, `:69`) |
| `unrestricted_enabled` bật | 4 công cụ bản ghi + `api_delete_record`, `api_submit_record`, `api_call_method` | mức khác `L0` (tức `L1`, `L2`, `L3`, kể cả khi ngân sách vượt và mức bị hạ về `L1`) và có người ra lệnh; **không cần ô code** (`registry.py:48-50`, `:73-78`) |

- **Ghi bản ghi trực tiếp, không qua duyệt:** ngay khi ô code bật ở `L3`, bot (chạy dưới tài khoản agent, theo phân quyền Frappe của tài khoản đó) tạo và sửa bản ghi mà không ai bấm gì: tạo User, gán vai trò nghiệp vụ, sửa cấu hình, bản ghi nháp. Site `miyano` đã ở đúng trạng thái này (ô code bật, `L3`) từ 2026-11-14 00:26 (spec Amd-2 N-1 "Why now"). Ô "Cho phép sửa code và lệnh bench" vì vậy có hai nghĩa (A-24).
- **Chế độ thường vẫn bị từ chối** (AC-31, `test_site_api`): gán `System Manager`, `Administrator`, `ERP AI Instructor`, `ERP AI Agent`, `Guest`, `All` (kể cả qua Role Profile); sửa `Administrator`, `Guest`, tài khoản agent; ghi Role Permission, Custom DocPerm; ghi DocType trong danh sách đóng; xóa, submit, hủy (không có công cụ); Server Script và Webhook luôn lưu ở trạng thái tắt.
- **"Toàn quyền (khẩn cấp)"** (AC-32): thêm xóa, submit/hủy, gọi hàm whitelist, và các giới hạn trên không còn: gán được `System Manager` cho bất kỳ ai, sửa được phân quyền, bật được Server Script. Tắt bằng tay, không hẹn giờ, **không có cảnh báo khi đang bật** (A-23). Xóa và submit không hoàn tác.
- **Chỉ chặn ở mức cố gắng (best-effort):** đọc mật khẩu và khóa API của người dùng qua `api_call_method` (người chọn "Giữ gọi hàm bất kỳ, chặn ở mức cố gắng", không allowlist); chặn ghi vào DocType của app bằng so chuỗi chỉ là từ chối sớm, ranh giới thật là kiểm danh tính tài khoản agent ở controller (ADR-023 QĐ 5); cam kết "bot không tự đổi công tắc, khóa, nhật ký, đề xuất của mình" ở Toàn quyền là cố gắng với hàm ghi DB không qua controller (ADR-023 QĐ 6 b). Sáu dạng còn lọt: mục 5.
- **Luôn đóng ở mọi chế độ:** ghi hay đọc `ERP AI Setting`, `ERP AI Credential`, `ERP AI Log`, `ERP AI Change Proposal`; gọi hàm của app `erp_ai`, kể cả hàm quyết định (`test_decision_method_refused_even_with_valid_signed_link`); bot không bao giờ tự duyệt đề xuất của mình; chữ "ok" trong phiếu không phải duyệt (AC-5, AC-29).
- **Code và lệnh `bench` vẫn cần người bấm.** Lệnh `bench` trong danh sách cố định: `migrate`, `clear-cache`, `clear-website-cache`, `list-apps`, `build`, `version` (`change_guard.py:33-36`); không `restart`, không push, fetch, đổi nhánh, sửa lịch sử, không chạy hook của repo. App lõi (`frappe`, `erpnext`, `helpdesk`, `hrms`) sửa được khi System Manager thêm vào `code_change_apps`; `erp_ai` không bao giờ.
- **Tài khoản agent:** trên `miyano` đang giữ `System Manager` (người chọn giữ; ADR-023 Bối cảnh, đọc 2026-11-14) và, tới khi người gỡ, `ERP AI Instructor`. Mã từ chối tài khoản agent ở bước áp dụng và hoàn tác dù đang mang vai trò (`apply_job.py:212`, `NEVER_AUTHORITY`). Vì tài khoản có `System Manager`, danh sách cấm trong mã là lớp chặn duy nhất cho chế độ thường (ADR-023 QĐ 3).

## Differences from design

Cách đọc: mỗi hàng một mục của `design.md` (8 mục lớn, tách theo mục con) và mỗi touchpoint ở mục 7; `file:dòng` là dòng của hunk mới trên `b8d3e74`. "Lý do" chỉ lấy từ `design-addendum-N`, `review-NN` (NN = số task), `tasks.md`, `spec.md` Amendment; không có thì "không ghi". Lưu ý phương pháp: với các hàng "đúng thiết kế", writer đối chiếu tên file trong `diff.patch`, tên test trong `acceptance.md` và các hunk đã mở; không đọc từng dòng của 40581 dòng diff.

### 3.1 Theo mục thiết kế

| Mục thiết kế | Thực tế | file:dòng | Lý do |
|---|---|---|---|
| 1. Bối cảnh | đúng; phạm vi mở rộng thêm sau thiết kế: Amendment 2 (bot làm luôn, duyệt một lần bấm, công cụ bản ghi, Toàn quyền) và Amendment 3 | spec.md Amendment 2, 3 | lệnh của người (CHG-001 intake) |
| 2.1 DocType `ERP AI Change Proposal` | đúng thiết kế (9 trường git, bố cục 3.3) | erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.json:1 | — |
| 2.2 Trạng thái (9) | đúng thiết kế | erp_ai/constants.py:22-30 | — |
| 2.3 `content_digest` | đúng thiết kế | erp_ai/agent/changes/transitions.py:95 | — |
| 2.4 `ERP AI Setting` 2 trường + 1 Section | khác: thêm trường thứ ba `unrestricted_enabled` ("Toàn quyền (khẩn cấp)") và đổi nghĩa `code_change_enabled` (nay mở cả công cụ bản ghi) | erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json:36,64 | spec Amd-2 N-4, A-24 (lệnh của người, handoff CHG-001) |
| 2.5 `ERP AI Log` 1 giá trị + 3 trường | đúng thiết kế; thêm: cột `actions` của lượt có trần 60000 byte, 1024 byte mỗi giá trị, dấu `[đã cắt]` | erp_ai/agent/runner.py:93-94 | spec Amd-3 P-3 (AC-34), phát hiện F-1 của qa; đội nhận giới hạn (journal "rework T62/T64") |
| 2.6 Hằng số | đúng thiết kế; `JOB_TIMEOUT_S = 600`, `JOB_SAFETY_MARGIN_S = 60` | erp_ai/constants.py:40,42 | — |
| 3.1 Tool đề xuất (3 tool, `propose_change.py`) | đúng thiết kế; tool đăng comment có liên kết ký | erp_ai/agent/tools/propose_change.py:102 | — |
| 3.1 (mở rộng) nhóm tool | khác: thêm hai nhóm cấp `site_admin`, `site_unrestricted` ngoài nhóm `change_propose` | erp_ai/agent/tools/registry.py:44-45,66-78 | spec Amd-2 N-2 S-3, S-5, S-6; ADR-023 QĐ 4 |
| 3.2 Bộ chặn đường dẫn/lệnh | đúng thiết kế sau phụ lục 2 (pathspec chính xác, tên có `* ? [ ]` hoặc bắt đầu `:`/`-` bị từ chối) | erp_ai/agent/tools/change_guard.py:138 | design-addendum-2 QĐ-A1, QĐ-A2 |
| 3.3 Cửa vào HTTP: 3 method POST | đúng, chữ ký `name=None`; thêm method thứ tư `decide(name, action, _signature)` POST-only | erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py:115-132; erp_ai/change_decision.py:20-21 | design-addendum-3 QĐ-B6 (`name=None`); ADR-023 QĐ 1, spec Amd-3 P-2 (liên kết ký) |
| 3.3 Form `.js` (3 nút + `frappe.confirm`) | đúng; thêm xử lý liên kết ký: bỏ tham số khỏi địa chỉ rồi POST đúng một lần, không hộp xác nhận | erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.js:56,58 | spec Amd-3 P-2, AC-25 (ADR-023 QĐ 1) |
| 3.4 Hàng đợi `enqueue_change_job` | đúng thiết kế | erp_ai/agent/queue.py:1 | — |
| 3.5 Job, `transitions`, `file_writer`, `process_runner` | đúng; `bench_runner.py` đã đổi thành `process_runner.py` ngay trong design; `finish(..., before=, after=)`; lệnh `bench` hết ngân sách thì `Lỗi` "quá thời gian", 0 tiến trình | erp_ai/agent/changes/apply_job.py:84,131; erp_ai/agent/changes/process_runner.py:1 | design-addendum-2 QĐ-A3; design-addendum-3 QĐ-B4, QĐ-B5 |
| 3.5 (mở rộng) dòng git lỗi lưu vào `failure_reason` | khác so với design gốc: dòng cuối được che đường dẫn, URL, email, chuỗi dạng khóa rồi cắt 120 ký tự | erp_ai/agent/changes/apply_job.py:272,290 | design-addendum-4 QĐ-D1, QĐ-D2 (review-45 deferred) |
| 3.6 Chữ ký nội bộ bị đổi | khác: `policy.validate_change_apps(settings, apps_root)` nhận gốc `apps/` | erp_ai/agent/policy.py:138 | design-addendum-3 QĐ-B3 (cắt vòng import) |
| 3.7 Prompt `CHANGE_TOOLS_BLOCK` | đúng; thêm hai khối `SITE_ADMIN_TOOLS_BLOCK` và `ACT_NOW_BLOCK` ("làm luôn") | erp_ai/agent/prompts.py:155,173,217 | spec Amd-2 AC-29 |
| 3.8 Comment trên phiếu (có ba liên kết) | đúng; liên kết mang chữ ký sinh ở `change_link.py` | erp_ai/agent/change_link.py:21-35 | spec Amd-2 AC-24 |
| 3.9 Chữ commit, cảnh báo, danh tính | đúng thiết kế | erp_ai/agent/change_text.py:1 | — |
| 4.1 Luồng đề xuất | đúng thiết kế | erp_ai/agent/tools/propose_change.py:125 | — |
| 4.2 Duyệt/từ chối | khác: thêm đường qua liên kết ký trong comment (form mở rồi POST một lần); không có đường GET đổi trạng thái | erp_ai/change_decision.py:21 | ADR-023 QĐ 1, spec Amd-3 S-1, AC-25, AC-26 |
| 4.3 Áp dụng | khác: kiểm lại người thực hiện (không thuộc `NEVER_AUTHORITY`, còn vai trò `ERP AI Instructor`, đúng user phiên của job); không lấy được khóa chung thì `Lỗi` "đang có thay đổi khác chạy" | erp_ai/agent/changes/apply_job.py:212,215 | ADR-023 QĐ 2, spec Amd-3 AC-5 |
| 4.3 (mở rộng) sau kết cục | khác: sau mỗi áp dụng/lỗi/hết hiệu lực/hoàn tác ghi một dòng `Info` lên phiếu | erp_ai/agent/changes/result_comment.py:81,90 | CHG-001 design (AC-28, A-D1) |
| 4.4 Hoàn tác | đúng thiết kế (cộng kiểm lại người thực hiện như 4.3) | erp_ai/agent/changes/apply_job.py:84 | ADR-023 QĐ 2 |
| 4.5 Lỗi và kết quả không rõ | đúng thiết kế sau phụ lục 3 QĐ-B2 (không trả lại file khi commit có thể đã thành) | erp_ai/agent/changes/apply_job.py:131 | design-addendum-3 QĐ-B2 |
| 5. Quyền | khác: tài khoản agent bị loại khỏi thẩm quyền ở duyệt, áp dụng, hoàn tác; ghi `ERP AI Setting`, `ERP AI Credential`, `ERP AI Log` của tài khoản agent chỉ qua đường của app | erp_ai/agent/agent_write_guard.py:15-19; erp_ai/erp_ai_agent/doctype/erp_ai_credential/erp_ai_credential.py:1; erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.py:1 | ADR-023 QĐ 2, QĐ 5 (CHG-001 M2, M5; commit 02493b3, 2a71c92) |
| 6. Migration và rollback | đúng thiết kế (không patch dữ liệu, `patches.txt` không đổi); lên: `cmd.migrate` exit 0 (qa 20:18); **xuống do qa chưa kiểm** (R-3) | erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.json:1 | R-3: lượt qa cấm `migrate` |
| 7. Touchpoints | xem 3.2 | — | — |
| 8. Test plan | đúng; ma trận AC-1/AC-2 mở thành 32 tổ hợp (hai ô × 4 mức × có/không người ra lệnh); luật kiến trúc thêm cho `apply_job`, `propose_change`, `site_api`, `change_decision`, và cấm method GET gọi duyệt/từ chối/hoàn tác | erp_ai/tests/test_architecture.py:1; erp_ai/agent/tools/test_registry.py:1 | spec Amd-2 AC-1/AC-2; ADR-023 Ràng buộc (T68) |

### 3.2 Theo touchpoint (design §7) và file ngoài touchpoint

| Touchpoint | Thực tế | file:dòng | Lý do |
|---|---|---|---|
| constants.py | đúng | erp_ai/constants.py:9,22-30,50,52 | — |
| agent/policy.py | đúng, chữ ký `validate_change_apps` đổi | erp_ai/agent/policy.py:138 | design-addendum-3 QĐ-B3 |
| agent/run_log.py | đúng | erp_ai/agent/run_log.py:1 | — |
| agent/queue.py | đúng | erp_ai/agent/queue.py:1 | — |
| agent/runner.py | đúng, thêm trần cỡ `actions` và dòng nhật ký công cụ bản ghi | erp_ai/agent/runner.py:93-94 | spec Amd-3 P-3 |
| agent/prompts.py | đúng, thêm hai khối | erp_ai/agent/prompts.py:155,173,217 | spec Amd-2 |
| agent/change_text.py (mới) | đúng | erp_ai/agent/change_text.py:1 | — |
| agent/git_no_hooks/README.md (mới) | đúng | erp_ai/agent/git_no_hooks/README.md:1 | — |
| agent/tools/registry.py | đúng, thêm hai nhóm | erp_ai/agent/tools/registry.py:44-79 | ADR-023 QĐ 4 |
| agent/tools/source.py | đúng; sau T69 logger lấy lúc dùng, không còn gọi `frappe.logger` lúc import | erp_ai/agent/tools/source.py:13 | review-69 (F-3 của qa) |
| agent/tools/change_guard.py (mới) | đúng | erp_ai/agent/tools/change_guard.py:31-36 | — |
| agent/tools/propose_change.py (mới) | đúng | erp_ai/agent/tools/propose_change.py:102 | — |
| agent/changes/__init__.py (mới) | đúng | erp_ai/agent/changes/__init__.py:1 | — |
| agent/changes/transitions.py (mới) | đúng | erp_ai/agent/changes/transitions.py:74 | — |
| agent/changes/apply_job.py (mới) | đúng, thêm kiểm lại người thực hiện, gọi `post_result` | erp_ai/agent/changes/apply_job.py:84 | ADR-023 QĐ 2; CHG-001 design |
| agent/changes/file_writer.py (mới) | đúng | erp_ai/agent/changes/file_writer.py:1 | — |
| agent/changes/process_runner.py (mới) | đúng (tên đã đổi trong design) | erp_ai/agent/changes/process_runner.py:1 | design D-12 |
| doctype/erp_ai_change_proposal/{__init__,.json,.py,.js} (mới) | đúng, `.py` và `.js` thêm đường liên kết | erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py:115 | ADR-023 QĐ 1 |
| doctype/erp_ai_setting/erp_ai_setting.json, .py | đúng, thêm `unrestricted_enabled` | erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json:64 | spec Amd-2 N-4 |
| doctype/erp_ai_log/erp_ai_log.json | đúng | erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json:1 | — |
| test_utils.py | đúng (`GitSandbox`) | erp_ai/test_utils.py:1 | — |
| 21 file test của design §7 (test_change_guard, test_propose_change, test_source, test_change_text, test_registry, test_run_status, test_transitions, test_apply_job, test_file_writer, test_process_runner, test_erp_ai_change_proposal, test_policy, test_run_log, test_queue, test_agent_runner, test_classification, test_erp_ai_setting, test_tasks, test_doctype_descriptions, test_architecture, test_install) | đúng, tất cả có trong diff | erp_ai/agent/changes/test_apply_job.py:1 (và 20 file còn lại cùng dạng) | — |
| (ngoài touchpoint) agent/change_link.py, agent/test_change_link.py | file mới: liên kết ký | erp_ai/agent/change_link.py:21 | CHG-001 M1, T53; review-53 |
| (ngoài touchpoint) change_decision.py, test_change_decision.py | file mới: method `decide` POST-only | erp_ai/change_decision.py:21 | CHG-001 M1, T54, T68, T70; review-54, review-70 |
| (ngoài touchpoint) agent/changes/result_comment.py, test_result_comment.py | file mới: dòng `Info` kết quả | erp_ai/agent/changes/result_comment.py:90 | CHG-001 design, T56/T57; review-56, review-57 |
| (ngoài touchpoint) agent/tools/site_api.py, test_site_api.py | file mới: 7 công cụ bản ghi (`api_list/get/create/update/delete/submit_record`, `api_call_method`), chặn khóa, lọc bí mật | erp_ai/agent/tools/site_api.py:519-624 | spec Amd-2/3, CHG-001 M3/M4, T59–T62; review-59 đến review-62 |
| (ngoài touchpoint) agent/agent_write_guard.py, test_agent_write_guard.py, doctype/erp_ai_credential/erp_ai_credential.py, doctype/erp_ai_log/erp_ai_log.py | file mới và sửa: tài khoản agent không ghi thẳng cấu hình, khóa, nhật ký | erp_ai/agent/agent_write_guard.py:15 | CHG-001 M5, T65–T67; review-65 đến review-67 |
| (ngoài touchpoint) `.github/*`, `.gitignore`, `.claude/rules/team-core.md`, `CLAUDE.md`, `erp_ai/public/js/agent_status_indicator.js`, `docs/**` | không thuộc hành vi FEAT-004: vào nhánh nhờ merge từ `develop` (CI/CODEOWNERS FEAT-001 `aa0deb9`, `.ruff_cache` `73ca1bc`, miễn trừ push `be92ea0`, chỉ báo ẩn BUG-003 `362b3bd`) | .github/workflows/team-ci.yml:1 | không có review của FEAT-004; ghi theo `git log f039112..HEAD` |

Đếm: 8 mục thiết kế (29 hàng ở 3.1) + 28 hàng touchpoint/ngoài touchpoint ở 3.2 (gộp 21 file test thành một hàng).

## Release notes (cho người dùng)

Bản đầy đủ, viết cho người quản trị và người duyệt, nằm ở `release-notes.md` cùng thư mục. Tóm tắt: ba điều đổi (bot ghi bản ghi trực tiếp khi ô code bật ở `L3`; đề xuất code/lệnh duyệt bằng một lần bấm trên phiếu; ô "Toàn quyền"), điều người phải làm sau merge (checklist trong `release-notes.md`), điều chưa được kiểm (mục 1 và 5 file này).

## CHANGELOG

Đã thêm dưới `## [Unreleased]` của `CHANGELOG.md`: Added 5 dòng, Changed 1 dòng, đều kết thúc `(FEAT-004)`. Không đổi `[Unreleased]` thành số phiên bản.

## CLAUDE.md

CLAUDE.md: không sửa. Lý do: lệnh gọi giới hạn vùng ghi của lượt này ở `asbuilt.md`, release notes, PR body, CHANGELOG và README; worktree có `CLAUDE.md` nhưng không có cặp `<!-- project:start -->` / `<!-- project:end -->` (`grep -c 'project:start' CLAUDE.md` → 0), nên không có khối dự án để cập nhật. `check-claude-md.py`: không chạy.
Việc để lại cho người điều phối: nếu muốn khối dự án có chỗ cho FEAT-004, các bẫy đã học: (1) `cmd.test` cả app chỉ đáng tin khi một phiên giữ site `miyano` (`flock` trên `.team/miyano-site.lock`); (2) `bench run-tests` thoát 0 cả khi đỏ; (3) `changes/` không được `set_user` hay phát realtime (ADR-013); (4) `source.py` không được gọi `frappe.logger` lúc import.

## 5. Rủi ro còn lại (đọc trước khi bật trên môi trường thật)

| # | Rủi ro | Nguồn |
|---|---|---|
| 1 | **T61, hàm gọi tự do.** `api_call_method` chặn đọc khóa/mật khẩu chỉ ở mức cố gắng. Sáu dạng còn lọt: (1) hàm whitelist tự chọn cột phía server trả giá trị trần dạng danh sách, không có khóa tên mật để che; (2) `` `db`.`tabUser`.* `` và `distinct *`; (3) NGHI, chưa chạy: `fields` là chuỗi JSON của chuỗi nhiều ký tự có `*` (`"*x"`, `"**"`) mà Frappe tách từng ký tự (`db_query.py:631`); (4) NGHI, chưa chạy: Frappe đổi chỗ `fields` và `filters` (`db_query.py:355-361`), vd `{"fields": [["name","=",X]], "filters": ["tabUser.*"]}`; (5) dương tính giả: từ `token`/`secret`/`password` ở bất kỳ đâu trong tham số làm từ chối cả lời gọi vô hại; (6) đọc DocType của app qua hàm bất kỳ chỉ có so chuỗi (kiểm danh tính ở controller phủ insert, save, delete, rename, submit, cancel; suy từ ADR-023 QĐ 5, chưa đối chiếu mã). Không có test cho (1)–(6). Người cho một vòng sửa cuối (vượt `max_rework` đúng một lần); không sửa thêm. Nâng Frappe (`2e9ecdc`) thì chạy lại probe chặn `fields` lạ (R-2) | spec Amd-3 P-3 AC-33; tasks.md "Rủi ro còn lại của T61"; review-61; acceptance R-2 |
| 2 | **Nhật ký `actions` có trần.** Mục vượt 60000 byte chỉ còn dấu `[đã cắt]`; lượt có quá nhiều lệnh ghi (ước tech-lead 85 đến 850 lời gọi, chưa đo) bỏ các mục cuối, thêm một mục đóng `{"cut", "dropped": n}`: "đúng một mục mỗi lời gọi" không giữ ở ca này. Giá trị trước/sau chỉ là bản tóm tắt (200 ký tự mỗi giá trị, tối đa 20 trường khi xóa). Bản đầy đủ chờ FEAT-005 AC-13 | spec Amd-3 P-3, P-5 mục 2, 3; acceptance R-1 |
| 3 | **Không có cảnh báo khi "Toàn quyền" đang bật,** không hẹn giờ tắt. Quên tắt là rủi ro chính; A-27 yêu cầu ô tắt trên môi trường đích và AC-35 đạt (hoặc người đồng ý bằng văn bản) trước khi bật thật | spec Amd-2 N-2 S-6, A-23, A-27 |
| 4 | **AC-11 thiếu kịch bản:** không có test câu chèn lệnh trong phiếu khi ô Toàn quyền bật (chỉ có kịch bản không có người ra lệnh và kịch bản model khẳng định "đã duyệt") | acceptance.md AC-11, R-5 |
| 5 | **Dòng kết quả `Info` chưa từng thấy trên trang phiếu Helpdesk thật** (AC-28). Theo mã nó hiện như dòng hoạt động mang tên người duyệt; nếu không hiện, phương án trong CHG-001 design A-D1 là ADR mới về cách đánh dấu comment hệ thống, hoặc người đồng ý bỏ AC-28 | acceptance.md "Chỉ người quan sát được sau merge"; CHG-001 design A-D1 |
| 6 | **Chưa quan sát bằng mắt/trình duyệt thật:** form duyệt ở từng trạng thái (AC-22), một lần bấm Duyệt thật (AC-25), "hỏi lại 0 lần" với model thật trên 3 phiếu kịch bản (AC-29), một lần bật Toàn quyền thử (AC-34). Bench `ui: false`, không có Playwright | acceptance.md; spec DoD sau G4 |
| 7 | **Người duyệt phải vào được Desk.** Role `ERP AI Instructor` được tạo với `desk_access: 1` (design §5); chưa kiểm cho Hiếu, Việt, Tiến | spec Amd-3 P-5 mục 6; ADR-012 Hệ quả, ADR-023 QĐ 1 |
| 8 | **Chữ ký liên kết không gắn với người và không hết hạn:** người có vai trò mở một liên kết được chuyển tiếp là duyệt ngay (họ đứng trên form có diff; đề xuất ghi tên họ là người duyệt). Không còn hộp xác nhận ở đường này; lưới còn lại là kiểm lại lúc áp dụng (AC-27) và hoàn tác bằng commit | spec Amd-3 P-2 S-1, A-25 |
| 9 | **Vai trò của tài khoản agent:** `ERP AI Instructor` cần được người gỡ trên từng site (A-31); chưa có bằng chứng đã gỡ trên `miyano`. Spec và README cũ còn câu "tài khoản agent không có System Manager" trong khi tài khoản đang có (P-5 mục 4); chưa sửa chữ, chờ người và architect chốt ADR-006 | spec Amd-3 P-5 mục 4, 5 |
| 10 | **ADR-023 còn `proposed`** dù người đã chọn QĐ 1 và QĐ 6 (b); ADR-011/012/013/022 cũng ghi trạng thái proposed ở đầu file; chuyển trạng thái là việc của architect | spec Amd-3 P-5 mục 1 |
| 11 | **Môi trường test:** cả app chưa sạch, 8 test vẫn 1213 khi chạy lại (mục 1; acceptance.md O-1..O-8); `test_route_ticket::test_sla_chosen_by_complexity_condition` và `test_ticket_panel::test_thread_ignores_non_comment_types` nằm ở `debt.md` (STD-TEST-7) tới lần thứ hai | acceptance.md F-3, F-5; debt.md:48-49 |
| 12 | **Migration:** qa chưa tự chạy up-down-up (R-3). Qa đọc mã Frappe: `remove_orphan_doctypes` chỉ xóa dòng DocType, không xóa bảng | acceptance.md R-3, O-9 |

## Nợ sau G4

Việc qa và spec giao cho writer: acceptance.md ("As-Built/CHANGELOG: owner writer, sau G4"); spec DoD "Sau G4": As-Built, README, CHANGELOG; spec P-6: ba nội dung phải vào As-Built. Đếm: 6 việc.

| Mục DoD qa ghi chủ | Đã làm | Kiểm lại (lệnh → kết quả) |
|---|---|---|
| As-Built | `docs/team/features/FEAT-004/asbuilt.md` | file này; bảng 3.1, 3.2 |
| CHANGELOG | `CHANGELOG.md` | `grep -c '(FEAT-004)' CHANGELOG.md` → 6 (5 Added + 1 Changed) |
| README: công tắc, app, duyệt, hoàn tác, danh sách lệnh, hai ô và ô nào mở gì, khi nào bật Toàn quyền | `README.md`, mục "Sửa code, lệnh bench và ghi bản ghi trực tiếp"; sửa câu "L2/L3 chỉ cấp bộ tool của L1" | `grep -n 'code_change_enabled\|unrestricted_enabled' README.md` khớp AC-1/AC-2 và `registry.py:55-79`. Chưa viết: "cách tự đẩy lên fork" và "làm gì trước và khi `bench update`" (spec Amd-1 DoD): không có nguồn trong diff |
| As-Built: sáu dạng còn lọt của AC-33 (P-6) | mục 5 hàng 1 | — |
| As-Built: hai giới hạn cỡ của AC-34/AC-35 (P-6) | mục 5 hàng 2 | — |
| As-Built: cách gỡ `ERP AI Instructor` khỏi tài khoản agent (A-31) | `release-notes.md`, checklist bước 3, và mục 5 hàng 9 | việc tay của người; không có lệnh trong `cmd.*`: người dán vai trò hiện có của tài khoản vào `acceptance.md` |

Đóng 6/6. Để `/team:release` kiểm: số `(FEAT-004)` trong CHANGELOG; bước 3 của checklist chỉ người làm được.

## Rollback

<!-- /team:release viết trước lần deploy đầu: điều kiện kích hoạt, lệnh (từ docs/team/ci.md), phần dữ liệu, thời gian dự kiến -->
Ghi chú của writer cho `/team:release` (từ design §6 và `registry.py:55-79`, không phải kế hoạch release): "xuống" của migration là đặt `code_change_enabled = 0` (hoàn tác hành vi, không đổi mã) **và** `unrestricted_enabled = 0`, vì nhóm Toàn quyền cấp độc lập với ô code. Revert mã (git revert các commit của tính năng) rồi `cmd.migrate` **xóa DocType `ERP AI Change Proposal`** cùng toàn bộ bản ghi đề xuất, tức mất dữ liệu kiểm toán; cột thừa trên `ERP AI Log` và giá trị thừa trong `tabSingles` vô hại. Commit bot đã tạo trong repo app ở lại trong lịch sử (không bước xuống nào sửa lịch sử git): hoàn tác từng đề xuất bằng nút Hoàn tác trước khi tắt, hoặc `git revert <apply_commit_sha>` tay. Bản ghi bot đã tạo/sửa trực tiếp, và mọi việc xóa/submit/gọi hàm lúc Toàn quyền bật, không có bước xuống: chỉ dựng lại được từ `ERP AI Log` (bản tóm tắt, có trần).

<!-- devops thêm dòng sau khi lên prod thành công: Released: <tag> <YYYY-MM-DD> -->
