Feature: FEAT-007
Stage: design
Author-agent: designer
Date: 2026-11-14
Approved-by:
<!-- G2b không áp dụng (team.py: chỉ cổng G5). -->

# Design addendum 1 — U4b Phân loại phần lõi và U8 Đầu mục C phần 1 (FEAT-007)

**Phạm vi.** U4b của `arch-impact.md:179`: AC-17 (ghi độ trễ), AC-21, AC-22 (comment hỏi, "Căn cứ"), AC-23, AC-24 (đưa 7 trường vào lượt). U8 của `arch-impact.md:182`, chỉ AC-62 (BA note) và AC-63 (nhiều Task có ước lượng). Kèm phần runner mà `design.md:29-33` đã giao U4b cho AC-19 (`created_labels`), AC-25 (truyền Hạn hoàn thành), AC-27 (ghi người theo dõi), AC-28 (đăng comment tách phiếu): phần quyết định thuần đã có ở U4a (`design.md:379-409`), U4b chỉ nối vào runner. Ngoài phạm vi: AC-64, U5b, U6b, U7. Văn bản AC theo `spec-addendum-1.md` mục 2.1 (AC-22, AC-23 `[changed]`), còn lại theo `spec.md:179-241`.

**Luật thi hành (trích, không chép):** ADR-030 QĐ 3, 4 (ngưỡng là đầu vào của hàm cấp; một vị từ duy nhất) và Ràng buộc (runner không lọc tool; `prompts.py` không đọc cấu hình); ADR-033 QĐ 1 (mọi ghi phía phiếu dưới tài khoản agent), QĐ 2 và Ràng buộc 3 (`handlers.py` không `save()`/`db.set_value` HD Ticket, chỉ xếp hàng), QĐ 5 (đơn vị nhật ký = mục hành động, một hàm dựng mục); ADR-019 QĐ 7 (bước định tuyến ghi vào dòng `classify`); ADR-020, ADR-021 (đơn vị ghi của bước định tuyến, savepoint). Hợp đồng dùng lại, không định nghĩa lại: `design-addendum-1-U1.md` mục 3.9, `design-addendum-1-U3.md` mục 3.10, tên chuyển chỗ `design-w0-fixes.md` mục 3.

---

## 1. Bối cảnh

### 1.1 Explore summary (đọc trực tiếp, 2026-11-14, nhánh `develop` @ `1918db2`)

| Chỗ | Hiện trạng | U4b / U8 đổi |
|---|---|---|
| `erp_ai/handlers.py:27-29` | `ticket_before_insert` chỉ đặt cờ `erp_ai_prefilled` khi đủ 3 trường; giá trị người gõ không được lưu | lưu tập trường người gõ vào `ai_created_labels` (AC-19, AC-21) |
| `handlers.py:62-81` | `ticket_validate`: người sửa khi chưa có dòng `classify` có dự đoán → bỏ qua `no_prediction`, không đánh dấu (A1-5 (b)) | đánh dấu `Người` cả khi chưa có dòng log (AC-21) |
| `handlers.py:70-71` | đổi dưới `AGENT_USER` → `changed_by_agent` | giữ; là chốt "ghi qua quyền (2) không tính là người" (AC-21, A1-5 (c)) |
| `erp_ai/agent/tools/route_ticket.py:41-71` | `apply_route` ghi mọi trường `decision` có giá trị; người điền một phần bị đè (A1-5 (a)) | **không sửa** (ngoài file U4b); runner đưa vào một `decision` đã bỏ trường người điền |
| `erp_ai/agent/tools/write_ticket.py:43-86` | `set_classification` gọi `decide_route` rồi ghi cả 3 trường | bỏ trường người điền; nhận `confidence_pct` |
| `write_ticket.py:102-112` | `post_comment` đăng mọi nội dung; `route_ticket.post_routing_comment` gọi lại hàm này | tách: hàm nội bộ giữ nguyên; tool `post_comment` có `kind` và kiểm "Độ tin cậy"/"Căn cứ"/BA note |
| `write_ticket.py:132-148` | `create_task` chỉ nhận tiêu đề, mô tả; không chống trùng, không giới hạn (A3-10) | ước lượng giờ bắt buộc, chống trùng theo (phiếu, tiêu đề), trần mỗi lần chạy (AC-63) |
| `erp_ai/agent/prompts.py:244-256` | bước phân loại chỉ gửi tiêu đề + nội dung (A1-3) | thêm 7 trường khi đã cấu hình (AC-24) |
| `prompts.py:337-362` | `build_initial_message` gửi 7 trường cố định của phiếu | thêm `ticket.fields` (AC-24); gợi ý đầu mục C (U8) |
| `erp_ai/agent/runner.py:144-147`, `:223-234` | chạm giới hạn ngày → dòng `skip`, không comment | 1 comment mỗi phiếu mỗi ngày (AC-23) |
| `runner.py:264-272`, `:620-629` | lỗi cổng model → dòng có `error`, không comment (A3-8) | 1 comment cho chuỗi lỗi (AC-23) |
| `runner.py:281-289` | `decide_route` không nhận hạn, người theo dõi | truyền `due_at`, `due_field_configured`, `d_watcher`, `now` (U4a đã thêm tham số) |
| `runner.py:337-358`, `:457-472` | comment định tuyến chỉ khi có câu lỗi; thành công chỉ ở log (A3-8) | đúng 1 comment gộp cho định tuyến thành công (AC-23) |
| `runner.py:578-583`, `:600` | lượt suy luận đọc 7 cột cố định; `classification=None` cho lần `@ai` | đọc thêm trường cấu hình; đưa đầu mục đã biết |
| `runner.py:609-658` | không đảm bảo có comment hỏi khi dưới ngưỡng | comment hỏi dự phòng ở lượt cuối (AC-22) |
| `constants.py:13`, `classification.py:32` | độ tin cậy là nhãn (A1-12) | U1 thêm số; U4b đọc số qua `policy` |
| ERPNext `Task.expected_time` (`erpnext/projects/doctype/task/task.json:169`) | Float, giờ | nơi lưu ước lượng (AC-63) |
| `erp_ai/agent/ops_data.py` | **chưa có** trên `develop` (U5a đợt 0) | U8 import `BA_NOTE_MARKER` từ đây |

### 1.2 Tên U4b / U8 dựa vào (nguồn)

| Tên | Nguồn | Có trên `develop` hôm nay? |
|---|---|---|
| `ToolContext.below_threshold`, `.run_id`, `.instructor`, `.effective_level` | U1 `design-addendum-1-U1.md:166`, `:291` | Không (U1) |
| `policy.latest_classification`, `confidence_threshold`, `is_below_confidence`, `main_path_level`, `effective_level(settings, *, over_budget)`, `is_over_budget` | U1 `:277-284` | Không (U1) |
| `Classification.confidence_pct` | U1 `:302` | Không (U1) |
| `ASK_TOOL_NAMES = {"post_comment"}`, `grant`, `Grant.ask_only_block` | U1 `:286`, `:289` | Không (U1) |
| `authority.enter_agent_session`, `run_for_ticket(..., comment_name)` | U1 `:293`, `:298` | Không (U1) |
| `run_log.action_entry`, `write_entry` (kiểm `ACTION_KEYS`), `runner._entry_values` (hàng "tạo mới" phủ `post_comment`, `create_task`) | U3 `design-addendum-1-U3.md:238-250` | Không (U3) |
| `runner._route_action(..., *, value_before, value_after, instructor)` | U3 `:166` | Không (U3) |
| `decide_route(..., due_at, due_field_configured, d_watcher, now)`, `RouteDecision.watcher`, `classification.split_request_comment` | U4a `design.md:381-409` | Không (U4a đợt 0) |
| `BA_NOTE_MARKER = "**BA note**"` | U5a `design.md:337`, `design-w0-fixes.md:201` (`erp_ai/agent/ops_data.py`) | Không (U5a đợt 0) |
| Trường Setting `field_ticket_nature`, `field_erp_module`, `field_origin`, `field_due_date`, `field_project`, `field_item_code`, `field_serial_no`, `d_ticket_watcher`, `max_tasks_per_run`, `confidence_threshold` | U0 `design.md:122`, `:127`, `:142`, `:146` | Không (U0) |
| Cột ERP AI Log `created_labels`, `predicted_confidence_pct`, `split_requested`, `split_requests` | U0 `design.md:233-236` | Không (U0) |
| Trường HD Ticket `ai_confidence_pct` | U0 `design.md:249` | Không (U0) |
| `CLASSIFIED_BY_AI`, `CLASSIFIED_BY_HUMAN`, `CLASSIFICATION_FIELDS`, `AGENT_USER`, `LOG_DOCTYPE`, `SETTING_DOCTYPE`, `LOGGER_NAME` | `erp_ai/constants.py` | Có |
| `post_routing_comment`, `apply_route`, `create_routed_task` | FEAT-006 `route_ticket.py` | Có (không sửa) |

**Điều kiện bắt đầu.** U4b: U0, U4a, U5a (đợt 0), U1, U3 đã merge vào `develop` (arch-impact: U4b phụ thuộc U1, U3). U8 (AC-62, AC-63): sau U4b (cùng khối `TOOLS` của `write_ticket.py` và cùng `build_initial_message`, mục 7.2). Cắt sớm hơn → `DESIGN_CONFLICT`, dừng.

