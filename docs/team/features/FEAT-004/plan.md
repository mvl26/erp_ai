Feature: FEAT-004
Stage: plan
Author-agent: tech-lead
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Plan FEAT-004 (lập lại sau spec Amendment 1, ADR-022 và design "Sửa vòng 1")

- Nhánh feature: `team/FEAT-004` từ **`team/FEAT-006 (hash at build time)`**. Nhánh chưa được tạo ở bước plan (không `git switch`; FEAT-006 đang do phiên khác build trong `.claude/worktrees/feat-006`). `config.base_branch` = `main` chỉ dùng lúc PR.
- Điều kiện bắt đầu build: FEAT-006 đã qua verify. Khi đó tech-lead tạo `team/FEAT-004` từ đầu nhánh `team/FEAT-006`, ghi mã commit thật vào dòng Tiến độ của `tasks.md`, chạy `cmd.test` trước T1 và T35. Số dòng `file:line` trong design là của `team/FEAT-003`: dev dò lại trên nền thật; tên hàm, tên file giữ nguyên.
- Số task: 51 (34 giữ ID, 17 mới T35–T51); song song tối đa: 2 (`limits.max_parallel_dev`). Bảng đổi ID cũ → mới nằm đầu `tasks.md`; FEAT-005 trích `F4-T2..T7, T12, T23, T24, T28..T33`, các ID đó không đổi.
- Cỡ L, gate áp dụng: G5 (G3 tắt trong `.team/config.json`). Lệnh: `cmd.test_one`, `cmd.test`, `cmd.migrate`, `cmd.lint` của profile. Plan không ghi `current.json`.

