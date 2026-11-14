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

## Chèn CHG-001 (Amendment 2), 2026-11-14 (`/team:plan --insert`)

Căn cứ: `spec.md` mục Amendment 2 (AC-24..AC-35, S-1..S-8), ADR-023, `docs/team/features/CHG-001/arch-impact.md` (M1–M5), `review-chg001.md` (3 blocker, 9 major), quyết định của người 2026-11-14 (journal). Không có design riêng cho phần này: `arch-impact.md` ghi các điểm "để designer quyết" không đạt ngưỡng xung đột, nên các lựa chọn dưới đây do plan chốt và mọi task dùng chung.

### Bản đồ file → task
| File | Trách nhiệm sau khi chèn | Task (theo thứ tự) |
|---|---|---|
| `erp_ai/agent/change_link.py` + test | dựng đường dẫn form Desk có chữ ký | T53 |
| `erp_ai/agent/tools/propose_change.py` + test | comment 3 liên kết; đường hợp lệ M5 khi tạo đề xuất | T53 → T67 |
| `erp_ai/change_decision.py` + test | một cửa POST `decide` | T54 → T58 (chỉ test) |
| `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.js` | form tự POST một lần, không hộp hỏi | T54 |
| `erp_ai/agent/changes/apply_job.py` + test | job áp dụng, hoàn tác | T47 → T21 → T22 → T55 → T57 → T48 |
| `erp_ai/agent/changes/result_comment.py` + test (mới) | comment kết quả về phiếu | T56 |
| `erp_ai/agent/tools/site_api.py` + test | công cụ bản ghi | T59 → T60 → T61 → T62 |
| `erp_ai/agent/tools/registry.py` + test | một bảng cấp | T63 |
| `erp_ai/agent/runner.py` + `test_agent_runner.py` | một lời gọi lấy schema; mục hành động có trước/sau | T63 → T64 |
| `erp_ai/agent/agent_write_guard.py` + test (mới) | kiểm danh tính tài khoản agent | T65 |
| controller `erp_ai_setting.py`, `erp_ai_credential.py` | đóng với tài khoản agent | T65 |
| controller `erp_ai_log.py`, `erp_ai/agent/run_log.py` + test | đường hợp lệ 1 | T66 |
| controller `erp_ai_change_proposal.py` | đường hợp lệ 2 | T67 |
| `erp_ai/tests/test_architecture.py` | luật tĩnh của ADR-023 | T32 → T44 → T68 |

### Ràng buộc chung của phần chèn (chép nguyên)
- Đường dẫn quyết định: `/app/erp-ai-change-proposal/<name>?name=<name>&action=<approve|reject>&_signature=<chữ ký>`; chữ ký là HMAC của Frappe trên `name` + `action` (`change_link._signed_query`, không đổi); không hạn (A-9).
- Method duy nhất: `erp_ai.change_decision.decide(name, action, _signature)`, `methods=["POST"]`, không `allow_guest`; role kiểm ở `_decider` của controller. Không method `GET` nào trong `erp_ai/**` đổi trạng thái (ADR-010, ADR-023 QĐ 1).
- Job: người thực hiện không thuộc `NEVER_AUTHORITY`, còn `ERP AI Instructor`, trùng `frappe.session.user`; khóa hết `LOCK_TIMEOUT_S` → `Lỗi` với `LOCK_BUSY`, 1 dòng nhật ký (ADR-023 QĐ 2).
- Tập cấm `site_api`: "đóng ở mọi chế độ" = mọi DocType thuộc module của app (tính động); chế độ thường thêm `DocType`, `Role`, `Custom DocPerm`, `Custom Role`; mọi phép so tên dùng tên đang lưu (ADR-023 QĐ 3).
- Bảng cấp: `site_admin` = (công tắc sửa code ∧ `L3` ∧ người ra lệnh) ∨ (toàn quyền ∧ mức > L0 ∧ người ra lệnh); `site_unrestricted` = toàn quyền ∧ mức > L0 ∧ người ra lệnh; một hàm cấp (ADR-023 QĐ 4).
- M5: `erp_ai/agent/agent_write_guard.py` với `AGENT_WRITE_FLAG = "erp_ai_agent_write_allowed"`, `allow_agent_write()`, `refuse_agent_write(doc)`; cờ ở `frappe.flags`, chỉ `run_log.py` và `tools/propose_change.py` gọi `allow_agent_write` (ADR-023 QĐ 5).
- `api_call_method` giữ gọi tự do (người chọn); không bao giờ trả khóa API hay mật khẩu: `SECRET_METHODS` + `_scrub` (T61). Cam kết "bot không tự đổi công tắc" qua đường ghi DB thẳng là cố gắng, không bảo đảm (ADR-023 QĐ 6 b).
- Nhật ký trước/sau: khóa `value_before`, `value_after` trong kết quả tool và trong mục hành động; không trường mật.