### 1.3 Cần từ U0 / U1 / U3 (không tự đặt)

| Cần | Chủ | Có trong hợp đồng? |
|---|---|---|
| **Trường tùy biến HD Ticket `ai_created_labels`** (Small Text, `hidden`, `read_only`, `no_copy`, permlevel 0, `module` app, thêm vào `_ai_field_specs` cạnh `ai_confidence_pct`) | U0 (`install.py`) | **Thiếu.** `design.md:233` đặt `created_labels` trên dòng log do runner ghi, nhưng runner chạy sau khi Helpdesk điền mặc định nên không còn biết người gõ gì; cần một chỗ lưu lúc `before_insert`. Không có trường này thì AC-21 (người điền một phần) và AC-19 không làm được trong file của U4b. Phương án thay nếu U0 từ chối: U1 thêm `created_labels` vào tham số `enqueue_agent_run` (A-U4b-1) |
| Ghi `ai_confidence_pct` lên phiếu ở bước định tuyến (một dòng trong `apply_route`) | ngoài U4b (`route_ticket.py` không có trong ô file của U4b) | **Mở.** U1 (`design-addendum-1-U1.md:62`) giao việc này cho U4b, nhưng `arch-impact.md:179` không cho U4b sửa `route_ticket.py`. U4b chỉ ghi `ai_confidence_pct` qua tool `set_classification`. Team-leader chọn: thêm `route_ticket.py` vào ô của U4b (một dòng `ai_confidence_pct=classification.confidence_pct`, một test), hoặc để phiếu chỉ hiện nhãn cho tới đơn vị sau |
| Mọi tên ở bảng 1.2 dòng U1, U3 | U1, U3 | Có |

---

## 2. Mô hình dữ liệu

U4b, U8 **không thêm** DocType hay trường (mọi trường do U0; thiếu `ai_created_labels`, mục 1.3). Đọc và ghi:

| Thực thể | Đọc / ghi | Ai, khi nào | Mẫu truy cập |
|---|---|---|---|
| HD Ticket `ai_created_labels` | ghi (giá trị JSON `{ticket_type?, agent_group?, priority?}`, chỉ khóa người gõ; không gõ gì → `""`) | `handlers.ticket_before_insert`, trên chính doc đang insert (không `save()` thêm) | đọc theo tên phiếu, 1 lần mỗi lần chạy |
| HD Ticket 7 trường cấu hình | đọc | runner, bước phân loại và lượt suy luận | `frappe.db.get_value` theo tên, gộp vào lời đọc đang có |
| HD Ticket `ticket_type`, `agent_group`, `priority`, `ai_classified_by`, `ai_confidence_pct` | ghi | `apply_route` (không đổi), `set_classification` | — |
| ERP AI Log dòng `classify` | ghi `created_labels`, `split_requested`, `split_requests`, `human_corrected_to` (chỉ khi phiếu đã `Người` trước dòng log đầu, A-U4b-4); `actions` thêm mục `add_watcher`, `post_notice` | runner | chỉ số `ticket`, `creation` có sẵn |
| ERP AI Log dòng `skip`, `reason` | `actions` thêm mục `post_notice` | runner | — |
| Comment (HD Ticket, `Comment`, `owner = AGENT_USER`) | ghi; đọc để chống trùng theo tiền tố nội dung và `creation` | tool `post_comment`, `post_notice` | lọc `reference_name`, `owner`, `creation ≥ mốc`, `content LIKE '<tiền tố>%'` — vài comment mỗi phiếu |
| Task (`ai_ticket`, `subject`, `expected_time`) | ghi; đọc chống trùng | tool `create_task` | lọc `ai_ticket` + `subject` |
| Document Follow | ghi qua `frappe.desk.form.document_follow.follow_document` | runner, bước định tuyến (AC-27) | — |

Khóa chống trùng (mỗi ý định một khóa, giữ khóa bằng khóa dòng phiếu `SELECT … FOR UPDATE` trong giao dịch của lượt):

| Ý định | Khóa | Cùng khóa, khác nội dung |
|---|---|---|
| BA note (AC-62) | (phiếu, comment của agent bắt đầu bằng `BA_NOTE_MARKER`) | từ chối `ok=false` "phiếu đã có BA note" |
| Task (AC-63) | (`ai_ticket`, `subject` đã `strip`, so không phân biệt hoa thường theo collation DB) | từ chối, nêu tên Task đã có |
| Thông báo chạm giới hạn ngày / vượt ngân sách | (phiếu, tiền tố thông báo, ngày hệ thống) | không đăng lần hai |
| Thông báo lần chạy lỗi | (phiếu, tiền tố, sau dòng thành công gần nhất) | không đăng lần hai |
| Comment hỏi dưới ngưỡng (AC-22) | `run_id` (cờ trong `frappe.flags`, sống trong một job) | lần hai trong cùng lần chạy bị từ chối |
| Comment tách phiếu (AC-28) | dòng `classify` có `split_requested = 1` của phiếu | không đăng lần hai |
| Người theo dõi D (AC-27) | Document Follow (phiếu, người) | không thêm lần hai |

---

## 3. API / hợp đồng

Mọi hàm là Python nội bộ; không endpoint, không whitelisted method mới. Hợp đồng chạm tới model (schema tool) chỉ **thêm** tham số; tên tool không đổi (`ASK_TOOL_NAMES` của U1 vẫn đúng). Một dạng lỗi: tool trả `{"ok": False, "reason": <chuỗi ≤ REASON_MAX>}` (có sẵn, `write_ticket.py:22-23`); hàm nội bộ ném `ValueError` cho tham số sai.

### 3.1 `handlers.py` (U4b)

```python
CREATED_LABELS_FIELD = "ai_created_labels"

def ticket_before_insert(doc, method=None)   # thêm: ghi CREATED_LABELS_FIELD
def ticket_validate(doc, method=None)        # thêm: giữ CREATED_LABELS_FIELD; đánh dấu người khi chưa có log
```

| Hàm | Hành vi | Lỗi / lối ra |
|---|---|---|
| `ticket_before_insert` | Giữ `erp_ai_prefilled`. Nếu `doc.meta.has_field(CREATED_LABELS_FIELD)`: `typed = {f: doc.get(f) for f in CLASSIFICATION_FIELDS if doc.get(f)}`; `doc.set(CREATED_LABELS_FIELD, json.dumps(typed, ensure_ascii=False) if typed else "")`. Ghi đè mọi giá trị client gửi (không giả mạo được lúc tạo) | không ném; trường chưa có (trước migrate) → bỏ qua |
| `ticket_validate` | (1) Đầu hàm, trước lối ra sớm: phiếu không mới và `has_value_changed(CREATED_LABELS_FIELD)` → trả về giá trị trước (`get_doc_before_save()`), mọi phiên. (2) Như nay đến `skip_reason`. Khác: khi `latest` rỗng hoặc không có `predicted_category` (chưa có dòng log có dự đoán) và phiên không phải `AGENT_USER` → vẫn `doc.ai_classified_by = CLASSIFIED_BY_HUMAN`, **không** đặt cờ `erp_ai_human_corrected` (không có dòng để cập nhật), `_log_decision(..., "recorded", "human_changed_before_prediction")` | không ném |

Không thêm `save()`/`db.set_value` trên HD Ticket (ADR-033 Ràng buộc 3): cả hai thay đổi nằm trên doc đang được người lưu.

### 3.2 `tools/write_ticket.py` (U4b, rồi U8)

```python
# U4b
REASON_HUMAN_FILLED = "người đã điền lúc tạo phiếu"
COMMENT_KINDS = ("de_xuat", "hoi")                       # U8 nối "ba_note"
CONFIDENCE_LINE = re.compile(r"Độ tin cậy:\s*(\d{1,3})\s*%")
EVIDENCE_HEADER = "Căn cứ"
ASK_FOOTER = "Độ tin cậy phân loại: {pct} (ngưỡng {threshold}%). Bot chỉ hỏi, chưa ghi gì trên phiếu."
REASON_NO_CONFIDENCE = "comment đề xuất thiếu dòng 'Độ tin cậy: NN%' (NN từ 0 đến 100)"
REASON_NO_EVIDENCE = "comment thiếu phần '**Căn cứ:**' có nội dung"
REASON_ASK_ONLY = "độ tin cậy dưới ngưỡng: chỉ được đăng comment hỏi (kind = hoi)"
REASON_ONE_ASK = "đã đăng comment hỏi trong lần chạy này"
NOTICE_PREFIXES = {
    "daily_limit": "Bot tạm dừng trên phiếu này hôm nay:",
    "over_budget": "Bot đang chạy ở mức L1:",
    "run_failed": "Bot chưa xử lý xong phiếu này:",
    "ask_fallback": "Bot chưa đủ chắc để xử lý phiếu này:",
}
REASON_NOTICE_SENT = "đã thông báo"

def created_labels(raw: str | None) -> dict
def keep_human_fields(decision: RouteDecision, labels: dict) -> RouteDecision
def section_text(content: str, header: str) -> str | None
def asked_in_run(run_id: str) -> bool
def post_comment(args: dict, ctx: ToolContext) -> dict            # giữ nguyên hành vi (route_ticket dùng)
def post_comment_tool(args: dict, ctx: ToolContext) -> dict       # handler mới của tool "post_comment"
def post_notice(ticket_name: str, notice: str, body: str, since: datetime) -> dict
def set_classification(args: dict, ctx: ToolContext) -> dict      # thêm bỏ trường người điền, confidence_pct

# U8
BA_NOTE_SECTIONS = ("Mục tiêu", "Phạm vi", "Tính năng sẵn có", "Rủi ro", "Câu hỏi mở")
REASON_BA_NOTE_MISSING = "BA note thiếu hoặc rỗng mục: {sections}"
REASON_BA_NOTE_FEATURE = "mục 'Tính năng sẵn có' phải bắt đầu bằng Có hoặc Không và có 'Nguồn:' không rỗng"
REASON_BA_NOTE_EXISTS = "phiếu đã có BA note"
REASON_BA_NOTE_NOT_C = "BA note chỉ dành cho phiếu đầu mục C ở mức L1 trở lên"
DEFAULT_MAX_TASKS_PER_RUN = 10
REASON_NO_ESTIMATE = "Task cần ước lượng bằng giờ, số dương"
REASON_TASK_DUPLICATE = "phiếu đã có Task cùng tiêu đề: {task}"
REASON_TASK_LIMIT = "đã tạo đủ {limit} Task trong lần chạy này"
def create_task(args: dict, ctx: ToolContext) -> dict             # thêm ước lượng, chống trùng, trần
```