## Ràng buộc chung (chép từ design/ADR-011/012/013/022; mọi task kế thừa)
- Tên chính xác: DocType `ERP AI Change Proposal` (autoname `AICHG-.#####`); 9 hằng `CHANGE_STATUS_*`; `CHANGE_KIND_CODE`, `CHANGE_KIND_COMMAND`; `TRIGGER_CHANGE_ACTION = "change_action"`; `TITLE_CHANGE_FAILED`; `COMMAND_TIMEOUT_S` (540); `RUN_BACKSTOP_S` (570); `OUTPUT_MAX_LINES` (400); `PROPOSAL_TEXT_MAX_CHARS = 20000`, `REPLACE_MAX_ITEMS = 10`; `PROPOSAL_FILE_MAX_BYTES`. **[Sửa vòng 1]** `CORE_APPS`, `BOT_GIT_NAME = "ERP AI Agent"`, `BOT_GIT_EMAIL = "erp-ai-agent@bot.invalid"` (`constants.py`); mã lý do `GIT_*` (`GIT_COMMIT_FAILED`, `GIT_COMMIT_MISMATCH`, `GIT_RESTORE_FAILED`, `GIT_BRANCH_CHANGED`, `GIT_NOT_ANCESTOR`, `GIT_LOCKED`, `GIT_ERROR`) chép đúng chữ design 3.2/4.3.
- Chữ ký (design 3.2–3.6, 3.9) giữ nguyên: `check_write_path(..., read_git=True)`, `build_bench_args`, `check_bench_args`, `GuardResult` (+`is_core_app`, `git`); `enqueue_change_job`; `run_change(proposal_name, action)` (chữ ký không đổi); `transitions.{InvalidTransition, STATE_FIELDS (+4), prepare_new, content_digest (14 trường), approve, reject, request_undo, begin_apply, finish(..., fields=None), log_step}`; `file_writer.{sha256_of, write_atomic, remove_created}`; **`process_runner.{CommandResult, run_bench, git_add_new, git_commit_only, git_unstage_new}`** (đổi tên từ `bench_runner`, D-12); `source.{read_git_state, run_git_read, git_env, git_global_options, git_head, git_commit_summary, git_blob, git_is_ancestor}`; `change_text.{safe_person_name, apply_message, undo_message, message_text, proposal_notes}`; `registry._granted_specs / get_tool_schemas / grants_change_tools` có `change_enabled` bắt buộc; `build_reason_system(prompt_digest, routing_table="", *, change_tools=False)` (D-21, nền FEAT-006).
- Câu chữ lỗi tool (bảng 3.1), lỗi method (3.3), lý do kiểm lại (4.3), câu từ chối git (3.2) là hợp đồng với test: chép nguyên.
- Đúng 3 method `@frappe.whitelist(methods=["POST"])`, không `allow_guest`; role bằng `frappe.get_roles`.
- Trường nội dung/đầu ra của DocType là `Code`, `read_only=1`. Quyền JSON: `ERP AI Agent` create+read, `ERP AI Instructor` read, `System Manager` read, không `write/delete/submit/cancel/amend`.
- Ghi trường trạng thái chỉ trong `changes/transitions.py`; ghi/đổi hệ tệp chỉ trong `file_writer.py`; tiến trình con chỉ trong `source.py` (git đọc, bench-sibling) và `changes/process_runner.py` (bench, git ghi `add`/`commit --only`/`rm --cached`); `changes/**` không có `frappe.set_user`, `publish_realtime`; tool đề xuất không `.save(`/`db_set`/`set_value`; controller, `@frappe.whitelist`, `handlers.py`, `runner.py` không gọi git (ADR-022 QĐ 3).
- **[Sửa vòng 1] Git (ADR-022):** đúng 1 commit local `--only` chỉ chứa file đích, trên nhánh đang checkout; không `push`, `fetch`, `checkout`, `branch`, `reset`, `rebase`, `merge`, `amend`, `tag`, `remote`, `config`; hook của repo không chạy (`core.hooksPath` = `agent/git_no_hooks`); danh tính commit lấy từ `BOT_GIT_*`, không email/URL/token thật; thứ tự áp dụng: dấu file → kiểm trước git → ghi → commit → kiểm sau (D-19); commit lỗi → đọc HEAD trước khi trả lại (D-17); hoàn tác file mới = gỡ file khỏi đĩa rồi `commit --only` (D-18, kiểm sớm ở T35).
- **Mọi test git dùng `GitSandbox` (T36, T51), không chạy git trong `apps/` thật (NFR-9).** Lệnh git của helper dùng `GIT_CONFIG_GLOBAL=/dev/null`.
- Trường mới của `ERP AI Setting` và `ERP AI Log` PHẢI có `description` tiếng Việt ≤ 400 ký tự (luật FEAT-003). Số nền đọc thật trên `team/FEAT-006` (FEAT-006 +2 trường Setting, +4 cột Log) rồi cộng: Setting +2 trường, +1 section; Log +3 trường.
- Thêm file mới chỉ dưới `erp_ai` (21 đường dẫn, design mục 7; 0 trong `protected_paths`) và hai file ghi chú `dev-notes*.md` dưới `docs/team/features/FEAT-004/`. Test cũ không sửa assertion (STD-TEST-5); chỉ các chỗ design liệt kê (`_all_specs` 11 → 14, lời gọi `get_tool_schemas` thêm `False`, luật kiến trúc).
- Task nào sửa `*.json` của DocType: `cmd.migrate` trên `miyano` trước `cmd.test_one`. Mọi task: test đỏ trước, chỉ sửa trong `files:`, không skip/xfail.
- Luật kiến trúc: task nào thêm mã làm luật HIỆN CÓ đỏ thì sửa luật đó theo ADR trong chính task (chuỗi `test_architecture.py` ở bảng một chủ). Luật mới: T31, T32 (ADR-011/012/013), T44 (ADR-022).

