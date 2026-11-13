Feature: FEAT-006
Stage: design
Author-agent: designer
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. G2b tắt (config.json), để trống. -->

# Design FEAT-006 — Chấm điểm, định tuyến (ưu tiên, nhóm, người), SLA và Task theo điểm

Mode `decide`. Nền mã: nhánh `team/FEAT-003` @ `7cb654f` (đọc 2026-11-12). Số dòng `file:line` bên dưới là của nền này. FEAT-006 merge sau FEAT-003 → FEAT-004 → FEAT-005 (arch-impact "Thứ tự merge"), nên dev phải dò lại số dòng sau khi rebase. Tên hàm và tên file thì giữ nguyên.

## 1. Bối cảnh

**Vấn đề** (spec "Why now"): bot chỉ ghi nhóm và ưu tiên theo bảng ánh xạ cố định. Bot không gán người. Người mặc định và SLA mới là chữ trong prompt (`prompts.py:134-144`). Phiếu vẫn phải chờ người chia.

**Trong phạm vi** (chép từ spec, mục Phạm vi 1–8):
1. Chấm 2 điểm, mỗi điểm 1–3, kèm lý do. Ghi nhật ký ở mọi mức; từ `L1` ghi thêm lên phiếu.
2. Tính ưu tiên theo R1–R5.
3. Chọn nhóm: A/B/C/F theo ánh xạ; D/E theo bảng bộ phận → nhóm.
4. Chọn người theo bảng người mặc định (có tiền tố tiêu đề), gán bằng cơ chế gán của Helpdesk.
5. Helpdesk tự chọn SLA; bot báo khi không có SLA hoặc SLA chậm hơn mức mong đợi.
6. C/D: tạo 1 Task, giao cho người bot vừa gán.
7. Công tắc tự gán và tạo Task, tắt sẵn khi cài.
8. Eval offline đo độ khớp ưu tiên và nhóm.

**Ngoài phạm vi** (spec): bot không tự tách phiếu; không tạo hay sửa HD Team, Assignment Rule, SLA; không tự tính `response_by`/`resolution_by`; không gán tài khoản agent; không chia lại phiếu cũ; không chấm lại khi phiếu bị sửa; không có UI riêng; không đổi người khi người cũ nghỉ; không thống kê tải. Feature không dọn dữ liệu site `miyano` (A-13).

**ADR phải tuân** (trích ID, không chép lại): ADR-019 (QĐ 1–8 và Ràng buộc), ADR-020 (QĐ 1–7 và Ràng buộc), ADR-021 (QĐ 1–6 và Ràng buộc). Giữ nguyên: ADR-001 (tầng, import một chiều), ADR-003 (bước a–e của runner, `excluded_teams` chỉ đọc ở policy), ADR-004 (chủ ghi; QĐ 4: `L0` không ghi), ADR-005 (tool qua phân quyền; QĐ 3 từ chối = `ok=false`), ADR-006 (tập role, permlevel 8 cho trường AI), ADR-007 (chỉ một chỗ xóa trong app), ADR-015 (ngoại lệ có tên `assign_to.add`, ADR-021 QĐ 3).

**Cơ sở khảo sát (Explore).** Tôi đọc thẳng các file vì đã biết trước file cần đọc. Cache explore `erp_ai` báo `MISS docs/team/explore/erp_ai.md 081022b2b86b07d5`.
- *Kiểu lỗi:* hàm tool trả `{"ok": False, "reason": ...}` qua `_fail` (`write_ticket.py:20-21`, ADR-005 QĐ 3). Ngoại lệ lan lên savepoint của người gọi (`registry.py:117-124`, `runner.py:256-284`). Cấu hình sai thì `frappe.throw` ném `ValidationError`, câu báo nêu đúng chỗ sai (`classification.py:79-106`, gọi ở `erp_ai_setting.py:56-62`). Nhật ký lỗi chỉ ghi lớp ngoại lệ (`runner.py:62-65`, `:376-377`).
- *Phân quyền:* tool kiểm `doc.has_permission(...)` và `has_permlevel_access_to` trước khi ghi, rồi ghi bằng `doc.save()` (`write_ticket.py:39-57`). Trong `agent/tools/**` cấm `ignore_permissions`, `db.set_value`, SQL ghi, `set_user` và `get_all` (`test_architecture.py:567-601`). `permission_level`, `excluded_teams`, `ai_opt_out` chỉ đọc trong `policy.py` (`test_architecture.py:104`, `:659-671`). Runner chạy dưới `AGENT_USER` (`runner.py:79-85`).
- *Cấu hình:* `frappe.get_single(SETTING_DOCTYPE)` đọc một lần mỗi lần chạy (`runner.py:88`). Bảng dạng Code JSON có một bộ kiểm và một bộ nạp (`category_mapping`, `classification.py:79-113`). Giá trị mặc định chỉ ghi khi DB đang NULL (`install.py:86-95`).
- *Test:* test đặt cạnh mã, tên `test_*.py`, dùng `FrappeTestCase`. Mỗi test có `addCleanup(frappe.db.rollback)`, một bộ chặn commit, `FakeGateway` (`test_agent_runner.py:61-113`, `test_utils.py:32-54`), `set_agent_settings` (`test_utils.py:74-77`) và `helpdesk.test_utils` (`make_ticket`, `create_agent`, `make_todo`). Có sẵn kiểm mô tả trường DocType ≤ 400 ký tự (`tests/test_doctype_descriptions.py:227-245`).
- *Nhật ký:* `run_log.write_entry` là chỗ duy nhất tạo ERP AI Log (`run_log.py:11-33`). Bản ghi `classify` được ghi với `applied=0` và commit trước, rồi cập nhật bằng `frappe.db.set_value` (`runner.py:229-286`).