| Hàm | Hành vi chính xác | Lỗi |
|---|---|---|
| `created_labels` | `""`/None → `{}`. JSON dict chỉ khóa thuộc `CLASSIFICATION_FIELDS` → dict đó. JSON hỏng hoặc không phải dict → `{f: True for f in CLASSIFICATION_FIELDS}` (fail-closed: coi cả 3 do người điền, bot không ghi trường nào) và 1 dòng `frappe.logger(LOGGER_NAME).warning("erp_ai created_labels invalid ticket=…")` do người gọi ghi | không ném |
| `keep_human_fields` | Với mỗi `f` trong `labels`: `dataclasses.replace(decision, f=None)` và nối `{"field": f, "reason": REASON_HUMAN_FILLED}` vào `notes` (tuple). `assignee`, `needs_task`, `watcher` không đổi. `labels` rỗng → trả nguyên `decision` | không ném |
| `section_text` | Tìm dòng bắt đầu bằng `**<header>:**` (cho phép không có `**`); trả văn bản sau dấu `:` cộng các dòng sau cho tới dòng kế bắt đầu bằng `**…:**`, đã `strip`; không có → `None` | — |
| `asked_in_run` | `run_id in frappe.flags.get("erp_ai_asked_runs", set())` | — |
| `post_comment` | Thân hiện nay (`write_ticket.py:102-112`), không kiểm `kind` | như nay |
| `post_comment_tool` | Kiểm theo thứ tự: (1) `kind ∉ COMMENT_KINDS` → `_fail("kind phải là một trong …")`; (2) `ctx.below_threshold`: `kind != "hoi"` → `REASON_ASK_ONLY`; `asked_in_run(ctx.run_id)` → `REASON_ONE_ASK`; `section_text(content, EVIDENCE_HEADER)` rỗng → `REASON_NO_EVIDENCE`; nội dung đăng = `content + "\n\n" + ASK_FOOTER.format(pct=f"{p}%" nếu p không None, ngược lại "chưa có", threshold=…)` với `p` từ `policy.latest_classification(ctx.ticket_name)[1]`, ngưỡng từ `policy.confidence_threshold(frappe.get_single(SETTING_DOCTYPE))`; thành công → thêm `ctx.run_id` vào `frappe.flags.erp_ai_asked_runs`; (3) `kind == "de_xuat"`: `CONFIDENCE_LINE` không khớp hoặc số > 100 → `REASON_NO_CONFIDENCE`; `section_text` rỗng → `REASON_NO_EVIDENCE`; (4) `kind == "hoi"` trên ngưỡng: không kiểm thêm; (5) đăng bằng `post_comment`. Bị từ chối → không có Comment nào | `{"ok": False, "reason": …}`; model đọc lý do trong `tool_result` |
| `post_notice` | `notice ∈ NOTICE_PREFIXES` (khác → `ValueError`). Khóa dòng phiếu: `frappe.db.get_value(TICKET_DOCTYPE, ticket_name, "name", for_update=True)`. Có Comment `owner = AGENT_USER`, `reference_name = ticket_name`, `comment_type = "Comment"`, `creation ≥ since`, `content LIKE '<tiền tố>%'` → `{"ok": False, "reason": REASON_NOTICE_SENT}`. Ngược lại đăng `"<tiền tố> <body>"` qua `post_comment` (dựng `ToolContext` tối thiểu không cần: tách thân đăng thành `_post(ticket_name, content)` dùng chung cho `post_comment`) | `ValueError` cho `notice` lạ |
| `set_classification` | Như nay, thêm: sau `decide_route` trong `_mapped_values`, `decision = keep_human_fields(decision, created_labels(doc.get(CREATED_LABELS_FIELD)))` (trường người điền vào `skipped` với `REASON_HUMAN_FILLED`). Tham số tùy chọn `confidence_pct` (int 0..100, không `bool`): có → thêm `ai_confidence_pct` vào `values` nếu phiếu có trường | `confidence_pct` sai kiểu/khoảng → `_fail("confidence_pct phải là số nguyên 0..100")` |
| `create_task` (U8) | Thứ tự: không `ctx.instructor` → như nay; `_task_refusal`; `expected_hours` phải là `int`/`float`, không `bool`, `> 0` → ngược lại `REASON_NO_ESTIMATE`; khóa dòng phiếu (như `post_notice`); `subject.strip()` trùng Task có `ai_ticket = phiếu` → `REASON_TASK_DUPLICATE`; số Task đã tạo trong `ctx.run_id` (cờ `frappe.flags.erp_ai_run_tasks[run_id]`) ≥ `max_tasks_per_run` (`frappe.db.get_single_value(SETTING_DOCTYPE, "max_tasks_per_run")`, rỗng → `DEFAULT_MAX_TASKS_PER_RUN`) → `REASON_TASK_LIMIT`; tạo Task như nay + `expected_time = float(expected_hours)`; tăng bộ đếm. Trả `{"ok": True, "task": name}` | `{"ok": False, …}`, không tạo gì |
| `post_comment_tool`, `kind == "ba_note"` (U8) | Trước bước (5): phiếu phải có `policy.latest_classification(...)[0] == "C"` và `policy.main_path_level(settings, ctx.effective_level, "C") != "L0"` → ngược lại `REASON_BA_NOTE_NOT_C`; `CONFIDENCE_LINE` bắt buộc (như `de_xuat`); mỗi mục của `BA_NOTE_SECTIONS` có `section_text` khác rỗng → ngược lại `REASON_BA_NOTE_MISSING` liệt kê mục thiếu; mục "Tính năng sẵn có" bắt đầu bằng "Có" hoặc "Không" và `section_text(…, "Nguồn")` khác rỗng (dòng `**Nguồn:**` trong mục, hoặc "Nguồn:" cùng dòng) → ngược lại `REASON_BA_NOTE_FEATURE`; khóa dòng phiếu; đã có comment agent bắt đầu bằng `BA_NOTE_MARKER` → `REASON_BA_NOTE_EXISTS`; nội dung đăng = `BA_NOTE_MARKER + "\n" + content` (bỏ marker trùng nếu model đã viết). Dưới ngưỡng, nhánh (2) chặn trước (chỉ `hoi`) → "chỉ có phần câu hỏi mở" (AC-62) | như trên |

Schema tool (khối `TOOLS`):

| Tool | U4b | U8 |
|---|---|---|
| `set_classification` | thêm `confidence_pct: {"type": "integer", "minimum": 0, "maximum": 100}` (không bắt buộc) | — |
| `post_comment` | `handler=post_comment_tool`; thêm `kind: {"type": "string", "enum": COMMENT_KINDS}` bắt buộc; mô tả: "kind=de_xuat: nhận định, phương án hoặc báo việc đã làm; phải có dòng 'Độ tin cậy: NN%' và phần '**Căn cứ:**' có nội dung. kind=hoi: câu hỏi; khi độ tin cậy dưới ngưỡng chỉ được dùng kind này, một lần, và vẫn phải có '**Căn cứ:**' nêu vì sao chưa chắc." | enum nối `"ba_note"`; mô tả thêm: "kind=ba_note: chỉ phiếu đầu mục C, một lần mỗi phiếu; đủ 5 mục **Mục tiêu:**, **Phạm vi:**, **Tính năng sẵn có:** (Có/Không, **Nguồn:**), **Rủi ro:**, **Câu hỏi mở:** và dòng 'Độ tin cậy: NN%'." |
| `create_task` | — | thêm `expected_hours: {"type": "number", "exclusiveMinimum": 0}` bắt buộc; mô tả thêm "Mỗi Task một việc, có ước lượng giờ; tiêu đề trùng Task đã có của phiếu bị từ chối; tối đa theo cấu hình mỗi lần chạy." |

### 3.3 `prompts.py` (U4b, rồi U8)