### Thứ tự và song song
Sáu chuỗi theo file chạy cạnh nhau, tối đa 5 dev: (1) `apply_job.py`: T47 → T21 (`cmd.migrate`, một mình trên site) → T22 → T55 → T57 → T48; (2) `site_api.py`: T59 → T60 → T61 → T62; (3) T53 → T67; (4) T63 → T64 (sau T62); (5) T54 → T58 (sau T55); (6) T65 → T66, T67; T56 đứng riêng; `test_architecture.py`: T32 (sau T22) → T44 → T68 (sau cùng). Đường găng: chuỗi (1) rồi T32 → T44 → T68 → T34.

### AC / biện pháp → task
| Mã | Task |
|---|---|
| M1 (AC-24, AC-25, AC-26, NFR-10) | T53, T54, T68 |
| M2 (ADR-012 QĐ 7, NFR-6) | T55 |
| AC-27, AC-12 qua liên kết | T58 |
| AC-28 | T56, T57, T48 |
| M3 (AC-31, AC-33) | T59, T68 |
| AC-30 | T60 |
| AC-33 phần gọi hàm, NFR-5 | T61 |
| AC-35, NFR-11 | T62, T64 |
| M4 (AC-1, AC-2, AC-32) | T63, T68 |
| M5 (AC-33, AC-5) | T65, T66, T67, T68 |
| AC-29, AC-14, AC-34 | đã có trong mã nhận về, review-chg001 nhóm H không còn blocker/major ngoài M4; 4 điểm nhỏ để deferred |

### Checkpoint thêm
8. Sau T54 và T53: `cmd.test_one` của `test_change_decision.py`, `test_change_link.py`, `test_propose_change.py` xanh; không còn `/api/method/` trong comment.
9. Sau T67 (M5 đủ ba task): `cmd.test` cả app xanh — đây là chỗ lộ ra nếu bộ chặn chặn nhầm chính runner.
10. Sau T68: `cmd.test`, `cmd.lint`; rồi T34.

### Rủi ro thêm
| Rủi ro | Dấu hiệu | Cách xử lý |
|---|---|---|
| M5 chặn nhầm runner (runner lưu Setting hoặc Log ngoài `write_entry` dưới tài khoản agent) | `cmd.test` đỏ ở `test_agent_runner`, `test_runner_*` sau T65/T66 | dev trả `NEEDS_CONTEXT`; không mở đường hợp lệ thứ ba khi chưa có architect |
| Comment kết quả (AC-28) do job ghi dưới phiên người duyệt làm agent chạy lại | job agent mới sau `post_result` | T56 có test đếm 0 job; ghi comment theo cách comment của bot |
| `api_call_method`: không biết bản ghi bị chạm nên `value_before` rỗng | AC-35 chỉ đạt phần tên hàm | ghi cho qa và người; không chặn build |
| Người duyệt không vào được Desk | qa/người kiểm trên `miyano` | ngoài build (ADR-023 QĐ 6); T33 đã ghim role có `desk_access` |
| Liên kết GET cũ trong comment của đề xuất đang chờ | người bấm nhận lỗi | duyệt bằng nút trên form; ghi vào As-Built |

### Trọng tâm review của phần chèn
1. Dict do client gửi có khóa `flags` không bật được đường hợp lệ của M5 (T65).
2. `decide` qua GET thật sự bị từ chối ở tầng Frappe, không chỉ ở test gọi hàm trực tiếp (T54).
3. Job áp dụng còn lại sau bước kết thúc request (T54), không đếm trên `frappe.enqueue` đã patch.
4. Tên chữ thường của DocType, role, user (T59); chuỗi JSON lồng trong tham số `call_method` (T61).
5. Comment kết quả không mang dòng cuối đầu ra git có URL (T56, review-45 deferred).

## Chèn sau nghiệm thu lượt chốt (F-3, F-4, F-5), 2026-11-14 (`/team:plan --insert --decide`)

Căn cứ: `acceptance.md` @ `8351761` (Verdict: rework; F-3, F-4, F-5), lệnh của team-leader (journal 2026-11-14). Không có Amendment mới của spec: đây là sửa lỗi test theo phán quyết của qa, không đổi hành vi sản phẩm. qa gọi hai bản sửa là "T65/T66" nhưng hai mã đó đã dùng; mã trống kế tiếp là T69.

### Bản đồ file → task
| File | Trách nhiệm sau khi chèn | Task |
|---|---|---|
| `erp_ai/agent/tools/source.py` | không gọi `frappe.logger` lúc import; lấy logger `"erp_ai.source"` ở lần dùng | T69 |
| `erp_ai/agent/tools/test_source.py` | ghim: import module không tạo logger; chỗ ghi log vẫn dùng tên `"erp_ai.source"` | T69 |
| `docs/team/debt.md` | F-5 và F-4 ở bảng "Test chập chờn" | tech-lead (không giao dev) |
| `docs/team/features/FEAT-004/diff.patch` | làm mới sau merge T69 | tech-lead |

