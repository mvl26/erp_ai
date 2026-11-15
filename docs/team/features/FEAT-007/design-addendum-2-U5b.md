Feature: FEAT-007
Stage: design
Author-agent: designer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. G2b không áp (team.py: chỉ G5). -->

# Design FEAT-007 — Addendum 2, đơn vị U5b: nhắc hạn, kiểm mốc, email vượt ngân sách

**Phạm vi.** Chỉ đơn vị U5b của `arch-impact.md:114` ("Vận hành — phần cần lõi"): AC-57, AC-58 và phần "email lần đầu vượt ngân sách + 1 dòng log" của AC-61. Phần còn lại của AC-61 có chủ khác: đọc ngân sách từ tổng nhật ký sống là U1 (`design-addendum-1-U1.md` mục 3.1, 3.9); "phiếu chạm giới hạn ngày → 1 thông báo" là U4b (`post_notice`, `NOTICE_PREFIXES["daily_limit"]`). Không thiết kế U7, U8 hay đơn vị nào khác. Tuân ADR-033 (QĐ 1, 3, 5, 6, 7, 9 và Ràng buộc), ADR-030 QĐ 2 (ngân sách sống), ADR-001 (model chỉ trong runner), ADR-003/ADR-013 QĐ 2 (mọi `frappe.enqueue` ở `agent/queue.py`), ADR-024 QĐ 3 (mẫu trường mốc). Văn bản AC: `spec.md:230-231` (AC-57, AC-58), `spec.md:234` (AC-61); `spec-addendum-1.md` không đổi ba AC này (chỉ đổi A-13 bằng cách bỏ số 24 giờ của liên kết; "nhắc hạn trước 24 giờ" giữ).

## 1. Bối cảnh

### 1.1 Explore summary (đọc trực tiếp, 2026-11-14, `develop` @ `431bf55`; đợt 0 đang build trên `team/FEAT-007`)

| Câu hỏi | Kết quả | Nguồn |
|---|---|---|
| Việc theo lịch hiện có | 3 hàm trong `erp_ai/tasks.py` (`recompute_monthly_spend`, `check_privilege_escalation`, `reprobe_exhausted_keys`); mẫu lỗi: `except Exception` → `frappe.db.rollback()` + `frappe.log_error(TITLE_RUN_FAILED, "<việc> … error=<Type>")`, không ném; `commit` chỉ khi `not frappe.flags.in_test` | `erp_ai/tasks.py:24-63, 130-153` |
| Lịch | chỉ khóa `hourly`, `daily`; U4a thêm khóa `cron` `"*/15 * * * *": ["erp_ai.agent.missed_scan.scan_missed_tickets"]`, U5a thêm ba khóa 08:00 | `erp_ai/hooks.py:159-162`; `design.md:350-360` |
| Hàng đợi | `queue.py` có đúng 2 lời `frappe.enqueue` (`run_for_ticket`, `run_change`), `long`, `JOB_TIMEOUT_S`, `enqueue_after_commit`, `job_id`, `deduplicate`; U5a (F-2) thêm `SCHEDULED_JOB_TIMEOUT_S = 1200` và 3 hàm `*_job` | `erp_ai/agent/queue.py:14-60`; `design-w0-fixes.md:68-90` |
| Luật enqueue | `ENQUEUE_TARGETS` 2 chuỗi hôm nay, 5 sau U5a; `check_single_enqueue_site`, `check_enqueue_call_shape` (số lời gọi = số đích) | `erp_ai/tests/test_architecture.py:120, 529-575` |
| Luật lớp | `LAYER_RULES`: `erp_ai.agent` cấm import `eval`, `handlers`, `ticket_panel`, `tasks`, `install`, `erp_ai_agent`; **không** cấm `erp_ai.alerts` | `erp_ai/tests/test_architecture.py:55-80` |
| Email cảnh báo | `alerts.send_notice(subject, message)`: logger info + `frappe.sendmail(..., subject="[erp_ai] …", delayed=True)` khi `alert_recipients` khác rỗng; không Error Log | `erp_ai/alerts.py:11-28` |
| Phiếu nhóm loại trừ | `policy.can_send_ticket(ticket)`: cờ `ai_opt_out` hoặc `agent_group` ∈ `excluded_teams` (U2 mở rộng thêm tiền tố tiêu đề) | `erp_ai/agent/policy.py:27-48` |
| Đăng comment | `HD Ticket.new_comment(content)` (tool `post_comment`); bản ghi tạo ra mang tác giả = `frappe.session.user` | `erp_ai/agent/tools/write_ticket.py:102-112` |
| Ngân sách | trường `monthly_budget_usd` đã có; U1 đổi `is_over_budget` sang tổng `cost_usd` sống | `erp_ai_setting.json:109`; `design-addendum-1-U1.md:110-124` |
| Giờ, lượt lỡ, 300 s | giờ = `System Settings.time_zone`; lượt lỡ gộp thành một; job `cron` chạy hàng `default` 300 s; job dài xếp `long` có `job_id` + `deduplicate`; `frappe.enqueue` chạy dưới user của phiên lúc xếp | `research-R5.md` mục a–c |

### 1.2 Tên U5b dựa vào (nguồn)