```python
# U4b
TICKET_FIELD_LABELS = {"ticket_nature": "Tính chất phiếu", "erp_module": "Phân hệ ERP",
    "origin": "Nguồn phát sinh", "due_date": "Hạn hoàn thành", "project": "Dự án",
    "item_code": "Mã hàng", "serial_no": "Số sê-ri"}   # khóa = phần sau "field_" của 7 trường U0
FIELD_VALUE_MAX_CHARS = 200
def ticket_fields_text(fields: dict[str, object]) -> str
def build_classify_request(subject, description, departments=(), ticket_fields: dict | None = None) -> dict
def build_initial_message(ticket, comments, trigger, classification, ticket_fields: dict | None = None) -> str
# U8
TASK_CATEGORY_C: str
```

- `ticket_fields_text`: khóa ∈ `TICKET_FIELD_LABELS`, giá trị khác rỗng → dòng `- <nhãn>: <_clean(str(giá trị), FIELD_VALUE_MAX_CHARS)>` theo thứ tự của `TICKET_FIELD_LABELS`; không còn dòng → `""`. Khóa lạ → `ValueError`.
- `build_classify_request`: `ticket_fields` rỗng/None → yêu cầu **trùng từng byte** bản hiện nay (eval offline giữ nguyên). Có → nội dung user = `ticket_text(...) + "\n\nTrường của phiếu:\n" + ticket_fields_text(...)`. Phần `system` không đổi (cache giữ).
- `build_initial_message`: `ticket_fields` có dòng → `payload["ticket"]["fields"] = {nhãn: giá trị đã cắt}`; rỗng → không có khóa `fields` (payload trùng bản hiện nay).
- U8: `TASK_CATEGORY_C` (ý, dev giữ ý): "Phiếu đầu mục C: tìm tính năng sẵn có bằng search_source trước, rồi đăng BA note bằng post_comment kind = ba_note (một lần mỗi phiếu). Nếu có tool create_task, tách việc thành các Task, mỗi Task có ước lượng giờ." `build_initial_message` ghép `"\n" + TASK_CATEGORY_C` sau dòng việc khi `(classification or {}).get("category") == "C"`.
- `prompts.py` không đọc cấu hình (ADR-011 QĐ 3): nhãn là hằng, giá trị do runner truyền.

### 3.4 `runner.py` (U4b)

```python
TICKET_FIELD_SETTINGS = tuple(f"field_{key}" for key in TICKET_FIELD_LABELS)   # 7 tên U0
ROUTE_DONE = "Bot đã phân loại phiếu: {fields}."
ROUTE_NO_CHANGE = "Bot đã phân loại phiếu, các trường đã đúng nên không đổi."
ROUTE_ASSIGNED = "Đã gán cho {person}."
ROUTE_TASK = "Đã tạo Task {task}."
ROUTE_WATCHER = "Đã thêm {person} làm người theo dõi."
FIELD_LABELS = {"ticket_type": "Loại", "agent_group": "Nhóm", "priority": "Ưu tiên"}
NOTICE_TOOL = "post_notice"
DAILY_LIMIT_BODY = "đã dùng hết {limit} lần chạy trong ngày. Bot xử lý tiếp từ ngày mai; cần gấp thì nhờ người phụ trách."
OVER_BUDGET_BODY = "chi phí AI tháng này đã vượt ngân sách, bot chỉ đọc, phân loại và đề xuất, không làm thay đổi gì ngoài phiếu. Quản trị tăng ngân sách trên ERP AI Setting để mở lại."
RUN_FAILED_BODY = "{cause}. Bot sẽ thử lại ở lần quét kế tiếp; cần gấp thì nhờ người phụ trách."
ASK_FALLBACK_BODY = "anh/chị bổ sung giúp mô tả cụ thể hơn (màn hình, mã chứng từ, bước làm).\n**Căn cứ:** nội dung phiếu chưa đủ để chọn đầu mục và nhóm."
CAUSE_GATEWAY = "lỗi khi gọi mô hình AI"
CAUSE_TIME = "hết thời gian của lần chạy"

def _ticket_fields(settings) -> tuple[dict[str, str], list[str]]
def _ticket_field_values(ticket_name: str, field_map: dict[str, str]) -> dict[str, object]
def _notice(ticket_name, notice, body, since, instructor=None) -> dict | None
def _last_success_at(ticket_name) -> datetime | None
def _route_lines(result, assigned, task, watcher) -> list[str]
def _watch_unit(watcher, context, actions, errors) -> str | None
```

| Chỗ | Hành vi chính xác |
|---|---|
| `_ticket_fields` | Với mỗi tên trong `TICKET_FIELD_SETTINGS`: giá trị Setting rỗng → khóa vào `missing` ("chưa cấu hình trường <nhãn>"); có nhưng `frappe.get_meta("HD Ticket").has_field` sai (trường bị xóa sau khi lưu) → `missing` ("trường <tên> không có trên phiếu"); còn lại `field_map[key] = fieldname`. `missing` khác rỗng → **1** dòng `logger.info("erp_ai ticket_fields run_id=%s missing=%s", …)` mỗi lần chạy (AC-24 "1 dòng log"). Gọi **một lần** ở `_run` sau khi nạp Setting |
| `_ticket_field_values` | Một `frappe.db.get_value("HD Ticket", name, list(field_map.values()), as_dict=True)`; trả `{key: value}` cho giá trị khác rỗng |
| `_run` (d) | Chạm giới hạn ngày: `_log_skip(..., "daily_limit", notice=…)`; thông báo chỉ khi `policy.effective_level(settings, over_budget=False) != "L0"` (không đọc ngân sách ở bước này) với `since` = 00:00 hôm nay (`frappe.utils.getdate()`, cùng mốc `runs_today`) |
| `_run` sau (e) | `over_budget` (U1) đúng ∧ `policy.effective_level(settings, over_budget=False) ∈ {"L2","L3"}` → `notices = [_notice(…, "over_budget", OVER_BUDGET_BODY, since=00:00 hôm nay)]` (bỏ phần tử None), đăng **ngay trước** `_reason` (sau `_classify` thành công) và truyền vào `_reason`. Mức gốc L1 hoặc L0 → không có gì để báo |
| `_run`, lần chạy không phải tạo phiếu | `classification = {"category": category, "confidence_pct": pct}` từ `policy.latest_classification` (U1 đã đọc) thay vì `None` khi `category` khác None — model biết đầu mục đã phân loại; dùng cho gợi ý đầu mục C (U8) |
| `_log_skip` | thêm tham số `notice: tuple[str, str, datetime] | None = None`; có và phiếu tồn tại → `_notice(...)`; mục trả về (nếu có) vào `actions` của dòng `skip` |
| `_notice` | `write_ticket.post_notice(...)`; `ok` → `run_log.action_entry(NOTICE_TOOL, "Comment", r["comment"], True, value_after={"notice": notice}, instructor=instructor)`; không ok (đã thông báo) → `None` (không có ghi nên không có mục) |
| `_last_success_at` | `creation` lớn nhất của dòng ERP AI Log của phiếu thỏa: `entry_type = "classify"` ∧ `predicted_category` khác rỗng, hoặc `entry_type = "reason"` ∧ `stop_reason ∉ (STOP_GATEWAY_ERROR, STOP_TIME_BUDGET)`; không có → `None` (mốc = `datetime.min`) |
| `_classify` lỗi cổng (`:264-272`) | `context is not None` (mức > L0) → mục `_notice(…, "run_failed", RUN_FAILED_BODY.format(cause=CAUSE_GATEWAY hoặc CAUSE_TIME theo `exc.kind`), since=_last_success_at)` vào `actions` của chính dòng `classify` lỗi. Ở L0 → không comment (AC-23) |
| `_classify` đọc phiếu (`:254`) | đọc thêm `ai_created_labels`, `ai_classified_by` và 7 trường cấu hình trong cùng `get_value` |
| `_classify` gọi model (`:260`) | `build_classify_request(subject, description, departments(routing), ticket_fields=values)` |
| `_classify` sau parse | (1) `decide_route(..., due_at=<giá trị field_due_date nếu có>, due_field_configured="due_date" in field_map, d_watcher=settings.d_ticket_watcher or None, now=now_datetime())`; (2) `labels = write_ticket.created_labels(ticket.ai_created_labels)`; JSON hỏng → 1 dòng logger warning; `route_decision = write_ticket.keep_human_fields(decision, labels)`; (3) `values` (cột `predicted_*`) vẫn từ `decision` gốc (dự đoán của model, AC-19 cần); (4) `write_entry` thêm `created_labels=json.dumps({k: v for k, v in labels.items() if v is not True}) or None`, `human_corrected_to=json.dumps(<3 trường hiện tại>)` khi `ai_classified_by == CLASSIFIED_BY_HUMAN` (A-U4b-4); `split_text = classification.split_request_comment(classification)` và chưa có dòng `classify` nào của phiếu `split_requested = 1` → `split_requested=1`, `split_requests=json.dumps(classification.requests)`; (5) `_route(log_name, classification, route_decision, …, split_text=split_text if split mới else None)`; (6) 1 dòng `logger.info("erp_ai classify ticket=%s run_id=%s ok=%d latency_s=%d", …)` với `latency_s = (now_datetime() − creation phiếu).total_seconds()` (AC-17; không thêm trường, D-8) |
| `_route` | Sau `_apply_route_unit` thành công: `_check_sla`, `_assign_unit`, `_task_unit` như nay; thêm `watcher = _watch_unit(decision.watcher, …)` khi `decision.watcher`; rồi `lines = _route_lines(result, assigned, task, watcher) + lines` (+ `split_text` cuối nếu có); `_comment_unit(lines, …)` như nay → **đúng 1 comment** cho định tuyến thành công. `result` None (bị từ chối, ví dụ người đã phân loại) → chỉ các câu lỗi cũ (nếu có), không câu "đã phân loại" |
| `_route_lines` | `fields` = `", ".join(f"{FIELD_LABELS[f]} {v}" for f, v in result["after"].items() if f in FIELD_LABELS)`; rỗng → `ROUTE_NO_CHANGE`, ngược lại `ROUTE_DONE`; `assigned` → `ROUTE_ASSIGNED.format(person=get_fullname(assigned))`; `task` → `ROUTE_TASK`; `watcher` → `ROUTE_WATCHER`. Không chứa nội dung phiếu |
| `_watch_unit` | đã có Document Follow (`ref_doctype` "HD Ticket", `ref_docname`, `user`) → mục `_route_action("add_watcher", "HD Ticket", ticket, False, "đã theo dõi")`, trả None; ngược lại `_run_unit("add_watcher", lambda: _follow(watcher, ticket), …)` với `_follow` gọi `follow_document("HD Ticket", ticket, watcher)`; trả về falsy (người đó tắt nhận theo dõi) → `{"ok": False, "reason": "người theo dõi tắt nhận theo dõi tài liệu"}`; thành công → mục `ok=True`, `value_after={"watcher": watcher}`, trả `watcher` |
| `_reason` đọc phiếu (`:578-583`) | cột cố định + 7 trường cấu hình; `build_initial_message(ticket, labelled, trigger, classification, ticket_fields=<7 trường có giá trị>)` (giá trị lấy ra khỏi dict `ticket` trước khi dựng payload, để payload chỉ có cột cố định + `fields`) |
| `_reason` tham số | thêm `notices: list[dict] | None = None`: nối vào `actions` của **lần `write_entry` đầu tiên** (nhánh lỗi cổng hoặc lượt 1), rồi bỏ |
| `_reason` lỗi cổng (`:620-629`) | `actions` = notices còn lại + mục `_notice(…, "run_failed", …, since=_last_success_at)` |
| `_reason` lượt cuối | `final = not wants_tools or not tool_results or turn == max_turns`. `final ∧ context.below_threshold ∧ not write_ticket.asked_in_run(run_id)` → mục `_notice(…, "ask_fallback", ASK_FALLBACK_BODY + "\n\n" + ASK_FOOTER…, since=datetime.min)` thêm vào `actions` của lượt này **trước** `write_entry`; đánh dấu `asked` cho `run_id`. Kết quả: dưới ngưỡng luôn đúng 1 comment hỏi |