## Thứ tự
1. **Kiểm sớm (T1, T35).** T1 đo `bench migrate`/`build --app` (D-10, NFR-3): > 540 s → dừng, báo team-leader. T35 kiểm D-18 trên git 2.43 trong thư mục tạm: `commit --only -- <đường dẫn đã xóa khỏi đĩa>` phải ghi việc xóa; không đạt → `DESIGN_CONFLICT`, dừng T20 và T47, báo architect (mở rộng ADR-022 QĐ 2).
2. **Nền (T2–T11, T36–T43).** Hằng số; `GitSandbox` (T36 lõi, T51 trạng thái); `source.py` git (T37 → T38 → T39); `change_text` (T40 → T41); bộ chặn (T7 → T8 → T9 → T42); cấu hình/log/policy (T3, T12, T4, T5, T6); `file_writer` (T10); `process_runner` (T11 → T43).
3. **Walking skeleton S1 (T12 → T13 → T14 → T16 → T18 → T19 → T46 → T45).** Bản ghi đề xuất có sẵn trong DB (dựng bằng test) đi qua `approve` POST → job → ghi đúng từng byte → đúng 1 commit local trong repo tạm → `Đã áp dụng`, và nhánh trả lại khi commit lỗi. Không cần model. **Không task nào của nhánh tool/runner (T25–T30, T50) bắt đầu trước khi review T45 là approve** (S1 nay gồm cả bước git, đường rủi ro nhất). T23, T24 (registry, prompt) độc lập với job nên được chạy trước cổng để lộ sớm xung đột với FEAT-006.
4. Hết S1: hoàn tác (T20, T47), lệnh (T21, T22), test chéo (T48), 3 tool và comment (T25 → T26 → T27 → T50), đăng ký (T28), runner (T29, T30), luật kiến trúc (T31, T32, T44), test cài đặt (T33), form (T49 → T17), checkpoint cuối (T34, tech-lead).

## Nhóm song song (≤ 2 dev, không chung file)
| Lượt | Cùng chạy | Ghi chú |
|---|---|---|
| 1 | T1 ∥ T35 | hai bước kiểm, ghi hai file khác nhau (`dev-notes.md`, `dev-notes-git.md`) |
| 2 | T7 ∥ T2 | |
| 3 | T36 ∥ T3 | |
| 4 | T51 ∥ T8 | |
| 5 | T37 ∥ T9 | T37 mở chuỗi `test_architecture` |
| 6 | T12 ∥ T38 | T12 trước T4 vì Link của log trỏ tới DocType |
| 7 | T4 ∥ T39 | |
| 8 | T5 ∥ T40 | |
| 9 | T11 ∥ T41 | T11 cần T1 xong |
| 10 | T43 ∥ T10 | |
| 11 | T13 ∥ T6 | |
| 12 | T14 ∥ T15 | |
| 13 | T16 ∥ T42 | |
| 14 | T49 ∥ T18 | |
| 15 | T17 ∥ T19 | |
| 16 | T46 ∥ T23 | |
| 17 | T45 ∥ T24 | hết lượt: checkpoint S1, review T45 approve mới mở lượt 18 |
| 18 | T20 ∥ T25 | T20 cần T35 đạt |
| 19 | T47 ∥ T26 | |
| 20 | T21 ∥ T27 | |
| 21 | T22 ∥ T50 | |
| 22 | T48 ∥ T28 | |
| 23 | T29 ∥ T31 | |
| 24 | T30 ∥ T32 | |
| 25 | T44 ∥ T33 | |
| 26 | T34 | tech-lead |
Lịch là gợi ý; ràng buộc thật là cột `depends:` và bảng một chủ. Hai task chung file không bao giờ chạy cùng lúc.

