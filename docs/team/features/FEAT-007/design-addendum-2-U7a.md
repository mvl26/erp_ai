Feature: FEAT-007
Stage: design
Author-agent: designer
Date: 2026-11-14
Approved-by:
<!-- Cổng: G2b không áp dụng cho FEAT-007 (team.py: chỉ G5). Để trống. -->

# Design addendum 2 — U7a Danh mục trắng, bộ thực thi, đề xuất thay đổi bản ghi, người duyệt theo loại, "Sửa", môi trường site (FEAT-007)

Theo ADR-031 QĐ 1–9 (đã đọc hết), ADR-023 QĐ 1–5, ADR-012 QĐ 1–7, ADR-033 QĐ 1, 5; không đổi kiến trúc. Phạm vi: AC-12, AC-29, AC-30, AC-33, AC-34, AC-35 (văn bản `[changed]` của `spec-addendum-1.md` 2.1 thắng `spec.md`). **Ngoài phạm vi** (lần gọi sau, U7b/U8): AC-36 (vị từ "Tự làm" và chuỗi duyệt), AC-37 (thống kê), AC-38 (ghi đè prompt), AC-39 và ADR-032 (duyệt trong ngăn), AC-64 (tạo Project), khối prompt danh mục và `Grant.catalog_block`, phần cảnh báo của ADR-031 QĐ 8 (ADR-024 đọc dòng bước áp dụng). Chỗ U7b chen vào được ghi tên ở mục 3.11.

---

## 1. Bối cảnh

### 1.1 Explore summary (đọc trực tiếp, đích đã biết; 2026-11-14; `team/FEAT-004` @ `73f346d` trong `.claude/worktrees/feat-004`)

- `tools/propose_change.py`: chỗ tạo đề xuất duy nhất là `_insert(ctx, values)` (`:125-139`), bọc `allow_agent_write()` (M5 đường hợp lệ 2), rồi `_comment` (`:102-122`) luôn dựng liên kết đã ký `change_link.decision_path` (bản T53; luật "(5) tắt → không ký" của U3 3.4 chưa có). `_entry_refusal` (`:57-64`) đòi `ctx.instructor`.
- `changes/transitions.py`: `STATE_FIELDS` (`:27-43`), `DIGEST_FIELDS` 14 trường (`:45-60`), `FINISH_EDGES` gồm `Đã duyệt → Lỗi` và `Đang áp dụng → Hết hiệu lực` (`:64-71`); `_lock` khóa dòng `for_update` (`:140-153`); `_decide` tính `approved_digest` (`:160-170`); `request_undo` chặn `Lệnh bench` (`:188-207`); `finish(..., fields=)` chỉ nhận `GIT_RESULT_FIELDS` (`:224-277`); `log_step` chưa truyền `actions` (`:106-132`).
- `changes/apply_job.py`: `_locked_run` lấy `filelock(LOCK_NAME, 30 s)` cho mọi loại, `LockTimeoutError` → `Lỗi` `LOCK_BUSY` (`:103-121`); `_run_in_lock` commit trạng thái chạy trước khi làm (`:124-168`); `_run` rẽ code / còn lại là lệnh (`:171-180`) — một loại thứ ba hôm nay sẽ rơi vào `_apply_command`; `_has_authority` so `ROLE_INSTRUCTOR` (`:183-184`); `_recheck` M2: người chạy = `decided_by`/`undo_by`, quyền, công tắc, dấu, bộ chặn (`:187-237`).
- Controller đề xuất: `CONTENT_FIELDS` 20 trường bất biến (`:13-34`), `_decider` so `ROLE_INSTRUCTOR` + `NEVER_AUTHORITY` rồi mới kiểm tồn tại (`:93-112`); `approve`/`reject`/`undo` POST (`:115-137`). JSON: `change_kind` Select `Thay đổi code\nLệnh bench`; DocPerm `ERP AI Agent` create+read, Instructor và System Manager read. JS có `decide_from_link` (T54 đã vào `team/FEAT-004`; `change_decision.decide` là POST, `:20`).
- `tools/site_api.py`: `PERMISSION_DOCTYPES` (`:26`), `FORBIDDEN_ROLES` (`:28`), `PROTECTED_USERS`, `SECRET_FIELDS`, `SYSTEM_FIELDS` (`:29-33`) công khai; `_write` savepoint mẫu (`:145-165`). Chưa có `PERMLEVEL_DOCTYPES` (U2 C-6).
- `authority.py` (giống nhau ở `develop` và `team/FEAT-004`): `NEVER_AUTHORITY` (`:12`), `is_instruction` (`:44-49`), `_assigned_by_other` đọc `_assign` + ToDo mới nhất `Open` (`:52-69`).
- `runner.py` (`team/FEAT-004`): bước "propose" của nhật ký do runner ghi theo tên tool `PROPOSE_TOOLS` (`:87`, `:676-683`); `WRITE_TOOL_TARGETS` (`:77-79`).
- Helpdesk/ERPNext đã cài: `HD Team.users` là Table MultiSelect `HD Team Member` (trường `user`); `Holiday List.holidays` (`Holiday`: `holiday_date`, `description`, `weekly_off`), `from_date`, `to_date`.
- FEAT-004 AC-28 (comment kết quả áp dụng): `grep new_comment` trong `erp_ai/agent/changes/`, controller đề xuất = 0; `grep "AC-28" FEAT-004/tasks.md` = 0. **Chưa có ở đâu.**

### 1.2 Tên FEAT-004 / U0 / U1 / U2 / U3 mà U7a dựa vào

| Tên | Nguồn | Có trên `team/FEAT-004` hôm nay? |
|---|---|---|
| `allow_agent_write`, `refuse_agent_write` (`agent_write_guard.py`) | FEAT-004 T65 | **Có** |
| `transitions.approve/reject/request_undo/begin_apply/finish/log_step/content_digest`, `STATE_FIELDS`, `DIGEST_FIELDS`, `FINISH_EDGES`, `GIT_RESULT_FIELDS`, `InvalidTransition` | FEAT-004 | **Có** |
| `apply_job._locked_run/_run_in_lock/_recheck/_Stop`, `WRONG_RUNNER`, `APPROVER_LOST_ROLE`, `DIGEST_CHANGED`, `LOCK_BUSY` | FEAT-004 (M2: ADR-023 QĐ 2) | **Có** |
| `queue.enqueue_change_job` | FEAT-004 | **Có** |
| `change_decision.decide` POST, JS `decide_from_link` | FEAT-004 T54 | **Có** |
| `change_link.decision_path`, `ACTION_APPROVE`, `ACTION_REJECT` | FEAT-004 T53 | **Có** |
| `site_api.PERMISSION_DOCTYPES`, `FORBIDDEN_ROLES`, `SECRET_FIELDS`, `SYSTEM_FIELDS`, `PROTECTED_USERS` | FEAT-004 (T59) | **Có** |
| `read.denied_doctypes()` | FEAT-004 | **Có** (`read.py:141`) |
| Comment kết quả áp dụng (xong, lỗi, hết hiệu lực, hoàn tác) gắn vào `transitions.finish` hoặc `apply_job` | FEAT-004 AC-28 | **Không** — không có mã, không có task (1.1). Cần từ FEAT-004 (1.3) |
| `CHANGE_KIND_*`, `CHANGE_STATUS_*`, `PROPOSAL_DOCTYPE`, `ROLE_INSTRUCTOR`, `AGENT_USER`, `CATEGORIES`, `LEVELS` | `erp_ai/constants.py` | **Có** |
| `ACTION_*` (6), `CATALOG_ACTIONS`, `MODE_DENY/MODE_NEEDS_APPROVAL/MODE_AUTO`, `CATALOG_MODES` | U0 (`constants.py`, w0-fixes F-1) | Không (nhánh FEAT-007, đợt 0) |
| `hard_bans.hard_ban_reason(doctype)` | U0 (`agent/hard_bans.py`, F-3, INT-1) | Không (FEAT-007 đợt 0) |
| Trường Setting `catalog_rules`, `user_templates`, `site_environment`; DocType con `ERP AI Catalog Rule` (`action`, `target_doctype`, `fields`, `categories`, `mode`), `ERP AI User Template` (`template_name`, `roles`) | U0 (`design.md:120-125, 202-225`) | Không (FEAT-007 đợt 0) |
| `policy.site_environment`, `SITE_ENVIRONMENTS`, `DEFAULT_SITE_ENVIRONMENT` | U1 (C-1) | Không (đợt 1) |
| `policy.latest_classification`, `policy.main_path_level`; `ToolContext.main_path_level`, `below_threshold`, `one_click_approval`; `GRANT_TABLE`, `grant`, `ToolSpec.group` | U1 (3.1, 3.2, 3.9) | Không |
| `authority.enter_agent_session`, `TITLE_WRONG_USER`; `_assigned_by_other` loại gán do agent | U1 (3.3) | Không |
| `site_api.PERMLEVEL_DOCTYPES`, `PERMLEVEL_REASON`, `_permlevel_refusal` | U2 (C-6) | Không |
| Vị từ phiếu loại trừ `is_ticket_record_excluded` | U2 (3.8 của `design-addendum-1-U2.md`) | Không |
| `run_log.action_entry`, `write_entry` nhận `actions` cho dòng `change`, `SECRET_MASK` | U3 (3.1, 3.10) | Không |
| `propose_change._comment` luật "(5) tắt → không gọi `decision_path`", `OPEN_PROPOSAL_LABEL` | U3 (3.4) | Không |
| `runner._entry_values` (bảng chọn trước/sau theo kết quả) | U3 (3.2) | Không |

**Điều kiện bắt đầu U7a:** FEAT-004 đã merge `develop` (hết chuỗi `apply_job.py`, T56, T67 — arch-impact hàng U7); U0, U1, U2, U3 đã ở `team/FEAT-007`. Cắt sớm hơn → dev phải dựng lại tên ở bảng trên → `DESIGN_CONFLICT`, dừng.