Runner không thêm, bớt, lọc tool (ADR-030 Ràng buộc); các chốt dưới ngưỡng ở tool là kiểm lúc thực thi, giống `execute_tool` kiểm lại cấp.

### 3.5 Contract for later units

| Tên | Chữ ký / giá trị | Module | Đơn vị gọi |
|---|---|---|---|
| `post_notice` | `(ticket_name: str, notice: str, body: str, since: datetime) -> dict`; khóa (phiếu, tiền tố, `since`) | `erp_ai/agent/tools/write_ticket.py` | U5b (AC-61 "chạm giới hạn ngày: 1 thông báo"; nhắc hạn có thể thêm khóa mới vào `NOTICE_PREFIXES` cùng commit) |
| `NOTICE_PREFIXES` | 4 khóa mục 3.2; thêm khóa = thêm một dòng | `write_ticket.py` | U5b, U6b |
| `NOTICE_TOOL` | `"post_notice"` (tên tool trong mục hành động) | `erp_ai/agent/runner.py` | người đọc: U5a báo cáo 08:00 (loại "comment") |
| `created_labels`, `keep_human_fields`, `REASON_HUMAN_FILLED` | mục 3.2 | `write_ticket.py` | U7 (đề xuất bản ghi ghi HD Ticket phải tôn trọng trường người điền nếu chạm 3 trường) |
| `COMMENT_KINDS` | `("de_xuat", "hoi", "ba_note")` sau U8 | `write_ticket.py` | U6b (tool trả lời dùng cùng luật "Căn cứ"), U7 (comment đề xuất bản ghi) |
| `CONFIDENCE_LINE`, `section_text`, `EVIDENCE_HEADER` | mục 3.2 | `write_ticket.py` | U6b (AC-40, AC-48 "nêu nguồn trong Căn cứ"), U7 (AC-33) |
| `asked_in_run` | `(run_id: str) -> bool` | `write_ticket.py` | U6b (AC-40 "dưới ngưỡng chỉ hỏi lại") |
| `CREATED_LABELS_FIELD` | `"ai_created_labels"` | `erp_ai/handlers.py` | U4a báo cáo đọc `created_labels` trên log, không đọc trường này |
| `ticket_fields_text`, `TICKET_FIELD_LABELS` | mục 3.3 | `erp_ai/agent/prompts.py` | U6b, U7 (ghi đè prompt phân loại không bỏ được phần trường vì nằm ở user message) |
| `TICKET_FIELD_SETTINGS`, `_ticket_fields` | mục 3.4 | `runner.py` | U6b (`field_origin` cho N-2 dùng cùng đọc, không đọc lại) |
| `expected_time` trên Task do bot tạo | Float giờ > 0 | Task (ERPNext) | U5a/U5b (KPI 5, kiểm mốc Task), U7 AC-64 (gắn Task vào Project) |
| BA note: comment agent bắt đầu bằng `BA_NOTE_MARKER` | dòng 1 = marker | Comment | U5a (`c_missing_ba_note`), U5b (AC-58) |

---

## 4. Luồng

**Tạo phiếu, đủ ngưỡng (happy path).** Người tạo phiếu → `ticket_before_insert` ghi `ai_created_labels` (ví dụ `{"priority": "High"}`) → Helpdesk điền mặc định → `after_insert` xếp job → runner: `enter_agent_session` (U1) → `_ticket_fields` → chốt gửi, giới hạn ngày → mức, ngân sách (U1) → `_classify`: đọc phiếu + 7 trường → model (≤ timeout gateway) → parse → `decide_route` (hạn, người theo dõi) → `keep_human_fields` bỏ `priority` → dòng `classify` (`created_labels`, `predicted_*` gốc, commit) → `_route` (savepoint): ghi Loại, Nhóm; giữ `priority` = High; gán; Task C/D; người theo dõi D; 1 comment "Bot đã phân loại phiếu: Loại …, Nhóm …. Đã gán cho …." → `_reason` (7 trường trong `ticket.fields`) → tool → mục hành động (U3).

**Dưới ngưỡng.** `_classify` → pct 69 < 70 → U1 bỏ `_route` → `_reason` với `read` + `post_comment` + khối "chỉ hỏi" → model `post_comment(kind="hoi", …Căn cứ…)` → tool thêm dòng độ tin cậy, đăng → lần gọi thứ hai bị từ chối. Model không đăng → lượt cuối runner đăng `ask_fallback`. Tổng: đúng 1 comment.

**Comment đề xuất thiếu căn cứ.** Model `post_comment(kind="de_xuat")` không có "**Căn cứ:**" → `ok=false REASON_NO_EVIDENCE` → mục `ok=false` có `reason` (U3) → model sửa và gọi lại trong lượt sau.

**Phiếu C (U8).** Lượt suy luận có `TASK_CATEGORY_C` → `search_source` → `post_comment(kind="ba_note")` → kiểm 5 mục, khóa phiếu, chống trùng → đăng `**BA note**…` → có người ra lệnh: `create_task(subject, description, expected_hours)` × n ≤ `max_tasks_per_run`.

**Lỗi và bỏ qua.**

| Tình huống | Kết quả |
|---|---|
| chạm giới hạn ngày, mức > L0 | dòng `skip` + 1 comment trong ngày (lần sau cùng ngày: dòng `skip`, 0 comment) |
| vượt ngân sách, mức gốc L2/L3 | chạy ở L1 + 1 comment trong ngày |
| lỗi cổng ở phân loại hoặc suy luận, mức > L0 | dòng có `error` + 1 comment; lỗi tiếp theo trước lần thành công kế → 0 comment |
| agent tắt, L0, phiếu nhóm loại trừ, cờ không dùng AI | 0 comment (chỉ log hoặc logger), như nay |
| job sập ngoài hai bước trên (ngoại lệ trong `_run`) | Error Log `TITLE_RUN_FAILED`, 0 comment (A-U4b-6) |
| `ai_created_labels` hỏng | không ghi trường nào trong 3, logger warning |
| trường cấu hình không còn trên phiếu | bỏ trường đó, 1 dòng logger, lần chạy tiếp tục |
| `follow_document` trả falsy | mục `add_watcher` `ok=false`, comment định tuyến không có câu theo dõi |
| hai job cùng phiếu cùng lúc (tạo phiếu ∥ `@ai`) | khóa dòng phiếu trong `post_notice`, BA note, `create_task` tuần tự hóa; chống trùng giữ |