| Tên | Chữ ký / giá trị | Module | Nguồn (đơn vị) |
|---|---|---|---|
| `due_reminder_hours`, `ba_note_due_hours`, `task_due_days` | Int, mặc định 24, 24, 3; khoảng 1..168, 1..168, 1..30 | ERP AI Setting | U0, `design.md:143-145, 293` |
| `budget_alert_sent_month` | Data `YYYY-MM`, read-only, tự quản; khôi phục khi người lưu (`restore_self_managed_fields`) | ERP AI Setting | U0, `design.md:149, 291, 515` |
| `field_due_date` | Data (fieldname HD Ticket, Date hoặc Datetime), rỗng = chưa cấu hình | ERP AI Setting | U0, `design.md:139` |
| `category_mapping`, `alert_recipients`, `monthly_budget_usd`, `enabled`, `excluded_teams` | có sẵn | ERP AI Setting | trước FEAT-007 |
| `policy.is_over_budget` | `(settings, now=None) -> bool` (tổng `cost_usd` sống, không đọc `spent_this_month_usd`) | `erp_ai/agent/policy.py` | U1, `design-addendum-1-U1.md:10` (3.9) |
| `policy.month_spend_usd` | `(now=None) -> float` | `policy.py` | U1 (3.9) |
| `policy.effective_level` | `(settings, *, over_budget: bool) -> str` | `policy.py` | U1 (3.9) |
| `policy.can_send_ticket`, `policy.is_enabled` | có sẵn | `policy.py` | trước FEAT-007; U2 mở rộng vị từ |
| `authority.enter_agent_session` | `() -> bool`; chỗ duy nhất `frappe.set_user(AGENT_USER)`; sai → `log_error(TITLE_WRONG_USER, …)`, `False` | `erp_ai/agent/authority.py` | U1 (3.3, 3.9) |
| `run_log.action_entry` | `(tool, doctype, name, ok, *, reason=None, value_before=None, value_after=None, instructor=None, rule=None) -> dict` — hàm dựng mục duy nhất | `erp_ai/agent/run_log.py` | U3 (3.1, 3.10) |
| `run_log.write_bot_action` | `(*, trigger, actions, ticket=None, instructor=None, run_id=None, site_environment=None) -> str`; `cost_usd = 0`; **commit** ngoài test; gọi **cuối** giao dịch | `run_log.py` | U3 (3.1, 3.10) |
| `run_log.TRIGGER_SCHEDULED_JOB`, `ENTRY_TYPE_BOT_ACTION`, `ACTION_KEYS` | `"scheduled_job"`, `"bot_action"`, 7 khóa | `run_log.py` | U3 (3.10) |
| `routing.processing_deadline` | `(category, resolution_by, due_at) -> datetime \| None`; D, E có `due_at` → `due_at`, ngược lại `resolution_by` | `erp_ai/agent/routing.py` | U4a, `design.md:391` |
| `missed_scan.scan_missed_tickets` | `(now: datetime \| None = None) -> None`; hàm `cron` `*/15`, phiên scheduler, hàng `default` | `erp_ai/agent/missed_scan.py` | U4a, `design.md:367-377` |
| Phiếu "đang mở" | `status_category != "Resolved"` (A-D3) | HD Ticket | U4a, `design.md:372` |
| `ops_data.category_by_ticket_type`, `ops_data.ticket_category` | `(mapping) -> dict[str, str]`, `(ticket_row, reverse_map) -> str \| None` | `erp_ai/agent/ops_data.py` | U5a, `design.md:423` |
| `ops_data.BA_NOTE_MARKER` | `"**BA note**"` | `ops_data.py` | U5a, `design.md:337`; `design-w0-fixes.md:200` |
| `queue.SCHEDULED_JOB_TIMEOUT_S` | `1200` | `erp_ai/agent/queue.py` | U5a (F-2) |
| `build_daily_report` khóa `due_soon`, `overdue`, `c_missing_ba_note`, `cd_missing_task` | mục 3.6.3 | `erp_ai/agent/daily_report.py` | U5a, `design.md:445-448` |
| `ENQUEUE_TARGETS` (5 chuỗi), `test_enqueue_targets_pinned`, `test_enqueue_call_shape_requires_one_call_per_target` | sau F-2 | `erp_ai/tests/test_architecture.py` | U5a (F-2) |
| BA note = comment của tài khoản agent, dòng 1 = `BA_NOTE_MARKER` | do tool `post_comment kind=ba_note` đăng | Comment phiếu | U8, `design-addendum-1-U4b-U8.md:267`; fixes Fix 3 |
| Task liên kết phiếu = Task có `ai_ticket` = tên phiếu | trường có sẵn từ FEAT-001 | Task | U5a `cd_missing_task`, U8 |
| `alerts.send_notice` | `(subject, message) -> None` | `erp_ai/alerts.py` | có sẵn |
| `AGENT_USER`, `SETTING_DOCTYPE`, `LOG_DOCTYPE`, `LOGGER_NAME`, `TITLE_RUN_FAILED` | có sẵn | `erp_ai/constants.py` | có sẵn |

### 1.3 Cần từ U0 / U1 / U3 / U5a / U8 (không tự đặt)

| Từ | Cần | Trạng thái |
|---|---|---|
| U0 | 4 trường mục 1.2 có trong JSON + `INT_LIMITS`; `budget_alert_sent_month` nằm trong `restore_self_managed_fields` | đã có trong `design.md:143-149, 291`; **không thiếu trường nào** |
| U1 | `is_over_budget(settings, now)` nhận `now` (test giả lập giữa tháng); `effective_level(settings, *, over_budget)`; `enter_agent_session` | có trong hợp đồng 3.9 |
| U3 | `write_bot_action` chấp nhận được gọi trong **phiên scheduler** (Administrator) cho dòng AC-61 — U3 3.1 (d) dùng `insert(ignore_permissions=…)` trong `allow_agent_write()` nên phiên nào cũng ghi được; `write_entry` bắt `ticket` là Link HD Ticket tùy chọn | có (U3 3.10 đã liệt kê "U5b … AC-61 1 dòng log") |
| U5a | `ops_data.py`, `daily_report.py`, `missed_scan.py` (U4a) đã merge vào `team/FEAT-007` trước khi U5b build (đợt 0) | theo đợt của arch-impact |
| U8 | BA note đăng bằng `HD Ticket.new_comment` dưới phiên agent, dòng 1 đúng `BA_NOTE_MARKER` | có trong U4b-U8 3.2 + Fix 3 |

## 2. Mô hình dữ liệu

**Không DocType mới, không trường mới, không patch.** Mọi dữ liệu U5b ghi đều đã có chủ ở ADR-033 QĐ 7:

| Thực thể | U5b ghi gì | Phiên |
|---|---|---|
| Comment phiếu (bản ghi do `HD Ticket.new_comment` tạo) | lời nhắc hạn (AC-57) và nhắc mốc (AC-58) cho phiếu thường | agent |
| `Notification Log` (Frappe) | thông báo chỉ có số phiếu và hạn cho người phụ trách của phiếu nhóm loại trừ (AC-57, AC-58 Task) | agent |
| ERP AI Log, `entry_type = "bot_action"`, `trigger = "scheduled_job"` | một dòng cho mỗi tác động (mỗi phiếu × mỗi loại nhắc; mỗi email vượt ngân sách) — vừa là nhật ký AC-10 vừa là **khóa chu kỳ** | agent (nhắc) / scheduler (ngân sách) |
| `ERP AI Setting.budget_alert_sent_month` | `YYYY-MM` của tháng đã gửi, bằng `set_single_value` | scheduler |
| Email Queue (Frappe) | email vượt ngân sách qua `alerts.send_notice` (`delayed=True`, cùng giao dịch) | scheduler |

**Dạng mục hành động (dựng bằng `run_log.action_entry`, không dict tay):**

