Feature: FEAT-007
Stage: plan
Author-agent: tech-lead
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. G3 không áp dụng (team.py: chỉ G5). -->

# Plan FEAT-007 — đợt 1a (task chèn, U1, U3, U4b)

Bổ sung cho `plan.md` (đợt 0), không thay nó. 61 task ở `tasks-w1.md`: T63–T119 trừ T90 (đã xóa, nhập vào T56; số không cấp lại) và năm task chèn T120–T124. Đợt 1b (U2, U6b, U8) và đợt 2 (U7a, U7b, U8 AC-64, U5b) chưa lập.

Sửa 1 (2026-11-15), theo ba tài liệu đến sau bản đầu: `arch-ruling-r5.md` (R5-1..R5-16: thứ tự `runner.py`, một lần gộp `develop` ở T56), `design-w0-fixes-4.md` (điểm 3 → T120, điểm 5 → T121), `design-w0-fixes-5.md` (điểm 1 → T122, điểm 2 → dòng T53, T54 của đợt 0, điểm 4 → T123). Hai file thiết kế đó thắng `design.md`, `design-w0-fixes-3.md` (K-4) và `design-addendum-1-U6b.md:300` ở đúng các dòng chúng nêu; kế hoạch không chép chúng vào `design.md`.

Sửa 2 (2026-11-15), theo `design-w0-fixes-6.md` (phán R-9): hàm tách dòng người nhận sống ở `erp_ai/agent/text_lines.py`. Dòng T53, T54 của đợt 0 đổi theo bảng "Sửa dòng task cũ khi gộp"; thêm T124 (controller `erp_ai_setting.py` chuyển sang `filled_lines` của module đó); T72 thêm `depends:` T124. `design-w0-fixes-6.md` thắng `design-w0-fixes-5.md` ở dòng 48 và dòng 59 của file đó; phần còn lại của điểm 2 giữ nguyên.

Sửa 3 (2026-11-15, tech-lead build đầu vòng 9), theo quyết định 01:31 (a) của team-leader (`journal-part17.md`): T124 xuống cuối chuỗi `erp_ai_setting.py`, `depends: T53, T87`; T72 trở lại `depends: T56, T19, T64` (không chờ T124); chuỗi chủ file: chuỗi U0 → T56 → T32 → T63 → T64 → T72 → T87 → T124. Dòng này thắng chữ "T72 thêm `depends:` T124" của Sửa 2.

Đầu vào đã đọc: `design-addendum-1-U1.md`, `design-addendum-1-U3.md`, `design-addendum-1-U4b-U8.md` mục 3, `design-addendum-1-U4b-U8-fixes.md` mục R1–R4, `design-addendum-3-w1.md`, `arch-review-design-w1a.md`, `arch-review-design-addendum-3.md` mục 1, 4, 5, 6, `arch-review-addendum-3.md` mục 5–7, `spec-addendum-3.md` mục 3–4, `spec-addendum-4.md` mục 7, ADR-037 mục Quyết định và Ràng buộc. Chưa đọc từng dòng: `design-addendum-1-U4b-U8.md` mục 1, 2, 4–6 và `design-addendum-1-U4b-U8-fixes.md` Fix 1–12; các task U4b dẫn số dòng của những mục đó làm nguồn chữ, dev đọc trực tiếp.

## Thứ tự

1. Đợt 0 chạy tiếp tới hết chuỗi U0 (T14 → T20, T21 → T22 → T60 → T23). Cùng lúc, bốn task chèn của đợt 0 chạy trước T56 và trước mọi task U6b: T121 (sau T38), T122 (sau T36), T120 → T123 (sau T39). T53 (tạo `text_lines.py`) không còn bị giữ: R-9 đã phán.
2. T56 (gộp đầu `develop`, ≥ `cf69b57`, có FEAT-004 và FEAT-005; SHA ghi ở `Receives`) → T57 (INT-1). T56 chờ T20, T23, T38, T59, T121, T122. Hai task này đi sớm hơn kế hoạch đợt 0: xem `tasks-w1.md` mục "Sửa dòng task cũ khi gộp".
3. Task chèn sau T56: T63 → T64, T65. T124 ở cuối chuỗi `erp_ai_setting.py`: sau T87 (U3) và sau T53.
4. U1: T66–T83, một mình trên các file lõi (`w1a.md:87`).
5. U3: T84–T89, T91 → T92 → T93 ngay sau U1 (T91, T92 trong chuỗi `runner.py` ngay sau T82, trước T108); T94 sau T66.
6. U4b: T95–T119.

`runner.py`: U1 → U3 → U4b → U2 (đợt 1b) → U6b, theo `arch-ruling-r5.md` R5-1..R5-6. Phán quyết đó thay thứ tự ở `arch-review-design-w1a.md:89-92`, `design-addendum-1-U4b-U8-fixes.md:328` và `arch-impact.md:185`; vùng hàm của từng đơn vị ở các bảng đó giữ nguyên.

## Nhóm song song

Trần `limits.max_parallel_dev` = 2. Hai làn, mỗi vòng lấy task sẵn sàng đầu làn; hai task cùng một dòng của bảng "Một file, một chủ" không bao giờ cùng lượt.

| Giai đoạn | Làn A | Làn B |
|---|---|---|
| Đợt 0, trước T56 (xen với chuỗi U0 trong phần dev = 2) | T121 (`source.py`; sẵn sàng ngay, T38 đã tick) → T120 → T123 (`redact.py`, `knowledge.py`; sau T39) | T122 (`test_architecture.py`; sẵn sàng ngay, T36 đã tick; không cùng lượt với task đợt 0 nào có file đó) |
| Sau T57 | T66 → T67 → T68 → T69 → T70 → T71 (`policy.py`) | T63 → T64 → T72 → T78 → T79 (cấu hình, phân loại, prompt); T65; T73 |
| U1 giữa | T74 → T75 → T80 → T81 → T82 → T83 (`runner.py`) | T76 → T77 (`registry.py`); T84 (chỉ chờ T56, T35) |
| U3 | T91 → T92 (`runner.py`, ngay sau T82) | T85 → T86 → T87 → T124 (T124 chờ thêm T53); T88 → T89 → T93 (T93 sau T92); T94 |
| Đầu U4b | T106 → T107 | T95 → T96; T97; T98 → T99 → T100 → T101 → T102 → T103 → T104 → T105 |
| U4b runner | T108 → T109 → T110 → T111 → T112 → T115 → T116 → T117 → T113 → T118 | T114 (sau T113); T119 cuối |