Không có lời gọi ra ngoài mới: model qua gateway có timeout sẵn; mọi thứ khác là DB local.

---

## 5. Quyền

- Mọi ghi mới (comment, Task, Document Follow, trường phiếu) chạy dưới `AGENT_USER` trong job (ADR-033 QĐ 1); tool kiểm `has_permission` như nay; `follow_document` dưới agent.
- `ai_created_labels` do server tính ở `before_insert` và bị giữ cố định ở `validate` (mọi phiên): người không giả mạo được "đã điền" để chặn bot.
- Ghi của bot qua công cụ bản ghi (quyền 2) hoặc Toàn quyền vào HD Ticket chạy dưới `AGENT_USER` → `ticket_validate` bỏ qua (`changed_by_agent`), không thành "sửa của người" (AC-21).
- Chốt dưới ngưỡng ở tool là lớp thứ hai; lớp quyết định là hàm cấp của U1 (chỉ `read` + `post_comment`).
- Nội dung thông báo là chữ cố định; không chứa nội dung phiếu, cấu hình thô hay lỗi kỹ thuật (STD-ERR-3); logger chỉ có mã, số, tên phiếu (STD-SEC-6).

---

## 6. Migration và rollback, quan sát

- **Schema:** không (U0; thiếu `ai_created_labels`, mục 1.3). **Dữ liệu:** không ghi lại dữ liệu cũ. Phiếu cũ không có `ai_created_labels` → `{}` → hành vi như nay (bot điền trường trống theo dự đoán).
- **Rollback:** revert commit U8 rồi U4b; không cần `cmd.migrate` (không đổi meta). Comment, Task, Document Follow, cột log đã ghi giữ nguyên (vô hại; mã cũ không đọc). Tool `post_comment` cũ không đòi `kind`: model gửi thừa `kind` → Python bỏ qua khóa thừa.
- **Đối chiếu sau deploy:** đếm dòng `classify` có `created_labels` khác rỗng ≤ số phiếu tạo mới có ít nhất một trong 3 trường; số Comment agent có tiền tố `daily_limit` mỗi ngày ≤ số phiếu có dòng `skip`/`daily_limit` ngày đó.
- **Quan sát (STD-OPS-5):** `erp_ai classify … latency_s` (AC-17); `erp_ai ticket_fields … missing` (AC-24); mục `post_notice` với `value_after.notice` (AC-23); mục `add_watcher`; mục `post_comment` `ok=false` với `REASON_NO_EVIDENCE`/`REASON_ASK_ONLY` cho biết model hay vi phạm luật; `skipped_fields` có `REASON_HUMAN_FILLED` (AC-21); `erp_ai handler … human_changed_before_prediction`.

---

## 7. Touchpoints

### 7.1 File

| File | Đơn vị | Sửa |
|---|---|---|
| `erp_ai/handlers.py` | U4b | 3.1 |
| `erp_ai/agent/tools/write_ticket.py` | U4b, rồi U8 | 3.2 |
| `erp_ai/agent/prompts.py` | U4b, rồi U8 | 3.3 |
| `erp_ai/agent/runner.py` | U4b | 3.4 |

Đều nằm trong ô "Module, file chạm" của U4b (`arch-impact.md:179`: `runner.py`, `prompts.py`, `handlers.py`, `tools/write_ticket.py`) và U8 (`arch-impact.md:182`: `prompts.py`, `tools/write_ticket.py`; module danh mục chỉ cho AC-64, không đụng). U8 không sửa `runner.py`: BA note đi qua tool `post_comment` có sẵn trong `WRITE_TOOL_TARGETS`, nên được ghi mục hành động mà không thêm dòng. Không sửa: `route_ticket.py` (mục 1.3), `registry.py`, `policy.py`, `queue.py`, `run_log.py`.

Test (cạnh mã, `structure.tests = colocated`; không file mới):

| File | Trạng thái |
|---|---|
| `erp_ai/tests/test_handlers.py` | thêm |
| `erp_ai/agent/tools/test_write_ticket.py` | thêm; sửa test gọi tool `post_comment` không có `kind` và `create_task` không có `expected_hours` (NFR-8: AC-22, AC-63 đổi hợp đồng tool) |
| `erp_ai/agent/test_prompts.py` | thêm (file do U1 tạo) |
| `erp_ai/agent/test_agent_runner.py` | thêm |
| `erp_ai/agent/test_runner_routing.py` | thêm; sửa test FEAT-006 đếm 0 comment khi định tuyến thành công (NFR-8: AC-23) |

### 7.2 Thứ tự sửa theo khối (không hai đơn vị cùng sửa một khối cùng lúc)

Dòng theo `develop` @ `1918db2`. Thứ tự build: U1 → U3 → U4b → U8; mỗi đơn vị cắt từ `develop` sau khi đơn vị trước merge.

`erp_ai/agent/prompts.py`

| Khối | U1 | U3 | U4b | U8 |
|---|---|---|---|---|
| `CLASSIFY_PROMPT` `:14-81` | khóa `do_tin_cay_pct` | — | — | — |
| `CORE_PROMPT` `:84-132` → `core_prompt` | toàn khối | — | — | — |
| khối quyền `:155-234`, `ASK_ONLY_BLOCK`, `PROMPT_CONFLICT_PAIRS` | toàn khối | — | — | — |
| `TASK_NEW_TICKET`, `TASK_COMMENT` `:236-237` | — | — | — | thêm `TASK_CATEGORY_C` ngay sau `:237` |
| `ticket_text`, `build_classify_request` `:244-256` | — | — | thêm hằng, `ticket_fields_text`, tham số | — |
| `build_reason_system` `:313-334` | toàn hàm | — | — | — |
| `build_initial_message` `:337-362` | — | — | tham số `ticket_fields`, khóa `fields` | 2 dòng ghép `TASK_CATEGORY_C` cạnh dòng `task =` (sau U4b) |

`erp_ai/agent/runner.py`

| Khối | U1 | U3 | U4b |
|---|---|---|---|
| import `:13-44` | registry (`grant`), authority | `run_log.action_entry` | `write_ticket` (`post_notice`, `created_labels`, `keep_human_fields`, `asked_in_run`, `ASK_FOOTER`), `follow_document` |
| hằng `:61-97` | — | `ACTION_DOCTYPE_MAX` chuyển đi | thêm hằng mục 3.4 sau `:97` |
| `WRITE_TOOL_TARGETS` `:72-85` | — | — | — (U8 cũng không) |
| `run_for_ticket`, `_run` `:100-190` | (a), (e), context, `comment_name` | — | (d) thông báo; `_ticket_fields`; thông báo ngân sách trước `_reason`; `classification` cho lần không tạo phiếu |
| `_log_skip` `:223-234` | — | — | tham số `notice` |
| `_classify` `:248-323` | context sau parse, chốt `_route`, `predicted_confidence_pct` | — | đọc phiếu `:254`; gọi model `:260`; nhánh lỗi cổng `:264-272`; `decide_route` `:281-289`; `keep_human_fields`; cột log mới; logger độ trễ |
| `_route` `:326-358` | — | — | `_watch_unit`, `_route_lines`, `split_text` |
| `_route_action`, `_run_unit` `:361-390` | — | thân → `action_entry` | chỉ gọi |
| `_assign_unit` … `_apply_route_unit` `:393-490` | — | trước/sau vào `_route_action` | — |
| `_reason` `:570-658` | `:584-599` (cấp tool, cờ) | — | `:578-583`, `:600`, `:620-629`, lượt cuối trước `write_entry` `:643` |
| `_run_tool`, `_action` `:661-700` | — | `_action`, `_entry_values` | — |

`erp_ai/agent/tools/write_ticket.py`: U1, U3 không sửa. U4b: `_mapped_values`, `set_classification`, `post_comment` (tách `_post`), hàm mới, `TOOLS[0..2]`. U8 sau U4b: `create_task`, nhánh `ba_note` trong `post_comment_tool`, `COMMENT_KINDS`, `TOOLS[2..3]`.

`erp_ai/handlers.py`: U1 sửa `comment_after_insert` `:119`; U4b sửa `ticket_before_insert` `:27-29`, `ticket_validate` `:62-81`; U6b thêm hàm mới. Không trùng khối.

Song song: U6b sửa `runner.py`, `prompts.py`, `handlers.py` (arch-impact cho U4b ∥ U6b khi "xếp lượt"): U6b cắt sau U4b cho `runner.py` và `prompts.py`, hoặc trước U4b nhưng chỉ ở hàm mới; tech-lead chọn khi lập plan.

### 7.3 So khớp đường dẫn

```
new: docs/team/features/FEAT-007/design-addendum-1-U4b-U8.md (artifact này) -> prefix "docs/" khớp
new code/test: không có
allowed_new_file_roots = ["erp_ai", "docs", ".github"]
protected_paths = [".env", ".env.*", "**/*.pem", "**/*.key", "license.txt"]
modified (4 nguồn + 5 test, đều dưới erp_ai/): không file nào khớp protected_paths
```

---

## 8. Test plan