## Assumptions decided by the team
| # | Chọn | Vì | Phương án khác | Sai thì sửa |
|---|---|---|---|---|
| D-1 | Các bảng cấu hình nằm trong **một** trường Code JSON `routing_rules`. Công tắc là trường Check `auto_assign_enabled` (mặc định 0). Cả hai đặt trong section `section_routing` của ERP AI Setting | Cùng kiểu với `category_mapping`: một bộ kiểm và một bộ nạp (ADR-019 QĐ 6). Không phải thêm DocType con | 4 bảng con (4 DocType mới); 4 trường JSON riêng | Tách trường bằng migrate. Bộ nạp đổi, chỗ gọi giữ nguyên |
| D-2 | Trên HD Ticket: `ai_complexity`, `ai_importance` kiểu Int, `default "0"`, `read_only`; `ai_score_reason` kiểu Small Text, `read_only`. Cả ba ở permlevel 8. Trên Task: `ai_ticket` kiểu Link → HD Ticket, permlevel 0, `search_index 1`, **không** `read_only` | Theo ADR-020 QĐ 5 và ADR-021 QĐ 5. `ai_ticket` phải để người sửa được vì AC-13 tính cả "Task người tạo" | Tiền tố `custom_` | Đổi tên trường bằng migrate, kèm patch chép giá trị |
| D-3 | Khóa JSON mới của bước phân loại: `do_phuc_tap`, `do_quan_trong` (số 1–3), `ly_do_diem` (≤ 25 từ), `bo_phan` (chỉ dùng cho D/E) | Cùng kiểu đặt tên tiếng Việt không dấu như các khóa đang có (`prompts.py:57-65`) | Khóa tiếng Anh | Đổi trong prompt và bộ đọc cùng lúc (eval dùng chung) |
| D-4 | Điểm đi theo **cặp**. Chỉ cần một trong hai điểm sai (không phải số nguyên, là bool, nằm ngoài 1–3, hoặc thiếu) thì coi cả hai là "không có điểm": hai điểm = 0, lý do = "". Lý do dài hơn 25 từ thì cắt còn 25 từ đầu | AC-1 không tách riêng hai điểm. Lý do chấm mô tả cả hai, nên nửa cặp đúng không dùng được | Chấp nhận từng điểm riêng | Đổi bộ đọc; AC-1 thêm ca |
| D-5 | Gán người và giao Task đều dùng `frappe.desk.form.assign_to.add`, gọi ở đúng một module là `agent/tools/route_ticket.py` | ADR-021 QĐ 3 coi hai cách là tương đương. Một hàm dùng được cho cả HD Ticket lẫn Task | `HDTicket.assign_agent` cho phiếu | Đổi một chỗ gọi |
| D-6 | Toàn bộ bước định tuyến (u1)–(u4) chạy trong **một** transaction: mỗi đơn vị có savepoint riêng, và chỉ commit một lần ở cuối (khi không chạy test). Lần lưu (u1) giữ khóa dòng HD Ticket tới lúc commit. Khóa này là "claim" nguyên tử: job thứ hai của cùng phiếu phải chờ, rồi thấy ToDo đã có nên không gán thêm | Không phải check-then-insert không khóa. Hàng đợi đã chống trùng job theo `job_id` (ADR-003), và khóa dòng phủ nốt trường hợp còn lại | Commit sau từng đơn vị (có cửa sổ chạy đua giữa hai job) | Commit từng đơn vị và thêm `for_update` khi đọc vị từ |
| D-7 | Cảnh báo SLA (AC-11, AC-12) là một phần tử `actions` có `"tool": "sla_check"`, `ok=false`, `reason` chứa các con số. Thêm một dòng `frappe.logger("erp_ai").warning` không có nội dung phiếu | AC-16 đã dùng `actions`. Không thêm loại bản ghi (ADR-019 QĐ 7) | Ghi vào cột `error` (làm sai số đếm lỗi) | Đổi chỗ ghi; test đếm theo `tool` |
| D-8 | `CLASSIFY_MAX_TOKENS` 400 → 600. Eval in thêm `output_tokens` lớn nhất và số trả lời có `stop_reason = max_tokens` | Ước lượng: khoảng 4 khóa và 25 từ, tức thêm chừng 100 token. 600 vẫn còn dư cho `cac_yeu_cau`. Chỉ trả tiền theo số token thật dùng. Số đo thật lấy từ lần chạy AC-15 | Giữ 400 rồi chờ đo | Lần eval AC-15 cho thấy max < 300 thì hạ lại; có ca `max_tokens` thì nâng |
| D-9 | Kiểm SLA và comment "chưa có SLA" chạy ở `L1`+ **dù công tắc bật hay tắt**. Công tắc chỉ chặn (u2) và (u3) | Spec Phạm vi 7 chỉ gắn công tắc với việc gán và tạo Task. AC-7c chỉ đòi 0 ToDo và 0 Task | Gắn cả kiểm SLA với công tắc | Thêm điều kiện công tắc vào bước kiểm SLA |
| D-10 | Danh sách tên bộ phận lấy từ `routing_rules.departments` và nối vào cuối system prompt phân loại. `build_classify_request` nhận `departments=()`. Không có bộ phận thì không nối gì | Model chỉ chọn được tên có trong cấu hình. Giá trị chỉ được dùng khi khớp bảng, nên không mở đường chèn lệnh (arch-impact "Để designer quyết") | Model tự đặt tên bộ phận rồi bot so gần đúng | Bỏ danh sách; AC-5 khi đó khớp kém hơn |
| D-11 | Mặc định `expected_sla` theo 16.2, tính bằng phút. Phản hồi / xử lý: A 15/480, B 15/240, C 60/1440 (lấy mốc "BA note 24h"), D 60/null, E 60/null, F 5/60. `null` = "theo Hạn hoàn thành", không kiểm | Cột "xử lý" của C ở 16.2 có hai mốc. Chọn mốc đầu, 24 giờ, vì đó là mốc của phản hồi xử lý đầu tiên. System Manager sửa được (QĐ-4) | C = 3 ngày; C = null | Sửa cấu hình, không cần deploy |
| D-12 | Gộp quy tắc R1–R5 và chọn nhóm/người vào `routing.decide_route`. `classification.resolve_ticket_values` bị **xóa**. Ba chỗ gọi (runner, `write_ticket`, test) chuyển sang hàm mới | ADR-019 Ràng buộc: R1–R5 chỉ ở một hàm. Nếu để R1 trong `classification.py` và R2–R5 ở chỗ khác thì thành hai hàm | Giữ `resolve_ticket_values` để bọc hàm mới (thì `classification` phải import `routing`, sinh vòng import) | — |
| D-13 | Tiền tố tiêu đề khớp kiểu `casefold`, là chuỗi con của tiêu đề (giống cách bắt `[GẤP]`, `classification.py:120`). Xét theo thứ tự khai trong cấu hình; tiền tố đầu tiên khớp mà có người thì dùng | 16.3 quy ước 1: tiền tố có thể đứng sau `[GẤP]` | Chỉ khớp ở đầu tiêu đề | Đổi một hàm |
| D-14 | Đường model (`set_classification`): điểm đọc từ `ai_complexity`/`ai_importance` đang có trên phiếu, `department = None`. Vì vậy D/E qua đường này thì bỏ qua ghi nhóm, lý do "không có bộ phận" | ADR-019 QĐ 4: điểm chỉ đến từ bước phân loại, không bao giờ từ tham số tool. Schema giữ nguyên | Lưu bộ phận lên phiếu (thêm trường thừa, STD-DESIGN-5) | Thêm trường bộ phận bằng change-request |
| D-15 | Nhật ký ERP AI Log thêm 4 cột: `predicted_complexity` (Int), `predicted_importance` (Int), `predicted_score_reason` (Small Text), `predicted_assignee` (Data, user ID). Không có điểm thì `predicted_score_reason = "không có điểm"` | Spec mục Dữ liệu: nhật ký có điểm, lý do và người dự kiến ở mọi mức. `ENTRY_TYPES` không đổi (ADR-019 Ràng buộc) | Nhét điểm vào `value_after` (ở `L0` không có giá trị trước/sau) | Thêm hoặc bớt cột |
| D-16 | (u1) ném lỗi → savepoint rollback, nhật ký ghi lớp ngoại lệ, bước định tuyến dừng. Bước suy luận vẫn chạy như hiện nay (`runner.py:134-135`) | ADR-020 QĐ 6 chỉ dừng (u2)–(u4). AC-18 chỉ đếm comment của bước định tuyến | Dừng cả lần chạy | Thêm `return` sau khi (u1) lỗi |
| D-17 | Đầu mục F mà cấu hình không có người (mặc định cài đặt) → mỗi phiếu F nhận 1 comment xin phân công | Đúng chữ của AC-8 và AC-13 ("không người thì 1 comment"). System Manager điền người cho F để tránh | Không comment ở F | Change-request AC-8 |

Câu hỏi nghiệp vụ: 0. Mọi luật nghiệp vụ đã có trong spec (R1–R5, A-5, A-7, A-12). Bảng trên chỉ là lựa chọn kỹ thuật.

## 2. Mô hình dữ liệu

### 2.1 HD Ticket — 3 Custom Field (ADR-020 QĐ 5; ADR-006 permlevel 8)
| fieldname | fieldtype | default | permlevel | khác | Ý nghĩa |
|---|---|---|---|---|---|
| `ai_complexity` | Int | `"0"` | 8 | `read_only 1`, `module "ERP AI agent"` | 0 = chưa chấm / không có điểm; 1–3 theo thang ở spec |
| `ai_importance` | Int | `"0"` | 8 | như trên | như trên |
| `ai_score_reason` | Small Text | — | 8 | `read_only 1` | Lý do chấm, ≤ 25 từ; "" khi không có điểm |

- Thêm vào `_ai_field_specs` (`install.py:114-153`), đặt sau `ai_confidence`. Nhờ vậy `_ensure_template_rows` (`install.py:156-181`) tự thêm dòng template với `visible_to = Agents`. Đây là đường user `Agent` đọc được điểm (AC-2).
- Cột Int của Frappe là `NOT NULL DEFAULT 0`, nên phiếu cũ nhận 0 lúc `ALTER`. Không cần chuyển dữ liệu (arch-impact G-4).
- Mẫu `condition` an toàn cho tài liệu người dùng: `doc.ai_complexity == 3`, `doc.ai_complexity >= 3`.

### 2.2 Task — 1 Custom Field (ADR-021 QĐ 5; ADR-019 QĐ 5 phương án T-a)
| fieldname | fieldtype | options | permlevel | khác |
|---|---|---|---|---|
| `ai_ticket` | Link | HD Ticket | 0 | `label "Phiếu Helpdesk"`, `search_index 1`, `module "ERP AI agent"`, `insert_after "description"` |

- Mẫu truy cập: `frappe.db.exists("Task", {"ai_ticket": <phiếu>})`. Mỗi phiếu chạy một lần, nên index trên `ai_ticket` là đủ.
- Mọi Task do `erp_ai` tạo đều đặt trường này: cả (u3) lẫn `create_task` của model. Link bấm được trong `description` vẫn giữ.

### 2.3 Custom DocPerm Task của app (ADR-021 QĐ 2)
Dòng (Task, `ERP AI Agent`, permlevel 0, `if_owner=1`) có `share=1`. Thủ tục cài đặt chỉ bật cờ này từ 0 lên 1, không đổi cờ nào khác, không đụng dòng của role khác.

### 2.4 ERP AI Setting — 2 trường trong `section_routing` (hàng "trường người đặt" của ADR-004)
| fieldname | fieldtype | default | description (≤ 400 ký tự) |
|---|---|---|---|
| `auto_assign_enabled` | Check | `"0"` | Bật thì từ L1, phiếu mới chưa có ai được gán sẽ được bot gán người theo `routing_rules`, và tạo 1 Task cho đầu mục C/D. Tắt thì không gán, không tạo Task. Trước khi bật: gỡ role thừa của tài khoản agent, tạo HD Agent cho người trong bảng |
| `routing_rules` | Code (`options "JSON"`) | JSON mặc định ở 3.3 | Bảng người mặc định theo đầu mục, bảng bộ phận → nhóm và trưởng bộ phận, bảng độ quan trọng → mức ưu tiên tối thiểu, SLA mong đợi (phút). Cấu hình sai bị chặn khi lưu |

- `_ensure_default_settings` (`install.py:86-95`) chỉ ghi giá trị mặc định khi DB đang NULL. Vì vậy cài lại không ghi đè giá trị người đã sửa (spec DoD, ADR-006).
- Chỉ `policy.py` đọc `auto_assign_enabled` (thêm vào `POLICY_FIELDS`, ADR-019 Ràng buộc).

### 2.5 ERP AI Log — 4 cột trong `section_prediction` (D-15; ADR-019 QĐ 7)
| fieldname | fieldtype | Ghi ở |
|---|---|---|
| `predicted_complexity` | Int | Bản ghi `classify`, mọi mức |
| `predicted_importance` | Int | như trên |
| `predicted_score_reason` | Small Text | như trên; "không có điểm" khi điểm bị loại |
| `predicted_assignee` | Data | như trên; user ID hoặc rỗng |