## Ràng buộc chung

Chép nguyên văn từ thiết kế; mọi task dùng đúng các tên này.

- `policy.py` (U1): `PermissionSwitches(unrestricted, record_tools, act_now, code_change, one_click_approval)`; `PERMISSION_SWITCH_FIELDS` thứ tự (1)..(5); `permission_switches(settings)`; `month_spend_usd(now=None)`; `is_over_budget(settings, now=None)`; `effective_level(settings, *, over_budget: bool)`; `category_level_cap(settings, category)`; `main_path_level(settings, permission_level, category)`; `confidence_threshold(settings)`; `is_below_confidence(confidence_pct, threshold, *, has_instructor, act_now)`; `latest_classification(ticket_name)`; `site_environment(settings=None)`; `RUN_LIMIT_TRIGGERS`. `DEFAULT_CONFIDENCE_THRESHOLD = 70`; `UNKNOWN_CATEGORY_LEVEL = "L1"`; `DEFAULT_SITE_ENVIRONMENT = "production"`; `SITE_ENVIRONMENTS = ("production", "test")`.
- Biên của vị từ ngưỡng: 69 < 70 → dưới; 70 → không dưới; `None` → dưới; người ra lệnh ∧ công tắc (3) bật → không bao giờ dưới.
- `registry.py` (U1): `GrantInputs(effective_level, main_path_level, has_instructor, switches, over_budget=False, below_threshold=False)`; `Grant(specs, change_block, record_block, unrestricted_block, act_now_block, ask_only_block)`; `grant(inputs)` là hàm cấp duy nhất; `ASK_TOOL_NAMES = frozenset({"post_comment"})`; `UNRESTRICTED_GROUP = "site_unrestricted"`.
- `prompts.py` (U1): `RULE_6_ACT`, `RULE_6_ASK`, `NO_OK_APPROVAL`, `PROMPT_CONFLICT_PAIRS` (P-1..P-5, P-7, P-8, P-9), `ASK_ONLY_BLOCK`; `NO_OK_APPROVAL` có ở mọi tổ hợp cờ; `prompts.py` không đọc cấu hình.
- `classification.py`: khóa JSON `do_tin_cay_pct`, `Classification.confidence_pct: int`, 0..100. Cột log `predicted_confidence_pct`: -1 = không biết.
- `run_log.py` (U3): `ACTION_KEYS = ("tool", "doctype", "name", "ok", "value_before", "value_after", "instructor")`; `SECRET_MASK = "[đã ẩn]"`; `NO_REASON = "tool không nêu lý do"`; `ENTRY_TYPES = ("classify", "reason", "skip", "change", "bot_action")`; `BOT_ACTION_TRIGGERS = ("setting_save", "scheduled_job")`; `TOOL_PERMISSION_SWITCH = "permission_switch"`; dòng `bot_action` có `cost_usd = 0`.
- `change_decision.py` (U3): `ONE_CLICK_OFF = "Duyệt một lần bấm đang tắt. Mở đề xuất và dùng nút Duyệt hoặc Từ chối trên form (có bước xác nhận)."`; `OPEN_PROPOSAL_LABEL = "Mở đề xuất để Duyệt hoặc Từ chối"` ở `propose_change.py`.
- `write_ticket.py` (U4b): `GUIDANCE_MARKER = "<!-- erp_ai:huong-xu-ly -->"` ở dòng 1 của comment hướng; `SECTION_DONE, SECTION_PENDING, SECTION_DECIDE = "Đã làm", "Chờ duyệt", "Cần ai quyết"`; `locked_rows(ticket_name, doctype, filters, fields=("name",))` là chỗ duy nhất có `for_update=True`; `locked_count` gọi nó; chế độ "đưa hướng" chỉ đọc từ `collecting(run_id)`, không có trường trên `ToolContext`; `collect(run_id, section, line)` nhận chữ thô, thoát HTML đúng một lần ở chỗ đổ ra comment; dòng "Chờ duyệt" chỉ thêm trong `propose_change._insert`.
- Hướng phụ thuộc: `propose_change` → `write_ticket`; `write_ticket` không import `propose_change`, `catalog`, `catalog_tools`, `runner`; `policy` không import `run_log`; không module nào dưới `erp_ai/agent/**` import `erp_ai.erp_ai_agent.*`.
- ADR-024 trên nền đã có FEAT-005 (`arch-ruling-r5.md` R5-13, R5-14, R5-16): khóa `"<tool>#<n>"` và trước/sau theo dòng của `_record_snapshot` giữ nguyên (T91); `write_entry` giữ `insert` và `commit` trong cùng lời gọi, mọi phép kiểm chạy trước `insert` (T85, T93); `post_guidance` được gọi trong khối `try` mở sau `frappe.db.savepoint(REASON_TURN_SAVEPOINT)`, trước `write_entry` của lượt cuối, và các hàm của `write_ticket.py` chạy trong lượt không gọi `frappe.db.commit` (T99–T104, T116).
- `_classify` sau U4b (R5-1..R5-3): đúng một lời gọi `parse_classification(` trong `runner.py`; thứ tự parse → [ô của U2, để trống] → chốt dưới ngưỡng → chọn chế độ → khóa định tuyến → `_route`; dạng trả `(proceed, classification, context)`; lời gọi `decide_route` giữ tham số từ khóa `is_excluded_team=`.
- `redact.py` (T120): luật K-4, K-4a, K-8 theo `design-w0-fixes-4.md:24-26`; chữ ký `redact_secrets`, `is_secret_key`, `SECRET_PATTERNS` không đổi; nơi gọi che trước rồi cắt, không giải thực thể HTML trước khi che.
- `source.py` (T121): `resolve_safe_path(rel)` trả `None` khi đích nằm hẳn trong `manuals_root()` và không phải thư mục có sẵn; mã từ chối phía ghi vẫn là `PATH_INVALID`.
- `knowledge.py` (T123): `text_words(text) -> set[str]`, `plain_text(html) -> str`; `tokenize` giữ `QUERY_MAX_WORDS` = 8 và chỉ dùng cho câu tìm.
- Lệnh: chỉ các ô `cmd.test_one`, `cmd.test`, `cmd.migrate`, `cmd.lint`, `formatters_by_ext` của profile, chạy qua khóa site theo `plan.md` mục "Chạy test từ worktree trên site dùng chung".

