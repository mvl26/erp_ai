Feature: FEAT-007
Stage: design
Author-agent: designer
Date: 2026-11-14
Approved-by:
<!-- G2b không áp dụng (team.py: chỉ cổng G5). -->

# Design addendum 1 — U3 Nhật ký hành động và cổng công tắc (5) (FEAT-007)

**Phạm vi.** Chỉ đơn vị U3 của `arch-impact.md:178`: AC-10 `[changed]`, AC-11 `[changed]` (`spec-addendum-1.md` mục 2.1, thắng `spec.md`), AC-4 phần "dòng nhật ký khi công tắc đổi" và "điều kiện hằng ngày" (`spec.md:61`; phần thông báo trên form là của U0, `design.md:322`). Không thiết kế U2, U4b, U5b, U6b, U7, U8; phần các đơn vị đó gọi tới U3 nằm ở mục 3.10 "Contract for later units".

**Luật thi hành (trích, không chép):** ADR-033 QĐ 1, QĐ 5 và Ràng buộc "một dạng mục hành động, dựng bởi một hàm dùng chung", "dòng không phải lần chạy có `cost_usd = 0`"; ADR-032 QĐ 4 và Ràng buộc 3 ("đọc (5) qua `policy.py` trước khi kiểm chữ ký"; "`propose_change.py` không dựng liên kết có chữ ký khi (5) = 0"); ADR-030 QĐ 7; ADR-024 QĐ 2, QĐ 3.5 và Ràng buộc "`write_entry` giữ `insert` và `commit` trong cùng lời gọi"; ADR-023 QĐ 1 (chữ ký, POST, CSRF giữ nguyên), QĐ 5 (M5: hai đường hợp lệ, không thêm đường). Tên của U0 theo `design.md:229-245` và `design-w0-fixes.md` F-5, F-6, mục 3; tên của U1 theo `design-addendum-1-U1.md` mục 3.9.

---

## 1. Bối cảnh

### 1.1 Explore summary (đọc trực tiếp, 2026-11-14; `develop` @ `1918db2`, `team/FEAT-004` @ `f8b3b81`)

| Chỗ | Trên `develop` | Trên nhánh FEAT-004 | U3 đổi |
|---|---|---|---|
| `erp_ai/agent/run_log.py:7-10` | `ENTRY_TYPES` 4 giá trị, `TRIGGERS` 2, `CHANGE_TRIGGERS` 1 | như `develop` | thêm `bot_action`, `BOT_ACTION_TRIGGERS` |
| `run_log.py:25-57` `write_entry` | kiểm `entry_type`/`trigger`; `insert(ignore_permissions=is_change)`; `commit` ngoài test | T66 (`05989a7`): `insert` bọc trong `allow_agent_write()` | kiểm hình dạng mục, điền `site_environment`, dòng `bot_action` |
| `erp_ai/agent/runner.py:695-700` `_action` | dict `{tool, doctype, name, ok}` viết tay | T64 dự kiến thêm `value_before`, `value_after`, `instructor` cho tool `api_*` (chưa có mã) | gọi `run_log.action_entry` |
| `runner.py:358-366` `_route_action` | dict thứ hai viết tay, khóa thêm `reason`, `rule`; 13 lời gọi | như `develop` | thân gọi `run_log.action_entry` |
| `runner.py:684-688` | trước/sau ở mức dòng theo **tên tool**: gọi cùng tool hai lần thì lần sau đè lần trước | như `develop` | giữ (người đọc FEAT-005); thêm trước/sau **theo mục** |
| `erp_ai/change_decision.py:25-39` | `decide` GET, chuyển hướng | T54 (`team/FEAT-004-task-54` @ `50b3432`): POST, `PermissionError(BAD_LINK)`, trả `{ok, status}` | cổng (5) ở dòng đầu |
| `erp_ai/agent/change_link.py:27-29` | `/api/method/...` | T53 (`1dcc2f4`): `/app/erp-ai-change-proposal/<tên>?<chữ ký>` | không sửa |
| `erp_ai/agent/tools/propose_change.py:84-101` `_comment` | luôn 3 liên kết | T53/T67 (`:102-122`): câu đầu trỏ form, trả tên Comment, luôn 2 liên kết quyết định | liên kết quyết định chỉ khi (5) bật |
| `erp_ai_change_proposal.js` | không tự gọi | T54: `decide_from_link` xóa tham số khỏi địa chỉ rồi POST một lần khi "Chờ duyệt"; 3 nút có `frappe.confirm` | không sửa (mục 3.5) |
| `erp_ai/tasks.py:83-108` `check_privilege_escalation` | 4 điều kiện, một giao dịch, rollback khi lỗi | FEAT-005 T8–T13 viết lại (cửa sổ, `filelock`, mốc) | thêm điều kiện thứ 5 |
| `erp_ai_log.json` | `entry_type` 4 option, `trigger` 3 option, `actions` Small Text, không có `site_environment` | như `develop` | option mới (F-5) |
| `erp_ai/tests/test_architecture.py:1592`, `:1838-1858`, `:2126` | `ENTRY_TYPES_EXPECTED` 4 giá trị, ghim cả hằng và option JSON | như `develop` | ghim 5 giá trị (ADR-033 QĐ 5) |
| `policy.runs_today` (`policy.py:80-87`) | đếm `run_id` của dòng `classify`/`reason` | — | không đổi: dòng `bot_action` tự đứng ngoài |

### 1.2 Code FEAT-004 / FEAT-005 mà U3 dựa vào

