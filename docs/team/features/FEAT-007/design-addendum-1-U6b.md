Feature: FEAT-007
Stage: design
Author-agent: designer
Date: 2026-11-14
Approved-by:
<!-- G2b không áp dụng (team.py: chỉ cổng G5). -->

# Design addendum 1 — U6b Tri thức, trả lời người tạo, đóng phiếu (FEAT-007)

**Phạm vi.** Chỉ đơn vị U6b của `arch-impact.md:180`: AC-40..AC-50 (AC-42 theo bản `[changed]` của `spec-addendum-1.md:94`, thắng `spec.md:212`). Gồm: đăng ký tool tri thức và đọc hệ thống (bọc hàm Lõi của U6a), tool trả lời người tạo sau công tắc, handler khi người tạo trả lời, trigger soạn bài CSKT nháp, job vòng đời (Resolved khi Task xong; đóng F im lặng). Không thiết kế U0..U5, U6a, U7, U8.

**Luật thi hành (trích, không chép):** ADR-034 QĐ 1–7 và Ràng buộc; ADR-033 QĐ 1–6 và Ràng buộc; ADR-003 / ADR-013 QĐ 2 (mọi `frappe.enqueue` ở `agent/queue.py`, nhắc lại ở `design-w0-fixes.md` F-2); ADR-001 (model chỉ gọi trong runner); ADR-023 QĐ 4 (một hàm cấp, một bảng). Tên của U0 theo `design.md:91-153`, D-15 (`design.md:73`), `design-w0-fixes.md` mục 3 và F-5; tên U1 theo `design-addendum-1-U1.md` mục 3.9; tên U3 theo `design-addendum-1-U3.md` mục 3.10; tên U6a theo `design.md:484-493`.

---

## 1. Bối cảnh

### 1.1 Explore summary (đọc trực tiếp, 2026-11-14, nhánh `develop`)

| Chỗ | Hiện trạng | U6b đổi |
|---|---|---|
| `erp_ai/agent/tools/registry.py:34-40` | `TOOL_MODULES` 5 module | thêm 3 module tool mới |
| `registry.py:29` | `ToolSpec.group` là `Literal` 6 nhóm | thêm `requester_reply`, `kb_draft` |
| `registry.py:49-62` | `GRANT_TABLE` (U1 thay bằng bảng nhận `GrantInputs`) | thêm 2 dòng, thêm vế `¬kb_draft_run` cho 5 dòng ghi (mục 3.2) |
| `erp_ai/agent/queue.py:6`, `:14-40` | `VALID_TRIGGERS` 2 trigger; `job_id = erp_ai::{ticket}::{trigger}`, `deduplicate`, tập chờ theo giao dịch `PENDING_JOB_IDS_FLAG` | thêm 2 trigger, tham số `communication_name`, hàm xếp job vòng đời |
| `erp_ai/handlers.py:84-97` | `ticket_on_update` chỉ ghi nhận người sửa phân loại, `return` sớm khi không có cờ | tách thành 2 hàm riêng, thêm nhánh soạn CSKT |
| `handlers.py:100-120` | `comment_after_insert`: lọc rẻ trước khi đọc DB, `_log_decision` | mẫu cho 2 handler mới |
| `erp_ai/hooks.py:141-162` | `doc_events` có HD Ticket, Comment (U6a thêm HD Article, `design.md:346`); `scheduler_events` `hourly`, `daily` (U4a/U5a thêm `cron`) | thêm `Communication`, `Task`; thêm một dòng `cron` |
| `erp_ai/agent/tools/read.py:103-138` | `search_resolved_tickets`: LIKE chuỗi con nguyên câu, `order_by modified`, lọc `can_send_ticket` sau truy vấn, không có comment | xếp theo số từ khớp, thêm comment người phụ trách khi chi tiết giải quyết trống (AC-48) |
| `read.py:24` | `ALLOWED_READ_DOCTYPES` có `HD Article` | giữ |
| `erp_ai/agent/runner.py:100-190` | `run_for_ticket(ticket, trigger)`; bỏ qua L0 chỉ cho `comment_mention`; kiểm giới hạn ngày cho mọi trigger | thêm tham số, bỏ qua L0 cho mọi trigger khác `ticket_insert`, kiểm trước riêng cho 2 trigger mới |
| `runner.py:72-84` | `WRITE_TOOL_TARGETS` | thêm 2 tool ghi |
| `erp_ai/agent/prompts.py:338-361` | `build_initial_message` chọn `TASK_COMMENT` hay `TASK_NEW_TICKET` theo trigger | thêm 2 nhiệm vụ |
| `erp_ai/agent/policy.py:27-39`, `:80-92` | `can_send_ticket` (vị từ gửi duy nhất); `runs_today` đếm dòng `classify|reason` **không lọc trigger** | U6b chỉ gọi; đổi `runs_today` là việc của chủ `policy.py` (mục 1.4) |
| `erp_ai/agent/run_log.py:9` | `TRIGGERS = ("ticket_insert", "comment_mention")` | thêm `requester_reply`, `kb_draft` (F-5) |
| `erp_ai_log.json:96` | option `trigger` 3 giá trị (U3 thêm 2) | thêm 2 (F-5) |
| `erp_ai/install.py:22` | `TASK_TICKET_FIELD = "ai_ticket"` (Link HD Ticket trên Task) | U6b chỉ đọc (AC-43, A-11) |
| `erp_ai/agent/tools/write_ticket.py:102-112` | comment phiếu qua `doc.new_comment(...)` | job vòng đời dùng cùng đường |
| `erp_ai/tests/test_architecture.py:120` | `ENQUEUE_TARGETS` ghim (U5a nâng lên 5, F-2) | thêm 1 đích |
| Helpdesk `hd_ticket.py:668-676` | `reply_via_agent(self, message, from_email=None, to=None, cc=None, bcc=None, attachments=[])`, chặn `is_agent()` | tool trả lời gọi với `to=raised_by` |
| Frappe `desk/query_report.py:247-256` | `run(report_name, filters=None, user=None, ignore_prepared_report=False, ...)` | tool báo cáo gọi dưới phiên agent |
| Helpdesk `hd_ticket_status` | `category` ∈ Open/Paused/Resolved; `Closed` thuộc nhóm Resolved | "đã Resolved hoặc Closed" = `status_category == "Resolved"` |

Research áp dụng: R-1 (a) kênh `reply_via_agent`, (b) `first_responded_on`, (d) sự kiện `Communication.on_update` và các bẫy: **B-1** thư mở phiếu cũng là `Received`; **B-2** `on_update` bắn hai lần cho một thư (`receive.py:730`, `:738`); **B-3** phiếu gộp đổi `reference_name` (`T:1063-1068`). R-4 (b): role `Agent` xuất bản được bài, chốt chặn ở app (U6a `article_guard`).

### 1.2 Tên U6b dựa vào và nguồn

| Tên | Nguồn | Có trên `develop` hôm nay? |
|---|---|---|
| `reply_enabled`, `resolve_on_tasks_done_enabled`, `close_silent_f_enabled`, `close_silent_f_days` (Int 3, 1..30), `kb_draft_enabled`, `knowledge_search_limit` (Int 5, 1..20), `manuals_dir`, `allowed_reports`, `report_row_limit` (Int 20, 1..100), `field_origin`, `origin_board_value` | U0, `design.md:105-137` | Không (U0, đợt 0) |
| Trường tùy biến `ai_source_ticket` (Link HD Ticket, read-only, có chỉ mục) trên HD Article | U0, `design.md:73` (D-15), `:250` | Không |
| `TICKET_CONTENT_DOCTYPES` | U0, `erp_ai/constants.py` (`design-w0-fixes.md` mục 3) | Không |
| `check_allowed_reports` (kiểm lúc lưu `allowed_reports`) | U0, `design.md:307` | Không |
| `redact.redact_secrets` | U6a, `erp_ai/agent/redact.py` (`design.md:486`) | Không |
| `system_read.read_error_logs(since, until, keyword, limit)` | U6a, `erp_ai/agent/system_read.py` (`design.md:487`) | Không |
| `knowledge.tokenize`, `knowledge.search_kb_articles(query, limit)`, `knowledge.search_manuals(query, limit, manuals_dir)` (trả `None` khi chưa cấu hình) | U6a, `erp_ai/agent/knowledge.py` (`design.md:488-491`) | Không |
| `article_guard.check_article_write` (chặn bot xuất bản, sửa bài người khác) | U6a, `design.md:493` | Không |
| `GrantInputs`, `Grant`, `grant`, `GRANT_TABLE`, `ASK_TOOL_NAMES`, `ToolContext.grant_inputs`, `ToolContext.below_threshold` | U1, `design-addendum-1-U1.md:285-292` | Không |
| `enter_agent_session`, `TITLE_WRONG_USER`, `run_instructor` | U1, `:293-295` (`erp_ai/agent/authority.py`) | Không |
| `enqueue_agent_run(ticket, trigger, comment_name=None)`, `run_for_ticket(ticket, trigger, comment_name=None)`, `build_reason_system(..., *, flags)` | U1, `:297-299` | Không |
| `policy.latest_classification`, `confidence_threshold`, `is_below_confidence`, `is_over_budget`, `effective_level(settings, *, over_budget)` | U1, `:278-284` | Không |
| `run_log.action_entry`, `write_bot_action`, `TRIGGER_SCHEDULED_JOB`, `TRIGGERS`, `runner._entry_values` | U3, `design-addendum-1-U3.md:238-250` | Không |
| `ENQUEUE_TARGETS` 5 đích, `check_enqueue_call_shape` "one per target" | U5a, `design-w0-fixes.md` F-2 | Không |
| `policy.can_send_ticket`, `policy.is_enabled`, `read.denied_doctypes`, `read._check_ticket`, `read.TOOL_RESULT_MAX_CHARS`, `WRITE_TOOL_TARGETS`, `TASK_TICKET_FIELD`, `AGENT_USER`, `LOG_DOCTYPE` | FEAT-001/FEAT-004 | Có |