## Touchpoint → task

| Touchpoint (nguồn) | Task |
|---|---|
| `erp_ai/agent/policy.py` (U1 3.1, C-1, C-3) | T66, T67, T68, T69, T70, T71 |
| `erp_ai/agent/tools/registry.py` (U1 3.2) | T76, T77, T82 |
| `erp_ai/agent/authority.py` (U1 3.3) | T73, T74, T80 |
| `erp_ai/agent/queue.py`, `erp_ai/handlers.py` (U1 3.4) | T75 |
| `erp_ai/agent/prompts.py` (U1 3.5, 3.6; w1 U1-1..U1-8) | T72, T78, T79, T82 |
| `erp_ai/agent/classification.py` (U1 3.6) | T72 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py` (C-4) | T72 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json` mô tả `prompt_override_classify` (`design-w1-fixes-4.md` Điểm 2) | T72 |
| `erp_ai/agent/runner.py` (U1 3.7) | T67, T74, T75, T80, T81, T82 |
| `erp_ai/tests/test_architecture.py` (U1) | T70, T71, T74, T80, T83 |
| `erp_ai/agent/test_prompts.py` (mới) | T78 |
| `erp_ai/agent/run_log.py` (U3 3.1) | T84, T85, T86, T93 |
| `erp_ai/agent/runner.py` (U3 3.2) | T91, T92 |
| `erp_ai/change_decision.py` (U3 3.3) | T88 |
| `erp_ai/agent/tools/propose_change.py` (U3 3.4) | T89 |
| `erp_ai_change_proposal.js` (U3 3.5) | không sửa, không task |
| `erp_ai_setting.py` (U3 3.6, C-9) | T87 |
| `erp_ai/tasks.py` (U3 3.7) | T94 |
| `erp_ai_log.json` (U3 3.8) | T85 |
| `erp_ai/handlers.py` (U4b 3.1, Fix 1; ADR-037 QĐ 5) | T95, T96, T114 |
| `erp_ai/agent/tools/write_ticket.py` (U4b 3.2; w1 mục 1, U4b-1..U4b-9) | T98, T99, T100, T101, T102, T103, T104 |
| `erp_ai/agent/tools/route_ticket.py` (Fix 5) | T97 |
| `erp_ai/agent/prompts.py` (U4b 3.3; U4b-10; ADR-037 QĐ 2) | T106, T107 |
| `erp_ai/agent/runner.py` (U4b 3.4; U4b-11..U4b-16; ADR-037) | T108, T109, T110, T111, T112, T113, T115, T116, T117 |
| `erp_ai/agent/tools/propose_change.py` (AD3-5, AD3-11) | T105 |
| `erp_ai/tests/test_architecture.py` (ADR-036, ADR-037) | T99, T105, T119 |
| `erp_ai/agent/hard_bans.py` (AR3-3) | T63 |
| `erp_ai_setting.json` mô tả (phụ lục 4 mục 7) | T64 |
| `erp_ai/agent/tools/site_api.py` (quyết định (d)) | T65 |
| `erp_ai/agent/redact.py`, `test_redact.py`, `test_knowledge.py` (`design-w0-fixes-4.md` điểm 3) | T120 |
| `erp_ai/agent/tools/source.py`, `test_source.py`, `test_change_guard.py` (`design-w0-fixes-4.md` điểm 5) | T121 |
| `erp_ai/tests/test_architecture.py` (`design-w0-fixes-5.md` điểm 1) | T122 |
| `erp_ai/agent/knowledge.py`, `test_knowledge.py` (`design-w0-fixes-5.md` điểm 4) | T123 |
| `erp_ai/agent/daily_report.py`, `test_daily_report.py` (`design-w0-fixes-5.md` điểm 2; nơi đặt hàm theo `design-w0-fixes-6.md`) | T53, T54 của đợt 0 (bảng "Sửa dòng task cũ khi gộp") |
| `erp_ai/agent/text_lines.py`, `test_text_lines.py` (`design-w0-fixes-6.md` phán quyết 1; file mới) | T53 của đợt 0 |
| `erp_ai_setting.py`: import `filled_lines` từ `erp_ai.agent.text_lines`, xóa `_filled_lines` (`design-w0-fixes-6.md` phán quyết 2) | T124 |
| `erp_ai/agent/tools/read.py`, `test_read.py` (`design-w0-fixes-5.md` điểm 4, hai test `:94-95`) | chưa lập (task `search_resolved_tickets` của U6b, đợt 1b; `depends:` T123) |
| `design.md:308`, `:309`, `:433`, `:487`, `:489`, `:492`, `design-addendum-1-U6b.md:300`, `design-w0-fixes-3.md:164` (sửa chữ) | không task: task dẫn thẳng tới `design-w0-fixes-4.md`, `-5.md`; chép vào As-Built ở `/team:asbuilt`, kể cả giới hạn K-4a |

Phần của `design-addendum-3-w1.md` không thuộc đợt 1a: mục 4 (U8-1..U8-3) và mục 5 (U6b-1) sang đợt 1b.

## Một file, một chủ

Các task trên cùng một dòng chạy nối tiếp theo thứ tự ghi; `depends:` đã mang phần lớn thứ tự, chỗ nào chưa có thì tech-lead build giữ theo bảng này.