| Thứ U3 dựa vào | Task | Có trên `develop` hôm nay? |
|---|---|---|
| `decide` `methods=["POST"]`, `BAD_LINK`, `DECIDERS`, trả `{"ok": True, "status": …}`; test `test_get_is_refused_and_changes_nothing`, `test_post_approve_sets_approved_and_one_job_survives_request_end`, `test_post_reject_zero_jobs`, `test_replay_keeps_state_and_enqueues_nothing`, `test_refused_accounts` | FEAT-004 T54 | **Không.** Chỉ ở `team/FEAT-004-task-54` @ `50b3432`; review vòng 68 request-changes (1 major STD-TEST-6), sửa vòng 69; chưa vào `team/FEAT-004` |
| JS `decide_from_link` (xóa tham số trước, POST một lần, `reload_doc`), `add_action_button` có `frappe.confirm` | FEAT-004 T54 | **Không** (cùng nhánh trên) |
| `change_link.decision_path` trỏ form, `FORM_ROUTE`, `signature_ok` | FEAT-004 T53 | **Không.** Có ở `team/FEAT-004` (`1dcc2f4`), chưa tick (chờ `cmd.test`) |
| `propose_change._comment` bản T53/T67 (trả tên Comment, câu đầu trỏ form), `_insert` bọc `allow_agent_write` | FEAT-004 T53, T67 | **Không.** Có ở `team/FEAT-004` (`1dcc2f4`, `f8b3b81`) |
| `write_entry` bọc `allow_agent_write()`; controller ERP AI Log `refuse_agent_write` | FEAT-004 T66 | **Không.** Có ở `team/FEAT-004` (`05989a7`) |
| `refuse_agent_write(self)` đầu `validate` của ERP AI Setting; `allow_agent_write` | FEAT-004 T65 | **Không.** Có ở `team/FEAT-004` (`0325147`) |
| Mục hành động của tool `api_*` có `value_before`, `value_after`, `instructor` | FEAT-004 T64 | **Không**, ở đâu cũng chưa: `team/FEAT-004-task-64` @ `2108dd2` chỉ có merge T62/T63; `tasks.md:665` `[ ]` |
| Tóm tắt `value_before`/`value_after` trong kết quả tool `api_*` | FEAT-004 T62 | **Không** (nhánh task) |
| `site_api.SECRET_FIELDS` | FEAT-004 (trước T53) | **Có** (`site_api.py:38`) |
| `SECRET_RESULT_KEYS`, `_scrub` | FEAT-004 T61 | **Không** (nhánh task `5130c88`) |
| Luật kiến trúc ADR-023 trong `test_architecture.py` | FEAT-004 T68 | **Không** (`[ ]`) |
| `GENERIC_WRITE_TOOLS`, `_record_snapshot` khóa `"<tool>#<n>"` | FEAT-005 T3 | **Không** (`[ ]`, chưa nhánh) |
| `REASON_TURN_SAVEPOINT`, `_undo_turn` (lỗi `write_entry` hoàn tác lượt) | FEAT-005 T5, T6 | **Không** |
| `check_privilege_escalation` một giao dịch trong `filelock`, mốc `privilege_alert_checked_until` | FEAT-005 T7–T13 | **Không** |
| Luật kiến trúc ADR-024 | FEAT-005 T14 | **Không** |
| `alerts.send_alarm`, `tasks._raise_alarm`, `_list_names`, `MAX_LISTED_NAMES`, `TITLE_RUN_FAILED`, `LOG_DOCTYPE`, `SETTING_DOCTYPE`, `TRIGGER_CHANGE_ACTION` | FEAT-001/FEAT-004 cũ | **Có** |

**Điều kiện bắt đầu U3** (arch-impact): T53, T54, T64, T66, T67 và FEAT-005 T3, T5, T13, T14 đã ở `develop`; U1 đã merge vào `team/FEAT-007`. Cắt trước thì dev U3 phải dựng lại hình dạng mục của T64 hoặc thân `decide` của T54 → `DESIGN_CONFLICT`, dừng.

### 1.3 Cần từ U0, U1, U6a (không tự đặt)

| Cần | Có trong design của đơn vị chủ? |
|---|---|
| Cột `site_environment` (Data) trên ERP AI Log | Có (`design.md:237`, U0) |
| `actions` Long Text | Có (F-6, U0) |
| `one_click_approval_enabled`, `site_environment` trên ERP AI Setting | Có (`design.md:119-120`, U0) |
| `on_update` → `notify_permission_switches()` đọc trường `Check` của `section_permissions` từ meta | Có (`design.md:322`: "Dòng nhật ký người bật: U3 thêm vào cùng hàm này") |
| `PermissionSwitches`, `permission_switches(settings)`, `PERMISSION_SWITCH_FIELDS`, `ToolContext.one_click_approval` | Có (`design-addendum-1-U1.md` 3.9) |
| **`policy.site_environment(settings=None) -> str`** | **Thiếu.** `design.md:120` ghi người đọc là `policy` (U3, U7) và U1 thêm tên vào `POLICY_FIELDS`, nhưng mục 3.1 của U1 không có hàm đọc. Hành vi cần: `settings` None → `frappe.get_single(SETTING_DOCTYPE)`; giá trị ∈ {`test`, `production`} → giá trị đó; khác (rỗng, lạ, trước migrate) → `"production"`. Chủ: U1. Nếu U1 đã merge khi U3 bắt đầu, sửa `policy.py` nằm ngoài ô file của U3 → team-leader quyết (giao lại U1 hay cho U3 thêm đúng hàm này) |
| **`redact.is_secret_key(name: str) -> bool`** | **Thiếu.** `redact.redact_secrets(text)` của U6a (`design.md:486`) che theo văn bản; U3 cần che theo **tên khóa** trong dict trước/sau. Hành vi cần: `name.casefold()` chứa một từ của cùng danh sách từ bí mật mà `redact_secrets` dùng (`api_key`, `api_secret`, `token`, `secret`, `password`, `passwd`, `pwd`, `mật khẩu`) — phủ cả 4 tên của `site_api.SECRET_FIELDS`. Chủ: U6a (`erp_ai/agent/redact.py`), một danh sách, không chép |

---

## 2. Mô hình dữ liệu

U3 **không thêm trường, không thêm DocType**. Chỉ thêm option và quy ước giá trị trên cột U0 đã thêm.

**Option ERP AI Log (F-5, cùng commit với hằng của `run_log.py`):**

| Trường | Option sau U3 (thứ tự) |
|---|---|
| `entry_type` | `classify`, `reason`, `skip`, `change`, `bot_action` |
| `trigger` | `ticket_insert`, `comment_mention`, `change_action`, `setting_save`, `scheduled_job` (U6b nối `requester_reply`, `kb_draft`) |

**Một dạng mục hành động** (phần tử của list JSON trong `actions`; ADR-033 QĐ 5, FEAT-004 AC-34/AC-35):

| Khóa | Kiểu | Luôn có | Ý nghĩa |
|---|---|---|---|
| `tool` | str | có | tên tool, hoặc tên việc không qua model (`permission_switch`, việc của U5b/U6b) |
| `doctype` | str \| null | có | loại bản ghi đích |
| `name` | str \| null | có | tên bản ghi đích |
| `ok` | bool | có | thành công hay không |
| `value_before` | object \| null | có | `{trường: giá trị}` trước khi ghi; null khi tạo mới hoặc bị từ chối |
| `value_after` | object \| null | có | `{trường: giá trị}` sau khi ghi; null khi bị từ chối/sập/xóa |
| `instructor` | str \| null | có | người ra lệnh (user ID) |
| `reason` | str | chỉ khi `ok` = false | lý do bị từ chối hoặc lớp lỗi khi sập |
| `rule` | str | chỉ đường định tuyến, khi có | quy tắc định tuyến (có sẵn) |

Giá trị bí mật trong `value_before`/`value_after` thay bằng `"[đã ẩn]"` (mục 3.1).

**Mức dòng, theo loại dòng:**