**Điều kiện bắt đầu U6b:** U1, U3, U6a đã merge vào `team/FEAT-007` (arch-impact cột Phụ thuộc). Thiếu một tên ở bảng trên → `DESIGN_CONFLICT`, dừng, không tự đặt.

### 1.3 Cần từ U0 (không tự đặt)

| Cần | Có trong schema U0? |
|---|---|
| Các trường mục 1.2 dòng 1–4 | Có |
| **Quyền đọc HD Article cho `ERP AI Instructor`** (AC-45 câu cuối "Người có Instructor mở được danh sách bài nháp do bot soạn"). HD Article chỉ cấp read cho Agent, System Manager, HD Customer, HD Customer Manager (R-4 (a)). COO chỉ có Instructor (ADR-034 QĐ 8) | **Thiếu** — không thấy ở `design.md:229-250`. Chủ: U0 (`install.py`, Custom DocPerm `read=1`, `report=1` cho `ERP AI Instructor` trên HD Article, cài theo ADR-006). Nếu U0 không thêm: As-Built ghi "Instructor phải kèm role Agent" và test AC-45 dòng cuối dùng tài khoản Instructor + Agent |

### 1.4 Cần từ U1 / U3 / U4b / U2 / U5a

| Cần | Chủ | Vì sao |
|---|---|---|
| `policy.runs_today` lọc theo **một** tập trigger được đếm: `RUN_LIMIT_TRIGGERS = ("ticket_insert", "comment_mention", "requester_reply")` (hằng ở `policy.py`, chuỗi literal để không import `queue`); trigger `kb_draft` không đếm | U1 (chủ `policy.py`; ADR-033 QĐ 4 và Ràng buộc "`runs_today` lọc theo tập trigger được đếm, định nghĩa một lần") | `policy.py` không thuộc ô file của U6b. Thiếu thì dòng `reason` của lần chạy `kb_draft` ăn vào giới hạn ngày (trái NFR-2). Nếu U1 đã đóng: tech-lead giao một task nhỏ trên `policy.py` trước task runner của U6b |
| Comment "bỏ qua vì chạm giới hạn ngày" (tối đa 1/phiếu/ngày) | U4b (AC-23) | AC-41 ca 4 đếm comment này; U6b chỉ bảo đảm lần chạy `requester_reply` đi qua đúng nhánh `_log_skip(..., "daily_limit")` |
| Vị từ phiếu loại trừ dạng điều kiện truy vấn (ADR-034 QĐ 1) | U2 | Nếu U2 có hàm dạng truy vấn, `search_resolved_tickets` dùng hàm đó; nếu chưa, giữ lọc từng dòng bằng `can_send_ticket` (đang có, `read.py:132`) — kết quả tìm không lộ số đếm nên vẫn đạt AC-48 |
| `daily_report.ACTION_KIND_BY_TOOL` thêm `reply_to_requester` → "trả lời", `resolve_on_tasks_done`/`close_silent_f` → "đổi trạng thái", `create_kb_draft` → "bài CSKT" | U5a file (`design.md:453` giao U6b) | `daily_report.py` ngoài ô file U6b → việc hòa nhập INT-U6b-1, làm khi merge U6b, có test của U5a |

---

## 2. Mô hình dữ liệu

U6b **không thêm DocType, không thêm trường**. Chỉ:

| Thay đổi | Ở đâu | Kiểu | Cùng commit với |
|---|---|---|---|
| Option `trigger` thêm `requester_reply`, `kb_draft` (sau các option U3) | `erp_ai_log.json` | Select, chỉ thêm | `run_log.TRIGGERS`, `queue.VALID_TRIGGERS`, cụm từ mô tả `trigger` (F-5) |
| Dữ liệu tạo mới: HD Article `status="Draft"`, `ai_source_ticket=<phiếu>`, `owner=author=AGENT_USER` | bảng HD Article | bản ghi | — |
| Communication `Sent` của bot (`owner=AGENT_USER`, `recipients=raised_by`) | Helpdesk | bản ghi | — |
| HD Ticket `status` → `Resolved` / `Closed` | Helpdesk | ghi dưới phiên agent | dòng `bot_action` |

**Mẫu truy cập (không cần chỉ mục mới):**
- Đồng hồ im lặng (AC-44): Communication theo `(reference_doctype, reference_name, sent_or_received, owner, creation)` — Frappe đã có chỉ mục `reference_doctype, reference_name`. Không lưu trạng thái đồng hồ: tính lại từ Communication mỗi lần quét (người tạo trả lời = đồng hồ tự bắt đầu lại).
- Một bài cho một phiếu: `HD Article.ai_source_ticket` có chỉ mục (D-15).
- Task liên kết: `Task.ai_ticket` (Link, có chỉ mục của Link).
- Mốc "1 dòng log mỗi ngày" khi chưa cấu hình (AC-42 (c)): dòng `bot_action` có `run_id = "lifecycle-config-<YYYY-MM-DD>"` (khóa chu kỳ là chính dòng, ADR-033 QĐ 6).

**Dòng ERP AI Log do U6b tạo:**

| Đường | `entry_type` / `trigger` | `actions` (mỗi lần ghi một mục, qua `action_entry`) |
|---|---|---|
| Lần chạy người tạo trả lời | `classify`?/`reason`/`skip` / `requester_reply` | mục của lượt; `reply_to_requester` → `("Communication", tên)` |
| Lần chạy soạn CSKT | `reason`/`skip` / `kb_draft` | `create_kb_draft` → `("HD Article", tên)` |
| Resolved khi Task xong | `bot_action` / `scheduled_job` | `resolve_on_tasks_done` (`value_before={"status": cũ}`, `value_after={"status": "Resolved"}`), `lifecycle_comment` |
| Đóng F im lặng | `bot_action` / `scheduled_job` | `requester_notice`, `close_silent_f` (status cũ → `Closed`), `lifecycle_comment` |
| Chưa cấu hình Nguồn phát sinh | `bot_action` / `scheduled_job`, `ticket` rỗng | một mục `ticket_lifecycle`, `ok=False`, `reason=REASON_ORIGIN_NOT_CONFIGURED` |

---

## 3. API / hợp đồng

Mọi hàm là Python nội bộ; **không có method whitelist mới**, không endpoint mới. Tool trả một dạng: `{"ok": True, ...}` hoặc `{"ok": False, "reason": <chữ cố định>}` (dạng có sẵn, `read.py:40-41`). Hàm Lõi ném `ValueError` cho tham số sai (như `queue.py:15-16`).

### 3.1 `erp_ai/agent/queue.py` (sửa)

```python
TRIGGER_REQUESTER_REPLY = "requester_reply"
TRIGGER_KB_DRAFT = "kb_draft"
VALID_TRIGGERS = (TRIGGER_TICKET_INSERT, TRIGGER_COMMENT_MENTION, TRIGGER_REQUESTER_REPLY, TRIGGER_KB_DRAFT)
LIFECYCLE_JOB_TIMEOUT_S = 300

def enqueue_agent_run(ticket_name: str, trigger: str, comment_name: str | None = None,
                      communication_name: str | None = None) -> bool
def enqueue_lifecycle_job(ticket_name: str) -> bool
```

- Hai hằng trigger đặt ở `queue.py` (cạnh `VALID_TRIGGERS`) vì `constants.py` ngoài ô file U6b (A-U6b-1).
- `enqueue_agent_run`: kiểm biên thêm — `trigger == TRIGGER_REQUESTER_REPLY` mà `communication_name` không phải chuỗi khác rỗng → `ValueError`; `communication_name` có giá trị với trigger khác → `ValueError`. `job_id` **giữ** `erp_ai::{ticket}::{trigger}` + `deduplicate=True` (hai tin liên tiếp của người tạo khi job chưa chạy gộp thành một lần chạy, A-U6b-4). `frappe.enqueue(..., comment_name=comment_name, communication_name=communication_name)`.
- Tách thân tập chờ (`:20-28`) thành `_claim_pending(job_id) -> bool` riêng tư, dùng chung cho hai hàm xếp hàng (STD-DESIGN-4).
- `enqueue_lifecycle_job`: `ticket_name` không phải chuỗi khác rỗng → `ValueError`; `job_id = f"erp_ai_lifecycle::{ticket_name}"`; `_claim_pending` sai → `False`; đúng **một** lời `frappe.enqueue("erp_ai.agent.lifecycle.run_task_lifecycle", queue="default", timeout=LIFECYCLE_JOB_TIMEOUT_S, enqueue_after_commit=True, job_id=job_id, deduplicate=True, ticket_name=ticket_name)`; trả `True`. Đích là chuỗi; `queue.py` không import `lifecycle`.

