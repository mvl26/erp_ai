Feature: FEAT-006
Stage: research
Author-agent: researcher (R1, đọc mã nguồn)
Date: 2026-11-12

# Research FEAT-006 (R1) — quyền gán/Task, Assignment Rule, `condition` SLA, khuyến nghị Q-A1..Q-A4

Phạm vi: R1 chỉ đọc mã nguồn đã cài. Dữ liệu site (SLA, trường trên phiếu, cờ HD Settings) thuộc R2 (`research-site.md`), không có ở đây.
Mọi đường dẫn `file:line` dưới đây là bản cài trong `/home/miyano/frappe-bench/apps/`; URL GitHub ghim đúng commit đã cài (mục Sources).

## Version in use

| Gói | Phiên bản | Nguồn |
|---|---|---|
| frappe | 15.126.1 (commit 2e9ecdc03fa5b5b8d1ba05224a1aff7dad832bd0) | `apps/frappe/frappe/__init__.py:54` (`__version__ = "15.126.1"`), `git rev-parse HEAD` |
| helpdesk | 15.1.0 (commit a1858964f63a9deb287a6577ca785cc90800e402) | `apps/helpdesk`, `git rev-parse HEAD` |
| erpnext | 15.83.0 | `apps/erpnext/erpnext/__init__.py:7` |

## Câu hỏi con

1. Q-A2: quyền cần để gán (ToDo, `assign_to.add` + thông báo) và tạo Task với role {ERP AI Agent, Agent}.
2. Q-A3: Assignment Rule chạy ở sự kiện nào của HD Ticket; bot gán trước/sau thì rule có chồng hoặc gỡ người không.
3. `condition` của SLA đánh giá ra sao; có đọc được Custom Field trên HD Ticket không.
4. Khuyến nghị Q-A1..Q-A4.

## 1. Q-A2 — quyền gán và tạo Task

### 1a. Gán người (ToDo + thông báo) — ĐÃ TRẢ LỜI (độ tin cậy cao, đọc mã)

- `assign_to.add(args)` gọi `_add(args, ignore_permissions=False, validate_assignees=is_endpoint_call(...))` — `frappe/frappe/desk/form/assign_to.py:44-59`. Gọi từ Python trong job nền thì `validate_assignees` = False (chỉ True khi đi qua endpoint HTTP).
- Quyền duy nhất được kiểm với người gọi: `frappe.get_doc(doctype, name).check_permission()` — `assign_to.py:85-86`; `check_permission` mặc định `permtype="read"` — `frappe/frappe/model/document.py:347`. Tức là: tài khoản agent chỉ cần **đọc** được HD Ticket đó. Không cần quyền ghi phiếu.
- ToDo được tạo bằng `.insert(ignore_permissions=True)` — `assign_to.py:99-114`. Không cần quyền nào trên DocType ToDo. `assigned_by` = `frappe.session.user` (tài khoản agent) — `assign_to.py:111`.
- Người được gán không đọc được phiếu → nếu System Settings `disable_document_sharing` bật thì `frappe.throw("Missing Permission")`, ngược lại tự share phiếu cho người đó — `assign_to.py:121-134`.
- Thông báo: `notify_assignment(... action="ASSIGN")` — `assign_to.py:140-148`. Bỏ qua khi tự gán chính mình hoặc user bị disable — `assign_to.py:285-297`. Notification Log được tạo qua `enqueue_create_notification` (enqueue sau commit; trong test `enqueue_after_commit=not frappe.flags.in_test`) — `frappe/frappe/desk/doctype/notification_log/notification_log.py:131-160`, insert `ignore_permissions=True` — `notification_log.py:176`. Không cần quyền trên Notification Log.
- `HDTicket.assign_agent(agent)` chỉ bọc đúng `assign_to.add` — `helpdesk/helpdesk/helpdesk/doctype/hd_ticket/hd_ticket.py:483-487`; không kiểm người được gán là HD Agent (AC-6 phải tự kiểm `HD Agent.is_active`).
- Quyền đọc HD Ticket: `has_permission` của helpdesk — `hd_ticket.py:1352-1362`: admin → được; người tạo/contact/raised_by → được; không phải agent → không; agent → `_agent_has_permission` `hd_ticket.py:1372-1398`. `is_agent` ưu tiên bản ghi `HD Agent.is_active` nếu có, rồi mới tới role — `helpdesk/helpdesk/utils.py:42-56`. Nếu HD Settings `restrict_tickets_by_agent_group` bật, agent chỉ đọc được phiếu của nhóm mình, phiếu gán cho mình, phiếu chưa có nhóm (khi bật `do_not_restrict_tickets_without_an_agent_group`), hoặc mọi phiếu nếu thuộc nhóm có `ignore_restrictions`. Hệ quả: khi cờ này bật, tài khoản agent phải là HD Agent active thuộc nhóm có `ignore_restrictions` (hoặc là người tạo phiếu); nếu không, sau khi bot ghi `agent_group` sang nhóm khác, `assign_to.add` ném PermissionError. Giá trị cờ trên site: R2 kiểm.
- `_add` kiểm trùng ToDo Open cho cùng người — `assign_to.py:73-91`; gán lại cùng người là no-op (chỉ msgprint). Idempotent theo người.
- **Kết luận 1a:** với bộ role hiện có ({ERP AI Agent, Agent}), gán người KHÔNG cần thêm quyền nào, miễn tài khoản agent đọc được phiếu (điều kiện trên). Không phải sửa role (giữ ADR-006).