| `entry_type` | `trigger` | `ticket` | `run_id` | `instructor` | `actions` | `cost_usd` | `site_environment` |
|---|---|---|---|---|---|---|---|
| `classify`, `reason`, `skip` | trigger của runner | có | mã lần chạy | người ra lệnh của lần chạy | mục của lượt | chi phí thật | tự điền |
| `change` | `change_action` | như nay | như nay | — | U7 thêm mục cho đề xuất bản ghi đã áp dụng | như nay | tự điền |
| `bot_action` | `setting_save` | rỗng | `uuid4().hex` mới | người lưu form | một mục mỗi công tắc đổi | **0** | giá trị sau khi lưu |
| `bot_action` | `scheduled_job` | phiếu của việc (hoặc rỗng) | `uuid4().hex` mỗi lần việc chạy | rỗng | mục của việc | **0** | tự điền |

**Mẫu truy cập.** Người đọc theo ngày/loại (báo cáo 08:00 U5a, KPI 3) đọc `actions` theo `creation`; cảnh báo ADR-024 chỉ đọc dòng `reason` nên dòng `bot_action` không vào cửa sổ của nó; `month_spend_usd` (U1) cộng mọi dòng, dòng `bot_action` cộng 0; `runs_today` lọc `classify|reason` nên không đếm dòng `bot_action`. Không cần chỉ số mới. Dòng cũ không có `site_environment` và mục cũ thiếu khóa `value_before`/`instructor`: người đọc dùng `.get`.

---

## 3. API / hợp đồng

Mọi hàm là Python nội bộ, trừ `decide` (whitelisted, đã có). Không có endpoint mới. Hợp đồng công khai duy nhất bị chạm là `decide`: chỉ **thêm** một lý do từ chối, cùng lớp lỗi (`PermissionError`), không đổi tham số hay dạng trả về của T54.

### 3.1 `run_log.py`

```python
ENTRY_TYPE_CHANGE = "change"
ENTRY_TYPE_BOT_ACTION = "bot_action"
ENTRY_TYPES = ("classify", "reason", "skip", "change", "bot_action")
TRIGGERS = ("ticket_insert", "comment_mention")            # U3 không đổi; U6b nối
CHANGE_TRIGGERS = (TRIGGER_CHANGE_ACTION,)
TRIGGER_SETTING_SAVE = "setting_save"
TRIGGER_SCHEDULED_JOB = "scheduled_job"
BOT_ACTION_TRIGGERS = (TRIGGER_SETTING_SAVE, TRIGGER_SCHEDULED_JOB)
TOOL_PERMISSION_SWITCH = "permission_switch"
ACTION_KEYS = ("tool", "doctype", "name", "ok", "value_before", "value_after", "instructor")
SECRET_MASK = "[đã ẩn]"                                     # cùng chữ với mặt nạ của T61
NO_REASON = "tool không nêu lý do"

def action_entry(tool: str, doctype: str | None, name: str | None, ok: bool, *,
                 reason: str | None = None, value_before: dict | None = None,
                 value_after: dict | None = None, instructor: str | None = None,
                 rule: str | None = None) -> dict
def write_entry(**fields) -> str                            # chữ ký giữ nguyên
def write_bot_action(*, trigger: str, actions: list[dict], ticket: str | None = None,
                     instructor: str | None = None, run_id: str | None = None,
                     site_environment: str | None = None) -> str
```

| Hàm | Hành vi chính xác | Lỗi |
|---|---|---|
| `action_entry` (**hàm dựng mục duy nhất**, ADR-033 Ràng buộc) | Trả dict có đủ `ACTION_KEYS` đúng thứ tự, rồi `reason` khi `ok` là `False` (rỗng → `NO_REASON`), `rule` khi khác rỗng. `doctype` cắt `ACTION_DOCTYPE_MAX` (80, chuyển từ runner sang đây). `value_before`/`value_after` đi qua `_mask(values, doctype)`: đệ quy dict/list; khóa có `redact.is_secret_key(khóa)` hoặc là trường `Password` theo `frappe.get_meta(doctype)` (khi `doctype` là DocType có thật) → `SECRET_MASK`; mọi chuỗi lá → `redact.redact_secrets`. Không sửa dict đầu vào | `tool` không phải chuỗi khác rỗng, `ok` không phải `bool`, `value_*` không phải dict/None → `ValueError` |
| `write_entry` | Như nay, thêm: (a) `entry_type == "bot_action"` → `trigger` ∈ `BOT_ACTION_TRIGGERS`, `actions` là list khác rỗng, `cost_usd` thiếu hoặc 0 (ghi 0); (b) mọi loại dòng: nếu có `actions` thì mỗi phần tử là dict chứa đủ `ACTION_KEYS`; (c) `site_environment` không truyền → `policy.site_environment()` (cần từ U1); (d) `insert(ignore_permissions=is_change or is_bot_action)`, vẫn trong `allow_agent_write()` (T66); `commit` ngoài test **trong cùng lời gọi** (ADR-024 Ràng buộc) | `ValueError` cho mọi vi phạm (a), (b), không có dòng nào; `PermissionError` như nay |
| `write_bot_action` | `run_id = run_id or uuid.uuid4().hex`; gọi `write_entry(entry_type="bot_action", trigger=…, ticket=…, instructor=…, run_id=…, actions=…, cost_usd=0, site_environment=…)` (khóa `site_environment` chỉ truyền khi khác None). Trả tên dòng. **Commit** (ngoài test): người gọi ghi tác động và khóa chu kỳ của mình **trước**, gọi hàm này **cuối cùng**, để một commit phủ cả ba (ADR-033 QĐ 6) | như `write_entry` |

`policy.py` không được import `run_log` (tránh vòng); test kiến trúc ở mục 8.

### 3.2 `runner.py` — mọi mục qua `action_entry`

- `_action(name, context, outcome, ok, arguments, *, crash: str | None = None) -> dict`: giữ cách suy `doctype`, `record` hiện có (`runner.py:695-700`), rồi `return run_log.action_entry(name, doctype, record, ok, reason=crash or (outcome or {}).get("reason"), value_before=…, value_after=…, instructor=context.instructor)`. Nhánh sập (`runner.py:670-673`) truyền `crash=f"lỗi: {type(exc).__name__}"` (chỉ tên lớp, như D-20).
- `_entry_values(name, outcome, arguments) -> tuple[dict | None, dict | None]` (mới, một chỗ), áp khi `ok`:

  | Tool | `value_before` | `value_after` |
  |---|---|---|
  | kết quả có `value_before`/`value_after` (tool `api_*`, T62/T64) | nguyên giá trị đó | nguyên giá trị đó |
  | kết quả có `before`/`after` là dict (`set_classification`) | `before` | `after` |
  | kết quả có `before`/`after` không phải dict (`set_resolution_hint`) | `{write_ticket.HINT_FIELD: before}` | `{write_ticket.HINT_FIELD: after}` |
  | tạo mới không trả trước/sau (`post_comment`, `create_task`) | `None` | `arguments` của lời gọi (dict; khác dict → `None`) |
  | `propose_*` | `None` | `{"change_status": outcome["status"]}` |
  | `ok` = false hoặc sập | `None` | `None` |

  Tool mới của đơn vị sau phải rơi vào một hàng có sẵn hoặc thêm hàng ở đây (mục 3.10).