### 1.3 Cần từ U0 / U1 / U2 / U3 / FEAT-004 (không tự đặt)

| Cần | Chủ | Trạng thái |
|---|---|---|
| Ba hằng trong khối FEAT-007 của `erp_ai/constants.py`: `CHANGE_KIND_RECORD = "Thay đổi bản ghi"`; `ACTION_TARGET_DOCTYPES = {ACTION_CREATE_USER: "User", ACTION_ADD_TEAM_MEMBER: "HD Team", ACTION_ADD_HOLIDAY: "Holiday List", ACTION_SET_ITEM_GROUP: "Item", ACTION_CREATE_CUSTOM_FIELD: "Custom Field", ACTION_UPDATE_FIELDS: None}` (đúng cột "DocType đích" của `design.md:214-221`); `TEST_SITE_ONLY_DOCTYPES = ("Custom Field", "Server Script", "Client Script", "Property Setter", "Workflow", "Data Import")` (AC-12 `[changed]`) | U0 (chủ khối hằng) | **Thiếu** trong U0. `constants.py` không có trong ô file U7 của arch-impact. Team-leader chọn: giao U0 thêm, hoặc thêm `constants.py` (đúng 3 hằng) vào touchpoint U7a. Lý do đặt ở đây, không trong module danh mục: ADR-031 Ràng buộc 7 cấm tên DocType viết tay trong module danh mục, và `"Custom Field"` ∈ `PERMLEVEL_DOCTYPES` |
| `policy.site_environment()` | U1 C-1 | Có trong điều kiện C-1 |
| `site_api.permlevel_refusal(doctype: str, values: dict, *, stored: dict \| None = None) -> str \| None` — bản công khai của `_permlevel_refusal` (U2, C-6), không cần `ctx` (luôn chế độ thường) | U2 | **Thiếu** tên công khai. Không có thì U7a phải chép luật `permlevel` (STD-DESIGN-4) |
| `is_ticket_record_excluded` gọi được với `(doctype, name)` từ Lõi | U2 | Có theo U2 3.8 (chưa đọc lại chữ ký; dev đối chiếu) |
| `write_entry` nhận `actions` trên dòng `entry_type="change"` (U3 2: "U7 thêm mục cho đề xuất bản ghi đã áp dụng") | U3 | Có |
| Comment kết quả của đề xuất (FEAT-004 AC-28) — một hàm do `transitions.finish` (hoặc job) gọi cho mọi loại | FEAT-004 | **Thiếu** (1.1). AC-33 `[changed]` dựa vào nó cho 4 kết cục. Nếu FEAT-004 bỏ AC-28 (thứ tự bỏ ở FEAT-004 spec N-7) thì AC-33 phần comment mất chủ → team-leader báo analyst |
| Danh sách ngoại lệ có tên của phép thử tĩnh FEAT-006 AC-9 (ADR-031 Ràng buộc 8) thêm `catalog_add_team_member.user`, `catalog_create_user.email/first_name/last_name` | chủ phép thử FEAT-006 (file ngoài ô U7) | **Thiếu** — team-leader giao |

---

## 2. Mô hình dữ liệu

### 2.1 ERP AI Change Proposal — chỉ thêm (STD-DESIGN-3)

`change_kind` options: `Thay đổi code\nLệnh bench\nThay đổi bản ghi` (thêm đúng một giá trị, ADR-031 Ràng buộc 1). Section mới `section_record` "Thay đổi bản ghi" (`depends_on: eval:doc.change_kind=='Thay đổi bản ghi'`), mọi trường `read_only: 1`, không DocPerm mới:

| fieldname | Kiểu | Nhóm | Ghi bởi | Ý nghĩa |
|---|---|---|---|---|
| `catalog_action` | Data | nội dung | `propose_change.insert_proposal` | một giá trị của `CATALOG_ACTIONS` |
| `target_doctype` | Data | nội dung | như trên | DocType đích (cố định theo hành động, hoặc của dòng "Đổi trường") |
| `target_name` | Data | nội dung | như trên | tên bản ghi đích (với hành động tạo: tên sẽ tạo — email, `dt-fieldname`) |
| `category` | Data | nội dung | như trên | đầu mục của phiếu lúc đề xuất (A–F) |
| `confidence_pct` | Int | nội dung | như trên | 0..100 |
| `action_args` | Code (JSON) | nội dung | như trên | tham số của hành động (mục 3.3), không gồm độ tin cậy/căn cứ |
| `record_before` | Code (JSON) | nội dung | như trên | "giá trị trước đã biết" để kiểm hết hiệu lực (mục 3.3, "giá trị canh") |
| `edited_args` | Code (JSON) | trạng thái | `transitions.approve` | giá trị sau "Sửa" (chỉ các khóa sửa được); rỗng nếu duyệt không sửa |
| `approved_with_edit` | Check | trạng thái | `transitions.approve` | 1 khi duyệt có sửa |
| `applied_values` | Code (JSON) | trạng thái | `transitions.finish` | ảnh chụp sau của lần áp dụng (cho hoàn tác) |

Dùng lại: `reason` = "Căn cứ"; `reversible` = 1 khi hành động ∈ `RESTORABLE_ACTIONS`; `ticket`, `run_id`, `instructor` (có thể rỗng: đường chính không cần người ra lệnh); `decided_by/at`, `undo_by/at`, `finished_at`, `failure_reason`, `approved_digest`. Không trường nào tên `value_before`/`value_after` (tránh trùng tên với ERP AI Log khi grep luật ADR-012 Ràng buộc 1).

- `CONTENT_FIELDS` += `RECORD_CONTENT_FIELDS = ("catalog_action", "target_doctype", "target_name", "category", "confidence_pct", "action_args", "record_before")`; `NUMERIC_CONTENT_FIELDS` += `confidence_pct`.
- `STATE_FIELDS` += `("edited_args", "approved_with_edit", "applied_values")`.
- `RECORD_DIGEST_FIELDS = ("change_kind", "catalog_action", "target_doctype", "target_name", "category", "action_args", "record_before", "edited_args")`. `content_digest` rẽ theo loại: loại bản ghi dùng bộ này; code/lệnh giữ **đúng** `DIGEST_FIELDS` (dấu của đề xuất code đã duyệt trước deploy không đổi — test ghim).
- Không có trường bộ đếm (ADR-031 QĐ 4, Ràng buộc 5). Mẫu truy cập của U7b/AC-37: lọc `change_kind`, `catalog_action`, sắp `decided_at` (khối lượng nhỏ, không thêm chỉ mục ở U7a).

### 2.2 Danh mục — đọc từ ERP AI Setting (U0 đã có schema)

`policy.CatalogRule` (dataclass frozen): `action: str`, `target_doctype: str | None`, `fields: frozenset[str]`, `categories: frozenset[str]`, `mode: str`. Dựng từ dòng `catalog_rules`: `categories` tách dấu phẩy, giữ phần tử ∈ `CATEGORIES`; `fields` tách dòng, bỏ trống; `mode` ∉ `CATALOG_MODES` → `MODE_DENY` (fail-closed); `action` ∉ `CATALOG_ACTIONS` → bỏ dòng. Đọc mỗi lần gọi (hiệu lực từ lần chạy kế tiếp, không deploy — AC-29).

---

## 3. API / hợp đồng

Mọi hàm là Python nội bộ trừ các method whitelisted của controller (POST, không `allow_guest`). Hợp đồng công khai bị chạm: thêm method `approve_with_edit`; `approve`/`reject`/`undo` giữ chữ ký và dạng trả, chỉ đổi tập người được phép theo AC-35 (thêm người được giao cho loại bản ghi; loại code không đổi).

### 3.1 `erp_ai/agent/policy.py` (thêm)

```python
CATALOG_RULES_FIELD = "catalog_rules"
USER_TEMPLATES_FIELD = "user_templates"
@dataclass(frozen=True)
class CatalogRule: ...                                   # mục 2.2
def catalog_rules(settings=None) -> tuple[CatalogRule, ...]
def user_template_roles(template_name: str, settings=None) -> tuple[str, ...] | None   # None: không có mẫu
```
`settings` None → `frappe.get_single(SETTING_DOCTYPE)`. So tên mẫu không phân biệt hoa thường (như U0 E-5). `policy` không import `hard_bans`, `tools` (w0-fixes F-1).

### 3.2 `erp_ai/agent/authority.py` (thêm)

```python
def is_assigned(user: str, ticket_name: str) -> bool
def can_decide(user: str, change_kind: str, ticket_name: str | None) -> bool   # vị từ duy nhất "đủ điều kiện duyệt"
@contextmanager
def agent_session() -> Iterator[None]
```

| Hàm | Hành vi | Lỗi |
|---|---|---|
| `is_assigned` | `user` có trong `_assign` của phiếu **và** ToDo mới nhất (`reference_type="HD Ticket"`, `reference_name`, `allocated_to=user`) có `status == "Open"`. Không xét `assigned_by` (gán do bot hay tự gán đều tính — ADR-031 Hệ quả, A-U7a-3). Thân tách từ `_assigned_by_other` thành `_open_assignment(user, ticket) -> dict \| None`; `_assigned_by_other` (bản U1) gọi lại nó rồi xét `assigned_by` (STD-DESIGN-4) | không ném; phiếu không có → `False` |
| `can_decide` | `user` rỗng hoặc ∈ `NEVER_AUTHORITY` → `False`. `ROLE_INSTRUCTOR ∈ frappe.get_roles(user)` → `True`. `change_kind == CHANGE_KIND_RECORD` và `ticket_name` → `is_assigned(user, ticket_name)`. Còn lại `False` (code, lệnh: chỉ Instructor — AC-35 (b)) | không ném |
| `agent_session` | lưu `previous = frappe.session.user`; `enter_agent_session()` (U1) sai → `frappe.throw(TITLE_WRONG_USER, frappe.PermissionError)`; `yield`; `finally: frappe.set_user(previous)`. Chỉ bộ thực thi danh mục dùng (ADR-031 Ràng buộc 3) | `PermissionError` khi không vào được phiên agent |

