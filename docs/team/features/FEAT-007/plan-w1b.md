Feature: FEAT-007
Stage: plan
Author-agent: tech-lead
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. G3 không áp dụng (team.py: chỉ G5). -->

# Plan FEAT-007 — đợt 1b (gộp `develop` lần hai, U2, U6b, U8 AC-62/63)

Bổ sung cho `plan.md` (đợt 0) và `plan-w1.md` (đợt 1a), không thay chúng. 47 task ở `tasks-w1b.md`: T126 (gộp `develop` lần hai), T127–T139 (U2), T140–T166 (U6b), T167–T171 (U8), T172 (U6a, một sửa trên `knowledge.py` đứng trước T148; chèn ngày 2026-11-15 theo `design-w1b-fixes-1.md`, bản phán hai điểm R-3 và R-7 của designer). Đợt 2 (U7a, U7b, U8 AC-64, U5b) chưa lập.

Skill đã chọn: `/team:plan FEAT-007` theo lời giao của team-leader (`docs/team/journal/FEAT-007.pending.md`, dòng 04:02 (c) và dòng "lý do gọi tech-lead ×2"); `team.py status FEAT-007` lúc lập: `planned 50/124 READY`, không cổng nào trước G5. Lượt này chạy song song với vòng build 12, nên chỉ ghi hai file `plan-w1b.md`, `tasks-w1b.md`; không ghi `tasks.md`, `docs/team/journal/FEAT-007.md`, `.team/current.json` (file sau đang là của phiên CHG-002).

Đầu vào đã đọc: `design-addendum-1-U2.md` mục 1.3–8; `design-w0-fixes-3.md` phán quyết 2 và mục 4; `arch-review-design-w1a.md` mục 1–5; `arch-review-w0-fixes-3.md` mục 3–6; `arch-review-design-w2a.md:104-115`; `arch-ruling-r5.md` mục Căn cứ, 1, 2; `design-addendum-1-U6b.md` mục 1.2–8; `design-addendum-1-U6b-fixes.md` mục 1–5; `arch-review-design-w1b-r2.md` mục 3–8; `design-addendum-3-w1.md` mục 4–8; `design-w0-fixes-5.md` điểm 4; `review-39.md` kết luận của tech-lead; `design-addendum-1-U4b-U8.md:149-204`; `design-addendum-1-U4b-U8-fixes.md` Fix 3, Fix 7, R1–R4; `arch-impact-chg-002.md` mục 1.4, 2, 3; `docs/team/features/CHG-002/design.md` mục 1.6; `spec-addendum-2.md:50` (AC-22 `[changed]`). Chưa đọc từng dòng: `design-addendum-1-U6b.md` mục 1.1; `design-addendum-1-U4b-U8.md` mục 1, 2, 4–8; các task dẫn số dòng của những mục đó làm nguồn chữ, dev đọc trực tiếp.

## Thứ tự

1. T126 (gộp `develop` lần hai) chạy ở vòng build đầu tiên sau khi commit merge của CHG-002 có trên `develop` và không nhánh task nào mở trên file của nó. Mốc cứng: trước T105, trước mọi task U7a và trước khi lập kế hoạch đợt 2. Mốc mềm: trước T89. Không chờ cuối đợt 1 (`arch-impact-chg-002.md:112-118`).
2. U2, phần không chạm `runner.py`, `handlers.py`: T127 → T128 → T129 → T130 (`policy.py`, sau T71) và T132 → T133 → T134 → T135 → T136 (`site_api.py`, sau T82) chạy xen với U3, U4b (R5-4).
3. U2, phần còn lại: T131 (sau T114), T137 (sau T113, T118), T138, T139 (sau T119). **T137 merge thì ràng buộc R5-5 hết**: ưu tiên T137 ngay khi T118 tick.
4. U6b, file mới, chạy xen với U4b: T142 → T143 → T144 → T146 → T147 (`lifecycle.py`); T172 (`knowledge.py`, sau T123) → T148 → T149 → T150 (`knowledge_read.py`); T152 (`kb_draft.py`); T151 (`reply.py`, sau T100 theo E-3); T153 → T154 (`read.py`, sau T130).
5. U6b, file chung, sau U4b và U2: T140 (commit trigger) → T141 → T145; T155 (bảng cấp); T156 → T157 (prompt); T158 → T159 → T160 (handler); T162 → T163 → T164 → T165 (runner); T161 (móc sự kiện, cuối cùng); T166 (sau T54).
6. U8: T167 → T168 → T169 (`write_ticket.py`, ngay sau T104); T170 (`prompts.py`, sau T157); T171 (kiểm đầu-cuối, sau T165).

`runner.py`: U1 → U3 → U4b → U2 (T137) → U6b (T162 → T163 → T164). U8 không sửa `runner.py`. `prompts.py`: U1 → U4b → U6b (T156, T157) → U8 (T170).

## Nhóm song song

Trần `limits.max_parallel_dev` = 2. Hai làn, mỗi vòng lấy task sẵn sàng đầu làn; hai task cùng một dòng của bảng "Một file, một chủ" không bao giờ cùng lượt.

