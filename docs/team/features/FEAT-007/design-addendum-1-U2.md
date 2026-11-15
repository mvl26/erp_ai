Feature: FEAT-007
Stage: design
Author-agent: designer
Date: 2026-11-14
Approved-by:
<!-- G2b không áp dụng (team.py: chỉ cổng G5). -->

# Design addendum 1 — U2 Bảo vệ dữ liệu (FEAT-007)

**Phạm vi.** Chỉ đơn vị U2 của `arch-impact.md:177`: AC-5 `[changed]` (vector phân quyền ở chế độ thường), AC-8 `[changed]` (đọc chéo qua công cụ bản ghi), AC-9 (phiếu chưa có nhóm thuộc bộ phận loại trừ). Văn bản AC lấy theo `spec-addendum-1.md` mục 2.1 (thắng `spec.md` khi khác); AC-9 không đổi nên lấy `spec.md:167`. Không thiết kế đơn vị nào khác. Tên của U1 dùng nguyên theo `design-addendum-1-U1.md` mục 3.9; tên của U0 theo `design.md:91-153`, D-13 (`design.md:71`), D-19 (`design.md:77`) và `design-w0-fixes.md` mục 3.

**Luật thi hành (trích, không chép):** ADR-034 QĐ 1 và Ràng buộc 1–2 (một vị từ phiếu loại trừ, lọc ở truy vấn); ADR-023 QĐ 3 (M3: một danh sách cấm dẫn xuất), QĐ 5 (M5, không đổi ở đây), QĐ 6 phương án (b) (người đã chọn: `api_call_method` gọi tự do, chặn ở mức cố gắng — `team/FEAT-004:tasks.md:131`); ADR-030/033 không bị U2 chạm.

---

## 1. Bối cảnh

### 1.1 Explore summary (đọc trực tiếp, 2026-11-14, `develop` @ `1918db2`, và nhánh task FEAT-004 bằng `git show`)

| Chỗ | Hiện trạng | U2 đổi |
|---|---|---|
| `erp_ai/agent/policy.py:27-48` | `can_send_ticket` = ¬`ai_opt_out` ∧ ¬`is_excluded_team(agent_group)`; nhóm trống ⇒ gửi được | thêm tiền tố tiêu đề (AC-9 a) và "bị loại bởi phân loại" khi chưa có nhóm (AC-9 b); thêm dạng truy vấn của **cùng** vị từ (ADR-034 QĐ 1) |
| `policy.py:11-14` | `SEND_POLICY_FIELDS = (ai_opt_out, agent_group)` | thêm `subject` |
| `erp_ai/agent/tools/site_api.py:243-255` (develop) / `:375` (task-62) | `get_record` không gọi vị từ phiếu — **lỗ A5-3c** | từ chối bản ghi thuộc phiếu loại trừ |
| `site_api.py:273-300` (develop) / `:405` (task-62) | `list_records` gọi `frappe.get_list` không lọc phiếu — **lỗ A5-3c** | thêm điều kiện loại trừ vào chính truy vấn (trước `limit`) |
| `site_api.py:26` (task-59..62) | `PERMISSION_DOCTYPES = {"Custom Role", "Custom DocPerm", "DocType", "Role"}`; `_denied_doctypes(ctx)` (`:85`) chế độ thường = `read.denied_doctypes() − {User}` ∪ tập này; so tên `casefold` (`_named_in`, `:99`) | thêm `User Permission`, `DocShare` (AC-5); thêm chốt mức giá trị cho Property Setter `permlevel` |
| `site_api.py:150` (task-62) `_values_refusal` | chặn trường hệ thống, trường mật, 6 vai trò | không đổi; chốt `permlevel` là hàm riêng |
| T62 `value_before`/`value_after`, `_deleted_values` (task-62 `:169-190`) | kết quả ghi trả giá trị trước/sau của bản ghi | là đường lộ thứ hai cho phiếu loại trừ → ghi lên bản ghi của phiếu loại trừ bị từ chối (mục 3.3) |
| `erp_ai/agent/runner.py:141` | chốt (c) `can_send_ticket` lúc chạy | không đổi dòng; hưởng vị từ mở rộng |
| `runner.py:248-323` `_classify` | `decide_route(..., is_excluded_team=policy.is_excluded_team)` (`:281-289`); routing chỉ **bỏ ghi** nhóm loại trừ (`routing.py:93-94`), rồi `_reason` vẫn chạy với tới 30 comment — **lỗ A5-3a (1)** | dừng sau dòng `classify`, không `_route`, không `_reason` |
| `erp_ai/handlers.py:38`, `:113` | chốt lúc xếp hàng bằng `can_send_ticket`, lý do log `not_sendable` | ghi mã lý do cụ thể vào dòng logger |
| `erp_ai/agent/tools/read.py:51-59`, `:132`, `:165` | tool đọc đã gọi `can_send_ticket` | **không sửa** (ngoài file của U2); tự hưởng vị từ mở rộng |
| `erp_ai/eval/export_tickets.py:31` | gọi `can_send_ticket` | không sửa; tự hưởng |
| Helpdesk `hd_ticket_comment.json` | ghi chú nội bộ của agent nằm ở `HD Ticket Comment`, trường `reference_ticket` | phủ cùng 4 DocType của AC-8 (D-13) |
| ERP AI Log `stop_reason` | `Data` (không phải Select) | giá trị mới `excluded_by_classification`, không cần đổi schema |

### 1.2 Code FEAT-004 mà U2 dựa vào