### 1b. Tạo Task — ĐÃ TRẢ LỜI (độ tin cậy cao, đọc mã)

- DocType: `Task` của ERPNext (module Projects) — `erpnext/erpnext/projects/doctype/task/task.json`. Quyền chuẩn chỉ có role `Projects User` (create/read/write/delete/share) — `task.json:418-430`.
- erp_ai đã thêm Custom DocPerm cho role `ERP AI Agent` trên Task: permlevel 0, read/write/create, **`if_owner=1`** — `erp_ai/erp_ai/install.py:184-205` (sau `setup_custom_perms("Task")` để giữ quyền chuẩn). Vậy tài khoản agent tạo được Task và đọc/sửa được Task do chính nó tạo. Không cần thêm quyền để tạo.
- Giao Task cho người: dùng `assign_to.add` trên Task → kiểm `read` của tài khoản agent trên Task đó — `assign_to.py:85-86`; Task do agent tạo nên `if_owner` thỏa. Không cần thêm quyền. Người được giao không có role `Projects User` → Task được share cho họ, hoặc lỗi nếu `disable_document_sharing` bật — `assign_to.py:121-134` (R2 kiểm cờ; cần ghi vào rủi ro).
- Tham chiếu phiếu: Task **không có** trường Link tới HD Ticket. Trường `issue` là Link tới `Issue` (ERPNext Support), không phải HD Ticket — `task.json:89-92`; `project` là Link `Project`, không bắt buộc (không có `reqd` ở `task.json:74-80`). Hiện `create_task` chỉ nhét đường dẫn `/helpdesk/tickets/<name>` vào `description` (Text Editor) — `erp_ai/erp_ai/agent/tools/write_ticket.py:86-108`. Đếm "C/D có ≥ 1 Task liên kết" (quy ước 3, AC-13) qua `description LIKE` là dễ sai (HTML, người sửa mô tả).
- `create_task` hiện từ chối khi không có người ra lệnh: `if not ctx.instructor: return _fail(...)` — `write_ticket.py:87-88` (ADR-005 Quyết định 1); registry chỉ cấp nhóm `task_write` khi có người ra lệnh — `erp_ai/erp_ai/agent/tools/registry.py:48-51`. Đây là chỗ Q-A1 phải nới.
- `Task.on_update` tự đóng/gỡ ToDo của Task khi Task `Completed`/`Cancelled` — `erpnext/erpnext/projects/doctype/task/task.py:173-185`; không đụng HD Ticket.
- **Kết luận 1b:** tạo và giao Task KHÔNG cần thêm quyền cho role. Cần thêm một tham chiếu có cấu trúc từ Task về HD Ticket (phương án ở mục 4) để AC-13 đếm được và idempotent.

