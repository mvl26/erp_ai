Feature: FEAT-001
Stage: design
Author-agent: designer
Date: 2026-11-11
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Design FEAT-001 — AI Agent `erp_ai` cho Helpdesk Miyano (`L0`/`L1`)

Đầu vào: `spec.md` (AC-1..AC-20, NFR-1..NFR-9, A-1..A-15), `research.md` (Q1–Q3), `arch-impact.md`, `docs/team/architecture.md`, ADR-001..ADR-006 (đều `proposed`; G1, G2, G2b tắt trong `.team/config.json`). Mode decide: không có `questions.md`. Mọi lựa chọn kỹ thuật của designer nằm ở mục "Assumptions decided by the team" (mã D-n) và được trích từ các mục bên dưới.

## 1. Bối cảnh

**Vấn đề (spec Mục tiêu):** phiếu Helpdesk mới được agent đọc và phân loại vào 1 trong 6 đầu mục A–F. Ở `L1`, agent ghi thêm hướng giải quyết và comment. Agent không được tự nâng quyền, không gửi dữ liệu nhạy cảm ra ngoài, không vượt ngân sách. Kèm theo là bộ đánh giá offline để đo độ chính xác trước khi bật.

**Trong phạm vi:** spec mục Phạm vi, các mục 1–11 (eval; cài app; điều kiện kích hoạt; chốt tài khoản job; thẩm quyền; `L0`/`L1`; ghi nhận người sửa + báo cáo; tool đọc; vòng lặp có giới hạn + chi phí; nhiều khóa API; scheduler).
**Ngoài phạm vi:** tool `L2`/`L3` (A-1), dự phòng nhà cung cấp thứ hai (A-6), tự giao phiếu cho người (A-7), đổi `status`, tự tách phiếu, gửi file đính kèm, nút Custom Action trên trang ticket, mọi bước trên production, tạo HD Ticket Type (A-8).

**ADR phải tuân:**

| ADR | Áp vào design ở đâu |
|---|---|
| ADR-001 | Bố cục 4 tầng ở mục 7; luật import có test ở `erp_ai/test_architecture.py` (mục 8) |
| ADR-002 | Cổng `erp_ai/gateway/` (mục 3.4); bảng cầu dao (mục 3.4.3); chi phí (mục 3.4.4) |
| ADR-003 | Handler + hàm xếp hàng duy nhất (mục 3.2, 4.1, 4.2); thứ tự đầu job (mục 4.3) |
| ADR-004 | Bảng chủ ghi (mục 5.2); controller không lưu cấu hình (mục 3.6); nhật ký là nguồn sự thật (mục 2.3, 4.5) |
| ADR-005 | Registry tool (mục 3.5); mức hiệu lực tính một lần (mục 3.3) |
| ADR-006 | Thủ tục cài đặt (mục 3.7, 6) |

**Cơ sở khảo sát (Explore, đọc trực tiếp 2026-11-11).** Bộ nhớ đệm `docs/team/explore/erp_ai.md` (HIT) đã cũ: nó ghi "không có helpdesk", trong khi helpdesk 15.1.0 đã có trong bench (`sites/apps.txt`). Vì vậy tôi đọc lại mã nguồn trực tiếp:
- Repo vẫn là khung rỗng, 19 file. `erp_ai/hooks.py` chỉ có khai báo app, `pyproject.toml` có `dependencies = []`, module `ERP AI agent` → `erp_ai/erp_ai_agent/` (rỗng).
- HD Ticket (`apps/helpdesk/.../hd_ticket/hd_ticket.json`):
  - các trường `subject`, `description`, `status`; `priority`, `ticket_type`, `agent_group`, `raised_by` ở permlevel 7;
  - quyền level 8 RW cho `System Manager`/`Agent`/`Agent Manager`; `HD Customer` không có level 8;
  - `before_validate` tự điền `ticket_type` (HD Settings `default_ticket_type`) và `priority` (`hd_ticket.py:268-275`, `:366-371`) → ảnh hưởng điều kiện "đã điền đủ" (D-4).
- `has_permission` của HD Ticket: agent qua `is_agent()` = có role `Agent`/`Agent Manager` hoặc bản ghi HD Agent (`helpdesk/utils.py:42-57`) → tài khoản agent không cần bản ghi HD Agent.
- HD Ticket Comment có `content` (Text Editor), `reference_ticket`, `commented_by`; `Agent` được tạo.
- HD Ticket Template có dòng con `fieldname`, `required`, `visible_to` (`Everyone`/`Agents`), `editable_after_creation`. Template mặc định tên `Default` (`helpdesk/consts.py:3`).
- Task (ERPNext): `subject` và `description` bắt buộc; chỉ `Projects User` được tạo. Không có trường link tới HD Ticket (D-14).
- Kiểu lỗi đang dùng:
  - controller/whitelist của Frappe: `frappe.throw` (ValidationError), `frappe.only_for`/`PermissionError`;
  - tool: `{"ok": false, "reason": ...}` (ADR-005);
  - cổng: lỗi riêng không mang khóa (ADR-002).
- Kiểm quyền: role permission của Frappe + `has_permission` của Helpdesk + permlevel 7/8. Không có middleware riêng.
- Đọc cấu hình: Single DocType (`frappe.get_single`, `frappe.db.get_single_value`).
- Test:
  - `FrappeTestCase` (`frappe/tests/utils.py:20`) với `self.set_user`, `self.freeze_time`, `change_settings`; rollback sau mỗi class; không commit trong test;
  - factory của Helpdesk dùng lại được: `helpdesk.test_utils.make_ticket`, `make_team`, `create_agent`, `create_contact`, `make_todo` (`helpdesk/tests/AGENTS.md`); `frappe.flags.in_test`.
- `frappe.log_error(title)` mà không có `message` sẽ gọi `get_traceback(with_context=True)` (`frappe/utils/error.py:54`). Site `miyano` bật `developer_mode` → in biến cục bộ (ADR-002) → D-20.
- `frappe.permissions.AUTOMATIC_ROLES` = Guest, All, Desk User, Administrator (`permissions.py:31-37`).
- Webhook dùng cờ `enabled`, Server Script dùng cờ `disabled` (khác guide `:516`, xem mục 4.6).

## 2. Mô hình dữ liệu

Tên DocType theo guide (`ERP AI Setting`, `ERP AI Credential`, `ERP AI Log`). Tên trường dùng tiếng Anh snake_case, nhãn tiếng Việt (D-1); bảng đối chiếu với tên trong guide ở cuối mục này. Mọi DocType/Report có `"module": "ERP AI agent"` (ADR-001).

### 2.1 `ERP AI Setting` (Single) — `erp_ai/erp_ai_agent/doctype/erp_ai_setting/`

| Trường | Kiểu | Mặc định | Ràng buộc / ghi chú |
|---|---|---|---|
| `enabled` | Check | 0 | Bật agent. Khi bật thì validate đòi đủ 4 đơn giá > 0 và `trigger_keyword` không rỗng (STD-ERR-6, D-25) |
| `permission_level` | Select `L0`/`L1`/`L2`/`L3` | `L0` | Chỉ hàm `policy.effective_level` đọc (ADR-005) |
| `max_turns_per_run` | Int | 8 | 1..20 (NFR-3) |
| `max_runs_per_ticket_per_day` | Int | 5 | 1..50 (NFR-3) |
| `max_keys_per_call` | Int | 3 | 1..10 (NFR-7, guide `max_key_thu`) |
| `request_timeout_s` | Int | 60 | 5..300; timeout mỗi lời gọi API (D-5) |
| `monthly_budget_usd` | Currency | 10 | ≥ 0 (NFR-3) |
| `spent_this_month_usd` | Float (precision 6) | 0 | read_only; chỉ `tasks.recompute_monthly_spend` ghi (ADR-004) |
| `price_input_per_mtok` | Float | 0 | ≥ 0; USD / 1 triệu token |
| `price_cache_write_per_mtok` | Float | 0 | ≥ 0 (research `:64`) |
| `price_cache_read_per_mtok` | Float | 0 | ≥ 0 |
| `price_output_per_mtok` | Float | 0 | ≥ 0 |
| `model_classify_default` | Data | `claude-haiku-5-5` | Model phân loại khi khóa không khai riêng (guide `:653`); người phải xác nhận ID (guide `:680`) |
| `trigger_keyword` | Data | `@ai` | So không phân biệt hoa thường (AC-5d) |
| `excluded_teams` | Small Text | `Nhân sự & Hành chính`↵`Tài chính Kế toán` | Mỗi dòng một tên HD Team. Chỉ `policy.can_send_ticket` đọc (ADR-003) |
| `category_mapping` | Code (JSON) | xem D-8 | `{"A": {"ticket_type": str, "agent_group": str, "priority": str}, …}`; khóa ⊆ A–F; khóa con ⊆ 3 tên trên; sai → `frappe.throw` khi lưu |
| `prompt_digest` | Long Text | rỗng | Trích yếu HDSD đưa vào system prompt lập luận (A-14) |
| `alert_recipients` | Small Text | `info@miyano.com.vn` | Mỗi dòng một email (A-15) |
| `credentials` | Table → `ERP AI Credential` | — | Nhãn khác nhau, không phân biệt hoa thường |

Không có các trường guide `model_reason_default` (D-7), `doctype_duoc_ghi`, `property_cho_phep`, `system_prompt_override` (thuộc `L2`/`L3` hoặc không có trong spec, STD-DESIGN-5).

### 2.2 `ERP AI Credential` (bảng con) — `erp_ai/erp_ai_agent/doctype/erp_ai_credential/`

| Trường | Kiểu | Mặc định | Ai ghi (ADR-004) |
|---|---|---|---|
| `label` | Data, reqd | — | Người |
| `provider` | Select `Anthropic`/`OpenAI` | `Anthropic` | Người; khi chọn khóa, giá trị khác `Anthropic` bị loại (A-6) |
| `api_key` | **Password** | — | Người; chỉ cổng giải mã (ADR-002) |
| `model_classify` | Data | rỗng | Người; rỗng → `model_classify_default` |
| `model_reason` | Data | rỗng | Người; rỗng → khóa không dùng cho lập luận (D-7) |
| `try_order` | Int | 10 | Người; nhỏ thử trước (guide `uu_tien`) |
| `purpose` | Select `Chính`/`Dự phòng`/`Theo khách hàng` | `Chính` | Người; chỉ để đọc, không tham gia chọn khóa |
| `budget_month_usd` | Currency | 0 | Người; 0 = không giới hạn |
| `spent_month_usd` | Float (precision 6), read_only | 0 | `tasks.recompute_monthly_spend` |
| `enabled` | Check | 1 | Người |
| `status` | Select `Hoạt động`/`Tạm nghỉ`/`Hết hạn mức`/`Lỗi khóa` | `Hoạt động` | Cổng; người chỉ được chuyển `Lỗi khóa` → `Hoạt động`. `read_only_depends_on: eval:doc.status!='Lỗi khóa'` (D-15) |
| `paused_until` | Datetime, read_only | — | Cổng |
| `tokens_remaining` | Int, read_only | — | Cổng (header) |
| `limit_reset_at` | Datetime, read_only | — | Cổng (header) |
| `error_count` | Int, read_only | 0 | Cổng |
| `last_error` | Small Text, read_only | — | Cổng; chỉ chứa `kind status request-id`, không chứa văn bản khóa (NFR-5) |
| `last_success_at` | Datetime, read_only | — | Cổng |
| `note` | Small Text | — | Người |

### 2.3 `ERP AI Log` — `erp_ai/erp_ai_agent/doctype/erp_ai_log/`