| Thứ U2 dựa vào | Task FEAT-004 | Có trên `develop` hôm nay? |
|---|---|---|
| `site_api.PERMISSION_DOCTYPES`, `_denied_doctypes(ctx)`, `always_denied_doctypes()`, `_named_in` (so `casefold`), `_stored_name` | T59 | **Không.** `team/FEAT-004-task-59-r2` @ `95fd547`; không là tổ tiên của `team/FEAT-004`; `tasks.md:635` `[ ]` (review vòng 2 đang xếp, round 69) |
| `_write` rollback về `SAVEPOINT` mọi lỗi (AC-5 "dữ liệu không đổi") | T60 | **Không.** `team/FEAT-004-task-60` @ `7b55147` (approve round 68), chưa merge; `tasks.md:641` `[ ]` |
| `SECRET_METHODS`, `_scrub` của `call_method` (U2 không gọi; chỉ là mắt xích chuỗi file) | T61 | **Không.** `team/FEAT-004-task-61` @ `5130c88`; `tasks.md:647` `[ ]` |
| `value_before`/`value_after`, `_shown`, `_deleted_values` | T62 | **Không.** `team/FEAT-004-task-62` @ `337ccd8` (xếp chồng trên T61), chưa review; `tasks.md:653` `[ ]` |
| Mục hành động `ok=false` kèm lý do cho mỗi lời gọi công cụ bản ghi (AC-5 "1 mục nhật ký"; runner `_action`) | T64 | **Không.** `tasks.md:665` `[ ]`, depends T62, T63 |
| Luật kiến trúc ADR-023 trong `test_architecture.py` (U2 thêm luật ADR-034 cùng file) | T68 | **Không.** `tasks.md:689` `[ ]` |
| `policy.can_send_ticket`, `policy.is_excluded_team`, `policy._normalize`, `read.denied_doctypes()`, `authority.ticket_comment_filters`, `site_api.get_record`/`list_records`/`_fail`, `ToolContext.unrestricted` | FEAT-001/006; `6d90e79` (mã nhận vào FEAT-004) | **Có** (`policy.py:23-48`, `read.py:141`, `authority.py:18`, `site_api.py:54`, `:243`, `:273`) |

**Điều kiện bắt đầu U2** (arch-impact "Sau FEAT-004, sau U1"): T59–T62, T64, T68 đã vào `develop`, rồi `develop` merge vào `team/FEAT-007`, và U1 đã merge. Cắt trước T59–T62 thì dev U2 sửa `site_api.py` song song chuỗi T59→T62 (xung đột chắc chắn) → `DESIGN_CONFLICT`, dừng.

### 1.3 Cần từ U0 (không tự đặt)

| Cần | Có trong schema U0? |
|---|---|
| `excluded_title_prefixes` (Small Text, mỗi dòng một tiền tố, mặc định `[HR]\n[Kế toán]`) trên ERP AI Setting | Có (`design.md:126`, D-19) |
| `TICKET_CONTENT_DOCTYPES = ("HD Ticket", "HD Ticket Comment", "Comment", "Communication", "File")` | Có (D-13; chuyển về `erp_ai/constants.py`, `design-w0-fixes.md:189`) |
| Option mới của ERP AI Log | Không cần: `stop_reason` là `Data` |

Không có trường nào thiếu trong schema U0.

### 1.4 Cần từ U1

| Cần | Ghi chú |
|---|---|
| `runner._classify` theo dạng sau U1 (thay context, chốt dưới ngưỡng trước `_route`, `design-addendum-1-U1.md` 3.7) | U2 chèn chốt "bị loại bởi phân loại" **trước** chốt dưới ngưỡng của U1; cùng hàm, phải cắt sau U1 |
| `grant`, `GrantInputs`, `PermissionSwitches`, `ToolContext.grant_inputs` (U1 3.9; U2 là "đơn vị gọi" trong bảng đó) | chỉ test dùng, để khẳng định công cụ bản ghi được cấp trong ca AC-8 |

---

## 2. Mô hình dữ liệu

U2 **không thêm, không đổi** trường hay DocType nào. Không có migration.

| Đọc | Ở đâu | Mẫu truy cập |
|---|---|---|
| `excluded_teams`, `excluded_title_prefixes` | ERP AI Setting (Single), chỉ trong `policy.py` | `frappe.db.get_single_value` (cache của Frappe) |
| `ai_opt_out`, `agent_group`, `subject` của phiếu | HD Ticket | một `get_value` theo tên (vị từ từng phiếu); một `get_all` có `or_filters` (dạng truy vấn) |
| Tên HD Team | HD Team | `get_all(pluck="name")` để quy tên nhóm loại trừ đã chuẩn hóa về tên thật (vài chục dòng) |
| Phiếu bị loại bởi phân loại | ERP AI Log `entry_type="classify"`, `stop_reason="excluded_by_classification"` | lọc theo `stop_reason` (vài trăm dòng/tháng, không cần chỉ mục) |
| Liên kết bản ghi → phiếu | `Comment.reference_doctype/reference_name`, `Communication.reference_doctype/reference_name`, `File.attached_to_doctype/attached_to_name`, `HD Ticket Comment.reference_ticket` | lọc `not in` trên cột liên kết |

**Ghi duy nhất:** runner ghi `stop_reason = "excluded_by_classification"` lên dòng `classify` của chính lần phân loại (dòng đã được ghi như nay, `runner.py:296-318`). Không ghi gì vào HD Ticket.

---

## 3. API / hợp đồng

Mọi hàm là Python nội bộ; không endpoint, không whitelisted method mới. Hợp đồng ra model của công cụ bản ghi chỉ **thêm**: một khóa `excluded_note` cố định trong kết quả liệt kê của 5 DocType mang nội dung phiếu, và lý do từ chối mới. Không bỏ khóa nào.

### 3.1 `policy.py` — một vị từ, hai dạng (ADR-034 QĐ 1)