### 3.2 `erp_ai/agent/tools/registry.py` (sửa, trên bản U1)

- `TOOL_MODULES` thêm `"erp_ai.agent.tools.knowledge_read"`, `"erp_ai.agent.tools.reply"`, `"erp_ai.agent.tools.kb_draft"`.
- `ToolSpec.group` thêm `"requester_reply"`, `"kb_draft"`.
- `GrantInputs` thêm (có mặc định, giữ hành vi U1 — hợp đồng U1 `:285`): `reply_enabled: bool = False`, `kb_draft_run: bool = False`.
- `ToolContext` thêm: `reply_enabled: bool = False`, `kb_draft_run: bool = False`; `grant_inputs()` chuyển hai trường này.
- `Grant` thêm `reply_block: bool = False` (cờ khối prompt trả lời).
- Hằng `REPLY_GROUP = "requester_reply"`, `KB_DRAFT_GROUP = "kb_draft"`.

**Bảng cấp sau U6b** (`kb = inputs.kb_draft_run`; điều kiện U1 giữ nguyên, chỉ thêm vế `¬kb`):

| Nhóm | Điều kiện |
|---|---|
| `read` | luôn (gồm 4 tool tri thức mới) |
| `ticket_write` | điều kiện U1 ∧ `¬kb` |
| `task_write` | điều kiện U1 ∧ `¬kb` |
| `change_propose` | điều kiện U1 ∧ `¬kb` |
| `site_admin` | điều kiện U1 ∧ `¬kb` |
| `site_unrestricted` | `u` ∧ `¬kb` |
| `requester_reply` | `reply_enabled ∧ ¬kb` (không phụ thuộc ngưỡng: dưới ngưỡng tool vẫn có nhưng chỉ nhận câu hỏi, mục 3.4) |
| `kb_draft` | `kb` |

Đây là "dòng cố định" của trigger soạn CSKT (ADR-033 QĐ 3): `kb` đúng → đúng `read` + `kb_draft`, mọi cờ khối False (`ask_only_block` thêm vế `¬kb`). Vẫn một hàm `grant`, một `GRANT_TABLE`. Mức L0 → `Grant(specs=())` như U1. Cờ `reply_block` ⇔ nhóm `requester_reply` được cấp. `ASK_TOOL_NAMES` **không đổi**.

### 3.3 `erp_ai/agent/tools/knowledge_read.py` (mới, nhóm `read`)

```python
KNOWLEDGE_TOOL_NAMES = frozenset({"search_knowledge_base", "search_manuals", "read_error_logs", "run_report"})
MANUALS_NOT_CONFIGURED = "chưa có kho HDSD"
REPORT_FILTER_MAX_KEYS = 10
REPORT_TYPES = ("Script Report", "Query Report")
TOOLS: list[ToolSpec]
```

Một chỗ đọc cấu hình của nhóm này: `_limits() -> tuple[int, tuple[str, ...], int]` = (`knowledge_search_limit`, các dòng khác rỗng đã `strip` của `allowed_reports`, `report_row_limit`) bằng `frappe.db.get_single_value`. Mọi chuỗi trả về đi qua `redact.redact_secrets`; kết quả JSON cắt theo `read.TOOL_RESULT_MAX_CHARS`.

| Tool (input_schema) | Hành vi | Lý do từ chối (chữ cố định) |
|---|---|---|
| `search_knowledge_base(query: string 2..100)` AC-46 | `knowledge.search_kb_articles(query, limit)` dưới phiên agent → `{"ok": True, "articles": [{name, title, excerpt}]}` | `frappe.ValidationError` của U6a → `"Câu tìm cần ít nhất một từ dài 2 ký tự"` (chữ của U6a) |
| `search_manuals(query: string 2..100)` AC-47 | `knowledge.search_manuals(query, limit, manuals_dir)`; `None` → từ chối; list → `{"ok": True, "sections": [{document, heading, line, excerpt}]}` | `MANUALS_NOT_CONFIGURED`; lỗi U6a như trên |
| `read_error_logs(since?: string, until?: string, keyword?: string 2..100, limit?: integer 1..50)` AC-50 | `since`/`until` parse bằng `frappe.utils.get_datetime`; gọi `system_read.read_error_logs(...)`; `{"ok": True, "errors": [...]}`. Tool **không** có `ignore_permissions` (ADR-034 Ràng buộc) | `"thời điểm không hợp lệ: since"` / `until`; `frappe.ValidationError` → chữ của U6a ("Khoảng thời gian tối đa 7 ngày") |
| `run_report(report_name: string 1..140, filters?: object ≤ 10 khóa, giá trị string/number/boolean)` AC-49 | (1) danh sách rỗng → từ chối; (2) tên không nằm trong danh sách; (3) `Report` không có, `disabled`, `report_type ∉ REPORT_TYPES`; (4) `ref_doctype ∈ TICKET_CONTENT_DOCTYPES ∪ read.denied_doctypes()` (kiểm lại lúc chạy, vì cấu hình có thể bị ghi lách form); (5) `frappe.desk.query_report.run(report_name, filters=filters or {}, ignore_prepared_report=True)` dưới phiên agent; (6) cắt `result` còn `report_row_limit` dòng; trả `{"ok": True, "columns": [nhãn], "rows": [...], "truncated": bool}` | (1) `"chưa cho phép báo cáo nào"`; (2) `"báo cáo không nằm trong danh sách cho phép"`; (3) `"báo cáo không chạy được"`; (4) `"báo cáo dựa trên dữ liệu phiếu hoặc dữ liệu của app: bot không được chạy"`; `frappe.PermissionError` → `"tài khoản agent không có quyền chạy báo cáo này"`; `filters` sai → `_invalid` có sẵn của registry |

### 3.4 `erp_ai/agent/tools/reply.py` (mới, nhóm `requester_reply`) — AC-40

```python
REPLY_KINDS = ("answer", "question")
REPLY_MAX_CHARS = 4000
SOURCES_MAX = 5
TOOLS = [ToolSpec("reply_to_requester", "requester_reply", schema, reply_to_requester)]
```

Input: `message` string 1..4000 (bắt buộc), `kind` enum `answer|question` (bắt buộc), `sources` array ≤ 5 string 1..200 (tên bài CSKT, mục HDSD, số phiếu cũ).

Thứ tự kiểm (dừng ở lý do đầu tiên):

| # | Điều kiện | `reason` |
|---|---|---|
| 1 | `read._check_ticket(ctx.ticket_name)` từ chối (không có, không quyền, nhóm loại trừ, cờ không dùng AI) | chữ có sẵn của `read.py:54-58` (`"phiếu không được phép đưa cho AI"`, …) |
| 2 | `raised_by` rỗng | `"phiếu không có người tạo để trả lời"` |
| 3 | `ctx.below_threshold` ∧ `kind != "question"` | `"độ tin cậy dưới ngưỡng: chỉ được hỏi lại"` |
| 4 | `kind == "question"` ∧ `"?" not in message` | `"câu hỏi lại phải có dấu ?"` |
| 5 | đầu mục (`policy.latest_classification(ticket)[0]`) là F ∧ `kind == "answer"` ∧ `sources` rỗng | `"đầu mục F: trả lời phải nêu ít nhất một nguồn (bài CSKT, mục HDSD hoặc số phiếu cũ); không có nguồn thì hỏi lại"` |
| 6 | `lifecycle.send_to_requester` ném `frappe.ValidationError` (gồm lỗi thiếu Email Account gửi đi, R-1 (c)) | `"chưa gửi được: site chưa có tài khoản email gửi đi"`; một dòng `frappe.logger(LOGGER_NAME).warning` có mã phiếu và tên lớp lỗi; **không** comment thay thế (ADR-034 QĐ 7) |

Thành công: nội dung = `html.escape(message)` (xuống dòng → `<br>`), với `answer` có `sources` thêm đoạn `"Nguồn: …"`; qua `redact_secrets`; `send_to_requester(ticket, html)` → `{"ok": True, "communication": <tên>}`. Không gọi `new_comment`/`add_comment` (ADR-034 Ràng buộc). Người nhận duy nhất là `raised_by` của **chính** `ctx.ticket_name` (tool không nhận tham số người nhận hay phiếu).

### 3.5 `erp_ai/agent/tools/kb_draft.py` (mới, nhóm `kb_draft`) — AC-45

```python
KB_TITLE_MAX = 140
TOOLS = [ToolSpec("create_kb_draft", "kb_draft", schema, create_kb_draft)]
```

Input: `title` string 5..140, `problem` string 20..4000, `resolution_steps` array 1..20 string 1..1000.