## Bảng mỗi file một chủ
Chuỗi (`→`) là thứ tự bắt buộc; task sau phụ thuộc task trước. **[F6]** = file FEAT-006 cũng sửa.
| File | Chủ | Task khác chạm | Thứ tự |
|---|---|---|---|
| docs/team/features/FEAT-004/dev-notes.md | T1 | T17 (ghi bước tay) | T1 → T17 |
| docs/team/features/FEAT-004/dev-notes-git.md | T35 | — | — |
| erp_ai/constants.py | T2 | — | — |
| erp_ai/agent/changes/__init__.py | T2 | — | — |
| erp_ai/agent/change_text.py, test_change_text.py | T40 | T41 | T40 → T41 |
| erp_ai/agent/git_no_hooks/README.md | T37 | — | — |
| erp_ai/agent/tools/source.py, test_source.py | T36 (test) | T37, T38, T39, T51 (test) | T36 → T51 → T37 → T38 → T39 |
| erp_ai/agent/changes/transitions.py, test_transitions.py | T13 | T2 (test hằng), T14 | T2 → T13 → T14 |
| erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json **[F6]** | T3 | — | — |
| erp_ai/tests/test_doctype_descriptions.py **[F6]** | T3 | T4 | T3 → T4 |
| erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json **[F6]** | T4 | — | — |
| erp_ai/agent/run_log.py, test_run_log.py, erp_ai/tests/test_tasks.py | T4 | — | — |
| erp_ai/agent/policy.py **[F6]**, test_policy.py **[F6]** | T5 | — | — |
| erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py **[F6]**, test_erp_ai_setting.py **[F6]** | T6 | — | — |
| erp_ai/agent/tools/change_guard.py, test_change_guard.py | T7 | T8, T9, T42 | T7 → T8 → T9 → T42 |
| erp_ai/test_utils.py **[F6]** | T7 | T36, T51, T12 | T7 → T36 → T51 → T12 |
| erp_ai/agent/changes/file_writer.py, test_file_writer.py | T10 | — | — |
| erp_ai/agent/changes/process_runner.py, test_process_runner.py | T11 | T43 | T11 → T43 |
| erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/{__init__.py, .json} | T12 | — | — |
| erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py, test_erp_ai_change_proposal.py | T12 | T13 (hook `before_insert`), T16, T49, T17 (test) | T12 → T13 → T16 → T49 → T17 |
| erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.js | T17 | — | — |
| erp_ai/agent/queue.py, test_queue.py | T15 | — | — |
| erp_ai/agent/changes/apply_job.py, test_apply_job.py | T18 | T19, T46, T45, T20, T47, T21, T22, T48 (chỉ test) | T18 → T19 → T46 → T45 → T20 → T47 → T21 → T22 → T48 |
| erp_ai/agent/tools/registry.py **[F6]**, test_registry.py **[F6]** | T23 | T28 | T23 → T28 |
| erp_ai/agent/test_run_status.py | T23 | — | — |
| erp_ai/agent/prompts.py **[F6]**, erp_ai/agent/test_classification.py **[F6]** | T24 | — | — |
| erp_ai/agent/tools/propose_change.py, test_propose_change.py | T25 | T26, T27, T50 | T25 → T26 → T27 → T50 |
| erp_ai/agent/runner.py **[F6]**, test_agent_runner.py **[F6]** | T23 (chỗ gọi `get_tool_schemas`) | T29, T30 | T23 → T29 → T30 |
| erp_ai/tests/test_architecture.py **[F6]** | T37 | T5, T11, T43, T13, T15, T25, T31, T32, T44 | T37 → T5 → T11 → T43 → T13 → T15 → T25 → T31 → T32 → T44 |
| erp_ai/tests/test_install.py **[F6]** | T33 | — | — |

**Các file FEAT-006 chung (design "Chỗ đụng FEAT-006": 16 mục trong bảng, trừ `write_ticket.py` không sửa) và task chạm:** `prompts.py` T24; `runner.py` T23, T29, T30; `registry.py` T23, T28; `policy.py` T5; `erp_ai_setting.json` T3; `erp_ai_setting.py` T6; `erp_ai_log.json` T4; `test_doctype_descriptions.py` T3, T4; `test_utils.py` T7, T36, T51, T12; `test_classification.py` T24; `test_agent_runner.py` T23, T29, T30; `test_policy.py` T5; `test_registry.py` T23, T28; `test_erp_ai_setting.py` T6; `test_install.py` T33; `test_architecture.py` T37, T5, T11, T43, T13, T15, T25, T31, T32, T44. Quy tắc: đọc mã FEAT-006 thật trước; chỉ thêm; không đổi assertion của FEAT-006; mốc "trùng byte" (AC-1, AC-14) là đầu ra của bản FEAT-006. (Đầu việc nêu "14 file", bảng design liệt kê 16 mục, nên plan đánh dấu cả 16; chênh lệch cần team-leader xác nhận với danh sách FEAT-006.)