### 3.3 `erp_ai/agent/tools/catalog.py` (mới) — bộ thực thi hành động danh mục

Chỉ import `frappe`, `erp_ai.constants`, `erp_ai.agent.policy`, `erp_ai.agent.authority`, `erp_ai.agent.hard_bans`, `erp_ai.agent.tools.site_api`, vị từ loại trừ của U2. Không import `transitions`, `apply_job`, `registry`, `run_log`; không chứa `ignore_permissions`; không chứa chuỗi tên DocType hay tên vai trò (ADR-031 Ràng buộc 2, 7).

```python
@dataclass(frozen=True)
class CatalogRequest:
    action: str; args: dict; category: str | None
@dataclass(frozen=True)
class CheckResult:
    ok: bool; reason: str | None; mode: str | None; doctype: str | None; name: str | None
    watched: dict | None; test_site_only: bool = False
@dataclass(frozen=True)
class ExecResult:
    outcome: Literal["applied", "refused", "stale"]; reason: str | None
    doctype: str | None; name: str | None; value_before: dict | None; value_after: dict | None
@dataclass(frozen=True)
class ActionHandler:
    tool: str; target_keys: tuple[str, ...]; editable_keys: tuple[str, ...]; restorable: bool
    validate: Callable[[dict], str | None]       # hình dạng tham số
    target: Callable[[dict], tuple[str, str]]    # (doctype, name)
    watched: Callable[[dict], dict]              # giá trị canh hiện tại
    write: Callable[[dict], tuple[dict | None, dict]]   # (trước, sau), chạy trong phiên agent
ACTION_HANDLERS: dict[str, ActionHandler]          # 6 khóa = CATALOG_ACTIONS
RESTORABLE_ACTIONS = (ACTION_SET_ITEM_GROUP, ACTION_UPDATE_FIELDS)
CUSTOM_FIELD_ALLOWED_KEYS = ("dt", "fieldname", "label", "fieldtype", "options", "insert_after", "description")
CUSTOM_FIELD_FIELDTYPES = ("Data", "Small Text", "Text", "Long Text", "Int", "Float", "Currency",
                           "Percent", "Check", "Date", "Datetime", "Select", "Link")
UPDATE_REFUSED_FIELDTYPES = ("Table", "Table MultiSelect", "Password", "Section Break", "Column Break", "Tab Break")
SAVEPOINT = "erp_ai_catalog"

def rule_mode(rules, request, doctype, fields) -> tuple[str | None, str | None]
def check(request: CatalogRequest, *, rules=None, environment: str | None = None) -> CheckResult
def execute(request: CatalogRequest, *, watched_before: dict | None) -> ExecResult
def undo(request: CatalogRequest, *, applied_values: dict, record_before: dict) -> ExecResult
def check_edit(action: str, action_args: dict, edited: dict, category: str | None) -> str | None
def effective_args(action_args: dict, edited: dict | None) -> dict   # {**action_args, **edited}
```

**Sáu hành động** (tham số = khóa của `args`; khóa thừa → `ARGS_INVALID`):

| Hành động | Tham số (đích ∣ sửa được) | Canh (`watched`) | Ghi (dưới phiên agent, theo phân quyền) | Trước → sau (mục nhật ký) |
|---|---|---|---|---|
| `ACTION_CREATE_USER` | `email` ∣ `template`, `first_name`, `last_name` | `{"present": User email đã có}` | `insert` User `{email, first_name, last_name, roles: [{"role": r} for r in vai trò của mẫu]}`; không khóa mật khẩu nào được nhận | `None` → `{"name", "template", "roles"}` |
| `ACTION_ADD_TEAM_MEMBER` | `team` ∣ `user` | `{"present": user ∈ users}` | `get_doc(for_update=True)`, `append("users", {"user"})`, `save()` | `{"users": [cũ, sắp]}` → `{"users": [mới, sắp]}` |
| `ACTION_ADD_HOLIDAY` | `holiday_list` ∣ `holiday_date` (`YYYY-MM-DD`), `description` | `{"present": ngày đã có}` | `append("holidays", {"holiday_date", "description"})`, `save()` (ngoài `from_date..to_date` → Frappe từ chối) | `{"holiday_count": n}` → `{"holiday_count": n+1, "holiday_date", "description"}` |
| `ACTION_SET_ITEM_GROUP` | `item` ∣ `item_group` | `{"item_group": giá trị hiện tại}` | `item_group = …`, `save()` | `{"item_group": cũ}` → `{"item_group": mới}` |
| `ACTION_CREATE_CUSTOM_FIELD` | `dt`, `fieldname` ∣ `label`, `fieldtype`, `options`, `insert_after`, `description` | `{"present": Custom Field dt-fieldname đã có}` | `insert` Custom Field chỉ với `CUSTOM_FIELD_ALLOWED_KEYS` | `None` → các khóa đã ghi |
| `ACTION_UPDATE_FIELDS` | `doctype`, `name` ∣ `values` (giá trị sửa được, **tập khóa** khóa cứng) | `{trường: giá trị hiện tại}` cho mỗi khóa của `values` | `doc.update(values)`, `save()` | `{trường: cũ}` → `{trường: mới}` |

**`check` — thứ tự cố định (ADR-031 QĐ 2), trả lý do đầu tiên khớp, không ghi gì:**
1. `action ∈ CATALOG_ACTIONS`, `handler.validate(args)`; với tạo Custom Field: mọi khóa ∈ `CUSTOM_FIELD_ALLOWED_KEYS` (khác → `CUSTOM_FIELD_KEY_REFUSED`, phủ `permlevel`, `fetch_from`, `ignore_user_permissions`), `fieldtype ∈ CUSTOM_FIELD_FIELDTYPES`, `fieldname` khớp `^[a-z][a-z0-9_]{0,60}$`; với Đổi trường: `doctype` chuẩn hóa về tên lưu, mỗi khóa là trường có thật, kiểu ∉ `UPDATE_REFUSED_FIELDTYPES`, ∉ `site_api.SECRET_FIELDS ∪ SYSTEM_FIELDS ∪ {"name"}`; `(doctype, name) = handler.target(args)`; đích phải tồn tại (trừ hai hành động tạo) → `TARGET_MISSING`.
2. Danh mục: `rule_mode(rules or policy.catalog_rules(), …)`. Ứng viên = dòng cùng `action`, cùng `target_doctype` (Đổi trường, Tạo Custom Field theo `dt`), `category ∈ categories`. Có ứng viên `Cấm` (với Đổi trường: giao trường khác rỗng) → `RULE_DENIED`. Không ứng viên không-Cấm nào phủ (Đổi trường: tập khóa ⊆ `fields`) → `OUT_OF_CATALOG`. Chế độ = `Cần duyệt` nếu có một dòng phủ là `Cần duyệt`, ngược lại `Tự làm`. `category` None → không dòng nào khớp.
3. Điều cấm cứng: `hard_bans.hard_ban_reason(doctype)`; với tạo Custom Field thêm `hard_ban_reason(dt)` và, khi `fieldtype == "Link"`, `hard_ban_reason(options)`; `site_api.permlevel_refusal(doctype, values, stored=…)` khi `doctype ∈ site_api.PERMLEVEL_DOCTYPES` (U2); đích là bản ghi của phiếu loại trừ (vị từ U2) → lý do của U2. Đổi trường trên `User` có tên ∈ `site_api.PROTECTED_USERS` → `HARD_BAN`.
4. Vai trò cấm (tạo tài khoản): `policy.user_template_roles(template)` None → `TEMPLATE_MISSING`; giao với `site_api.FORBIDDEN_ROLES` (so `casefold`) khác rỗng → `FORBIDDEN_ROLE` (kiểm lại cả khi U0 đã chặn lúc lưu — mẫu có thể sửa sau).
5. Môi trường: `doctype` (với tạo Custom Field là `"Custom Field"` của `ACTION_TARGET_DOCTYPES`) ∈ `TEST_SITE_ONLY_DOCTYPES` và `(environment or policy.site_environment()) != "test"` → `TEST_SITE_ONLY`, `test_site_only=True`.
6. `watched = handler.watched(args)`; precondition đã đạt (`present` đúng ở hành động thêm/tạo; giá trị hiện tại bằng giá trị mới ở hành động đổi) → `NO_CHANGE`.

Đạt cả 6 → `CheckResult(ok=True, mode=…, watched=…)`.

**`execute`:** `check(request)`; không đạt → `ExecResult("refused", reason)`. `watched_before` khác None và `watched != watched_before` → `ExecResult("stale", STALE_TARGET)` (ở hành động thêm/tạo, `NO_CHANGE` ở bước 6 cũng trả `stale` khi `watched_before` khác None). Ghi: `savepoint(SAVEPOINT)` → `with authority.agent_session(): before, after = handler.write(args)` → `release_savepoint`. Lỗi: `PermissionError` → rollback savepoint, `refused` `AGENT_NO_PERMISSION`; `ValidationError` → `refused` `SYSTEM_REFUSED` (chữ đã `strip_html`); khác → rollback savepoint, `frappe.log_error(TITLE_CATALOG_FAILED, f"action={…} doctype={…} error={type(exc).__name__}")`, `refused` `UNEXPECTED_ERROR`. Phiên luôn được trả lại trước khi hàm trả (người gọi rồi mới ghi trạng thái đề xuất). Một dòng `frappe.logger(LOGGER_NAME).info("erp_ai catalog action=%s doctype=%s name=%s outcome=%s env=%s", …)` mỗi lần gọi.