| # | Điều kiện | `reason` |
|---|---|---|
| 1 | `read._check_ticket` từ chối | chữ có sẵn |
| 2 | `status_category` của phiếu ≠ `"Resolved"` | `"phiếu chưa đóng"` |
| 3 | đã có HD Article với `ai_source_ticket = ticket` | `"phiếu đã có bài CSKT"` |

Thành công: `frappe.get_doc({"doctype": "HD Article", "title": title, "content": <html>, "status": "Draft", "ai_source_ticket": ticket}).insert()` — **không** `ignore_permissions`, dưới phiên agent; `article_guard` của U6a chặn mọi trạng thái khác `Draft`. `content` = `<h2>Vấn đề</h2><p>…</p><h2>Các bước đã giải quyết</h2><ol><li>…</li></ol><p>Phiếu nguồn: #<ticket></p>`, mọi đoạn `html.escape` rồi `redact_secrets`. Trả `{"ok": True, "article": <tên>}`.

### 3.6 `erp_ai/agent/lifecycle.py` (mới, "file job vòng đời"; Lõi agent, không import Cổng model)

```python
STATUS_RESOLVED = "Resolved"; STATUS_CLOSED = "Closed"; RESOLVED_CATEGORY = "Resolved"
TASK_COMPLETED = "Completed"; TASK_CANCELLED = "Cancelled"
CATEGORY_E = "E"; CATEGORY_F = "F"
TOOL_RESOLVE_ON_TASKS_DONE = "resolve_on_tasks_done"; TOOL_CLOSE_SILENT_F = "close_silent_f"
TOOL_LIFECYCLE_COMMENT = "lifecycle_comment"; TOOL_REQUESTER_NOTICE = "requester_notice"
TOOL_LIFECYCLE_CONFIG = "ticket_lifecycle"
REASON_ORIGIN_NOT_CONFIGURED = "chưa cấu hình trường Nguồn phát sinh (field_origin, origin_board_value)"
TITLE_LIFECYCLE_FAILED = "ERP AI lifecycle failed"
COMMENT_RESOLVED = "ERP AI: mọi Task liên kết đã xong ({completed} Completed), phiếu chuyển Resolved."
COMMENT_SILENT_CLOSED = "ERP AI: người tạo chưa phản hồi {days} ngày sau tin của bot, phiếu chuyển Closed."
NOTICE_SILENT_CLOSE = "Phiếu #{ticket} được đóng vì chưa nhận được phản hồi sau {days} ngày. Nếu vấn đề còn, anh/chị trả lời tin này để mở lại."

@dataclass(frozen=True)
class LifecycleSettings:
    reply: bool; resolve_on_tasks_done: bool; close_silent_f: bool
    close_silent_f_days: int; kb_draft: bool; field_origin: str; origin_board_value: str

def lifecycle_settings(settings) -> LifecycleSettings          # chỗ đọc duy nhất 7 trường này
def kb_draft_enabled() -> bool                                  # 1 get_single_value, cho handler
def origin_configured(ls: LifecycleSettings) -> bool
def status_change_refusal(ticket_name: str, ls: LifecycleSettings) -> str | None
def send_to_requester(ticket_name: str, html: str) -> str
def tasks_done(ticket_name: str) -> tuple[bool, int]
def silent_since(ticket_name: str) -> datetime | None
def run_task_lifecycle(ticket_name: str) -> None               # đích của enqueue_lifecycle_job
def scan_silent_f_tickets(now=None) -> None                     # lịch mỗi giờ
```

| Hàm | Hành vi chính xác |
|---|---|
| `origin_configured` | `field_origin` và `origin_board_value` đều khác rỗng **và** `frappe.get_meta("HD Ticket").has_field(field_origin)`; sai một vế → `False` (fail-closed, AC-42 (c)) |
| `status_change_refusal` (chốt chung AC-42 (b)) | theo thứ tự: chưa cấu hình → `"origin_not_configured"`; `not policy.can_send_ticket(ticket)` → `"not_sendable"` (A-U6b-5); giá trị trường `field_origin` của phiếu (so sau `strip`, `casefold`) = `origin_board_value` → `"board_directed"`; đầu mục `policy.latest_classification(ticket)[0] == CATEGORY_E` → `"category_e"`; ngược lại `None` |
| `send_to_requester` | `doc = frappe.get_doc("HD Ticket", t)`; `doc.reply_via_agent(message=html, to=doc.raised_by)`; trả tên Communication `Sent` mới nhất có `owner = AGENT_USER` của phiếu. Không bắt lỗi (người gọi quyết) |
| `tasks_done` | `frappe.get_all("Task", {TASK_TICKET_FIELD: t}, pluck="status")`; bỏ `Cancelled`; đúng ⇔ còn ≥ 1 Task và mọi Task còn lại `Completed`; trả `(đúng/sai, số Completed)`. Task không có `ai_ticket` không bao giờ được đếm (A-11) |
| `silent_since` | `last_bot` = `creation` lớn nhất của Communication `Sent`, `owner = AGENT_USER` của phiếu; không có → `None`. Có Communication `Received` của người tạo (`extract_email_id(sender)` == `extract_email_id(raised_by)`, so `casefold`) với `creation > last_bot` → `None` (đồng hồ dừng, bắt đầu lại ở tin kế của bot — AC-41 câu cuối, AC-44). Ngược lại trả `last_bot` |
| `run_task_lifecycle` (AC-43) | (1) `enter_agent_session()` sai → dừng; (2) `ls.resolve_on_tasks_done` tắt → dừng, không ghi (AC-42 (a)); (3) `not origin_configured` → `_log_config_missing_daily(now)`, dừng; (4) khóa dòng phiếu `frappe.db.get_value("HD Ticket", t, "status_category", for_update=True)`; `RESOLVED_CATEGORY` → dừng; (5) `status_change_refusal` ≠ None → một dòng logger, dừng; (6) `tasks_done` sai → dừng; (7) `before = doc.status`; `doc.status = STATUS_RESOLVED`; `doc.save()`; `doc.new_comment(COMMENT_RESOLVED)` (cùng đường `write_ticket.py:102-112`); (8) `write_bot_action(trigger=TRIGGER_SCHEDULED_JOB, ticket=t, actions=[action_entry(TOOL_RESOLVE_ON_TASKS_DONE, "HD Ticket", t, True, value_before={"status": before}, value_after={"status": STATUS_RESOLVED}), action_entry(TOOL_LIFECYCLE_COMMENT, "Comment", <tên>, True, value_after={"content": COMMENT_RESOLVED…})])` **cuối cùng** (commit phủ cả ba, ADR-033 QĐ 6). Lỗi bất kỳ ở (4)–(8) → `frappe.db.rollback()`, `frappe.log_error(TITLE_LIFECYCLE_FAILED, f"ticket={t} error={type(exc).__name__}")`, job kết thúc bình thường |
| `scan_silent_f_tickets` (AC-44) | (1) `enter_agent_session()`; (2) `ls.close_silent_f` tắt → dừng; (3) chưa cấu hình → `_log_config_missing_daily(now)`, dừng; (4) `now = now or now_datetime()`, `cutoff = now − close_silent_f_days ngày`; ứng viên = `frappe.get_all("Communication", {"reference_doctype": "HD Ticket", "sent_or_received": "Sent", "owner": AGENT_USER, "creation": ("<=", cutoff)}, pluck="reference_name", distinct=True)`; (5) mỗi phiếu, giao dịch riêng: khóa dòng; `status_category == RESOLVED_CATEGORY` → bỏ; `status_change_refusal` ≠ None → bỏ; đầu mục ≠ F → bỏ; `silent_since(t)` là `None` hoặc `> cutoff` → bỏ; (6) `send_to_requester(t, NOTICE_SILENT_CLOSE)` **trước** khi đổi trạng thái (Communication `Sent` có thể đổi status theo luật Helpdesk); lỗi → `write_bot_action` một mục `requester_notice` `ok=False` có lý do, **không đóng**, phiếu được thử lại ở lần quét sau; (7) `doc.flags.erp_ai_silent_close = True`; `doc.status = STATUS_CLOSED`; `doc.save()`; comment `COMMENT_SILENT_CLOSED`; (8) `write_bot_action` 3 mục (`requester_notice`, `close_silent_f`, `lifecycle_comment`). Lỗi một phiếu → rollback phiếu đó, `log_error(TITLE_LIFECYCLE_FAILED, …)`, sang phiếu kế |
| `_log_config_missing_daily(now)` (riêng tư) | `run_id = f"lifecycle-config-{now.date().isoformat()}"`; đã có dòng ERP AI Log với `run_id` đó → không làm gì; chưa → `write_bot_action(trigger=TRIGGER_SCHEDULED_JOB, run_id=run_id, actions=[action_entry(TOOL_LIFECYCLE_CONFIG, None, None, False, reason=REASON_ORIGIN_NOT_CONFIGURED)])`. Chỉ chạy khi ít nhất một công tắc đổi trạng thái bật |

Không hàm nào ở đây ghi ERP AI Setting (ADR-033 QĐ 1) hay gọi Cổng model (ADR-033 QĐ 3).