| Tác động | `tool` | `doctype`, `name` | `value_after` (chỉ mã, không nội dung phiếu) |
|---|---|---|---|
| Nhắc hạn, phiếu thường | `DUE_REMINDER_TOOL = "due_reminder"` | doctype thật của bản ghi `new_comment` trả về, tên comment | `{"kind": "due_soon" \| "overdue", "deadline": "YYYY-MM-DD HH:MM:SS", "assignees": [user…]}` |
| Nhắc hạn, phiếu loại trừ | `due_reminder` | `"Notification Log"`, tên bản ghi đầu tiên | như trên + `"by_code": true` |
| Nhắc mốc | `MILESTONE_REMINDER_TOOL = "milestone_reminder"` | Comment hoặc `Notification Log` như trên | `{"kind": "ba_note_missing" \| "task_missing", "assignees": […]}` (+ `"by_code": true`) |
| Email vượt ngân sách | `BUDGET_ALERT_TOOL = "budget_alert"` | `SETTING_DOCTYPE`, `SETTING_DOCTYPE` | `value_before={"budget_alert_sent_month": <cũ>}`, `value_after={"budget_alert_sent_month": "YYYY-MM", "spent_usd": <6 chữ số>, "budget_usd": <số>}` |

**Khóa chu kỳ (ADR-033 QĐ 6, "tính từ lịch, lưu cùng giao dịch với tác động"):**

| Việc | Chu kỳ = khóa | Nơi lưu khóa |
|---|---|---|
| AC-57 | `(phiếu, kind, deadline)` — hạn đổi là chu kỳ mới (A-U5b-2) | mục `due_reminder` `ok=True` trong dòng `bot_action` của phiếu |
| AC-58 | `(phiếu, kind)` — một lần cho đời phiếu | mục `milestone_reminder` `ok=True` |
| AC-61 | tháng lịch `YYYY-MM` của `now` | `budget_alert_sent_month` (+ dòng `bot_action` làm nhật ký) |

Đọc khóa theo truy cập: một truy vấn `frappe.get_all(LOG_DOCTYPE, filters={"entry_type": "bot_action", "trigger": "scheduled_job", "ticket": ["in", names]}, fields=["ticket", "actions"])` cho cả lô ứng viên, rồi parse JSON `actions` ở Python, lấy mục có `tool` ∈ {`due_reminder`, `milestone_reminder`} và `ok` đúng. Số dòng nhỏ (≤ 4 mỗi phiếu mỗi chu kỳ), không cần chỉ mục mới (`ticket` là Link, đã có chỉ mục).

## 3. API / hợp đồng

Mọi hàm là Python nội bộ; **không endpoint, không whitelisted method**. Một dạng lỗi cho cả đơn vị: hàm job **không ném** ra khỏi job; lỗi → `frappe.db.rollback(save_point=…)` hoặc `rollback()`, `frappe.log_error(TITLE_RUN_FAILED, "<việc> ticket=<tên> kind=<kind> error=<TênLớpLỗi>")` (chỉ mã, không nội dung phiếu, không khóa), đi tiếp. Tham số sai kiểu do code gọi (không do dữ liệu) → `ValueError`. Hợp đồng chỉ **thêm**: không đổi chữ ký hàm có sẵn nào.

### 3.1 `erp_ai/agent/ops_data.py` (sửa, file U5a) — một nguồn cho báo cáo 08:00 và U5b

```python
def ticket_deadline(category: str | None, resolution_by, due_value) -> datetime | None
def tickets_with_ba_note(names: list[str]) -> set[str]
def tickets_with_task(names: list[str]) -> set[str]
```

| Hàm | Hành vi chính xác | Lỗi |
|---|---|---|
| `ticket_deadline` | `due_value` là `date` không giờ (trường Date) → `datetime.combine(d, time(23, 59, 59))` (A-U5b-3); `datetime`/chuỗi → `get_datetime`; rỗng → `None`; trả `routing.processing_deadline(category, get_datetime(resolution_by) if resolution_by else None, due_at)` | không ném |
| `tickets_with_ba_note` | **Chuyển nguyên** phép U5a đã dựng cho `c_missing_ba_note` (doctype comment, cột tác giả = `AGENT_USER`, nội dung `LIKE BA_NOTE_MARKER%`) thành hàm nhận danh sách; trả tập tên phiếu có BA note. Comment của người có marker không tính | `names` rỗng → `set()` |
| `tickets_with_task` | `frappe.get_all("Task", filters={"ai_ticket": ["in", names]}, pluck="ai_ticket", distinct=True)` → tập | `names` rỗng → `set()` |

`daily_report.build_daily_report` (U5a) đổi đúng 3 chỗ để gọi 3 hàm trên thay cho phép tại chỗ (`due_soon`/`overdue`, `c_missing_ba_note`, `cd_missing_task`), để báo cáo AC-51 và kiểm mốc AC-58 không thể lệch (AC-58 "có trong báo cáo").

### 3.2 `erp_ai/agent/due_checks.py` (mới) — nhắc hạn và kiểm mốc (AC-57, AC-58)

```python
DUE_REMINDER_TOOL = "due_reminder"
MILESTONE_REMINDER_TOOL = "milestone_reminder"
KIND_DUE_SOON, KIND_OVERDUE = "due_soon", "overdue"
KIND_BA_NOTE_MISSING, KIND_TASK_MISSING = "ba_note_missing", "task_missing"
CANDIDATE_LIMIT = 200          # mỗi loại ứng viên mỗi lần chạy; phần dư sang lần sau
LOCK_NAME = "erp_ai_due_checks"
DUE_SOON_TEXT = "Nhắc hạn: phiếu còn dưới {hours} giờ tới hạn {deadline}. Người phụ trách: {people}."
OVERDUE_TEXT = "Nhắc hạn: phiếu đã quá hạn {deadline}. Người phụ trách: {people}."
BA_NOTE_TEXT = "Nhắc mốc: phiếu đầu mục C đã quá {hours} giờ mà chưa có BA note. Người phụ trách: {people}."
TASK_TEXT = "Nhắc mốc: phiếu đã quá {days} ngày mà chưa có Task liên kết. Người phụ trách: {people}."
NO_ASSIGNEE_TEXT = "chưa có người phụ trách"
CODE_SUBJECT = {                # phiếu nhóm loại trừ: chỉ số phiếu và hạn (A-12)
    KIND_DUE_SOON: "Phiếu #{name}: còn dưới {hours} giờ tới hạn {deadline}",
    KIND_OVERDUE: "Phiếu #{name}: đã quá hạn {deadline}",
    KIND_TASK_MISSING: "Phiếu #{name}: quá {days} ngày chưa có Task liên kết",
}

def run_due_checks(now: datetime | None = None) -> None          # đích của job `long`
def due_kind(deadline: datetime | None, now: datetime, hours: int) -> str | None   # thuần
def milestone_due(created: datetime, now: datetime, hours: float) -> bool         # thuần
def sent_keys(names: list[str]) -> set[tuple[str, str, str]]
```