Chạy từng file bằng `cmd.test_one`, cả app bằng `cmd.test`. Stub cổng model (trả JSON phân loại có `do_tin_cay_pct` theo ca, và các lượt `tool_use` theo kịch bản), không mạng; mốc thời gian đặt bằng cách ghi `creation` của bản ghi test, không đọc đồng hồ thật để so (STD-TEST-6). Mỗi test tự đặt Setting (mức, ngưỡng, 7 trường, `max_tasks_per_run`) và trả lại.

| AC | Test (`file::name`) | Ca biên / lỗi |
|---|---|---|
| AC-17 | `erp_ai/agent/test_agent_runner.py::TestClassifyLatency::test_success_row_written_at_result_time` | `creation` phiếu = lúc chạy − 6 phút → dòng `classify` có `predicted_category`, `creation(dòng) − creation(phiếu) ≥ 360 s`; logger có `latency_s` |
| AC-17 | `…test_agent_runner.py::TestClassifyLatency::test_gateway_error_row_has_no_prediction` | dòng có `error`, `predicted_category` rỗng (U4a đếm "chưa phân loại"); biên 5:00 do test báo cáo của U4a |
| AC-21 | `erp_ai/tests/test_handlers.py::TestCreatedLabels::test_before_insert_records_typed_fields_only` | 8 ca: rỗng, 3 tập 1 trường, 3 tập 2 trường, đủ 3; client gửi sẵn `ai_created_labels` giả → bị ghi đè |
| AC-21 | `…test_handlers.py::TestCreatedLabels::test_created_labels_frozen_after_insert` | người sửa trường → giá trị cũ; dưới agent cũng vậy |
| AC-21 | `erp_ai/agent/test_runner_routing.py::TestHumanFilledFields::test_partial_fill_kept_blank_filled` | 6 tập con × L1, L2, L3 (subTest): trường người điền không đổi, trường còn lại = quyết định của bot, `ai_classified_by` = AI, `skipped_fields` có `REASON_HUMAN_FILLED` |
| AC-21 | `…test_runner_routing.py::TestHumanFilledFields::test_log_keeps_model_prediction_and_created_labels` | `predicted_priority` = giá trị model; `created_labels` = tập người gõ |
| AC-21 | `erp_ai/agent/tools/test_write_ticket.py::TestHumanFields::test_set_classification_skips_created_fields` | lần `@ai` sau không đè trường người điền |
| AC-21 | `…test_write_ticket.py::TestHumanFields::test_invalid_created_labels_write_none_of_three` | JSON hỏng → 0 trường trong 3 |
| AC-21 | `erp_ai/tests/test_handlers.py::TestHumanCorrection::test_edit_before_first_log_marks_human` | không có dòng `classify` → `ai_classified_by = Người`, không cập nhật dòng log nào |
| AC-21 | `…test_runner_routing.py::TestHumanFilledFields::test_insert_run_after_pre_log_edit_writes_nothing` | `apply_route` từ chối; dòng `classify` có `human_corrected_to` |
| AC-21 | `erp_ai/tests/test_handlers.py::TestHumanCorrection::test_record_tool_write_is_not_human` | dưới `AGENT_USER`, `site_api.api_update_record` đổi `priority` có dòng log → `ai_classified_by` không thành Người |
| AC-22 | `erp_ai/agent/tools/test_write_ticket.py::TestPostCommentKinds::test_proposal_needs_confidence_and_evidence` | subTest: thiếu dòng độ tin cậy; `101%`; thiếu "Căn cứ"; "Căn cứ" rỗng trước header kế; đủ → đăng. Bị từ chối → 0 Comment |
| AC-22 | `…test_write_ticket.py::TestPostCommentKinds::test_bad_kind_refused` | `kind` thiếu, `"x"` |
| AC-22 | `…test_write_ticket.py::TestPostCommentKinds::test_below_threshold_one_question_with_footer` | `below_threshold`: `de_xuat` → `REASON_ASK_ONLY`; `hoi` thiếu Căn cứ → từ chối; `hoi` đủ → đăng, có "69% (ngưỡng 70%)"; lần hai → `REASON_ONE_ASK` |
| AC-22 | `…test_write_ticket.py::TestPostCommentKinds::test_footer_threshold_80_and_unknown_pct` | ngưỡng 80; pct None → "chưa có" |
| AC-22 | `erp_ai/agent/test_agent_runner.py::TestAskOnly::test_stub_69_70_100` | 69 → 0 ghi trường, 0 gán, 0 Task, đúng 1 comment hỏi; 70, 100 → định tuyến chạy, comment định tuyến |
| AC-22 | `…test_agent_runner.py::TestAskOnly::test_model_posts_nothing_fallback_one_comment` | mục `post_notice` `ask_fallback` ở dòng `reason` cuối |
| AC-22 | `…test_agent_runner.py::TestAskOnly::test_model_asks_twice_one_posted` | |
| AC-22 | `…test_agent_runner.py::TestAskOnly::test_threshold_80_with_75_asks` | |
| AC-22 | `…test_agent_runner.py::TestAskOnly::test_missing_evidence_error_reaches_model_comment_not_posted` | `tool_result` chứa `REASON_NO_EVIDENCE`; mục `ok=false` có `reason`; 0 Comment. Ca (3) bật + người ra lệnh do U1 kiểm (`test_low_confidence_with_instructor_and_act_now_keeps_record_tools`) |
| AC-23 | `erp_ai/agent/test_runner_routing.py::TestOneCommentPerAction::test_route_success_one_comment_lists_fields_assignee_task` | C có Task: 1 comment có Loại, Nhóm, "Đã gán", "Đã tạo Task" |
| AC-23 | `…test_runner_routing.py::TestOneCommentPerAction::test_success_with_failure_line_still_one_comment` | gán lỗi → 1 comment gồm câu đã phân loại + câu nhờ trưởng nhóm |
| AC-23 | `…test_runner_routing.py::TestOneCommentPerAction::test_no_field_change_one_comment` | `ROUTE_NO_CHANGE` |
| AC-23 | `erp_ai/agent/test_agent_runner.py::TestRunNotices::test_matrix_eight_situations` | subTest 8 ca: định tuyến thành công 1; lỗi cổng 1; vượt ngân sách ở L3 1; chạm giới hạn ngày 1; agent tắt 0; L0 0; nhóm loại trừ 0; cờ không dùng AI 0 |
| AC-23 | `…test_agent_runner.py::TestRunNotices::test_daily_limit_repeated_same_day_one_comment` | 3 lần chạm trong ngày → 1; comment cũ đặt `creation` hôm qua → thêm 1 |
| AC-23 | `…test_agent_runner.py::TestRunNotices::test_over_budget_once_a_day_only_when_level_lost` | L3 hai lần → 1; mức gốc L1 → 0 |
| AC-23 | `…test_agent_runner.py::TestRunNotices::test_failures_one_comment_until_next_success` | lỗi, lỗi → 1; thành công; lỗi → 2 |
| AC-23 | `…test_agent_runner.py::TestRunNotices::test_gateway_error_at_l0_no_comment` | |
| AC-23 (AC-10) | `…test_agent_runner.py::TestRunNotices::test_each_notice_has_one_action_entry` | mục `post_notice` có `ACTION_KEYS`, `value_after.notice`; lần bị chống trùng → 0 mục |
| AC-24 | `erp_ai/agent/test_agent_runner.py::TestTicketFields::test_four_cases` | trường tùy biến do test tạo (`create_custom_field`, xóa ở `tearDown`): có/không trường × có/không cấu hình → yêu cầu phân loại của stub và `ticket.fields` của lượt suy luận chứa "Phân hệ ERP: Kho" chỉ ở ca (có, có) |
| AC-24 | `…test_agent_runner.py::TestTicketFields::test_unconfigured_one_log_line_per_run` | logger 1 dòng có "chưa cấu hình trường"; trường bị xóa sau khi lưu → "không có trên phiếu", lần chạy tiếp tục |
| AC-24 | `erp_ai/agent/test_prompts.py::TestTicketFields::test_classify_request_unchanged_without_fields` | bằng từng byte bản cũ |
| AC-24 | `…test_prompts.py::TestTicketFields::test_fields_labelled_cut_and_ordered` | giá trị 300 ký tự → 200; HTML bị bỏ; khóa lạ → `ValueError`. Lưu tên sai bị chặn: test U0 (E-1, E-2) |
| (AC-25, AC-27, AC-28, AC-19 phần runner) | `erp_ai/agent/test_runner_routing.py::TestRunnerHooks::test_due_value_reaches_decide_route`, `::test_d_watcher_followed_once`, `::test_watcher_notify_off_logged`, `::test_split_comment_once_in_route_comment` | B hạn 10 giờ → High; D chạy 2 lần → 1 Document Follow; 4 yêu cầu → trong comment định tuyến, chạy lại không lặp, `split_requested = 1` |
| AC-62 | `erp_ai/agent/tools/test_write_ticket.py::TestBaNote::test_full_note_posted_with_marker` | dòng 1 = `BA_NOTE_MARKER`; marker model tự viết không bị lặp |
| AC-62 | `…test_write_ticket.py::TestBaNote::test_missing_or_empty_section_refused` | subTest 5 mục thiếu/rỗng; "Tính năng sẵn có" không Có/Không; thiếu "Nguồn"; thiếu độ tin cậy → lỗi liệt kê mục; 0 Comment |
| AC-62 | `…test_write_ticket.py::TestBaNote::test_second_note_refused` | chạy lại → `REASON_BA_NOTE_EXISTS`, vẫn 1 |
| AC-62 | `…test_write_ticket.py::TestBaNote::test_not_c_or_main_path_l0_refused` | đầu mục B; `level_cap_c = L0` |
| AC-62 | `…test_write_ticket.py::TestBaNote::test_below_threshold_only_question` | 69% → `ba_note` bị `REASON_ASK_ONLY`; `hoi` (câu hỏi mở) đăng được |
| AC-62 | `erp_ai/agent/test_prompts.py::TestCategoryC::test_hint_only_for_c` | C có `TASK_CATEGORY_C`; A–F khác và `classification=None` không có |
| AC-62 | `erp_ai/agent/test_agent_runner.py::TestCategoryC::test_two_runs_one_ba_note` | stub đăng BA note ở cả hai lần chạy (tạo phiếu, `@ai`) → 1 Comment; lần `@ai` có `category` C trong tin nhắn đầu |
| AC-63 | `erp_ai/agent/tools/test_write_ticket.py::TestCreateTaskEstimate::test_three_tasks_with_estimates` | `expected_time`, `ai_ticket`, đoạn liên kết phiếu |
| AC-63 | `…test_write_ticket.py::TestCreateTaskEstimate::test_missing_or_non_positive_estimate_refused` | thiếu, 0, −1, `"2"`, `True` → `REASON_NO_ESTIMATE`, 0 Task |
| AC-63 | `…test_write_ticket.py::TestCreateTaskEstimate::test_eleventh_task_in_run_refused` | mặc định 10: lần 11 → `REASON_TASK_LIMIT`; cấu hình 3 → lần 4; `run_id` mới → đếm lại |
| AC-63 | `…test_write_ticket.py::TestCreateTaskEstimate::test_same_subject_not_duplicated` | lần chạy khác, tiêu đề có khoảng trắng thừa / khác hoa thường → `REASON_TASK_DUPLICATE` |
| AC-63 (AC-10) | `erp_ai/agent/test_agent_runner.py::TestCategoryC::test_each_task_one_action_entry` | 3 `create_task` → 3 mục, `value_after` có `expected_hours` |