### 3.7 `erp_ai/handlers.py` (sửa)

```python
def ticket_on_update(doc, method=None)        # gọi _record_human_correction(doc), rồi _maybe_enqueue_kb_draft(doc)
def communication_on_update(doc, method=None) # AC-41
def task_on_update(doc, method=None)          # AC-43
```

| Handler | Lọc rẻ (không đọc DB) | Lọc có đọc DB → lý do `_log_decision` | Xếp hàng |
|---|---|---|---|
| `_maybe_enqueue_kb_draft` | `doc.flags.in_insert` → về; `not doc.has_value_changed("status")` → về; `doc.status_category != "Resolved"` → về | `not policy.is_enabled()` → `agent_disabled`; `not lifecycle.kb_draft_enabled()` → `kb_draft_off`; `doc.flags.erp_ai_silent_close` → `silent_close`; `not policy.can_send_ticket(doc)` → `not_sendable`; có HD Article `ai_source_ticket = doc.name` → `kb_exists` | `enqueue_agent_run(doc.name, TRIGGER_KB_DRAFT)` |
| `communication_on_update` | `reference_doctype != "HD Ticket"` hoặc `sent_or_received != "Received"` hoặc `communication_type != "Communication"` → về | `not policy.is_enabled()` → `agent_disabled`; `owner == AGENT_USER` → `written_by_agent`; người gửi ≠ `raised_by` (cùng phép so của `silent_since`) → `not_requester`; **B-1:** không có Communication `Sent`, `owner = AGENT_USER` của phiếu với `creation < doc.creation` → `no_bot_message_before`; `not can_send_ticket(ticket)` → `not_sendable` | `enqueue_agent_run(doc.reference_name, TRIGGER_REQUESTER_REPLY, communication_name=doc.name)` (đọc `reference_name` lúc `on_update`, **B-3**) |
| `task_on_update` | `not doc.get(TASK_TICKET_FIELD)` → về (A-11); `not doc.has_value_changed("status")` → về | `not policy.is_enabled()` → `agent_disabled` | `enqueue_lifecycle_job(doc.get(TASK_TICKET_FIELD))` |

**B-2** (hai lần `on_update` cho một thư): trong cùng giao dịch → `_claim_pending` trả `False` lần hai; giao dịch khác khi job còn chờ → `deduplicate` của RQ; sau khi job đã chạy → runner bỏ qua `already_handled` (3.8). Handler không ghi gì, không đổi trạng thái, không import Cổng model (ADR-033 Ràng buộc).

### 3.8 `erp_ai/agent/runner.py` (sửa, trên bản U1/U3)

- `run_for_ticket(ticket_name, trigger, comment_name=None, communication_name=None)` → `_run(...)`.
- Bước sau (c): `requester_reply` → `_requester_reply_skip(ticket, communication_name) -> str | None`: Communication không có → `"event_missing"`; `reference_name ≠ ticket` (đọc lại từ DB, **B-3**) → `"event_moved"`; đã có dòng ERP AI Log `ticket=ticket`, `trigger=requester_reply`, `creation ≥ communication.creation` → `"already_handled"` (**B-2** khác giao dịch). `kb_draft` → `_kb_draft_skip(ticket, settings)`: `lifecycle_settings(settings).kb_draft` tắt → `"kb_draft_off"`; `status_category ≠ "Resolved"` → `"not_closed"`; có bài `ai_source_ticket` → `"kb_exists"`; `resolution_details` trống **và** không có Comment của người được giao phiếu (`_assign`, khác `AGENT_USER`) → `"no_resolution_content"` (A-16). Có lý do → `_log_skip`, dừng.
- Bước (d) giới hạn ngày: **không** kiểm cho `kb_draft` (ADR-033 QĐ 4).
- Bỏ qua L0 (`runner.py:153`): áp cho mọi trigger khác `ticket_insert` (`"level_L0"`) — AC-45 "mức hiệu lực ≥ L1".
- Context: `reply_enabled = lifecycle_settings(settings).reply`; với `kb_draft`: `instructor=None`, `below_threshold=False`, `kb_draft_run=True`, `reply_enabled=False`.
- `WRITE_TOOL_TARGETS` thêm `"reply_to_requester": ("Communication", "communication")`, `"create_kb_draft": ("HD Article", "article")`; cả hai rơi vào hàng "tạo mới không trả trước/sau" của `_entry_values` (U3 3.2) → `value_after = arguments`. Không thêm hàng.
- `build_reason_system(..., reply_tools=granted.reply_block)`.

### 3.9 `erp_ai/agent/prompts.py` (sửa)

- `build_initial_message`: `requester_reply` → `TASK_REQUESTER_REPLY` ("Người tạo phiếu vừa trả lời tin của bạn. Đọc tin mới nhất, trả lời người tạo bằng reply_to_requester nếu được cấp, hoặc ghi comment cho người phụ trách."); `kb_draft` → `TASK_KB_DRAFT` ("Phiếu đã đóng. Soạn đúng một bài CSKT nháp bằng create_kb_draft: vấn đề và các bước đã giải quyết, lấy từ chi tiết giải quyết và comment của người phụ trách; không chép tên người, email, số điện thoại, mật khẩu.").
- `KNOWLEDGE_SOURCES_BLOCK` (luôn ghép sau `CONVENTIONS` khi có tool): "Ba nguồn tra trước khi kết luận: bài CSKT (search_knowledge_base), HDSD (search_manuals), phiếu cũ (search_resolved_tickets). Nêu nguồn đã dùng trong phần Căn cứ. Tool trả 'chưa có kho HDSD' hoặc không có kết quả thì không nêu nguồn đó." (AC-47, AC-48).
- `REPLY_BLOCK` ⇔ `reply_tools`: "TRẢ LỜI NGƯỜI TẠO. reply_to_requester gửi tới người tạo phiếu (họ đọc được). Comment thì người tạo không đọc được. Đầu mục F: trả lời phải có ít nhất một nguồn, không có thì hỏi lại. Độ tin cậy dưới ngưỡng: chỉ hỏi lại (kind=question)." Không có câu cấm nào trong `CORE_PROMPT` trái khối này → `PROMPT_CONFLICT_PAIRS` không thêm cặp.

### 3.10 `erp_ai/agent/tools/read.py` — `search_resolved_tickets` (AC-48)

- Từ: `knowledge.tokenize(query)`; rỗng → `"câu tìm cần ít nhất một từ dài 2 ký tự"`. Lọc thô: `or_filters` LIKE **từng từ** trên `subject`, `description`, `resolution_details` (`_like_pattern`), `limit_page_length=SEARCH_SCAN_MAX`.
- Điểm = số từ khác nhau của câu tìm có mặt nguyên từ trong `tokenize(subject + description + resolution_details)`; bỏ điểm 0; sắp điểm giảm, `modified` giảm.
- Lọc phiếu loại trừ trước khi cắt `limit` (vị từ của `policy`, mục 1.4 U2).
- `resolution_details` trống → thêm `"resolver_comments"`: tối đa `RESOLVER_COMMENTS_MAX = 3` comment mới nhất của người trong `_assign` của phiếu, `owner ≠ AGENT_USER`, mỗi comment `_clean(…, COMMENT_MAX_CHARS)`; không có → `[]`.
- Chữ ký tool, tên tool, `limit` 1..10 không đổi (hợp đồng tool không vỡ; thêm khóa là thêm).

### 3.11 `erp_ai/hooks.py` (sửa)

- `doc_events["Communication"] = {"on_update": "erp_ai.handlers.communication_on_update"}` (R-1 (d): Helpdesk không móc Communication; `on_update` vì **B-3**).
- `doc_events["Task"] = {"on_update": "erp_ai.handlers.task_on_update"}`.
- `doc_events["HD Ticket"]["on_update"]` giữ đường dẫn (`erp_ai.handlers.ticket_on_update`).
- `scheduler_events["cron"]["0 * * * *"]` thêm `"erp_ai.agent.lifecycle.scan_silent_f_tickets"` (khóa `cron` theo ADR-033 QĐ 6; tạo khóa nếu U4a/U5a chưa có). Quét nhẹ, chạy ở hàng `default` 300 s, không cần xếp `long`.

### 3.12 `run_log.py`, `erp_ai_log.json` (F-5)

`run_log.TRIGGERS = ("ticket_insert", "comment_mention", "requester_reply", "kb_draft")`; option `trigger` thêm hai giá trị; mô tả `trigger` thêm "requester_reply: người tạo phiếu trả lời sau tin của bot; kb_draft: soạn bài CSKT nháp khi phiếu đóng."; cụm từ `"requester_reply"`, `"kb_draft"` trong `DOCTYPE_CONFIG["ERP AI Log"]["phrases"]`. `BOT_ACTION_TRIGGERS` không đổi (job vòng đời dùng `scheduled_job`).

### 3.13 Contract for later units