| Hàm | Hành vi chính xác | Lỗi |
|---|---|---|
| `due_kind` | `deadline` None → None. `deadline ≤ now` → `overdue`. `now < deadline ≤ now + hours` → `due_soon` (đúng 24 giờ tính nhắc). Còn lại None | — |
| `milestone_due` | `now − created ≥ hours` (đúng 24 h / 72 h tính đến mốc) | — |
| `sent_keys` | mục 2 "Đọc khóa": trả tập `(phiếu, kind, deadline_iso)`; mục `milestone_reminder` có `deadline_iso = ""` | `actions` JSON hỏng → bỏ dòng đó, 1 dòng logger warning |
| `run_due_checks` | Các bước ở mục 4.1 | không ném |

Ứng viên (đọc bằng `frappe.get_all`, không đọc `subject`, `description` hay comment của phiếu — chỉ cột cấu trúc): `name`, `creation`, `ticket_type`, `resolution_by`, `_assign`, `ai_opt_out`, `agent_group`, và trường `field_due_date` khi đã cấu hình và `frappe.get_meta("HD Ticket").has_field` đúng (ngược lại hạn = `resolution_by`, 1 dòng logger mỗi lần chạy). Bộ lọc chung: `status_category != "Resolved"` (đã đóng không nhắc), sắp `creation` tăng, `limit = CANDIDATE_LIMIT`. Đầu mục: `ops_data.ticket_category(row, ops_data.category_by_ticket_type(settings.category_mapping))`.

| Loại | Đầu mục | Điều kiện thêm | Phiếu loại trừ (`can_send_ticket` sai) |
|---|---|---|---|
| `due_soon` / `overdue` (AC-57) | D, E | `due_kind(ticket_deadline(...), now, due_reminder_hours)` khác None; khóa `(phiếu, kind, deadline)` chưa có. Thấy lần đầu đã quá hạn → chỉ `overdue` | `Notification Log` mã (A-12) |
| `ba_note_missing` (AC-58) | C | `milestone_due(creation, now, ba_note_due_hours)` ∧ phiếu ∉ `tickets_with_ba_note` ∧ khóa chưa có | **bỏ qua** (A-U5b-4) |
| `task_missing` (AC-58) | C, D | `milestone_due(creation, now, task_due_days × 24)` ∧ phiếu ∉ `tickets_with_task` ∧ khóa chưa có | `Notification Log` mã (A-U5b-4) |

Nội dung: `deadline` in `%d/%m/%Y %H:%M`; `people` = với mỗi user trong `_assign` (JSON list): thẻ mention theo dạng Helpdesk (`<span class="mention" data-type="mention" data-id="<user>" data-label="<full name>">@<full name></span>`), nối bằng ", "; `_assign` rỗng → `NO_ASSIGNEE_TEXT`. Không chuỗi nào lấy từ tiêu đề, mô tả hay comment của phiếu.

### 3.3 `erp_ai/agent/budget_alert.py` (mới) — email lần đầu vượt ngân sách (AC-61)

```python
BUDGET_ALERT_TOOL = "budget_alert"
SENT_MONTH_FIELD = "budget_alert_sent_month"
LOCK_NAME = "erp_ai_budget_alert"
SUBJECT = "Chi phí AI tháng {month} đã vượt ngân sách"
MESSAGE = ("Chi tháng {month}: {spent:.2f} USD, ngân sách {budget:.2f} USD. Từ lần chạy kế tiếp bot chạy ở "
           "mức L1 cho tới khi tăng ngân sách trên ERP AI Setting hoặc sang tháng mới.")

def run_budget_alert(now: datetime | None = None) -> None
```

| Bước | Hành vi chính xác |
|---|---|
| 1 | `frappe.session.user == AGENT_USER` → 1 dòng logger warning `"budget_alert: phiên agent, bỏ qua"`, return (ADR-033 QĐ 1: phiên agent không bao giờ ghi ERP AI Setting) |
| 2 | `filelock(LOCK_NAME, timeout=5)`; bận → logger, return |
| 3 | `now = get_datetime(now) if now else now_datetime()`; `month = f"{now:%Y-%m}"` (tháng lịch, giờ site); `settings = frappe.get_single(SETTING_DOCTYPE)` |
| 4 | `settings.budget_alert_sent_month == month` → return (đã gửi trong chu kỳ) |
| 5 | `policy.is_over_budget(settings, now)` sai → return (không đọc `spent_this_month_usd`) |
| 6 | `spent = policy.month_spend_usd(now)`; `alerts.send_notice(SUBJECT.format(month=month), MESSAGE.format(...))` (người nhận rỗng → không email, chỉ logger: A-U5b-5) |
| 7 | `frappe.db.set_single_value(SETTING_DOCTYPE, SENT_MONTH_FIELD, month)` — chỗ ghi duy nhất của trường này |
| 8 | `run_log.write_bot_action(trigger=TRIGGER_SCHEDULED_JOB, actions=[action_entry(BUDGET_ALERT_TOOL, SETTING_DOCTYPE, SETTING_DOCTYPE, True, value_before=…, value_after=…)])` — **cuối cùng**, commit phủ Email Queue + mốc + dòng (U3 3.1) |
| Lỗi ở 3–8 | `frappe.db.rollback()`; `frappe.log_error(TITLE_RUN_FAILED, f"budget_alert month={month} error={type(exc).__name__}")`; return. Mốc chưa ghi → lần quét sau thử lại, đúng một email |

### 3.4 `erp_ai/agent/queue.py` (sửa) — một lời `frappe.enqueue` mới

```python
def enqueue_due_checks_job() -> None
```
Đúng một lời `frappe.enqueue("erp_ai.agent.due_checks.run_due_checks", queue="long", timeout=SCHEDULED_JOB_TIMEOUT_S, enqueue_after_commit=True, job_id="erp_ai::due_checks", deduplicate=True)`; không kwarg nào khác (job tự lấy `now`). Đích là chuỗi; `queue.py` không import `due_checks`. Các hàm có sẵn không đổi. `budget_alert` không qua hàng đợi (A-U5b-1).

### 3.5 `erp_ai/agent/missed_scan.py` (sửa, file U4a) — điểm gắn vào lịch 15 phút

Thêm vào **đầu** `scan_missed_tickets`, trước kiểm `policy.is_enabled()` của U4a:
```python
budget_alert.run_budget_alert(now)        # AC-61; không ném; phiên scheduler (ADR-033 QĐ 9)
queue.enqueue_due_checks_job()            # AC-57, AC-58; xếp sau commit của job cron
```
Bọc cả hai trong một `try/except Exception` riêng → `frappe.log_error(TITLE_RUN_FAILED, "missed_scan operations error=<Type>")`, rồi thân U4a chạy tiếp như cũ. Không đổi `hooks.py`, không cần `cmd.migrate`.