```python
EXCLUDED_TITLE_PREFIXES_FIELD = "excluded_title_prefixes"
SUBJECT_FIELD = "subject"
SEND_POLICY_FIELDS = (OPT_OUT_FIELD, TEAM_FIELD, SUBJECT_FIELD)
EXCLUDED_BY_CLASSIFICATION = "excluded_by_classification"     # giá trị stop_reason
# Lý do gửi lại (mã, không chứa nội dung phiếu)
REFUSAL_OPTED_OUT = "opted_out"
REFUSAL_EXCLUDED_TEAM = "excluded_team"
REFUSAL_EXCLUDED_TITLE = "excluded_title"
REFUSAL_EXCLUDED_BY_CLASSIFICATION = "excluded_by_classification"
REFUSAL_MISSING = "missing"
EXCLUDED_TICKET_REASON = "bản ghi thuộc phiếu không được phép đưa cho AI"   # cùng chữ read.py:166
# DocType mang nội dung phiếu (trừ HD Ticket) -> (cột loại tham chiếu hoặc None, cột tên phiếu)
TICKET_LINK_FIELDS = {
    "Comment": ("reference_doctype", "reference_name"),
    "Communication": ("reference_doctype", "reference_name"),
    "File": ("attached_to_doctype", "attached_to_name"),
    "HD Ticket Comment": (None, "reference_ticket"),
}

def excluded_title_prefixes() -> tuple[str, ...]
def has_excluded_title(subject) -> bool
def excluded_team_names() -> list[str]
def is_excluded_by_classification(ticket_name: str) -> bool
def send_refusal(ticket) -> str | None
def can_send_ticket(ticket) -> bool                     # giữ chữ ký
def excluded_ticket_names() -> list
def ticket_content_filters(doctype: str) -> tuple[list, list]
def owning_ticket(doctype: str, name: str) -> str | None
def is_ticket_record_excluded(doctype: str, name: str) -> bool
```

| Hàm | Hành vi chính xác | Lỗi |
|---|---|---|
| `excluded_title_prefixes` | đọc `excluded_title_prefixes`; mỗi dòng → `_title_key(line)`; bỏ dòng rỗng; trường thiếu (trước migrate) → `()` | không ném |
| `_title_key(text)` (riêng) | `unicodedata.normalize("NFC", text or "")` rồi `_normalize` (gộp khoảng trắng, `casefold`) | — |
| `has_excluded_title` | `any(_title_key(subject).startswith(p) for p in excluded_title_prefixes())`. Chỉ đầu tiêu đề: `"Hỏi về [HR]"` → False; `"  [hr]  Nghỉ phép"` → True | — |
| `excluded_team_names` | tên HD Team thật có `_normalize(name)` ∈ tập `excluded_teams` đã chuẩn hóa — **cùng** phép so của `is_excluded_team` | — |
| `is_excluded_by_classification` | tồn tại dòng ERP AI Log `ticket=<tên>`, `entry_type="classify"`, `stop_reason=EXCLUDED_BY_CLASSIFICATION` | — |
| `send_refusal` (**vị từ duy nhất**) | nhận tên hoặc doc như `can_send_ticket` hôm nay. Theo thứ tự: không có phiếu → `REFUSAL_MISSING`; `ai_opt_out` → `REFUSAL_OPTED_OUT`; `is_excluded_team(agent_group)` → `REFUSAL_EXCLUDED_TEAM`; `has_excluded_title(subject)` → `REFUSAL_EXCLUDED_TITLE` (có nhóm hay không: tiền tố là ý của người tạo); `agent_group` trống ∧ doc đã lưu ∧ `is_excluded_by_classification(name)` → `REFUSAL_EXCLUDED_BY_CLASSIFICATION`; ngược lại `None` | — |
| `can_send_ticket` | `send_refusal(ticket) is None` (thân cũ thành `send_refusal`; mọi người gọi giữ nguyên) | — |
| `excluded_ticket_names` (dạng truy vấn) | (1) ứng viên = `frappe.get_all("HD Ticket", or_filters=[[ai_opt_out, "=", 1], [agent_group, "in", excluded_team_names()]*, [subject, "like", "%<lõi tiền tố>%"]* , [name, "in", <phiếu có dòng EXCLUDED_BY_CLASSIFICATION>]*], fields=[name, ai_opt_out, agent_group, subject])` (* chỉ khi tập khác rỗng; "lõi" = tiền tố bỏ khoảng trắng đầu/cuối, thoát `\ % _` như `read._like_pattern`); (2) giữ dòng có `send_refusal(row)` khác `None`. Bước (1) là tập cha, bước (2) là đúng vị từ trên → hai dạng không lệch nhau. Không ứng viên → `[]` | lỗi DB nổi lên (người gọi là tool, runner bắt như nay) |
| `ticket_content_filters` | `doctype ∉ TICKET_CONTENT_DOCTYPES` hoặc `excluded_ticket_names()` rỗng → `([], [])`. `HD Ticket` → `([["name", "not in", names]], [])`. Có cột loại → `([], [[type_col, "!=", "HD Ticket"], [name_col, "not in", names]])` (nghĩa: ¬(loại = HD Ticket ∧ tên ∈ names)). `HD Ticket Comment` → `([["reference_ticket", "not in", names]], [])` | — |
| `owning_ticket` | `HD Ticket` → `name`; DocType trong `TICKET_LINK_FIELDS`: đọc hai cột; cột loại khác `"HD Ticket"` → `None`; ngược lại tên phiếu; DocType khác → `None` | bản ghi không có → `None` |
| `is_ticket_record_excluded` | `t = owning_ticket(...)`; `t is not None and not can_send_ticket(t)` | — |

`TICKET_LINK_FIELDS` phải phủ đúng `set(TICKET_CONTENT_DOCTYPES) − {"HD Ticket"}` (test kiến trúc mục 8). Tên `excluded_teams`, `ai_opt_out`, `excluded_title_prefixes` chỉ được đọc trong `policy.py` (ADR-034 Ràng buộc 1).