| Tên | Chữ ký / giá trị | Module | Người dùng sau |
|---|---|---|---|
| `TRIGGER_REQUESTER_REPLY`, `TRIGGER_KB_DRAFT` | `"requester_reply"`, `"kb_draft"` | `agent/queue.py` | U1/`policy.RUN_LIMIT_TRIGGERS` (literal), U5a báo cáo |
| `enqueue_lifecycle_job` | `(ticket_name: str) -> bool` | `agent/queue.py` | — |
| `lifecycle_settings`, `LifecycleSettings` | mục 3.6 | `agent/lifecycle.py` | U5a/U5b nếu cần đọc công tắc |
| `send_to_requester` | `(ticket_name, html) -> str` | `agent/lifecycle.py` | U5b (nếu nhắc hạn gửi người tạo) |
| `KNOWLEDGE_TOOL_NAMES`, `REPLY_GROUP`, `KB_DRAFT_GROUP` | mục 3.2–3.3 | tools | U7 (thêm nhóm phải giữ vế `¬kb_draft_run`) |
| `TOOL_*` của lifecycle | mục 3.6 | `agent/lifecycle.py` | U5a `ACTION_KIND_BY_TOOL` (INT-U6b-1) |

---

## 4. Luồng

**F-1 Trả lời người tạo (happy).** Lần chạy (`ticket_insert` / `comment_mention` / `requester_reply`) → `grant` có `requester_reply` khi `reply_enabled` → model gọi `reply_to_requester` → kiểm 1–5 → `reply_via_agent` (Communication `Sent`, Email Queue; `first_responded_on` đặt ở `on_communication_update`, R-1 (b)) → mục hành động `reply_to_requester` trong dòng `reason` (AC-10).
Lỗi: thiếu Email Account → `ValidationError` trước khi ghi (R-1 (c)) → `ok=false`, savepoint không cần rollback; tool không được cấp → lý do có sẵn của `execute_tool`.

**F-2 Người tạo trả lời.** Email (`receive.py:730` insert, `:738` save) hoặc cổng (`create_communication_via_contact`) → `Communication.on_update` → `communication_on_update` → (lọc) → `enqueue_agent_run(..., requester_reply, communication_name)` sau commit → worker `run_for_ticket` → `enter_agent_session` → chốt bật, `can_send_ticket`, giới hạn ngày (đếm) → `_requester_reply_skip` → mức, `run_instructor` (nhánh chủ phiếu) → `_reason`. Hết giới hạn → `_log_skip("daily_limit")` (+ comment của U4b), 0 lời gọi model.

**F-3 Task xong → Resolved.** Người lưu Task (có `ai_ticket`, `status` đổi) → `task_on_update` → `enqueue_lifecycle_job` → `run_task_lifecycle` (phiên agent, hàng `default`, 300 s) → mục 3.6. Chạy lại / sự kiện lặp → bước (4) thấy `Resolved` → 0 thay đổi.

**F-4 Đóng F im lặng.** Mỗi giờ: `scan_silent_f_tickets` → mục 3.6. Đổi `status` → `ticket_on_update` thấy `flags.erp_ai_silent_close` → không soạn CSKT.

**F-5 Soạn CSKT.** Phiếu sang nhóm `Resolved` (người, hoặc F-3) → `_maybe_enqueue_kb_draft` → `enqueue_agent_run(..., kb_draft)` → runner: không kiểm giới hạn ngày, `_kb_draft_skip`, L0 bỏ → `grant` dòng cố định (`read` + `kb_draft`) → model đọc phiếu, comment, có thể tìm CSKT → `create_kb_draft` → HD Article `Draft` (U6a chặn mọi trạng thái khác).

**Lời gọi ra ngoài và thời hạn.** Model: trong runner, hạn `JOB_TIMEOUT_S` (có sẵn). Email: Email Queue, không gửi đồng bộ (`delayed=True`, R-1). Báo cáo: trong job runner, chịu `deadline` của lượt; báo cáo chậm là rủi ro ghi ở mục 6. HDSD: ngân sách 10 s của U6a.

---

## 5. Quyền

| Thao tác | Ai / phiên | Chốt (server) |
|---|---|---|
| Tool trả lời | tài khoản agent, khi `reply_enabled` | `grant` (ranh giới cấp), `read._check_ticket`, `is_agent()` của Helpdesk, người nhận cố định `raised_by` |
| Bài CSKT nháp | tài khoản agent, trigger `kb_draft` | `grant` dòng cố định; HD Article DocPerm `Agent` (không `ignore_permissions`); `article_guard` (U6a) chỉ cho `Draft` của bot |
| Đổi `status` HD Ticket theo N-2 | tài khoản agent qua `enter_agent_session` | công tắc, `status_change_refusal`, `has_permission` write HD Ticket của Helpdesk (R-1 U-2) |
| Error Log | Lõi `system_read` (đường bỏ quyền duy nhất, U6a); tool chỉ gọi | ADR-034 QĐ 2; tập role agent không đổi |
| Báo cáo | phiên agent, `query_report.run` kiểm quyền Report/`ref_doctype` | danh sách cho phép + kiểm lại `ref_doctype` lúc chạy (ADR-034 QĐ 3) |
| Đọc bài nháp của bot | `ERP AI Instructor` | DocPerm đọc HD Article (cần từ U0, mục 1.3) |
| Handler | phiên người gây sự kiện | chỉ đọc và xếp hàng (ADR-033 QĐ 2) |

Không DocType nào của app bị ghi dưới phiên agent ngoài `write_bot_action`/`write_entry` (đường hợp lệ M5 có sẵn, ADR-033 QĐ 8).

---

## 6. Migration và rollback, quan sát

- **Lên:** `cmd.migrate` đồng bộ option `trigger` (chỉ thêm, 0 DDL — Select là `varchar`); `scheduler_events` mới được đồng bộ ở migrate (R-5). Không dữ liệu nào bị đổi.
- **Xuống:** revert các commit U6b rồi `cmd.migrate`. Dòng ERP AI Log đã có `trigger = requester_reply|kb_draft` giữ nguyên (append-only, không bao giờ lưu lại nên Select không bị kiểm lại). Bài HD Article nháp và Communication đã gửi là dữ liệu nghiệp vụ, giữ. **Đối chiếu:** trước và sau xuống, `SELECT trigger, COUNT(*) FROM tabERP AI Log GROUP BY trigger` bằng nhau; `COUNT(*) FROM tabHD Article WHERE ai_source_ticket IS NOT NULL` bằng nhau.
- **Rollback hành vi không cần deploy:** 4 công tắc mặc định tắt; tắt công tắc là dừng đường đó từ lần chạy/quét kế tiếp.
- **Quan sát (STD-OPS-5):** handler — một dòng `_log_decision` mỗi quyết định (`requester_reply`, `kb_draft`, `task_lifecycle`); runner — dòng `skip` có lý do mới (`event_moved`, `already_handled`, `kb_exists`, `no_resolution_content`, `not_closed`, `kb_draft_off`); job vòng đời — dòng `bot_action` mỗi lần đổi trạng thái, một dòng/ngày khi chưa cấu hình, Error Log `TITLE_LIFECYCLE_FAILED` khi lỗi; tool trả lời — logger `warning` khi thiếu Email Account.
- **Rủi ro còn lại:** R-1 U-1..U-7 (Email Account, IMAP, `restrict_tickets_by_agent_group`) kiểm trên site trước khi bật `reply_enabled`; báo cáo nặng có thể ăn hạn của lượt (giới hạn bằng danh sách cho phép do người chọn).

---

## 7. Touchpoints

Nguồn: ô "Module, file chạm" của U6b (`arch-impact.md:180`): `registry.py`, `runner.py`, `queue.py`, `handlers.py`, `hooks.py`, tool mới, `prompts.py`, file job vòng đời.