## 2. Q-A3 — Assignment Rule và thứ tự gán — ĐÃ TRẢ LỜI (độ tin cậy cao, đọc mã)

**Sự kiện.** `assignment_rule.apply` gắn vào doc_events `"*"`: `on_update` (`frappe/frappe/hooks.py:174`), `on_cancel` (`hooks.py:183`), `on_update_after_submit` (`hooks.py:192`). `on_update` chạy cả sau `insert` lẫn sau mỗi `save` — `document.py:1321-1332` (`run_post_save_methods`). Thứ tự trong một lần lưu: method controller `HDTicket.on_update` chạy trước, rồi doc_events của HD Ticket, rồi `"*"` — `document.py:1506-1526` (compose: `fn` trước, `hooks` sau; `doc_events[doctype] + doc_events["*"]` ở :1519-1521). Vậy trong một lần lưu HD Ticket: `remove_assignment_if_not_in_team` (helpdesk) → `assignment_rule.apply` (frappe).

**Luật trong `apply`** (`frappe/frappe/automation/doctype/assignment_rule/assignment_rule.py:270-367`):

1. Lấy "assignments" = ToDo của phiếu có `status != "Cancelled"` (gồm cả Open và Closed), tối đa 5 — `assignment_rule.py:223-232`.
2. Nếu đã có assignment: chỉ thử **gỡ** — `apply_unassign` chỉ gỡ khi rule có `unassign_condition` **và** tên rule nằm trong `assignment_rule` của các ToDo đang có — `assignment_rule.py:68-72`, vòng lặp `:308-319`. ToDo do bot tạo qua `assign_to.add` có `assignment_rule = None` (`assign_to.py:112`, bot không truyền khóa này) → không rule nào gỡ ToDo của bot → `clear = False` → rule **không gán thêm** (`:321-329` chỉ chạy khi `clear`).
3. Nếu chưa có assignment: chạy `apply_assign` theo `priority desc`, rule đầu tiên có `assign_condition` đúng sẽ `assign_to.clear` rồi `_add(..., assignment_rule=self.name, notify=True, ignore_permissions=True)` — `assignment_rule.py:74-102`.
4. `assign_condition`/`unassign_condition` đánh giá bằng `frappe.safe_eval(expr, None, doc)` với `doc` là dict của phiếu (biến là tên trường trực tiếp, vd. `status == 'Open'`) — `assignment_rule.py:203-212`; lỗi chỉ msgprint, không chặn lưu.

**Rule của HD Team.** Mỗi HD Team tự tạo 1 Assignment Rule "<team> - Support Rotation", `priority=1`, users = thành viên nhóm — `helpdesk/helpdesk/helpdesk/doctype/hd_team/hd_team.py:63-99`. `assign_condition = "status == 'Open' and agent_group == '<team>'"` — `hd_team.py:105-110`; `unassign_condition = "agent_group != '<team>'"` — `hd_team.py:112-117`.

**Helpdesk gỡ người khi đổi nhóm.** `HDTicket.on_update` → `remove_assignment_if_not_in_team` — `hd_ticket.py:238-255`, `:428-448`: bỏ qua khi phiếu mới (`is_new`); khi `agent_group` vừa đổi, `status_category == "Open"`, người đang gán (`_assign[0]` nếu là HD Agent) **không** là HD Team Member của nhóm mới, và nhóm mới có Assignment Rule đang bật với ≥ 1 user (`:459-482`) → `clear_all_assignments` (gỡ **mọi** người, kể cả người bot gán).