| File | Chuỗi task |
|---|---|
| `erp_ai/agent/policy.py`, `test_policy.py` | T66 → T67 → T68 → T69 → T70 → T71 |
| `erp_ai/agent/runner.py` | T56 → T67 → T74 → T75 → T80 → T81 → T82 → T91 → T92 → T108 → T109 → T110 → T111 → T112 → T115 → T116 → T117 → T113 |
| `erp_ai/agent/test_agent_runner.py` | T56 → T72 → T80 → T81 → T82 → T91 → T92 → T108 → T110 → T111 → T115 → T116 → T117 → T113 → T118 |
| `erp_ai/agent/test_runner_routing.py` | T72 → T108 → T109 → T112 → T115 |
| `erp_ai/tests/test_architecture.py` | T122 → T56 → T70 → T71 → T74 → T80 → T83 → T85 → T88 → T89 → T93 → T99 → T105 → T119 |
| `erp_ai/agent/prompts.py`, `test_prompts.py` | T72 → T78 → T79 → T82 → T106 → T107 |
| `erp_ai/agent/tools/registry.py`, `test_registry.py` | T76 → T77 → T82 |
| `erp_ai/agent/authority.py`, `test_authority.py` | T73 → T74 → T80 |
| `erp_ai/handlers.py`, `tests/test_handlers.py` | T75 → T95 → T96 → T114 |
| `erp_ai_setting.py`, `erp_ai_setting.json`, `test_erp_ai_setting.py` | chuỗi U0 → T56 → T32 → T63 → T64 → T72 → T87 → T124 (T124 còn chờ T53 vì cần `text_lines.py`); riêng `erp_ai_setting.json`: T64 → T125 → T72 (`design-w1-fixes-4.md` Điểm 2) |
| `erp_ai/agent/text_lines.py`, `test_text_lines.py` | T53 (T54 và T124 chỉ import, không sửa) |
| `erp_ai/tests/test_doctype_descriptions.py` | T56 → T64 → T85; T43, T49 của đợt 0 không cùng lượt với task nào ở dòng này |
| `erp_ai/agent/tools/source.py`, `test_source.py` | T38 → T121 → T56 (R5-8) |
| `erp_ai/agent/tools/test_change_guard.py` | T121 |
| `erp_ai/agent/redact.py`, `test_redact.py` | T35 → T120 |
| `erp_ai/agent/knowledge.py`, `test_knowledge.py` | T37 → T39 → T120 (chỉ `test_knowledge.py`) → T123 |
| `erp_ai/agent/run_log.py`, `test_run_log.py` | T84 → T85 → T86 → T93 |
| `erp_ai/agent/tools/write_ticket.py`, `test_write_ticket.py` | T98 → T99 → T100 → T101 → T102 → T103 → T104 |
| `erp_ai/agent/tools/propose_change.py`, `test_propose_change.py` | T89 → T105 |
| `erp_ai/agent/tools/site_api.py`, `test_site_api.py` | T65 → T82 |
| `erp_ai/agent/hard_bans.py`, `test_hard_bans.py` | T57 → T63 |
| `erp_ai/tasks.py`, `tests/test_tasks.py` | T94 |
| `erp_ai/change_decision.py`, `test_change_decision.py` | T88 |
| `erp_ai/agent/tools/route_ticket.py`, `test_route_ticket.py` | T97 |
| `erp_ai/agent/classification.py`, `test_classification.py`, `eval/test_run_eval.py` | T72 |
| `erp_ai/agent/queue.py`, `test_queue.py` | T75 |
| `erp_ai_log.json`, `test_erp_ai_log.py` | T85 |

Task `[migrate]` của đợt 1a: T64, T85 (và T56 là lần gộp duy nhất, có `cmd.migrate`).

## Điều kiện → task

Nguồn: `arch-review-design-w1a.md` mục 3 (C-1..C-10), `arch-review-design-w1b-r2.md:75-77` (E-1..E-3), `arch-review-addendum-3.md` mục 5, 7 (AR3-3, AR3-11), `arch-review-design-addendum-3.md` mục 6 (AD3-1..AD3-11), `arch-review-w0-fixes-3.md` mục 4, 5 (thứ tự `policy.py`). `arch-review-design-w1b.md` không có điều kiện đánh số C-n riêng; các phán quyết của nó đã vào `design-addendum-1-U4b-U8-fixes.md` (Fix 1–12).