| Giai đoạn | Làn A | Làn B |
|---|---|---|
| Xen với U3, U4b (sau T71, T82) | T127 → T128 → T129 → T130 → T153 → T154 | T132 → T133 → T134 → T135 → T136 (T132 chờ T130) |
| Xen với U4b (file mới) | T142 → T143 → T144 → T146 → T147 | T172 (sau T123) → T148 → T149 → T150; T152; T151 (sau T100, T143); T167 → T168 → T169 (sau T104) |
| Sau T118, T119 (hết U4b) | T137 → T138 → T162 | T131 → T139 → T140 → T141 → T145 |
| U6b file chung | T163 → T164 → T165 → T171 | T155; T156 → T157 → T170; T158 → T159 → T160; T166 (sau T54) |
| Cuối | T161 [migrate] | — |

T126 chạy một mình trong lượt của nó.

## Ràng buộc chung

Chép nguyên văn từ thiết kế; mọi task dùng đúng các tên này. Ràng buộc chung của `plan-w1.md` giữ nguyên.

- `policy.py` (U2): `EXCLUDED_TITLE_PREFIXES_FIELD = "excluded_title_prefixes"`; `SUBJECT_FIELD = "subject"`; `SEND_POLICY_FIELDS = (OPT_OUT_FIELD, TEAM_FIELD, SUBJECT_FIELD)`; `EXCLUDED_BY_CLASSIFICATION = "excluded_by_classification"`; `REFUSAL_OPTED_OUT = "opted_out"`, `REFUSAL_EXCLUDED_TEAM = "excluded_team"`, `REFUSAL_EXCLUDED_TITLE = "excluded_title"`, `REFUSAL_EXCLUDED_BY_CLASSIFICATION = "excluded_by_classification"`, `REFUSAL_MISSING = "missing"`; `EXCLUDED_TICKET_REASON = "bản ghi thuộc phiếu không được phép đưa cho AI"`; `TICKET_LINK_FIELDS` có đúng 3 khóa `Comment`, `Communication`, `File`; `excluded_title_prefixes()`, `has_excluded_title(subject)`, `excluded_team_names()`, `is_excluded_by_classification(ticket_name)`, `send_refusal(ticket) -> str | None`, `can_send_ticket(ticket) -> bool` (giữ chữ ký), `excluded_ticket_names() -> list`, `ticket_link_columns(doctype) -> tuple[tuple[str | None, str], ...]`, `ticket_content_filters(doctype) -> tuple[list, list]`, `owning_ticket(doctype, name) -> str | None`, `is_ticket_record_excluded(doctype, name) -> bool`.
- Thứ tự của `send_refusal`: không có phiếu → `missing`; `ai_opt_out` → `opted_out`; nhóm loại trừ → `excluded_team`; tiêu đề có tiền tố → `excluded_title`; `agent_group` trống ∧ doc đã lưu ∧ bị loại bởi phân loại → `excluded_by_classification`; ngược lại `None`.
- Một lối vào cột (C-U2-1): chỉ `ticket_link_columns` đọc `TICKET_LINK_FIELDS`; cặp động cộng mọi Link tĩnh của `ticket_link_fieldnames`. Thân `ticket_link_fieldnames`, `is_ticket_content_doctype` (T15) không sửa.
- `site_api.py` (U2): `EXCLUDED_LIST_NOTE = "Phiếu nhóm loại trừ, phiếu không dùng AI và mọi bản ghi của chúng không bao giờ có trong danh sách."`; `PERMISSION_DOCTYPES` thêm `"User Permission"`, `"DocShare"`; `PROPERTY_SETTER_DOCTYPE = "Property Setter"`; `PERMLEVEL_PROPERTY = "permlevel"`; `PERMLEVEL_REASON = "Property Setter đổi permlevel là sửa phân quyền, không làm qua công cụ"`; `PERMLEVEL_DOCTYPES = ("Property Setter", "Custom Field")`; `permlevel_refusal(doctype: str, values: dict, *, name: str | None = None) -> str | None`; `_permlevel_refusal(doctype, name, values, ctx)`. Vị từ phiếu loại trừ áp ở cả hai chế độ; vector phân quyền chỉ khi `ctx.unrestricted` sai. `call_method` không đổi.
- `_classify` sau U2: parse → ô U2 (hàm dò `excluded_probe`, `stop_reason=policy.EXCLUDED_BY_CLASSIFICATION`, trả `(False, classification, context)`) → chốt dưới ngưỡng → chọn chế độ → khóa định tuyến → `_route`. Đúng một lời gọi `parse_classification(`; đúng một dòng `is_excluded_team=`.
- Trigger (U6b): `TRIGGER_REQUESTER_REPLY = "requester_reply"`, `TRIGGER_KB_DRAFT = "kb_draft"` ở `erp_ai/constants.py`; `policy.RUN_LIMIT_TRIGGERS = (TRIGGER_TICKET_INSERT, TRIGGER_COMMENT_MENTION, TRIGGER_REQUESTER_REPLY)`; luật `set(run_log.TRIGGERS) - set(policy.RUN_LIMIT_TRIGGERS) == {TRIGGER_KB_DRAFT}`; `kb_draft` không bao giờ vào `RUN_LIMIT_TRIGGERS` hay `NOTICE_TRIGGERS`.
- `queue.py` (U6b): `requester_reply_key(ticket_name, communication_name) -> str` = `f"{TRIGGER_REQUESTER_REPLY}:{ticket_name}:{communication_name}"`; `enqueue_agent_run(ticket_name, trigger, comment_name=None, communication_name=None) -> bool`; `job_id` của `requester_reply` = `f"erp_ai::{ticket_name}::{trigger}::{communication_name}"`; `_claim_pending(job_id) -> bool`; `LIFECYCLE_JOB_TIMEOUT_S = 300`; `enqueue_lifecycle_job(ticket_name) -> bool`, `job_id = f"erp_ai_lifecycle::{ticket_name}"`; `ENQUEUE_TARGETS` = 6 đích, đích mới `"erp_ai.agent.lifecycle.run_task_lifecycle"`.
- `lifecycle.py` (U6b): `LifecycleSettings(reply, resolve_on_tasks_done, close_silent_f, close_silent_f_days, kb_draft, field_origin, origin_board_value)`; `lifecycle_settings(settings)`, `kb_draft_enabled()`, `origin_configured(ls)`, `status_change_refusal(ticket_name, ls)`, `send_to_requester(ticket_name, html) -> str`, `is_requester_sender(sender, raised_by) -> bool`, `newer_requester_message_exists(ticket_name, communication_name) -> bool`, `tasks_done(ticket_name) -> tuple[bool, int]`, `silent_since(ticket_name)`, `run_task_lifecycle(ticket_name)`, `scan_silent_f_tickets(now=None)`; `STATUS_RESOLVED = "Resolved"`, `STATUS_CLOSED = "Closed"`, `RESOLVED_CATEGORY = "Resolved"`; `TOOL_RESOLVE_ON_TASKS_DONE = "resolve_on_tasks_done"`, `TOOL_CLOSE_SILENT_F = "close_silent_f"`, `TOOL_LIFECYCLE_COMMENT = "lifecycle_comment"`, `TOOL_REQUESTER_NOTICE = "requester_notice"`, `TOOL_LIFECYCLE_CONFIG = "ticket_lifecycle"`; savepoint `"erp_ai_lifecycle"`, `"erp_ai_silent_close"`; `run_id` của dòng "chưa cấu hình" = `f"lifecycle-config-{now.date().isoformat()}"`; cờ `doc.flags.erp_ai_silent_close`. Chỉ `write_bot_action`, gọi cuối, là commit. `lifecycle` không import `erp_ai.agent.tools.*`, `runner`, Cổng model.
- Lần chạy `requester_reply`: `run_id = queue.requester_reply_key(...)`; lý do `skip`: `event_missing`, `event_moved`, `superseded`; `already_handled` chỉ là dòng logger, không có dòng ERP AI Log. Lần chạy `kb_draft`: lý do `skip` `kb_draft_off`, `not_closed`, `kb_exists`, `no_resolution_content`; không kiểm giới hạn ngày.
- `registry.py` (U6b): `REPLY_GROUP = "requester_reply"`, `KB_DRAFT_GROUP = "kb_draft"`; `GrantInputs` và `ToolContext` thêm `reply_enabled: bool = False`, `kb_draft_run: bool = False`; `Grant.reply_block: bool = False`; `ASK_TOOL_NAMES = frozenset({"post_comment", "reply_to_requester"})`; hàng `requester_reply` | `reply_enabled ∧ ¬kb ∧ ¬below_threshold`; hàng `kb_draft` | `kb`; mọi nhóm của U1 thêm vế `¬kb`.
- Tool (U6b): `KNOWLEDGE_TOOL_NAMES = frozenset({"search_knowledge_base", "search_manuals", "read_error_logs", "run_report"})`, nhóm `read`; `MANUALS_NOT_CONFIGURED = "chưa có kho HDSD"`; `REPORT_FILTER_MAX_KEYS = 10`; `REPORT_TYPES = ("Script Report", "Query Report")`; `REPLY_KINDS = ("answer", "question")`; `REPLY_MAX_CHARS = 4000`; `SOURCES_MAX = 5`; `KB_TITLE_MAX = 140`; `RESOLVER_COMMENTS_MAX = 3`. Mọi chuỗi tool trả về đi qua `redact.redact_secrets`.
- Một lần hỏi mỗi lần chạy, mọi kênh (E-1, AC-22 `[changed]`): chỉ `write_ticket.py` đọc và ghi `frappe.flags.erp_ai_asked_runs`; `reply.py` gọi `write_ticket.asked_in_run`, `write_ticket.mark_asked`, dùng `write_ticket.REASON_ONE_ASK`.
- `prompts.py`: `TASK_REQUESTER_REPLY`, `TASK_KB_DRAFT`, `KNOWLEDGE_SOURCES_BLOCK`, `REPLY_BLOCK`, tham số `reply_tools` (U6b); `TASK_CATEGORY_C`, `CATEGORY_HINT_TRIGGERS = (TRIGGER_TICKET_INSERT, TRIGGER_COMMENT_MENTION)` (U8). `prompts.py` không đọc cấu hình.
- `write_ticket.py` (U8): `DEFAULT_MAX_TASKS_PER_RUN = 10`; `REASON_NO_ESTIMATE`, `REASON_TASK_DUPLICATE`, `REASON_TASK_LIMIT`; `BA_NOTE_SECTIONS = ("Mục tiêu", "Phạm vi", "Tính năng sẵn có", "Rủi ro", "Câu hỏi mở")`; `REASON_BA_NOTE_MISSING`, `REASON_BA_NOTE_FEATURE`, `REASON_BA_NOTE_EXISTS`, `REASON_BA_NOTE_NOT_C`; `BA_NOTE_MARKER` import từ `erp_ai.agent.ops_data`; chống trùng chỉ qua `locked_count`; không commit trong lượt (R5-16); không import `propose_change`, `catalog`, `catalog_tools`, `runner`.
- Hướng phụ thuộc mới: `tools/reply.py` → `tools/write_ticket.py`, `lifecycle`; `handlers` → `lifecycle`, `queue`; `runner` → `lifecycle`, `queue`; `daily_report` → `lifecycle`; `queue` không import `lifecycle`, `runner`; `policy` không import `queue`, `run_log`, `tools`.
- Lệnh: chỉ các ô `cmd.test_one`, `cmd.test`, `cmd.migrate`, `cmd.lint`, `formatters_by_ext` của profile, chạy qua khóa site theo `plan.md` mục "Chạy test từ worktree trên site dùng chung".