- `_route_action(tool, doctype, name, ok, reason=None, rule=None, *, value_before=None, value_after=None, instructor=None)`: thân chỉ gọi `run_log.action_entry`; lời gọi ghi trường phiếu ở bước định tuyến truyền `before`/`after` mà `route_ticket` đã trả (`route_ticket.py:71-72`) và `context.instructor`. Không còn dict mục hành động viết tay nào trong `runner.py`.
- Trước/sau mức dòng theo tên tool (`runner.py:684-688`) và khóa `"<tool>#<n>"` của FEAT-005 T3 **giữ nguyên**; điểm lưu và hoàn tác lượt của FEAT-005 T5 không đổi.

### 3.3 `change_decision.py` — cổng (5) ở server

```python
ONE_CLICK_OFF = "Duyệt một lần bấm đang tắt. Mở đề xuất và dùng nút Duyệt hoặc Từ chối trên form (có bước xác nhận)."

@frappe.whitelist(methods=["POST"])
def decide(name=None, action=None, _signature=None) -> dict:
    if not policy.permission_switches(frappe.get_single(SETTING_DOCTYPE)).one_click_approval:
        frappe.logger(LOGGER_NAME).info("one-click link refused: switch off proposal=%s user=%s", name, frappe.session.user)
        frappe.throw(_(ONE_CLICK_OFF), frappe.PermissionError)
    # phần còn lại đúng thân T54: kiểm action + chữ ký → BAD_LINK; DECIDERS[action](name)
```

- Đọc (5) **mỗi request**, qua `policy` (ADR-032 QĐ 4), **trước** `signature_ok`. Không lưu (5) vào liên kết hay comment.
- Danh sách lỗi đầy đủ của `decide` (mọi lỗi là `frappe.PermissionError`, HTTP 403, trừ dòng cuối):

  | Điều kiện | Thông báo | Ghi gì |
  |---|---|---|
  | (5) tắt | `ONE_CLICK_OFF` | không gì (một dòng logger) |
  | `action` lạ, chữ ký thiếu/sai | `BAD_LINK` (T54) | không gì |
  | người không đủ điều kiện (`_decider`) | thông báo của controller (T54) | không gì |
  | đề xuất không còn "Chờ duyệt" | `ValidationError` của controller (T54, 417) | không gì |

### 3.4 `propose_change._comment` — không ký khi (5) tắt

- Câu đầu (trỏ form) và ghi chú giữ nguyên chữ của T53/T67.
- `ctx.one_click_approval` (U1, runner điền từ `policy.permission_switches` lúc bắt đầu lần chạy) đúng → thêm đúng dòng liên kết của T53 (Duyệt · Từ chối · Xem nội dung thay đổi), từng byte như nay.
- Sai → **không gọi** `change_link.decision_path`; dòng cuối chỉ có `<a href="/app/erp-ai-change-proposal/<tên>">{OPEN_PROPOSAL_LABEL}</a>`, `OPEN_PROPOSAL_LABEL = "Mở đề xuất để Duyệt hoặc Từ chối"`.
- Chữ ký hàm và giá trị trả (tên Comment) không đổi.

### 3.5 `erp_ai_change_proposal.js` — không sửa

Có trong ô file của U3 nhưng **không cần sửa**: liên kết cũ mở form → `decide_from_link` (T54) xóa tham số khỏi địa chỉ **trước** khi gọi, POST một lần → server trả 403 `ONE_CLICK_OFF` → `frappe.call` hiện thông báo của server; trạng thái đứng yên; tải lại trang không gửi lại. Nút Duyệt/Từ chối có `frappe.confirm` (FEAT-004 AC-22) đã là đường khi (5) tắt. JS không biết (5) mà không thêm dữ liệu `__onload` ở controller (ngoài file của U3), và kiểm ở JS không phải ranh giới (ADR-032 "Phương án đã xét").

### 3.6 `erp_ai_setting.py` — dòng nhật ký khi công tắc đổi

```python
def record_permission_switch_changes(self) -> str | None
```

- Gọi ở **cuối** `on_update`, sau `notify_permission_switches()` của U0.
- Tập trường: đúng tập `notify_permission_switches` dùng (trường `Check` của `section_permissions` đọc từ meta, D-7). Nếu U0 viết tập đó ngay trong thân hàm, U3 tách thành `_permission_switch_fields()` trong cùng file và cả hai hàm gọi (STD-DESIGN-4).
- `before = self.get_doc_before_save()`; `None` → mọi công tắc coi là 0.
- Mỗi trường có `bool(trước) != bool(sau)` → một `run_log.action_entry(TOOL_PERMISSION_SWITCH, SETTING_DOCTYPE, SETTING_DOCTYPE, True, value_before={trường: int(trước)}, value_after={trường: int(sau)}, instructor=frappe.session.user)`.
- Không trường nào đổi → trả `None`, không ghi gì. Có → `run_log.write_bot_action(trigger=TRIGGER_SETTING_SAVE, actions=<các mục>, instructor=frappe.session.user, site_environment=self.site_environment)`; trả tên dòng. "Người bật" = `instructor`, "thời điểm" = `creation` của dòng.
- Phiên agent không tới được đây (T65 từ chối ở `validate`), nên dòng `setting_save` luôn mang người thật.

### 3.7 `tasks.py` — điều kiện hằng ngày

```python
PERMISSION_SWITCHES_ON_SUBJECT = "Quyền mở rộng đang bật"
def _enabled_permission_switches() -> list[str]
```

- `settings = frappe.get_single(SETTING_DOCTYPE)`; `switches = policy.permission_switches(settings)`; ghép `zip(policy.PERMISSION_SWITCH_FIELDS, dataclasses.astuple(switches))` (cùng thứ tự (1)..(5), U1); trả **nhãn** (`meta.get_label(trường)`) của từng công tắc đang bật. Không viết tên trường nào trong `tasks.py` (luật `POLICY_FIELDS`).
- Thêm `(PERMISSION_SWITCHES_ON_SUBJECT, _enabled_permission_switches)` làm phần tử **thứ năm** của `checks` trong `check_privilege_escalation` (bản FEAT-005 T13): cùng giao dịch, cùng `filelock`, không đọc, không ghi mốc ADR-024 (ADR-030 QĐ 7). Tắt hết → `[]` → không có mục cảnh báo. Không ghi dòng ERP AI Log.