**`undo`** (chỉ `handler.restorable`): bước 1, 3, 5 của `check` (không xét danh mục — khôi phục giá trị cũ, như hoàn tác code bỏ qua công tắc); giá trị hiện tại của các khóa ≠ `applied_values` → `refused` `UNDO_TARGET_CHANGED`; ghi lại `record_before` như `write` (cùng savepoint, cùng phiên agent). Không bao giờ xóa.

**`check_edit`** (AC-34): `edited` phải là dict, khóa ⊆ `editable_keys` (khác → `EDIT_TARGET_LOCKED`); Đổi trường: `set(edited["values"]) == set(action_args["values"])` (khác → `EDIT_TARGET_LOCKED`); `effective_args(...) == action_args` → `EDIT_NO_CHANGE`; rồi `check(CatalogRequest(action, effective_args, category))` đủ 6 bước → lý do của nó. `None` = hợp lệ.

**Chữ (hằng của module):** `OUT_OF_CATALOG = "ngoài danh mục: việc này chưa có trong danh mục trắng cho đầu mục của phiếu"`; `RULE_DENIED = "ngoài danh mục: danh mục đặt chế độ Cấm cho việc này"`; `HARD_BAN = "điều cấm cứng: {reason}"`; `FORBIDDEN_ROLE = "vai trò không được gán: {roles}"`; `TEMPLATE_MISSING = "không có mẫu tài khoản: {name}"`; `ARGS_INVALID = "tham số sai: {detail}"`; `CUSTOM_FIELD_KEY_REFUSED = "thuộc tính Custom Field không được phép: {key}"`; `TEST_SITE_ONLY = "cần làm trên site test: môi trường site đang là production"`; `TARGET_MISSING = "không có {doctype} {name}"`; `NO_CHANGE = "đích đã ở giá trị đề xuất"`; `STALE_TARGET = "giá trị hiện tại của đích khác giá trị lúc đề xuất"`; `UNDO_TARGET_CHANGED = "đích đã đổi sau khi áp dụng, không hoàn tác"`; `AGENT_NO_PERMISSION = "tài khoản agent thiếu quyền Frappe trên {doctype}"`; `SYSTEM_REFUSED = "hệ thống từ chối: {detail}"`; `UNEXPECTED_ERROR = "lỗi hệ thống khi ghi, không có gì thay đổi"`; `EDIT_TARGET_LOCKED = "Sửa chỉ đổi giá trị, không đổi đích hay danh sách trường: {key}"`; `EDIT_NO_CHANGE = "giá trị sửa trùng giá trị đề xuất"`; `TITLE_CATALOG_FAILED = "erp_ai: hành động danh mục lỗi"`. Mọi chữ ≤ `site_api.REASON_MAX`.

### 3.4 `erp_ai/agent/tools/catalog_tools.py` (mới) — nhóm tool `catalog`

`GROUP = "catalog"`; `CATALOG_WRITE_TOOL_NAMES` = 6 tên `catalog.ACTION_HANDLERS[a].tool`: `catalog_create_user`, `catalog_add_team_member`, `catalog_add_holiday`, `catalog_set_item_group`, `catalog_create_custom_field`, `catalog_update_fields`; thêm tool đọc `catalog_list_allowed` (không tham số; trả các dòng không-Cấm áp cho đầu mục của phiếu: `action`, `target_doctype`, `fields`, `mode`). Schema mỗi tool ghi = tham số của 3.3 + `confidence_pct` (integer 0..100) + `basis` (string 1..1000, "Căn cứ"); `additionalProperties: false`. Chỉ `catalog_update_fields` và `catalog_create_custom_field` nhận tên DocType (ngoại lệ hẹp ADR-031 bổ sung ADR-005 QĐ 3).

Handler chung `_propose(action, args, ctx) -> dict`:
1. Tách `confidence_pct`, `basis`; sai kiểu/khoảng/rỗng → `{"ok": False, "reason": ARGS_INVALID…}` (AC-22: thiếu căn cứ thì không đăng comment).
2. `category = policy.latest_classification(ctx.ticket_name)[0]`; `result = catalog.check(CatalogRequest(action, args, category))`.
3. Không đạt: nếu `result.test_site_only` → đăng **1** comment `TEST_SITE_COMMENT` trên phiếu (một lần mỗi `ctx.run_id`, nhớ ở `frappe.local.flags.erp_ai_test_site_runs`); trả `{"ok": False, "reason": result.reason}`. Không tạo đề xuất.
4. Đạt (chế độ `Cần duyệt` hoặc `Tự làm`): **U7a luôn tạo đề xuất** (`Tự làm` chưa có vị từ AC-36 = rơi về `Cần duyệt`, đúng AC-33). Điểm chen của U7b: một nhánh trước bước này, gọi `catalog.execute(..., watched_before=None)` khi vị từ U7b đúng (3.11).
5. `propose_change.insert_proposal(ctx, {"change_kind": CHANGE_KIND_RECORD, "catalog_action": action, "target_doctype": result.doctype, "target_name": result.name, "category": category, "confidence_pct": …, "action_args": json.dumps(args, ensure_ascii=False, sort_keys=True), "record_before": json.dumps(result.watched, …), "reason": basis, "reversible": int(action in RESTORABLE_ACTIONS)})` → trả `{"ok": True, "proposal", "status", "comment"}` (cùng dạng `propose_*`).

Trước bước 2: `frappe.has_permission(PROPOSAL_DOCTYPE, "create")` và `("Comment", "create")` như `_entry_refusal` (không đòi `ctx.instructor`). `TEST_SITE_COMMENT = "Việc «{action}» trên {doctype} cần làm trên site test. Site này đang đặt môi trường production nên bot không làm và không tạo đề xuất."` (thoát HTML).

### 3.5 `erp_ai/agent/tools/propose_change.py` (sửa)

- `_insert` đổi tên thành `insert_proposal(ctx, values) -> dict` — **hàm chèn duy nhất** cho mọi loại (ADR-031 QĐ 3); ba tool cũ gọi tên mới; thân, `allow_agent_write`, dạng trả giữ nguyên.
- `_comment` thêm nhánh `CHANGE_KIND_RECORD`: câu đầu `Đề xuất <a>{name}</a> đang chờ duyệt: {catalog_action} trên <code>{target_doctype} {target_name}</code>.`; mỗi khóa sửa được một dòng `{khóa}: {trước} → {đề xuất}`; `Độ tin cậy: {confidence_pct}%`; `Căn cứ: {reason}` (mọi giá trị qua `escape_html`). Dòng liên kết theo luật U3 3.4: (5) bật → `Duyệt · Sửa · Từ chối` (Duyệt/Từ chối = `decision_path` đã ký như loại code; Sửa = `form + "?erp_ai_edit=1"`, không ký, không đổi trạng thái); (5) tắt → `<a href=form>{OPEN_PROPOSAL_LABEL}</a> · <a href=form?erp_ai_edit=1>Sửa</a>`. `EDIT_LINK_LABEL = "Sửa"`, `EDIT_QUERY = "erp_ai_edit=1"`.

### 3.6 `erp_ai/agent/changes/transitions.py` (sửa)

| Hàm | Đổi |
|---|---|
| `approve(name, user, *, edited: dict \| None = None) -> str` | `edited` None → như nay. Có → loại phải là `CHANGE_KIND_RECORD` (khác → `InvalidTransition("Chỉ đề xuất thay đổi bản ghi có Sửa")`); ghi cùng một `set_value`: `edited_args = json.dumps(edited, ensure_ascii=False, sort_keys=True)`, `approved_with_edit = 1`, `approved_digest` tính trên doc **đã gán** `edited_args`; `log_step(name, "approve", user, before={k: action_args[k] for k in edited}, after=edited)` (AC-34 "giá trị trước và sau của lần sửa"). Kiểm hợp lệ của `edited` không ở đây (controller gọi `catalog.check_edit` trước) |
| `request_undo` | `_lock` đọc thêm `reversible`. Loại bản ghi: `reversible` ≠ 1 → `InvalidTransition("Hành động này không hoàn tác được")`; còn lại như loại code |
| `content_digest` | rẽ `RECORD_DIGEST_FIELDS` / `DIGEST_FIELDS` theo `change_kind` |
| `finish(..., actions: list[dict] \| None = None)` | `fields` được phép = `RESULT_FIELDS = GIT_RESULT_FIELDS + ("applied_values",)`; `actions` truyền xuống `log_step` → `write_entry(actions=…)` (ADR-031 QĐ 8: mục hành động nằm trong dòng của bước áp dụng) |
| `log_step(..., actions=None)` | thêm tham số, truyền nguyên |

`FINISH_EDGES` không đổi (đủ cạnh). Không trạng thái mới.

### 3.7 `erp_ai/agent/changes/apply_job.py` (sửa)