### 3.2 `site_api.py` — đọc (AC-8; lỗ A5-3c)

Áp ở **mọi** chế độ (`ctx.unrestricted` đúng hay sai):

- `get_record`: sau `_doctype_refusal` và kiểm tồn tại, trước `has_permission`: `if policy.is_ticket_record_excluded(doctype, name): return _fail(policy.EXCLUDED_TICKET_REASON, doctype)`.
- `list_records`: sau khi kiểm `fields`/`filters` của model: `extra, or_filters = policy.ticket_content_filters(doctype)`; `frappe.get_list(doctype, filters=[*filters, *extra], or_filters=or_filters, fields=..., limit_page_length=..., order_by=...)`. Điều kiện nằm trong truy vấn nên `limit` và thứ tự không lộ phiếu loại trừ (ADR-034 Ràng buộc 2). Với `doctype ∈ TICKET_CONTENT_DOCTYPES`, kết quả thêm `"excluded_note": EXCLUDED_LIST_NOTE` (hằng mới: `"Phiếu nhóm loại trừ, phiếu không dùng AI và mọi bản ghi của chúng không bao giờ có trong danh sách."`) — **luôn** có, kể cả khi không phiếu nào bị lọc, để vừa có "lý do" (AC-8) vừa không lộ sự tồn tại.
- `list_records` không nhận `or_filters` từ model (schema giữ), nên nhóm OR duy nhất là của vị từ.

### 3.3 `site_api.py` — ghi lên bản ghi của phiếu loại trừ

T62 làm kết quả ghi mang `value_before` (sửa) và các trường của bản ghi (xóa): đó là đầu ra tool, thuộc NFR-1. Ở mọi chế độ:

- `update_record`, `delete_record`, `submit_record`: sau `_doctype_refusal`/kiểm tồn tại, `is_ticket_record_excluded(doctype, name)` → `_fail(EXCLUDED_TICKET_REASON, doctype)`.
- `create_record`: `doctype ∈ TICKET_LINK_FIELDS` và giá trị liên kết trong `values` trỏ tới phiếu có `can_send_ticket` sai → cùng lời từ chối (A-U2-3).
- `call_method`: **không** thay đổi; theo ADR-023 QĐ 6 (b) đường này không được bảo đảm (mục 5).

### 3.4 `site_api.py` — vector phân quyền ở chế độ thường (AC-5)

- `PERMISSION_DOCTYPES` (của T59) thêm `"User Permission"`, `"DocShare"`. Không lập tập thứ hai: tập này vào `_denied_doctypes(ctx)` (chế độ thường) và `hard_bans.PERMISSION_SET` của U0 (INT-1, `design-w0-fixes.md:209`), nên danh mục trắng cũng cấm.
- Hằng `PROPERTY_SETTER_DOCTYPE = "Property Setter"`, `PERMLEVEL_PROPERTY = "permlevel"`, `PERMLEVEL_REASON = "Property Setter đổi permlevel là sửa phân quyền, không làm qua công cụ"`.
- `_permlevel_refusal(doctype, name, values, ctx) -> dict | None`: `ctx.unrestricted` → `None`; `doctype` khác Property Setter (so `_named_in`) → `None`; `str(values.get("property", "")).strip().casefold() == PERMLEVEL_PROPERTY` → từ chối; với `update_record`, thêm: thuộc tính đã lưu `frappe.db.get_value(PROPERTY_SETTER_DOCTYPE, name, "property")` là `permlevel` → từ chối. Gọi trong `create_record` (`name=None`) và `update_record` ngay sau `_values_refusal`.
- Ba vector đã có chủ (Custom DocPerm, Role, DocType: T59) chỉ được ghim lại trong cùng test (AC-5 "chống thụt lùi").
- **Không** cấm `Has Role`, `Role Profile`, ghi `roles` của User: vai trò nghiệp vụ vẫn gán được; 6 vai trò cấm của `FORBIDDEN_ROLES` giữ (AC-5 `[changed]`).

### 3.5 `runner.py` — dừng sau phân loại khi phiếu thuộc bộ phận loại trừ (AC-9 b; lỗ A5-3a (1))

Trong `_classify`, sau `parse_classification` hợp lệ:

1. Dò nhóm loại trừ mà không sửa `routing.py`: truyền cho `decide_route` hàm bọc `excluded_probe(team)` = `policy.is_excluded_team(team)` và ghi lại lần trả `True`. `excluded = probe_hit or policy.is_excluded_team(classification.department)` (bộ phận được đặt trùng tên nhóm loại trừ).
2. `excluded` đúng: ghi dòng `classify` như nay với `applied=0`, `stop_reason=policy.EXCLUDED_BY_CLASSIFICATION`, các cột dự đoán giữ (cho báo cáo độ đúng); **không** `_route`, **không** comment; trả `(False, None)` để `_run` không gọi `_reason`. Mức L0 (context `None`) cũng ghi `stop_reason` này.
3. Chốt này đứng **trước** chốt dưới ngưỡng của U1 (bị loại trừ thắng dưới ngưỡng).

Từ đó `send_refusal` trả `REFUSAL_EXCLUDED_BY_CLASSIFICATION` cho tới khi một người đặt nhóm cho phiếu (A-U2-2): `@ai` bị chặn ở `handlers.py:113` và `runner.py:141`; quét 15' của U4a bị chặn vì nó gọi `can_send_ticket` (`design.md:375`).

### 3.6 `handlers.py` — mã lý do

`ticket_after_insert` và `comment_after_insert` dùng `refusal = policy.send_refusal(...)` thay `not policy.can_send_ticket(...)`; dòng logger có `skip_reason = f"not_sendable:{refusal}"` (chỉ mã, không nội dung, như `_log_decision` hiện nay). Thứ tự chốt không đổi.