### 3.8 `erp_ai_log.json` và mô tả trường

Đổi đúng `options` của `entry_type` và `trigger` (mục 2) và `description` của hai trường, cùng commit với `run_log.py` (F-5). Mô tả `entry_type` thêm: "bot_action: việc của bot không qua model, hoặc người đổi công tắc quyền; chi phí 0." Mô tả `trigger` thêm: "setting_save: người lưu cấu hình đổi công tắc quyền; scheduled_job: việc theo lịch hoặc theo sự kiện không qua model." Cụm từ bắt buộc mới trong `DOCTYPE_CONFIG["ERP AI Log"]["phrases"]`: `"bot_action"`, `"setting_save"`, `"scheduled_job"`. `field_count` không đổi.

### 3.9 Lỗi — một dạng

Không có kiểu lỗi mới. Hàm nội bộ ném `ValueError` cho tham số sai (như `write_entry` hôm nay). `decide` chỉ ném `frappe.PermissionError` với chữ cố định (mục 3.3). Việc theo lịch giữ đường `TITLE_RUN_FAILED` (D-20). Tool vẫn trả `{"ok": False, "reason": …}`.

### 3.10 Contract for later units

| Tên | Chữ ký / giá trị | Module | Đơn vị gọi |
|---|---|---|---|
| `action_entry` | `(tool: str, doctype: str \| None, name: str \| None, ok: bool, *, reason: str \| None = None, value_before: dict \| None = None, value_after: dict \| None = None, instructor: str \| None = None, rule: str \| None = None) -> dict` — hàm dựng mục duy nhất, tự che bí mật | `erp_ai/agent/run_log.py` | U4b (mục của dòng `classify`: 7 trường AC-24, comment hỏi), U6b (tool trả lời, CSKT, job vòng đời, đóng F), U7 (bộ thực thi danh mục; mục của dòng `change` khi áp dụng đề xuất bản ghi), U8 (đường ghi Task/BA note không qua tool), U5b (nhắc hạn, kiểm mốc) |
| `write_bot_action` | `(*, trigger: str, actions: list[dict], ticket: str \| None = None, instructor: str \| None = None, run_id: str \| None = None, site_environment: str \| None = None) -> str`; `cost_usd = 0`; commit (gọi cuối giao dịch) | `run_log.py` | U5b (nhắc hạn, kiểm mốc, AC-61 "1 dòng log" lần đầu vượt ngân sách), U6b (job vòng đời, đóng F im lặng), U7 (ghi danh mục ngoài lượt runner, nếu có) |
| `write_entry` | `(**fields) -> str`; mọi phần tử `actions` phải do `action_entry` dựng; `site_environment` tự điền | `run_log.py` | U4b, U6b, U7 (dòng `change` có `actions`) |
| `ENTRY_TYPE_BOT_ACTION` | `"bot_action"` | `run_log.py` | U5b, U6b; người đọc: U5a `bot_actions` |
| `ENTRY_TYPES` | `("classify", "reason", "skip", "change", "bot_action")`; ghim ở `test_architecture.py` | `run_log.py` | — (đổi nữa cần ADR) |
| `TRIGGER_SCHEDULED_JOB` | `"scheduled_job"` | `run_log.py` | U5b, U6b |
| `TRIGGER_SETTING_SAVE` | `"setting_save"` | `run_log.py` | chỉ U3 |
| `BOT_ACTION_TRIGGERS` | `(TRIGGER_SETTING_SAVE, TRIGGER_SCHEDULED_JOB)`; đơn vị cần trigger mới cho dòng `bot_action` nối vào đây **cùng commit** với option JSON (luật F-5) | `run_log.py` | U6b nếu cần trigger cho job theo sự kiện |
| `TRIGGERS` | `("ticket_insert", "comment_mention")`; U6b nối `requester_reply`, `kb_draft` cùng `queue.VALID_TRIGGERS` | `run_log.py` | U6b |
| `ACTION_KEYS` | tuple 7 khóa luôn có (mục 2) | `run_log.py` | người đọc: U5a, U5b, U7 (thống kê) |
| `TOOL_PERMISSION_SWITCH` | `"permission_switch"` | `run_log.py` | người đọc: U5a báo cáo 08:00 (loại "đổi quyền") |
| `SECRET_MASK`, `NO_REASON` | `"[đã ẩn]"`, `"tool không nêu lý do"` | `run_log.py` | test của mọi đơn vị |
| `runner._entry_values` | `(name, outcome, arguments) -> tuple[dict \| None, dict \| None]`; bảng mục 3.2 | `erp_ai/agent/runner.py` | U4b, U6b, U7, U8: tool ghi mới thêm vào `WRITE_TOOL_TARGETS` và rơi vào một hàng (hoặc thêm hàng) |
| `ONE_CLICK_OFF`, `decide` | mục 3.3 | `erp_ai/change_decision.py` | U7: method quyết định của ngăn (ADR-032 QĐ 2) gọi thẳng controller, **không** đi qua `decide` (nếu không sẽ bị cổng (5) chặn) |
| `OPEN_PROPOSAL_LABEL`; luật "(5) tắt → không gọi `decision_path`" | mục 3.4 | `erp_ai/agent/tools/propose_change.py` | U7 (comment đề xuất bản ghi dùng chung `_comment` hoặc giữ cùng luật) |
| `PERMISSION_SWITCHES_ON_SUBJECT` | `"Quyền mở rộng đang bật"` | `erp_ai/tasks.py` | — |

---

## 4. Luồng

**Lần ghi của tool trong lượt suy luận (AC-10).** Model gọi tool → `execute_tool` → kết quả → `_action` → `_entry_values` → `action_entry` (che bí mật) → `actions` của lượt → `write_entry` (kiểm hình dạng, điền `site_environment`, `insert`, `commit`). Thay đổi của tool và dòng `reason` vào **cùng** một commit; lỗi ở `write_entry` (hình dạng sai) → FEAT-005 T5 hoàn tác lượt (ADR-024 QĐ 2). Gọi cùng tool hai lần → hai mục, mỗi mục có trước/sau riêng. Bị từ chối → mục `ok=false` có `reason`. Sập → mục `ok=false`, `reason = "lỗi: <Lớp>"`.

**Bước định tuyến.** `_route` → mỗi đơn vị ghi → `_route_action` → `action_entry` → dòng `classify` (như nay, cùng savepoint `ROUTE_SAVEPOINT`).