| Điều kiện | Đơn vị | Task | Ghi chú |
|---|---|---|---|
| C-1 | U1 | T70 | `site_environment` và ba hằng ở `policy.py` |
| C-2 | U1 | T70 (luật và danh sách cho phép), T83 (`POLICY_FIELDS` không có `site_environment`) | dev của T70 grep `site_environment` trên nhánh đã gộp |
| C-3 | U1 | T71 | phần "U6b nối một phần tử" ở đợt 1b |
| C-4 | U1 | T72 | khóa prompt và phần tử `PROMPT_REQUIRED_MARKERS` cùng commit |
| C-5 | U1 (U2) | T81 | nhánh `(False, classification, context)` của U2 ở đợt 1b |
| C-6, C-7, C-8 | U2 | chưa lập (đợt 1b) | cùng C-U2-1, C-U2-2 của `arch-review-w0-fixes-3.md` mục 5 |
| C-9 | U3 | T87 | |
| C-10 | U6a (file), U3 dùng | T35 của đợt 0, T84 chờ T35 | T35 đã merge (`a805842`); ngày 2026-11-15 `git grep -c "def is_secret_key" team/FEAT-007 -- erp_ai/agent/redact.py` = 1 |
| E-1 | U6b | chưa lập (đợt 1b) | phía U4b đã có hợp đồng: `asked_in_run`, `mark_asked`, `REASON_ONE_ASK` ở T100 |
| E-2 | U6b | chưa lập (đợt 1b) | phía U4b: `NOTICE_TRIGGERS` là danh sách cho phép 3 khóa ở T110, `_notice` không có điều kiện cấm theo trigger |
| E-3 | U6b | chưa lập (đợt 1b) | task `reply.py` của đợt 1b ghi `depends: T100` |
| AR3-3 | task chèn | T63 | sau T57 (INT-1) |
| AR3-11 | plan | T63, T64; bảng "Touchpoint → task" | U7 (đợt 2) phụ thuộc thêm U4b và T63 |
| AD3-1 | U4b | T112 (`_route` khóa phiếu, một lần), T113 (phân loại lại), T114 (dòng tham chiếu) | |
| AD3-2 | U4b | T116 | |
| AD3-3 | U4b | T119 (luật `test_write_ticket_imports_no_proposal_or_catalog_module`); tên theo "Ràng buộc chung" | phần w2 ở đợt 2 |
| AD3-4 | U4b | T103, T116, T117 | ba chỗ đổ dòng gom |
| AD3-5 | U4b | T105, T116 | nhánh trùng và dòng loại bản ghi của U7a ở đợt 2 |
| AD3-6 | U4b | T99 | |
| AD3-7 | U7 | chưa lập (đợt 2) | AD3-8, AD3-9, AD3-10 cũng thuộc đợt 2 |
| AD3-11 | U4b | T105 (`propose_change.py`), T114 (`handlers.py`), T106 (hàm dựng request phân loại) | phần U7a ở đợt 2 |
| Thứ tự `policy.py` (C-T15-1, `arch-review-w0-fixes-3.md:64`) | T15 → U1 | T15 (đợt 0) → T66 → … → T71 | T56 chờ T20, T20 nằm sau T15 trong chuỗi U0, nên T66 luôn sau T15. T66–T71 không sửa thân `ticket_link_fieldnames`, `is_ticket_content_doctype`; cần sửa → `DESIGN_CONFLICT` |
| R5-1, R5-2, R5-3 | U4b | T108 (R5-2), T109 (R5-3), T113 (R5-1, R5-3), T115 (R5-2, R5-3) | hai phép grep và đoạn `_classify` dán vào review |
| R5-4, R5-6 | U2 | chưa lập (đợt 1b) | task U2 sửa `runner.py`/`test_agent_runner.py` `depends:` T113 và T118; `handlers.py` → T114; `site_api.py` → T82; `policy.py` → T71; không "rebase" |
| R5-5 | — | team-leader | không merge `team/FEAT-007` → `develop` từ khi T108 merge tới khi task `runner.py` của U2 merge |
| R5-7, R5-8, R5-9, R5-10, R5-11 | gộp | T56 (bảng "Sửa dòng task cũ khi gộp" của `tasks-w1.md`) | R5-7 do tech-lead làm trước khi gọi dev |
| R5-12 | gộp | T57 | không đổi `files:`, `Expect` |
| R5-13 | U3 | T91 | `test_tasks` trong `Expect` |
| R5-14 | U3 | T85, T93 | |
| R5-15 | U3 → U4b | T110 `depends:` T93 | |
| R5-16 | U4b | T99–T104 (không commit), T116 (chỗ gọi và một ca test), M10 (grep) | |
| `design-w0-fixes-4.md` điểm 3, điểm 5 | U6a | T120, T121 | rủi ro "thư mục kho đã lưu bị xóa khỏi đĩa" (`design-w0-fixes-4.md:73`), đọc mã ngày 2026-11-15: job áp **không** tạo thư mục cha. (1) `file_writer.write_atomic` (`erp_ai/agent/changes/file_writer.py:36`, giống nhau trên `develop` và `team/FEAT-007`) gọi `tempfile.mkstemp(dir=os.path.dirname(full_path))`, thư mục cha thiếu thì ném lỗi, không có `makedirs`/`mkdir` nào trong `erp_ai/**` ngoài test trên cả hai nhánh; `_apply_code` (`develop:apply_job.py:415`) chỉ ghi qua hàm đó. (2) Lúc đề xuất, `propose_new_file` từ chối `NO_PARENT` khi thư mục cha chưa có (`develop:propose_change.py:196-197`; dòng này vào nhánh ở T56). (3) Thư mục được dựng lại giữa lúc đề xuất và lúc áp thì `manuals_root()` có giá trị trở lại và `check_write_path` chạy lại ở job áp (`develop:apply_job.py:379`) từ chối theo T121. Theo điều kiện của designer ("nếu có → chuyển architect") thì không phải chuyển. Ngoài phạm vi câu hỏi: đề xuất loại lệnh (`_apply_command`) do người duyệt, không đi qua `check_write_path` |
| `design-w0-fixes-5.md` điểm 1, điểm 4 | U6a | T122, T123 | hai test `test_read.py` của điểm 4 sang U6b (đợt 1b) |
| `design-w0-fixes-5.md` điểm 2, `design-w0-fixes-6.md` | U5a | T53, T54 (đợt 0), T124 | R-9 đã phán: hàm ở `erp_ai/agent/text_lines.py`; `_filled_lines` và `filled_lines` cùng tồn tại (cùng hành vi) từ khi T53 merge tới khi T124 merge |

Không điều kiện nào của U1, U3, U4b còn thiếu task.

T43 và T49 chạm `erp_ai/tests/test_doctype_descriptions.py`, một file của T56 (hàng T56 của `tasks-w1.md` đã sửa theo câu này). Task đợt 0 chạm file của T56 phải merge trước khi gọi dev T56 hoặc cắt nhánh sau T56: T121 (`source.py`, `test_source.py`) và T122 (`test_architecture.py`) merge trước (T56 `depends:` chúng), T32 (`erp_ai_setting.py`) cắt nhánh sau T56, T43, T49 (`test_doctype_descriptions.py`), và mọi nhánh task đang mở trên tám file của T56 lúc đó. T43, T49 không chạy cùng lượt với T64, T85 (cùng `test_doctype_descriptions.py`).

## AC → task