### 3.7 Lỗi — một dạng

Mọi từ chối của công cụ bản ghi là `_fail(reason, doctype)` = `{"ok": False, "reason": ..., "doctype": ...}` (có sẵn). Lý do mới: `EXCLUDED_TICKET_REASON`, `PERMLEVEL_REASON`; DocType cấm dùng lý do có sẵn của T59. Runner không ném lỗi mới; `send_refusal` không ném.

### 3.8 Contract for later units

| Tên | Chữ ký / giá trị | Module | Đơn vị gọi |
|---|---|---|---|
| `send_refusal` | `(ticket) -> str \| None` — vị từ duy nhất | `erp_ai/agent/policy.py` | U3 (mục nhật ký bỏ qua), U5a/U5b (báo cáo 08:00, nhắc hạn: chỉ đếm), U6b |
| `can_send_ticket` | `(ticket) -> bool` (giữ) | `policy.py` | U4a (quét), U5a, U5b, U6b (trả lời AC-40, soạn CSKT AC-45, phiếu cũ AC-48) |
| `excluded_ticket_names` | `() -> list` | `policy.py` | U5a (rà soát tháng AC-59), U6b (tìm phiếu cũ lọc ở truy vấn) |
| `ticket_content_filters` | `(doctype) -> (filters, or_filters)` | `policy.py` | U6b (báo cáo, tìm phiếu cũ) |
| `is_ticket_record_excluded`, `owning_ticket` | mục 3.1 | `policy.py` | U6b |
| `has_excluded_title` | `(subject) -> bool` | `policy.py` | U5a (dòng email chỉ số phiếu) |
| `EXCLUDED_BY_CLASSIFICATION`, `REFUSAL_*`, `EXCLUDED_TICKET_REASON`, `TICKET_LINK_FIELDS` | mục 3.1 | `policy.py` | U4a (bỏ qua khi đếm "chưa phân loại"), U3, U6b |
| `PERMISSION_DOCTYPES` (+ `User Permission`, `DocShare`) | frozenset | `erp_ai/agent/tools/site_api.py` | U0 `hard_bans` (INT-1), U7 |

---

## 4. Luồng

**Phiếu mới có tiền tố (AC-9 a).** `HD Ticket.after_insert` → `send_refusal(doc)` = `excluded_title` → logger `skipped not_sendable:excluded_title` → không xếp job → 0 lời gọi model. Nếu job vẫn chạy (xếp trước khi cấu hình đổi): `runner.py:141` → dòng `skip` `not_sendable`.

**Phiếu mới chưa nhóm, phân loại ra bộ phận loại trừ (AC-9 b).** handler xếp job (chưa biết) → runner → 1 lời gọi `classify` → `decide_route` với hàm dò → trúng → dòng `classify` `applied=0`, `stop_reason=excluded_by_classification` → hết lần chạy. `@ai` sau đó: handler `not_sendable:excluded_by_classification`, 0 job. Quét: bỏ qua.

**Model liệt kê Comment (AC-8).** `execute_tool(api_list_records)` (cấp bởi U1) → kiểm DocType, trường, filters → `ticket_content_filters("Comment")` (1 `get_all` ứng viên HD Ticket + 1 đọc ERP AI Log + 1 đọc HD Team) → `get_list` có điều kiện → kết quả + `excluded_note`.

**Model đọc theo tên.** `api_get_record("Communication", X)` → `owning_ticket` → `can_send_ticket` sai → `ok=false`, `EXCLUDED_TICKET_REASON`; mục hành động `ok=false` (T64).

**Lỗi.**

| Tình huống | Kết quả |
|---|---|
| `excluded_title_prefixes` chưa có (site chưa migrate U0) | `()` → chỉ hai luật cũ (như hôm nay) |
| `excluded_teams` có tên không trùng HD Team nào | không vào `excluded_team_names()`; `is_excluded_team` cũng không khớp phiếu nào → nhất quán |
| Comment không có `reference_doctype` | `!=` của Frappe dùng `ifnull` → vẫn được liệt kê (test riêng) |
| Lỗi DB trong `excluded_ticket_names` | ném lên; `execute_tool`/runner bắt như nay, không trả danh sách chưa lọc |
| Phiếu bị xóa trước khi đọc | `owning_ticket` trả tên, `send_refusal` → `missing` → từ chối (fail-closed) |

Không có lời gọi ra ngoài mới (chỉ DB local); lời gọi model giữ timeout của gateway.

---

## 5. Quyền

- Vị từ phiếu loại trừ là chốt server cho mọi đường của công cụ bản ghi, ở cả chế độ thường và Toàn quyền, độc lập với phân quyền Frappe (tài khoản agent là System Manager trên `miyano`, ADR-023 Bối cảnh, nên phân quyền không lọc gì).
- **Không bảo đảm:** `api_call_method` (Toàn quyền) — ví dụ `frappe.client.get_list("HD Ticket")`, `frappe.client.get_count` — theo ADR-023 QĐ 6 (b) do người chọn (`team/FEAT-004:tasks.md:131`). AC-8 nhánh (b): rủi ro nằm ở mô tả `unrestricted_enabled` của U0 (`design.md:159`: "không đọc phiếu nhóm loại trừ qua gọi hàm chỉ là cố gắng"), thông báo bật (AC-4, U3) và As-Built. U2 không thêm allowlist.
- AC-5 chỉ áp khi Toàn quyền tắt; khi bật, `_denied_doctypes` là `always_denied_doctypes()` (T59) và `_permlevel_refusal` trả `None` — đúng N-1.
- Ranh giới ghi DocType của app vẫn là M5 (T65–T67), không đổi.