## Touchpoint → task

| Touchpoint (nguồn) | Task |
|---|---|
| Lần gộp `develop` thứ hai (`arch-impact-chg-002.md` mục 2; `CHG-002/design.md` mục 1.6) | T126 |
| `erp_ai/agent/policy.py`, `test_policy.py` (U2 3.1; `design-w0-fixes-3.md:81-95`; C-U2-1) | T127, T128, T129, T130 |
| `erp_ai/agent/tools/site_api.py`, `test_site_api.py` (U2 3.2, 3.3, 3.4; C-6, C-7, C-U2-2; w2a (5)) | T132, T133, T134, T135, T136 |
| `erp_ai/agent/runner.py`, `test_agent_runner.py` (U2 3.5; C-5; R5-6) | T137, T138 |
| `erp_ai/agent/test_routing.py` (C-8) | T137 |
| `erp_ai/handlers.py`, `erp_ai/tests/test_handlers.py` (U2 3.6) | T131 |
| `erp_ai/tests/test_architecture.py` (U2: ADR-034 Ràng buộc 1–2, `POLICY_FIELDS`) | T139 |
| `erp_ai/constants.py` (U6b Sửa 3) | T140 |
| `erp_ai/agent/queue.py`, `test_queue.py` (U6b 3.1; Sửa 1, 3) | T140, T141, T145 |
| `erp_ai/agent/run_log.py`, `test_run_log.py`, `erp_ai_log.json` (U6b 3.12; Sửa 4) | T140 |
| `erp_ai/agent/policy.py` (U6b Sửa 3, một chỗ) | T140 |
| `erp_ai/tests/test_doctype_descriptions.py` (U6b 3.12, cụm từ) | T140 |
| `erp_ai/tests/test_architecture.py` (U6b Sửa 3, Sửa 5) | T140, T145 |
| `erp_ai/agent/lifecycle.py`, `test_lifecycle.py` (mới; U6b 3.6; Sửa 1, 2, 13, 15) | T142, T143, T144, T146, T147 |
| `erp_ai/agent/knowledge.py`, `test_knowledge.py` (U6a; `design-w1b-fixes-1.md` điểm 2; `review-39.md:34`, `:95`) | T172 |
| `erp_ai/agent/tools/knowledge_read.py`, `test_knowledge_read.py` (mới; U6b 3.3; `review-39.md`; `design-w1b-fixes-1.md` điểm 2) | T148, T149, T150 |
| `erp_ai/agent/tools/reply.py`, `test_reply.py` (mới; U6b 3.4; E-1, E-3) | T151 |
| `erp_ai/agent/tools/kb_draft.py`, `test_kb_draft.py` (mới; U6b 3.5) | T152 |
| `erp_ai/agent/tools/read.py`, `test_read.py` (U6b 3.10; Sửa 6; `design-w0-fixes-5.md` điểm 4) | T153, T154 |
| `erp_ai/agent/tools/registry.py`, `test_registry.py` (U6b 3.2; Sửa 12) | T155 |
| `erp_ai/agent/prompts.py`, `test_prompts.py` (U6b 3.9; Sửa 1, 9) | T156, T157 |
| `erp_ai/handlers.py`, `erp_ai/tests/test_handlers.py` (U6b 3.7; Sửa 1) | T158, T159, T160 |
| `erp_ai/hooks.py` (U6b 3.11; Sửa 14) | T161 |
| `erp_ai/agent/runner.py`, `test_agent_runner.py` (U6b 3.8; Sửa 1, 9; E-1, E-2; U6b-1) | T162, T163, T164, T165 |
| `erp_ai/agent/daily_report.py`, `test_daily_report.py` (U6b Sửa 7, INT-U6b-1) | T166 |
| `erp_ai/agent/tools/write_ticket.py`, `test_write_ticket.py` (U8: `create_task`, `ba_note`; Fix 3; U8-1, U8-2) | T167, T168, T169 |
| `erp_ai/agent/prompts.py`, `test_prompts.py` (U8: Fix 7) | T170 |
| `erp_ai/agent/test_agent_runner.py` (U8: R2, U8-3) | T171 |
| `erp_ai/install.py`, `erp_ai/tests/test_install.py` (U6b Sửa 8) | không task: T60 đã cài quyền đọc HD Article cho Instructor và đã tick |
| `erp_ai/agent/routing.py`, `erp_ai/eval/export_tickets.py` (U2 mục 7) | không sửa, không task |
| `erp_ai/agent/tools/route_ticket.py`, `schedules.py`, `tasks.py` (U6b mục 2) | không sửa, không task |