Touchpoint của design → task: tất cả dòng bảng mục 7 đều có chủ: constants T2; policy T5; run_log T4; queue T15; runner T23/T29/T30; prompts T24; **change_text T40/T41 (mới)**; **git_no_hooks/README T37 (mới)**; registry T23/T28; **source.py T37–T39 (mới)**; change_guard T7–T9, T42; propose_change T25–T27, T50; `changes/__init__` T2; transitions T13/T14; apply_job T18–T22, T45–T48; file_writer T10; **process_runner T11/T43 (đổi tên)**; DocType 4 file T12/T13/T16/T49/T17; setting.json T3; setting.py T6; log.json T4; test_utils T7/T36/T51/T12; test file: test_change_guard T7–T9/T42, test_propose_change T25–T27/T50, test_source T36–T39/T51, test_change_text T40/T41, test_registry T23/T28, test_run_status T23, test_transitions T2/T13/T14, test_apply_job T18–T22/T45–T48, test_file_writer T10, test_process_runner T11/T43, test_erp_ai_change_proposal T12/T13/T16/T49/T17, test_policy T5, test_run_log T4, test_queue T15, test_agent_runner T23/T29/T30, test_classification T24, test_erp_ai_setting T6, test_tasks T4, test_doctype_descriptions T3/T4, test_architecture (chuỗi trên), test_install T33. Không hàng trống.

## AC / NFR → task
| Mã | Task |
|---|---|
| AC-1 | T23 (ma trận registry), T24 (prompt trùng byte), T29 (runner) |
| AC-2 | T23, T28, T29 |
| AC-3 | T25, T26, T50 (HEAD/`status` không đổi) |
| AC-4 | T7, T8, T9, T25, T26 |
| AC-5 | T16, T33 |
| AC-6 | T10, T14, T18, T19 (stale, 1 commit), T46 |
| AC-7 | T16, T20, T47 |
| AC-8 | T11, T21, T27 |
| AC-9 | T9, T21, T27 |
| AC-10 | T11, T22 |
| AC-11 | T30 |
| AC-12 | T4, T14, T19 (mã commit dòng `apply`), T20 (dòng `undo`), T30 |
| AC-13 | T11, T22, T43, T48 |
| AC-14 | T24, T29 |
| AC-15 | T31, T32, T44, T34 (`ls docs/team/adr/`, `cmd.test` xanh) |
| AC-16 | T8, T42, T50 |
| AC-17 | T19, T40, T43 |
| AC-18 | T25 (lúc đề xuất), T38, T46 (lúc áp dụng; spec D-1 đổi nhánh → `Hết hiệu lực`) |
| AC-19 | T45 (áp dụng; spec D-2 a, b), T47 (hoàn tác), T48 (hook không chạy, D-2 c) |
| AC-20 | T20, T47 |
| AC-21 | T39 (upstream), T41, T50 |
| AC-22 | T12 (bố cục), T49, T17, T34 (qa mở form, ảnh/mô tả vào `acceptance.md`) |
| AC-23 | T44, T48 (ref remote không đổi) |
| NFR-1 | T19 (0 commit khi job lặp), T25, T27 |
| NFR-2 | T14, T19, T21 |
| NFR-3 | T1, T11, T22, T43, T46 (khóa git nhanh) |
| NFR-4 | T11 |
| NFR-5 | T11, T22 |
| NFR-6 | T14, T19, T20 |
| NFR-7 | T19, T20, T48 |
| NFR-8 | T37 (env git), T40 (`safe_person_name`), T48 (metadata sạch) |
| NFR-9 | T36, T51 (mixin), T34 (qa/tech-lead so HEAD và `status` 4 repo lõi trước/sau `cmd.test`) |
23/23 AC, 9/9 NFR. Mục ngoài AC: mô tả field (T3, T4), `runs_today`/`recompute` không đổi (T4, T5), `validate_change_apps` cho app lõi (T5, T6), D-17 (T45), D-18 (T35, T20), D-12 (T11), D-21 (T24, T29), D-14 (T49), D-13 (T37).