**Luồng hiện tại của bot.** `set_classification` ghi `agent_group`/`priority` bằng `doc.save()` — `erp_ai/erp_ai/agent/tools/write_ticket.py:39-58` (save ở :56), gọi từ `_apply_classification` trong bước phân loại — `erp_ai/erp_ai/agent/runner.py:225-246`. Tức là hiện nay bot **save nhóm trước** mọi bước gán → rơi vào kịch bản S2 dưới đây.

**Kịch bản (bot chạy trong job sau `after_insert`, nên phiếu không còn `is_new`):**

| # | Thứ tự | Kết quả |
|---|---|---|
| S1 | Lúc tạo phiếu đã có `agent_group` = nhóm có rule bật | Ngay `on_update` của insert, rule gán người xoay vòng. Bot chạy sau thấy đã có người → theo A-5 không gán. Không chồng. |
| S2 | Bot ghi `agent_group` (save) **trước**, rồi mới gán | Save đó kích hoạt `apply`: chưa có ToDo → rule nhóm mới gán người xoay vòng. Bước gán của bot sau đó sẽ thấy đã có người (A-5 → không gán) hoặc, nếu bot không kiểm, thành **2 người** (chồng). |
| S3 | Bot **gán trước** (`assign_to.add`, không save phiếu — ToDo cập nhật `_assign` qua `frappe.db.set_value`, `frappe/frappe/desk/doctype/todo/todo.py:87-114`), rồi save `agent_group` mới | Lần save: (i) helpdesk gỡ hết người nếu người bot gán không thuộc nhóm mới và nhóm mới có rule bật+user; khi đó (ii) `apply` thấy 0 assignment → rule nhóm mới gán người xoay vòng. Nếu người bot gán **là** thành viên nhóm mới: (i) không gỡ; (ii) có ToDo không mang `assignment_rule` → rule không gỡ, không gán thêm. Người bot gán được giữ. |
| S4 | Nhóm đích không có rule, hoặc rule disabled, hoặc rule không có user | Không ai gỡ, không ai tự gán; bot là nguồn gán duy nhất. |
| S5 | Các lần save sau (người khác sửa phiếu) | Có ToDo của bot (không `assignment_rule`) → rule bỏ qua mãi. Chỉ đổi `agent_group` sang nhóm mà người đó không thuộc (và nhóm có rule bật) mới bị helpdesk gỡ. |

Kết luận cho Q-A3: rule **không chồng** lên người bot đã gán, và rule **không tự gỡ** người bot gán (vì ToDo không mang tên rule). Nguồn gỡ duy nhất là `remove_assignment_if_not_in_team` của helpdesk khi đổi nhóm. Muốn người theo cấu hình được giữ khi nhóm có rule bật: (a) bot gán **trước** khi save `agent_group`, và (b) người theo cấu hình phải là HD Team Member của nhóm đích. Nếu save nhóm trước (luồng hiện tại), rule của nhóm gán người xoay vòng trước bot (S2), và A-5 khiến bot dừng — tức là ở nhóm có rule bật, bảng người mặc định sẽ không bao giờ có hiệu lực.

## 3. `condition` của SLA — ĐÃ TRẢ LỜI (độ tin cậy cao, đọc mã)

- Khi nào chọn SLA: `HDTicket.before_validate` → `set_sla()` — `hd_ticket.py:101`, `:970-979`; `before_save` → `apply_sla()` tính `response_by`/`resolution_by` — `hd_ticket.py:112`, `:994-999`. Chạy ở **mọi** lần save, với giá trị đang có trong bộ nhớ của lần save đó.
- Thuật toán `get_sla(ticket)` — `helpdesk/helpdesk/helpdesk/doctype/hd_service_level_agreement/utils.py:12-52`:
  1. Lọc SLA `enabled`, trong khoảng `start_date`/`end_date`; nếu phiếu có `priority` thì INNER JOIN bảng con `HD Service Level Priority` với đúng `priority` đó (`:37-42`) — SLA không khai báo mức ưu tiên của phiếu sẽ bị loại.
  2. Thứ tự: SLA không-mặc-định trước, mặc định sau cùng; rồi `rank` (0 xếp sau), rồi `creation` (`:32-35`).
  3. SLA mặc định → trả về ngay, không xét `condition` (`:45-46`). SLA không mặc định mà `condition` rỗng → bỏ qua (`:47-48`).
  4. `frappe.safe_eval(sla.condition, None, context)` với `context = get_context(ticket)` (`:49-51`).