### 3.6 `erp_ai/tests/test_architecture.py` (sửa, cùng task với 3.4)

- `ENQUEUE_TARGETS` thêm `"erp_ai.agent.due_checks.run_due_checks"` (5 → 6 sau U5a). Chữ lỗi của `check_enqueue_call_shape` đã dùng `len(ENQUEUE_TARGETS)` từ F-2, không sửa.
- `TestScannersCatchViolations::test_enqueue_targets_pinned` ghim tuple 6 chuỗi. Lý do sửa ghim ghi trong commit: ADR-033 QĐ 6, addendum này (NFR-8, STD-TEST-5).
- `LAYER_RULES` thêm một dòng: scope `"erp_ai.agent.due_checks"` và `"erp_ai.agent.budget_alert"` (một dòng mỗi scope, hoặc nối vào tuple module việc theo lịch nếu U5a đã lập), cấm `"erp_ai.gateway"`, `"erp_ai.agent.runner"`; lý do `"ADR-033 QĐ 3, ADR-001: scheduled checks never call the model gateway"`.

### 3.7 Contract for later units

| Tên | Chữ ký / giá trị | Module | Đơn vị gọi |
|---|---|---|---|
| `ops_data.ticket_deadline`, `tickets_with_ba_note`, `tickets_with_task` | mục 3.1 | `erp_ai/agent/ops_data.py` | U5a (báo cáo 08:00), U7 nếu cần |
| `DUE_REMINDER_TOOL`, `MILESTONE_REMINDER_TOOL`, `BUDGET_ALERT_TOOL` | tên tool trong mục hành động | `due_checks.py`, `budget_alert.py` | người đọc: U5a `bot_actions` (rơi vào "khác" nếu không thêm vào `ACTION_KIND_BY_TOOL`) |
| `enqueue_due_checks_job` | `() -> None` | `erp_ai/agent/queue.py` | chỉ `missed_scan` |

## 4. Luồng

### 4.1 Nhắc hạn và kiểm mốc (mỗi 15 phút)

1. Scheduler (phiên Administrator, hàng `default`, ≤ 300 s) chạy `missed_scan.scan_missed_tickets` → `queue.enqueue_due_checks_job()` → sau commit, đúng một job `long` `erp_ai::due_checks` (trùng `job_id` đang chờ → không xếp thêm).
2. `run_due_checks(now)`: `filelock(LOCK_NAME, timeout=5)`; bận → logger, return.
3. `policy.is_enabled()` sai, hoặc `policy.effective_level(settings, over_budget=policy.is_over_budget(settings, now)) == "L0"` → 1 dòng logger, return (AC-23: agent tắt hoặc L0 chỉ log).
4. `authority.enter_agent_session()` sai → return (hàm đó đã ghi Error Log).
5. Đọc ứng viên ba loại (mục 3.2), `sent_keys(names)`, `tickets_with_ba_note`, `tickets_with_task` — mỗi thứ một truy vấn cho cả lô.
6. Với mỗi (phiếu, kind) cần nhắc, theo `creation` tăng:
   1. `frappe.db.savepoint("erp_ai_due")`; khóa dòng phiếu `frappe.db.get_value("HD Ticket", name, "name", for_update=True)`; đọc lại khóa của phiếu (`sent_keys([name])`) — đã có → bỏ.
   2. Phiếu thường: `frappe.get_doc("HD Ticket", name).new_comment(<chữ mục 3.2>)`. Phiếu loại trừ: với mỗi user trong `_assign`, `frappe.get_doc({"doctype": "Notification Log", "for_user": u, "from_user": AGENT_USER, "type": "Alert", "document_type": "HD Ticket", "document_name": name, "subject": CODE_SUBJECT[kind].format(...)}).insert(ignore_permissions=True)`; `_assign` rỗng → không ghi gì, không khóa, đếm vào `no_assignee` (lần sau thử lại).
   3. `run_log.write_bot_action(trigger=TRIGGER_SCHEDULED_JOB, ticket=name, actions=[action_entry(...)])` — cuối cùng; commit phủ comment/thông báo + khóa.
   4. Lỗi ở 6.1–6.3 → `frappe.db.rollback(save_point="erp_ai_due")`, `log_error(TITLE_RUN_FAILED, "due_checks ticket=<tên> kind=<kind> error=<Type>")`, sang phiếu kế (lỗi giữa chừng không chặn phiếu khác; khóa phiếu lỗi không được ghi → lần sau làm lại đúng một lần).
7. 1 dòng logger: `"due_checks: due_soon=%d overdue=%d ba_note=%d task=%d errors=%d no_assignee=%d capped=%s"`.

### 4.2 Email vượt ngân sách (mỗi 15 phút)

Scheduler chạy `scan_missed_tickets` → `budget_alert.run_budget_alert(now)` (phiên scheduler, trước mọi việc khác của lượt quét) → các bước mục 3.3. Lần đầu tổng `cost_usd` sống của tháng vượt `monthly_budget_usd`: một email + một mốc + một dòng, một commit. Các lượt sau cùng tháng dừng ở bước 4.

### 4.3 Lượt lỡ, giờ, 300 s (R-5)

- Lượt lỡ gộp thành một: cả hai việc tính lại từ dữ liệu hiện tại, không đếm lượt lỡ. Lỡ qua cả cửa sổ "còn 24 giờ" → chỉ còn lời nhắc quá hạn (đúng AC: không nhắc hai lần trễ). Lỡ qua lúc vượt ngân sách → email ở lượt kế tiếp.
- Giờ: `now_datetime()` = giờ `System Settings.time_zone`; tháng của AC-61 và mốc "24 giờ / 72 giờ" tính theo giờ đó; `creation` của phiếu cùng hệ giờ.
- 300 s: phần chạy ở `default` chỉ gồm một truy vấn tổng + tối đa một email + một lời `enqueue`; phần duyệt phiếu chạy ở `long` với `SCHEDULED_JOB_TIMEOUT_S` 1200 s và `CANDIDATE_LIMIT`. Không có worker `long` → job đứng chờ (rủi ro đã nêu ở ADR-033 Hệ quả); `bench doctor`/danh sách worker là phép kiểm vận hành của R-5 (d), không thuộc U5b.

## 5. Quyền