## Preflight (cặp task chung file hoặc giao diện)
| Cặp | Chung | Xử lý |
|---|---|---|
| T3 ↔ T4 | `test_doctype_descriptions.py` | T3 → T4 |
| T5 ↔ T6 | `policy.validate_change_apps` | T5 làm hàm, T6 chỉ gọi |
| chuỗi `test_architecture.py` | T37 → T5 → T11 → T43 → T13 → T15 → T25 → T31 → T32 → T44 | cố định; T37 đứng đầu vì lời gọi git mới của `source.py` có thể làm luật subprocess đỏ |
| T7 ↔ T36 ↔ T51 ↔ T12 | `test_utils.py` | T7 helper gốc `apps/`; T36 `GitSandbox` lõi; T51 trạng thái + mixin; T12 đề xuất mẫu |
| T36 → T51 → T37 → T38 → T39 | `source.py`, `test_source.py` | cố định; T36/T51 chỉ thêm test |
| T7 → T8 → T9 → T42 | `change_guard.py` | T42 thêm `read_git`, `is_core_app`; không đổi hành vi T7–T9 |
| T11 → T43 | `process_runner.py` | T11 bench; T43 git ghi; không đổi `run_bench` |
| T12 → T13 → T16 → T49 → T17 | controller + test | cố định; T49 dùng `change_text` (T41) |
| T18 → T19 → T46 → T45 → T20 → T47 → T21 → T22 → T48 | `apply_job.py`, `test_apply_job.py` | mỗi task thêm một nhánh, không đổi nhánh cũ; T48 chỉ thêm test |
| T23 → T28 | `registry.py` | T23 đổi cấp + `ToolContext` (sau `routing_config`); T28 chỉ thêm module |
| T23 → T29 → T30 | `runner.py` | T23 chỉ thêm đối số `change_enabled` ở lời gọi `get_tool_schemas`; T29 truyền thêm `routing_table` và `change_tools`; T30 dòng `propose` |
| T25 → T26 → T27 → T50 | `propose_change.py` | cùng `PROPOSE_TOOL_NAMES`; T50 điền trường git và comment |
| T24 ↔ T29 | `build_reason_system` | T24 định nghĩa chữ ký `(prompt_digest, routing_table="", *, change_tools=False)`; T29 gọi |
| T35 → T20 | D-18 | T20 chỉ chạy khi T35 ghi "đạt" |
Không có task tự mâu thuẫn. Task cần chữ ký chưa có đều đứng sau task tạo ra nó (ví dụ T19 cần `git_commit_only` T43 và `read_git_state` T38; T25 cần `check_write_path(read_git=True)` T42). Chữ ký trong design không khớp mã thật → `DESIGN_CONFLICT`.