File "mới" đều dưới `erp_ai` (khớp `structure.allowed_new_file_roots`); không đường dẫn nào khớp `protected_paths`. File "sửa" đều có trên `team/FEAT-007` @ `7821d40`, trừ `erp_ai/agent/daily_report.py` (T51–T54 của đợt 0 tạo; T166 chờ T54) và `erp_ai/agent/test_prompts.py` (T78 tạo).

## Một file, một chủ

Nối tiếp các chuỗi của `plan-w1.md`. Task trên cùng một dòng chạy nối tiếp theo thứ tự ghi; chỗ `depends:` chưa mang thì tech-lead build giữ theo bảng này. T126 chen vào mọi dòng có file của nó ở đúng lúc nó chạy.

| File | Chuỗi task |
|---|---|
| `erp_ai/agent/policy.py`, `test_policy.py` | … T71 → T127 → T128 → T129 → T130 → T140 |
| `erp_ai/agent/runner.py` | … T113 → T137 → T162 → T163 → T164 |
| `erp_ai/agent/test_agent_runner.py` | … T118 → (T126) → T137 → T138 → T162 → T163 → T164 → T165 → T171 |
| `erp_ai/agent/test_routing.py` | T137 |
| `erp_ai/handlers.py`, `tests/test_handlers.py` | … T114 → T131 → T158 → T159 → T160 → T161 (T161 chỉ `test_handlers.py`) |
| `erp_ai/agent/tools/site_api.py`, `test_site_api.py` | T65 → T82 → T132 → T133 → T134 → T135 → T136 |
| `erp_ai/tests/test_architecture.py` | … T99 → T119 → T139 → T140 → T145; T105 và T126 đứng ở bất kỳ chỗ nào trong chuỗi nhưng không cùng lượt với task nào ở dòng này |
| `erp_ai/agent/queue.py`, `test_queue.py` | T75 → T140 (chỉ `queue.py`) → T141 → T145 |
| `erp_ai/agent/run_log.py`, `test_run_log.py` | … T93 → T140 |
| `erp_ai_log.json` | T85 → T140 |
| `erp_ai/tests/test_doctype_descriptions.py` | … T64 → T125, T85 → T140; T43, T49 của đợt 0 không cùng lượt với T140 |
| `erp_ai/constants.py` | (T126) → T140 |
| `erp_ai/agent/lifecycle.py`, `test_lifecycle.py` | T142 → T143 → T144 → T146 → T147 |
| `erp_ai/agent/knowledge.py`, `test_knowledge.py` | T37 → T39 → T120 (chỉ `test_knowledge.py`) → T123 → T172 (nối chuỗi của `plan-w1.md:129`) |
| `erp_ai/agent/tools/knowledge_read.py`, `test_knowledge_read.py` | (T172, file khác, phải merge trước) → T148 → T149 → T150 |
| `erp_ai/agent/tools/reply.py`, `test_reply.py` | T151 |
| `erp_ai/agent/tools/kb_draft.py`, `test_kb_draft.py` | T152 |
| `erp_ai/agent/tools/read.py`, `test_read.py` | T153 → T154 |
| `erp_ai/agent/tools/registry.py`, `test_registry.py` | … T82 → (T126, chỉ `test_registry.py`) → T155 |
| `erp_ai/agent/prompts.py`, `test_prompts.py` | … T107 → (T126) → T156 → T157 → T170 |
| `erp_ai/agent/tools/write_ticket.py`, `test_write_ticket.py` | … T104 → T167 → T168 → T169 |
| `erp_ai/hooks.py` | T34, T44 (đợt 0), T161: không cùng lượt |
| `erp_ai/agent/daily_report.py`, `test_daily_report.py` | T51 → T52 → T53 → T54 → T166 |
| `erp_ai/agent/tools/propose_change.py`, `test_propose_change.py` | T89 (trước hoặc sau T126) → T126 → T105 |
| `erp_ai/agent/tools/source.py`, `test_source.py`, `test_change_guard.py`, `erp_ai/test_utils.py`, `erp_ai/agent/test_classification.py` | T126 |
| `erp_ai_setting.py`, `erp_ai_setting.json`, `test_erp_ai_setting.py` | chuỗi của `plan-w1.md` giữ nguyên (chuỗi U0 → T56 → T32 → T63 → T64 → T72 → T87 → T124); không task nào của đợt 1b vào chuỗi này. Các trường đợt 1b đọc đã có trên `team/FEAT-007` @ `7821d40` (U0): `excluded_title_prefixes`, `field_origin`, `origin_board_value`, `reply_enabled`, `resolve_on_tasks_done_enabled`, `close_silent_f_enabled`, `close_silent_f_days`, `kb_draft_enabled`, `manuals_dir`, `report_row_limit`, `max_tasks_per_run`. Task nào thấy thiếu trường → `DESIGN_CONFLICT`, không tự thêm |