| Việc | Ai | Kiểm ở đâu |
|---|---|---|
| Đăng comment nhắc | tài khoản agent (`enter_agent_session`) | quyền Helpdesk của role Agent như tool `post_comment` (không `ignore_permissions`); `owner` = `AGENT_USER` (ADR-033 Ràng buộc cuối) |
| Tạo `Notification Log` cho người phụ trách | tài khoản agent | `insert(ignore_permissions=True)` (DocType Frappe, không phải DocType của app; ngoài phạm vi M5); `from_user` = agent |
| Ghi dòng `bot_action` | agent (nhắc) / scheduler (ngân sách) | `run_log.write_entry` của U3 (đường hợp lệ 1, `allow_agent_write()`), không mở đường M5 mới (ADR-033 QĐ 8) |
| Ghi `budget_alert_sent_month` | chỉ `run_budget_alert`, phiên scheduler | bước 1 từ chối phiên agent; người lưu form không đổi được (U0 `restore_self_managed_fields`) |
| Đọc nội dung phiếu nhóm loại trừ | không ai trong U5b | U5b chỉ đọc cột cấu trúc; không import `gateway`/`runner` (luật lớp 3.6) |

Không endpoint mới nên không có kiểm quyền ở biên HTTP.

## 6. Migration và rollback, quan sát

- Lên: không schema; sửa code. Lịch không đổi (gắn vào hàm `*/15` có sẵn), nên không cần chạy `cmd.migrate` cho U5b.
- Xuống: revert commit của U5b. Dòng `bot_action` đã ghi ở lại (nhật ký, `cost_usd = 0`, không đếm `runs_today`); `budget_alert_sent_month` ở lại, vô hại (chỉ U5b đọc).
- Đối soát: số lời nhắc của một tháng = số mục `ok` có `tool` ∈ {`due_reminder`, `milestone_reminder`} trong dòng `bot_action` của tháng; đối chiếu với số comment của agent có tiền tố "Nhắc hạn:"/"Nhắc mốc:" + số `Notification Log` `from_user = AGENT_USER`. Lệch → dòng Error Log `due_checks …` tương ứng giải thích.
- Quan sát: 1 dòng logger mỗi lần chạy `due_checks` (mục 4.1 bước 7); 1 dòng logger mỗi lần `budget_alert` gửi hoặc bỏ qua vì phiên agent; Error Log `TITLE_RUN_FAILED` cho mỗi lỗi; dòng `bot_action` cho mỗi tác động.

## 7. Touchpoints

Ô file của U5b ở `arch-impact.md:114`: "file việc theo lịch, hàm nhắc hạn ở Lõi". Thêm hai file người giao việc yêu cầu cho luật enqueue (`agent/queue.py`, `tests/test_architecture.py`).

| file | change | Thuộc ô U5b vì | ghi chú |
|---|---|---|---|
| `erp_ai/agent/due_checks.py` | mới | hàm nhắc hạn ở Lõi | 3.2 |
| `erp_ai/agent/budget_alert.py` | mới | việc theo lịch (ADR-033 QĐ 9) | 3.3 |
| `erp_ai/agent/ops_data.py` | sửa | file việc theo lịch (U5a) | 3.1: 3 hàm mới |
| `erp_ai/agent/daily_report.py` | sửa | file việc theo lịch (U5a) | 3.1: 3 chỗ gọi helper |
| `erp_ai/agent/missed_scan.py` | sửa | file việc theo lịch (U4a, lượt quét 15 phút) | 3.5: 2 dòng + `try` |
| `erp_ai/agent/queue.py` | sửa | luật enqueue (F-2) | 3.4 |
| `erp_ai/tests/test_architecture.py` | sửa | luật enqueue, cùng task với `queue.py` | 3.6; gộp tay nếu FEAT-004/FEAT-005 còn sửa |
| `erp_ai/agent/test_due_checks.py` | mới | test | mục 8 |
| `erp_ai/agent/test_budget_alert.py` | mới | test | mục 8 |
| `erp_ai/agent/test_ops_data.py`, `erp_ai/agent/test_daily_report.py`, `erp_ai/agent/test_missed_scan.py`, `erp_ai/agent/test_queue.py` | sửa | test của file sửa | mục 8 |

Không chạm `hooks.py`, `tasks.py`, `alerts.py`, `tools/write_ticket.py`, `runner.py`, ERP AI Setting.

**So khớp đường dẫn mới với `allowed_new_file_roots` (`["erp_ai", "docs", ".github"]`) và `protected_paths` (`[".env", ".env.*", "**/*.pem", "**/*.key", "license.txt"]`):**

| Đường dẫn mới | Root khớp | Khớp protected? |
|---|---|---|
| `erp_ai/agent/due_checks.py` | `erp_ai` | không |
| `erp_ai/agent/budget_alert.py` | `erp_ai` | không |
| `erp_ai/agent/test_due_checks.py` | `erp_ai` | không |
| `erp_ai/agent/test_budget_alert.py` | `erp_ai` | không |
| `docs/team/features/FEAT-007/design-addendum-2-U5b.md` | `docs` | không |

Tên file theo `naming.file` snake_case, test theo `test_{name}.py`, colocated (`structure.tests = "colocated"`).

## 8. Test plan

Chạy từng file bằng slot `cmd.test_one`. Mọi test truyền `now` giả lập; phiếu dựng bằng fixture có `ticket_type` ánh xạ đầu mục qua `category_mapping` thử nghiệm.