| AC | Task |
|---|---|
| AC-1 (hồi quy M4, đọc công tắc) | T66, T76 |
| AC-3 | T66, T76, T82, T83 |
| AC-4 (dòng nhật ký, điều kiện hằng ngày) | T87, T94 |
| AC-6 | T77, T78, T79, T82 |
| AC-7 | T67, T77, T82 |
| AC-10 | T84, T85, T86, T87, T91, T92, T93, T110, T116 |
| AC-11 | T88, T89 |
| AC-13 | T73, T75, T80 |
| AC-17 | T108 |
| AC-19, AC-25, AC-27, AC-28 (phần runner) | T108, T109 |
| AC-21 | T95, T96, T98, T108 |
| AC-22 | T69, T72, T77, T81, T82, T97, T98, T100, T111 |
| AC-23 và AC-23 `[changed]` | T101, T109, T110, T115, T116, T117, T118 |
| AC-24 | T106, T107, T108 |
| AC-29 `[changed]` (ca bảng con, chữ mô tả) | T63, T64 |
| AC-31, AC-32 | T68, T77 |
| AC-41 `[changed]` (phần runner; hai test của U6b ở đợt 1b) | T113 |
| AC-61 | T67, T82, T110 |
| AC-65 | T102, T103, T104, T105, T107, T113, T115, T116, T117, T118, T119 |
| AC-66 (a) và phần prompt | T78, T82, T104, T118 |
| AC-67 (phần đợt 1: dòng "Chờ duyệt") | T105 |
| NFR-6, AC-46, AC-50 (giá trị trần chứa `,` `;` `&` bị che hết) | T120 |
| AC-47 (câu cuối), AC-45 (bot không ghi được file vào kho HDSD) | T121 |
| AC-50 (đường bỏ quyền duy nhất nằm ngoài `tools/`) | T122 |
| AC-48, AC-46 (so với mọi từ của tài liệu; phần `knowledge.py`) | T123 |
| AC-51, AC-52 (người nhận đọc theo dòng) | T53, T54 (đợt 0, dòng sửa khi gộp) |

Không thuộc đợt 1a: AC-62, AC-63 (U8); AC-66 (b), AC-67 phần còn lại, AC-68, AC-69 (U7a, U7b, đợt 2); AC-5, AC-8, AC-9 (U2).

## Mốc kiểm

Chính sách N-6 của `tasks.md` giữ: sau mỗi merge chạy `cmd.test_one` của task và `erp_ai/tests/test_architecture.py`, cùng `cmd.lint`; `cmd.test` cả bộ chỉ ở mốc.

| Mốc | Sau | Kiểm |
|---|---|---|
| M7 | T57 | Trước `cmd.test`: phép diff và `comm -23` của R5-9 đã rỗng, năm module của R5-11 đã xanh (ghi ở progress của T56). Rồi `cmd.migrate` và `cmd.test` xanh trên nền mới (đây là mốc "sau chuỗi U0" của `plan.md` dời về sau T56, và thay mốc "cả bộ ở M8" của T90 cũ) |
| M8 | T83 (hết U1) | `cmd.test` xanh. Luồng tay: lưu ERP AI Setting với cả 5 công tắc tắt, tạo một phiếu ở L1 → bộ tool bằng bản nền |
| M9 | T93 (hết U3, trừ T94) | `cmd.test` xanh. Luồng tay: bật rồi tắt một công tắc → hai dòng `bot_action` trên ERP AI Log |
| M10 | T104 | `cmd.test_one` của `test_write_ticket`, `test_propose_change`, `test_architecture` xanh; `git grep -c "frappe.db.commit" team/FEAT-007 -- erp_ai/agent/tools/write_ticket.py` = 0 (R5-16) |
| M11 | T119 (hết U4b) | `cmd.test` xanh. Luồng tay trên `miyano`: tạo phiếu → 1 comment hướng; `@ai` hai lần → vẫn 1 |

## Rủi ro

| # | Rủi ro | Cách giữ |
|---|---|---|
| R-1 | Hết: FEAT-005 đã ở `develop` (`464063f`); T90 nhập vào T56 theo quyết định 00:59 (b) và `arch-ruling-r5.md` mục 2 | — |
| R-2 | T56 gộp `develop` khi chuỗi U0 chưa xong hẳn | T56 chỉ chạy khi T20, T23, T38, T59, T121, T122 đã tick và không task nào đang mở trên tám file của nó (gồm T43, T49 trên `test_doctype_descriptions.py`) |
| R-3 | `erp_ai/tests/test_architecture.py` và `runner.py` là hai điểm nghẽn: 12 và 17 task nối tiếp sau T56 (T122 đứng trước T56) | Bảng "Một file, một chủ"; làn B lấy task không chạm hai file đó |
| R-4 | T72 đổi stub ở ba file test lớn; T82 xóa hàm cũ ở sáu file | Hai task này chạy một mình trong lượt của chúng |
| R-5 | Đã phán: `arch-ruling-r5.md`. U2 đến sau U4b trong `runner.py` với điều kiện R5-1..R5-6 | R5-1..R5-3 nằm trong T108, T109, T113, T115; R5-4, R5-6 cho kế hoạch đợt 1b; R5-5 là việc của team-leader |
| R-6 | Test hai kết nối DB (T99, T103, T112) commit thật trên site dùng chung | `tearDown` xóa bản ghi đã commit; chạy trong một lần giữ khóa site |
| R-7 | T65 có thể không có lỗ thật | Task nói rõ lối ra `DONE_WITH_CONCERNS` với test hồi quy |
| R-8 | Tên `later_messages`, `LATER_MESSAGES_MAX = 5`, `reference_classify_row`, `ROUTE_ALREADY_DONE`, và tên test `test_last_turn_log_failure_leaves_no_guidance` (T116, R5-16) do kế hoạch đặt; ADR-037 và phán quyết chỉ nêu hành vi | Ghi ở "Ràng buộc chung" của task; designer đổi tên thì sửa một dòng task |
| R-9 | Đã phán: `design-w0-fixes-6.md`. `filled_lines` sống ở `erp_ai/agent/text_lines.py` (Lõi agent, chỉ thư viện chuẩn); `daily_report` và controller cùng import từ đó, không bên nào import bên kia (`LAYER_RULES`, ADR-001) | T53 tạo module và test của nó, không chạm `erp_ai_setting.py`; T124 đổi controller sau T53 và sau T87 (cuối chuỗi `erp_ai_setting.py`); T72 không chờ T124. T53 không còn bị giữ. Còn lại: hai hàm cùng tồn tại tạm thời giữa T53 và T124; tên test của T124 do kế hoạch đặt |
| R-10 | T121, T122 merge trước T56 (lệnh của team-leader; `design-w0-fixes-4.md:93`) nên lần gộp của T56 phải giữ phần của chúng | Đọc ngày 2026-11-15: `develop` chỉ đổi các dòng logger của `source.py` từ merge-base, không đổi `resolve_safe_path`; thân `check_tools_never_bypass_permissions` giống hệt nhau ở merge-base, `develop` và nhánh, nên hai chỗ sửa mã dự kiến tự gộp. `test_source.py` đã có một khối xung đột; test mới của T121 nằm trong lớp `TestManualsExcluded` chỉ có trên nhánh. `source.py` đã vào `files:` của T56; `Expect` (4), (5) của T56 chạy lại test của T121, T122 sau gộp. R5-7 chạy lại `git merge-tree` trên đầu nhánh lúc đó |
| R-12 | T120 (biểu thức che có phép nhìn trước; T35 cùng file từng mất 5 vòng) kéo dài | T56 không `depends:` T120, T123 (không chung file), nên đợt 1a không bị chặn. Task U6b của đợt 1b `depends:` T120, T121, T123 |
| R-11 | T120, T123 chung `test_knowledge.py` với T39 đang mở ở vòng build 8 | `depends:` T39; không gọi dev T120 khi T39 chưa merge |