`run_log.ENTRY_TYPES` giữ nguyên `("classify", "reason", "skip")`.

### 2.6 Dữ liệu chỉ đọc (không ghi)
- Bảng ToDo, đọc theo `reference_type = "HD Ticket"`, `reference_name`, `status != "Cancelled"`, lấy các trường `allocated_to`, `assignment_rule`.
- HD Agent (`user`, `is_active`), HD Team (tồn tại), HD Ticket (`sla`, `priority`).
- HD Service Level Priority (`parent = sla`, `priority`, lấy `response_time`, `resolution_time` tính bằng giây).

Không đọc ở `tools/`, không đưa cho model (ADR-019 QĐ 3, ADR-021 QĐ 4).

## 3. API / hợp đồng

Không có HTTP method, job, hàng đợi hay lời gọi model mới. Các hợp đồng dưới đây là hợp đồng nội bộ của app, cộng hai hợp đồng dữ liệu mà người khác sẽ dựa vào: trường điểm trên phiếu (người viết `condition` SLA dùng) và cấu hình `routing_rules`. **Không có thay đổi phá vỡ hợp đồng công khai.** Mọi thay đổi đều là thêm vào. Hai thay đổi nội bộ có phá: xóa `resolve_ticket_values` và bỏ hằng `ROUTING_TABLE`. Mọi chỗ gọi đều nằm trong repo và được sửa cùng lúc (mục 7).

### 3.1 JSON trả lời của bước phân loại (model → bộ đọc), thêm khóa
Khóa cũ (`prompts.py:57-65`) giữ nguyên, thêm 4 khóa:
```
"do_phuc_tap": 1|2|3,
"do_quan_trong": 1|2|3,
"ly_do_diem": "<một câu, tối đa 25 từ, vì sao chấm hai điểm này>",
"bo_phan": "<chỉ với D/E: một tên trong DANH SÁCH BỘ PHẬN; không thì rỗng>"
```
- `CLASSIFY_PROMPT` thêm bảng thang điểm (bảng ở spec mục Dữ liệu, chép nguyên văn) và 4 khóa trên.
- `build_classify_request(subject, description, departments=())`: khi `departments` có giá trị thì nối thêm một khối text `DANH SÁCH BỘ PHẬN: <tên, cách nhau bằng dấu phẩy>` vào sau `CLASSIFY_PROMPT`, trong cùng block system (vẫn `cache_control`). Runner và eval cùng gọi hàm này (ADR-019 QĐ 1).
- **Hành vi là hợp đồng** (bộ đọc `parse_classification`, chữ ký không đổi):
  - không bao giờ ném lỗi;
  - điểm sai thì không bỏ cả kết quả phân loại;
  - trả lời cũ không có khóa điểm → `complexity = importance = 0`, `score_reason = ""`;
  - D-4 áp dụng cho cặp điểm;
  - `bo_phan` không phải chuỗi → `None`.
- `Classification` (`classification.py:27-35`) thêm `complexity: int = 0`, `importance: int = 0`, `score_reason: str = ""`, `department: str | None = None`. Các trường cũ giữ nguyên. Thêm hằng `SCORE_VALUES = (1, 2, 3)`, `SCORE_REASON_MAX_WORDS = 25`.

### 3.2 Hàm của Lõi agent (ngoài `tools/`)
| Hàm | Module | Vào | Ra | Lỗi / từ chối |
|---|---|---|---|---|
| `load_routing_config(raw)` | `agent/routing.py` (mới) | chuỗi JSON của `routing_rules` | `dict` đã chuẩn hóa (3.3); sai dạng → `{}` | Không ném (giống `load_mapping`) |
| `validate_routing_config(raw)` | `agent/routing.py` | như trên | `None` | `frappe.ValidationError` (qua `frappe.throw`), câu báo nêu đường dẫn khóa sai (3.3) |
| `decide_route(classification, subject, mapping, config, *, team_exists, is_excluded_team, is_active_agent)` | `agent/routing.py` | `Classification`; tiêu đề; ánh xạ đã nạp; cấu hình đã nạp; 3 hàm hỏi sự thật của site `(str) -> bool` | `RouteDecision` (bên dưới) | Không ném; hàm thuần nếu 3 hàm hỏi thuần |
| `sla_lag(category, resolution_s, config)` | `agent/routing.py` | đầu mục; `resolution_time` (giây) của dòng SLA đang áp; cấu hình | `(actual_min, expected_min)` khi chậm hơn; `None` khi khớp hoặc không kiểm (`resolution_min` null, D/E) | Không ném |
| `departments(config)` | `agent/routing.py` | cấu hình | `tuple[str, ...]` tên bộ phận theo thứ tự khai | — |
| `ticket_assignments(ticket)` | `agent/site_facts.py` (mới) | tên phiếu | `list[{"allocated_to", "assignment_rule"}]` của ToDo `status != "Cancelled"` | — (đọc hệ thống, ADR-019 QĐ 5) |
| `has_linked_task(ticket)` | `agent/site_facts.py` | tên phiếu | `bool`: có Task nào với `ai_ticket = ticket` | — |
| `is_active_agent(user)` | `agent/site_facts.py` | user ID | `bool`: có HD Agent với `user = user` và `is_active = 1` | — |
| `team_exists(team)` | `agent/site_facts.py` | tên nhóm | `bool` | — |
| `applied_sla(ticket)` | `agent/site_facts.py` | tên phiếu | `{"sla", "priority", "resolution_s"}`, hoặc `None` khi phiếu không có `sla` | — (đọc hệ thống, ADR-021 QĐ 4) |
| `auto_assign_enabled(settings)` | `agent/policy.py` | đối tượng setting đã đọc ở bước (b) | `bool` | — (chỉ chỗ này đọc trường công tắc) |
| `is_excluded_team(team)` | `agent/policy.py` | tên nhóm | `bool`, chuẩn hóa bằng `_normalize` giống `can_send_ticket` (`policy.py:18-38`) | — |
| `build_routing_table(mapping, config, names)` | `agent/prompts.py` | ánh xạ; cấu hình; `{user: tên hiển thị}` | chuỗi bảng routing (cùng cột với 16.2) | — |
| `build_reason_system(prompt_digest, routing_table="")` | `agent/prompts.py` | thêm tham số `routing_table` | `routing_table` thay vị trí của `ROUTING_TABLE` cũ; rỗng thì bỏ phần đó | — |

`RouteDecision` là frozen dataclass trong `routing.py`:
```
ticket_type: str | None
agent_group: str | None     # None = không ghi nhóm
priority: str | None        # None = không ghi ưu tiên (R3, hoặc ánh xạ rỗng)
assignee: str | None        # user ID hợp lệ, hoặc None
needs_task: bool            # category ∈ {C, D} và assignee không None
notes: tuple[dict, ...]     # {"field": "agent_group"|"assignee", "reason": "<câu cố định>"}
```

**Thuật toán của `decide_route`** (chỉ hiện thực ở đây, ADR-019 QĐ 3–4, Ràng buộc):
- *Ưu tiên*, xét lần lượt theo `imp = classification.importance`:
  1. tiêu đề chứa `[GẤP]`/`[GẬP]` → `Urgent`;
  2. F → `Low`;
  3. E → `None`;
  4. A và `imp == 3` → `Urgent`;
  5. còn lại → mức cao hơn (theo thứ tự `PRIORITIES`) giữa `mapping[cat].priority` và `config.importance_priority[str(imp)]`, bỏ qua giá trị rỗng. Cả hai rỗng → `None`. `imp == 0` → không có mức tối thiểu.
- *Nhóm*:
  - A/B/C/F → `mapping[cat].agent_group` (rỗng → `None`).
  - D/E → bộ phận model chọn, khớp tên bộ phận đã chuẩn hóa (`casefold`, gộp khoảng trắng). Lần lượt xét:
    - không có bộ phận → note "không có bộ phận";
    - bộ phận không có trong bảng → note "bộ phận '<x>' không có trong bảng bộ phận";
    - nhóm rỗng hoặc `not team_exists` → note "nhóm '<t>' không tồn tại";
    - `is_excluded_team` → note "nhóm '<t>' bị loại trừ";
    - qua cả bốn → `team`.
- *Người*:
  - Ứng viên:
    - D/E → `departments[bộ phận].head`;
    - A/B/C/F → người của tiền tố đầu tiên khớp (D-13) trong `assignees[cat].prefixes`, nếu không có thì `assignees[cat].default`.
  - Loại ứng viên khi:
    - rỗng → note "cấu hình không có người cho đầu mục <cat>";
    - `== AGENT_USER` → note "không gán tài khoản agent" (AC-8, A-7);
    - `not is_active_agent` → note "<user> không phải HD Agent đang hoạt động" (AC-6).
- `ticket_type` lấy theo ánh xạ như hiện nay.

### 3.3 Cấu hình `routing_rules` (hợp đồng với System Manager)
```json
{
  "assignees": {
    "A": {"default": "", "prefixes": {"[tracecore]": ""}},
    "B": {"default": "", "prefixes": {}},
    "C": {"default": "", "prefixes": {}},
    "F": {"default": "", "prefixes": {}}
  },
  "departments": {},
  "importance_priority": {"1": "", "2": "High", "3": "High"},
  "expected_sla": {
    "A": {"response_min": 15, "resolution_min": 480},
    "B": {"response_min": 15, "resolution_min": 240},
    "C": {"response_min": 60, "resolution_min": 1440},
    "D": {"response_min": 60, "resolution_min": null},
    "E": {"response_min": 60, "resolution_min": null},
    "F": {"response_min": 5, "resolution_min": 60}
  }
}
```
Đây là giá trị mặc định khi cài. Danh sách người để trống (spec DoD). Dạng một dòng `departments` khi người điền: `"Kế toán": {"team": "<HD Team>", "head": "<user ID>"}`.