| Tiêu chí | Test | Ca / assert | Loại |
|---|---|---|---|
| AC-57 | `erp_ai/agent/test_due_checks.py::TestDueReminder::test_three_kinds_by_due_overdue_closed` | 3 loại phiếu (D thường, E thường, D nhóm loại trừ) × {còn 24 h, quá hạn, đã đóng} = 9 ca; đếm: thường → 1 comment mỗi ca mở, loại trừ → 1 `Notification Log` mỗi người phụ trách và 0 comment, đã đóng → 0 | integration |
| AC-57 (biên) | `…::TestDueReminder::test_boundary_exactly_24h` | hạn − now = 24:00 → 1; = 24:01 → 0; = 0 → `overdue` | unit (`due_kind`) |
| AC-57 | `…::TestDueReminder::test_first_seen_overdue_only_overdue` | phiếu thấy lần đầu đã quá hạn → chỉ 1 lời `overdue`, 0 `due_soon` | integration |
| AC-57 | `…::TestDueReminder::test_due_soon_then_overdue_two_total` | chạy ở −20 h rồi +1 h → đúng 2 lời nhắc, mỗi loại 1 | integration |
| AC-57 (A-U5b-2) | `…::TestDueReminder::test_deadline_moved_is_new_cycle` | nhắc `due_soon`, dời hạn +3 ngày rồi tới −20 h của hạn mới → thêm 1 | integration |
| AC-57 | `…::TestDueReminder::test_not_d_or_e_not_reminded` | A, B, C, F có hạn trong 24 h → 0 | integration |
| AC-57 | `…::TestDueReminder::test_due_field_not_configured_uses_resolution_by` | `field_due_date` rỗng → hạn = `resolution_by`; 1 dòng logger | integration |
| AC-57 (A-U5b-3) | `erp_ai/agent/test_ops_data.py::TestTicketDeadline::test_date_value_is_end_of_day` | Date 20/11 → 20/11 23:59:59; Datetime giữ; rỗng → `resolution_by` cho D, E | unit |
| AC-57 "tới người phụ trách" | `…test_due_checks.py::TestDueReminder::test_comment_mentions_assignees_owner_is_agent` | comment có `data-id="<user>"` của mỗi người trong `_assign`; `owner`/tác giả = `AGENT_USER`; không có `_assign` → chữ "chưa có người phụ trách" | integration |
| AC-57, A-12, NFR-1 | `…::TestExcluded::test_seeded_string_never_leaves_ticket` | tiêu đề + mô tả chứa chuỗi gieo; sau chạy: 0 comment trên phiếu; `Notification Log.subject` chỉ có `#<tên>` + hạn; chuỗi gieo vắng trong Notification Log, ERP AI Log, Error Log, Email Queue; `erp_ai.gateway` bị patch ném nếu gọi → không gọi | integration |
| AC-57 | `…::TestExcluded::test_no_assignee_no_key_then_reminded_after_assign` | phiếu loại trừ không `_assign` → 0 tác động, 0 khóa; gán người rồi chạy → 1 | integration |
| AC-57, AC-23 | `…::TestGates::test_agent_off_or_l0_no_reminder` | `enabled = 0` → 0; mức L0 → 0; mỗi ca 1 dòng logger | integration |
| AC-57, AC-58 (ADR-033 "chạy hai lần") | `…::TestIdempotent::test_run_twice_same_now_one_effect` | đủ 4 loại nhắc; chạy 2 lần cùng `now` → 0 comment, 0 Notification Log, 0 dòng `bot_action` thêm ở lần 2 | integration |
| AC-57, AC-58 (ADR-033 "lỗi giữa chừng") | `…::TestIdempotent::test_fail_midway_then_exactly_once` | 3 phiếu; patch `write_bot_action` ném ở phiếu 2 → phiếu 1, 3 có 1 tác động, phiếu 2 có 0 comment và 0 khóa, 1 Error Log `due_checks ticket=<2>`; chạy lại không lỗi → phiếu 2 đúng 1, phiếu 1, 3 thêm 0 | integration |
| AC-58 | `…::TestMilestones::test_ba_note_23h_24h_with_and_without` | C không BA note: 23 h → 0, 24 h → 1; C có BA note (comment agent bắt đầu `BA_NOTE_MARKER`) ở 24 h → 0 | integration |
| AC-58 | `…::TestMilestones::test_task_71h_72h_with_and_without` | C và D không Task: 71 h → 0, 72 h → 1; có Task `ai_ticket` = phiếu ở 72 h → 0 | integration |
| AC-58 | `…::TestMilestones::test_human_comment_with_marker_not_ba_note` | comment của người bắt đầu bằng marker → vẫn nhắc ở 24 h | integration |
| AC-58 (A-U5b-4) | `…::TestMilestones::test_excluded_c_no_ba_note_check_task_by_code` | C nhóm loại trừ 72 h không Task: 0 nhắc BA note, 1 `Notification Log` mã cho Task, 0 comment | integration |
| AC-58 "có trong báo cáo" | `erp_ai/agent/test_daily_report.py::TestDailyReport::test_missing_lists_match_due_checks` | cùng fixture và mốc: `c_missing_ba_note`, `cd_missing_task`, `due_soon`, `overdue` của `build_daily_report` = tập ứng viên tương ứng của `due_checks` (cùng helper 3.1) | integration |
| AC-58 | `erp_ai/agent/test_ops_data.py::TestMilestoneHelpers::test_ba_note_and_task_sets` | `tickets_with_ba_note`, `tickets_with_task`: rỗng, có, của người, phiếu khác | unit |
| AC-61 | `erp_ai/agent/test_budget_alert.py::TestBudgetAlert::test_first_over_one_email_one_log_row` | gieo dòng ERP AI Log tổng > ngân sách giữa ngày → 1 Email Queue tới `alert_recipients`, 1 dòng `bot_action` mục `budget_alert`, mốc = tháng | integration |
| AC-61 (ADR-033 "chạy hai lần") | `…::TestBudgetAlert::test_run_twice_one_email` | lần 2 cùng tháng → 0 email, 0 dòng thêm | integration |
| AC-61 (ADR-033 "lỗi giữa chừng") | `…::TestBudgetAlert::test_fail_midway_key_not_written_then_once` | patch `write_bot_action` ném → 0 Email Queue, mốc giữ giá trị cũ, 1 Error Log `budget_alert month=…`, không ngoại lệ; chạy lại → đúng 1 email | integration |
| AC-61 (tổng sống) | `…::TestBudgetAlert::test_reads_live_log_not_spent_field` | log > ngân sách, `spent_this_month_usd = 0` → email; log < ngân sách, `spent_this_month_usd` > ngân sách → 0 | integration |
| AC-61 | `…::TestBudgetAlert::test_new_month_new_alert` | mốc `2026-11`, `now` 2026-12-01 có chi > ngân sách → 1 email | integration |
| AC-61 (A-U5b-5) | `…::TestBudgetAlert::test_empty_recipients_no_email_key_set` | `alert_recipients` rỗng → 0 email, 1 dòng, mốc = tháng | integration |
| AC-61, ADR-033 Ràng buộc 2 | `…::TestBudgetAlert::test_agent_session_does_not_write_setting` | dưới `AGENT_USER` → mốc không đổi, 0 email, 0 dòng | integration |
| AC-61 (phần "chạm giới hạn ngày") | `erp_ai/agent/test_agent_runner.py::TestRunNotices::test_daily_limit_repeated_same_day_one_comment` (chủ U4b, không lặp) | — | integration |
| AC-61 (phần "lùi về L1") | test `is_over_budget` / `effective_level` của U1 (`design-addendum-1-U1.md` mục 8, chủ U1, không lặp) | — | unit |
| ADR-033 QĐ 9, lịch | `erp_ai/agent/test_missed_scan.py::TestScan::test_runs_budget_alert_and_enqueues_due_checks` | 1 lời `run_budget_alert(now)` và 1 lời `enqueue_due_checks_job` mỗi lượt, kể cả khi agent tắt | unit (patch) |
| ADR-033 QĐ 9 | `…test_missed_scan.py::TestScan::test_operations_error_does_not_stop_scan` | `run_budget_alert` ném → 1 Error Log, phần quét U4a vẫn xếp phiếu | unit (patch) |
| F-2, ADR-033 QĐ 6 | `erp_ai/agent/test_queue.py::TestScheduledJobs::test_enqueue_due_checks_job_shape` | đúng 1 lời `frappe.enqueue` với đích, `queue="long"`, `timeout=SCHEDULED_JOB_TIMEOUT_S`, `enqueue_after_commit=True`, `job_id="erp_ai::due_checks"`, `deduplicate=True`, không kwarg khác | unit |
| F-2 | `erp_ai/tests/test_architecture.py::TestScannersCatchViolations::test_enqueue_targets_pinned` | tuple 6 chuỗi | unit |
| F-2 | `erp_ai/tests/test_architecture.py::TestScannersCatchViolations::test_enqueue_call_shape_requires_one_call_per_target` (có sẵn sau U5a) | vẫn xanh với 6 đích | unit |
| ADR-033 QĐ 3, ADR-001 | `erp_ai/tests/test_architecture.py::TestScannersCatchViolations::test_scheduled_checks_must_not_import_model_gateway` | nguồn giả `due_checks.py` có `from erp_ai import gateway` → 1 vi phạm; mã thật → 0 | unit |
| ADR-033 Ràng buộc 2 | `erp_ai/agent/test_due_checks.py::TestBoundaries::test_no_setting_write_in_agent_session_code` | AST `due_checks.py`: 0 lời `set_single_value`, 0 `db.set_value`/`save()` trên `SETTING_DOCTYPE` | unit |
| ADR-033 QĐ 5, AC-10 | `…test_due_checks.py::TestBoundaries::test_entries_built_by_action_entry` | mọi mục trong dòng `bot_action` có đủ `ACTION_KEYS`, `cost_usd = 0`; dòng không đếm vào `runs_today` | integration |