---

## 6. Migration và rollback, quan sát

- **Schema / dữ liệu:** không. Dòng `classify` cũ không có `stop_reason=excluded_by_classification` → phiếu cũ không bị loại hồi tố bởi luật (b) (A-U2-4); luật tiền tố áp ngay cho phiếu cũ.
- **Rollback:** revert commit của U2; không `cmd.migrate`. Dòng log đã ghi `excluded_by_classification` vô hại với mã cũ (`stop_reason` là Data tự do).
- **Đối chiếu sau deploy:** `len(policy.excluded_ticket_names())` so với đếm tay trên Desk (lọc HD Ticket theo `ai_opt_out=1` ∪ nhóm loại trừ ∪ tiêu đề bắt đầu bằng tiền tố) — dán vào `acceptance.md`.
- **Log/metric cho đường mới (STD-OPS-5):** chặn lúc xếp hàng → logger `not_sendable:<mã>`; chặn lúc chạy → dòng `skip` (có sẵn); loại bởi phân loại → dòng `classify` có `stop_reason=excluded_by_classification` (đếm được bằng Report View); từ chối của công cụ bản ghi → mục hành động `ok=false` + lý do (T64). Không log nội dung phiếu (STD-SEC-6).

---

## 7. Touchpoints

Nguồn — đều trong ô "Module, file chạm" của U2 (`arch-impact.md:177`: `site_api.py`, `policy.py`, `handlers.py`, `runner.py`):

| File | Sửa |
|---|---|
| `erp_ai/agent/policy.py` | 3.1 |
| `erp_ai/agent/tools/site_api.py` | 3.2, 3.3, 3.4 |
| `erp_ai/agent/runner.py` | 3.5 (`_classify` và hàm dò cục bộ) |
| `erp_ai/handlers.py` | 3.6 |

Không sửa `erp_ai/agent/tools/read.py`, `erp_ai/agent/routing.py`, `erp_ai/eval/export_tickets.py` (hưởng vị từ qua `can_send_ticket`).

Test (`structure.tests = colocated`):

| File | Trạng thái |
|---|---|
| `erp_ai/agent/test_policy.py` | thêm |
| `erp_ai/agent/tools/test_site_api.py` | thêm |
| `erp_ai/agent/test_agent_runner.py` | thêm |
| `erp_ai/tests/test_handlers.py` | thêm; sửa ca so chuỗi `not_sendable` chính xác (nếu có) sang tiền tố, lý do NFR-8 ghi ở commit |
| `erp_ai/tests/test_architecture.py` | thêm luật ADR-034 Ràng buộc 1–2; `POLICY_FIELDS` thêm `excluded_title_prefixes` |

**So khớp đường dẫn mới với `allowed_new_file_roots` và `protected_paths`:**

```
new: (không có file mới)
allowed_new_file_roots = ["erp_ai", "docs", ".github"]
protected_paths = [".env", ".env.*", "**/*.pem", "**/*.key", "license.txt"]
modified (4 nguồn + 5 test, đều dưới erp_ai/): không file nào khớp protected_paths
```

---

## 8. Test plan

Chạy mỗi file bằng `cmd.test_one`, cả app bằng `cmd.test`. Stub cổng model, không mạng (STD-TEST-6). Mỗi lớp test tự tạo HD Team, phiếu, comment, Communication, File, đặt `excluded_teams`/`excluded_title_prefixes` và trả lại trong `tearDown`. Chuỗi gieo `U2-SEED-<uuid>` trong tiêu đề, mô tả, nội dung comment/email, tên file của phiếu loại trừ; khẳng định bằng "chuỗi gieo xuất hiện 0 lần trong `json.dumps(kết quả)`".