| Đường dẫn | Mới/sửa | Trong ô arch-impact? | Mục |
|---|---|---|---|
| `erp_ai/agent/tools/registry.py` | sửa | có | 3.2 |
| `erp_ai/agent/runner.py` | sửa | có | 3.8 |
| `erp_ai/agent/queue.py` | sửa | có | 3.1 |
| `erp_ai/handlers.py` | sửa | có | 3.7 |
| `erp_ai/hooks.py` | sửa | có | 3.11 |
| `erp_ai/agent/prompts.py` | sửa | có | 3.9 |
| `erp_ai/agent/tools/knowledge_read.py` | mới | có (tool mới) | 3.3 |
| `erp_ai/agent/tools/reply.py` | mới | có (tool mới) | 3.4 |
| `erp_ai/agent/tools/kb_draft.py` | mới | có (tool mới) | 3.5 |
| `erp_ai/agent/lifecycle.py` | mới | có (file job vòng đời) | 3.6 |
| `erp_ai/agent/run_log.py` | sửa | **không — theo phán quyết F-5** (option `trigger` của U6b đi cùng `run_log.TRIGGERS`) | 3.12 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json` | sửa | **không — theo F-5** | 3.12 |
| `erp_ai/agent/tools/read.py` | sửa | **không — ghi rõ:** AC-48 sửa `search_resolved_tickets` đang nằm ở đây; brief của team-leader liệt kê file này. Tech-lead xác nhận khi lập plan; nếu không chấp nhận → `DESIGN_CONFLICT` cho AC-48 | 3.10 |
| `erp_ai/tests/test_architecture.py` | sửa | **không — bắt buộc bởi ghim F-2** (`ENQUEUE_TARGETS` +1 đích `"erp_ai.agent.lifecycle.run_task_lifecycle"`) | 8 |
| Test cùng chỗ (`test_{name}.py`): `erp_ai/agent/tools/test_registry.py`, `test_read.py` (sửa); `erp_ai/agent/tools/test_knowledge_read.py`, `test_reply.py`, `test_kb_draft.py`, `erp_ai/agent/test_lifecycle.py` (mới); `erp_ai/agent/test_queue.py`, `test_agent_runner.py`, `test_run_log.py` (sửa); `erp_ai/agent/test_prompts.py` (mới nếu U1 chưa tạo, ngược lại sửa); `erp_ai/tests/test_handlers.py`, `test_doctype_descriptions.py` (sửa) | — | test của các file trên | 8 |

**So khớp đường dẫn mới với `structure.allowed_new_file_roots` = `['erp_ai', 'docs', '.github']`:**

| Đường dẫn mới | Gốc khớp |
|---|---|
| `erp_ai/agent/tools/knowledge_read.py`, `reply.py`, `kb_draft.py` | `erp_ai` |
| `erp_ai/agent/lifecycle.py` | `erp_ai` |
| `erp_ai/agent/tools/test_knowledge_read.py`, `test_reply.py`, `test_kb_draft.py`, `erp_ai/agent/test_lifecycle.py`, `erp_ai/agent/test_prompts.py` | `erp_ai` |

**So với `protected_paths` = `['.env', '.env.*', '**/*.pem', '**/*.key', 'license.txt']`:** 0 đường dẫn khớp (không file `.env*`, `.pem`, `.key`, `license.txt`).

**Không có:** `constants.py` (hai trigger đặt ở `queue.py`, A-U6b-1), `policy.py` (mục 1.4), `daily_report.py` (INT-U6b-1).

---

## 8. Test plan

Chạy từng file bằng `cmd.test_one`; trước merge `cmd.test`. Đồng hồ giả lập bằng tham số `now` / `frappe.utils.now_datetime` patch (STD-TEST-6). Email: `frappe.flags.in_test` giữ Email Queue, không gửi thật.

| AC / ràng buộc | Test (`file::Class::name`) | Ca |
|---|---|---|
| AC-40 tắt → không tool | `erp_ai/agent/tools/test_registry.py::TestKnowledgeGrant::test_reply_tool_absent_when_switch_off` | `reply_enabled=False` × 4 mức → `"reply_to_requester" ∉ grant(...).names()` |
| AC-40 bật → có tool | `::TestKnowledgeGrant::test_reply_tool_present_when_switch_on` | L1..L3, kể cả `below_threshold=True` |
| AC-40 người tạo không Agent đọc được | `erp_ai/agent/tools/test_reply.py::TestReplyToRequester::test_customer_without_agent_role_reads_reply` | user chỉ có `HD Customer` gọi `helpdesk.helpdesk.doctype.hd_ticket.api.get_one` → `communications` chứa nội dung |
| AC-40 chỉ người tạo | `::test_sends_only_to_raised_by` | `Communication.recipients == raised_by`; tool không nhận tham số người nhận |
| AC-40 nhóm loại trừ / cờ không AI | `::test_excluded_team_refused`, `::test_ai_opt_out_refused` | `ok=False`, 0 Communication |
| AC-40 F không nguồn | `::test_category_f_answer_without_source_refused`, `::test_category_f_answer_with_source_sent`, `::test_category_f_question_without_source_sent` | lý do 5; có nguồn → gửi; câu hỏi → gửi |
| AC-40 dưới ngưỡng | `::test_below_threshold_answer_refused_question_allowed` | độ tin cậy 69, ngưỡng 70: `answer` → lý do 3; `question` có `?` → gửi; `question` không `?` → lý do 4 (biên) |
| AC-40 mốc phản hồi | `::test_first_responded_on_set_after_first_reply` | trước: rỗng; sau lần đầu: có; lần hai: không đổi |
| AC-40 lỗi Email Account (R-1 (c)) | `::test_missing_outgoing_account_refused_no_comment` | `reply_via_agent` patch ném `frappe.OutgoingEmailError` → `ok=False`, 0 Communication, 0 Comment |
| AC-40 log (AC-10) | `erp_ai/agent/test_agent_runner.py::TestKnowledgeActions::test_reply_writes_one_action_entry` | stub model gọi tool một lần → đúng 1 mục `reply_to_requester` dạng `ACTION_KEYS` |
| ADR-034 "không comment" | `test_reply.py::TestReplyToRequester::test_never_calls_comment_api` | AST `reply.py`, `lifecycle.send_to_requester`: 0 `new_comment`/`add_comment` |
| AC-41 người tạo trả lời → 1 job | `erp_ai/tests/test_handlers.py::TestRequesterReply::test_requester_reply_enqueues_one_job` | bot đã `Sent`, người tạo `Received` → 1 `enqueue_agent_run(..., requester_reply, communication_name=…)` |
| AC-41 tin của bot | `::test_bot_own_message_no_job` | `Sent` và `owner=AGENT_USER` → 0 |
| AC-41 người khác | `::test_other_person_no_job` | `Received` từ email khác `raised_by` → 0, lý do `not_requester` |
| AC-41 **bẫy B-1** thư mở phiếu | `::test_opening_message_no_job` | tạo phiếu qua cổng (`create_communication_via_contact(new_ticket=True)`) và qua email → 0 job, lý do `no_bot_message_before` |
| AC-41 **bẫy B-2** `on_update` hai lần | `::test_on_update_twice_one_job` (insert rồi `save()` cùng giao dịch → 1 lời `frappe.enqueue`); `test_agent_runner.py::TestRequesterReplyRun::test_second_event_after_run_already_handled` (job đã chạy, `on_update` lần sau ở giao dịch khác → dòng `skip` `already_handled`, 0 lời gọi model) |
| AC-41 **bẫy B-3** phiếu gộp | `test_handlers.py::TestRequesterReply::test_merged_ticket_uses_final_reference`; `test_agent_runner.py::TestRequesterReplyRun::test_event_moved_skipped` | job xếp theo phiếu đích; job của phiếu cũ → `event_moved` |
| AC-41 hết giới hạn ngày | `test_agent_runner.py::TestRequesterReplyRun::test_daily_limit_reached_no_model_call` | `runs_today` = giới hạn → 0 lời gọi model, 1 dòng `skip daily_limit` (comment đếm ở test U4b) |
| AC-41 đặt lại đồng hồ | `erp_ai/agent/test_lifecycle.py::TestSilentClose::test_requester_reply_resets_clock` | bot ngày 0, người tạo ngày 2, quét ngày 4 → không đóng; bot lại ngày 4, quét ngày 7 → đóng |
| AC-42 bảng chân trị | `test_lifecycle.py::TestStatusGuard::test_truth_table` | `subTest` 6 đầu mục × {BGĐ, không BGĐ, chưa cấu hình} × 2 công tắc × 2 đường: chỉ (F, không BGĐ, cấu hình, công tắc đóng-F bật) đóng; chỉ (≠E, không BGĐ, cấu hình, công tắc Task bật) Resolved |
| AC-42 (a) cả hai tắt | `::test_switches_off_no_status_change_any_job` | gọi `run_task_lifecycle` và `scan_silent_f_tickets` → `status` không đổi, 0 dòng log |
| AC-42 (c) chưa cấu hình | `::test_origin_not_configured_one_log_per_day` | `field_origin` rỗng; `field_origin` tên không có trên phiếu; `origin_board_value` rỗng → 0 đổi; gọi 3 lần cùng ngày → 1 dòng; ngày sau → thêm 1 |
| AC-42 (d) | `::test_every_status_change_has_log_and_one_comment` | mỗi đường: 1 dòng `bot_action`, đúng 1 Comment, `owner` = `AGENT_USER` (ADR-033 Ràng buộc) |
| AC-43 | `test_lifecycle.py::TestResolveOnTasksDone::test_two_of_two_completed_resolved`, `::test_one_of_two_not_changed`, `::test_no_task_not_changed`, `::test_cancelled_plus_completed_resolved`, `::test_all_cancelled_not_changed`, `::test_closed_ticket_not_changed`, `::test_repeated_event_changes_once`, `::test_task_without_ticket_link_not_counted` | 7 ca của spec + A-11 |
| AC-43 handler | `test_handlers.py::TestTaskLifecycle::test_status_change_enqueues_once`, `::test_task_without_ai_ticket_no_job` | |
| AC-44 | `test_lifecycle.py::TestSilentClose::test_2d23h_not_closed`, `::test_3d_closed_with_comment_and_notice`, `::test_reply_on_day2_not_closed`, `::test_board_f_not_closed`, `::test_category_e_not_closed`, `::test_category_c_not_closed`, `::test_f_never_replied_not_closed`, `::test_notice_failure_not_closed` | biên 71 h / 72 h; thông báo là Communication `Sent` tới `raised_by` |
| AC-45 trigger | `test_handlers.py::TestKbDraftTrigger::test_resolved_enqueues_kb_draft`, `::test_excluded_team_no_job`, `::test_ai_opt_out_no_job`, `::test_silent_close_no_job`, `::test_switch_off_no_job`, `::test_second_close_no_second_job` | |
| AC-45 bài | `erp_ai/agent/tools/test_kb_draft.py::TestCreateKbDraft::test_draft_linked_to_ticket`, `::test_second_article_refused`, `::test_agent_cannot_publish`, `::test_excluded_seed_string_absent` (NFR-1: phiếu nhóm loại trừ có chuỗi gieo, đóng → 0 HD Article chứa chuỗi), `::test_instructor_lists_bot_drafts` | trạng thái = `Draft`; lưu `Published` dưới agent → `PermissionError` |
| AC-45 không nội dung, mức | `test_agent_runner.py::TestKbDraftRun::test_no_resolution_content_skipped`, `::test_level_l0_skipped`, `::test_not_counted_in_daily_limit` (cần mục 1.4 U1) | |
| AC-45 dòng cố định | `test_registry.py::TestKnowledgeGrant::test_kb_draft_fixed_row` | mọi tổ hợp công tắc/thẩm quyền × `kb_draft_run=True` → tên = `read` ∪ {`create_kb_draft`}, mọi cờ False |
| AC-46 | `erp_ai/agent/tools/test_knowledge_read.py::TestSearchKnowledgeBase::test_published_only`, `::test_reversed_words_found`, `::test_more_matches_ranked_first`, `::test_limit_from_setting` | 6 bài (2 nháp, 1 lưu trữ); `knowledge_search_limit` = 2 |
| AC-47 | `::TestSearchManuals::test_match_returns_document_heading_line`, `::test_no_match_empty`, `::test_not_configured_refused` | kho giả 3 file `.md`; rỗng → `MANUALS_NOT_CONFIGURED` |
| AC-47 câu cuối | `::TestSearchManuals::test_manuals_not_readable_by_read_source` | `read_source` trên file của kho → từ chối (hành vi U6a, kiểm lại ở mức tool) |
| AC-48 | `erp_ai/agent/tools/test_read.py::TestSearchResolvedTickets::test_excluded_ticket_not_returned`, `::test_empty_resolution_returns_resolver_comments`, `::test_empty_resolution_no_comment`, `::test_bot_comments_excluded`, `::test_ranked_by_word_matches` | 5 phiếu Resolved theo spec; tối đa 3 comment |
| AC-48 prompt | `erp_ai/agent/test_prompts.py::TestKnowledgeSources::test_reason_prompt_names_three_sources` | prompt chứa 3 tên tool và "Căn cứ" |
| AC-49 | `test_knowledge_read.py::TestRunReport::test_empty_list_refused`, `::test_not_in_list_refused`, `::test_row_limit_20`, `::test_ticket_based_report_refused` (đặt danh sách bằng `db.set_single_value` lách form, `ref_doctype` HD Ticket → từ chối), `::test_agent_permission_error_refused`, `::test_cells_redacted` | báo cáo test 25 dòng |
| AC-50 | `::TestReadErrorLogs::test_time_and_keyword_filter`, `::test_limit`, `::test_seeded_key_masked`, `::test_agent_roles_unchanged` | `frappe.get_roles(AGENT_USER)` trước = sau, không có System Manager |
| Hồi quy M4 (AC-1, U1) | `test_registry.py::TestGrantTable::test_grant_matrix_matches_snapshot` | so ảnh chụp trên `names() − KNOWLEDGE_TOOL_NAMES`; `reply_enabled`, `kb_draft_run` mặc định → bảng U1 không đổi. Lý do sửa test: AC-46..AC-50 thêm tool đọc (NFR-8, STD-TEST-5) |
| ADR-003/013, F-2 | `erp_ai/tests/test_architecture.py::TestScannersCatchViolations::test_enqueue_targets_pinned` | tuple 6 đích; `check_enqueue_call_shape` xanh |
| ADR-033 "handler chỉ xếp hàng", "không import Cổng model" | `test_handlers.py::TestRequesterReply::test_handlers_write_nothing` (đếm `save`/`db.set_value` = 0 trên 3 handler mới), `test_lifecycle.py::TestArchitecture::test_no_model_gateway_import` (AST) | |
| ADR-033 "không ghi Setting dưới agent" | `test_lifecycle.py::TestArchitecture::test_setting_unchanged_after_jobs` | `modified` của ERP AI Setting trước = sau hai job |
| `queue` biên | `erp_ai/agent/test_queue.py::TestEnqueueAgentRun::test_requester_reply_requires_communication_name`, `::test_communication_name_rejected_for_other_triggers`, `::TestEnqueueLifecycleJob::test_job_id_dedupe_and_target` | |
| F-5 | `erp_ai/agent/test_run_log.py::TestTriggers::test_triggers_match_queue_and_json` | `run_log.TRIGGERS` ⊇ `queue.VALID_TRIGGERS`; option JSON = `TRIGGERS ∪ CHANGE_TRIGGERS ∪ BOT_ACTION_TRIGGERS`; `test_doctype_descriptions.py` có 2 cụm từ mới |

### Đối chiếu AC (Done criteria)

- AC của spec cho U6b (`spec.md:210-220`, AC-42 theo `spec-addendum-1.md:94`): AC-40, AC-41, AC-42, AC-43, AC-44, AC-45, AC-46, AC-47, AC-48, AC-49, AC-50.
- AC có test ở bảng trên: AC-40, AC-41, AC-42, AC-43, AC-44, AC-45, AC-46, AC-47, AC-48, AC-49, AC-50. Khớp 11/11; 11/11 có ca lỗi/biên.
- Bẫy của R-1 (d) có test riêng: B-1 `test_opening_message_no_job`; B-2 `test_on_update_twice_one_job` + `test_second_event_after_run_already_handled`; B-3 `test_merged_ticket_uses_final_reference` + `test_event_moved_skipped`. Bẫy kênh gửi R-1 (c): `test_missing_outgoing_account_refused_no_comment`.

---

## Assumptions decided by the team

| # | Chọn | Vì | Phương án khác | Sai thì sửa |
|---|---|---|---|---|
| A-U6b-1 | Hằng `TRIGGER_REQUESTER_REPLY`, `TRIGGER_KB_DRAFT` ở `agent/queue.py` | `constants.py` ngoài ô file U6b; `VALID_TRIGGERS` đã ở đây | `constants.py` cạnh `TRIGGER_*` cũ | Chuyển hai dòng sang `constants.py`, `queue.py` import lại |
| A-U6b-2 | Bốn tool tri thức ở nhóm `read` (mọi mức > L0) | AC-49 đòi L1+ = điều kiện của `read`; Error Log đã che bí mật, giới hạn | Nhóm riêng cho Error Log/báo cáo | Thêm một dòng `GRANT_TABLE` |
| A-U6b-3 | Dưới ngưỡng, tool trả lời vẫn được cấp nhưng chỉ nhận `kind=question` có `?` | AC-40 "dưới ngưỡng chỉ được hỏi lại" (hỏi lại phải tới được người tạo) | Rút tool khi dưới ngưỡng (người tạo không nhận được câu hỏi) | Thêm `¬below_threshold` vào dòng `requester_reply` |
| A-U6b-4 | Hai tin người tạo khi job chưa chạy → một lần chạy (`job_id` theo phiếu) | Lần chạy đọc mọi tin; tiết kiệm giới hạn NFR-2 | `job_id` theo Communication | Đổi `job_id` của trigger này |
| A-U6b-5 | Phiếu nhóm loại trừ / cờ không dùng AI cũng không bị job vòng đời đổi trạng thái | "Không dùng AI" bao cả việc tự động của bot; spec không nói | Cho phép (không gửi nội dung cho model) | Bỏ vế `not_sendable` ở `status_change_refusal` |
| A-U6b-6 | Lịch đóng F gọi thẳng `erp_ai.agent.lifecycle.scan_silent_f_tickets` từ `hooks.py`, mỗi giờ | Lịch là Cửa vào; `schedules.py` (U5a) và `tasks.py` (FEAT-005) ngoài ô file | Hàm một dòng ở `schedules.py` | Thêm hàm bọc ở `schedules.py`, đổi đường dẫn trong `hooks.py` |
| A-U6b-7 | "1 thông báo tới người tạo" (AC-44) gửi bằng `reply_via_agent` trước khi đổi `Closed`; gửi lỗi → không đóng | Comment không tới người tạo (R-1 (a)); đóng mà không báo trái AC-44 | Đóng rồi báo; đóng dù báo lỗi | Đổi thứ tự bước (6)–(7) |
| A-U6b-8 | `RESOLVER_COMMENTS_MAX = 3` | spec "tối đa số comment cuối" không cho số; A-13 không có | 1 hoặc 5 | Đổi hằng |
| A-U6b-9 | Người gửi so bằng `extract_email_id(...).casefold()` của `sender` và `raised_by` | Thư có dạng `Tên <email>` | So chuỗi thẳng | Đổi hàm so trong `lifecycle` |