Task `[migrate]` của đợt 1b: T126, T140, T161.

## Điều kiện → task

| Điều kiện | Nguồn | Task | Ghi chú |
|---|---|---|---|
| C-5 (phần U2) | `arch-review-design-w1a.md:59` | T137 | trả `(False, classification, context)` |
| C-6 | `arch-review-design-w1a.md:60`, `:82-85` | T136 | Custom Field `permlevel`; `PERMLEVEL_DOCTYPES` công khai |
| C-7 | `arch-review-design-w1a.md:61` | T134 | chép nguyên văn vào task |
| C-8 | `arch-review-design-w1a.md:62` | T137 | test ghim ở `test_routing.py`; không sửa `routing.py` |
| C-U2-1 | `arch-review-w0-fixes-3.md:62` | T130 (hàm), T133 (test lọc), T134 (ghi) | chép nguyên văn vào T130; thắng `design-w0-fixes-3.md:86` ở vế "ngược lại" |
| C-U2-2 | `arch-review-w0-fixes-3.md:63` | T133 (hai test đọc), T134 (ca Task của C-7) | |
| Thứ tự `policy.py` | `arch-review-w0-fixes-3.md:64` | T15 → U1 (T66–T71) → U2 (T127–T130) → U6b (T140) | không sửa thân hai hàm của T15 |
| w2a (5) `permlevel_refusal` công khai | `arch-review-design-w2a.md:110-115` | T136 | U7a (đợt 2) gọi, không chép luật |
| R5-4 | `arch-ruling-r5.md:49` | `depends:` của T127 (T71), T131 (T114), T132 (T82), T137 (T113, T118) | không "rebase" |
| R5-5 | `arch-ruling-r5.md:50` | team-leader; hết khi T137 merge | SHA ghi ở progress của T137 |
| R5-6 | `arch-ruling-r5.md:51` | T137 | ca phân loại lại; `test_excluded_wins_over_low_confidence` giữ |
| E-1 | `arch-review-design-w1b-r2.md:75` | T151 (tool), T163 (hai test đầu-cuối) | chép nguyên văn; AC-22 đã `[changed]` ở `spec-addendum-2.md:50` |
| E-2 | `arch-review-design-w1b-r2.md:76` | T163 (ba ô `NOTICE_TRIGGERS`), T164 (giữ test `kb_draft`) | chép nguyên văn |
| E-3 | `arch-review-design-w1b-r2.md:77` | T151 `depends:` T100 | chép nguyên văn |
| C-3 phần U6b; w1a phán quyết (2) | `arch-review-design-w1a.md:70-74` | T140 | một commit |
| Quyết định (ii), Sửa 8 | `arch-review-design-w1b-r2.md:88` | T60 (đã tick); T152 có `test_instructor_lists_bot_drafts` | U6b không sửa `install.py` |
| U6b-1 | `design-addendum-3-w1.md:128` | T165 | ca hai dựa vào ADR-037 (T113) |
| U8-1, U8-2, U8-3 | `design-addendum-3-w1.md:120-122` | T168, T169, T171 | |
| `review-39.md`: che `heading`; file HDSD không đọc được | `review-39.md:94-95`, `:100`; `design-w1b-fixes-1.md` điểm 2 | T148 (che `heading`; tool không bắt `OSError`), T172 (bỏ riêng file hỏng ở `knowledge.search_manuals`) | ba test mới: hai của T148, một của T172 |
| U2-R1, U2-R2, U2-R3 | `design-w1b-fixes-1.md` điểm 1 | T137 | hai test thêm, một test mở rộng; không thêm chỗ sửa ngoài ô U2 |
| Task sửa `knowledge.py` merge trước T148 | `design-w1b-fixes-1.md:93` | T148 `depends:` T172 | |
| `design-w0-fixes-5.md` điểm 4, hai test `test_read.py` | `design-w0-fixes-5.md:94-95` | T153 | `depends:` T123 |
| R-12 của `plan-w1.md` (U6b chờ T120, T121, T123) | `plan-w1.md` R-12 | T148 `depends:` T120, T121, T123, T172; T172 `depends:` T123; T151, T152 `depends:` T120; T153 `depends:` T123 | |
| CI-17..CI-24; CI-1, CI-4, CI-5, CI-6, CI-12 (tiền tố), CI-15, CI-16 | `arch-impact-chg-002.md:90-133` | T126 | |
| CI-2, CI-3, CI-5, CI-6 trên task đợt 1a | `arch-impact-chg-002.md:91-95` | bảng "Sửa dòng task cũ khi gộp" của `tasks-w1b.md` (T105, T89, T76, chuỗi `prompts.py`) | |
| CI-7..CI-14 | `arch-impact-chg-002.md:96-103` | chưa lập (U7a, U7b, đợt 2) | |