- `_locked_run`: đọc thêm `change_kind`; loại bản ghi → `return _run_record(name, action, actor)` **không** lấy `filelock` (ADR-031 QĐ 9). Code/lệnh giữ nguyên đường khóa.
- `_has_authority(user)` bị bỏ; `_recheck` dòng quyền gọi `authority.can_decide(runner, proposal.change_kind, proposal.ticket)` (ADR-031 QĐ 5; với code/lệnh kết quả trùng hàm cũ).
- `_run_record(name, action, actor) -> str` (một giao dịch, không commit giữa chừng):
  1. Apply: `transitions.begin_apply(name)` sai → `OUTCOME_SKIPPED`; `expected = APPLYING`. Undo: trạng thái ≠ `Đang hoàn tác` → `OUTCOME_SKIPPED`.
  2. `_recheck_record(proposal, action)`: phiên = `decided_by`/`undo_by` (**trước** khi bộ thực thi đổi phiên) → `WRONG_RUNNER`; `can_decide` → `APPROVER_LOST_ROLE`; `content_digest == approved_digest` → `DIGEST_CHANGED`. Sai → `finish(expected, Lỗi, step="fail", reason=…)`.
  3. `request = CatalogRequest(catalog_action, catalog.effective_args(action_args, edited_args), category)`. Apply → `catalog.execute(request, watched_before=record_before)`; undo → `catalog.undo(request, applied_values=…, record_before=…)`.
  4. `refused` → `finish(expected, Lỗi, step="fail", reason, actions=[entry])`; `stale` → `finish(APPLYING, Hết hiệu lực, step="stale", reason, actions=[entry])`; `applied` → `finish(APPLYING, Đã áp dụng, step="apply", fields={"applied_values": json(after)}, before, after, actions=[entry])`; undo xong → `finish(UNDOING, Đã hoàn tác, step="undo", …)`. `entry = run_log.action_entry(handler.tool, doctype, name, ok, reason=…, value_before=…, value_after=…, instructor=proposal.instructor)`.
  5. `frappe.db.commit()` một lần. Ngoại lệ không lường → `rollback` (trạng thái về `Đã duyệt`/`Đang hoàn tác` vì chưa commit), `log_error(TITLE_CHANGE_FAILED, …)`, `finish(waiting, Lỗi, step="fail", reason=type(exc).__name__)`, commit.
- Dòng logger của `run_change` thêm `kind=%s`.

### 3.8 Controller và JS của ERP AI Change Proposal (sửa)

- `_decider(name) -> tuple[str, str]` (người, loại): `user ∈ NEVER_AUTHORITY` → `PermissionError` (chữ cũ); đọc `change_kind`, `ticket` của đề xuất; không có → `DoesNotExistError` nếu người có `ERP AI Instructor`, ngược lại `PermissionError` (không lộ tên đề xuất cho người không vai trò; giữ hành vi test FEAT-004); `not authority.can_decide(user, kind, ticket)` → `PermissionError` `NOT_ELIGIBLE = "Bạn không đủ điều kiện duyệt đề xuất này: cần vai trò ERP AI Instructor, hoặc đang được giao phiếu (chỉ với đề xuất thay đổi bản ghi)"`. Không chỗ nào khác so role để quyết duyệt (ADR-031 Ràng buộc 4).
- `approve`, `reject`, `undo`: gọi `_decider` mới; thân khác giữ.
- **Mới** `@frappe.whitelist(methods=["POST"]) approve_with_edit(name=None, edited_args=None) -> dict`: `_decider`; loại ≠ bản ghi → `ValidationError` `"Chỉ đề xuất thay đổi bản ghi có Sửa"`; `edited_args` là chuỗi JSON (≤ `PROPOSAL_TEXT_MAX_CHARS`) hoặc dict → dict, sai → `ValidationError` `"Giá trị sửa không đọc được"`; trạng thái ≠ `Chờ duyệt` → để `transitions.approve` ném `InvalidTransition`; `catalog.check_edit(...)` có lý do → `ValidationError` với lý do đó, **không ghi gì**; `transitions.approve(name, user, edited=edited)`; `queue.enqueue_change_job(name, "apply")`; trả `{"name", "status"}`.
- `validate` lúc tạo, loại bản ghi: `catalog_action ∈ CATALOG_ACTIONS`, `target_doctype`/`target_name` khác rỗng, `action_args`/`record_before` là JSON object, `0 ≤ confidence_pct ≤ 100` → sai thì `ValidationError`. Bất biến: `CONTENT_FIELDS` mở rộng (2.1).
- `onload`: loại bản ghi → `set_onload("editable_args", {k: effective_args[k] for k in editable_keys})`, không gọi `change_text.proposal_notes`.
- JS: loại bản ghi + `Chờ duyệt` → nút "Sửa và duyệt": dialog một ô Data mỗi khóa sửa được (khóa `values` bung thành một ô mỗi trường, gộp lại khi gửi), nút chính gọi `approve_with_edit` (dialog là bước xác nhận); địa chỉ có `erp_ai_edit=1` → xóa tham số khỏi địa chỉ rồi mở dialog (không gọi server). Nút "Hoàn tác" hiện theo `doc.reversible && doc.change_status == "Đã áp dụng"` (thay điều kiện chỉ-code).

### 3.9 `tools/registry.py`, `runner.py` (sửa, mỗi file vài dòng)

- `registry.py`: `TOOL_MODULES` thêm `"erp_ai.agent.tools.catalog_tools"`; `ToolSpec.group` Literal thêm `"catalog"`; `GRANT_TABLE` thêm dòng `("catalog", lambda i: LEVELS.index(i.main_path_level) >= LEVELS.index("L2") and not i.below_threshold)` (đúng U1 3.9). Không thêm `Grant.catalog_block` (người dùng là khối prompt U7b; thêm bây giờ là mã chết).
- `runner.py`: `PROPOSE_TOOLS = propose_change.PROPOSE_TOOL_NAMES + catalog_tools.CATALOG_WRITE_TOOL_NAMES`; điều kiện ghi bước `propose` thành `name in PROPOSE_TOOLS and outcome.get("ok") and outcome.get("proposal")`; 6 tool ghi vào `WRITE_TOOL_TARGETS` (kết quả có `proposal` → `(PROPOSAL_DOCTYPE, "proposal")`; kết quả có `doctype`/`name` → hai khóa đó); `_entry_values` (U3) chọn hàng theo kết quả, không theo tiền tố tên: có `proposal` → hàng `propose_*`; có `value_before`/`value_after` → hàng 1.

### 3.10 Lỗi — một dạng

Tool: `{"ok": False, "reason": <chữ 3.3>}` (dạng có sẵn). Method whitelisted: `frappe.PermissionError` (người), `frappe.DoesNotExistError`, `frappe.ValidationError` / `InvalidTransition` (dữ liệu, trạng thái) — chữ cố định, không lộ stack hay truy vấn (STD-ERR-3). Job: trạng thái `Lỗi`/`Hết hiệu lực` với `failure_reason` = chữ 3.3 hoặc 3.7, 1 dòng nhật ký `change`. Hàm nội bộ sai tham số: `ValueError`.

### 3.11 Contract for U7b và U8

| Tên | Chữ ký / giá trị | Module | Ai gọi |
|---|---|---|---|
| `can_decide` | `(user: str, change_kind: str, ticket_name: str \| None) -> bool` — vị từ duy nhất | `erp_ai/agent/authority.py` | U7b method duyệt của ngăn (ADR-032), `ticket_panel.py` (hiện nút) |
| `is_assigned` | `(user: str, ticket_name: str) -> bool` | `authority.py` | U7b (ngăn) |
| `agent_session` | context manager; chỉ quanh lần ghi đích | `authority.py` | U8 AC-64 qua bộ thực thi (không gọi trực tiếp) |
| Method controller `approve`, `reject`, `undo`, `approve_with_edit` | `(name=None)`, `(name=None, edited_args=None)` → `{"name", "status"}`; POST | `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py` | U7b: method của ngăn gọi thẳng các hàm này (không qua `decide`, U3 3.10) |
| `transitions.approve` | `(name, user, *, edited: dict \| None = None) -> str` | `erp_ai/agent/changes/transitions.py` | chỉ controller |
| `CatalogRequest`, `CheckResult`, `ExecResult`, `ActionHandler` | 3.3 | `erp_ai/agent/tools/catalog.py` | U7b, U8 |
| `check`, `execute`, `undo`, `check_edit`, `effective_args`, `rule_mode` | 3.3 | `catalog.py` | U7b: `execute(request, watched_before=None)` cho "Tự làm"; U8: không gọi trực tiếp |
| `ACTION_HANDLERS` | `dict[action, ActionHandler]`; thêm hành động = thêm một khóa + một hằng `ACTION_*` vào `CATALOG_ACTIONS` (U0 option Select theo) + `ACTION_TARGET_DOCTYPES` | `catalog.py` | U8 AC-64 (`ACTION_CREATE_PROJECT`) |
| `RESTORABLE_ACTIONS` | `(ACTION_SET_ITEM_GROUP, ACTION_UPDATE_FIELDS)` | `catalog.py` | U7b (AC-36: hoàn tác cắt chuỗi), U8 |
| Chữ `OUT_OF_CATALOG`, `RULE_DENIED`, `TEST_SITE_ONLY`, `NO_CHANGE`, `STALE_TARGET` | 3.3 | `catalog.py` | U7b test, U8 test |
| `GROUP = "catalog"`, `CATALOG_WRITE_TOOL_NAMES`, `_propose` bước 4 (điểm chen nhánh "Tự làm") | 3.4 | `erp_ai/agent/tools/catalog_tools.py` | U7b (vị từ AC-36 + comment báo lại), U8 (tool tạo Project = thêm một tên) |
| Dòng `catalog` của `GRANT_TABLE` | `main_path_level ≥ L2 ∧ ¬below_threshold` | `registry.py` | U7b thêm `Grant.catalog_block` + khối prompt |
| `insert_proposal` | `(ctx: ToolContext, values: dict) -> dict` — hàm chèn duy nhất | `erp_ai/agent/tools/propose_change.py` | U8 (qua `catalog_tools`) |
| `CatalogRule`, `catalog_rules`, `user_template_roles` | 3.1 | `erp_ai/agent/policy.py` | U7b ("đầu mục được phép trong dòng" của AC-36), U8 |
| `policy.site_environment` | U1 C-1 | `policy.py` | (đã có chủ) |
| Trường đề xuất cho AC-36/AC-37 | `change_kind == CHANGE_KIND_RECORD`, `catalog_action`, `category`, `confidence_pct`, `change_status`, `decided_by`, `decided_at`, `approved_with_edit`, `edited_args`, `undo_by`, `undo_at`, `finished_at`, `reversible` | JSON đề xuất | U7b đọc (không thêm trường bộ đếm, ADR-031 QĐ 4) |
| `CHANGE_KIND_RECORD`, `ACTION_TARGET_DOCTYPES`, `TEST_SITE_ONLY_DOCTYPES` | 1.3 | `erp_ai/constants.py` | U7b, U8 |
| Bước nhật ký: `approve` có `value_before`/`value_after` = lần sửa; `apply`/`stale`/`fail`/`undo` có `actions` = 1 mục `action_entry` | 3.6, 3.7 | ERP AI Log | U7b (thống kê, cảnh báo ADR-024 đọc dòng bước áp dụng) |