- `get_context(d)` = `{"doc": d.as_dict(), "frappe": frappe._dict(utils=...)}` — `helpdesk/helpdesk/utils.py:163-174`. Vậy biểu thức phải viết dạng **`doc.<fieldname>`** (khác Assignment Rule, nơi tên trường là biến trực tiếp). `as_dict()` chứa mọi trường của meta, gồm Custom Field → **có**, `condition` đọc được Custom Field trên HD Ticket, vd. `doc.custom_ai_complexity == 3` (tên trường do designer chọn).
- Khi lưu SLA, `validate_condition` chạy thử biểu thức trên một HD Ticket mới rỗng — `hd_service_level_agreement.py:180-198`. `doc` là `frappe._dict` nên trường sai tên trả `None`, không bị bắt lỗi khi lưu (suy luận từ kiểu `_dict`; UNVERIFIED bằng chạy thật).
- **Rủi ro quan trọng:** trong `get_sla`, lỗi khi đánh giá `condition` **không** được bắt (`utils.py:49-51` không có try) → ngoại lệ lan ra `before_validate` và **chặn lưu phiếu**. Ví dụ `doc.custom_ai_complexity >= 3` khi giá trị là `None` (phiếu chưa chấm, `L0`) → `TypeError` trong Python 3 → mọi lần lưu phiếu lỗi. Khuyến nghị cho người cấu hình/tài liệu: dùng `==` hoặc `(doc.custom_ai_complexity or 0) >= 3`; trường kiểu Int/Select có default.
- Thứ tự ghi của bot: ưu tiên và độ phức tạp phải được ghi **trong cùng một lần save** (hoặc độ phức tạp trước), vì SLA được chọn lại ở mỗi save theo cả `priority` lẫn `condition`. `set_classification` hiện ghi bằng `doc.save()` (`write_ticket.py:56`) nên nếu thêm trường điểm vào cùng lần save đó thì SLA được chọn đúng. Ghi bằng `frappe.db.set_value` (bỏ qua controller) sẽ KHÔNG chọn lại SLA.
- `condition_json` chỉ dùng cho UI portal, phải là JSON hợp lệ — `hd_service_level_agreement.py:192-198`; không tham gia đánh giá.

## 4. Phương án và khuyến nghị (architect quyết; đây chỉ là khuyến nghị)

### Q-A1 — ghi (gán người, tạo Task) khi không có người ra lệnh

| Phương án | Mô tả | Rủi ro | Chi phí |
|---|---|---|---|
| A1-a | Bước gán/Task là **code tất định** trong bước phân loại của runner (sau `_classify`), không phải tool model gọi được; nhận đầu vào chỉ từ cấu hình + điểm đã kiểm. Registry tool cho model giữ nguyên (`task_write` vẫn chỉ khi có người ra lệnh) | Thấp: model không có tham số người/SLA/ưu tiên (AC-9 dễ chứng minh bằng test tĩnh schema). Cần ADR mới bổ sung ADR-005 QĐ-1: "ghi do code runner, theo cấu hình + công tắc, không qua model" | Vừa: 1 module mới + ADR |
| A1-b | Mở nhóm tool `task_write`/`assign` cho model khi công tắc bật (thêm đầu vào thứ tư cho hàm cấp tool) | Cao hơn: model chọn người → phải chặn chèn lệnh ở tầng tool; nới hàng rào ADR-005 nhiều hơn | Vừa |