Không điều kiện nào của U2, U6b, U8 (AC-62/63) còn thiếu task.

## AC → task

| AC | Task |
|---|---|
| AC-5 `[changed]` | T135, T136, T138 |
| AC-8 `[changed]` | T129, T130, T132, T133, T134, T139 |
| AC-9 | T127, T128, T131, T137 |
| AC-22 `[changed]` (một câu hỏi, một kênh) | T151, T163 |
| AC-23 (thông báo của lần chạy `requester_reply`, `kb_draft`) | T163, T164 |
| AC-40 | T143, T151, T155, T157, T163 |
| AC-41, AC-41 `[changed]` | T140, T141, T143, T146, T156, T158, T162, T165 |
| AC-42 | T142, T144, T147 |
| AC-43 | T144, T145, T159 |
| AC-44 | T146, T161 |
| AC-45 | T140, T152, T155, T156, T160, T164 |
| AC-46 | T148 |
| AC-47 | T172, T148, T157 |
| AC-48 | T153, T154, T157 |
| AC-49 | T150 |
| AC-50 | T149 |
| AC-51 (xếp loại hành động của U6b trong báo cáo 08:00) | T166 |
| AC-62 | T169, T170, T171 |
| AC-63 | T167, T168, T171 |
| AC-65 (phần của U6b, U8) | T165, T168, T169, T171 |
| NFR-1 | T129, T132, T133, T134, T137, T152, T153 |
| NFR-2 | T140, T162, T164 |