### Đối chiếu AC (Done criteria)

- AC của spec giao U5b (`arch-impact.md:114`): **AC-57, AC-58, AC-61** (phần email vượt ngân sách).
- AC trong test plan trên: **AC-57, AC-58, AC-61** (AC-61 thêm hai dòng tham chiếu tới test của chủ U4b, U1, không lặp).
- Mỗi việc theo lịch có cả "chạy hai lần → một tác động" và "lỗi giữa chừng → khóa không ghi, lần sau đúng một lần": `due_checks` (`TestIdempotent` hai test, phủ AC-57 và AC-58), `budget_alert` (`test_run_twice_one_email`, `test_fail_midway_key_not_written_then_once`).
- Lời `frappe.enqueue` mới: 1, ở `agent/queue.py`; `ENQUEUE_TARGETS` cập nhật cùng task (3.6).

## Assumptions decided by the team

| # | Chọn | Vì | Phương án khác | Sai thì sửa |
|---|---|---|---|---|
| A-U5b-1 | Gắn vào lượt quét 15 phút có sẵn của U4a (`missed_scan.scan_missed_tickets`): email ngân sách chạy tại chỗ (phiên scheduler, `default`), nhắc hạn/mốc xếp một job `long` | ADR-033 QĐ 9 ghi "email lần đầu vượt do việc quét 15 phút gửi"; ô file U5b không có `hooks.py`; email ngân sách là một truy vấn tổng, không cần worker `long` (cảnh báo vẫn đi khi worker `long` chết) | Hai hàm `cron` mới trong `schedules.py` + một dòng `hooks.py` dưới cùng khóa `*/15` (độc lập hơn, cần `cmd.migrate`, chạm file ngoài ô U5b) | Chuyển 2 dòng của 3.5 sang `schedules.py` + `hooks.py`; test 3.5 đổi sang `test_schedules.py` |
| A-U5b-2 | Khóa AC-57 gồm cả giá trị hạn: hạn đổi → chu kỳ mới, nhắc lại | "1 lời nhắc khi còn 24 giờ" gắn với một hạn; hạn dời mà không nhắc thì lời nhắc cho hạn mới không bao giờ có | Khóa `(phiếu, kind)` cho đời phiếu | Bỏ `deadline` khỏi khóa; bỏ test `test_deadline_moved_is_new_cycle` |
| A-U5b-3 | Trường hạn kiểu Date tính là 23:59:59 ngày đó; báo cáo 08:00 dùng cùng helper | "Hạn ngày 20/11" nghĩa là còn làm được trong ngày 20/11; 00:00 làm nhắc sớm một ngày | `get_datetime(date)` = 00:00 | Đổi một dòng trong `ticket_deadline` |
| A-U5b-4 | Phiếu C nhóm loại trừ không kiểm BA note; kiểm Task cho phiếu C/D loại trừ bằng `Notification Log` chỉ có mã (như A-12) | BA note chỉ do bot viết, mà bot không đọc phiếu loại trừ → mốc này luôn "thiếu", nhắc là vô nghĩa; phiếu loại trừ không được có comment của bot (AC-23, NFR-1) | Nhắc cả hai bằng thông báo mã; hoặc bỏ phiếu loại trừ khỏi AC-58 | Bật nhánh BA note cho phiếu loại trừ, hoặc bỏ nhánh Task |
| A-U5b-5 | `alert_recipients` rỗng lúc vượt: không email, vẫn ghi mốc và dòng nhật ký (một lần mỗi tháng) | "Lần đầu vượt" là một sự kiện; không ghi mốc thì 96 dòng logger mỗi ngày | Không ghi mốc, gửi khi người nhận được thêm | Bỏ bước 7, 8 khi người nhận rỗng |
| A-U5b-6 | Phiếu loại trừ không có người phụ trách: không tác động, không khóa, đếm `no_assignee` trong dòng logger; phiếu thường không có người phụ trách: vẫn đăng comment ghi "chưa có người phụ trách" | Thông báo mã cần người nhận; comment trên phiếu thường vẫn có người đọc (nhóm) | Ghi khóa `ok=False` để không thử lại | Ghi mục `ok=False` làm khóa |
| A-U5b-7 | Dừng cả hai việc nhắc khi agent tắt hoặc mức L0 (tính sau hạ vì ngân sách); email ngân sách vẫn chạy | AC-23: agent tắt và L0 chỉ log; email ngân sách là cảnh báo vận hành, không phải hành động trên phiếu | Nhắc cả khi agent tắt | Bỏ bước 3 của 4.1 |

Rủi ro để dev xác nhận ở test (không phải câu hỏi nghiệp vụ): doctype và cột tác giả thật của bản ghi do `HD Ticket.new_comment` tạo (Helpdesk dùng `HD Ticket Comment`); `tickets_with_ba_note` dùng đúng phép U5a đã chọn nên không tạo phép thứ hai. Dạng thẻ mention phải là dạng Helpdesk nhận để báo người được nhắc.