Khuyến nghị: **A1-a**. Lý do: AC-9 yêu cầu không tool nào nhận tên người/ưu tiên/SLA; `set_classification` đã là tiền lệ "runner gọi tool có quyết định tất định" (`runner.py:243-246`). Cần ADR mới (architect đánh số).

### Q-A2 — quyền

| Phương án | Mô tả | Rủi ro | Chi phí |
|---|---|---|---|
| A2-a | Giữ nguyên role. Gán: chỉ cần đọc phiếu (mục 1a). Task: Custom DocPerm `if_owner` đã có (mục 1b) | Thất bại nếu HD Settings `restrict_tickets_by_agent_group` bật mà tài khoản agent không thuộc nhóm `ignore_restrictions`; hoặc `disable_document_sharing` bật mà người được giao thiếu quyền đọc Task/phiếu. Cả hai là cấu hình site (R2) | Thấp |
| A2-b | Thêm quyền vào role `ERP AI Agent` (vd. Task không `if_owner`) | Đổi role, trái ADR-006, không cần thiết theo mã | Vừa (ADR sửa đổi) |

Khuyến nghị: **A2-a**. Bắt lỗi `frappe.PermissionError` khi gán/giao → nhật ký `ok=false` + comment xin phân công (AC-8/AC-16).

### Q-A3 — thứ tự với Assignment Rule

| Phương án | Mô tả | Rủi ro | Chi phí |
|---|---|---|---|
| A3-a | Giữ thứ tự hiện tại (save nhóm → gán). A-5: thấy đã có người (do rule) → không gán | Ở nhóm có rule bật + user, rule luôn thắng; bảng người mặc định vô hiệu ở nhóm đó (S2). Đúng tinh thần A-5 "nếu nhóm đã có rule thì đó là chủ ý của người cấu hình" | Thấp |
| A3-b | Gán **trước** khi save nhóm: kiểm "chưa có ToDo nào khác Cancelled" → `assign_to.add` người cấu hình → rồi `set_classification` save nhóm | Người cấu hình không thuộc nhóm đích + nhóm có rule → helpdesk gỡ và rule gán người khác (S3) → 2 thông báo (gán rồi gỡ). Cần kiểm "người là HD Team Member của nhóm đích" trước khi gán. Bot gán người dù nhóm có rule → lệch A-5 | Vừa |
| A3-c | Như A3-a, nhưng khi nhóm đích có rule bật + user thì bot không gán và ghi nhật ký "nhóm có rule"; chỉ gán ở nhóm không có rule (S4) | Hành vi rõ ràng, không 2 thông báo; người cấu hình chọn: tắt rule nhóm để dùng bảng người mặc định | Thấp |

Khuyến nghị: **A3-c** (A3-a có nhánh nhật ký rõ). Lý do: khớp A-5 và QĐ-3 (không giành việc), tránh gán-rồi-bị-gỡ. Kiểm tra trước khi gán phải dùng cùng định nghĩa với rule: ToDo `status != "Cancelled"` (`assignment_rule.py:223-232`), không chỉ `_assign`. Test cần phủ S1, S2, S4 (AC-7a).

### Tham chiếu Task ↔ phiếu (AC-13)

| Phương án | Mô tả | Rủi ro | Chi phí |
|---|---|---|---|
| T-a | Custom Field Link `HD Ticket` trên Task (tên do designer chọn), đếm `frappe.db.count("Task", {<field>: ticket})` | Thêm 1 Custom Field trên DocType ERPNext (cài/gỡ qua `install.py`) | Thấp |
| T-b | Giữ link trong `description`, đếm bằng `LIKE` | Sai khi người sửa mô tả; HTML escape | Thấp nhưng dễ vỡ |
| T-c | Dùng `Task.issue` | Sai kiểu: Link tới `Issue`, không phải HD Ticket (`task.json:89-92`) | Không dùng được |

Khuyến nghị: **T-a**, vẫn giữ link trong mô tả để người bấm được.