AC của đợt 1b theo `arch-impact.md` và các addendum: AC-5, AC-8, AC-9 (U2); AC-40..AC-50 (U6b); AC-62, AC-63 (U8). 16/16 có task. Không thuộc đợt 1b: AC-64 (U8 phần 2), AC-66 (b), AC-67 phần còn lại, AC-68, AC-69 (U7a, U7b), AC-53..AC-58 (U5b).

## Mốc kiểm

Chính sách N-6 của `tasks.md` giữ: sau mỗi merge chạy `cmd.test_one` của task và `erp_ai/tests/test_architecture.py`, cùng `cmd.lint`; `cmd.test` cả bộ chỉ ở mốc.

| Mốc | Sau | Kiểm |
|---|---|---|
| M-G2 | T126 | `cmd.migrate` rồi `cmd.test` cả bộ xanh, trước task kế tiếp trên `propose_change.py` (CI-23). Gộp vào mốc M8..M11 gần nhất nếu mốc đó rơi ngay sau T126 |
| M12 | T139 (hết U2) | `cmd.test` xanh. `git merge-base --is-ancestor <SHA của T137> team/FEAT-007` đúng; báo team-leader R5-5 đã hết. Luồng tay trên `miyano`: tạo phiếu tiêu đề `[HR] thử` → 0 lần chạy, 1 dòng logger `not_sendable:excluded_title` |
| M13 | T147, T150, T154 (hết file mới của U6b) | `cmd.test_one` xanh cho `test_lifecycle`, `test_knowledge` (T172), `test_knowledge_read`, `test_reply`, `test_kb_draft`, `test_read`, `test_architecture` |
| M14 | T166, T171 (hết đợt 1b) | `cmd.migrate`, `cmd.test` xanh. Luồng tay trên `miyano`: Task có `ai_ticket` sang `Completed` với công tắc tắt → `status` phiếu không đổi, 0 dòng `bot_action`. Đây là mốc "cuối đợt 1" của `arch-impact.md:185`: từ đây `team/FEAT-007` → `develop` mới được xét (R5-5) |

## Rủi ro

| # | Rủi ro | Cách giữ |
|---|---|---|
| R-1 | Mã CHG-002 chưa ở `develop` khi U4b tới T105 | T105 `depends:` T126; chuỗi `test_architecture.py` đi T99 → T119 → T105. U4b tới T105 mà CHG-002 chưa xong thì dừng báo người (quyết định 03:46 (c) của team-leader) |
| R-2 | T135 mở rộng `PERMISSION_DOCTYPES`, tập mà `erp_ai/tasks.py` (cảnh báo hằng ngày của FEAT-005, ADR-024) và `hard_bans` cùng đọc | `Expect` của T135 chạy `test_tasks`, `test_hard_bans`, `test_erp_ai_setting`; test ghim tập cũ mà đỏ → `DESIGN_CONFLICT`, architect phán |
| R-3 | Thiết kế U2 viết trước U4b: câu "payload không chứa comment" của AC-9 (b) chỉ đúng cho lần tạo phiếu; lần phân loại lại (T113) gửi `later_messages` cho model trước khi biết phiếu thuộc bộ phận loại trừ (`arch-ruling-r5.md:53`, để ngỏ cho designer) | Đã phán ở `design-w1b-fixes-1.md` điểm 1; câu rủi ro còn lại → analyst (`--amend`), chặn nghiệm thu AC-9, không chặn T137. T137 mang ba luật U2-R1..R3 và ba test của điểm đó |
| R-4 | T140 có 9 file trong một commit | Thiết kế buộc (`design-addendum-1-U6b-fixes.md:141`); mỗi file đổi 1–3 dòng; chạy một mình trong lượt của nó |
| R-5 | Hai chuỗi dài chờ hết U4b: `test_architecture.py` (T119 → T139 → T140 → T145) và `runner.py` (T113 → T137 → T162 → T163 → T164) | File mới của U6b, `policy.py`, `site_api.py`, `write_ticket.py` của U8 chạy xen với U4b theo bảng "Nhóm song song" |
| R-6 | Tên do kế hoạch đặt, thiết kế chỉ nêu hành vi: test `test_block_operations_in_manuals_refused` (T126), `test_link_columns_dynamic_plus_static` (T130), `test_custom_field_permlevel_refused` (T136), `test_reclassified_into_excluded_team_stops` (T137), `test_refusal_reasons_in_order` (T142), bốn test `TestRequesterMessages` (T143), `test_secret_in_heading_masked` (T148), `test_question_marks_run_and_second_question_refused` (T151), `TestReplyBlock::test_block_follows_reply_tools_flag` (T157), `TestHooksWiring::test_u6b_hooks_registered` (T161), `test_guidance_run_collects_done_line` (T168) | Designer đổi tên thì sửa một dòng task |
| R-7 | `review-39.md` cho hai lối với file HDSD không đọc được; kế hoạch chọn "tool bắt `OSError`" vì `knowledge.py` không thuộc touchpoint của U6b. Hệ quả: một file hỏng làm cả lần tìm trả từ chối có lý do, không trả kết quả của các file còn lại | Đã phán ở `design-w1b-fixes-1.md` điểm 2: bỏ riêng file hỏng ở `knowledge.search_manuals`, một task U6a trước T148. Task đó là T172; T148 `depends:` T172, tool không bắt `OSError`, tên `MANUALS_UNREADABLE` bỏ |
| R-8 | T166 chờ T54, T161 không cùng lượt với T34, T44: ba chỗ đợt 1b dựa vào task đợt 0 còn mở | Vòng build ưu tiên T51 → T54 trước M14; T161 là task cuối |
| R-9 | Giữa T158 (handler xếp job `requester_reply`) và T162 (runner nhận `communication_name`) nhánh có handler mà runner chưa nhận tham số | `hooks.py` chỉ móc handler ở T161, sau T164; trước đó không sự kiện thật nào gọi handler mới |
| R-10 | Khi Helpdesk bật gửi ngay, lỗi ở bước (7)–(8) của đóng F làm thông báo gửi hai lần (m-3 của `arch-review-design-w1b-r2.md:81`) | Rủi ro đã nhận; ghi As-Built; kiểm R-1 U-1..U-7 trước khi bật `close_silent_f_enabled` |
| R-11 | Test hai kết nối DB và test commit thật (T144, T146 qua `write_bot_action`) trên site dùng chung | `tearDown` xóa bản ghi đã commit; chạy trong một lần giữ khóa site |