Không sửa `erp_ai/gateway/test_gateway.py`: phép so `used_sinks()` ở `:937` giữ nguyên độ chặt (STD-TEST-5).

### Ràng buộc chung của phần chèn
- Tên logger giữ nguyên `"erp_ai.source"`; chữ và mức của 9 chỗ ghi log (`source.py:153, 213, 309, 315, 318, 418, 421, 615` và chỗ tương ứng) không đổi.
- Chỉ `source.py:13` gọi `frappe.logger` ở mức module trong `erp_ai/**` ngoài test (grep 2026-11-14: 17 chỗ gọi, 16 chỗ nằm trong thân hàm).
- Mọi `bench --site miyano run-tests` bọc `flock -w 1800 /home/miyano/frappe-bench/apps/erp_ai/.team/miyano-site.lock`, mỗi lúc một lệnh; `QueryDeadlockError` thì chạy lại theo tên một lần. Không chạy `cmd.test` cả app ở lượt này (team-leader xếp khung giờ riêng cho qa).

### F-4 không thành task (quyết định, decide)
Lệnh giao: tìm test để lại trạng thái làm `test_erp_ai_log::test_no_role_can_write_or_delete` đỏ, rồi sửa tại nguồn và ghim bằng cặp test theo thứ tự. Bằng chứng đọc được trước khi lập task cho thấy không có test nào như vậy:
- Role thừa trong thông điệp lỗi là `ERP AI Instructor`. Trên `team/FEAT-004`, `develop`, `team/FEAT-005`, file `erp_ai_log.json` chỉ có `System Manager`, `ERP AI Agent`; không chỗ nào trong `erp_ai/**` của nhánh tạo DocPerm hay Custom DocPerm trên `ERP AI Log` (grep `add_permission|Custom DocPerm|setup_custom_perms|update_permission_property`: chỉ `Task` và `HD Ticket`).
- `team/FEAT-007` commit `5b3fe27` (2026-11-14 19:17:46, T5 của FEAT-007) thêm đúng DocPerm thứ ba `ERP AI Instructor` (`read`, `report`) vào `erp_ai_log.json` và sửa chính phép so này thành ba role. Dòng progress T5 trong `docs/team/features/FEAT-007/tasks.md` ghi "`cmd.migrate` từ worktree dev xong" trước commit đó. Phiên FEAT-007 không dùng chung khóa site.
- Lần cả app của qa chạy `TestERPAILog` lúc 19:14:44 (junit `v/app.xml`), tức trong lúc site `miyano` đang mang lược đồ của FEAT-007. `v/migrate.log` (19:21:10) là một lần migrate sau đó; 19:27 chạy riêng `Ran 1` `OK`; tech-lead chạy lại cả module dưới khóa lúc 19:51: `Ran 7 tests in 5.092s` / `OK`.

Kết luận: F-4 là lược đồ của nhánh khác được migrate vào site dùng chung giữa lúc chạy, không phải thứ tự test trong FEAT-004. Sửa mã hay sửa test trong nhánh này đều sai (nới phép so là vi phạm STD-TEST-5; FEAT-007 đã tự đổi phép so cùng với lược đồ của nó). Việc làm: ghi vào `debt.md`, báo team-leader. Phương án khác đã loại: giao dev cắt đôi danh sách module (tốn ít nhất một lần chạy cả app, không tìm ra gì vì nguyên nhân nằm ngoài tiến trình test). Sai thì: nếu một lần cả app trong khung giờ độc quyền (đã migrate từ worktree FEAT-004 ngay trước, không phiên nào khác migrate) vẫn đỏ ở test này, mở task T70 với junit của lần đó.

### Thứ tự và song song
Một task dev (T69), không phụ thuộc. Việc tài liệu của tech-lead chạy cạnh.

### AC / phát hiện → task
| Mã | Task |
|---|---|
| F-3 (STD-TEST-6; AC-14 phần khóa gateway, NFR-5) | T69 |
| F-4 (STD-TEST-6 theo qa) | không task; `debt.md` + báo team-leader |
| F-5 (STD-TEST-7) | `debt.md` |

### Checkpoint thêm
11. Sau T69: `cmd.test_one` của `test_gateway.py` chạy riêng (thứ tự từng đỏ: module `source` chưa được nạp) và chạy sau khi `source` đã nạp (thứ tự cả app), `test_source.py`, `test_erp_ai_setting.py`, `test_architecture.py` đều `OK`.

### Trọng tâm review của phần chèn
1. Phép so của `test_api_key_never_leaks` không bị đụng; `git diff` không chạm `test_gateway.py`.
2. Test ghim mới đỏ vì hành vi thiếu (logger tạo lúc import), không vì lỗi import.
3. Hai test cũ vá `source.logger` (`test_source.py:110`, `:1346`) chỉ đổi cách vá, giữ nguyên điều chúng khẳng định.
4. Lỗi khi lấy logger không nuốt lỗi gốc ở các nhánh `except` của `source.py` (STD-ERR-1).