Luật kiểm (`validate_routing_config`). Mỗi lỗi một câu tiếng Việt, nêu đường dẫn khóa (AC-4):
| Lỗi | Câu báo (mẫu) |
|---|---|
| Không phải JSON object | `Cấu hình định tuyến không phải JSON object hợp lệ` |
| Khóa gốc lạ | `Cấu hình định tuyến có khóa lạ '<k>', chỉ nhận assignees, departments, importance_priority, expected_sla` |
| `assignees.<cat>`: cat ∉ {A, B, C, F} | `assignees: đầu mục '<cat>' không hợp lệ (D, E lấy người theo departments)` |
| `assignees.<cat>` sai dạng | `assignees.<cat> phải là object có default (chuỗi) và prefixes (object)` |
| User không tồn tại (`default`, `prefixes.*`, `departments.*.head`, khi khác rỗng) | `<đường dẫn>: người '<u>' không tồn tại` |
| `departments.<d>` sai dạng hoặc tên rỗng | `departments.<d> phải là object có team và head (chuỗi)` |
| `importance_priority` không đủ đúng 3 khóa "1", "2", "3" | `importance_priority phải có đúng các khóa 1, 2, 3` |
| `importance_priority.<n>` ∉ PRIORITIES ∪ {""} | `importance_priority.<n>: mức '<v>' không hợp lệ, chỉ nhận Low, Medium, High, Urgent hoặc rỗng` |
| `expected_sla.<cat>` sai | `expected_sla.<cat>.<khóa> phải là số nguyên dương (phút) hoặc null` |

- Bộ kiểm không chặn tài khoản agent và không kiểm nhóm có tồn tại hay không. Hai việc đó được chặn lúc chạy (AC-8, AC-5/A-14), để người tạo team sau vẫn lưu được cấu hình.
- Bộ nạp trả `{}` khi cấu hình sai. Với `{}`: mọi bảng rỗng, không có mức tối thiểu, không kiểm SLA. Runner ghi thêm lỗi `routing_rules không hợp lệ` vào nhật ký (giống `BAD_MAPPING_ERROR`, `runner.py:49`).

### 3.4 Hàm ghi của bước định tuyến: `agent/tools/route_ticket.py` (mới, **không** `ToolSpec`, không có `TOOLS`, không có trong `TOOL_MODULES`; ADR-019 QĐ 3, Ràng buộc)
| Hàm | Vào | Ra (một kiểu lỗi, ADR-005 QĐ 3) | Ghi |
|---|---|---|---|
| `apply_route(decision, classification, ctx)` | `RouteDecision`, `Classification`, `ToolContext` | `{"ok": True, "before": {...}, "after": {...}, "skipped": [...]}`. Từ chối: `{"ok": False, "reason": ...}` khi thiếu quyền ghi phiếu, khi người đã phân loại, khi thiếu quyền ghi một trường | **Một** `doc.save()` của HD Ticket gồm: `ticket_type`, `agent_group`, `priority` (chỉ giá trị có thật trên site, kiểm bằng `LINKED_DOCTYPES` như `write_ticket.py:12-16`), `ai_confidence`, `ai_complexity`, `ai_importance`, `ai_score_reason`, `ai_classified_by = "AI"`, `ai_updated_at`. Luôn lưu, kể cả khi E không có nhóm và ưu tiên (ADR-020 QĐ 1, QĐ 6) |
| `assign_owner(user, ctx)` | user ID, `ToolContext` | `{"ok": True, "assignee": user}`. Từ chối: thiếu quyền đọc phiếu | `assign_to.add({"assign_to": [user], "doctype": "HD Ticket", "name": ctx.ticket_name})`. Không truyền cờ bỏ quyền (ADR-021 QĐ 3) |
| `create_routed_task(user, ticket_subject, classification, ctx)` | user ID, tiêu đề phiếu, `Classification` (điểm, lý do), `ToolContext` | `{"ok": True, "task": name}`. Từ chối: không có DocType Task, thiếu quyền tạo Task, thiếu quyền đọc phiếu | `Task.insert()`: `subject` = tiêu đề phiếu cắt còn 140 ký tự; `ai_ticket`; `description` = đoạn link phiếu (dùng chung với `create_task`) + dòng cố định "Độ phức tạp {c}/3, độ quan trọng {i}/3: {lý do}" (đã `escape_html`). Sau đó `assign_to.add` trên Task. Lỗi chia sẻ (`disable_document_sharing`) ném `frappe.ValidationError` cho runner rollback |
| `post_routing_comment(lines, ctx)` | `list[str]` các câu cố định ở 3.6 | Kết quả của `post_comment` (`write_ticket.py:73-83`, dùng lại) | 1 Comment |

- Ngoại lệ không bắt trong các hàm này lan lên savepoint của runner.
- `write_ticket.py` sửa:
  - `set_classification` gọi `routing.decide_route` với `Classification(category, confidence, complexity=doc.ai_complexity or 0, importance=doc.ai_importance or 0)` và `department = None` (D-14), rồi chỉ dùng `ticket_type`/`agent_group`/`priority`. Schema giữ nguyên;
  - `create_task` đặt `ai_ticket`;
  - tách hàm `_ticket_link_html(name)` và `_existing_values(wanted)` để `route_ticket` dùng lại (STD-DESIGN-4).
- `ToolContext` (`registry.py:12-19`) thêm trường cuối `routing_config: dict | None = None`. Runner đưa cấu hình đã nạp vào; tool không đọc cấu hình (ADR-019 QĐ 6).

### 3.5 Nhật ký (hợp đồng với người duyệt và AC-16)
Bản ghi `classify` của lần chạy (không thêm loại bản ghi):
- Ghi ngay, mọi mức: các cột `predicted_*` cũ lấy từ `RouteDecision`, cộng 4 cột ở 2.5; `applied=0`; commit (D-20 như cũ).
- Sau bước định tuyến (`L1`+), cập nhật một lần:
  - `applied = 1` khi (u1) ok;
  - `value_before` / `value_after` = `{"ticket": {...}, "assign": [user...], "task": "<tên>"}`, chỉ những đơn vị có ghi;
  - `actions` = danh sách theo đúng thứ tự chạy, mỗi phần tử `{"tool": "<apply_route|assign_owner|create_routed_task|post_routing_comment|sla_check>", "doctype": "...", "name": "<phiếu|user ID|Task|Comment>", "ok": bool, "reason"?: "...", "rule"?: "<Assignment Rule>"}`;
  - `skipped_fields` = `skipped` của (u1) cộng `notes` của quyết định;
  - `error` thêm `route <tên hàm>: <LớpNgoạiLệ>` khi một đơn vị ném lỗi.