---

## 4. Luồng

**4.1 Đề xuất (AC-29, AC-33).** Runner (mức đường chính ≥ L2, trên ngưỡng) cấp nhóm `catalog` → model gọi `catalog_*` → `_propose`: kiểm tham số → `check` (6 bước) → từ chối (`ok=false`, nhật ký lượt có mục `ok=false` + lý do; môi trường production thì thêm 1 comment) **hoặc** `insert_proposal` (phép chuyển không có; đề xuất `Chờ duyệt`; 1 comment có Duyệt/Sửa/Từ chối, độ tin cậy, căn cứ) → runner ghi bước `propose`. Đích không đổi.

**4.2 Duyệt / Từ chối / Sửa (AC-33, AC-34, AC-35).** Người mở form (liên kết hoặc ngăn U7b) → POST → `_decider` (`can_decide`) → Duyệt: `transitions.approve` + xếp job; Sửa: `check_edit` (danh mục, điều cấm cứng, vai trò, môi trường **hiện tại**) → `transitions.approve(edited=…)` (dấu phủ giá trị sửa) + xếp job; Từ chối: `transitions.reject`, không job, 1 dòng `reject` (comment kết quả: FEAT-004 AC-28).

**4.3 Áp dụng (một giao dịch, không khóa chung).** Job (phiên = `decided_by`) → `begin_apply` (khóa dòng đề xuất) → `_recheck_record` (phiên, `can_decide`, dấu) → `catalog.execute(effective_args, watched_before=record_before)`: `check` lại (dòng danh mục **hiện tại**, điều cấm cứng, vai trò, môi trường) → so canh → `agent_session` + savepoint → ghi theo phân quyền → trả phiên → `finish` (`Đã áp dụng` | `Hết hiệu lực` | `Lỗi`, 1 dòng có 1 mục hành động) → commit. Lệnh `bench` đang giữ `erp_ai_change` không chặn bước này.

**4.4 Hoàn tác (loại bản ghi, `reversible`).** `undo` POST (`can_decide`) → `request_undo` → job → `_recheck_record` với `undo_by` → `catalog.undo` (hiện tại = `applied_values`?) → ghi `record_before` → `Đã hoàn tác` hoặc `Lỗi`.

**4.5 Mọi lời gọi ra ngoài** đều là DB nội bộ, không có gọi mạng mới; job giữ `timeout` của `enqueue_change_job` (`JOB_TIMEOUT_S`).

---

## 5. Quyền

| Biên | Kiểm ở server |
|---|---|
| Tool `catalog_*` | cấp bởi `grant` (mức đường chính ≥ L2, trên ngưỡng); `has_permission` tạo đề xuất + comment dưới tài khoản agent; danh mục + điều cấm cứng + vai trò + môi trường ở `catalog.check` |
| Method duyệt/sửa/từ chối/hoàn tác | POST, phiên người, `can_decide` theo loại (AC-35); tài khoản agent, Administrator, Guest luôn bị từ chối |
| Job áp dụng | M2: phiên = người đã quyết, `can_decide` lại, dấu; rồi bộ thực thi kiểm lại toàn bộ |
| Ghi đích | chỉ `catalog.py`, dưới tài khoản agent qua `agent_session`, theo DocPerm của Frappe, không `ignore_permissions`. Trên `miyano` tài khoản agent có `System Manager` (ADR-023 Bối cảnh) nên danh mục + điều cấm cứng là lớp chặn duy nhất (ADR-031 Hệ quả) |
| Ghi trạng thái đề xuất | chỉ `transitions.py` (gồm `edited_args`, `approved_with_edit`, `applied_values`) |
| Tạo đề xuất | chỉ `insert_proposal` trong `allow_agent_write` (M5 đường 2) |

---

## 6. Migration, rollback, quan sát

- **Lên:** sửa JSON đề xuất → `cmd.migrate` thêm 10 cột rỗng và một option; không ghi dữ liệu; bản ghi cũ không đổi (code/lệnh có các cột mới rỗng; dấu của chúng không đổi vì `DIGEST_FIELDS` giữ).
- **Xuống:** trước khi trả mã: đối chiếu `SELECT COUNT(*) FROM tabERP AI Change Proposal WHERE change_kind='Thay đổi bản ghi' AND change_status IN ('Chờ duyệt','Đã duyệt','Đang áp dụng','Đang hoàn tác')` = 0 (người có vai trò từ chối các đề xuất còn chờ); rồi trả JSON + mã, `cmd.migrate`. Frappe không xóa cột: dữ liệu cột mới giữ nguyên, bản ghi loại bản ghi đã kết thúc vẫn đọc được. Nếu lỡ còn một đề xuất bản ghi `Đã duyệt`, mã cũ rẽ vào `_apply_command` → `check_bench_args(None)` từ chối → `Lỗi` (fail-closed, không ghi đích). Test lên/xuống: mục 8 (ADR-031, STD-OPS-2).
- **Quan sát:** mỗi lần bộ thực thi chạy: 1 dòng logger `erp_ai catalog …` + 1 mục hành động trong ERP AI Log (dòng `reason` của lượt khi "Tự làm" — U7b; dòng bước của đề xuất khi sau duyệt) kèm `site_environment` (U3). `run_change` log thêm `kind`. Lỗi lạ: Error Log `TITLE_CATALOG_FAILED` / `TITLE_CHANGE_FAILED` chỉ tên lớp lỗi.

---

## 7. Touchpoints