| AC | Test (`file::name`) | Ca biên / lỗi |
|---|---|---|
| AC-8 | `erp_ai/agent/tools/test_site_api.py::TestExcludedTicketReads::test_list_hides_excluded_rows_in_both_modes` | **lỗ A5-3c (liệt kê).** 5 DocType (`TICKET_CONTENT_DOCTYPES`) × {nhóm loại trừ, cờ không dùng AI, tiêu đề tiền tố, bị loại bởi phân loại, phiếu thường} × `ctx.unrestricted` ∈ {False, True}: dòng của 4 loại đầu vắng, chuỗi gieo 0 lần; phiếu thường có |
| AC-8 | `…test_site_api.py::TestExcludedTicketReads::test_get_refuses_excluded_record_in_both_modes` | **lỗ A5-3c (đọc theo tên).** cùng ma trận: `ok=false`, `reason == policy.EXCLUDED_TICKET_REASON`, chuỗi gieo 0 lần; phiếu thường `ok=true` |
| AC-8 | `…test_site_api.py::TestExcludedTicketReads::test_list_result_identical_when_excluded_ticket_added` | ADR-034 Ràng buộc 2: `limit=2`, `order_by modified desc`; kết quả trước == sau khi thêm phiếu loại trừ mới nhất có 3 comment |
| AC-8 | `…test_site_api.py::TestExcludedTicketReads::test_name_filter_on_excluded_ticket_returns_zero_rows_with_note` | filter `["reference_name", "=", <phiếu loại trừ>]` → `records == []`, `excluded_note` có |
| AC-8 | `…test_site_api.py::TestExcludedTicketReads::test_excluded_note_present_even_with_nothing_excluded` | tập loại trừ rỗng → note vẫn có; DocType ngoài tập (ví dụ `ToDo`) → không có note |
| AC-8 | `…test_site_api.py::TestExcludedTicketReads::test_comment_without_reference_still_listed` | `reference_doctype` NULL; Comment của DocType khác có `reference_name` trùng số phiếu loại trừ → vẫn liệt kê |
| AC-8 | `…test_site_api.py::TestExcludedTicketWrites::test_update_delete_submit_refused_on_excluded_records` | `value_before`/trường bản ghi (T62) không lộ: `ok=false`, chuỗi gieo 0 lần, bản ghi không đổi |
| AC-8 | `…test_site_api.py::TestExcludedTicketWrites::test_create_linked_to_excluded_ticket_refused` | Comment `reference_name` = phiếu loại trừ → `ok=false`, số Comment không đổi; phiếu thường → `ok=true` |
| AC-8 | `…test_site_api.py::TestExcludedTicketReads::test_record_tools_granted_when_switch_on` | `grant(GrantInputs(L3, …, record_tools=True, has_instructor=True))` có `api_list_records`, `api_get_record` (U1) — ca "khi công cụ bản ghi bật" |
| AC-8 | `erp_ai/agent/test_policy.py::TestExcludedQuery::test_query_form_matches_predicate` | 8 phiếu (mỗi luật + kết hợp + thường, tiêu đề có khoảng trắng đầu, chữ hoa, `%`/`_` trong tiền tố): `set(excluded_ticket_names()) == {t : not can_send_ticket(t)}` |
| AC-8 | `…test_policy.py::TestExcludedQuery::test_owning_ticket_per_doctype` | 5 DocType; File đính kèm DocType khác → `None`; bản ghi không có → `None` |
| AC-8 | `…test_policy.py::TestExcludedQuery::test_ticket_content_filters_empty_when_nothing_excluded` | `([], [])`; DocType ngoài tập → `([], [])` |
| AC-8 | `erp_ai/tests/test_architecture.py::test_ticket_policy_fields_read_only_in_policy` | grep `excluded_teams`, `ai_opt_out`, `excluded_title_prefixes` trong `erp_ai/**/*.py` ngoài `policy.py`, JSON, controller Setting, `install.py`, test → finding (ADR-034 Ràng buộc 1) |
| AC-8 | `…test_architecture.py::test_site_api_read_paths_call_ticket_policy` | AST: `get_record` gọi `policy.is_ticket_record_excluded`; `list_records` gọi `policy.ticket_content_filters` và truyền kết quả vào `frappe.get_list` (không lọc sau) |
| AC-8 | `…test_architecture.py::test_ticket_link_fields_cover_ticket_content_doctypes` | `set(TICKET_LINK_FIELDS) | {"HD Ticket"} == set(TICKET_CONTENT_DOCTYPES)` |
| AC-9 (a) | `erp_ai/agent/test_policy.py::TestTitlePrefix::test_prefix_boundaries` | `"[HR] X"`, `"  [hr]   X"`, `"[Kế toán]X"` (NFC và NFD) → loại; `"Hỏi về [HR]"`, `"[HRM] X"` khi tiền tố `[HR]`... **lưu ý:** `"[HRM]"` không bắt đầu bằng `"[hr]"` → không loại; dòng rỗng trong cấu hình bỏ qua; trường thiếu → không luật |
| AC-9 (a) | `erp_ai/tests/test_handlers.py::TestExcludedTitle::test_prefixed_ticket_not_enqueued_and_logged_once` | stub `enqueue_agent_run` đếm 0; đúng 1 dòng logger `not_sendable:excluded_title` |
| AC-9 (a) | `erp_ai/agent/test_agent_runner.py::TestExcludedTitle::test_prefixed_ticket_calls_model_zero_times` | chạy `run_for_ticket` trực tiếp: stub cổng model đếm 0; 1 dòng `skip` `not_sendable` |
| AC-9 (b) | `…test_agent_runner.py::TestExcludedByClassification::test_classified_into_excluded_team_stops_before_reasoning` | **lỗ A5-3a.** phiếu chưa nhóm, stub phân loại trả bộ phận ánh xạ tới nhóm loại trừ, 3 comment có chuỗi gieo: lời gọi model = 1 (chỉ `classify`), payload lời gọi đó không chứa comment; 0 ghi phiếu (`modified` không đổi), 0 comment, 0 Task, 0 dòng `reason`; dòng `classify` `applied=0`, `stop_reason=excluded_by_classification` |
| AC-9 (b) | `…test_agent_runner.py::TestExcludedByClassification::test_later_mention_and_scan_skip` | sau ca trên: `comment_after_insert` với `@ai` → 0 job; `run_for_ticket(comment_mention)` → dòng `skip`; tổng lời gọi model vẫn 1 (quét của U4a dùng `can_send_ticket`, kiểm bằng `test_policy` ca dưới) |
| AC-9 (b) | `…test_agent_runner.py::TestExcludedByClassification::test_department_named_as_excluded_team` | bộ phận không có trong bảng nhưng trùng tên nhóm loại trừ → cùng kết quả |
| AC-9 (b) | `…test_agent_runner.py::TestExcludedByClassification::test_excluded_wins_over_low_confidence` | độ tin cậy 10 + bộ phận loại trừ → `stop_reason=excluded_by_classification` (thứ tự chốt U1/U2) |
| AC-9 (b) | `…test_agent_runner.py::TestExcludedByClassification::test_l0_still_records_exclusion` | mức L0 → dòng `classify` có `stop_reason`; `@ai` sau đó bỏ qua |
| AC-9 (b) | `erp_ai/agent/test_policy.py::TestSendRefusal::test_order_and_codes` | mỗi mã `REFUSAL_*`; phiếu bị loại bởi phân loại rồi được người đặt nhóm thường → gửi được; đặt nhóm loại trừ → `excluded_team` |
| AC-5 | `erp_ai/agent/tools/test_site_api.py::TestPermissionVectors::test_six_vectors_refused_in_normal_mode` | subTest: `User Permission` (tạo), `DocShare` (tạo), Property Setter `property="permlevel"` (tạo), Property Setter đang `permlevel` (sửa `value`), `Custom DocPerm` (tạo), `Role` (sửa), `DocType` (sửa `permissions`) — mỗi ca `ok=false` có lý do, số bản ghi và giá trị trước == sau |
| AC-5 | `…test_site_api.py::TestPermissionVectors::test_property_setter_casing_and_spaces` | `" PermLevel "`, `"PERMLEVEL"` → từ chối; `property="label"` → `ok=true` (Property Setter thường không bị chặn) |
| AC-5 | `…test_site_api.py::TestPermissionVectors::test_business_role_assignment_still_works` | `api_update_record("User", <user test>, {"roles": [{"role": <role nghiệp vụ do test tạo>}]})` → `ok=true`, role có trên User |
| AC-5 | `…test_site_api.py::TestPermissionVectors::test_vectors_allowed_when_unrestricted` | `ctx.unrestricted=True`: `User Permission`, Property Setter `permlevel` → không bị U2 chặn (N-1) |
| AC-5 | `…test_site_api.py::TestPermissionVectors::test_one_shared_list` | `{"User Permission", "DocShare"} ⊆ site_api.PERMISSION_DOCTYPES`; `hard_bans.hard_ban_reason("User Permission") == "DocType phân quyền"` (U0 INT-1) |
| AC-5 | `erp_ai/agent/test_agent_runner.py::TestPermissionVectorsLogged::test_refused_vector_has_one_failed_action_entry` | stub gateway gọi `api_create_record` cho `DocShare` ở L3 + (2) bật + Instructor: đúng 1 mục hành động `ok=false` có lý do (T64), DB không đổi |