Đặt tên tự động `hash`. Không ai có quyền write/delete (A-10); chỉ runner tạo (ADR-004). Mỗi bản ghi tương ứng một lượt gọi model hoặc một quyết định "bỏ qua".

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `ticket` | Link HD Ticket, `search_index` | |
| `run_id` | Data, `search_index` | `uuid4().hex`, gom các lượt của một lần chạy |
| `entry_type` | Select `classify`/`reason`/`skip` | `skip` = quyết định không gọi model |
| `turn` | Int | `classify` = 0; `reason` = 1..N; `skip` = 0 |
| `trigger` | Select `ticket_insert`/`comment_mention` | |
| `instructor` | Link User | người ra lệnh gần nhất (AC-15) |
| `model` | Data | |
| `input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens` | Int | từ usage; `None` → 0 |
| `cost_usd` | Float (precision 6) | do cổng tính (ADR-002 #6) |
| `credential_label` | Data | khóa đã trả lời |
| `keys_tried` | Small Text (JSON) | `[{"label": "...", "outcome": "<kind>"}]`, theo thứ tự thử |
| `latency_ms` | Int | |
| `stop_reason` | Data | stop reason của API (`end_turn`, `tool_use`, `max_tokens`…) hoặc của app: `max_turns`, `time_budget`, `gateway_error`, `unparseable`, `daily_limit`, `not_sendable`, `level_L0` |
| `tools_called` | Small Text (JSON) | danh sách tên tool trong lượt |
| `actions` | Small Text (JSON) | `[{"tool", "doctype", "name", "ok"}]` |
| `value_before`, `value_after` | Code (JSON) | trước/sau do tool ghi trả về (ADR-004) |
| `predicted_category` | Data | `A`..`F`; rỗng khi không phân loại được |
| `predicted_confidence` | Data | |
| `predicted_ticket_type`, `predicted_agent_group`, `predicted_priority` | Data | giá trị sau ánh xạ, đúng giá trị mà `L1` sẽ ghi |
| `applied` | Check | 1 khi tool ghi phân loại trả `ok=true` |
| `human_corrected_to` | Small Text (JSON) | `{"ticket_type", "agent_group", "priority"}`, lần sửa gần nhất (AC-11) |
| `human_corrected_by` | Link User | |
| `human_corrected_at` | Datetime | thời điểm sửa **đầu tiên**, dùng cho cửa sổ 7 ngày (A-12) |
| `error` | Small Text | `UNPARSEABLE: không phân loại được` (AC-3); `<kind> status=<n>` cho lỗi cổng |

Mẫu truy cập → chỉ mục:
- (1) đếm số lần chạy hôm nay của một phiếu: `ticket` + `creation`. `creation` đã có chỉ mục trên Frappe 15; thêm `search_index` cho `ticket`.
- (2) bản ghi `classify` gần nhất của phiếu (AC-11): cùng chỉ mục.
- (3) tổng chi phí trong tháng theo `credential_label` (AC-16): quét theo `creation`. Khối lượng ≤ 40 dòng/phiếu/ngày, nên không cần chỉ mục thêm.

Không có bộ đếm thứ hai (ADR-004 #2).

### 2.4 Custom field trên HD Ticket (permlevel 8, `module = "ERP AI agent"`)

| fieldname | label | fieldtype | Thuộc tính |
|---|---|---|---|
| `ai_section` | ERP AI | Section Break | `insert_after` = trường cuối cùng của meta HD Ticket lúc cài, để không cắt section có sẵn |
| `ai_resolution_hint` | Hướng giải quyết (AI) | Text Editor | read_only |
| `ai_confidence` | Độ tin cậy (AI) | Select `\nCao\nTrung bình\nThấp` | read_only |
| `ai_classified_by` | Phân loại bởi | Select `\nAI\nNgười` | read_only (server vẫn ghi được) |
| `ai_updated_at` | AI cập nhật lúc | Datetime | read_only |
| `ai_opt_out` | Không dùng AI cho phiếu này | Check | người (HD Agent) sửa được |

Bỏ `ai_so_luot_hom_nay` và `ai_cho_xac_nhan` của guide (D-12).

### 2.5 Report `ERP AI Accuracy` (Script Report, ref DocType `ERP AI Log`) — `erp_ai/erp_ai_agent/report/erp_ai_accuracy/`

Bộ lọc `from_date`, `to_date` (bắt buộc, tính cả hai đầu, theo `creation`). Cột: `category`, `predictions`, `corrected`, `pending`, `accuracy_pct`. Có 6 dòng A–F và 1 dòng `Tổng`. Định nghĩa ở mục 3.8.

### 2.6 Đối chiếu tên guide → design (D-1)

`muc_quyen`→`permission_level`, `max_key_thu`→`max_keys_per_call`, `uu_tien`→`try_order`, `muc_dich`→`purpose`, `budget_thang_usd`→`budget_month_usd`, `da_dung_thang_usd`→`spent_month_usd`, `trang_thai`→`status`, `tam_nghi_den`→`paused_until`, `token_con_lai`→`tokens_remaining`, `han_muc_reset_luc`→`limit_reset_at`, `so_lan_loi`→`error_count`, `loi_gan_nhat`→`last_error`, `dung_thanh_cong_luc`→`last_success_at`, `ghi_chu`→`note`, `dau_muc_mapping`→`category_mapping`, `nguoi_ra_lenh`→`instructor`, `da_chuyen_key`→`keys_tried`, `hanh_dong`→`actions`, `gia_tri_truoc/sau`→`value_before/after`, `ai_huong_giai_quyet`→`ai_resolution_hint`, `ai_do_tin_cay`→`ai_confidence`, `ai_phan_loai_boi`→`ai_classified_by`, `ai_cap_nhat_luc`→`ai_updated_at`, `ai_bo_qua`→`ai_opt_out`.

## 3. API / hợp đồng

Mọi hợp đồng đều mới, phiên bản v1, không có bên tiêu thụ cũ. Với Helpdesk, chỉ **thêm** custom field và dòng template, không có thay đổi phá vỡ (ADR-006). Mỗi biên giới dùng một kiểu lỗi duy nhất, theo đúng mã sẵn có:

| Biên giới | Kiểu lỗi |
|---|---|
| Whitelist / controller / form | `frappe.throw(msg)` → `frappe.ValidationError`; `frappe.only_for` → `frappe.PermissionError` |
| Tool (model gọi) | luôn trả `dict`: `{"ok": false, "reason": "<tiếng Việt, ≤ 200 ký tự>"}`; không ném ngoại lệ (ADR-005 #3) |
| Cổng model | ném `GatewayError` (mục 3.4.1); `str()` chỉ chứa `kind`, `status`, nhãn khóa, request-id |
| Handler / job / scheduler | không ném ra framework: lỗi được ghi `frappe.log_error(<tiêu đề hằng>, <message tường minh>)` rồi dừng (D-20) |

Hằng dùng chung ở `erp_ai/constants.py` (D-2):
- `AGENT_USER = "ai.agent@miyano.com.vn"`, `ROLE_AGENT = "ERP AI Agent"`, `ROLE_INSTRUCTOR = "ERP AI Instructor"`, `HELPDESK_AGENT_ROLE = "Agent"`;
- `SETTING_DOCTYPE`, `CREDENTIAL_DOCTYPE`, `LOG_DOCTYPE`;
- `LEVELS`, `CATEGORIES = ("A".."F")`, `CONFIDENCE_VALUES`, `CLASSIFIED_BY_AI = "AI"`, `CLASSIFIED_BY_HUMAN = "Người"`;
- 4 hằng trạng thái khóa; `TRIGGER_TICKET_INSERT`, `TRIGGER_COMMENT_MENTION`;
- `JOB_TIMEOUT_S = 600`, `JOB_SAFETY_MARGIN_S = 60`, `PROBE_TIMEOUT_S = 10`;
- `CLASSIFICATION_FIELDS = ("ticket_type", "agent_group", "priority")`;
- tiêu đề Error Log: `TITLE_WRONG_USER = "erp_ai: sai tài khoản job"`, `TITLE_RUN_FAILED = "erp_ai: lần chạy lỗi"`, `TITLE_ALARM = "erp_ai: CẢNH BÁO"`, `TITLE_NOTICE = "erp_ai: thông báo"`;
- `LOGGER_NAME = "erp_ai"`.

### 3.1 Cửa vào: `doc_events` (`erp_ai/handlers.py`) — ADR-003

Khai trong `hooks.py`: HD Ticket `before_insert`, `after_insert`, `validate`, `on_update`; HD Ticket Comment `after_insert`. Các handler không ném lỗi nào làm hỏng lượt lưu của người, không gọi mạng, không import `erp_ai.gateway` hay `erp_ai.agent.runner`.

| Hàm | Hành vi là hợp đồng |
|---|---|
| `ticket_before_insert(doc, method=None)` | Đặt `doc.flags.erp_ai_prefilled = all(doc.get(f) for f in CLASSIFICATION_FIELDS)`. Chạy trước khi Helpdesk tự điền mặc định (D-4) |
| `ticket_after_insert(doc, method=None)` | Xếp đúng 1 job `ticket_insert` khi đủ: agent bật **và** `doc.owner != AGENT_USER` **và** `policy.can_send_ticket(doc)` **và** `not doc.flags.erp_ai_prefilled`. Còn lại: 0 job (AC-5 a, b, c, e) |
| `ticket_validate(doc, method=None)` | Khi phiếu không mới, `frappe.session.user != AGENT_USER`, ít nhất một trường trong `CLASSIFICATION_FIELDS` đổi (`has_value_changed`), và phiếu đã có bản ghi `classify` có `predicted_category` → đặt `doc.ai_classified_by = "Người"` và `doc.flags.erp_ai_human_corrected = True`. Chạy cả khi agent tắt (vẫn đo được). Không xếp job (ADR-003 #1) |
| `ticket_on_update(doc, method=None)` | Bỏ qua khi `doc.flags.in_insert`. Khi cờ `erp_ai_human_corrected` bật → cập nhật bản ghi `classify` gần nhất: `human_corrected_to` (JSON 3 giá trị hiện tại), `human_corrected_by`; `human_corrected_at` chỉ đặt nếu còn rỗng. Ghi bằng `frappe.db.set_value(..., update_modified=False)` (ADR-004) |
| `comment_after_insert(doc, method=None)` | Xếp 1 job `comment_mention` khi đủ: agent bật **và** `doc.owner` và `doc.commented_by` đều ≠ `AGENT_USER` **và** `policy.contains_keyword(doc.content)` **và** `policy.can_send_ticket(doc.reference_ticket)`. Còn lại: 0 job (AC-5 c, d, e) |

Mỗi lần xếp job hoặc quyết định bỏ qua → `frappe.logger(LOGGER_NAME).info` với ticket, trigger, lý do. Không ghi nội dung phiếu vào log.

### 3.2 Lõi agent: hàm xếp hàng duy nhất (`erp_ai/agent/queue.py`) — ADR-003 #2

`enqueue_agent_run(ticket_name: str, trigger: str) -> bool`
- Đầu vào: `trigger` ∈ {`ticket_insert`, `comment_mention`}; giá trị khác → `ValueError` (lỗi lập trình).
- `job_id = f"erp_ai::{ticket_name}::{trigger}"`.
- Chặn trùng trong cùng giao dịch (D-3): tập `frappe.flags.erp_ai_pending_job_ids`. Lần đầu tạo tập thì đăng ký `frappe.db.after_commit.add(...)` và `frappe.db.after_rollback.add(...)` để xóa tập. Nếu `job_id` đã có trong tập → trả `False`, không gọi `enqueue`.
- Lời gọi duy nhất tới runner trong `erp_ai/**`: `frappe.enqueue("erp_ai.agent.runner.run_for_ticket", queue="long", timeout=600, enqueue_after_commit=True, job_id=job_id, deduplicate=True, ticket_name=ticket_name, trigger=trigger)`. Trả `True`.

### 3.3 Lõi agent: chính sách, thẩm quyền, prompt, phân loại

`erp_ai/agent/policy.py` — chỉ ORM đọc:

| Hàm | Đầu vào → đầu ra | Hợp đồng |
|---|---|---|
| `is_enabled()` | → `bool` | `frappe.db.get_single_value(SETTING_DOCTYPE, "enabled")` |
| `can_send_ticket(ticket)` | `str` (tên) \| Document \| dict → `bool` | **Hàm điều kiện gửi duy nhất** (ADR-003 #4). `False` khi `ai_opt_out` = 1 hoặc `agent_group` (đã chuẩn hóa: strip, gộp khoảng trắng, casefold) trùng một dòng của `excluded_teams`. `agent_group` rỗng → `True`. Phiếu không tồn tại → `False`. Hai tên trường chỉ xuất hiện dưới dạng chuỗi trong file này (`OPT_OUT_FIELD`, `EXCLUDED_TEAMS_FIELD`, `SEND_POLICY_FIELDS`) và trong JSON DocType |
| `contains_keyword(content)` | `str \| None` → `bool` | `trigger_keyword.casefold() in (content or "").casefold()`; từ khóa rỗng → `False` |
| `effective_level(settings)` | Document `ERP AI Setting` → `"L0".."L3"` | Nơi duy nhất đọc `permission_level` (ADR-005). Khi `spent_this_month_usd > monthly_budget_usd` → `min(level, "L1")` theo thứ tự `LEVELS`; `L0` không bao giờ thành `L1` (A-4) |
| `runs_today(ticket_name, now=None)` | → `int` | Số `run_id` khác nhau trong `ERP AI Log` của phiếu, `entry_type ∈ {classify, reason}`, `creation ≥ 00:00 hôm nay` (giờ hệ thống). Nguồn duy nhất cho giới hạn ngày (ADR-004) |

`erp_ai/agent/authority.py` — AC-7, guide `:85-142`:

| Hàm | Hợp đồng |
|---|---|
| `is_instruction(author, ticket_name) -> bool` | `False` nếu `author` rỗng, ∈ {`Administrator`, `Guest`, `AGENT_USER`} (D-16). `True` nếu có `ROLE_INSTRUCTOR`. `True` nếu `author` có trong `_assign` của phiếu **và** ToDo mới nhất (status ≠ Cancelled, `reference_type = HD Ticket`, `reference_name = ticket_name`, `allocated_to = author`) có `assigned_by` khác rỗng và ≠ `author`. Còn lại `False` |
| `latest_instructor(ticket_name) -> str \| None` | Duyệt comment của phiếu theo `creation` giảm dần, tác giả = `commented_by or owner`; trả tác giả đầu tiên có `is_instruction`. Không ai → xét `owner` của phiếu. Vẫn không → `None` |
| `label_comments(ticket_name, comments) -> list[dict]` | Gắn `role: "chỉ thị" \| "dữ liệu"` cho từng comment (D-24) |

`erp_ai/agent/prompts.py` — guide 16.4–16.5, AC-3:
- `CLASSIFY_PROMPT`: nguyên văn guide `:1348-1403`.
- `CORE_PROMPT`: nguyên văn guide `:1409-1457`, kèm các khối `CATEGORY_TABLE` (16.1), `ROUTING_TABLE` (16.2), `CONVENTIONS` (16.3).
- `ticket_text(subject, description) -> str`: `"Tiêu đề: …\n\nNội dung:\n…"`; HTML được bỏ bằng `frappe.utils.strip_html`; nội dung cắt ở `DESCRIPTION_MAX_CHARS = 6000`.
- `build_classify_request(subject, description) -> dict`: trả `{"system": [{"type": "text", "text": CLASSIFY_PROMPT, "cache_control": {"type": "ephemeral"}}], "messages": [{"role": "user", "content": ticket_text(...)}]}`. Đây là **nguồn duy nhất** cho cả runner lẫn eval.
- `build_reason_system(prompt_digest) -> list[dict]`: một khối `CORE_PROMPT + tables + conventions + digest`, có `cache_control`.
- `build_initial_message(ticket: dict, comments: list[dict], trigger: str, classification: dict | None) -> str`: JSON gồm phiếu (subject, nội dung ≤ 6000 ký tự, status, priority, ticket_type, agent_group, creation); tối đa 30 comment gần nhất (tác giả theo họ tên, `role`, nội dung ≤ 2000 ký tự); trigger; kết quả phân loại. Kèm một dòng việc cần làm: phiếu mới → gọi `set_resolution_hint` một lần, rồi `post_comment` nếu cần; comment → trả lời bằng `post_comment`. Không có file đính kèm (NFR-4).

`erp_ai/agent/classification.py` — AC-3, AC-10:
- `parse_classification(text: str) -> Classification | None`.
  - Dataclass `Classification(category, confidence, reason, team, priority, needs_split, requests)`.
  - Chấp nhận JSON thuần hoặc JSON nằm trong một rào ```json duy nhất.
  - Trả `None` khi: không phải JSON object; `dau_muc` ∉ A–F; `do_tin_cay` ∉ `CONFIDENCE_VALUES`.
  - `uu_tien` ∉ {Low, Medium, High, Urgent} → `priority = None`. Không bao giờ ném lỗi.
- `load_mapping(raw: str | None) -> dict`: parse và kiểm schema của `category_mapping`. Sai → `{}`, và lỗi được ghi vào `error` của nhật ký lượt đó (controller đã chặn sai lúc lưu).
- `validate_mapping(raw) -> None`: ném `frappe.ValidationError` có thông báo cụ thể; controller Setting gọi hàm này.
- `resolve_ticket_values(classification, subject, mapping) -> dict`: trả `{"ticket_type", "agent_group", "priority"}` lấy từ `mapping[category]` (thiếu → `None`); tiêu đề chứa `[GẬP]` → `priority = "Urgent"` (guide `:1337`). Giá trị model trả trong `nhom`/`uu_tien` không dùng để ghi (D-8).

`erp_ai/agent/run_log.py`: `write_entry(**fields) -> str`. Hàm này là nơi duy nhất tạo `ERP AI Log` (ADR-004): serialize JSON, insert có phân quyền dưới tài khoản agent, commit khi `not frappe.flags.in_test` (D-20).

### 3.4 Cổng model (`erp_ai/gateway/`) — ADR-002

`import anthropic` chỉ có trong `erp_ai/gateway/client.py`. API công khai export ở `erp_ai/gateway/__init__.py`. Bên gọi dùng dạng `from erp_ai import gateway; gateway.call_model(...)`, nên test chỉ cần patch một chỗ là `erp_ai.gateway.call_model`.

#### 3.4.1 Hàm công khai

`call_model(task, *, system, messages, max_tokens, tools=None, deadline=None) -> ModelResult`

| Phần | Hợp đồng |
|---|---|
| Đầu vào | `task` ∈ {`classify`, `reason`} (khác → `ValueError`). `system`, `messages`, `tools` theo định dạng Messages API. `deadline` = mốc `time.monotonic()`; `None` = chỉ dùng `request_timeout_s` |
| Đầu ra | `ModelResult` (frozen dataclass): `content: list[dict]` (`{"type":"text","text"}` \| `{"type":"tool_use","id","name","input"}`), `text: str` (nối các khối text), `stop_reason`, `model`, `usage: dict` (4 khóa int), `cost_usd: float`, `credential_label`, `keys_tried: list[dict]`, `latency_ms`, `request_id`. Không có kiểu SDK nào lọt ra ngoài cổng |
| Lỗi | `GatewayError(kind, status, credential_label, request_id, keys_tried)` với `kind` ∈ `no_key` (không có khóa hợp lệ), `all_keys_failed` (đã thử `max_keys_per_call` khóa, khóa nào cũng bị cầu dao chuyển), `bad_request` (400 thường, không chuyển khóa), `deadline` (thời gian còn lại < 5 s), `unexpected` (ngoại lệ không phải của API). Ném `from None` để bỏ chuỗi ngoại lệ gốc |
| Thử lại | Chỉ bằng cách chuyển khóa, tối đa `max_keys_per_call` khóa mỗi lời gọi; không thử lại trên cùng khóa (ADR-002 #4). Timeout mỗi lần thử = `min(request_timeout_s, deadline − now)` |
| Không xét | agent bật/tắt, mức quyền, nhóm loại trừ (ADR-002 #7) |

`probe_credential(row_name: str) -> dict`
- Trả `{"label", "ok": bool, "error_kind": str | None, "status": int | None}`.
- Lời gọi 1 token (`max_tokens=1`, nội dung `"ping"`), model = `model_classify` của khóa hoặc mặc định, timeout `PROBE_TIMEOUT_S`.
- Cập nhật trạng thái khóa theo cùng bảng cầu dao. Thành công → `Hoạt động`.
- `provider ≠ Anthropic` → `ok=false`, `error_kind="unsupported_provider"`, trạng thái không đổi.

`reprobe_exhausted_keys() -> list[dict]`: dò các khóa `enabled = 1` và `status = Hết hạn mức` (không dò `Lỗi khóa`). Trả danh sách kết quả.

#### 3.4.2 Chọn khóa (`credentials.py`) — AC-17

- Đọc dòng khóa bằng `frappe.db.get_all(CREDENTIAL_DOCTYPE, filters={parent, parenttype, parentfield})` ngay lúc gọi (không cache).
- Loại khóa: `enabled = 0`; `status ∈ {Lỗi khóa, Hết hạn mức}`; `paused_until > now`; `budget_month_usd > 0` và `spent_month_usd ≥ budget_month_usd`; `provider ≠ Anthropic` (A-6); đã thử trong lời gọi này. Việc `reason` còn loại thêm khóa có `model_reason` rỗng (D-7).
- Sắp theo `(try_order or 99, error_count or 0, idx)`.
- Đọc khóa bằng `frappe.utils.password.get_decrypted_password(CREDENTIAL_DOCTYPE, row_name, "api_key", raise_exception=False)` → truyền thẳng vào `client.send`. Không giữ trong đối tượng nào được trả ra.
- Ghi trạng thái: `frappe.db.set_value(CREDENTIAL_DOCTYPE, row_name, {...}, update_modified=False)`. Chỉ cổng ghi các trường này (ADR-004).

#### 3.4.3 Bảng cầu dao (`breaker.py`, hàm thuần `decide(failure, error_count) -> Action`) — AC-17, research `:65`, D-6

`client.py` đổi ngoại lệ SDK thành `ApiFailure(status, kind, error_type, error_code, message_prefix, retry_after)`.

| # | Điều kiện | `status` mới | Nghỉ | Chuyển khóa | Báo | `kind` |
|---|---|---|---|---|---|---|
| 1 | 429 và `error.details.error_code = enforced_spend_limit_reached` | Hết hạn mức | — | Có | tin (email) | `quota` |
| 2 | 429 khác | Tạm nghỉ | `retry-after + 1 s` (thiếu header → 61 s) | Có | — | `rate_limit` |
| 3 | 529 | Tạm nghỉ | `min(30 s × error_count mới, 600 s)` | Có | — | `overloaded` |
| 4 | ≥ 500 (trừ 529), `APITimeoutError`, `APIConnectionError` | Tạm nghỉ | 30 s | Có | — | `server` / `timeout` |
| 5 | 402 | Hết hạn mức | — | Có | tin | `quota` |
| 6 | 400 và message bắt đầu `You have reached your specified` | Hết hạn mức | — | Có | tin | `quota` |
| 7 | 401, 403 | Lỗi khóa | — | Có | **động** (Error Log + email) | `auth` |
| 8 | 4xx khác (400, 404, 413, 422…) | không đổi | — | **Không** → `GatewayError(bad_request)` | — | `bad_request` |
| 9 | Ngoại lệ không thuộc API | không đổi | — | Không → `GatewayError(unexpected)` | — | `unexpected` |

- Hàng 1–7: `error_count += 1`, `last_error = f"{kind} status={status} request_id={rid}"`.
- Tin/động chỉ gửi khi trạng thái thực sự chuyển sang giá trị mới (D-21).
- Thành công:
  - `status = Hoạt động`, `error_count = 0`, `last_error = ""`, `last_success_at = now`;
  - header `anthropic-ratelimit-tokens-remaining` (int) → `tokens_remaining`; `anthropic-ratelimit-tokens-reset` (RFC 3339 → giờ hệ thống) → `limit_reset_at`;
  - header vắng hoặc sai định dạng → bỏ qua (NFR-8, research `:67`);
  - `tokens_remaining < 20000` và có `limit_reset_at` → `status = Tạm nghỉ`, `paused_until = limit_reset_at` (NFR-8).
- `no_key` và `all_keys_failed` → báo động `Hết khóa dùng được cho việc '<task>'` (AC-17).

#### 3.4.4 Client và chi phí

- `client.py`: `_build_client(api_key, timeout)` → `anthropic.Anthropic(api_key=api_key, max_retries=0, timeout=timeout)`. Đây là chỗ duy nhất tạo client; test patch hàm này.
- `send(api_key, *, timeout, request) -> RawReply(message: dict, headers: dict, request_id)` dùng `client.messages.with_raw_response.create(**request)` → `.parse()` + `.headers` (research `:44`).
- `cost.py`: `compute_cost(usage, prices) -> float` = `(input × p_in + cache_creation × p_cache_write + cache_read × p_cache_read + output × p_out) / 1e6`, làm tròn 6 chữ số. Đây là công thức duy nhất trong app (ADR-002 #6).

### 3.5 Registry tool (`erp_ai/agent/tools/registry.py`) — ADR-005

- `ToolContext` (frozen dataclass): `ticket_name`, `effective_level`, `instructor: str | None`, `run_id`, `category_mapping: dict`, `agent_user`. Runner dựng một lần cho mỗi lần chạy. Tool không đọc cấu hình.
- `get_tool_schemas(effective_level: str, has_instructor: bool) -> list[dict]` (AC-8):
  - `L0` → `[]` (không có lượt lập luận, A-3);
  - `L1`/`L2`/`L3` → `READ_TOOLS + TICKET_WRITE_TOOLS`, cộng `create_task` khi `has_instructor` (A-1, A-5);
  - trả bản sao để runner gắn `cache_control` vào tool cuối.
- `execute_tool(name, arguments, context) -> dict`:
  - tên không thuộc `get_tool_schemas(context.effective_level, bool(context.instructor))` → `ok=false` "tool không được cấp ở mức/thẩm quyền hiện tại";
  - kiểm `arguments` theo schema của tool (bộ kiểm nhỏ tự viết: thiếu khóa bắt buộc, sai kiểu, ngoài enum, quá độ dài) → `ok=false` "tham số không hợp lệ: <khóa>" (STD-ERR-2; không thêm thư viện, STD-DEP-3);
  - ghi chạy trong `frappe.db.savepoint`. Ngoại lệ bất ngờ → rollback về savepoint và ném lên, runner biến thành `tool_result` có `is_error`.

| Tool | Tham số (JSON schema rút gọn) | Trả về khi `ok=true` | Từ chối (`ok=false`) |
|---|---|---|---|
| `get_ticket` | `name?: string` (mặc định phiếu hiện tại) | các trường phiếu như `build_initial_message` | không có quyền đọc; `can_send_ticket` = false; không tồn tại |
| `list_comments` | `ticket?: string`, `limit?: int 1..50 = 20` | `[{author, role, creation, content}]` | như trên |
| `search_resolved_tickets` | `query: string 2..100`, `limit?: int 1..10 = 5` | phiếu `status_category = Resolved`, `subject`/`description` LIKE chuỗi cố định (tham số hóa, STD-SEC-3), đã lọc `can_send_ticket` và quyền: `[{name, subject, ticket_type, agent_group, resolution_date, resolution_details ≤ 1500}]` | — |
| `get_record` | `doctype: string`, `name: string` | bản ghi sau `apply_fieldlevel_read_permissions()`, bỏ mọi trường kiểu Password | `doctype` thuộc `DENIED_DOCTYPES` → "bị cấm"; ngoài `ALLOWED_READ_DOCTYPES` → "chưa được mở"; không có quyền; HD Ticket/HD Ticket Comment thuộc phiếu không gửi được (D-10) |
| `search_source` | `pattern: string 2..200` (chuỗi cố định, không phân biệt hoa thường), `app?: string`, `extension?: enum DUOI_CHO_PHEP` | ≤ 40 `{path, line, text ≤ 300}` | gốc ngoài `apps/`; tên bí mật |
| `read_source` | `path: string`, `offset?: int ≥ 1 = 1`, `limit?: int 1..400 = 200` | `{path, from_line, total_lines, content}` | ngoài `apps/` (kể cả `../`, symlink); tên bí mật; đuôi không cho phép; không phải file |
| `git_source` | `app: string`, `subcommand: enum log/show/diff/blame`, `args?: string[] ≤ 10` | `{output ≤ 8000}` | subcommand khác; arg bắt đầu bằng cờ cấm (mục 5.4); repo ngoài `apps/`; thiếu `git` → "chưa cài git"; quá 30 s → "quá thời gian" |
| `set_classification` | `category: enum A–F`, `confidence: enum Cao/Trung bình/Thấp` | `{before, after, skipped: [{field, reason}]}` | phiếu có `ai_classified_by = Người` → "người đã phân loại, không ghi đè"; thiếu quyền ghi bất kỳ trường đích nào |
| `set_resolution_hint` | `text: string 1..5000` | `{before, after}` | thiếu quyền ghi |
| `post_comment` | `content: string 1..5000` | `{comment: name}` | thiếu quyền tạo |
| `create_task` | `subject: string 1..140`, `description: string 1..5000` | `{task: name}` | không có người ra lệnh; DocType `Task` không có trên site; thiếu quyền |

- Tool ghi chỉ ghi lên `context.ticket_name`; không tool nào nhận tên DocType hay tên trường (AC-8).
- `set_classification` ghi các trường có giá trị tồn tại thật (`frappe.db.exists` trên HD Ticket Type / HD Team / HD Ticket Priority), cùng `ai_confidence`, `ai_classified_by = "AI"`, `ai_updated_at = now`. Giá trị không tồn tại → vào `skipped` kèm lý do (AC-10).
- Trước khi ghi, mọi tool ghi kiểm `doc.has_permission("write")` và, với từng trường đích, `doc.has_permlevel_access_to(field, permission_type="write")`. Lý do: thiếu quyền permlevel thì Frappe âm thầm đặt lại giá trị thay vì báo lỗi (AC-8 "`ok=false`, bản ghi không đổi").
- Hằng (định nghĩa một lần, ADR-005):
  - `DENIED_DOCTYPES` (trong `read.py`) = {`ERP AI Setting`, `ERP AI Credential`, `ERP AI Log`, `Salary Slip`, `Employee`, `Purchase Invoice`, `Payment Entry`, `GL Entry`, `User`, `Role Permission`, `Custom DocPerm`} ∪ mọi DocType có `module = "ERP AI agent"`;
  - `ALLOWED_READ_DOCTYPES` = {`HD Ticket`, `HD Ticket Comment`, `HD Team`, `HD Ticket Type`, `HD Ticket Priority`, `HD Article`};
  - `DUOI_CHO_PHEP` và `TEN_CAM` đúng guide `:342-345`.
- Kết quả tool đưa lại cho model được cắt ở `TOOL_RESULT_MAX_CHARS = 20000`.

### 3.6 Whitelist: `check_keys` (`erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py`) — AC-19

`erp_ai.erp_ai_agent.doctype.erp_ai_setting.erp_ai_setting.check_keys(label: str | None = None) -> list[dict]`
- Quyền: `frappe.only_for("System Manager")` → `PermissionError` cho mọi role khác.
- Đầu vào: `label` tùy chọn. Có `label` mà không khớp dòng nào → `frappe.throw("Không có khóa '<label>'")`.
- Đầu ra: theo thứ tự `idx`, `[{"label", "ok", "error_kind", "status"}]` (chính là kết quả `gateway.probe_credential`). Không trả văn bản ngoại lệ (NFR-5).
- Chạy đồng bộ: mỗi khóa ≤ `PROBE_TIMEOUT_S` (D-13). Không gọi `.save()` lên cấu hình (ADR-004).

Controller `ERPAISetting.validate()`:
- (a) Với mỗi dòng khóa đã có, lấy lại từ DB các trường tự quản (`status`, `paused_until`, `tokens_remaining`, `limit_reset_at`, `error_count`, `last_error`, `last_success_at`, `spent_month_usd`). Ngoại lệ duy nhất: DB đang `Lỗi khóa` và form gửi `Hoạt động` → chấp nhận, đặt `error_count = 0`, `last_error = ""`. Dòng mới → các trường tự quản về mặc định (D-15).
- (b) `spent_this_month_usd` lấy lại từ DB.
- (c) Nhãn không rỗng và khác nhau (không phân biệt hoa thường).
- (d) `classification.validate_mapping(category_mapping)`.
- (e) Kiểm giới hạn số ở mục 2.1.
- (f) `enabled = 1` thì cần 4 đơn giá > 0 và `trigger_keyword` không rỗng.
- Mọi lỗi dùng `frappe.throw`.

`erp_ai_setting.js`: nút "Kiểm tra khóa" gọi `check_keys`, hiện bảng kết quả, rồi `frm.reload_doc()`.

### 3.7 Scheduler, cài đặt, eval

| Hàm | Lịch / cách gọi | Hợp đồng |
|---|---|---|
| `erp_ai.tasks.recompute_monthly_spend(now=None)` | `daily` | `spent_this_month_usd` = tổng `cost_usd` của `ERP AI Log` có `creation` từ đầu tháng của `now`. Mỗi khóa: `spent_month_usd` = tổng theo `credential_label` (nhãn không có → 0). Ghi bằng `frappe.db.set_single_value` / `set_value(update_modified=False)` (ADR-004). Ngày 1 trong tháng → tổng của tháng mới ≈ 0, tức là reset (AC-16, D-19) |
| `erp_ai.tasks.check_privilege_escalation()` | `daily` | Báo động (mục 4.6) khi có ít nhất một điều kiện của AC-18 |
| `erp_ai.tasks.reprobe_exhausted_keys()` | `hourly` | Gọi `gateway.reprobe_exhausted_keys()`. Khóa hồi phục → cổng gửi tin "Khóa <label> đã dùng lại được" |
| `erp_ai.install.after_install()` / `after_migrate()` | hook | Cả hai gọi `ensure_setup()`, chạy lặp lại không lỗi (ADR-006, mục 6) |
| `erp_ai.eval.export_tickets.export(path)` | người gọi qua `bench execute` (architecture.md) | Ghi JSONL, mỗi dòng đúng 6 khóa `subject, description, ticket_type, agent_group, priority, owner`; bỏ phiếu `can_send_ticket = false` (A-9); không cần agent bật. `path` nằm trong thư mục repo của app → `ValueError("Không ghi dữ liệu phiếu vào repo")`. Trả số dòng đã ghi |
| `erp_ai.eval.run_eval.run(path)` | như trên | Đọc JSONL. Dòng chưa có `predicted_category` → `build_classify_request` + `gateway.call_model("classify", …)` + `parse_classification`. In `format_report(compute_metrics(rows, mapping))`. Trả dict số liệu |
| `erp_ai.eval.run_eval.compute_metrics(rows, mapping) -> dict` | thuần | Nhãn = đầu mục có `mapping[c]["ticket_type"] == row["ticket_type"]`; không khớp → `skipped_unlabeled`. Trả `labeled`, `correct`, `accuracy`, `per_category{c: count, correct, accuracy}`, `confusion{expected: {predicted: n}}` (6×6), `unclassified`, `top_owner`, `non_top_owner{count, correct, accuracy}`, `verdict` ∈ {`≥ 85%`, `70–85%`, `< 70%`} với ngưỡng `≥ 0.85` / `≥ 0.70` (AC-1). Không phân loại được → tính là sai |

### 3.8 Report `ERP AI Accuracy` — AC-12, A-12

`execute(filters) -> (columns, data)`. Lấy các bản ghi `entry_type = classify`, `predicted_category` khác rỗng, `creation` trong khoảng lọc.
- `corrected`: `human_corrected_at ≤ creation + 7 ngày` **và** `human_corrected_to` khác dự đoán ở ít nhất một trong 3 trường (D-17).
- `pending`: chưa `corrected` và `creation > now − 7 ngày`.
- `accuracy_pct = (predictions − pending − corrected) / (predictions − pending) × 100`; mẫu = 0 → để trống.
- Cùng công thức cho từng dòng A–F và dòng `Tổng`.

## 4. Luồng

Thời hạn mọi lời gọi ra ngoài:

| Lời gọi | Thời hạn |
|---|---|
| Claude API | `min(request_timeout_s, deadline − now)`; hạn chót của job = start + `JOB_TIMEOUT_S − JOB_SAFETY_MARGIN_S` = 540 s (D-5) |
| Dò khóa | 10 s |
| `git` | 30 s |
| Email | gửi bất đồng bộ qua Email Queue (`frappe.sendmail(..., delayed=True)`) |

Kết quả của lời gọi API có ba trạng thái:
- thành công → `ModelResult`;
- thất bại → `GatewayError`;
- **không rõ** (timeout sau khi request đã đi) → hàng 4 của cầu dao (cho khóa nghỉ, chuyển khóa). Lượt đó được ghi `error = timeout` mà không có usage. Đối soát chi phí "không rõ" bằng bảng Usage trên Console (việc của người, guide `:951-953`).

### 4.1 Phiếu mới (AC-5 a/b/c/e, NFR-1)
1. Người lưu HD Ticket → `ticket_before_insert` ghi cờ `erp_ai_prefilled` → Helpdesk tự điền mặc định → insert.
2. `ticket_after_insert`: agent tắt → dừng (AC-4); `owner = AGENT_USER` → dừng; `can_send_ticket = false` → dừng (0 job, 0 byte); `prefilled` → dừng.
3. `enqueue_agent_run(name, "ticket_insert")` → callback đăng ký vào `after_commit` → job vào hàng đợi `long` sau commit. 0 lời gọi model trong request.
- Lỗi: ngoại lệ trong handler sẽ làm hỏng lượt lưu của người. Vì vậy handler chỉ gồm các phép đọc có kiểm trước (`frappe.db.get_single_value`, `get_value`), không có khối try/except nuốt lỗi (STD-ERR-1).

### 4.2 Comment mới (AC-5 c/d/e/f)
1. `comment_after_insert`: agent tắt / tác giả là agent / không có từ khóa / phiếu không gửi được → 0 job.
2. `enqueue_agent_run(ticket, "comment_mention")`. Trùng trong cùng giao dịch → bỏ (D-3). Khác request mà job cũ còn `queued`/`started` → `deduplicate` của Frappe bỏ (research `:102`).

### 4.3 Job agent `run_for_ticket(ticket_name, trigger)` — ADR-003 #3
Toàn bộ thân hàm nằm trong `try/except Exception`. Khi bắt được lỗi: `frappe.log_error(TITLE_RUN_FAILED, f"ticket={ticket_name} trigger={trigger} error={type(exc).__name__}")` rồi kết thúc. Lý do: nếu job ném lỗi ra ngoài, framework sẽ ghi traceback có biến cục bộ (D-20).
1. **(a)** Tài khoản agent không tồn tại hoặc bị tắt → `log_error(TITLE_WRONG_USER, "Không có tài khoản agent")` → dừng. `frappe.set_user(AGENT_USER)`. `frappe.session.user != AGENT_USER` → `log_error(TITLE_WRONG_USER, f"Sai tài khoản: {frappe.session.user}")` → dừng, chưa đọc phiếu (AC-6).
2. **(b)** `settings = frappe.get_single(SETTING_DOCTYPE)`; `enabled = 0` → dừng, không ghi nhật ký.
3. **(c)** `can_send_ticket(ticket_name) = false` → nhật ký `skip`/`not_sendable` → dừng (NFR-4).
4. **(d)** `runs_today ≥ max_runs_per_ticket_per_day` → nhật ký `skip`/`daily_limit` → dừng (AC-15).
5. **(e)** `level = effective_level(settings)`; `run_id = uuid4().hex`; `deadline = monotonic() + 540`.
6. **Bước phân loại** (chỉ khi `trigger = ticket_insert`):
   - `call_model("classify", **build_classify_request(subject, description), max_tokens=400, deadline=deadline)`.
   - `GatewayError` → nhật ký `classify` có `error`, `stop_reason = gateway_error` → dừng.
   - `parse_classification(text)`: `None` → nhật ký có `error = "UNPARSEABLE: không phân loại được"`, `stop_reason = unparseable`, không có giá trị dự đoán → dừng ở `L0`; ở `L1` vẫn chạy tiếp bước lập luận (AC-3: lần chạy không hỏng).
   - Có kết quả → `values = resolve_ticket_values(...)` → nhật ký `classify` với `predicted_*`, `applied = 0`.
   - `level = L0` → dừng (AC-9: phiếu trước = sau).
   - `level ≥ L1` → `execute_tool("set_classification", {category, confidence}, ctx)`. `ok=true` → cập nhật `applied = 1`, `value_before/after`, `actions` của đúng bản ghi `classify` vừa tạo (`frappe.db.set_value` trên bản ghi do runner tạo, trong `erp_ai/agent/`).
7. `trigger = comment_mention` và `level = L0` → nhật ký `skip`/`level_L0`, 0 lời gọi (A-3) → dừng.
8. **Bước lập luận** (`level ≥ L1`):
   - `instructor = latest_instructor(ticket)`; `ctx = ToolContext(...)`; `tools = get_tool_schemas(level, bool(instructor))` (gắn `cache_control` vào tool cuối); `system = build_reason_system(settings.prompt_digest)`; `messages = [user: build_initial_message(...)]`.
   - Với `turn` = 1..`max_turns_per_run`:
     - `call_model("reason", system=system, messages=messages, tools=tools, max_tokens=4096, deadline=deadline)`.
     - `GatewayError(kind = deadline)` → nhật ký `reason`, `stop_reason = time_budget` → dừng. Kind khác → nhật ký có `error`, `stop_reason = gateway_error` → dừng.
     - Với từng khối `tool_use`: `execute_tool(...)`; ngoại lệ → `{"type": "tool_result", "tool_use_id": id, "content": "Lỗi: <tên lớp lỗi>", "is_error": true}`.
     - Nhật ký `reason`: usage, `cost_usd`, `credential_label`, `keys_tried`, `latency_ms`, `stop_reason`, `tools_called`, `actions`, `value_before/after`, `instructor` (AC-15).
     - `stop_reason ≠ tool_use` → dừng. Nếu không, nối `assistant: content`, `user: tool_results` (`tool_use_id` khớp `id`, guide `:1141-1143`).
   - Hết `max_turns_per_run` mà lượt cuối vẫn là `tool_use` → sửa `stop_reason` của bản ghi lượt cuối thành `max_turns` (AC-15).
9. Mỗi bản ghi nhật ký được commit ngay khi `not frappe.flags.in_test`, để chi phí không mất nếu worker chết (D-20).

### 4.4 Người sửa phân loại (AC-11)
`validate` của người (session ≠ agent) đổi `ticket_type`/`agent_group`/`priority` trên phiếu đã có dự đoán → `ai_classified_by = Người` ngay trong lượt lưu đó → `on_update` ghi vào bản ghi `classify` gần nhất. Tool `set_classification` chạy dưới agent → không ghi nhận (ADR-004 #5).

### 4.5 Hằng ngày (AC-16, AC-18)
`recompute_monthly_spend` (mục 3.7) rồi `check_privilege_escalation` (mục 4.6). Runner đọc `spent_this_month_usd` ở bước (e), nên số liệu có thể trễ tối đa 1 ngày (ADR-004, đã chấp nhận).

### 4.6 Kiểm nâng quyền (AC-18)
Báo động một lần cho mỗi điều kiện đúng:
1. `set(frappe.get_roles(AGENT_USER)) − AUTOMATIC_ROLES ≠ {ROLE_AGENT, "Agent"}`, hoặc tài khoản agent không tồn tại.
2. Với từng DocType tồn tại trong (`Custom DocPerm`, `DocPerm`, `Role`, `Has Role`, `User Permission`, `Role Profile`): có bản ghi `modified_by = AGENT_USER` (liệt kê ≤ 5 tên).
3. `Server Script` có `owner = AGENT_USER, disabled = 0`; `Webhook` có `owner = AGENT_USER, enabled = 1`.
4. `ERP AI Credential` có `enabled = 1` mà `api_key` rỗng (đọc giá trị che trên bảng, không giải mã).

`erp_ai/alerts.py`:
- `send_alarm(subject, message)` = `frappe.log_error(TITLE_ALARM, message)` + `frappe.sendmail(recipients=<các dòng alert_recipients>, subject=f"[erp_ai] {subject}", message=message, delayed=True)`;
- `send_notice(subject, message)` = logger info + cùng kiểu email, không tạo Error Log;
- nội dung báo không bao giờ chứa văn bản khóa (NFR-5).

### 4.7 Mỗi giờ (AC-18) và "Kiểm tra khóa" (AC-19)
Mỗi giờ, `reprobe_exhausted_keys`: với từng khóa `Hết hạn mức` → `probe_credential`. Thành công → `Hoạt động` + tin. Lỗi → cập nhật theo cầu dao; còn `Hết hạn mức` thì không báo lại.
"Kiểm tra khóa" dùng cùng `probe_credential`, cho mọi dòng (hoặc đúng `label`).

### 4.8 Eval offline (AC-1..AC-3)
`export(path)` → JSONL (chỉ phiếu `can_send_ticket`). `run(path)` → phân loại qua cổng với **cùng** `build_classify_request` + `parse_classification` → `compute_metrics` → in báo cáo + kết luận. Eval không ghi `ERP AI Log`; chi phí của eval không vào ngân sách (D-22).

### 4.9 Quan sát được ở prod (STD-OPS-5)

| Đường mới | Tín hiệu |
|---|---|
| Handler xếp/bỏ job | `frappe.logger("erp_ai")` info: ticket, trigger, lý do |
| Mỗi lượt / mỗi quyết định bỏ qua của runner | 1 bản ghi `ERP AI Log` (chi phí, khóa, lý do dừng) |
| Lỗi job, sai tài khoản | Error Log tiêu đề `TITLE_RUN_FAILED` / `TITLE_WRONG_USER` |
| Chuyển trạng thái khóa | logger info: label, kind, trạng thái mới; email tin/động |
| Job ngày / giờ | logger info: tổng chi phí tính lại, số điều kiện báo động, số khóa dò |
| Độ chính xác | Report `ERP AI Accuracy` |

Không log nào chứa khóa, mật khẩu hay nội dung phiếu (STD-SEC-6).

## 5. Quyền

### 5.1 Ma trận
| Đối tượng | System Manager | ERP AI Agent | Agent (Helpdesk) | HD Customer | ERP AI Instructor |
|---|---|---|---|---|---|
| `ERP AI Setting` (+ bảng khóa) | đọc/ghi | — (runner đọc bằng `get_single`, cổng bằng `frappe.db`, không qua quyền; D-18) | — | — | — |
| `ERP AI Log` | đọc, báo cáo, export | đọc, tạo | — | — | — |
| Report `ERP AI Accuracy` | có | — | — | — | — |
| `check_keys` | có (`only_for`) | — | — | — | — |
| HD Ticket pl 0/7/8, HD Ticket Comment | theo Helpdesk | qua role `Agent` (ADR-006 #2) | theo Helpdesk | pl 0/7, **không pl 8** | — |
| Task (ERPNext) | theo ERPNext | Custom DocPerm đọc/tạo/ghi, `if_owner = 1` (D-14) | — | — | — |

Không ai có quyền xóa `ERP AI Log` (A-10). `ERP AI Instructor` không mang quyền DocType nào. Thẩm quyền của role này chỉ do `authority.is_instruction` đọc. App không cấp role này cho ai (A-15).

### 5.2 Chủ ghi (ADR-004)
- Trường người đặt: chỉ form.
- `spent_*`: chỉ `tasks.recompute_monthly_spend`.
- Trạng thái khóa: chỉ `erp_ai/gateway/**`.
- Nhật ký: tạo ở `run_log.write_entry`; cập nhật `applied`/`value_*` của bản ghi `classify` bởi runner; cập nhật `human_corrected_*` bởi handler.
- HD Ticket/Comment/Task: chỉ tool ghi ở `L1+`, dưới tài khoản agent, có phân quyền.
- `ignore_permissions=True` / `frappe.db.set_value` chỉ có ở `erp_ai/gateway/**`, `erp_ai/tasks.py::recompute_monthly_spend`, `erp_ai/install.py`, `erp_ai/handlers.py::ticket_on_update`, và cập nhật bản ghi `classify` trong `erp_ai/agent/runner.py` (bản ghi do runner tạo).
- Test giả lập "người lưu form" có `.save()` trên cấu hình trong `test_erp_ai_setting.py`. Đó là đường "Lưu form" mà ADR-004 cho phép, không phải mã sản phẩm.

### 5.3 Kiểm ở biên (STD-ERR-2, STD-SEC-4)
- Whitelist `check_keys`: kiểm quyền ở server (`only_for`) trước mọi việc.
- Form: validate ở controller (mục 3.6).
- Tool: kiểm schema tham số (registry), rồi kiểm quyền Frappe dưới tài khoản agent (tool). Phản hồi của model là dữ liệu không tin cậy: chỉ tên tool trong bộ được cấp mới chạy, và JSON phân loại sai → `None`.
- Handler: không tin nội dung comment. Từ khóa chỉ quyết định có chạy hay không; thẩm quyền theo role của tác giả (guide `:1037`).
- Truy vấn: chỉ ORM có tham số. `search_resolved_tickets` dùng filter `like` của ORM, không ghép SQL (STD-SEC-3).

### 5.4 Tool mã nguồn (AC-13, NFR-6) — ADR-005 #5
- `get_source_root()` = `realpath(dirname(dirname(frappe.get_app_path("frappe"))))` (test patch hàm này sang thư mục tạm).
- `resolve_safe_path(rel)`: `realpath(join(root, rel))`, phải nằm trong `root` (dùng `os.path.commonpath`) và khác `root`; `TEN_CAM` khớp đường dẫn tương đối → `None`; với file, đuôi phải ∈ `DUOI_CHO_PHEP`.
- Tìm: `os.walk(followlinks=False)`; bỏ thư mục ẩn và `node_modules`; bỏ file > 1 MB, file không đọc được UTF-8 (`errors="replace"`); so chuỗi cố định; dừng ở 40 kết quả hoặc sau 30 s (D-9).
- `git`:
  - lệnh = `["git", "--no-pager", "-C", repo, sub, *(["--no-ext-diff", "--no-textconv"] if sub in {"diff", "show", "log"} else []), *args]`, gọi `subprocess.run(list, capture_output=True, text=True, timeout=30)`, không `shell`, env `GIT_PAGER=cat`;
  - `repo` = thư mục con trực tiếp của `root` có `.git`;
  - arg bắt đầu bằng `--output`, `--no-index`, `--ext-diff`, `--textconv`, `-O`, `--contents`, `--exec`, `--upload-pack`, `-c` → từ chối;
  - không có `args` thì log mặc định `--oneline -n 15`.

## 6. Migration và rollback

Thay đổi dữ liệu có `cmd.migrate`: tạo 3 DocType + 1 Report mới, 6 custom field, 2 role, 1 user, cấu hình mặc định, 5 dòng template, Custom DocPerm cho Task. **Không chuyển dữ liệu cũ**: 0 dòng HD Ticket / HD Ticket Comment bị ghi (ADR-006 #4), nên không cần chia lô.

- **Lên** (`ensure_setup()` ở `after_install` và `after_migrate`, theo thứ tự, mỗi bước "tạo nếu thiếu"):
  1. Role `ERP AI Agent`, `ERP AI Instructor` (`desk_access = 1`).
  2. User `AGENT_USER`: `first_name "ERP AI"`, `user_type System User`, `send_welcome_email 0`, không đặt mật khẩu, không API key. Thêm role còn thiếu trong {`ERP AI Agent`, `Agent`}; không gỡ role nào. Không tạo HD Agent (A-7).
  3. `create_custom_fields({"HD Ticket": [...]}, update=True)` cho 6 trường ở mục 2.4 (D-11). Tên trường lấy từ hằng, cờ "không dùng AI" lấy `policy.OPT_OUT_FIELD`.
  4. Template `Default`: thêm dòng còn thiếu cho 5 trường AI (`visible_to = Agents`, `required = 0`, `editable_after_creation` = 1 chỉ với `ai_opt_out`), nối vào cuối. Không sửa, xóa hay đổi thứ tự dòng có sẵn. Template không tồn tại → logger warning, bỏ qua.
  5. Cấu hình: với mỗi trường của meta `ERP AI Setting` có `default` mà giá trị đơn hiện tại là `None` → `frappe.db.set_single_value` bằng default. Không ghi đè giá trị người đã đặt. Kết quả: tắt, `L0`.
  6. `frappe.db.exists("DocType", "Task")` → `setup_custom_perms("Task")` (sao chép quyền chuẩn) + insert Custom DocPerm {role `ERP AI Agent`, permlevel 0, read/write/create = 1, `if_owner = 1`} nếu chưa có → `frappe.clear_cache(doctype="Task")`.
  Thứ tự triển khai: mã và migrate đi cùng (`cmd.migrate`). Agent tắt sẵn, nên không cần cửa sổ chuyển giao.
- **Xuống** (dev `miyano`, người/devops chạy):
  1. Rollback hành vi: `enabled = 0` trên form → 0 job, 0 lời gọi (đã có test AC-4).
  2. Rollback schema: gỡ app khỏi site bằng lệnh gỡ app của bench. Profile chưa có slot `cmd.*` cho lệnh này; tech-lead/devops đề xuất slot `cmd.uninstall` trước khi qa chạy up/down/up, tôi không tự viết lệnh.
  3. Gỡ app xóa DocType/Report của module và dữ liệu `ERP AI Log`, `ERP AI Setting` (mất nhật ký và khóa đã nhập). Đây là mất dữ liệu khi đi xuống → cần người duyệt. Trên dev chưa có dữ liệu thật.
  4. Custom field `ai_*`, dòng template, user, role và Custom DocPerm Task **được giữ** (spec `:78` cấm xóa; trường ở permlevel 8, khách không thấy). Muốn xóa hẳn thì người xóa tay sau khi duyệt.
  Điều kiện kích hoạt rollback: migrate thoát mã ≠ 0; test AC-4 đỏ sau cài; Error Log `erp_ai:` xuất hiện khi agent tắt. Thành công khi: `cmd.migrate` thoát 0, số đếm đối soát khớp.
- **Đối soát** (qa chạy trên `miyano` trước/sau mỗi chiều, bằng `frappe.db.count` trong test hoặc console):

| Đếm | Trước → sau "lên" lần 1 | Sau "lên" lần 2 | Sau "xuống" |
|---|---|---|---|
| `HD Ticket`, `HD Ticket Comment` | n → n | n | n |
| Dòng con template `Default` | k → k + 5 | k + 5 | k + 5 |
| `Custom Field` có `dt = HD Ticket` và tên `ai_%` | 0 → 6 | 6 | 6 |
| `Role` ∈ {ERP AI Agent, ERP AI Instructor} | 0 → 2 | 2 | 2 |
| `User` = `AGENT_USER` | 0 → 1 | 1 | 1 |
| `Has Role` của `AGENT_USER` (trừ AUTOMATIC_ROLES) | 0 → 2 | 2 | 2 |
| `Custom DocPerm` parent Task, role ERP AI Agent | 0 → 1 | 1 | 1 |
| `tabERP AI Log` | (không có) → 0 | 0 | (không có) |

## 7. Touchpoints

`structure.tests = colocated`, `naming.test_file = test_{name}.py`. Tên module test cho `cmd.test_one` lấy từ đường dẫn file. Các file ADR-001 bắt buộc nằm ở đúng tầng.

| file | change | ghi chú |
|---|---|---|
| `pyproject.toml` | sửa | `dependencies = ["anthropic>=0.103.1,<1"]` (ADR-002; lý do STD-DEP-1: research Q1 — giữ bản env dùng chung, không làm vỡ `workflowcore`); `[tool.bench.frappe-dependencies] frappe = ">=15.126.1,<16.0.0"` |
| `erp_ai/hooks.py` | sửa | `required_apps = ["helpdesk"]`, `doc_events` (mục 3.1), `scheduler_events` (mục 3.7), `after_install`, `after_migrate`; không có `fixtures` (D-11) |
| `.github/workflows/ci.yml` | sửa | Chỉ phần "CI xanh" của DoD: `bench init` nhánh `version-15`, cài thêm `telephony`, `helpdesk` (tag `v15.1.0`), `erpnext` (`version-15`) trước `install-app erp_ai` (D-23). Không nâng version action (debt riêng) |
| `erp_ai/constants.py` | mới | Hằng dùng chung (mục 3, D-2) |
| `erp_ai/alerts.py` | mới | `send_alarm`, `send_notice` (mục 4.6, D-2) |
| `erp_ai/handlers.py` | mới | Cửa vào `doc_events` (mục 3.1) |
| `erp_ai/tasks.py` | mới | Cửa vào scheduler (mục 3.7, 4.5, 4.6) |
| `erp_ai/install.py` | mới | `ensure_setup` (mục 6) |
| `erp_ai/test_utils.py` | mới | Helper test dùng chung: `set_agent_settings`, `add_credential`, `FakeGateway` (hàng đợi `ModelResult`/`GatewayError`, đếm lời gọi), `make_model_result`, `fake_anthropic_client`, `make_log_entry`; dùng lại factory `helpdesk.test_utils` (STD-DESIGN-4) |
| `erp_ai/test_handlers.py` | mới | Test AC-4 (tắt), AC-5, AC-11, NFR-1, NFR-2 |
| `erp_ai/test_tasks.py` | mới | Test AC-16, AC-18 |
| `erp_ai/test_install.py` | mới | Test AC-4, ADR-006 |
| `erp_ai/test_architecture.py` | mới | Test quét mã nguồn cho các Ràng buộc ADR-001..005 |
| `erp_ai/agent/__init__.py` | mới | Gói lõi agent |
| `erp_ai/agent/queue.py` | mới | `enqueue_agent_run` (mục 3.2) |
| `erp_ai/agent/policy.py` | mới | Điều kiện gửi, mức hiệu lực, giới hạn ngày (mục 3.3) |
| `erp_ai/agent/authority.py` | mới | Thẩm quyền (mục 3.3) |
| `erp_ai/agent/prompts.py` | mới | Prompt chung runner/eval (mục 3.3) |
| `erp_ai/agent/classification.py` | mới | Bộ đọc JSON, ánh xạ (mục 3.3) |
| `erp_ai/agent/run_log.py` | mới | Tạo `ERP AI Log` (mục 3.3) |
| `erp_ai/agent/runner.py` | mới | `run_for_ticket` (mục 4.3) |
| `erp_ai/agent/test_queue.py` | mới | Test chặn trùng trong giao dịch, 5 tham số |
| `erp_ai/agent/test_policy.py` | mới | Test mục 3.3 policy |
| `erp_ai/agent/test_authority.py` | mới | Test AC-7 |
| `erp_ai/agent/test_classification.py` | mới | Test AC-3, AC-10 (phần thuần) |
| `erp_ai/agent/test_runner.py` | mới | Test AC-6, AC-9, AC-10, AC-15, ADR-003 (b)–(e) |
| `erp_ai/agent/tools/__init__.py` | mới | Gói tool; export `get_tool_schemas`, `execute_tool`, `ToolContext` |
| `erp_ai/agent/tools/registry.py` | mới | Schema, bộ tool theo mức × thẩm quyền, kiểm tham số (mục 3.5) |
| `erp_ai/agent/tools/read.py` | mới | `get_ticket`, `list_comments`, `search_resolved_tickets`, `get_record`, `DENIED_DOCTYPES` |
| `erp_ai/agent/tools/source.py` | mới | `search_source`, `read_source`, `git_source`, chặn đường dẫn (mục 5.4) |
| `erp_ai/agent/tools/write_ticket.py` | mới | `set_classification`, `set_resolution_hint`, `post_comment`, `create_task` |
| `erp_ai/agent/tools/test_registry.py` | mới | Test AC-8 (ma trận, schema) |
| `erp_ai/agent/tools/test_read.py` | mới | Test AC-14, NFR-4, NFR-5 (đọc) |
| `erp_ai/agent/tools/test_source.py` | mới | Test AC-13, NFR-6 |
| `erp_ai/agent/tools/test_write_ticket.py` | mới | Test AC-8 (thu quyền), AC-10 (tool) |
| `erp_ai/gateway/__init__.py` | mới | API công khai cổng (mục 3.4.1) |
| `erp_ai/gateway/client.py` | mới | Chỗ duy nhất `import anthropic` |
| `erp_ai/gateway/breaker.py` | mới | Bảng cầu dao thuần (mục 3.4.3) |
| `erp_ai/gateway/credentials.py` | mới | Chọn khóa, ghi trạng thái khóa, giải mã khóa |
| `erp_ai/gateway/cost.py` | mới | Công thức chi phí |
| `erp_ai/gateway/test_breaker.py` | mới | Test AC-17 (bảng) |
| `erp_ai/gateway/test_gateway.py` | mới | Test AC-14/NFR-5, AC-15 (chi phí), AC-17, NFR-7, NFR-8 |
| `erp_ai/eval/__init__.py` | mới | Gói eval |
| `erp_ai/eval/export_tickets.py` | mới | `export` (AC-2) |
| `erp_ai/eval/run_eval.py` | mới | `run`, `compute_metrics`, `format_report` (AC-1) |
| `erp_ai/eval/test_export_tickets.py` | mới | Test AC-2 |
| `erp_ai/eval/test_run_eval.py` | mới | Test AC-1, AC-3 (eval) |
| `erp_ai/erp_ai_agent/doctype/__init__.py` | mới | Gói DocType của module |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/__init__.py` | mới | |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json` | mới | Mục 2.1, quyền mục 5.1 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py` | mới | Controller + `check_keys` (mục 3.6) |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.js` | mới | Nút "Kiểm tra khóa" |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py` | mới | Test AC-19 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_credential/__init__.py` | mới | |
| `erp_ai/erp_ai_agent/doctype/erp_ai_credential/erp_ai_credential.json` | mới | Mục 2.2 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_credential/erp_ai_credential.py` | mới | Lớp controller rỗng (bảng con) |
| `erp_ai/erp_ai_agent/doctype/erp_ai_log/__init__.py` | mới | |
| `erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json` | mới | Mục 2.3, quyền mục 5.1 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.py` | mới | Lớp controller rỗng |
| `erp_ai/erp_ai_agent/report/__init__.py` | mới | Gói Report của module |
| `erp_ai/erp_ai_agent/report/erp_ai_accuracy/__init__.py` | mới | |
| `erp_ai/erp_ai_agent/report/erp_ai_accuracy/erp_ai_accuracy.json` | mới | Script Report, role System Manager |
| `erp_ai/erp_ai_agent/report/erp_ai_accuracy/erp_ai_accuracy.py` | mới | `execute` (mục 3.8) |
| `erp_ai/erp_ai_agent/report/erp_ai_accuracy/erp_ai_accuracy.js` | mới | Bộ lọc `from_date`, `to_date` |
| `erp_ai/erp_ai_agent/report/erp_ai_accuracy/test_erp_ai_accuracy.py` | mới | Test AC-12 |

Tổng: 65 touchpoint (3 sửa, 62 mới). Không có file nào ở `erp_ai/erp_ai/` (ADR-001).

**Kiểm đường dẫn mới với `structure.allowed_new_file_roots` = [`erp_ai`, `docs`, `.github`]:**
```
erp_ai/constants.py, erp_ai/alerts.py, erp_ai/handlers.py, erp_ai/tasks.py, erp_ai/install.py,
erp_ai/test_utils.py, erp_ai/test_handlers.py, erp_ai/test_tasks.py, erp_ai/test_install.py,
erp_ai/test_architecture.py  (10 file)                          -> erp_ai
erp_ai/agent/** (8 mã + 5 test)                                  -> erp_ai
erp_ai/agent/tools/** (5 mã + 4 test)                            -> erp_ai
erp_ai/gateway/** (5 mã + 2 test)                                -> erp_ai
erp_ai/eval/** (3 mã + 2 test)                                   -> erp_ai
erp_ai/erp_ai_agent/doctype/** (12 file)                         -> erp_ai
erp_ai/erp_ai_agent/report/** (6 file)                           -> erp_ai
Mới: 62, ngoài 3 gốc: 0. Sửa (đã tồn tại): pyproject.toml, erp_ai/hooks.py, .github/workflows/ci.yml
```
**Kiểm với `protected_paths` = [`.env`, `.env.*`, `**/*.pem`, `**/*.key`, `license.txt`]:** không đường dẫn nào ở trên có đuôi `.pem`/`.key`, tên `.env*` hay là `license.txt` → **0 in protected_paths**.

## 8. Test plan

Mọi test chạy bằng `cmd.test_one` (từng file) và `cmd.test` (toàn app), trên site `miyano`, không có mạng thật:
- runner/handler: patch `erp_ai.gateway.call_model` bằng `FakeGateway`;
- cổng: patch `erp_ai.gateway.client._build_client` bằng client giả;
- email: patch `frappe.sendmail` và đếm;
- xếp hàng: patch `erp_ai.agent.queue.frappe.enqueue` và đếm.

Không có test nào commit hay đọc Redis (STD-TEST-6, ADR-003). Lớp test kế thừa `FrappeTestCase`; dữ liệu có tên duy nhất (`frappe.generate_hash`).

| Tiêu chí | Test | Loại | Đường lỗi / biên |
|---|---|---|---|
| AC-1 | `erp_ai/eval/test_run_eval.py::test_metrics_twelve_ticket_sample` | unit | — (10/12 → 83,3% → `70–85%`; so từng ô ma trận, từng đầu mục, nhóm không-phải-tác-giả-nhiều-nhất) |
| AC-1 | `erp_ai/eval/test_run_eval.py::test_verdict_thresholds_at_85_and_70` | unit | biên: đúng 85,0% → `≥ 85%`; đúng 70,0% → `70–85%`; 69,9% → `< 70%` |
| AC-1 | `erp_ai/eval/test_run_eval.py::test_unparseable_and_unlabeled_rows` | unit | lỗi: dự đoán rỗng tính sai; `ticket_type` không có trong ánh xạ → `skipped_unlabeled` |
| AC-1 | `erp_ai/eval/test_run_eval.py::test_run_uses_given_predictions_without_gateway` | integration | biên: 0 lời gọi cổng khi mọi dòng đã có dự đoán |
| AC-2 | `erp_ai/eval/test_export_tickets.py::test_export_skips_excluded_team` | integration | 3 phiếu (1 nhóm loại trừ) → 2 dòng, mỗi dòng đúng 6 khóa |
| AC-2 | `erp_ai/eval/test_export_tickets.py::test_export_skips_opt_out_and_runs_when_disabled` | integration | biên: cờ `ai_opt_out`; agent tắt vẫn xuất |
| AC-2 | `erp_ai/eval/test_export_tickets.py::test_export_refuses_path_inside_repo` | unit | lỗi: `ValueError` |
| AC-3 | `erp_ai/agent/test_classification.py::test_eval_and_runner_share_classify_request` | unit | — (request của runner == của eval với cùng phiếu) |
| AC-3 | `erp_ai/agent/test_classification.py::test_parse_rejects_non_json_and_bad_values` | unit | lỗi: không phải JSON, `dau_muc = "G"`, `do_tin_cay` lạ → `None`; JSON trong rào → hợp lệ |
| AC-3 | `erp_ai/agent/test_runner.py::test_unparseable_classification_logged_run_continues` | integration | lỗi: stub trả chuỗi thường → nhật ký `UNPARSEABLE`, không có ngoại lệ |
| AC-4 | `erp_ai/test_install.py::test_setup_twice_is_idempotent` | integration | biên: chạy 2 lần, không trùng role/user/field/dòng template |
| AC-4 | `erp_ai/test_install.py::test_agent_user_has_exact_roles_without_system_manager` | integration | — |
| AC-4 | `erp_ai/test_install.py::test_ai_fields_permlevel_8_and_template_rows_agents_only` | integration | — |
| AC-4 | `erp_ai/test_install.py::test_default_settings_disabled_level_l0` | integration | biên: giá trị người đã đặt không bị ghi đè |
| AC-4 | `erp_ai/test_handlers.py::test_disabled_agent_new_ticket_no_job_no_model_call` | integration | — |
| AC-4 | `erp_ai/test_install.py::test_existing_template_row_preserved` | integration | biên: dòng tự thêm sẵn còn nguyên, đúng thứ tự (ADR-006) |
| AC-5 | `erp_ai/test_handlers.py::test_new_unclassified_ticket_enqueues_one_job` | integration | (a), kể cả khi Helpdesk tự điền mặc định |
| AC-5 | `erp_ai/test_handlers.py::test_prefilled_ticket_no_job` | integration | (b) |
| AC-5 | `erp_ai/test_handlers.py::test_agent_created_ticket_and_comment_no_job` | integration | (c) theo `owner` và `commented_by` |
| AC-5 | `erp_ai/test_handlers.py::test_comment_keyword_case_insensitive` | integration | (d) không từ khóa → 0; `@AI` → 1 |
| AC-5 | `erp_ai/test_handlers.py::test_opt_out_or_excluded_team_no_job_no_model_call` | integration | (e) tên nhóm khác hoa thường/khoảng trắng vẫn bị loại |
| AC-5 | `erp_ai/agent/test_queue.py::test_duplicate_trigger_same_transaction_one_job` | integration | (f); sau `after_rollback` xếp lại được |
| AC-6 | `erp_ai/agent/test_runner.py::test_wrong_session_user_stops_before_model` | integration | lỗi: `frappe.set_user` bị patch thành không làm gì → 0 lời gọi, 1 Error Log chứa tên tài khoản thật |
| AC-6 | `erp_ai/agent/test_runner.py::test_missing_agent_user_stops` | integration | biên: user agent bị tắt |
| AC-7 | `erp_ai/agent/test_authority.py::test_instructor_role_has_authority_on_any_ticket` | integration | — |
| AC-7 | `erp_ai/agent/test_authority.py::test_assigned_by_other_authority_only_on_that_ticket` | integration | P → chỉ thị, Q → dữ liệu |
| AC-7 | `erp_ai/agent/test_authority.py::test_self_assigned_is_data` | integration | biên: `assigned_by` = chính mình; `assigned_by` rỗng |
| AC-7 | `erp_ai/agent/test_authority.py::test_contact_and_plain_agent_are_data` | integration | HD Contact, HD Agent thường |
| AC-7 | `erp_ai/agent/test_authority.py::test_latest_instructor_prefers_latest_comment_then_owner` | integration | biên: không ai → `None`; Administrator không tính |
| AC-8 | `erp_ai/agent/tools/test_registry.py::test_tool_names_per_level_and_authority` | unit | ma trận 4 mức × có/không thẩm quyền |
| AC-8 | `erp_ai/agent/tools/test_registry.py::test_no_write_tool_accepts_doctype_or_field` | unit | xét schema lẫn chữ ký hàm |
| AC-8 | `erp_ai/agent/tools/test_registry.py::test_execute_rejects_tool_not_granted_and_bad_arguments` | unit | lỗi: tên ngoài bộ, sai enum, quá độ dài |
| AC-8 | `erp_ai/agent/tools/test_write_ticket.py::test_write_without_permission_returns_ok_false_unchanged` | integration | lỗi: thu quyền ghi pl 7 → `ok=false`, DB không đổi |
| AC-8 | `erp_ai/agent/tools/test_write_ticket.py::test_create_task_requires_instructor` | integration | lỗi: không có người ra lệnh → `ok=false` |
| AC-9 | `erp_ai/agent/test_runner.py::test_l0_logs_prediction_ticket_unchanged` | integration | số comment, 3 trường, trường AI trước = sau; `applied = 0` |
| AC-9 | `erp_ai/agent/test_runner.py::test_l0_comment_mention_skipped_no_call` | integration | biên: A-3 |
| AC-10 | `erp_ai/agent/test_runner.py::test_l1_applies_mapping_confidence_and_hint` | integration | `status` không đổi |
| AC-10 | `erp_ai/agent/test_runner.py::test_l1_human_classified_not_overwritten` | integration | lỗi: `ai_classified_by = Người` |
| AC-10 | `erp_ai/agent/tools/test_write_ticket.py::test_mapping_to_missing_value_skips_field` | integration | lỗi: HD Team không tồn tại → bỏ trường, lý do vào `skipped`/nhật ký |
| AC-10 | `erp_ai/agent/test_classification.py::test_urgent_prefix_forces_urgent` | unit | biên: `[GẬP]` ở giữa tiêu đề |
| AC-11 | `erp_ai/test_handlers.py::test_human_correction_updates_latest_log` | integration | biên: sửa 2 lần → giá trị cuối, `human_corrected_at` lần đầu |
| AC-11 | `erp_ai/test_handlers.py::test_agent_correction_not_recorded` | integration | — |
| AC-12 | `erp_ai/erp_ai_agent/report/erp_ai_accuracy/test_erp_ai_accuracy.py::test_accuracy_ten_log_sample` | integration | 10 bản ghi mẫu, đáp số tính tay; biên: sửa sau 7 ngày tính đúng; sửa về đúng giá trị dự đoán không tính sửa; mẫu = 0 → trống |
| AC-13 | `erp_ai/agent/tools/test_source.py::test_path_escape_refused` | integration | lỗi: `../`, đường tuyệt đối, symlink ra ngoài |
| AC-13 | `erp_ai/agent/tools/test_source.py::test_secret_names_and_extensions_refused` | unit | lỗi: từng mẫu `TEN_CAM` (subTest), đuôi `.sh` |
| AC-13 | `erp_ai/agent/tools/test_source.py::test_read_capped_at_400_lines` | unit | biên: `limit = 401` → bị từ chối; 400 → đủ 400 |
| AC-13 | `erp_ai/agent/tools/test_source.py::test_search_capped_at_40_hits` | unit | biên: 50 dòng khớp → 40 |
| AC-13 | `erp_ai/agent/tools/test_source.py::test_git_only_read_subcommands_and_safe_flags` | unit | lỗi: `push`, `--output=x`, `--no-index` |
| AC-13 | `erp_ai/agent/tools/test_source.py::test_git_missing_returns_not_installed` | unit | lỗi: `FileNotFoundError` → `ok=false` "chưa cài" |
| AC-14 | `erp_ai/agent/tools/test_read.py::test_denied_doctypes_refused` | integration | lỗi: từng DocType bị cấm (subTest) |
| AC-14 | `erp_ai/agent/tools/test_read.py::test_password_fields_never_returned` | integration | — |
| AC-14 | `erp_ai/gateway/test_gateway.py::test_api_key_never_leaks` | integration | đường thành công + 401 + ngoại lệ lạ; tìm chuỗi khóa trong `ERP AI Log`, HD Ticket Comment, Error Log, email đã gửi, `last_error` → 0 |
| AC-15 | `erp_ai/agent/test_runner.py::test_stops_after_max_turns` | integration | biên: stub luôn `tool_use` → đúng 8 bản ghi `reason`, bản cuối `max_turns` |
| AC-15 | `erp_ai/agent/test_runner.py::test_sixth_run_same_day_no_call` | integration | biên: lần 6 → 0 lời gọi, nhật ký `daily_limit`; hôm sau chạy lại được (`freeze_time`) |
| AC-15 | `erp_ai/agent/test_runner.py::test_turn_log_fields` | integration | đủ trường mục 2.3 |
| AC-15 | `erp_ai/gateway/test_gateway.py::test_cost_uses_four_token_prices` | unit | biên: usage `None` → 0 |
| AC-16 | `erp_ai/test_tasks.py::test_recompute_spend_from_log` | integration | tổng chung + theo khóa |
| AC-16 | `erp_ai/test_tasks.py::test_month_start_resets_to_zero` | integration | biên: ngày 1, chỉ có nhật ký tháng trước → 0 |
| AC-16 | `erp_ai/agent/test_policy.py::test_effective_level_over_budget_never_raises` | unit | L3/L2 → L1; L1 → L1; L0 → L0; đúng bằng ngân sách → không lui |
| AC-17 | `erp_ai/gateway/test_breaker.py::test_breaker_table` | unit | từng hàng 1–9 (subTest); 529 trần 600 s; 429 thiếu `retry-after` → 61 s |
| AC-17 | `erp_ai/gateway/test_gateway.py::test_selection_filters_and_order` | integration | khóa tắt / Lỗi khóa / Hết hạn mức / đang nghỉ / vượt ngân sách / OpenAI bị loại; sắp theo `try_order` rồi `error_count` |
| AC-17 | `erp_ai/gateway/test_gateway.py::test_reason_requires_model_reason` | integration | biên: khóa chỉ có `model_classify` |
| AC-17 | `erp_ai/gateway/test_gateway.py::test_bad_request_does_not_switch_key` | integration | lỗi: 400 → 1 khóa đã thử, trạng thái không đổi |
| AC-17 | `erp_ai/gateway/test_gateway.py::test_no_usable_key_alarm` | integration | lỗi: hết khóa → 1 email báo động; 401 → `Lỗi khóa` + báo động; 402 → `Hết hạn mức` + tin |
| AC-18 | `erp_ai/test_tasks.py::test_reprobe_only_exhausted_keys` | integration | `Lỗi khóa` không bị dò; dò được → `Hoạt động` + 1 email tin |
| AC-18 | `erp_ai/test_tasks.py::test_alarm_on_role_drift` | integration | thêm System Manager → 1 email |
| AC-18 | `erp_ai/test_tasks.py::test_alarm_on_permission_records_modified_by_agent` | integration | — |
| AC-18 | `erp_ai/test_tasks.py::test_alarm_on_enabled_server_script_or_webhook_by_agent` | integration | Server Script `disabled = 0`; Webhook `enabled = 1` |
| AC-18 | `erp_ai/test_tasks.py::test_alarm_on_enabled_key_without_secret` | integration | biên: không có điều kiện nào → 0 email |
| AC-19 | `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py::test_hd_agent_cannot_read_or_write_settings` | integration | lỗi: `PermissionError` |
| AC-19 | `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py::test_self_managed_fields_restored_on_human_save` | integration | biên: người sửa `paused_until`, `error_count`, `spent_*` → giá trị DB giữ nguyên |
| AC-19 | `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py::test_human_can_move_key_error_to_active_only` | integration | lỗi: `Hoạt động` → `Lỗi khóa` bằng tay bị bỏ |
| AC-19 | `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py::test_check_keys_system_manager_only_and_per_key_result` | integration | lỗi: HD Agent → `PermissionError`; `label` lạ → `ValidationError` |
| AC-19 | `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py::test_validation_rejects_bad_mapping_limits_and_missing_prices` | integration | lỗi: JSON sai, `max_turns_per_run = 0`, bật mà giá = 0 |
| AC-19 | Sau G4: người bấm "Kiểm tra khóa" trên `/app/erp-ai-setting` site dev, chụp kết quả (spec AC-19) | thủ công | — |
| AC-20 | `erp_ai/test_install.py::test_ai_fields_permlevel_8_and_template_rows_agents_only` (phần tự động: permlevel 8, `visible_to = Agents`, HD Customer không có quyền pl 8) | integration | — |
| AC-20 | Sau G4: người mở 1 phiếu bằng HD Agent và 1 bằng HD Contact trên site dev, chụp màn hình (`ui: false`) | thủ công | — |
| NFR-1 | `erp_ai/test_handlers.py::test_save_ticket_and_comment_make_no_model_call` | integration | stub cổng đếm = 0 trong luồng lưu |
| NFR-1 | `erp_ai/agent/test_queue.py::test_enqueue_parameters` | unit | `enqueue_after_commit=True`, `deduplicate=True`, `job_id` |
| NFR-1 | `erp_ai/test_architecture.py::test_handlers_do_not_import_gateway_or_runner` | unit | — |
| NFR-2 | `erp_ai/agent/test_queue.py::test_enqueue_parameters` | unit | `queue="long"`, `timeout=600` |
| NFR-2 | `erp_ai/gateway/test_gateway.py::test_deadline_limits_attempt_timeout` | unit | biên: còn 3 s → `GatewayError(deadline)`, 0 lời gọi client |
| NFR-3 | AC-15, AC-16 ở trên + `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py::test_validation_rejects_bad_mapping_limits_and_missing_prices` | integration | biên giới hạn số |
| NFR-4 | `erp_ai/test_handlers.py::test_opt_out_or_excluded_team_no_job_no_model_call` | integration | — |
| NFR-4 | `erp_ai/agent/test_runner.py::test_not_sendable_at_run_time_no_model_call` | integration | biên: đổi nhóm sau khi xếp hàng |
| NFR-4 | `erp_ai/agent/tools/test_read.py::test_excluded_tickets_never_returned` | integration | `get_ticket`, `get_record`, `search_resolved_tickets` |
| NFR-5 | `erp_ai/gateway/test_gateway.py::test_api_key_never_leaks` | integration | xem AC-14 |
| NFR-5 | `erp_ai/test_architecture.py::test_secret_handling_rules` | unit | `get_decrypted_password`/`import anthropic` chỉ ở `erp_ai/gateway/**`; không có `with_context=True`; mọi `frappe.log_error(` có 2 đối số |
| NFR-6 | `erp_ai/agent/tools/test_source.py::test_read_capped_at_400_lines`, `::test_search_capped_at_40_hits`, `::test_git_runs_with_timeout_list_args_no_shell` | unit | biên 400/40/30 s |
| NFR-7 | `erp_ai/gateway/test_gateway.py::test_max_keys_per_call` | integration | biên: 5 khóa đều 529, `max_keys_per_call = 3` → đúng 3 lần thử; client có `max_retries=0` và `timeout` |
| NFR-8 | `erp_ai/gateway/test_gateway.py::test_low_tokens_pause_until_reset_and_missing_headers_ignored` | integration | biên: 19 999 → nghỉ; 20 000 → không; header vắng → không đổi |
| NFR-9 | `erp_ai/eval/test_run_eval.py::test_metrics_twelve_ticket_sample` + `erp_ai/erp_ai_agent/report/erp_ai_accuracy/test_erp_ai_accuracy.py::test_accuracy_ten_log_sample` (bảo đảm phép đo đúng); con số ≥ 85% đo sau G4 trên dữ liệu thật (spec NFR-9) | integration | — |
| ADR-001..005 | `erp_ai/test_architecture.py::test_layer_imports`, `::test_single_enqueue_call_site`, `::test_no_save_on_settings_in_product_code`, `::test_tools_never_bypass_permissions`, `::test_subprocess_only_in_source_tool`, `::test_level_and_send_policy_fields_only_in_policy` | unit | — |
| ADR-003 (b) | `erp_ai/agent/test_runner.py::test_disabled_at_run_time_no_model_call` | integration | — |
| ADR-006 | `erp_ai/test_install.py::test_setup_never_writes_existing_tickets` | integration | đếm phiếu/comment trước = sau |

**AC-n trong spec:** AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18, AC-19, AC-20 (20).
**AC-n trong test plan:** AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18, AC-19, AC-20 (20) — khớp. NFR-1..NFR-9: 9/9 có dòng.

## Assumptions decided by the team

Định dạng: chọn | vì | phương án khác | sai thì sửa thế nào.

- **D-1 Tên định danh.** Chọn: fieldname/hàm tiếng Anh snake_case, nhãn tiếng Việt, bảng đối chiếu ở mục 2.6 | Vì: STD-NAME-6/7 (một quy ước, không trộn); guide trộn Việt–Anh | Khác: giữ nguyên tên guide | Sai thì: đổi trước khi có dữ liệu (dev); sau khi có dữ liệu thì cần patch đổi tên trường.
- **D-2 Hai module lá `erp_ai/constants.py`, `erp_ai/alerts.py`.** Chọn: hằng và gửi cảnh báo nằm ở module lá, chỉ import `frappe` (và `constants`) | Vì: cổng, runner và tasks đều cần báo động; architecture.md để designer chọn "chỗ đặt hằng số (một chỗ)". Đặt trong `gateway/` thì handler/tasks không được import (ADR-001); đặt trong `agent/` thì cổng không được import | Khác: mỗi tầng tự gửi email | Sai thì: architect ghi rõ "module lá" vào ADR-001 hoặc chuyển vào tầng được chỉ định; chỉ phải đổi đường import.
- **D-3 Chặn trùng trong giao dịch.** Chọn: tập `job_id` trong `frappe.flags`, xóa ở `after_commit`/`after_rollback` | Vì: research Q2 phương án B; phạm vi của tập = đúng lỗ hổng (một giao dịch); test không cần Redis | Khác: khóa trên phiếu (ADR-003 đã loại) | Sai thì: thêm khóa cache có hạn ở đầu job.
- **D-4 "Đã điền đủ" xét giá trị người nhập.** Chọn: chụp ở `before_insert`, trước khi Helpdesk tự điền `ticket_type`/`priority` | Vì: `hd_ticket.py:268-275`, `:366-371` điền mặc định, nếu xét sau thì AC-5(a) gần như không bao giờ xảy ra | Khác: so với giá trị mặc định HD Settings | Sai thì: đổi một hàm trong `handlers.py` + test AC-5(b).
- **D-5 Thời gian.** Chọn: `request_timeout_s` = 60; hạn chót của job = 600 − 60 s; timeout mỗi lần thử = min(timeout, thời gian còn lại); còn < 5 s → dừng `time_budget` | Vì: guide `:216` ước 5–40 s/lượt; ADR-003 #5 | Khác: 120 s (research) | Sai thì: sửa trên form, không cần code.
- **D-6 Bảng cầu dao.** Chọn: 402 / 429 `enforced_spend_limit_reached` / 400 "You have reached your specified…" → `Hết hạn mức`; 500/timeout không thử lại trên cùng khóa | Vì: research `:65`; ADR-002 #4 thắng guide `:796` ("sau 1 lần thử lại") | Khác: 402 → `Lỗi khóa` | Sai thì: sửa một hàng trong `breaker.py` + subTest.
- **D-7 Khóa lập luận phải có `model_reason` riêng.** Chọn: bỏ `model_reason_default` | Vì: AC-17 "chỉ dùng khóa Anthropic có model lập luận"; guide `:719` "để rỗng nếu key này chỉ dùng phân loại" | Khác: dùng model mặc định khi khóa để trống | Sai thì: thêm 1 trường + 1 nhánh trong `credentials.py`.
- **D-8 Giá trị ghi.** Chọn: loại/nhóm/ưu tiên lấy từ `category_mapping`; `[GẬP]` → Urgent; `nhom`/`uu_tien` của model không dùng để ghi. Ánh xạ mặc định theo guide 16.1–16.2: `ticket_type` = tên đầu mục (`Sự cố & lỗi hệ thống`, `Quản trị & cấu hình hệ thống`, `Phát triển tính năng & tự động hóa`, `Chuẩn hóa dữ liệu & quy trình trên ERP`, `Công việc nghiệp vụ ngoài IT`, `Câu hỏi, phiếu nhiễu`); `agent_group` = `IT` cho A, B, C, F, rỗng cho D, E; `priority` = High (A), Medium (B, C, D), rỗng (E), Low (F) | Vì: AC-10 "ghi theo bảng ánh xạ"; giá trị không tồn tại thì tự bỏ qua (AC-10), Hiếu sửa trên form (A-8, A-15) | Khác: ưu tiên theo `uu_tien` của model | Sai thì: một dòng trong `resolve_ticket_values`.
- **D-9 Tìm mã nguồn.** Chọn: Python thuần, chuỗi cố định, không regex | Vì: research Q3 phương án A; regex do model đưa vào có rủi ro ReDoS | Khác: `rg` qua subprocess | Sai thì: thay thân `search_source`, giữ `resolve_safe_path`.
- **D-10 Tool `get_record`.** Chọn: một tool đọc bản ghi có allowlist (6 DocType Helpdesk) + denylist | Vì: AC-14 cần một tool đọc theo DocType để kiểm từ chối; guide `:1482` "Allowlist + deny-list"; allowlist chặn `Communication`/`File` của phiếu nhóm loại trừ (NFR-4) | Khác: chỉ tool chuyên biệt | Sai thì: thêm DocType vào `ALLOWED_READ_DOCTYPES`.
- **D-11 Custom field tạo bằng mã cài đặt.** Chọn: `create_custom_fields(update=True)` trong `ensure_setup`, không có `fixtures` | Vì: ADR-006 #5 cho chọn; `update=True` giữ permlevel 8 sau mỗi migrate, giống tác dụng của fixture; một thủ tục duy nhất test được | Khác: fixture lọc `HD Ticket-ai_%` | Sai thì: xuất fixture, bỏ bước 3 của mục 6.
- **D-12 Bỏ `ai_so_luot_hom_nay`, `ai_cho_xac_nhan`.** Vì: ADR-004 #2 (không có bộ đếm thứ hai); xác nhận một lượt thuộc `L2`/`L3` (A-1); STD-DESIGN-5 | Sai thì: thêm field chỉ để hiển thị ở feature sau.
- **D-13 "Kiểm tra khóa" chạy đồng bộ, 10 s mỗi khóa.** Vì: NFR-1 chỉ áp cho luồng lưu phiếu (arch-impact `:58`); ~1–10 khóa | Khác: chạy qua job | Sai thì: bọc `check_keys` bằng `frappe.enqueue` + realtime.
- **D-14 Task.** Chọn: role agent có Custom DocPerm đọc/tạo/ghi `if_owner = 1` trên Task; "liên kết phiếu" = dòng đầu `description` có tên và đường dẫn phiếu, cộng `value_after` trong nhật ký. Giả định ERPNext đã cài trên `miyano` (có trong `sites/apps.txt`; chưa chạy được `list-apps` ở vai designer) | Vì: Task không có trường link HD Ticket; chỉ `Projects User` được tạo | Khác: custom field `hd_ticket` trên Task | Sai thì: task đầu tiên của dev kiểm `frappe.db.exists("DocType", "Task")`; không có thì báo tech-lead. Theo thứ tự cắt của spec, tool Task là mục (3).
- **D-15 Bảo toàn trường tự quản khi người lưu form.** Chọn: `validate` lấy lại giá trị DB, trừ `Lỗi khóa` → `Hoạt động` | Vì: form gửi lại toàn bộ dòng con với giá trị cũ, sẽ ghi đè trạng thái cổng vừa ghi (ADR-004) | Khác: tách trạng thái sang DocType riêng (ADR-004 đã loại) | Sai thì: sửa một hàm controller.
- **D-16 Người ra lệnh.** Chọn: `Administrator`, `Guest`, tài khoản agent không bao giờ có thẩm quyền; ToDo có `assigned_by` rỗng → dữ liệu | Vì: `frappe.get_roles("Administrator")` trả mọi role, phiếu tạo qua email/console sẽ thành "chỉ thị"; khi không rõ thì chọn đóng | Khác: theo đúng mã guide | Sai thì: bỏ một điều kiện trong `is_instruction` + test.
- **D-17 Báo cáo độ chính xác.** Chọn: chỉ tính là "sửa" khi giá trị người đặt khác dự đoán; dự đoán < 7 ngày chưa sửa = `pending`, không vào mẫu số | Vì: A-12 định nghĩa theo 7 ngày; người đặt đúng giá trị dự đoán là đồng ý chứ không phải sửa | Khác: mọi lần đổi đều là sửa | Sai thì: đổi một điều kiện trong `erp_ai_accuracy.py`.
- **D-18 Role agent không có quyền trên `ERP AI Setting`.** Vì: runner đọc bằng `frappe.get_single`, cổng đọc bằng `frappe.db`, không đi qua quyền; bớt quyền thì bớt đường lộ khóa (guide `:738`) | Khác: Read như guide `:943` | Sai thì: thêm 1 dòng permission vào JSON.
- **D-19 "Đã dùng tháng" tính lại từ nhật ký.** Chọn: một hàm hằng ngày tính tổng từ đầu tháng (ngày 1 → 0); không có job `monthly`; khóa `Hết hạn mức` về `Hoạt động` nhờ dò mỗi giờ | Vì: ADR-004 #2 (giá trị suy ra); ADR-004 cấm ghi trạng thái khóa ngoài cổng; guide `:894` | Khác: cộng dồn + job reset tháng | Sai thì: thêm `scheduler_events.monthly`.
- **D-20 Lỗi job và commit.** Chọn: `run_for_ticket` bắt mọi ngoại lệ, ghi Error Log có message tường minh, không ném lại; commit sau mỗi bản ghi nhật ký khi `not frappe.flags.in_test` | Vì: framework ghi traceback `with_context=True` khi job ném lỗi (`frappe/utils/error.py:54`, ADR-002); nhật ký là nguồn sự thật của chi phí (ADR-004) | Khác: để job ném lỗi | Sai thì: bỏ khối bắt lỗi khi Frappe không còn in biến cục bộ.
- **D-21 Không chống spam cảnh báo.** Chọn: tin/động của khóa chỉ gửi khi trạng thái chuyển; báo động hằng ngày mỗi ngày một lần; "hết khóa" mỗi lần chạy thất bại (đã bị chặn bởi 5 lần/phiếu/ngày) | Vì: STD-DESIGN-5; spec không có yêu cầu | Khác: khóa cache 1 giờ cho mỗi tiêu đề | Sai thì: thêm 5 dòng trong `alerts.py`.
- **D-22 Chi phí eval không vào ngân sách.** Vì: ADR-004 chỉ cho runner tạo nhật ký; eval chạy một lần trước khi bật, do người chạy | Sai thì: eval ghi tổng chi phí ra màn hình (đã có usage trong `ModelResult`).
- **D-23 CI.** Chọn: workflow cài Frappe `version-15` + `telephony` + helpdesk `v15.1.0` + erpnext `version-15` | Vì: `required_apps = ["helpdesk"]` và test Task cần ERPNext; nếu không có thì CI đỏ ở bước `install-app` (DoD "CI xanh") | Khác: bỏ ERPNext và bỏ tool Task | Sai thì: devops chỉnh workflow; không ảnh hưởng mã.
- **D-24 Gắn nhãn "chỉ thị"/"dữ liệu" cho comment đưa vào model.** Vì: thẩm quyền đã tính bằng hàm (ADR-005); nhãn giúp model biết lời nào của người có thẩm quyền mà không cần giải thích luật trong prompt (guide `:155`) | Khác: không gắn | Sai thì: bỏ trường `role` trong `label_comments`.
- **D-25 Không cho bật khi chưa có đơn giá.** Vì: đơn giá = 0 thì chi phí = 0 và ngân sách không bao giờ chặn (STD-ERR-6) | Sai thì: bỏ một điều kiện trong `validate`.

Rủi ro còn mở (không chặn thiết kế):
- tên header hạn mức với API `2023-06-01` (`UNVERIFIED`, guide `:1518`);
- `excluded_teams` gõ sai tên nhóm sẽ không loại được phiếu (form không kiểm vì ADR-003 chỉ cho hàm điều kiện gửi đọc trường này; người phải đối chiếu tên HD Team);
- comment của agent có mention sẽ gửi email cho người được mention (guide `:1218`).