| Đường dẫn | Mới/sửa | Trong ô U7 của arch-impact? | Ghi chú |
|---|---|---|---|
| `erp_ai/agent/tools/catalog.py` | mới | có ("module danh mục mới") | bộ thực thi, 3.3 |
| `erp_ai/agent/tools/catalog_tools.py` | mới | có (cùng module danh mục; tách vì tool ≠ bộ thực thi, ADR-031 Ràng buộc 2, STD-STRUCT-5) | 3.4 |
| `erp_ai/agent/tools/propose_change.py` | sửa | có | 3.5 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.json` | sửa | có | 2.1 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.py` | sửa | có | 3.8 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.js` | sửa | có | 3.8 |
| `erp_ai/agent/changes/transitions.py` | sửa | có | 3.6 |
| `erp_ai/agent/changes/apply_job.py` | sửa | có | 3.7 |
| `erp_ai/agent/authority.py` | sửa | có | 3.2 |
| `erp_ai/agent/tools/registry.py` | sửa | có | 3.9 |
| `erp_ai/agent/policy.py` | sửa | **không** trong bảng arch-impact; có trong design đã duyệt (`design.md:124` "bộ thực thi, `policy` (U7)", w0-fixes F-1 "`policy.py` (U7) phải đọc `MODE_*`") | 3.1 — team-leader ghi nhận |
| `erp_ai/agent/runner.py` | sửa | **không** trong bảng; có trong hợp đồng U3 3.10 ("U7 … thêm vào `WRITE_TOOL_TARGETS`") | 3.9 — team-leader ghi nhận |
| `erp_ai/constants.py` | sửa (3 hằng) | **không** — xem 1.3: giao U0 hoặc thêm vào U7a | — |
| Test: `erp_ai/agent/tools/test_catalog.py`, `erp_ai/agent/tools/test_catalog_tools.py` | mới | test | — |
| Test: `erp_ai/agent/test_authority.py`, `erp_ai/agent/test_policy.py`, `erp_ai/agent/changes/test_transitions.py`, `erp_ai/agent/changes/test_apply_job.py`, `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py`, `erp_ai/agent/tools/test_propose_change.py`, `erp_ai/agent/tools/test_registry.py`, `erp_ai/agent/test_agent_runner.py`, `erp_ai/tests/test_architecture.py` | sửa | test (ADR-031 Ràng buộc nêu `test_architecture.py`, `test_apply_job.py`, `test_transitions.py`, `test_authority.py`) | — |

Không chạm: `ticket_panel.py`, `agent_status_indicator.js`, `prompts.py`, report thống kê (U7b); `change_decision.py`, `site_api.py`, `run_log.py`, `hard_bans.py`, `erp_ai_setting.*` (đơn vị khác).

**So khớp đường dẫn mới với `structure.allowed_new_file_roots` = `["erp_ai", "docs", ".github"]`:**
```
erp_ai/agent/tools/catalog.py              -> erp_ai  OK
erp_ai/agent/tools/catalog_tools.py        -> erp_ai  OK
erp_ai/agent/tools/test_catalog.py         -> erp_ai  OK
erp_ai/agent/tools/test_catalog_tools.py   -> erp_ai  OK
docs/team/features/FEAT-007/design-addendum-2-U7a.md -> docs OK
```
**So với `protected_paths` = `[".env", ".env.*", "**/*.pem", "**/*.key", "license.txt"]`:** không đường dẫn nào ở bảng trên khớp (không `.env*`, không `.pem`/`.key`, không `license.txt`) → 0.

---

## 8. Test plan

Mọi test chạy qua `cmd.test_one` với `{file}` là đường dẫn file. Ký hiệu: `TC` = `erp_ai/agent/tools/test_catalog.py`, `TT` = `erp_ai/agent/tools/test_catalog_tools.py`, `TA` = `erp_ai/agent/changes/test_apply_job.py`, `TR` = `erp_ai/agent/changes/test_transitions.py`, `TP` = `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/test_erp_ai_change_proposal.py`, `TAU` = `erp_ai/agent/test_authority.py`, `TArch` = `erp_ai/tests/test_architecture.py`. Dữ liệu ERP (Item, Item Group, Holiday List, HD Team, User) do test tạo và dọn; không phụ thuộc thứ tự hay giờ máy (STD-TEST-6).

| AC / ràng buộc | Test (`file::Class::name`) | Ca biên / lỗi |
|---|---|---|
| AC-29 rỗng = cấm | `TC::TestRuleMode::test_empty_catalog_refuses_every_action` (6 hành động × danh mục rỗng → `OUT_OF_CATALOG`, DB trước = sau); `TT::TestProposeFlow::test_empty_catalog_no_proposal` (mỗi tool → `ok=false` "ngoài danh mục", 0 đề xuất, 0 comment) | 6 hành động + đề xuất bản ghi |
| AC-29 một dòng mở đúng phạm vi | `TC::TestRuleMode::test_one_row_opens_only_its_scope` (đúng hành động/DocType/trường/đầu mục → đạt; khác hành động, khác DocType, trường ngoài `fields`, đầu mục khác, `category` None → `OUT_OF_CATALOG`) | biên: trường thứ hai ngoài dòng; đầu mục None |
| AC-29 chế độ | `TC::TestRuleMode::test_deny_row_wins` (dòng `Cần duyệt` + dòng `Cấm` trùng trường → `RULE_DENIED`), `::test_unknown_mode_is_deny`, `::test_mode_needs_approval_beats_auto` | Select lạ → Cấm |
| AC-29 hiệu lực lần chạy kế, không deploy | `TT::TestProposeFlow::test_rule_added_between_calls_takes_effect` (gọi → từ chối; lưu Setting thêm dòng; gọi lại → đề xuất) | — |
| AC-29 điều cấm cứng ở bộ thực thi (danh mục truyền thẳng, bỏ qua kiểm lưu U0) | `TC::TestHardBans::test_hard_banned_targets_refused` (DocType của module app, `Custom DocPerm`, `Role`, một DocType submittable tìm động, Link `options` tới DocType của app, `User` thuộc `PROTECTED_USERS` → `HARD_BAN`) | 4 nhóm cấm của AC-29 |
| AC-29 không cổng 5 quyền | `TT::TestNotGated::test_record_tools_write_with_empty_catalog` ((2) bật, `ctx.record_tools`, danh mục rỗng → `site_api.create_record` `ok=true`) | — |
| AC-30 (1) tạo tài khoản | `TC::TestCreateUser::test_creates_with_template_roles` (vai trò = mẫu); `::test_forbidden_role_in_template_refused` (6 vai trò `FORBIDDEN_ROLES`, mẫu vá qua `policy.user_template_roles`, mỗi vai trò một ca → `FORBIDDEN_ROLE`, 0 User); `::test_password_key_refused` (`new_password`, `api_key` → `ARGS_INVALID`); `::test_missing_template`; `::test_existing_email_no_change` | 6 vai trò, khóa bí mật |
| AC-30 (2) thêm thành viên | `TC::TestAddTeamMember::test_adds_one_keeps_old` (tập cũ ⊆ tập mới, `len` +1); `::test_already_member_no_change` | đội rỗng; đã là thành viên |
| AC-30 (3) ngày nghỉ | `TC::TestAddHoliday::test_adds_one_keeps_old` (dòng cũ ⊆ mới, +1); `::test_date_outside_list_range_refused` (`SYSTEM_REFUSED`, DB không đổi); `::test_bad_date_format` | ngày ngoài `from_date..to_date`; `2026-02-30` |
| AC-30 (4) nhóm hàng | `TC::TestSetItemGroup::test_only_item_group_changes` (ảnh chụp mọi trường khác của Item trùng); `::test_unknown_item_group_refused` | nhóm không có |
| AC-30 (5) Custom Field | `TC::TestCreateCustomField::test_allowed_keys_create`; `::test_refused_keys` (`permlevel`, `fetch_from`, `ignore_user_permissions`, `allow_on_submit` → `CUSTOM_FIELD_KEY_REFUSED`, 0 Custom Field); `::test_fieldtype_outside_list` (`Password`, `Table`); `::test_bad_fieldname` | 4 khóa cấm; fieldname 62 ký tự |
| AC-30 Đổi trường | `TC::TestUpdateFields::test_only_listed_fields_change`; `::test_secret_system_table_fields_refused` (`new_password`, `owner`, một trường Table); `::test_permlevel_on_custom_field_refused` (U2 `permlevel_refusal`) | — |
| AC-30 ghi theo phân quyền | `TC::TestExecute::test_write_runs_as_agent_and_restores_session` (stub `handler.write` ghi lại `frappe.session.user` = `AGENT_USER`; sau `execute` phiên = người gọi, cả khi `write` ném); `::test_agent_permission_error_refused` (stub `PermissionError` → `AGENT_NO_PERMISSION`, savepoint trả, DB không đổi); `::test_unexpected_error_logged_and_refused` | ngoại lệ trong ghi |
| AC-33 đích không đổi tới khi duyệt | `TT::TestProposeFlow::test_needs_approval_creates_pending_proposal` (đề xuất `Chờ duyệt`, loại bản ghi, đủ trường 2.1, 1 comment có "Độ tin cậy: NN%", "Căn cứ", Duyệt, Sửa, Từ chối; Item không đổi); `::test_auto_mode_falls_back_to_proposal` (dòng `Tự làm` → vẫn đề xuất ở U7a) | — |
| AC-33 / AC-22 tham số | `TT::TestProposeFlow::test_missing_basis_or_bad_confidence_refused` (`basis` rỗng, `confidence_pct` -1, 101, `"70"`, `True` → `ok=false`, 0 comment) | biên 0 và 100 đạt |
| AC-33 comment (5) | `erp_ai/agent/tools/test_propose_change.py::TestRecordComment::test_links_follow_one_click_switch` ((5) tắt: không `decision_path`, có `OPEN_PROPOSAL_LABEL` và `erp_ai_edit=1`; bật: Duyệt · Sửa · Từ chối) ; `::test_values_escaped` (giá trị `<script>`) | HTML trong giá trị |
| AC-33 áp dụng một lần | `TA::TestApplyRecord::test_approve_applies_once` (duyệt → job → Item đổi, `Đã áp dụng`, `applied_values`, 1 dòng `apply` có 1 mục hành động trước/sau); `::test_job_twice_applies_once` (job lần hai `OUTCOME_SKIPPED`, 0 dòng mới) | — |
| AC-33 từ chối | `TP::TestRecordDecision::test_reject_writes_nothing` (đích không đổi, 1 dòng `reject`, 0 job) | — |
| AC-33 hết hiệu lực | `TA::TestApplyRecord::test_target_changed_is_stale` (đổi `item_group` sau đề xuất → `Hết hiệu lực`, đích giữ giá trị người đổi, 1 dòng `stale`); `::test_additive_precondition_met_is_stale` (người đã được thêm vào đội giữa chừng) | cả hai dạng canh |
| AC-33 kiểm lại lúc áp dụng | `TA::TestApplyRecord::test_rule_removed_before_job_fails` (xóa dòng danh mục → `Lỗi` `OUT_OF_CATALOG`, 0 thay đổi); `::test_unexpected_error_rolls_back_to_failed` (stub `execute` ném → `Lỗi`, đích không đổi, không kẹt `Đang áp dụng`) | — |
| AC-33 4 kết cục có comment (FEAT-004 AC-28) | `TA::TestApplyRecord::test_each_outcome_one_result_comment` (xong, lỗi, hết hiệu lực, hoàn tác → mỗi ca đúng 1 comment mới qua cơ chế AC-28) — **chỉ viết khi FEAT-004 AC-28 có mã** (1.3) | 4 ca |
| AC-33 hoàn tác | `TA::TestUndoRecord::test_undo_restores_before`; `::test_undo_refused_when_target_changed` (`Lỗi` `UNDO_TARGET_CHANGED`); `TR::TestRequestUndo::test_record_not_reversible_refused` (tạo tài khoản → `InvalidTransition`) | — |
| ADR-031 QĐ 9 | `TA::TestApplyRecord::test_record_applies_while_change_lock_held` (giữ `filelock(LOCK_NAME)` trong luồng test → đề xuất bản ghi vẫn `Đã áp dụng`, không `LOCK_BUSY`) | — |
| AC-34 sửa hợp lệ | `TP::TestApproveWithEdit::test_valid_edit_applies_edited_value` (đổi `item_group` sang nhóm khác trong danh mục → áp dụng giá trị sửa; `approved_with_edit=1`; dòng `approve` có `value_before`/`value_after` = lần sửa) | — |
| AC-34 sửa ra ngoài trường | `TP::TestApproveWithEdit::test_edit_field_outside_catalog_refused` (Đổi trường thêm khóa ngoài `fields` → `ValidationError` `EDIT_TARGET_LOCKED`, trạng thái `Chờ duyệt`, 0 dòng, 0 job) | — |
| AC-34 sửa sang DocType cấm | `TP::TestApproveWithEdit::test_edit_to_banned_doctype_refused` (đổi `doctype` sang DocType của app → từ chối, không ghi) | — |
| AC-34 kiểm lại thật (không chỉ khóa đích) | `::test_edit_rechecks_catalog_and_hard_bans` (mẫu tài khoản sửa sang mẫu có `System Manager` → `FORBIDDEN_ROLE`; Custom Field `options` Link sửa sang DocType của app → `HARD_BAN`; môi trường đổi sang production trước khi sửa → `TEST_SITE_ONLY`); `::test_identical_edit_refused`; `::test_bad_json_refused`; `::test_edit_on_code_kind_refused` | 3 đường kiểm |
| AC-34 dấu phủ giá trị sửa | `TA::TestApplyRecord::test_edited_args_changed_after_approval_fails` (`db.set_value` đổi `edited_args` sau duyệt → `Lỗi` `DIGEST_CHANGED`) | — |
| AC-35 5 vai × 2 loại | `TP::TestRecordDecision::test_eligibility_matrix` (Instructor; người được giao, ToDo mở, không vai trò; người tạo phiếu không giao; người có `Agent` không giao; tài khoản agent / Administrator / Guest) × (đề xuất bản ghi, đề xuất code) × (approve, reject, approve_with_edit chỉ bản ghi): được giao + code → `PermissionError`; trạng thái và số dòng nhật ký không đổi ở mọi ca bị từ chối | ToDo `Closed`/`Cancelled` = không được giao |
| AC-35 hàm vị từ | `TAU::TestCanDecide::test_by_kind` (cùng ma trận ở mức hàm); `::test_assigned_by_agent_counts_for_record` (A-U7a-3); `::test_is_instruction_unchanged` (hồi quy U1) | gán do bot |
| AC-35 mất điều kiện trước job | `TA::TestApplyRecord::test_assignment_closed_before_job_fails` (đóng ToDo → `Lỗi` `APPROVER_LOST_ROLE`, 0 thay đổi, 1 dòng `fail`); `::test_role_removed_before_job_fails`; `TA::TestUndoRecord::test_undo_by_loses_condition_fails`; `::test_wrong_session_user_fails` (`WRONG_RUNNER`) | cả áp dụng và hoàn tác |
| AC-35 không lộ tên | `TP::TestRecordDecision::test_unknown_name_non_instructor_permission_error` | — |
| AC-12 6 loại × 2 môi trường | `TT::TestSiteEnvironment::test_six_kinds_by_environment` (tạo Custom Field + Đổi trường trên Server Script, Client Script, Property Setter, Workflow, Data Import; dòng danh mục `Cần duyệt`; `production` → `ok=false` `TEST_SITE_ONLY`, 0 đề xuất, đúng 1 comment `TEST_SITE_COMMENT`; `test` → đề xuất được tạo. Loại nào `hard_ban_reason` trả lý do trên site (kiểm lúc chạy test) thì ca `test` khẳng định `HARD_BAN` — điều cấm cứng thắng môi trường) | 12 ca |
| AC-12 một comment mỗi lần chạy | `TT::TestSiteEnvironment::test_two_refusals_one_comment_per_run` (hai lời gọi cùng `run_id` → 1 comment; `run_id` khác → 2) | — |
| AC-12 kiểm ở bộ thực thi | `TA::TestApplyRecord::test_environment_switched_to_production_before_job_fails` (đề xuất Custom Field ở `test`, đổi sang `production`, chạy job → `Lỗi` `TEST_SITE_ONLY`, 0 Custom Field) | — |
| AC-12 không chặn 5 quyền | `erp_ai/agent/test_agent_runner.py::TestSiteEnvironmentGate::test_record_tools_not_gated_in_production` ((2) bật, `production`, `api_create_record` → ghi; dòng `reason` có `site_environment = "production"`); `erp_ai/agent/tools/test_propose_change.py::TestProposeChange::test_code_proposal_created_in_production` | — |
| ADR-031 Ràng buộc 1 | `TArch::TestCatalogArchitecture::test_one_proposal_doctype_three_kinds` (option `change_kind` = 3 giá trị theo hằng; đúng 1 DocType có trường `change_kind` trong module app) | — |
| ADR-031 Ràng buộc 2 | `TArch::TestCatalogArchitecture::test_executor_imports_and_no_ignore_permissions` (`catalog.py` không import `transitions`/`apply_job`, không có `ignore_permissions`); `::test_only_executor_writes_targets` (`catalog_tools.py`, `apply_job.py` nhánh bản ghi không gọi `.insert(`/`.save(`/`db.set_value`/`db.sql` ngoài `insert_proposal`, `new_comment`, `transitions`) | — |
| ADR-031 Ràng buộc 3 | `TC::TestExecute::test_write_runs_as_agent_and_restores_session` (trên); `TA::TestApplyRecord::test_finish_runs_under_decider_session` (stub `finish` ghi phiên = `decided_by`) | — |
| ADR-031 Ràng buộc 4 | `TArch::TestCatalogArchitecture::test_no_role_compare_for_decisions` (`ROLE_INSTRUCTOR` không xuất hiện trong controller đề xuất và `apply_job.py`) | — |
| ADR-031 Ràng buộc 5, 6 | `TArch::TestCatalogArchitecture::test_proposal_fields_snapshot` (tập trường JSON = ảnh chụp, không trường bộ đếm); `TP::TestERPAIChangeProposal::test_record_content_immutable` (đổi `action_args` rồi lưu → từ chối) | — |
| ADR-031 Ràng buộc 7 | `TArch::TestCatalogArchitecture::test_no_doctype_or_role_literal_in_catalog_modules` (mọi hằng chuỗi trong AST của `catalog.py`, `catalog_tools.py` ∉ tên DocType trên site ∪ `FORBIDDEN_ROLES`) | — |
| ADR-012 dấu code không đổi | `TR::TestTransitionsBasics::test_code_digest_unchanged_by_record_fields` (dấu của một đề xuất code cố định = giá trị ghim trước U7a) | — |
| Grant | `erp_ai/agent/tools/test_registry.py::TestGrantTable::test_catalog_row` (L1 → không; L2, L3 → có; dưới ngưỡng → không); ảnh chụp ma trận U1 cập nhật đúng một nhóm (lý do ghi commit, NFR-8) | biên L1/L2 |
| Policy | `erp_ai/agent/test_policy.py::TestCatalogRules::test_parse_rows` (categories bẩn, fields trống, mode lạ → Cấm, action lạ bỏ); `::test_user_template_roles_case_insensitive` | — |
| Migration | `TP::TestRecordKindMigration::test_columns_exist_after_migrate` (10 cột có trong `information_schema`); kiểm xuống: bước đối chiếu ở mục 6 chạy bằng `cmd.migrate` trên bản sao trước G5 (dán đầu ra ở As-Built, STD-OPS-2/3) | — |

### Đối chiếu AC (Done criteria)

- AC trong phạm vi U7a theo arch-impact hàng U7 ∩ lời gọi: **AC-12, AC-29, AC-30, AC-33, AC-34, AC-35**.
- AC có dòng test ở bảng trên: **AC-12** (5 dòng), **AC-29** (6), **AC-30** (8), **AC-33** (11), **AC-34** (5), **AC-35** (4). Khớp 6/6; mỗi AC có ca lỗi/biên.
- Phần AC-33 phụ thuộc FEAT-004 AC-28 (comment 4 kết cục) có dòng test nhưng đánh dấu điều kiện (1.3).

---

## Assumptions decided by the team

| # | Chọn | Vì | Phương án khác | Sai thì sửa |
|---|---|---|---|---|
| A-U7a-1 | "Giá trị trước" để kiểm hết hiệu lực là **giá trị canh** theo hành động: điều kiện tiên quyết (chưa là thành viên, chưa có ngày, chưa có tài khoản/trường) cho hành động thêm/tạo; giá trị hiện tại của trường cho hành động đổi | AC-30 (2), (3) đòi giữ tập cũ, không đòi tập cũ đứng yên; so cả danh sách làm mọi đề xuất thêm người hết hiệu lực khi ai đó thêm người khác | so ảnh chụp cả bảng con | đổi `handler.watched`, không đổi hợp đồng |
| A-U7a-2 | "Sửa" chỉ đổi giá trị: khóa đích và tập trường của Đổi trường bị khóa | AC-34 "đổi giá trị trong đề xuất"; đích là cơ sở kiểm hết hiệu lực | cho đổi đích rồi chỉ dựa vào kiểm lại | bỏ khóa trong `check_edit`, thêm tính lại `record_before` |
| A-U7a-3 | Người được giao duyệt được loại bản ghi dù việc gán do bot hay do chính họ làm (ToDo mở là đủ) | AC-35 (a) nguyên văn "việc gán còn mở"; ADR-031 Hệ quả đã chấp nhận rủi ro người do bot gán; định tuyến tự gán người phụ trách bằng tài khoản agent | loại gán do agent như `is_instruction` của U1 (người phụ trách do bot định tuyến sẽ không duyệt được) | thêm điều kiện `assigned_by` trong `is_assigned`; **câu không chặn cho team-leader/analyst**: tự gán rồi tự duyệt có chấp nhận không |
| A-U7a-4 | Tạo tài khoản giữ mặc định Frappe về email chào mừng | tool không nhận mật khẩu (AC-30 (1)); không email thì người dùng mới không đặt được mật khẩu | tắt email | thêm `send_welcome_email: 0` vào `write` |
| A-U7a-5 | Danh sách thuộc tính Custom Field cho phép và kiểu trường cho phép như 3.3 | AC-30 (5) đòi "danh sách cho phép"; ADR-031 giao designer tham số | danh sách rộng hơn | sửa hai tuple |
| A-U7a-6 | U7a: dòng `Tự làm` luôn tạo đề xuất | vị từ AC-36 là U7b; AC-33 cho rơi về `Cần duyệt` khi chưa đủ điều kiện | stub vị từ trả `False` | U7b thêm nhánh ở `_propose` bước 4 |
| A-U7a-7 | Đề xuất bản ghi áp dụng trong một giao dịch, không commit trạng thái `Đang áp dụng` trước | ADR-031 QĐ 9 "trong cùng giao dịch ghi"; worker chết thì quay về `Đã duyệt`, không kẹt | commit trước như loại code | — |
| A-U7a-8 | Comment "cần làm trên site test" tối đa 1 mỗi lần chạy | AC-12 "1 comment"; model có thể gọi lại tool | 1 mỗi lời gọi | đổi khóa nhớ |