**Người đổi công tắc (AC-4, AC-10(a)).** Lưu form → `validate` (T65 chặn agent; khôi phục trường tự quản; kiểm của U0) → ghi → `on_update`: `notify_permission_switches` (U0, chỉ khi 0 → 1) → `record_permission_switch_changes` → `write_bot_action` → commit (gồm cả bản lưu Setting). Lỗi ghi dòng → ngoại lệ lan ra → request rollback → cấu hình **không** đổi (không có công tắc đổi mà thiếu dòng).

**Hằng ngày.** `check_privilege_escalation` (FEAT-005 T13) → 4 điều kiện → `_enabled_permission_switches` → `_raise_alarm` (Error Log + Email Queue) → commit một lần cuối job.

**Liên kết khi (5) tắt (AC-11 (i)).** Comment mới: chỉ liên kết mở form. Liên kết cũ: form mở → JS xóa tham số → POST `decide` → đọc (5) = 0 → 403 `ONE_CLICK_OFF` → trạng thái đứng yên, 0 job, 0 dòng. Người dùng bấm nút trên form → hộp xác nhận → controller.

**Khi (5) bật (AC-11 (ii)).** Đúng FEAT-004 AC-25 (T53, T54).

| Tình huống lỗi | Kết quả |
|---|---|
| Mục có hình dạng sai tới `write_entry` | `ValueError`, 0 dòng; trong lượt → hoàn tác lượt, Error Log `TITLE_RUN_FAILED` |
| Dòng `bot_action` có `cost_usd` ≠ 0, `actions` rỗng, trigger lạ | `ValueError`, 0 dòng |
| Lỗi ghi dòng `setting_save` | lưu Setting thất bại, thông báo lỗi chung của Frappe |
| `site_environment` rỗng/lạ trên Setting | dòng ghi `"production"` |
| Đọc Setting lỗi trong `decide` | 500, không ghi gì |
| Lỗi giữa job hằng ngày | rollback cả mục cảnh báo (đường FEAT-005 T13) |

Không có lời gọi ra ngoài mới (DB local; email qua Email Queue có sẵn).

---

## 5. Quyền

- `decide`: POST, CSRF của phiên, không `allow_guest` (T54); cổng (5) ở **server**, trước chữ ký (ADR-032 QĐ 4, STD-SEC-4); sau đó `_decider` như nay. JS không phải ranh giới.
- Dòng `bot_action` chỉ tạo qua `write_entry` (đường hợp lệ 1 của M5, ADR-023 QĐ 5) — không thêm đường ghi ERP AI Log nào. `ignore_permissions=True` cho dòng `bot_action` vì người lưu Setting (System Manager) không có quyền tạo ERP AI Log (append-only, `test_no_role_can_write_or_delete`); chỉ trong `write_entry`, như dòng `change`.
- Dòng `scheduled_job` của U5b/U6b ghi dưới tài khoản agent qua `authority.enter_agent_session()` (ADR-033 QĐ 1, U1); `allow_agent_write` của T66 phủ.
- Không giá trị bí mật nào vào `actions` (AC-10(d), STD-SEC-6): `action_entry` là chỗ che duy nhất cho mục.
- Đọc nhật ký: không đổi (System Manager; `ERP AI Instructor` `read`, `report` do U0).

---

## 6. Migration và rollback, quan sát

- **Lên:** `cmd.migrate` áp option mới của hai trường Select (không DDL: Select là varchar). Không ghi lại dữ liệu cũ; không backfill `site_environment` (dòng cũ để trống).
- **Xuống:** revert commit U3 rồi `cmd.migrate`. Dòng `bot_action`/`setting_save`/`scheduled_job` đã ghi **giữ nguyên** (append-only; xóa nhật ký là quyết định của người). Sau revert không mã nào đọc chúng: `runs_today` lọc `classify|reason`, cảnh báo ADR-024 đọc `reason`, `month_spend_usd` cộng 0.
- **Đối chiếu:** trước và sau mỗi chiều chạy `SELECT entry_type, trigger, COUNT(*) FROM tabERP AI Log GROUP BY 1, 2` — mọi số đếm bằng nhau (không dòng nào mất); `SUM(cost_usd)` của tháng bằng nhau.
- **Quan sát (STD-OPS-5):** đổi công tắc → dòng `bot_action`/`setting_save`; công tắc đang bật → mục cảnh báo `PERMISSION_SWITCHES_ON_SUBJECT` mỗi ngày; liên kết bị cổng (5) từ chối → một dòng `frappe.logger("erp_ai")` có tên đề xuất và user ID (không bí mật); mỗi lần ghi của bot → một mục với `instructor`, `run_id`, `site_environment`.

---

## 7. Touchpoints

Nguồn (ô "Module, file chạm" của U3, `arch-impact.md:178`, cộng `erp_ai_log.json` theo phán quyết F-5):

| File | Sửa |
|---|---|
| `erp_ai/agent/run_log.py` | 3.1 |
| `erp_ai/agent/runner.py` | 3.2 |
| `erp_ai/change_decision.py` | 3.3 |
| `erp_ai/agent/tools/propose_change.py` | 3.4 (chỉ `_comment`, hằng `OPEN_PROPOSAL_LABEL`) |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py` | 3.6 |
| `erp_ai/tasks.py` | 3.7 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json` | 3.8 (F-5: "đi cùng commit đổi hằng (U3)") |
| `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.js` | có trong ô, **không sửa** (3.5) |

Ngoài ô của U3 và **không sửa**: `change_link.py` (T53 đủ), `policy.py` (cần `site_environment` từ U1, mục 1.3), `redact.py` (cần `is_secret_key` từ U6a, mục 1.3).

Test (đặt cạnh mã, `structure.tests = colocated`):