- Người được gán ghi bằng user ID. Không ghi nội dung phiếu (NFR-4').

### 3.6 Câu chữ cố định (hằng trong `route_ticket.py`; không chứa nội dung phiếu hay cấu hình thô; NFR-4)
- `ASSIGN_REQUEST`: "Bot chưa gán được người phụ trách cho phiếu này: {lý do}. Nhờ trưởng nhóm phân công." `{lý do}` là một trong các câu sau:
  - "cấu hình không có người hợp lệ";
  - "gán người không thành công";
  - "không giao được Task cho người phụ trách (chia sẻ tài liệu đang tắt)".
- `NO_SLA`: "Chưa có SLA áp vào phiếu, cần System Manager cấu hình."
- Nhiều câu thì gộp vào **một** comment, nối bằng xuống dòng (ADR-019 QĐ 2 u4: tối đa một comment).

### 3.7 Phiên bản
- Không có API công khai đổi phiên bản.
- Prompt phân loại và prompt suy luận đổi nội dung, nên cache prompt mới.
- Test "trùng từng byte" của FEAT-004/005 được cập nhật ảnh chụp nền theo arch-impact "Thứ tự merge" (STD-TEST-5: spec FEAT-006 đổi hành vi).

## 4. Luồng

### 4.1 Runner, lần chạy `ticket_insert` (sửa `runner.py:101-135`, `:195-286`)
1. Bước (b): giữ `settings = frappe.get_single(...)`. Nạp thêm `routing = load_routing_config(settings.routing_rules)` một lần.
2. Bước (e): `level = policy.effective_level(settings)` như cũ, và thêm `auto_assign = policy.auto_assign_enabled(settings)` (ADR-019 QĐ 6, ADR-003 bước e).
3. Dựng `ToolContext` như cũ (chỉ ở `L1`+), thêm `routing_config=routing`.
4. `_classify`:
   1. Gọi model với `build_classify_request(subject, description, departments(routing))` và `max_tokens = CLASSIFY_MAX_TOKENS (600)`. Lỗi cổng model → như cũ (`runner.py:211-219`).
   2. `parse_classification` → `None` thì như cũ (`unparseable`).
   3. `decision = decide_route(classification, subject, mapping, routing, team_exists=site_facts.team_exists, is_excluded_team=policy.is_excluded_team, is_active_agent=site_facts.is_active_agent)`.
   4. `write_entry(... predicted_* từ decision, predicted_complexity/importance/score_reason/assignee, applied=0)`, rồi commit như cũ. Ở `L0` dừng ở đây: 0 ghi lên phiếu, 0 ToDo, 0 Task (AC-1, AC-2, AC-7d; ADR-004 QĐ 4).
   5. `L1`+ → `_route(log_name, classification, decision, context, auto_assign, subject)`.
5. `_reason` như cũ, chỉ có một chỗ đổi: `system = build_reason_system(settings.prompt_digest, routing_table=build_routing_table(mapping, routing, names))`, trong đó `names` = `get_fullname` của mọi user trong cấu hình (AC-14).

### 4.2 `_route` (mới, trong `runner.py`; ADR-020 QĐ 1–7)
Mỗi bước `uN` = `frappe.db.savepoint("erp_ai_route")` → gọi hàm → `release_savepoint`. Ngoại lệ → `rollback(save_point=...)`, ghi `actions` `ok=false` + `error` lớp ngoại lệ, rồi xử lý theo từng bước dưới đây. Không thử lại bằng `db.set_value` (ADR-020 QĐ 6).

1. **(u1)** `apply_route(decision, classification, ctx)`.
   - Ngoại lệ, ví dụ `condition` SLA lỗi → dừng (u2)–(u4) và kiểm SLA (AC-18).
   - `ok=false` (người đã phân loại, AC-7b; thiếu quyền) → dừng như trên. Nhật ký có lý do.
   - `ok=true` → tiếp, kể cả khi không đổi nhóm hay ưu tiên (E, ADR-020 QĐ 6).
2. **Kiểm SLA** (đọc, không ghi; D-9): `fact = site_facts.applied_sla(ticket)`.
   - `None` → action `sla_check` `ok=false` "chưa có SLA áp vào phiếu", log warning, thêm câu `NO_SLA` (AC-11).
   - Có → `lag = sla_lag(cat, fact.resolution_s, routing)`; có lệch → action `sla_check` `ok=false` "SLA <tên> xử lý <a> phút > mong đợi <b> phút (<cat>)" và log warning (AC-12).
3. **(u2)** chỉ khi `auto_assign`:
   - `existing = site_facts.ticket_assignments(ticket)`, xét **sau** (u1) (ADR-020 QĐ 2).
     - Có → action `assign_owner` `ok=false` "phiếu đã có người được gán: <user...>", kèm `rule` = `assignment_rule` của ToDo đầu tiên có giá trị. Không Task, không comment phân công (AC-6 Amendment, AC-7a, A-12).
     - `decision.assignee is None` → action `ok=false` với note của quyết định, thêm câu `ASSIGN_REQUEST` "cấu hình không có người hợp lệ" (AC-8).
     - Còn lại → `assign_owner`. Ok → `assigned = user`. Ngoại lệ hoặc `ok=false` → câu `ASSIGN_REQUEST` "gán người không thành công".
4. **(u3)** chỉ khi `assigned` và `decision.needs_task`:
   - `site_facts.has_linked_task(ticket)` → action `create_routed_task` `ok=false` "phiếu đã có Task liên kết" (AC-13).
   - Ngược lại → `create_routed_task(assigned, ...)`. Task và lần giao Task chung một savepoint (ADR-020 QĐ 7). Ngoại lệ (chia sẻ bị tắt) → rollback cả Task lẫn ToDo của Task, `ok=false`, câu `ASSIGN_REQUEST` "không giao được Task…" (AC-13 i).
5. **(u4)** có câu nào → `post_routing_comment(lines, ctx)`, tối đa 1 comment. Ngoại lệ → `ok=false`, không thử lại.
6. Cập nhật bản ghi `classify` một lần (3.5) bằng `frappe.db.set_value(LOG_DOCTYPE, ...)` (runner, ngoài `tools/`, như `runner.py:280`). Thêm một dòng `frappe.logger("erp_ai").info("erp_ai route ticket=%s run_id=%s applied=%d assigned=%d task=%d comment=%d sla=%s", ...)` (STD-OPS-5: chỉ mã và số).
7. Commit một lần khi không chạy test (D-6).

### 4.3 Luồng lỗi theo tiêu chí
| Tình huống | Kết quả |
|---|---|
| Điểm sai hoặc thiếu (AC-1) | Bộ đọc trả 0/0/"". Ưu tiên lấy theo ánh xạ. Nhật ký `predicted_score_reason = "không có điểm"`. Từ `L1`, phiếu có 0/0/"" |
| `routing_rules` hỏng trên DB (bị ghi vòng qua form) | `{}` → không người, không mức tối thiểu, không kiểm SLA. Nhật ký `error` "routing_rules không hợp lệ". Công tắc bật thì có comment xin phân công |
| (u1) lỗi do `condition` (AC-18) | Rollback (u1). Phiếu trước = sau. 0 ToDo, 0 Task, 0 comment định tuyến. Nhật ký có lớp ngoại lệ, không có nội dung phiếu. Job kết thúc bình thường; bước suy luận chạy như cũ (D-16) |
| Nhóm có Assignment Rule bật và có user (AC-6 Amendment) | Rule gán ngay trong lần lưu (u1). (u2) thấy ToDo nên không gán, nhật ký có tên rule, 0 Task |
| Người cấu hình chưa là HD Agent hoặc là tài khoản agent (AC-6, AC-8) | Không gán. 1 comment xin phân công. 0 Task |
| `disable_document_sharing` bật (AC-13 i) | (u2) đã gán phiếu: role `Agent` có `share` trên HD Ticket, và người được giao là HD Agent nên đọc được phiếu. (u3) bị rollback, `ok=false`, 1 comment |
| Chạy lại cùng phiếu (AC-13) | (u2) thấy ToDo của lần trước nên không gán, (u3) không chạy. `has_linked_task` là lớp chặn thứ hai |
| Hai job song song cùng phiếu | Job sau chờ khóa dòng của (u1), rồi thấy ToDo nên không gán thêm (D-6) |

Không có lời gọi ra ngoài mới. Lời gọi model duy nhất vẫn là lời gọi phân loại với `deadline` sẵn có (`runner.py:205-210`, ADR-003). Bước định tuyến chỉ gồm vài truy vấn và tối đa 4 lần ghi trong job 600 giây (NFR-3).

### 4.4 Eval offline (`eval/run_eval.py`; AC-15)
- `_predict(row, routing, mapping)` trả `{"category", "complexity", "importance", "priority", "agent_group", "output_tokens", "stop_reason"}`. `priority`/`agent_group` lấy từ `decide_route` với cùng 3 hàm hỏi của site. Request là `build_classify_request(..., departments(routing))`, dùng chung với runner.
- `compute_metrics(rows, mapping)` vẫn là hàm thuần, thêm vào kết quả:
  - `priority` = `{"count", "correct", "accuracy"}` trên các dòng có `priority` nhãn và `predicted_priority` không None;
  - `team` = cùng dạng, trên các dòng có `agent_group` nhãn;
  - `score_distribution` = `{"complexity": {0..3: n}, "importance": {0..3: n}}`;
  - `classify_output_tokens_max` và `classify_max_tokens_hits`.
- `format_report` in thêm 4 khối này. Ngưỡng 0,85/0,70 chỉ dùng để đọc kết quả, không làm cổng (A-8).

## 5. Quyền

| Ai | Làm gì | Kiểm ở đâu |
|---|---|---|
| Tài khoản agent, tập role {`ERP AI Agent`, `Agent`} (ADR-021 QĐ 1) | (u1) lưu HD Ticket với các trường AI | `doc.has_permission("write")` + `has_permlevel_access_to(field, "write")` cho từng trường trong `apply_route`. Permlevel 8 của role `Agent` (research-site mục 5) |
| như trên | (u2) gán phiếu | `assign_to.add` kiểm quyền `read` của người gọi (`assign_to.py:85-86`). ToDo và Notification Log là bản ghi phụ, Frappe tạo bỏ quyền: ngoại lệ có tên của ADR-021 QĐ 3 |
| như trên | (u3) tạo Task, ghi `ai_ticket`, giao Task, chia sẻ Task | `frappe.has_permission("Task", "create")`. Dòng Custom DocPerm `if_owner` có `share=1` (ADR-021 QĐ 2). `add_docshare` kiểm `share` của người gọi trên Task do chính nó tạo |
| như trên | (u4) comment | `post_comment` như hiện nay (`write_ticket.py:73-83`) |
| Lõi agent (`site_facts`) | Đọc ToDo, Task, HD Agent, HD Team, SLA | Đọc hệ thống chỉ-đọc (`frappe.db.get_value`/`exists`/`get_all`), ngoài `tools/` (ADR-019 QĐ 3, ADR-021 QĐ 4). Kết quả chỉ dùng để quyết định, không đưa cho model hay vào comment |
| System Manager | Sửa `routing_rules`, `auto_assign_enabled` | DocPerm của ERP AI Setting (chỉ System Manager, `erp_ai_setting.json` mục permissions). Kiểm dữ liệu ở `validate` (biên vào, STD-ERR-2) |
| User role `Agent` | Đọc điểm trên phiếu (AC-2) | Permlevel 8 có `read` cho `Agent` + dòng template `visible_to = Agents` |
| Model | Không chọn được người, SLA, ưu tiên hay điểm | Không `ToolSpec` nào có thuộc tính như vậy. `route_ticket` không nằm trong `TOOL_MODULES`, nên `execute_tool` trả "không được cấp" (ADR-019 Ràng buộc; AC-9) |

- Nội dung phiếu là dữ liệu (STD-SEC-5). Model chỉ ảnh hưởng tới đầu mục, hai điểm (trần `High`, riêng A quan trọng 3 → `Urgent`, A-11) và tên bộ phận (chỉ dùng khi khớp bảng cấu hình).
- Trong `erp_ai/**` không có `ignore_share_permission`, `assign_to._add(`, `add_docshare`/`frappe.share.add` (ADR-021 Ràng buộc).
- Bằng chứng quyền (AC-17): mọi ca thành công chạy dưới tập role được ghim bằng helper `pin_agent_roles(testcase)` trong `erp_ai/test_utils.py`. Helper làm các bước sau:
  - đọc tập Has Role hiện tại của `AGENT_USER`;
  - đặt đúng {`ERP AI Agent`, `Agent`} (trừ `AUTOMATIC_ROLES`);
  - `addCleanup` khôi phục đúng tập cũ, đăng ký **sau** `addCleanup(frappe.db.rollback)` để chạy trước rollback;
  - khẳng định số Has Role trước = sau.
  Không dựa vào 99 role trên site (ADR-021 QĐ 6).

## 6. Migration và rollback

Có thay đổi dữ liệu, chạy bằng `cmd.migrate` (hook `after_migrate` → `ensure_setup`).

- **Lên** (`cmd.migrate` trên site dev; dev chạy trên bản sao, qa chạy lên/xuống/lên):
  1. DocType JSON: ERP AI Setting +2 trường; ERP AI Log +4 cột. Frappe tự `ALTER`.
  2. `ensure_setup`:
     - `_ensure_ticket_custom_fields` tạo 3 trường điểm. `ALTER ... ADD COLUMN ai_complexity int NOT NULL DEFAULT 0`, nên mọi phiếu cũ nhận 0 ngay;
     - `_ensure_template_rows` thêm 3 dòng template;
     - `_ensure_task_ticket_field` (mới) tạo `ai_ticket` trên Task;
     - `_ensure_task_permission` tạo dòng như cũ nếu chưa có. Có rồi thì chỉ bật `share` 0 → 1 trên đúng dòng (`parent="Task"`, `role=ROLE_AGENT`, `permlevel=0`, `if_owner=1`), rồi `clear_cache(doctype="Task")`;
     - `_ensure_default_settings` ghi mặc định `routing_rules` và `auto_assign_enabled=0` khi DB đang NULL.
  3. Chạy lại `ensure_setup` lần hai không đổi gì (idempotent; test cài đặt chạy hai lần).
  4. Bảng lớn: không có. Không có bước chép hay tính lại dữ liệu theo dòng, chỉ `ALTER ADD COLUMN` có giá trị mặc định. Vài chục phiếu mỗi tháng, nên không cần chia lô.
- **Xuống** (người làm, không agent nào làm trên dữ liệu thật, STD-OPS-7; ADR-007 cấm thêm chỗ xóa trong mã app):
  1. Hoàn tác hành vi, không cần deploy: `auto_assign_enabled = 0` → 0 ToDo, 0 Task mới (AC-7c). Muốn không ghi gì nữa thì `permission_level = L0`. Muốn quay về ưu tiên theo ánh xạ thì đặt `importance_priority` = `{"1": "", "2": "", "3": ""}`.
  2. Gỡ mã: revert các commit của feature, rồi chạy `cmd.migrate`. Phải revert mã **trước**, vì nếu không thì `after_migrate` tạo lại trường.
  3. Gỡ trường (tùy chọn). Trong `bench console` của site, người xóa 4 Custom Field `HD Ticket-ai_complexity`, `HD Ticket-ai_importance`, `HD Ticket-ai_score_reason`, `Task-ai_ticket` và 3 dòng template tương ứng, đặt `share = 0` trên dòng Custom DocPerm Task của app, rồi `frappe.clear_cache()`. Cột DB còn lại không gây hại (Frappe không tự xóa cột). Các cột thêm trên ERP AI Log và giá trị thừa trong `tabSingles` cũng không gây hại.
- **Đối soát** (qa, mỗi chiều; câu `SELECT` qua `bench --site miyano mariadb`):
  - số dòng `tabHD Ticket`, `tabTask`, `tabToDo`, `tabERP AI Log`, `tabComment` trước = sau lần migrate;
  - lên: `SELECT COUNT(*) FROM tabHD Ticket WHERE ai_complexity=0 AND ai_importance=0` = tổng số phiếu; `SELECT COUNT(*) ... WHERE ai_complexity IS NULL` = 0;
  - dòng Custom DocPerm Task của app: `read, write, create, share = 1`; `delete, submit, cancel, amend = 0`; `if_owner = 1`;
  - Has Role của tài khoản agent trước = sau;
  - giá trị `category_mapping`, `excluded_teams`, `permission_level` trước = sau (cài lại không ghi đè).
- **Điều kiện rollback:** một trong các dấu hiệu sau xuất hiện sau khi bật công tắc trên site:
  - log có `route apply_route:` với lớp lỗi lặp lại trên nhiều phiếu;
  - có phiếu bị gán hai người;
  - có Task không người được giao.
  Khi đó tắt công tắc. Rollback thành công khi phiếu mới không sinh thêm ToDo hay Task (đếm bằng câu `SELECT` ở trên).
- **Quan sát** (STD-OPS-5): mỗi lần định tuyến có một dòng `erp_ai route ...` (4.2 bước 6) và bản ghi `classify` có `actions`. Đủ để `/team:release` chứng minh feature chạy.

## 7. Touchpoints

| file | change | ghi chú |
|---|---|---|
| erp_ai/agent/routing.py | mới | `RouteDecision`, `decide_route` (R1–R5, nhóm, người, cần Task), `sla_lag`, `departments`, `load_routing_config`, `validate_routing_config`, `DEFAULT_ROUTING_RULES` (ADR-019 QĐ 3–4, 6) |
| erp_ai/agent/site_facts.py | mới | 5 phép đọc hệ thống chỉ-đọc ở 3.2 (ADR-019 QĐ 3, 5; ADR-021 QĐ 4) |
| erp_ai/agent/tools/route_ticket.py | mới | (u1)–(u4), hằng câu chữ 3.6. Không `TOOLS`, không `ToolSpec` (ADR-019 Ràng buộc) |
| erp_ai/agent/classification.py | sửa | `Classification` `:27-35` thêm 4 trường; `parse_classification` `:53-76` đọc điểm, lý do, bộ phận (D-4); xóa `resolve_ticket_values` `:116-122` (D-12); thêm `SCORE_VALUES` |
| erp_ai/agent/prompts.py | sửa | `CLASSIFY_PROMPT` `:55-65` thêm thang điểm và 4 khóa; xóa `ROUTING_TABLE` `:134-144` (AC-14); `build_classify_request` `:166-171` thêm `departments`; `build_reason_system` `:174-178` thêm `routing_table`; thêm `build_routing_table` |
| erp_ai/agent/runner.py | sửa | import `:11-12`; `CLASSIFY_MAX_TOKENS` `:32` → 600; bước (b)/(e) `:88-103` nạp `routing`, đọc công tắc; `ToolContext` `:119-126`; `_classify` `:195-246` dùng `decide_route` và 4 cột log; thay `_apply_classification` `:249-286` bằng `_route` (4.2); `_reason` `:306` truyền `routing_table` |
| erp_ai/agent/policy.py | sửa | thêm `auto_assign_enabled(settings)`, `is_excluded_team(team)` sau `:38`, dùng `_normalize` `:18-19` |
| erp_ai/agent/tools/registry.py | sửa | `ToolContext` `:12-19` thêm `routing_config: dict \| None = None` (trường cuối). `TOOL_MODULES` `:30-34` **không** đổi |
| erp_ai/agent/tools/write_ticket.py | sửa | import `:4`; `_mapped_values` `:24-36` gọi `decide_route` (D-14), tách `_existing_values`; `create_task` `:86-108` đặt `ai_ticket`, tách `_ticket_link_html` |
| erp_ai/install.py | sửa | `ensure_setup` `:41-49` thêm `_ensure_task_ticket_field`; `_ai_field_specs` `:114-153` thêm 3 trường; `_ensure_task_permission` `:184-205` bật `share` |
| erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json | sửa | `section_routing` `:181-199` thêm `auto_assign_enabled`, `routing_rules` (có description) |
| erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py | sửa | import `:5`; `validate` `:56-62` gọi `validate_routing_config(self.routing_rules)` |
| erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json | sửa | `section_prediction` `:219-264` thêm 4 cột (có description) |
| erp_ai/eval/run_eval.py | sửa | import `:7-9`; `compute_metrics` `:40-96`; `format_report` `:103-125`; `_predict` `:128-142`; `run` đọc `routing_rules` (4.4) |
| erp_ai/test_utils.py | sửa | thêm `pin_agent_roles`, `make_routing_rules`, `make_sla` (SLA tự tạo có `condition`), `make_team` (có/không rule), `make_active_agent` |
| erp_ai/agent/test_routing.py | mới | test hàm thuần: ưu tiên 36 ca, nhóm, người, `sla_lag`, cấu hình; nhận các ca `resolve_ticket_values` chuyển từ `test_classification.py` |
| erp_ai/agent/test_site_facts.py | mới | test 5 phép đọc dưới tập role đã ghim |
| erp_ai/agent/tools/test_route_ticket.py | mới | test (u1)–(u4) với Helpdesk thật (SLA, rule, chia sẻ Task) |
| erp_ai/agent/test_runner_routing.py | mới | test đầu-cuối qua runner + `FakeGateway`: AC-6..AC-18, NFR-1/2/4 |
| erp_ai/agent/test_classification.py | sửa | `TestParseClassification` `:30` thêm ca điểm; `TestResolveTicketValues` `:162-220` chuyển sang `test_routing.py`; `TestPrompts` `:221-262` theo `build_reason_system` mới và bảng routing từ cấu hình |
| erp_ai/agent/test_agent_runner.py | sửa | `:11`, `:791` gọi `build_reason_system` theo chữ ký mới |
| erp_ai/agent/test_policy.py | sửa | test 2 hàm policy mới |
| erp_ai/agent/tools/test_registry.py | sửa | AC-9 test tĩnh schema; `execute_tool` từ chối tên hàm định tuyến |
| erp_ai/agent/tools/test_write_ticket.py | sửa | `set_classification` cùng ưu tiên với (u1); `create_task` đặt `ai_ticket` |
| erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py | sửa | AC-4: lưu cấu hình sai bị chặn, mặc định hợp lệ |
| erp_ai/eval/test_run_eval.py | sửa | AC-15 các chỉ số mới |
| erp_ai/tests/test_install.py | sửa | trường điểm Int/0/permlevel 8; `ai_ticket`; `share`; tập role; idempotent |
| erp_ai/tests/test_architecture.py | sửa | `POLICY_FIELDS` `:104` thêm `auto_assign_enabled`; các luật mới của ADR-019..021 (mục 8) |

Đối chiếu đường dẫn mới với `allowed_new_file_roots` (`["erp_ai", "docs", ".github"]`):
```
erp_ai/agent/routing.py                  -> erp_ai
erp_ai/agent/site_facts.py               -> erp_ai
erp_ai/agent/tools/route_ticket.py       -> erp_ai
erp_ai/agent/test_routing.py             -> erp_ai
erp_ai/agent/test_site_facts.py          -> erp_ai
erp_ai/agent/tools/test_route_ticket.py  -> erp_ai
erp_ai/agent/test_runner_routing.py      -> erp_ai
```
`protected_paths` = `.env`, `.env.*`, `**/*.pem`, `**/*.key`, `license.txt`. **0 touchpoint nằm trong protected_paths.** Mọi touchpoint là `.py` hoặc `.json` dưới `erp_ai/`.

Tài liệu người dùng, As-Built và CHANGELOG thuộc `/team:asbuilt` sau G4 (spec DoD). Không phải touchpoint của build.

## 8. Test plan

Mọi ca thành công chạy dưới `pin_agent_roles` (AC-17). Test tự tạo team, HD Agent, SLA (tiền tố `PREFIX`); không dùng team `IT`, SLA `Standard`/`SLA Priority` hay HD Agent có sẵn (A-13). Lệnh chạy một file là slot `cmd.test_one`, cả bộ là slot `cmd.test`.

| Tiêu chí | Test | Loại | Ca biên / lỗi |
|---|---|---|---|
| AC-1 | erp_ai/agent/test_classification.py::TestParseClassification::test_scores_valid_each_level | unit | 1, 2, 3 cho từng điểm |
| AC-1 | erp_ai/agent/test_classification.py::TestParseClassification::test_bad_scores_mean_no_score | unit | 0, 4, `"2"`, `true`, `2.0`, thiếu khóa, một điểm đúng một điểm sai → 0/0/"" và đầu mục vẫn giữ |
| AC-1 | erp_ai/agent/test_classification.py::TestParseClassification::test_score_reason_cut_to_25_words | unit | 26 từ → 25 |
| AC-1 | erp_ai/agent/test_runner_routing.py::TestRoutingLog::test_l0_entry_has_scores_ticket_unchanged | integration | `L0`: nhật ký có điểm; mọi trường phiếu trước = sau; `ai_complexity` khác NULL |
| AC-1 | erp_ai/agent/test_runner_routing.py::TestRoutingLog::test_l1_no_score_writes_zero_logs_no_score | integration | `L1` + điểm sai → phiếu 0/0/"", nhật ký "không có điểm", ưu tiên theo ánh xạ |
| AC-2 | erp_ai/agent/tools/test_route_ticket.py::TestApplyRoute::test_scores_written_readable_by_agent_role_user | integration | user chỉ có role `Agent` đọc được 3 trường |
| AC-2 | erp_ai/agent/test_runner_routing.py::TestRoutingLog::test_l0_entry_has_scores_ticket_unchanged | integration | `L0` không đổi giá trị nào |
| AC-3 | erp_ai/agent/test_routing.py::TestDecidePriority::test_priority_matrix_36_cases | unit (tham số) | A–F × quan trọng 1–3 × có/không `[GẤP]`; cả `[GẬP]` |
| AC-3 | erp_ai/agent/test_routing.py::TestDecidePriority::test_spec_samples | unit | B2→High, C1→Medium, A3→Urgent, F3→Low, E→None |
| AC-3 | erp_ai/agent/test_runner_routing.py::TestRoutingEndToEnd::test_priority_from_scores_through_runner | integration | B + quan trọng 2 → phiếu `High` |
| AC-3 | erp_ai/agent/tools/test_write_ticket.py::TestSetClassification::test_same_priority_as_route | integration | cùng đầu vào → cùng `priority` qua `set_classification` và (u1) (ADR-019 Ràng buộc) |
| AC-4 | erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py::TestRoutingRules::test_bad_rules_blocked_with_location | integration | không phải JSON; khóa gốc lạ; mức `Hgh`; thiếu khóa "3"; đầu mục `D` trong assignees; user không tồn tại; phút âm → `ValidationError`, câu báo có đường dẫn |
| AC-4 | erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py::TestRoutingRules::test_default_rules_valid | integration | mặc định cài đặt lưu được |
| AC-4 | erp_ai/agent/test_runner_routing.py::TestRoutingEndToEnd::test_changed_importance_table_used_next_run | integration | đổi 2 → `Medium`, lần chạy sau B2 → `Medium` |
| AC-5 | erp_ai/agent/test_routing.py::TestDecideTeam::test_abcf_team_from_mapping | unit | — |
| AC-5 | erp_ai/agent/test_routing.py::TestDecideTeam::test_de_team_from_department | unit | tên bộ phận khác hoa/thường, thừa khoảng trắng |
| AC-5 | erp_ai/agent/test_routing.py::TestDecideTeam::test_de_team_skip_reasons | unit | không có bộ phận; bộ phận không trong bảng; nhóm không tồn tại; nhóm bị loại trừ → `None` + note |
| AC-5 | erp_ai/agent/test_policy.py::TestPolicy::test_is_excluded_team_same_normalization | unit | khớp `can_send_ticket` |
| AC-6 | erp_ai/agent/test_runner_routing.py::TestRoutingAssign::test_assigns_configured_person_one_notification | integration | nhóm không có rule: 1 ToDo mở, +1 Notification Log của người đó |
| AC-6 | erp_ai/agent/test_routing.py::TestDecideAssignee::test_prefix_overrides_default | unit | `[tracecore]` ở đầu, ở sau `[GẤP]`, khác hoa/thường |
| AC-6 | erp_ai/agent/test_routing.py::TestDecideAssignee::test_inactive_or_missing_agent_not_chosen | unit | HD Agent `is_active=0`; không có HD Agent → note |
| AC-6 | erp_ai/agent/test_runner_routing.py::TestRoutingAssign::test_team_rule_assigns_bot_does_not | integration | nhóm có rule bật có user: 0 ToDo của bot, đúng 1 ToDo của rule, nhật ký có tên rule, 0 Task |
| AC-6 | erp_ai/agent/tools/test_route_ticket.py::TestAssignOwner::test_ticket_never_shared_one_todo_one_notification | integration | ADR-021 Ràng buộc (u2) |
| AC-7 | erp_ai/agent/test_runner_routing.py::TestRoutingNoOverride::test_existing_assignment_kept | integration | (a) người gán trước → danh sách không đổi |
| AC-7 | erp_ai/agent/test_runner_routing.py::TestRoutingNoOverride::test_rule_assignment_in_route_save_kept | integration | (a) rule gán ngay trong (u1) |
| AC-7 | erp_ai/agent/test_runner_routing.py::TestRoutingNoOverride::test_human_classified_no_route_writes | integration | (b) nhóm, ưu tiên, người không đổi; 0 ToDo, 0 Task |
| AC-7 | erp_ai/agent/test_runner_routing.py::TestRoutingNoOverride::test_switch_off_no_todo_no_task | integration | (c) phân loại vẫn ghi |
| AC-7 | erp_ai/agent/test_runner_routing.py::TestRoutingNoOverride::test_l0_no_todo_no_task | integration | (d) |
| AC-8 | erp_ai/agent/test_runner_routing.py::TestRoutingAssign::test_agent_account_never_assigned_one_comment | integration | cấu hình trỏ tới `AGENT_USER` → 0 ToDo cho tài khoản đó, đúng 1 comment |
| AC-8 | erp_ai/agent/test_routing.py::TestDecideAssignee::test_agent_user_never_chosen | unit | kể cả khi tài khoản agent là HD Agent đang hoạt động |
| AC-9 | erp_ai/agent/test_runner_routing.py::TestRoutingInjection::test_ticket_text_does_not_steer_route | integration | phiếu ghi "giao cho Administrator", "SLA 1 phút", "đặt Urgent"; stub phân loại và stub suy luận gọi `set_classification` + tool lạ `assign` → người theo cấu hình, ưu tiên R2–R5, tool lạ `ok=false` |
| AC-9 | erp_ai/agent/tools/test_registry.py::TestRegistry::test_no_tool_schema_takes_person_sla_priority_or_score | unit (tĩnh) | mọi `ToolSpec` của `TOOL_MODULES`; schema `set_classification` trùng bản nền |
| AC-9 | erp_ai/agent/tools/test_registry.py::TestRegistry::test_route_functions_not_executable_as_tools | unit | `execute_tool("apply_route", ...)` → "không được cấp" |
| AC-10 | erp_ai/agent/tools/test_route_ticket.py::TestSlaFromHelpdesk::test_sla_chosen_by_complexity_condition | integration | SLA mặc định tự tạo + SLA `doc.ai_complexity == 3`; phiếu 3 → SLA thứ hai, phiếu 1 → mặc định; cả hai có `response_by`/`resolution_by` |
| AC-10 | erp_ai/agent/tools/test_route_ticket.py::TestSlaFromHelpdesk::test_ge_condition_saves_l0_and_new_ticket | integration | `doc.ai_complexity >= 3` đang bật: tạo phiếu mới và chạy `L0` → không lỗi |
| AC-10 | erp_ai/tests/test_architecture.py::TestArchitecture::test_feature_never_assigns_sla_dates | unit (tĩnh) | không có phép gán `response_by`/`resolution_by` trong `erp_ai/agent/` |
| AC-11 | erp_ai/agent/test_runner_routing.py::TestRoutingSla::test_no_sla_one_warning_one_comment | integration | tắt mọi SLA đang bật (cả `Standard`, `SLA Priority`, SLA tự tạo) trong transaction test; ưu tiên đúng; 1 action `sla_check`; 1 comment `NO_SLA`; số SLA trước = sau |
| AC-12 | erp_ai/agent/test_routing.py::TestSlaLag::test_slower_sla_returns_two_numbers | unit | 600 phút > 480 |
| AC-12 | erp_ai/agent/test_routing.py::TestSlaLag::test_matching_sla_none | unit | bằng nhau → None |
| AC-12 | erp_ai/agent/test_routing.py::TestSlaLag::test_d_e_not_checked | unit | `resolution_min` null |
| AC-12 | erp_ai/agent/test_runner_routing.py::TestRoutingSla::test_slow_sla_warning_in_log | integration | 1 action `sla_check` nêu 2 con số; 0 comment |
| AC-13 | erp_ai/agent/test_runner_routing.py::TestRoutingTask::test_c_ticket_one_linked_task_assigned | integration | đúng 1 Task `ai_ticket` = phiếu, giao cho người bot vừa gán |
| AC-13 | erp_ai/agent/test_runner_routing.py::TestRoutingTask::test_rerun_keeps_one_task | integration | chạy runner hai lần |
| AC-13 | erp_ai/agent/test_runner_routing.py::TestRoutingTask::test_existing_linked_task_no_new_task | integration | Task do người tạo có `ai_ticket` |
| AC-13 | erp_ai/agent/test_runner_routing.py::TestRoutingTask::test_other_category_or_no_person_no_task | integration | A → 0 Task; C không có người → 0 Task + 1 comment |
| AC-13 | erp_ai/agent/test_runner_routing.py::TestRoutingTask::test_sharing_disabled_no_task_one_comment | integration | (i) `disable_document_sharing=1`, người được giao không có `Projects User` → 0 Task, 0 ToDo của Task, 1 comment, `ok=false` |
| AC-13 | erp_ai/agent/test_runner_routing.py::TestRoutingTask::test_preassigned_by_human_no_task_no_comment | integration | (ii) |
| AC-13 | erp_ai/agent/test_runner_routing.py::TestRoutingTask::test_preassigned_by_rule_no_task_no_comment | integration | (ii) rule gán trong (u1) |
| AC-13 | erp_ai/agent/tools/test_route_ticket.py::TestCreateRoutedTask::test_assignee_without_projects_user_gets_share | integration | ADR-021 Ràng buộc (u3) |
| AC-14 | erp_ai/agent/test_runner_routing.py::TestRoutingAssign::test_changed_default_person_assigned_next_run | integration | đổi người của B → phiếu B kế tiếp gán người mới |
| AC-14 | erp_ai/agent/test_classification.py::TestPrompts::test_routing_table_shows_configured_people | unit | prompt trước/sau khi đổi cấu hình khác nhau đúng ở tên người |
| AC-14 | erp_ai/tests/test_architecture.py::TestArchitecture::test_no_default_people_in_agent_python | unit (tĩnh) | các tên 16.2 (Việt, Tiến, Hiếu, Lan, Hà, Thư, Chi) và `ai.agent` dạng tên người không có trong `.py` dưới `erp_ai/agent/` |
| AC-15 | erp_ai/eval/test_run_eval.py::TestRunEval::test_priority_team_match_and_score_distribution | unit | dòng không có nhãn ưu tiên; E (dự đoán None) không tính vào mẫu số |
| AC-15 | erp_ai/eval/test_run_eval.py::TestRunEvalRun::test_eval_uses_runner_route_function | integration | cùng `build_classify_request` (có `departments`) và cùng `decide_route` |
| AC-15 | bước kiểm của qa: chạy export + eval trên site dev, dán đầu ra (có `classify_output_tokens_max`) vào acceptance.md | check step | đo trần token (D-8) |
| AC-16 | erp_ai/agent/test_runner_routing.py::TestRoutingLog::test_every_write_in_actions_with_before_after | integration | ưu tiên, nhóm, người (user ID), Task |
| AC-16 | erp_ai/agent/test_runner_routing.py::TestRoutingLog::test_refusals_have_ok_false_reason | integration | người đã phân loại; đã có người; đã có Task |
| AC-17 | erp_ai/agent/test_runner_routing.py::TestRoutingPermissions::test_success_cases_under_pinned_roles | integration | đầu ca khẳng định tập role = {`ERP AI Agent`, `Agent`}; số Has Role trước = sau |
| AC-17 | erp_ai/agent/test_runner_routing.py::TestRoutingPermissions::test_privilege_findings_unchanged | integration | `tasks._agent_role_drift`, `_permission_records_by_agent`, `_enabled_scripts_by_agent` trước = sau |
| AC-17 | erp_ai/tests/test_install.py::TestInstall::test_task_permission_share_and_role_set | integration | chạy cài đặt hai lần: dòng Task có `share=1`, các cờ khác như ADR-021; dòng của role khác còn nguyên; tập role đúng 2 |
| AC-17 | `cmd.test` (cả bộ xanh) | suite | — |
| AC-18 | erp_ai/agent/test_runner_routing.py::TestRoutingSla::test_broken_sla_condition_stops_route_cleanly | integration | tạo phiếu, bật SLA có `condition` ném lỗi, chạy `L1`, công tắc bật → không ngoại lệ lọt ra; nhật ký có lớp lỗi, không có nội dung phiếu; 0 ToDo, 0 Task, 0 comment định tuyến; phiếu trước = sau; không có `db.set_value` trên HD Ticket |
| NFR-1 | erp_ai/agent/test_runner_routing.py::TestRoutingEndToEnd::test_model_call_count_unchanged | integration | `L0`: `["classify"]`; `L1`: `["classify", "reason"]` với stub 1 lượt, giống nhánh nền |
| NFR-2 | erp_ai/agent/test_runner_routing.py::TestRoutingEndToEnd::test_no_helpdesk_config_records_created | integration | đếm HD Service Level Agreement, HD Team, Assignment Rule trước = sau |
| NFR-3 | erp_ai/agent/test_agent_runner.py::TestRunner (lớp hiện có, giữ xanh) | integration | — |
| NFR-4 | erp_ai/agent/test_runner_routing.py::TestRoutingEndToEnd::test_fake_key_absent_from_comment_log_task | integration | gieo khóa giả vào credential; 0 lần xuất hiện trong Comment, ERP AI Log, mô tả Task |

Test của Ràng buộc ADR (không gắn với AC riêng; tất cả trong `erp_ai/tests/test_architecture.py::TestArchitecture`):
- `test_route_module_not_in_tool_modules_and_has_no_tools`;
- `test_route_module_single_ticket_save`: đúng một `save` HD Ticket, ở `apply_route`;
- `test_assign_to_only_in_route_module`;
- `test_no_share_bypass`: `ignore_share_permission`, `assign_to._add(`, `add_docshare`, `frappe.share.add`;
- `test_auto_assign_switch_only_in_policy`: qua `POLICY_FIELDS`;
- `test_entry_types_unchanged`;
- `test_assign_field_not_used_for_decision`: `"_assign"` trong `erp_ai/agent/**`;
- `test_route_module_bypass_rules_apply`: `check_tools_never_bypass_permissions` phủ `route_ticket.py`.

Thêm: `erp_ai/tests/test_install.py::TestInstall::test_score_fields_int_default_zero_permlevel_8` và `erp_ai/agent/test_site_facts.py::TestSiteFacts::test_assignments_include_closed_exclude_cancelled`.

**Đối chiếu danh sách AC.**
- Spec: AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18 (18) + NFR-1..NFR-4.
- Test plan: AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18 (18) + NFR-1..NFR-4.
- Hai danh sách khớp.