## Walking skeleton (cỡ L)

Bộ khung của feature là T1 (đã tick ở đợt 0). Đợt 1b không thêm bộ khung thứ hai. Lát đầu-cuối đầu tiên của từng đơn vị: T137 (U2: phiếu ra bộ phận loại trừ dừng sau một lời gọi model), T162 (U6b: thư của người tạo → một lần chạy), T171 (U8).

## Trọng tâm review

1. T133: dòng chỉ trỏ tới phiếu loại trừ qua Link tĩnh trên DocType có cặp động (`test_static_link_on_dynamic_doctype_also_filtered`); Task có `ai_ticket` NULL vẫn hiện (`test_empty_ticket_link_row_still_listed`).
2. T134: sửa bản ghi của phiếu thường để chuyển nó sang phiếu loại trừ, gồm Task đổi `ai_ticket` (`test_update_moving_record_into_excluded_ticket_refused`).
3. T137: lần phân loại lại ra bộ phận loại trừ không để lại comment hướng (`test_reclassified_into_excluded_team_stops`); bộ phận loại trừ thắng dưới ngưỡng.
4. T146: lỗi sau khi đã gửi thông báo gỡ được cả Communication và Email Queue rồi lần sau đóng đúng một lần (`test_failure_after_notice_rolls_back_then_once`).
5. T162, T163: tin thứ hai của người tạo đến lúc job đầu đang chạy không mất (`test_message_during_run_not_lost`); câu hỏi qua email là lần hỏi duy nhất, 0 comment hỏi dự phòng (`test_below_threshold_email_question_is_the_one_ask`).

## Gộp vào tasks.md

Tech-lead build làm ở đầu một vòng, khi không dev nào đang ghi `tasks.md`:

1. Áp bảng "Sửa dòng task cũ khi gộp" của `tasks-w1b.md` vào các dòng T105, T89, T76 và chuỗi `prompts.py` (T72, T78, T79, T82, T106, T107); task nào đã tick thì ghi điều kiện đó vào dòng progress của T126 thay vì sửa dòng task.
2. Chép từ dòng tiêu đề mục "Gộp `develop` lần hai" tới hết `tasks-w1b.md` vào cuối `tasks.md`; không đổi số.
3. Thêm một dòng "chèn 6" vào khối tiến độ của `tasks.md`, dẫn `plan-w1b.md`, `arch-impact-chg-002.md`.
4. Kiểm `grep -cE '^- \[[ x]\] T[0-9]+' docs/team/features/FEAT-007/tasks.md` = 171 (124 hiện có + 47 của file này). Khác 171 → dừng, không gọi dev.

## Việc cần team-leader

- R5-5 giữ tới khi T137 merge; kiểm bằng `git merge-base --is-ancestor <SHA của T137> develop` trước mọi lần merge `team/FEAT-007` → `develop`.
- T126 chờ mã CHG-002 ở `develop`; theo dõi `team.py status CHG-002` mỗi lần vòng build trả về. CI-24: sau T126 ghi một dòng vào `note-to-chg-002-session.md`.
- R-3: Đã phán ở `design-w1b-fixes-1.md` điểm 1; câu rủi ro còn lại → analyst (`--amend`), chặn nghiệm thu AC-9, không chặn T137. Người không nhận rủi ro đó → `DESIGN_CONFLICT` với ADR-037 QĐ 2 (team-leader → architect).
- R-7: Đã phán ở `design-w1b-fixes-1.md` điểm 2: bỏ riêng file hỏng ở `knowledge.search_manuals`, một task U6a trước T148 (T172).
- Hệ quả người dùng thấy, đưa vào danh sách câu hỏi không chặn và As-Built nếu chưa có: `run_id` là khóa sự kiện nên một tin của người tạo bị bỏ qua vì `daily_limit` hoặc `not_sendable` không được chạy lại hôm sau (m-5 của `arch-review-design-w1b-r2.md:81`); báo cáo trên Task và mọi DocType có Link tới phiếu không chạy được qua bot (C-T15-5, T150 có ca `Task`).
- Kế hoạch đợt 2 chỉ lập sau T126 và sau khi designer sửa S-4, S-6, S-7 của `design-addendum-3-w2.md`.