| File | Trạng thái |
|---|---|
| `erp_ai/agent/test_run_log.py` | thêm |
| `erp_ai/agent/test_agent_runner.py` | thêm; sửa test FEAT-004 so sánh dict mục `{tool, doctype, name, ok}` sang `ACTION_KEYS` (NFR-8: AC-10 đổi hình dạng mục) |
| `erp_ai/test_change_decision.py` | thêm; test T54 đặt (5) = 1 (ADR-032 Ràng buộc, NFR-8) |
| `erp_ai/agent/tools/test_propose_change.py` | thêm; test 3 liên kết của T53 đặt `ctx.one_click_approval=True` (lý do như trên) |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py` | thêm |
| `erp_ai/tests/test_tasks.py` | thêm |
| `erp_ai/erp_ai_agent/doctype/erp_ai_log/test_erp_ai_log.py` | thêm |
| `erp_ai/tests/test_architecture.py` | sửa ghim `ENTRY_TYPES_EXPECTED`; thêm luật |
| `test_doctype_descriptions.py` (cùng file U0 sửa ở F-5) | thêm 3 cụm từ |

**So khớp đường dẫn mới với `allowed_new_file_roots` và `protected_paths`:**

```
new: (không có file mới)
allowed_new_file_roots = ["erp_ai", "docs", ".github"] -> không áp dụng
protected_paths = [".env", ".env.*", "**/*.pem", "**/*.key", "license.txt"]
modified (7 nguồn + 9 test, đều dưới erp_ai/): không file nào khớp protected_paths
artifact này: docs/team/features/FEAT-007/design-addendum-1-U3.md -> prefix "docs/" khớp
```

---

## 8. Test plan

Chạy từng file bằng `cmd.test_one`, cả app bằng `cmd.test`. Stub Cổng model, không mạng, đồng hồ truyền vào (STD-TEST-6). Mỗi file tự dựng và trả cài đặt (đặt (5) và công tắc trong test, không đọc giá trị đang lưu trên site).

| AC | Test (`file::name`) | Ca biên / lỗi |
|---|---|---|
| AC-10 (hình dạng) | `erp_ai/agent/test_run_log.py::TestActionEntry::test_shape_has_all_keys_in_order` | `ok=True` không có khóa `reason` |
| AC-10(b) | `…test_run_log.py::TestActionEntry::test_refused_entry_keeps_reason` | `ok=False`, `reason=""` → `NO_REASON` |
| AC-10(d) | `…test_run_log.py::TestActionEntry::test_masks_secret_keys_password_fields_and_secret_text` | khóa `api_key`, `new_password` lồng trong list; trường `Password` theo meta `User`; chuỗi `sk-ant-…` trong giá trị thường; dict đầu vào không bị sửa |
| AC-10 | `…test_run_log.py::TestActionEntry::test_rejects_blank_tool_non_bool_ok_non_dict_values` | `tool=""`, `ok=1`, `value_after="x"` |
| AC-10(b) | `…test_run_log.py::TestWriteEntry::test_every_row_gets_site_environment` | Setting `production`, `test`, rỗng → `production` |
| AC-10 | `…test_run_log.py::TestWriteEntry::test_hand_built_entry_rejected` | dict thiếu `value_before` → `ValueError`, 0 dòng |
| AC-10 | `…test_run_log.py::TestBotAction::test_bot_action_row_cost_zero_not_counted` | `runs_today` và `month_spend_usd` không đổi sau 1 dòng |
| AC-10 | `…test_run_log.py::TestBotAction::test_bot_action_needs_known_trigger_actions_and_zero_cost` | `ticket_insert`, `[]`, `cost_usd=0.5` → `ValueError` |
| AC-10 | `…test_run_log.py::TestBotAction::test_bot_action_under_agent_and_human_sessions` | dưới agent ghi được; người không quyền tạo Log ghi được; `insert` trực tiếp dưới agent vẫn bị T66 chặn |
| AC-10(a) | `erp_ai/agent/test_agent_runner.py::TestActionLog::test_each_write_tool_has_one_entry_with_values_and_instructor` | subTest: `set_classification`, `set_resolution_hint`, `post_comment`, `create_task`, `propose_file_change`, `api_update_record` — đúng 1 mục, trước/sau theo bảng 3.2, `instructor` |
| AC-10(c) | `…test_agent_runner.py::TestActionLog::test_same_tool_twice_two_entries` | hai `set_classification` → 2 mục, trước/sau riêng |
| AC-10(b) | `…test_agent_runner.py::TestActionLog::test_refused_call_entry_has_reason` | |
| AC-10(b) | `…test_agent_runner.py::TestActionLog::test_crashed_call_entry_reason_is_class_name` | không có thông điệp lỗi, chỉ tên lớp |
| AC-10(d) | `…test_agent_runner.py::TestActionLog::test_fake_password_never_in_actions_column` | mật khẩu giả trong tham số tool → 0 lần trong cột `actions` |
| AC-10 (ca xuyên) | `…test_agent_runner.py::TestActionLog::test_record_tool_and_ticket_field_same_run_same_shape` | 1 `api_update_record` + 1 `set_classification` → 2 mục, cùng `run_id`, cùng `ACTION_KEYS` |
| AC-10 | `…test_agent_runner.py::TestActionLog::test_route_entries_use_shared_shape` | mục của dòng `classify` có `ACTION_KEYS`, có `rule` khi có |
| AC-10 | `erp_ai/tests/test_architecture.py::test_action_entries_built_only_in_run_log` | AST: dict literal có khóa `"tool"` và `"ok"` ngoài `run_log.py` (trừ test) → finding; chứng minh bằng chuỗi mẫu |
| AC-10 | `…test_architecture.py::test_entry_types_unchanged` | ghim 5 giá trị (hằng + option JSON); lý do: ADR-033 QĐ 5 |
| AC-10 | `…test_architecture.py::test_log_trigger_options_match_run_log` | option `trigger` == `TRIGGERS + CHANGE_TRIGGERS + BOT_ACTION_TRIGGERS` |
| AC-10 | `…test_architecture.py::test_policy_does_not_import_run_log` | |
| AC-10 | `erp_ai/erp_ai_agent/doctype/erp_ai_log/test_erp_ai_log.py::TestOptions::test_entry_type_and_trigger_options` | meta sau migrate |
| AC-11 (i) | `erp_ai/agent/tools/test_propose_change.py::TestOneClickGate::test_switch_off_comment_has_no_decision_links` | không `_signature`, không `action=`; có liên kết form và `OPEN_PROPOSAL_LABEL` |
| AC-11 (i) | `…test_propose_change.py::TestOneClickGate::test_switch_off_never_signs` | `change_link.decision_path` được gọi 0 lần |
| AC-11 (ii) | `…test_propose_change.py::TestOneClickGate::test_switch_on_comment_matches_feat004_links` | bằng từng byte dòng liên kết của T53 |
| AC-11 (i) | `erp_ai/test_change_decision.py::TestOneClickGate::test_switch_off_old_link_refused_state_unchanged_zero_jobs` | chữ ký hợp lệ tạo lúc (5) bật; tắt; POST → `PermissionError` `ONE_CLICK_OFF`; "Chờ duyệt"; stub `enqueue_call` 0; số dòng Log không đổi; chạy `frappe.app.sync_database` như T54 |
| AC-11 (i) | `…test_change_decision.py::TestOneClickGate::test_switch_checked_before_signature` | chữ ký sai + (5) tắt → `ONE_CLICK_OFF` (không `BAD_LINK`); `signature_ok` gọi 0 lần |
| AC-11 | `…test_change_decision.py::TestOneClickGate::test_switch_read_at_request_time` | bật khi tạo liên kết, tắt lúc POST → từ chối; tắt rồi bật lại → duyệt được |
| AC-11 (i) | `…test_change_decision.py::TestOneClickGate::test_switch_off_form_method_still_decides` | Instructor gọi `approve` của controller (đường nút form) → "Đã duyệt"; hộp xác nhận của nút: `erp_ai_change_proposal/test_erp_ai_change_proposal.py::test_form_script_static_rules` (FEAT-004, không sửa) |
| AC-11 (ii) | `…test_change_decision.py::test_post_approve_sets_approved_and_one_job_survives_request_end` (T54, thêm (5) = 1) và các test T54 khác | kết quả do FEAT-004 AC-25 kiểm |
| AC-11 | `erp_ai/tests/test_architecture.py::test_decide_reads_one_click_switch_before_signature` | AST: trong `decide`, lời gọi `policy.permission_switches` đứng trước `signature_ok`; `propose_change._comment` chỉ gọi `decision_path` trong nhánh `one_click_approval` |
| AC-4 (dòng log) | `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py::TestPermissionSwitchLog::test_each_switch_on_writes_one_row` | 5 subTest: 1 dòng `bot_action`/`setting_save`, `instructor` = người lưu, 1 mục trước 0 sau 1, `site_environment`, `cost_usd` 0 |
| AC-4 | `…test_erp_ai_setting.py::TestPermissionSwitchLog::test_two_switches_on_one_row_two_entries` | |
| AC-4 | `…test_erp_ai_setting.py::TestPermissionSwitchLog::test_save_without_switch_change_no_row` | đổi trường khác (`max_turns_per_run`) → 0 dòng, 0 `msgprint` |
| AC-4, AC-10(a) | `…test_erp_ai_setting.py::TestPermissionSwitchLog::test_switch_off_writes_row_without_notice` | 1 → 0: 1 dòng, `msgprint` 0 lần (A-U3-1) |
| AC-4 | `…test_erp_ai_setting.py::TestPermissionSwitchLog::test_log_failure_fails_the_save` | `write_bot_action` ném → `save()` ném, 0 dòng |
| AC-4 (hằng ngày) | `erp_ai/tests/test_tasks.py::TestPermissionSwitchAlarm::test_two_switches_on_listed_in_one_alarm` | (1), (5) bật → 1 mục cảnh báo `PERMISSION_SWITCHES_ON_SUBJECT`, có 2 nhãn |
| AC-4 | `…test_tasks.py::TestPermissionSwitchAlarm::test_all_off_no_alarm_entry` | |
| AC-4 | `…test_tasks.py::TestPermissionSwitchAlarm::test_condition_writes_no_log_row_and_keeps_watermark` | số dòng Log và `privilege_alert_checked_until` (FEAT-005 T7) không đổi |
| AC-4 | `…test_tasks.py::TestPermissionSwitchAlarm::test_error_later_rolls_back_switch_alarm` | lỗi ở bước sau trong job → không còn Error Log của mục này |

Test FEAT-004 ghim hành vi cũ phải sửa theo AC, ghi lý do trong commit (NFR-8, STD-TEST-5): so sánh dict mục 4 khóa trong `test_agent_runner.py`; test liên kết của T53 trong `test_propose_change.py` và test POST của T54 trong `test_change_decision.py` (đặt (5) = 1); `test_entry_types_unchanged`.

### Đối chiếu AC (Done criteria)

- AC giao cho U3 (`arch-impact.md:178` và lệnh giao việc): AC-4 (dòng nhật ký khi đổi công tắc, điều kiện hằng ngày), AC-10, AC-11.
- AC có trong test plan trên: AC-4, AC-10, AC-11. Khớp 3/3.
- Phần của các AC đó **không** thuộc U3: AC-4 thông báo trên form (U0); AC-10 mục của tool và việc do đơn vị sau thêm (U4b, U6b, U7, U8, U5b — mỗi đơn vị thêm test một ca cho tool/việc của mình, dùng `action_entry`); AC-10 phần FEAT-004 AC-34/35 (T64); AC-11 cơ chế liên kết (FEAT-004 AC-25, T53, T54).

---

## Assumptions decided by the team

| # | Chọn | Vì | Phương án khác | Sai thì sửa |
|---|---|---|---|---|
| A-U3-1 | Ghi dòng nhật ký cả khi công tắc đổi 1 → 0; thông báo chỉ khi 0 → 1 | AC-10(a) "thay đổi công tắc quyền"; AC-4 chỉ ràng thông báo và dòng khi bật | chỉ ghi khi bật | bỏ vế `bool(trước) != bool(sau)` thành `not trước and sau` |
| A-U3-2 | Một lần lưu = một dòng, một mục cho mỗi công tắc đổi | ADR-030 QĐ 7 "ghi đúng một dòng"; ADR-033 QĐ 5 mục là đơn vị | một dòng mỗi công tắc | tách vòng lặp trong `record_permission_switch_changes` |
| A-U3-3 | JS form không sửa; server từ chối, `frappe.call` hiện chữ của server | JS không biết (5) nếu không thêm `__onload` ngoài file U3; ranh giới ở server | thêm `__onload.one_click_approval` để JS không gọi | thêm dữ liệu ở controller đề xuất (U7 đang sửa file đó) |
| A-U3-4 | Mục bị từ chối mà tool không nêu lý do → `NO_REASON`, không ném | ném làm hỏng cả lượt (hoàn tác lượt) vì một tool thiếu chữ | `ValueError` | đổi một nhánh trong `action_entry` |
| A-U3-5 | Bản ghi tạo mới không trả trước/sau: `value_after` = tham số của lời gọi đã che; đề xuất: chỉ `change_status` | tool phiếu nằm ngoài file của U3; nội dung đề xuất (diff) đã ở bản ghi đề xuất | đọc lại bản ghi sau khi tạo | thêm hàng ở bảng `_entry_values` |
| A-U3-6 | `site_environment` rỗng/lạ → `"production"` | fail-closed: production là chế độ chặt hơn (ADR-031 QĐ 7) | để trống | đổi một nhánh trong `policy.site_environment` (U1) |
| A-U3-7 | `decide` đọc Setting bằng `frappe.get_single` mỗi request | ADR-032: giá trị lúc request; tắt có hiệu lực ngay | đọc từ cache | đổi sang `get_cached_doc` nếu đo được chậm |
| A-U3-8 | Lỗi ghi dòng `setting_save` làm lưu Setting thất bại | không có công tắc đổi mà thiếu dòng (NFR, AC-10) | nuốt lỗi, lưu tiếp | bắt lỗi trong `record_permission_switch_changes` và `log_error` |
| A-U3-9 | Liên kết bị cổng (5) từ chối: chỉ một dòng logger, không dòng ERP AI Log | ADR-032 QĐ 4 "không ghi gì" | dòng `bot_action` | thêm `write_bot_action` trong nhánh từ chối (cần architect) |

Câu hỏi nghiệp vụ: 0.