Test FEAT-001/004/006 ghim hành vi cũ phải sửa theo AC, ghi lý do trong commit (NFR-8, STD-TEST-5): gọi tool `post_comment` không có `kind`, `create_task` không có `expected_hours` (`test_write_ticket.py`, `test_agent_runner.py`); đếm 0 comment khi định tuyến thành công (`test_runner_routing.py`); `test_edit_without_prediction_is_skipped` hoặc tên tương đương trong `test_handlers.py` (AC-21). Ảnh chụp M4 của U1 so tên tool và cờ, không so schema → không đổi.

### Đối chiếu AC (Done criteria)

- AC giao (`arch-impact.md:179`, `:182` và lệnh giao việc): AC-17, AC-21, AC-22, AC-23, AC-24, AC-62, AC-63.
- AC có trong test plan trên: AC-17, AC-21, AC-22, AC-23, AC-24, AC-62, AC-63. Khớp 7/7.
- Phần của các AC đó **không** thuộc U4b/U8: AC-17 ba số của báo cáo (U4a); AC-22 vị từ ngưỡng, số 0–100, cấp tool, ca (3) bật (U1); AC-23 comment kết quả áp dụng đề xuất (FEAT-004 AC-28); AC-24 chặn lưu tên sai (U0); AC-62 nhắc mốc BA note (U5b).

---

## Assumptions decided by the team

| # | Chọn | Vì | Phương án khác | Sai thì sửa |
|---|---|---|---|---|
| A-U4b-1 | Lưu tập trường người gõ lúc tạo trên HD Ticket `ai_created_labels`, ghi ở `before_insert`, giữ cố định ở `validate` | runner chạy sau khi Helpdesk điền mặc định; trường bền qua quét bù và nhiều lần chạy; không cần `save()` thêm (ADR-033) | truyền qua tham số job (`queue.py` của U1; mất khi quét bù xếp lại) | U1 thêm tham số `created_labels` cho `enqueue_agent_run`; quét bù đọc từ dòng `classify` |
| A-U4b-2 | Bước định tuyến tôn trọng trường người điền bằng cách đưa `decision` đã bỏ trường vào `apply_route` | `route_ticket.py` ngoài file U4b; `_existing_values` và `_record_route` đã xử lý giá trị rỗng + `notes` | sửa `apply_route` | chuyển `keep_human_fields` vào `apply_route` khi có đơn vị được sửa file đó |
| A-U4b-3 | Mọi comment model đăng mà không phải câu hỏi (`de_xuat`) cần "Độ tin cậy: NN%" và "Căn cứ"; câu hỏi trên ngưỡng không cần | AC-22 chỉ nói "comment đề xuất"; tách bằng `kind` khai báo rõ; báo việc đã làm cũng có căn cứ (bản ghi đã tạo) | kiểm theo từ khóa trong nội dung; ba loại có "báo cáo" không kiểm | thêm giá trị vào `COMMENT_KINDS` |
| A-U4b-4 | Người sửa trước dòng log đầu: phiếu thành `Người`, bot không ghi 3 trường ở mọi lần sau; dòng `classify` sau đó ghi `human_corrected_to` để AC-19 có nhãn | đúng chữ AC-21; nhất quán với sửa sau dự đoán (A1-5) | chỉ chặn trường đã sửa | đổi điều kiện ở `ticket_validate` và `apply_route` |
| A-U4b-5 | "Lần chạy lỗi sau lần cuối" = 1 comment cho mỗi chuỗi lỗi, tính từ lần thành công gần nhất | quét bù xếp lại phiếu lỗi mỗi 15 phút; không chống trùng thì tới 5 comment/ngày | 1 comment mỗi lần lỗi; 1 mỗi ngày | đổi `since` trong `_notice(…, "run_failed", …)` |
| A-U4b-6 | Job sập ngoài lỗi cổng (ngoại lệ trong `_run`) không đăng comment, chỉ Error Log | giao dịch ở trạng thái không rõ (không rollback, `runner.py:103-104`); quét bù chạy lại | đăng trong `except` của `run_for_ticket` | thêm nhánh trong `run_for_ticket` sau rollback có chủ đích |
| A-U4b-7 | "Bỏ qua vì hết ngân sách": sau ADR-030 lần chạy không bị bỏ mà lùi về L1; comment 1 lần/phiếu/ngày khi mức gốc L2/L3 (có việc bị mất); L1 gốc không comment | AC-23 vẫn đòi người tạo thấy vì sao bot ít làm hơn; không có đường "bỏ qua" nào để comment | không comment (ca rỗng) | bỏ nhánh thông báo ngân sách trong `_run` |
| A-U4b-8 | Một lần chạy có tối đa 1 comment hỏi; đếm bằng `frappe.flags` theo `run_id` | `ToolContext` là của U1, không thêm trường; `frappe.flags` sống đúng một job | đếm Comment theo thời điểm bắt đầu lần chạy | thêm trường đếm vào `ToolContext` (U1) |
| A-U4b-9 | Người theo dõi D qua `follow_document`; người tắt nhận theo dõi → mục `ok=false`, không ép | dùng API của Frappe (STD-DESIGN-4); không ghi đè lựa chọn của người dùng | chèn thẳng Document Follow | đổi `_follow` |
| A-U4b-10 | Comment tách phiếu (AC-28) nằm trong comment định tuyến; dưới ngưỡng không đăng | "mỗi hành động 1 comment"; dưới ngưỡng chỉ có comment hỏi | comment riêng | tách `split_text` ra comment thứ hai |
| A-U8-1 | BA note là `kind = ba_note` của tool `post_comment`, không phải tool mới | tool mới cần dòng `WRITE_TOOL_TARGETS` trong `runner.py`, ngoài ô file của U8; dưới ngưỡng tự bị chặn bởi luật `hoi` (AC-62 "chỉ câu hỏi mở") | tool `post_ba_note` có tham số cấu trúc | thêm tool + một dòng `WRITE_TOOL_TARGETS` (cần thêm `runner.py` vào ô của U8) |
| A-U8-2 | Ước lượng bắt buộc cho mọi Task model tạo (mọi đầu mục), lưu ở `Task.expected_time` | AC-63 "Task không có ước lượng bị từ chối"; một tool, một luật | chỉ bắt buộc với C | thêm điều kiện đầu mục trong `create_task` |
| A-U8-3 | Trần Task đếm theo `run_id`, gồm mọi lời gọi `create_task`; Task của bước định tuyến (`create_routed_task`) không tính | AC-63 nói "mỗi lần chạy"; bước định tuyến tạo nhiều nhất 1 Task có sẵn | đếm theo phiếu | đổi khóa bộ đếm |
| A-U8-4 | Gợi ý đầu mục C trong tin nhắn đầu (`build_initial_message`), không trong system prompt | `build_reason_system` là của U1, prompt nền FEAT-004 không đổi; lần `@ai` có đầu mục nhờ U4b đưa `classification` | khối system mới có cờ | thêm cờ `category_c` vào `Grant`/`build_reason_system` (U1/U7) |

Câu hỏi nghiệp vụ: 0.