## Rủi ro
| Rủi ro | Dấu hiệu | Cách xử lý |
|---|---|---|
| `bench migrate`/`build` > 540 s (NFR-3) | số đo T1 | dừng, báo team-leader; cần ADR mới (ADR-013 QĐ 3) |
| D-18 sai: git 2.43 không ghi việc xóa khi `commit --only` | T35 báo không đạt | `DESIGN_CONFLICT`, dừng T20 và T47; architect mở rộng ADR-022 QĐ 2 (cho `rm --cached` trước commit) |
| Nền `team/FEAT-006` đổi/chưa verify; xung đột ở 16 file chung | `git log` khác lúc tạo nhánh; test FEAT-006 đỏ | build chỉ sau FEAT-006 verify; ghi hash thật; chạy `cmd.test` trước T1; số `field_count`/`section_count` đọc thật, không dùng số dự kiến |
| Số dòng design lệch (design đọc `team/FEAT-003` @ `7cb654f`) | `NEEDS_CONTEXT` ở dev | dev dò lại theo tên hàm; không đổi tên |
| Test git chạm repo thật `apps/frappe`... (NFR-9) | HEAD/`status` 4 repo lõi đổi sau `cmd.test` | mọi test git qua `GitSandbox`; `RealCoreReposUntouchedMixin` (T51, T48); T34 so trước/sau |
| Test git chậm hoặc phụ thuộc cấu hình git máy | test lạ, flaky | `GIT_CONFIG_GLOBAL=/dev/null`, danh tính cố định; lệnh git có `timeout`; không flaky thì không rerun-until-green |
| Lệnh git mới làm luật subprocess đỏ | `test_architecture` đỏ ở T37/T43 | sửa luật trong chính task theo ADR-022; không có thì `DESIGN_CONFLICT` |
| T19 và T36 vượt 5 phút | dev báo | tech-lead tách (T19: phần 4–5; T36: ví dụ worktree) và giữ ID; ghi vào `tasks.md` |
| Commit thành nhưng lệnh báo lỗi (git bị diệt sau khi dời ref), hoặc HEAD dời do commit tay của người | HEAD khác `old_head` | D-17 (Sửa vòng 2): đọc HEAD trước khi trả lại; HEAD đã đổi thì đọc `author_email`: ≠ `BOT_GIT_EMAIL` → trả lại + `GIT_COMMIT_FAILED`, không lưu commit id; là bot → kiểm sau `len(parents)==1` và `git_is_ancestor(old_head, parents[0])` (T39, T45, T47) |
| FEAT-005 cũ trích `build_reason_system(prompt_digest, change_tools=False)` | plan FEAT-005 lệch chữ ký | design "Chỗ đụng FEAT-005": team-leader/tech-lead chạy `/team:plan --insert` cho FEAT-005 sau; ngoài phạm vi lần này |
| `timeout`, `bench` hoặc `git` không có trong `PATH` của worker | `returncode 127` | `not_found` (có test); production `UNVERIFIED`, ghi vào `dev-notes.md` |
| Site `miyano` duy nhất: migrate DocType mới ảnh hưởng phiên khác | test lạ ở phiên song song | build chỉ sau FEAT-006 verify; FEAT-005 build sau FEAT-004 |

## Walking skeleton (cỡ L)
S1 = T12 → T13 → T14 → T16 → T18 → T19 → T46 → T45 (cộng T15 queue, T43/T38/T39/T40 làm nền): chạy đầu-cuối phía server mà không cần model, trong repo git tạm của `GitSandbox`. Đề xuất `Chờ duyệt` (dựng bằng helper test) → `approve` (POST, role Instructor) → `enqueue_change_job` → `run_change` lấy khóa chung, commit `Đang áp dụng`, kiểm lại, so `base_hash`, kiểm trước git, `write_atomic`, đúng 1 commit `--only` → file và blob khớp từng byte → `Đã áp dụng` kèm `apply_commit_sha`, đúng 1 dòng nhật ký mỗi bước; commit lỗi thì trả lại file, HEAD và vùng staged như trước. Sau review T45 approve mới mở nhánh tool/runner.

## Checkpoint (`cmd.test` xanh trên `team/FEAT-004`, dán đầu ra)
1. Sau T1, T35: số đo `migrate`/`build --app <app>` trong `dev-notes.md` (≤ 540 s); `dev-notes-git.md` ghi "đạt" D-18.
2. Sau T6 (dữ liệu/cấu hình): `cmd.migrate` thành công; `cmd.test` xanh; trường cũ của `ERP AI Setting` (gồm trường FEAT-006) trước = sau.
3. Sau T43 (nền git): `cmd.test` xanh; luật subprocess xanh với hai file.
4. Sau T45 (S1): review approve; `cmd.test` xanh; HEAD và `status` 4 repo lõi thật không đổi.
5. Sau T22 và T48: lệnh, hoàn tác, test chéo xong; `cmd.test` xanh.
6. Sau T30, T32, T44: `cmd.test`, `cmd.lint` sạch; `ls docs/team/adr/` có ADR-011/012/013/022 tham chiếu ADR-005 (AC-15); `cmd.migrate` lên/xuống/lên đối soát số dòng `ERP AI Log`, `runs_today`, `spent_this_month_usd`, trường cũ của `ERP AI Setting`.
7. Hết build (T34): `diff.patch`; xóa `.team/active-build`; báo roles đã gọi; qa dán HEAD/`status` 4 repo lõi trước/sau `cmd.test` (NFR-9) và ảnh/mô tả form 3 trạng thái (AC-22) vào `acceptance.md`.