### Q-A4 — chấm điểm ở bước nào

| Phương án | Mô tả | Rủi ro | Chi phí |
|---|---|---|---|
| A4-a | Thêm khóa điểm vào JSON của bước phân loại (`CLASSIFY_PROMPT`, `prompts.py:56-66`), dùng chung `build_classify_request` (`prompts.py:166-171`) với eval | `CLASSIFY_MAX_TOKENS = 400` (`runner.py:32`): thêm 2 số + 1 lý do ≤ 25 từ, có thể đủ (UNVERIFIED, cần đo trên eval). Đổi prompt → cache prompt mới | Thấp |
| A4-b | Chấm ở bước suy luận | Bước suy luận chỉ chạy từ `L1` (`runner.py:134-135`) → trái AC-1 (`L0`) và AC-15 (eval dùng request phân loại) | Vừa |

Khuyến nghị: **A4-a**. Lý do: bước phân loại chạy ở mọi mức khi `ticket_insert` (`runner.py:127-133`), không thêm lời gọi model (NFR-1), eval đo được (AC-15). Ghi điểm lên phiếu trong **cùng lần save** của `set_classification` để SLA `condition` thấy điểm (mục 3).

### Điểm chưa trả lời

- Giá trị cờ HD Settings (`restrict_tickets_by_agent_group`, `do_not_restrict_tickets_without_an_agent_group`), System Settings `disable_document_sharing`, danh sách SLA/rule/nhóm trên site: thuộc R2 (`research-site.md`).
- Số token thực tế của trả lời phân loại khi thêm điểm: UNVERIFIED, chưa chạy POC.

## Sources

Mã nguồn đã cài là nguồn chính (không có trang docs chính thức mô tả chi tiết thứ tự hook/điều kiện gỡ). URL ghim đúng commit đã cài:

- Frappe assignment_rule.py: https://github.com/frappe/frappe/blob/2e9ecdc03fa5b5b8d1ba05224a1aff7dad832bd0/frappe/automation/doctype/assignment_rule/assignment_rule.py (truy cập 2026-11-12)
- Frappe hooks.py (doc_events "*"): https://github.com/frappe/frappe/blob/2e9ecdc03fa5b5b8d1ba05224a1aff7dad832bd0/frappe/hooks.py (truy cập 2026-11-12)
- Frappe assign_to.py: https://github.com/frappe/frappe/blob/2e9ecdc03fa5b5b8d1ba05224a1aff7dad832bd0/frappe/desk/form/assign_to.py (truy cập 2026-11-12)
- Frappe document.py (hook compose, check_permission): https://github.com/frappe/frappe/blob/2e9ecdc03fa5b5b8d1ba05224a1aff7dad832bd0/frappe/model/document.py (truy cập 2026-11-12)
- Helpdesk hd_ticket.py: https://github.com/frappe/helpdesk/blob/a1858964f63a9deb287a6577ca785cc90800e402/helpdesk/helpdesk/doctype/hd_ticket/hd_ticket.py (truy cập 2026-11-12)
- Helpdesk hd_team.py: https://github.com/frappe/helpdesk/blob/a1858964f63a9deb287a6577ca785cc90800e402/helpdesk/helpdesk/doctype/hd_team/hd_team.py (truy cập 2026-11-12)
- Helpdesk SLA utils.py: https://github.com/frappe/helpdesk/blob/a1858964f63a9deb287a6577ca785cc90800e402/helpdesk/helpdesk/doctype/hd_service_level_agreement/utils.py (truy cập 2026-11-12)
- Helpdesk utils.py (`get_context`, `is_agent`): https://github.com/frappe/helpdesk/blob/a1858964f63a9deb287a6577ca785cc90800e402/helpdesk/utils.py (truy cập 2026-11-12)
- ERPNext Task (nhánh version-15; bản cài 15.83.0): https://github.com/frappe/erpnext/blob/version-15/erpnext/projects/doctype/task/task.json (truy cập 2026-11-12)