## Walking skeleton (cỡ L)

Bộ khung của feature là T1 (đã tick ở đợt 0). Đợt 1a không thêm bộ khung thứ hai. Lát đầu-cuối đầu tiên của đợt là T80 (lần chạy `@ai` đi qua `policy`, `authority`, `registry`, `runner`).

## Trọng tâm review

1. T77, T82: ca "(3) bật một mình" không được cho khối "làm luôn"; ca vượt ngân sách với cả 5 công tắc bật phải bằng đúng bộ L1.
2. T69, T113: phiếu cũ không có `predicted_confidence_pct` (-1 hoặc rỗng) → dưới ngưỡng; lần chạy `@ai` của người ra lệnh khi (3) bật không phân loại lại.
3. T103, T116, T117: giá trị `"<b>&x"` ra comment là `&lt;b&gt;&amp;x` đúng một lần ở cả ba chỗ đổ dòng gom (AD3-4).
4. T116: lối ra `turn == max_turns` vẫn đăng hướng (AD3-2); lần chạy thua khóa không mất dòng đã gom.
5. T85, T87: lỗi ghi dòng `setting_save` làm lưu cấu hình thất bại, không có công tắc đổi mà thiếu dòng (A-U3-8).

## Gộp vào tasks.md

Tech-lead build làm ở đầu một vòng, khi không dev nào đang ghi `tasks.md`:

1. Áp bảng "Sửa dòng task cũ khi gộp" của `tasks-w1.md` vào các dòng T56 (tên, `depends: T20, T23, T38, T59, T121, T122`, `files:` thành 8 file, Receives, Returns, Expect theo R5-7..R5-11), T57 (R5-12), T58, T32, T53, T54.
2. Chép từ dòng `## Task chèn` tới hết `tasks-w1.md` vào cuối `tasks.md`, sau T58; không đổi số. Không có dòng T90.
3. Thêm một dòng "chèn 4" vào khối tiến độ của `tasks.md`, dẫn `plan-w1.md`, `arch-ruling-r5.md`, `design-w0-fixes-4.md`, `design-w0-fixes-5.md`, `design-w0-fixes-6.md`.
4. Kiểm `grep -cE '^- \[[ x]\] T[0-9]+' docs/team/features/FEAT-007/tasks.md` = 123 (62 của đợt 0 + 61 của file này; `arch-ruling-r5.md:109` ghi 118 là trước khi có T120–T124).

## Việc cần team-leader

- R5-5: không merge `team/FEAT-007` → `develop`, và không đưa vào bản phát hành nào, từ khi T108 merge cho tới khi task `runner.py` của U2 merge; kiểm bằng `git merge-base --is-ancestor <commit runner U2> develop`.
- R-9: đã phán (`design-w0-fixes-6.md`, 2026-11-15); không còn việc chờ. T53 gọi dev được; bước đổi controller là T124.
- R-12: T56 không chờ T120, T123 (không chung file). Muốn cả bốn task chèn xong trước T56 thì thêm T120, T123 vào `depends:` của T56 ở bảng "Sửa dòng task cũ khi gộp".
- N-1 của `arch-review-design-w1a.md:46` (mọi `@ai` trên phiếu cũ thành "chỉ hỏi" sau T80–T82) là thay đổi người dùng thấy; đã có trong danh sách câu hỏi không chặn hay chưa thì team-leader kiểm.

## Đầu vòng 9 — việc của tech-lead build

1. Chờ vòng 8 trả về; không dev nào còn ghi `tasks.md`. Đọc dòng tiến độ của `tasks.md` và `git log --oneline develop..team/FEAT-007`; không làm lại task đã tick.
2. Gộp theo mục "Gộp vào tasks.md", bước 1–4: sửa các dòng T56, T57, T58, T32, T53, T54; chép từ `## Task chèn` tới hết `tasks-w1.md` vào sau T58; thêm dòng "chèn 4"; kiểm phép `grep -cE` = 123. Khác 123 → dừng, không gọi dev.
3. T53 không còn bị giữ (R-9 đã phán, `design-w0-fixes-6.md`): không ghi chữ giữ nào vào dòng progress của T53; gọi dev T53 khi `depends:` của nó đã tick, lệnh gọi dẫn `design-w0-fixes-5.md` điểm 2 và `design-w0-fixes-6.md`, kèm câu "không chạm `erp_ai_setting.py`". T51, T52 không chờ.
4. Preflight vòng 9 có thêm bốn task chèn của đợt 0. T121 (`depends:` T38) và T122 (`depends:` T36) sẵn sàng ngay; T120 chỉ khi T39 đã tick; T123 sau T120. T122 không cùng lượt với task nào có `erp_ai/tests/test_architecture.py` trong `files:`; T120, T123 không cùng lượt với task nào có `test_knowledge.py`. T124 chưa sẵn sàng ở vòng 9: chờ T53, T87; không cùng lượt với task nào đang mở trên `erp_ai_setting.py` hoặc `test_erp_ai_setting.py`; T72 không chờ T124.
5. Gọi dev T121, T122 trong lượt đầu có chỗ (phần dev = 2, xen với chuỗi U0); mỗi lệnh ghi BASE, touchpoint, `cmd.test_one`, câu "chỉ sửa trong touchpoint" và file thiết kế thắng (`design-w0-fixes-4.md` điểm 5; `design-w0-fixes-5.md` điểm 1).
6. Trước khi gọi dev T56: T20, T23, T38, T59, T121, T122 đã tick; không nhánh task nào mở trên tám file của T56 (T32, T43, T49); làm R5-7 trên đúng SHA `develop` sẽ gộp (hai phép `git grep -c` > 0, chạy lại `git merge-tree`), dán hai số và danh sách file xung đột vào progress của T56. Xung đột ở `runner.py`, `tasks.py` hoặc file ngoài `files:` → dừng, báo architect.
7. Sau merge T56: dán đầu ra `Expect` (1)–(5) vào progress; rồi T57; rồi M7 (`cmd.migrate`, `cmd.test` cả bộ) trước khi gọi dev nào của U1.
8. Từ khi T108 merge: nhắc team-leader R5-5 trong mỗi báo cáo cuối vòng cho tới khi task `runner.py` của U2 merge.