Test FEAT-004 sửa theo AC (NFR-8, ghi lý do ở commit): ca nào ở `test_site_api.py` của T59 khẳng định `User Permission`/`DocShare` ghi được ở chế độ thường (nếu có); ca `test_handlers.py` so chuỗi `not_sendable` chính xác.

### Đối chiếu AC (Done criteria)

- AC giao cho U2 (`arch-impact.md:177` và lệnh giao việc): AC-5, AC-8, AC-9.
- AC có trong test plan trên: AC-5, AC-8, AC-9. Khớp 3/3.
- Lỗ của `audit-A5.md`: A5-3a (1) → `test_classified_into_excluded_team_stops_before_reasoning`; A5-3c → `test_list_hides_excluded_rows_in_both_modes` và `test_get_refuses_excluded_record_in_both_modes`. A5-3a (2) (giá trị `excluded_teams` trên site) là việc kiểm site của qa, không phải mã.
- Phần của các AC đó **không** thuộc U2: AC-5 ý (a), (c), (d) (FEAT-004 AC-31, AC-2(a), AC-30); AC-8 nhánh `api_call_method` (ADR-023 QĐ 6 b — chữ ở U0/U3/As-Built); AC-9 việc quét 15' (U4a, đã gọi `can_send_ticket`).

---

## Assumptions decided by the team

| # | Chọn | Vì | Phương án khác | Sai thì sửa |
|---|---|---|---|---|
| A-U2-1 | Dạng truy vấn = ứng viên SQL (tập cha) rồi lọc bằng đúng `send_refusal`; site_api lọc bằng `not in <tên phiếu>` | một vị từ, hai dạng không thể lệch (chuẩn hóa khoảng trắng, NFC, `casefold` chỉ có ở Python) | điều kiện SQL thuần (`subject not like`) — lệch khi tiêu đề có khoảng trắng đầu | đổi thân `excluded_ticket_names`; test `test_query_form_matches_predicate` giữ |
| A-U2-2 | "Bị loại bởi phân loại" chỉ có hiệu lực khi phiếu chưa có nhóm; người đặt nhóm thì luật nhóm quyết | AC-9 nói về phiếu chưa có nhóm; tránh khóa vĩnh viễn phiếu bị phân loại nhầm | loại vĩnh viễn | bỏ vế `agent_group` trống trong `send_refusal` |
| A-U2-3 | Công cụ bản ghi từ chối cả ghi (tạo liên kết, sửa, xóa, submit) trên bản ghi của phiếu loại trừ | T62 trả `value_before`/trường đã xóa = đầu ra tool (NFR-1); A5-3a: phiếu loại trừ "không được xử lý" | chỉ chặn đọc, để ghi theo N-1 | bỏ 3.3; giữ chặn `value_before` bằng cách rỗng hóa giá trị |
| A-U2-4 | Không hồi tố luật (b) cho phiếu cũ đã phân loại | không có dòng log để suy; luật tiền tố và nhóm vẫn phủ | quét lại phiếu cũ | thêm việc một lần ở U4a |
| A-U2-5 | Phủ 5 DocType của D-13 (thêm `HD Ticket Comment` so với 4 của AC-8); không phủ `ToDo`, `HD Ticket Activity` | D-13 là danh sách "mang nội dung phiếu" đã duyệt; ToDo/Activity chỉ chứa mô tả gán và tên hành động | thêm hai DocType đó | thêm vào `TICKET_CONTENT_DOCTYPES` (U0) và `TICKET_LINK_FIELDS` |
| A-U2-6 | Liệt kê trả `excluded_note` cố định thay vì lý do theo từng lần | AC-8 đòi "có lý do" và "không lộ sự tồn tại" cùng lúc | không có note | bỏ khóa; test note bỏ theo |
| A-U2-7 | AC-5 không phủ `Custom Field` có `permlevel` qua công cụ bản ghi | AC-5 chỉ kể Property Setter; Custom Field `permlevel` của danh mục là AC-30 (5), U7 | chặn luôn ở `_permlevel_refusal` | thêm một vế; cần analyst nếu muốn coi là vector của AC-5 |

Câu hỏi nghiệp vụ: 0.