## Chèn 14 (2026-11-15, `/team:plan FEAT-007 --insert`, phụ lục spec 5 và ba phán quyết)

Nguồn: `spec-addendum-5.md` (H-4..H-6), `design-w1-fixes-18.md`, `design-w1-fixes-19.md`, `design-w1-fixes-20.md`, `arch-review-addendum-5.md`. Một task mới (T181), 179 → 180. Dòng thay nằm tại chỗ trong `tasks.md`; chi tiết ở dòng "chèn 14" đầu file đó.

Thứ tự: T181 → T82 → T83 → M8 (làn A); T52 → T53 → T54 (làn B); T126 sau T181; T47 sau T52. T103 không merge trước khi ADR-036 QĐ 2 có amendment chữ.

Touchpoint → task (phần mới hoặc đổi):

| Touchpoint | Việc | Task |
|---|---|---|
| `erp_ai/agent/prompts.py`, `test_prompts.py` | `_CORE_WRITING`, `RULE_6_ACT`, `ACT_NOW_BLOCK`, P-10, P-11 | T181 |
| `erp_ai/agent/test_classification.py` | cụm của `ACT_NOW_BLOCK` | T181 |
| `erp_ai_setting.py`, `erp_ai_setting.json`, `test_erp_ai_setting.py` | mục bắt buộc phần lập luận, mô tả trường | T181 |
| `erp_ai/agent/prompts.py` (`KNOWLEDGE_SOURCES_BLOCK`) | chữ nêu nguồn | T157 |
| `erp_ai/agent/kpi.py` | `log_actions`, `is_bot_close` | T52 |
| `erp_ai/agent/daily_report.py` | bảng loại hành động | T52, T166 |
| `erp_ai/agent/tools/write_ticket.py` | thứ tự mục, `PENDING_NOTE`, `failure_summary`, mô tả `post_comment` | T102, T103, T104 |
| `erp_ai/agent/tools/propose_change.py` | `PENDING_LINE` trỏ tới form | T105 |
| `erp_ai/agent/runner.py`, `test_agent_runner.py` | `_done_suffix`, phép kiểm đầu-cuối | T116, T117, T118 |

Một file, một chủ (chuỗi đổi):

| File | Chuỗi |
|---|---|
| `prompts.py`, `test_prompts.py` | T79 → T181 → T82 → T106 → T107 → T156 → T157; T126 sau T181 |
| `test_classification.py` | T72 → T79 → T176 → T181 → T82 |
| `erp_ai_setting.py`, `test_erp_ai_setting.py` | T72 → T79 → T181 → T87 → T124 |
| `erp_ai_setting.json` | T64 → T125 → T72 → T79 → T181 |
| `kpi.py` | T46 → T52 → T47 |

AC → task (AC `[changed]` của phụ lục 5, và AC-51):

| AC | Task |
|---|---|
| AC-65 (a) | T181, T102, T103, T104, T105, T116, T118 |
| AC-66 | T181, T103, T116, T118 |
| AC-23 | T181 (phần prompt), T104, T116, T118 |
| AC-32 | T181, T118 |
| AC-38 | T181 |
| AC-48 | T181 (phần lõi), T157 |
| AC-39 | T105 (đoạn (3)); nút "Duyệt ngay" và ngăn: chưa có task, chờ thiết kế U7b đợt 2 (AR5-1..AR5-7) |
| AC-69 | chưa có task, chờ thiết kế đợt 2 |
| AC-51 | T52, T166 |

Mốc kiểm: sau merge T181, một lần giữ khóa: `cmd.migrate`, rồi `cmd.test_one` cho `test_prompts.py`, `test_classification.py`, `test_erp_ai_setting.py`, `erp_ai/tests/test_architecture.py`. M8 (`cmd.test` cả bộ) giữ chỗ sau T83.

Rủi ro: T181 sáu file và `[migrate]`, chạy một mình trong các task `[migrate]`; claim file của T181 có thể `BUSY` nếu phiên CHG-002 đang giữ `prompts.py`; T82 còn hai chặn (`design-w1-fixes-21.md` chưa có, claim `BUSY`).

Trọng tâm review (test đã nằm trong task chủ):
1. Ghi đè lập luận đã lưu còn `**Căn cứ:**` vẫn lưu lại được (T181, `::test_reasoning_override_from_before_addendum_5_still_saves`).
2. Model viết thiếu tiêu đề "Hướng xử lý": dòng việc làm tay vẫn nằm đúng mục (T103, `::test_manual_lines_inside_plan_section`).
3. Dòng gom thoát HTML đúng một lần ở thông báo lỗi (T103, T117).
4. `cost_usd` rất nhỏ và cột làm tròn (T52, ca `0.0000004`).
5. Gộp `develop` không đưa mẫu comment cũ trở lại (T126, điều (10)).
