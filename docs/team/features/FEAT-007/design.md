Feature: FEAT-007
Stage: design
Author-agent: designer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. G2b không áp dụng cho FEAT-007 (team.py: chỉ G5). -->

# Design FEAT-007 — Đợt 0: U0 Nền cấu hình, U4a Phân loại (ngoài lõi), U5a Vận hành (ngoài lõi), U6a Tri thức (hàm đọc)

## 1. Bối cảnh

**Phạm vi file này.** Đợt 0 của `arch-impact.md` mục "Đơn vị build và thứ tự merge": U0 → (U4a ∥ U5a ∥ U6a), build trên `team/FEAT-007` song song với FEAT-004 (N-3), merge vào `develop` sau `team/FEAT-004` và sau phần ADR-024 của FEAT-005. Các đơn vị U1–U3, U4b, U5b, U6b, U7, U8 được thiết kế sau trong `design-addendum-N.md`; file này chỉ chốt **hợp đồng** mà chúng sẽ dùng (tên trường, hằng, chữ ký hàm), không thiết kế hành vi của chúng.

**Đầu vào.** `spec.md` + `spec-addendum-1.md` (addendum thắng); `arch-impact.md`; `research.md`, `research-R1..R5.md`. Luật thiết kế: ADR-030 (5 công tắc, hai mức, một hàm cấp, cảnh báo bật), ADR-031 (danh mục trên ERP AI Setting, điều cấm cứng một nguồn), ADR-032 (công tắc (5)), ADR-033 (lịch `cron`, khóa chu kỳ cùng giao dịch, bảng chủ ghi, phiên agent không ghi Setting), ADR-034 (một vị từ phiếu loại trừ, Error Log đọc hệ thống, tìm CSKT bằng truy vấn của app, kho HDSD `.md`, Script Report, bot không xuất bản), ADR-023 (M3 danh sách cấm một nguồn, M5 chặn ghi của tài khoản agent), ADR-024 (mốc chỉ job ghi bằng `set_single_value`, khôi phục khi người lưu; app không đọc `Version`). ADR-001 (Cửa vào → Lõi → Cổng model), ADR-006 (cài đặt chỉ điền thiếu), ADR-021 QĐ 4 (đọc hệ thống chỉ-đọc ở Lõi).

**AC đợt 0 (theo cột "Gói / AC" của bảng đơn vị build).**
- U0: phần cấu hình của Gói 1–6 — AC-1 (cài mới, migrate), AC-4 (thông báo trên form), cấu hình của AC-12, AC-22, AC-24, AC-26, AC-29, AC-30, AC-31, AC-36, AC-38, AC-44, AC-46, AC-47, AC-49, AC-51, AC-55, AC-59, AC-63; NFR-4, NFR-7; STD-OPS-2 (lên/xuống).
- U4a: AC-16, AC-17 (phần báo cáo), AC-18, AC-19, AC-20 (ERP AI Accuracy), AC-25, AC-26, AC-27, AC-28.
- U5a: AC-51, AC-52, AC-53, AC-54, AC-55, AC-56, AC-59, AC-60; AC-20 (hai báo cáo mới).
- U6a: hàm đọc Error Log (AC-50), tìm CSKT (AC-46), tìm HDSD + loại khỏi `source.py` (AC-47), hook HD Article chặn xuất bản (AC-45 phần chặn); NFR-6 (hàm che dùng chung).

**Phần của AC chỉ xong ở đợt sau** (ghi để qa không nghiệm thu nhầm; test đợt 0 chỉ phủ phần đợt 0):

| AC | Phần đợt 0 | Phần còn lại, đơn vị |
|---|---|---|
| AC-1 | cài mới, migrate, migrate lần hai | hồi quy ảnh chụp M4: U1 |
| AC-4 | thông báo khi lưu | dòng nhật ký người bật, cảnh báo hằng ngày: U3 |
| AC-17 | 3 số trong báo cáo (độ trễ suy từ dấu thời gian, D-8) | — (không cần trường độ trễ riêng) |
| AC-19 | luật nhãn và cột trong báo cáo; trường `created_labels` | runner ghi `created_labels` trước khi ghi phiếu: U4b |
| AC-25 | luật trong `decide_route` | runner truyền giá trị Hạn hoàn thành: U4b |
| AC-26 | vị từ quá mốc, đếm trong báo cáo 08:00, dòng log | — |
| AC-27 | quyết định "người theo dõi" trong `decide_route` | ghi theo dõi dưới tài khoản agent: U4b |
| AC-28 | luật "phiếu gộp" + chữ comment | đăng comment, ghi cờ vào nhật ký: U4b |
| AC-45 | hook chặn xuất bản, trường liên kết phiếu nguồn | soạn bài (trigger runner): U6b |
| AC-46, AC-47, AC-50 | hàm Lõi | đăng ký tool, giới hạn từ cấu hình: U6b |
| AC-51 | báo cáo đủ mục | mục "C thiếu BA note" có dữ liệu thật khi U8 đăng BA note theo `BA_NOTE_MARKER` |

**Explore (2026-11-14, hai lệnh song song; `develop` @ `1918db2` là tổ tiên của `team/FEAT-004` @ `1dcc2f4`; các file dưới đây trùng byte giữa hai nhánh trừ ghi chú).** Cache `docs/team/explore/erp_ai.md` (2026-11-10) đã cũ nên không dùng.
- ERP AI Setting: Single, 27 trường dữ liệu, 7 section, một bảng con `credentials`; `validate` gọi `restore_self_managed_fields` (khôi phục `spent_this_month_usd` và trường tự quản của khóa), `INT_LIMITS`, `validate_mapping`, `validate_routing_config`, `policy.validate_change_apps` (`erp_ai_setting.py:58-130`). T65 (FEAT-004, nhánh `team/FEAT-004-task-65`) thêm `refuse_agent_write` vào `before_insert/validate/on_trash/...`. FEAT-005 T7 thêm `privilege_alert_checked_until` (Datetime, read-only) vào `section_alerts` và vào `restore_self_managed_fields`.
- `install._ensure_default_settings` điền mọi trường có `default` khi dòng `tabSingles` thiếu hoặc NULL, không ghi đè (`install.py:90-104`); trường tùy biến HD Ticket từ `_ai_field_specs` (permlevel 8, `install.py:123-182`); trường Task `ai_ticket` bằng `create_custom_fields(update=False)` (`:213-233`).
- `test_doctype_descriptions.py`: `DOCTYPE_CONFIG["ERP AI Setting"]` ghim `field_count` 27, cụm từ bắt buộc của mô tả (≤ 400 ký tự), `section_count` 7, `read_only_fields`, bộ ba section.
- `test_architecture.py:139` `POLICY_FIELDS` (gồm `unrestricted_enabled`, `code_change_enabled`) chỉ được xuất hiện trong `agent/policy.py` (luật quét `.py`, `:763`); `agent/tools/**` cấm `ignore_permissions`, `set_user`, `db.set_value`, `get_all` (trừ DocType) (`:623`).
- `routing.decide_route(classification, subject, mapping, config, *, team_exists, is_excluded_team, is_active_agent) -> RouteDecision` thuần, hai nơi gọi (`runner.py:281`, `write_ticket.py:50`); `_priority` đã có [GẤP]/[GẬP] → Urgent, F → Low, E không ghi, A ∧ độ quan trọng 3 → Urgent (`routing.py:135-150`); không đọc hạn, không có người theo dõi. `DEFAULT_ROUTING_RULES.expected_sla.<A..F>.response_min` = 15, 15, 60, 60, 60, 5 (`routing.py:21-28`) — đúng mặc định của AC-26.
- `classification.parse_classification` đọc khóa `dau_muc, do_tin_cay, ly_do, nhom, uu_tien, can_tach, cac_yeu_cau, do_phuc_tap, do_quan_trong, ly_do_diem, bo_phan`; `needs_split`, `requests` đã parse nhưng không ai dùng.
- ERP AI Accuracy: Script Report, `ref_doctype` ERP AI Log, `roles` chỉ System Manager, cột `category, predictions, corrected, pending, accuracy_pct`, "im lặng 7 ngày = đúng" (`erp_ai_accuracy.py:57-118`). Frappe đòi quyền `report` trên `ref_doctype` (`frappe/desk/query_report.py:57,283`); ERP AI Log chỉ cấp `report` cho System Manager.
- `handlers.py`: nhãn người gõ lúc tạo phiếu không được lưu ở đâu; sửa của người ghi vào `human_corrected_to/by/at` của dòng `classify` mới nhất.
- `queue.enqueue_agent_run(ticket, trigger)` nhận `ticket_insert`, `comment_mention`; `job_id = erp_ai::{ticket}::{trigger}`, hàng `long`, `deduplicate`. `policy.can_send_ticket`, `runs_today`, `is_enabled` có sẵn.
- `hooks.py:141-163`: `doc_events` HD Ticket, Comment; `scheduler_events` hourly 1, daily 2, chưa có `cron`; không có `has_permission`.
- `alerts._send_mail` = `frappe.sendmail(..., delayed=True)` tới `alert_recipients`.
- `source.py`: `get_source_root()` = thư mục `apps/`; `resolve_safe_path(rel)` (ngoài gốc, symlink, `TEN_CAM`, đuôi file); `search_source`, `git_source` đều đi qua `resolve_safe_path`.
- `site_api.FORBIDDEN_ROLES` (6 vai trò của FEAT-004 AC-31), `site_api.DENIED_DOCTYPES`, `read.denied_doctypes()` (gồm mọi DocType module app) là tên công khai; T59 của FEAT-004 đang đổi cách dựng hai tập của `site_api` (ADR-023 M3).
- `test_utils.set_agent_settings` ghi thẳng `set_single_value`, không có hàm trả lại.
- Helpdesk 15.1.0: HD Ticket có `first_responded_on`, `status_category` (Data), `resolution_by`, `resolution_date`, `raised_by`; HD Article có `title`, `content`, `status` (Published/Draft/Archived), `author`; Frappe có `frappe.desk.form.document_follow.follow_document`; `remove_orphan_doctypes` xóa bản ghi DocType mất file khi migrate, **không** xóa bảng (`frappe/model/sync.py:143-175`); lưu Single xóa và ghi lại toàn bộ dòng `tabSingles` theo meta (`document.py:699-711`).

### Để designer quyết — các mục đợt 0 cần (arch-impact "Để designer quyết", ADR "Phải làm thêm")

| # | Mục | Quyết định | Vì |
|---|---|---|---|
| D-1 | Lưu mức tối đa theo đầu mục (ADR-030 QĐ 2) | 6 trường Select `level_cap_a`..`level_cap_f`, mặc định L2, L3, L1, L2, L1, L3 | `_ensure_default_settings` điền được trường thiếu; bảng con hay JSON thì cài lại không phân biệt được "người đã xóa dòng" với "dòng chưa có" (ADR-006). |
| D-2 | Mốc phản hồi theo đầu mục (AC-26) | Dùng lại `routing_rules.expected_sla.<X>.response_min`, không thêm trường | Đã có, mặc định trùng AC-26, đã có kiểm lúc lưu (STD-DESIGN-4). |
| D-3 | Nơi lưu lịch sử ghi đè prompt (AC-38) | Bảng con chỉ-đọc `prompt_revisions` (DocType `ERP AI Prompt Revision`), controller khôi phục từ DB mỗi lần lưu rồi thêm dòng | App không đọc `Version` (ADR-024 Ràng buộc); bảng con được M5 của Setting che (không thêm DocType có quyền riêng). |
| D-4 | Hình dạng dòng danh mục, tên hành động (ADR-031) | Mục 2.2; 6 hành động có mã cố định | Một chỗ khai báo cho kiểm lúc lưu (U0) và bộ thực thi (U7). |
| D-5 | Trường mới của ERP AI Log | Thêm trong U0, mục 2.3 | Không đơn vị nào trong bảng arch-impact sở hữu `erp_ai_log.json`; gom vào đơn vị "nền" để chỉ một lần sửa JSON. **Lệch bảng file của arch-impact — báo team-leader.** |
| D-6 | Kiểu trường `actions` (ADR-024 Bối cảnh, ADR-033 Hệ quả) | Small Text → Long Text (nới, không mất dữ liệu) | Mục có trước/sau có thể vượt 64 KB. Cần chủ FEAT-004 T64 xác nhận (câu mở cho team-leader). |
| D-7 | Cách controller biết "5 công tắc" cho thông báo AC-4 | Đọc từ meta: mọi trường `Check` trong `section_permissions`; chữ hậu quả = `description` của trường | `POLICY_FIELDS` cấm tên công tắc trong `.py` ngoài `policy.py`; một nguồn chữ cho form và thông báo. |
| D-8 | Độ trễ phân loại (AC-17) | Suy ra: `creation` dòng `classify` thành công đầu tiên − `creation` phiếu; phiếu bị bỏ qua có chủ ý (không gửi được, đã điền đủ 3 trường) không vào 3 số | Dấu thời gian của dòng đã là "thời điểm có kết quả"; không thêm trường thứ hai cho cùng một sự thật. |
| D-9 | Nhãn và "đúng" (AC-19) | Mục 3.5.3 | Theo chữ AC-19; đổi nghĩa "im lặng = đúng" cũ → sửa test theo AC (NFR-8). |
| D-10 | Bù chu kỳ lịch bị lỡ (ADR-033 "Phải làm thêm") | 08:00: không bù; KPI tuần: bù các tuần thiếu, tối đa 8 tuần; rà soát tháng: chỉ tháng trước | Báo cáo ngày cũ hết giá trị; KPI tuần cần chuỗi để so (AC-55); rà soát tháng cũ không ai làm. |
| D-11 | Công thức KPI chi tiết (A-14 đã chốt hướng) | Mục 3.6.4 | Mọi KPI tính lại được từ dữ liệu theo mốc cuối tuần (không phụ thuộc giờ chạy). |
| D-12 | Tách từ cho tìm CSKT, HDSD | NFC + `casefold`, `\w+` Unicode, từ ≥ 2 ký tự, tối đa 8 từ, khớp nguyên từ, giữ dấu | ADR-034 QĐ 4 (giữ dấu tiếng Việt, xếp theo số từ khớp). |
| D-13 | Danh sách DocType "mang nội dung phiếu" (ADR-034 QĐ 3) | `TICKET_CONTENT_DOCTYPES = ("HD Ticket", "HD Ticket Comment", "Comment", "Communication", "File")` ∪ `read.denied_doctypes()` | Helpdesk lưu ghi chú nội bộ ở `HD Ticket Comment`; File chứa đính kèm phiếu. |
| D-14 | Độ tin cậy số và nhãn cũ | Trường mới `ai_confidence_pct` (Int) trên HD Ticket, `predicted_confidence_pct` trên ERP AI Log; nhãn cũ không quy đổi, giữ nguyên | AC-22 "nhãn cũ giữ cho dữ liệu cũ"; quy đổi nhãn → số là bịa dữ liệu. Hành vi ngưỡng: U1. |
| D-15 | Liên kết bài CSKT ↔ phiếu (ADR-034 QĐ 6) | Trường tùy biến `ai_source_ticket` (Link HD Ticket, read-only, có chỉ mục) trên HD Article, cài theo ADR-006 | Một bài một phiếu tra được bằng chỉ mục; người không sửa được trên form. |
| D-16 | Phạm vi quét 15 phút | Mục 3.5.1 | AC-16 + giới hạn lô cho job hàng `default` 300 s. |
| D-17 | Dòng log của việc theo lịch đợt 0 | Một dòng `frappe.logger("erp_ai")` mỗi lần chạy; lỗi → `frappe.log_error` có tiêu đề hằng | Việc đợt 0 không ghi gì vào phiếu, nên không thuộc "mục hành động" của ADR-033 QĐ 5; loại dòng không-phải-lần-chạy thuộc U3. |
| D-18 | Mốc xử lý cho "sắp quá hạn/quá hạn" | D, E có trường Hạn hoàn thành đã cấu hình và có giá trị → giá trị đó; còn lại → `HD Ticket.resolution_by` (SLA Helpdesk); không có → không xét | AC-26 câu cuối; SLA Helpdesk đã tính giờ làm việc (tài liệu: "4 giờ làm việc"). |
| D-19 | Tiền tố bộ phận loại trừ (AC-9, ADR-034 QĐ 1) | Trường `excluded_title_prefixes`, mặc định `[HR]` và `[Kế toán]` | Mặc định an toàn hơn khi loại nhiều hơn (NFR-4). Hành vi: U2. |
| D-20 | Một dạng lỗi | Kiểm lúc lưu: `frappe.throw(msg)` (ValidationError); hàm Lõi đợt 0: `frappe.throw(msg)` khi đầu vào sai, trả dữ liệu khi đúng; tool đợt sau đổi thành `{ok: False, reason}` | Giữ cách hiện có của controller và `read.py`. |

**Assumptions decided by the team** (kỹ thuật; không có câu nghiệp vụ mới — câu HDSD của `arch-impact.md` "Trả về người" vẫn mở, không chặn build vì kho mặc định rỗng):
- A-D1: Mô tả 5 công tắc trên form viết theo hành vi cuối của FEAT-007. Giữa lúc đợt 0 merge vào `develop` và lúc U1 merge, mô tả của ô (4) nói "không còn mở công cụ bản ghi" trong khi mã cũ vẫn mở. Chấp nhận: chỉ trên site dev; production chỉ nhận cả feature qua G5.
- A-D2: "Phiếu đang mở" tại mốc t = tạo trước t và (`resolution_date` rỗng hoặc ≥ t). Phiếu mở lại sau khi Resolved có thể bị đếm lệch; chấp nhận (vài chục phiếu/tháng).
- A-D3: Quét 15 phút không xét phiếu `status_category = "Resolved"` (đã xong thì phân loại vô ích).
- A-D4: KPI 5 xét phiếu C tạo trong cửa sổ 7 ngày lùi 3 ngày so với tuần tính (mục 3.6.4), để mỗi phiếu được tính đúng một lần và đã đủ 72 giờ.
- A-D5: Email báo cáo 08:00 liệt kê tiêu đề phiếu thường (đã che bí mật, D-12/NFR-6); phiếu loại trừ chỉ có mã phiếu.

**Phụ thuộc trong đợt 0 (tech-lead xếp thứ tự):** U0 trước mọi đơn vị (trường cấu hình). Phần AC-18 của controller (U0) gọi `l0_l1_gate` của U4a. U5a gọi `routing.response_overdue`, `routing.processing_deadline` (U4a) và `redact.redact_secrets` (U6a). Kiểm M5 (`refuse_agent_write`) cho DocType mới của U5a nối khi T65 đã ở `develop` (arch-impact). **Ngoài đợt:** FEAT-005 T7 sửa cùng `restore_self_managed_fields` và `DOCTYPE_CONFIG` (`field_count` 27 → 28): khi merge, số đếm của file này là "số thật trên nhánh nền + 49".

## 2. Mô hình dữ liệu

### 2.1 ERP AI Setting (Single) — trường mới, trường chuyển chỗ

Chỉ thêm trường; không đổi tên, không xóa (hợp đồng "chỉ thêm" của arch-impact). Mọi trường mới: mặc định tắt hoặc rỗng, trừ số kỹ thuật lấy từ tài liệu (A-13, bảng mục 3, mục 5). Thứ tự section sau U0 (field_order):

| # | Section (fieldname, nhãn) | Trường theo thứ tự |
|---|---|---|
| 1 | `section_activation` "Bật và mức quyền" | `enabled`, `permission_level`, **`agent_enabled_at`** |
| 2 | **`section_permissions`** "Năm quyền mở rộng (mặc định tắt)" | `unrestricted_enabled` (chuyển), **`record_tools_enabled`**, **`act_now_enabled`**, `code_change_enabled` (chuyển), **`one_click_approval_enabled`**, **`site_environment`** |
| 3 | **`section_autonomy`** "Mức tự chủ theo đầu mục và độ tin cậy" | **`level_cap_a`..`level_cap_f`**, **`confidence_threshold`**, **`auto_approve_streak`** |
| 4 | **`section_catalog`** "Danh mục trắng" | **`catalog_rules`**, **`user_templates`** |
| 5 | `section_limits` (giữ) | như cũ |
| 6 | `section_budget` (giữ) | như cũ |
| 7 | `section_model` (giữ) | như cũ |
| 8 | `section_routing` (giữ) | `excluded_teams`, **`excluded_title_prefixes`**, `category_mapping`, `auto_assign_enabled`, `routing_rules`, `prompt_digest` |
| 9 | **`section_ticket_fields`** "Trường sẵn có của phiếu" | **`field_ticket_nature`**, **`field_erp_module`**, **`field_origin`**, **`origin_board_value`**, **`field_due_date`**, **`field_project`**, **`field_item_code`**, **`field_serial_no`** |
| 10 | `section_code_change` (giữ, chỉ còn danh sách app) | `code_change_apps` |
| 11 | **`section_knowledge`** "Trả lời, đóng phiếu và tri thức" | **`reply_enabled`**, **`resolve_on_tasks_done_enabled`**, **`close_silent_f_enabled`**, **`close_silent_f_days`**, **`kb_draft_enabled`**, **`knowledge_search_limit`**, **`manuals_dir`**, **`allowed_reports`**, **`report_row_limit`** |
| 12 | **`section_operations`** "Báo cáo và vận hành" | **`coo_report_recipients`**, **`daily_report_weekends`**, **`monthly_reviewers`**, **`review_sample_size`**, **`d_ticket_watcher`**, **`due_reminder_hours`**, **`ba_note_due_hours`**, **`task_due_days`**, **`max_tasks_per_run`**, **`kpi_targets`**, **`daily_report_sent_on`**, **`budget_alert_sent_month`** |
| 13 | **`section_prompts`** "Ghi đè prompt" | **`prompt_override_classify`**, **`prompt_override_reasoning`**, **`prompt_override_category_guide`**, **`prompt_revisions`** |
| 14 | `section_alerts` (giữ) | `alert_recipients`, (`privilege_alert_checked_until` của FEAT-005), `credentials` |

Chi tiết 49 trường mới (in đậm ở trên):

| fieldname | Kiểu | Mặc định | Ràng buộc lúc lưu | Ai đọc (đơn vị) | Nguồn |
|---|---|---|---|---|---|
| `agent_enabled_at` | Datetime, read-only | — | tự quản (3.1) | quét 15' (U4a) | AC-16 |
| `record_tools_enabled` | Check | 0 | — | `policy` (U1) | AC-1, AC-3, ADR-030 QĐ 1 |
| `act_now_enabled` | Check | 0 | — | `policy` (U1) | AC-6, AC-22, ADR-030 QĐ 3–4 |
| `one_click_approval_enabled` | Check | 0 | — | `policy` (U3) | AC-11, ADR-032 QĐ 4 |
| `site_environment` | Select `production\ntest` | `production` | Select | `policy` (U3, U7) | AC-12, ADR-031 QĐ 7 |
| `level_cap_a`..`level_cap_f` | Select `L0\nL1\nL2\nL3` | L2, L3, L1, L2, L1, L3 | Select | `policy` (U1) | AC-31, ADR-030 QĐ 2 |
| `confidence_threshold` | Int | 70 | 0..100 | `policy` (U1) | AC-22, ADR-030 QĐ 4 |
| `auto_approve_streak` | Int | 20 | 1..100 | vị từ "Tự làm" (U7) | AC-36, ADR-031 QĐ 4 |
| `catalog_rules` | Table `ERP AI Catalog Rule` | rỗng | 3.1 E-4 | bộ thực thi, `policy` (U7) | AC-29, ADR-031 QĐ 1 |
| `user_templates` | Table `ERP AI User Template` | rỗng | 3.1 E-5 | hành động "tạo tài khoản theo mẫu" (U7) | AC-30 (1) |
| `excluded_title_prefixes` | Small Text (mỗi dòng một tiền tố) | `[HR]\n[Kế toán]` | — | `policy` (U2) | AC-9, ADR-034 QĐ 1 |
| `field_ticket_nature`, `field_erp_module`, `field_origin`, `field_due_date`, `field_project`, `field_item_code`, `field_serial_no` | Data (tên trường HD Ticket) | rỗng | 3.1 E-1, E-2 | U4b (đưa vào lượt), U4a/U5a (`field_due_date`), U6b (`field_origin`) | AC-24, AC-25, AC-42 |
| `origin_board_value` | Data | rỗng | 3.1 E-3 | U6b | AC-24, AC-42 |
| `reply_enabled` | Check | 0 | — | U6b | AC-40 |
| `resolve_on_tasks_done_enabled` | Check | 0 | — | U6b | AC-43 |
| `close_silent_f_enabled` | Check | 0 | — | U6b | AC-44 |
| `close_silent_f_days` | Int | 3 | 1..30 | U6b | AC-44 |
| `kb_draft_enabled` | Check | 0 | — | U6b | AC-45 |
| `knowledge_search_limit` | Int | 5 | 1..20 | U6b (tool CSKT, HDSD, phiếu cũ) | AC-46, AC-47, A-13 |
| `manuals_dir` | Data (đường dẫn tương đối dưới `apps/`) | rỗng | 3.1 E-7 | `source.py`, `knowledge.py` (U6a) | AC-47, ADR-034 QĐ 5 |
| `allowed_reports` | Small Text (mỗi dòng một tên Report) | rỗng | 3.1 E-6 | U6b | AC-49, ADR-034 QĐ 3 |
| `report_row_limit` | Int | 20 | 1..100 | U6b | AC-49, A-13 |
| `coo_report_recipients` | Small Text (mỗi dòng một email) | rỗng | 3.1 E-8 | báo cáo 08:00 (U5a) | AC-51, AC-52 |
| `daily_report_weekends` | Check | 1 | — | báo cáo 08:00 (U5a) | A-13 |
| `monthly_reviewers` | Small Text (mỗi dòng một User) | rỗng | 3.1 E-8 | rà soát tháng (U5a) | AC-59 |
| `review_sample_size` | Int | 10 | 1..50 | rà soát tháng (U5a) | AC-59, NFR-5 |
| `d_ticket_watcher` | Link User | rỗng | 3.1 E-8 | `decide_route` qua runner (U4b) | AC-27 |
| `due_reminder_hours` | Int | 24 | 1..168 | báo cáo 08:00 (U5a), nhắc hạn (U5b) | AC-51, AC-57, A-13 |
| `ba_note_due_hours` | Int | 24 | 1..168 | U5a, U5b | AC-51, AC-58 |
| `task_due_days` | Int | 3 | 1..30 | U5a, U5b | AC-51, AC-58 |
| `max_tasks_per_run` | Int | 10 | 1..20 | U8 | AC-63, A-13 |
| `kpi_targets` | Code (JSON) | mục 2.1.1 | 3.1 E-9 | KPI (U5a) | AC-55, AC-56 |
| `daily_report_sent_on` | Date, read-only | — | tự quản | báo cáo 08:00 (U5a) | AC-52, ADR-033 QĐ 6 |
| `budget_alert_sent_month` | Data (`YYYY-MM`), read-only | — | tự quản | email vượt ngân sách (U5b) | AC-61, ADR-033 QĐ 6, 9 |
| `prompt_override_classify`, `prompt_override_reasoning`, `prompt_override_category_guide` | Long Text | rỗng | 3.1 E-10 | `prompts.py` qua runner (U7) | AC-38 |
| `prompt_revisions` | Table `ERP AI Prompt Revision`, read-only | rỗng | tự quản | người đọc trên form | AC-38 |

Đếm: 49 trường dữ liệu mới, 7 section mới (`section_count` 7 → 14, `field_count` 27 → 76, cộng 1 nếu FEAT-005 T7 đã merge). `read_only_fields` thêm `agent_enabled_at`, `daily_report_sent_on`, `budget_alert_sent_month`, `prompt_revisions`.

**Mô tả trường (≤ 400 ký tự, kiểm bởi `test_doctype_descriptions.py`).** Mô tả là nguồn chữ của thông báo AC-4 (D-7), nên 5 công tắc phải nêu hậu quả. Cụm từ bắt buộc thêm vào `DOCTYPE_CONFIG["phrases"]`:

| fieldname | Mô tả (dev giữ ý, cắt chữ nếu > 400 ký tự) | Cụm bắt buộc |
|---|---|---|
| `unrestricted_enabled` | "Toàn quyền. Bật thì từ L1, khi có người ra lệnh và chưa vượt ngân sách tháng, bot được tạo, sửa, xóa, submit, hủy bản ghi, gán mọi vai trò kể cả System Manager và gọi hàm whitelist, không qua duyệt. Gọi hàm là tự do: bot không tự đổi công tắc và không đọc phiếu nhóm loại trừ qua gọi hàm chỉ là cố gắng. Vẫn đóng: cấu hình, khóa API, Log, đề xuất; mật khẩu. Chỉ bật khi cần gấp." | cũ (L1, người ra lệnh, xóa, System Manager, Vẫn đóng, mật khẩu, Log, cần gấp) + "vượt ngân sách", "gọi hàm", "cố gắng" |
| `record_tools_enabled` | "Công cụ bản ghi chung. Bật thì ở L3 và khi có người ra lệnh, bot liệt kê, đọc, tạo, sửa bản ghi của DocType không bị cấm, ghi thẳng không qua duyệt (không xóa, không submit, không gán 6 vai trò quản trị). Không theo danh mục trắng. Mọi lần ghi có trong Log. Sau cập nhật ô này tắt, kể cả khi ô sửa code đang bật." | "L3", "người ra lệnh", "không qua duyệt", "danh mục trắng", "Log", "Sau cập nhật" |
| `act_now_enabled` | "Làm luôn. Bật thì khi có người ra lệnh và có ít nhất một quyền mở rộng được cấp, bot làm ngay trong lượt, không hỏi lại, không bị ngưỡng độ tin cậy chặn. Không thêm công cụ nào. Tắt thì dưới ngưỡng bot chỉ hỏi." | "người ra lệnh", "không hỏi lại", "ngưỡng độ tin cậy", "Không thêm công cụ" |
| `code_change_enabled` | "Sửa code và lệnh bench. Bật thì ở L3 và khi có người ra lệnh, bot đề xuất sửa file, tạo file, lệnh bench; mọi thay đổi phải được ERP AI Instructor duyệt trên form đề xuất. Mỗi thay đổi đã áp dụng là một commit git local; bot không push. Ô này không còn mở công cụ bản ghi. Tắt thì bot không có ba công cụ đó." | cũ (L3, người ra lệnh, được duyệt, commit git local, không push, Tắt) + "không còn mở công cụ bản ghi" |
| `one_click_approval_enabled` | "Duyệt một lần bấm. Bật thì comment đề xuất có liên kết Duyệt và Từ chối: một lần bấm là chạy, không hộp xác nhận; người có quyền duyệt bấm liên kết được chuyển tiếp cũng duyệt. Tắt thì máy chủ từ chối liên kết, kể cả liên kết cũ; duyệt trên form hoặc ngăn của bot, có bước xác nhận." | "một lần bấm", "không hộp xác nhận", "chuyển tiếp", "liên kết cũ" |
| `site_environment` | "test hoặc production. Ở production bot từ chối Custom Field, Server Script, Client Script, Property Setter, Workflow, Data Import trên đường danh mục trắng và đề nghị làm trên site test. Năm quyền mở rộng không bị chặn theo môi trường; giá trị ghi vào cảnh báo và Log." | "production", "site test", "không bị chặn" |
| `level_cap_<x>` | "Mức cao nhất của bot cho phiếu đầu mục X trên đường danh mục trắng, Task, đề xuất. Mức thực tế là mức nhỏ hơn giữa ô này và Mức quyền. Không áp cho năm quyền mở rộng. Đầu mục chưa biết tính L1." | "Mức quyền", "năm quyền mở rộng", "chưa biết" |
| `confidence_threshold` | "Độ tin cậy tối thiểu, từ 0 đến 100 (phần trăm). Dưới ngưỡng bot không ghi gì, chỉ đăng một comment hỏi; trừ khi có người ra lệnh và ô Làm luôn bật." | "từ 0 đến 100", "chỉ đăng một comment hỏi", "Làm luôn" |
| `auto_approve_streak` | "Số đề xuất liên tiếp được duyệt không sửa của một loại hành động để dòng Tự làm chạy không cần duyệt, từ 1 đến 100. Từ chối, duyệt có sửa, hoàn tác đếm lại từ 0." | "từ 1 đến 100", "Tự làm", "đếm lại từ 0" |
| `catalog_rules` | "Danh mục trắng của đường chính. Không có dòng nào = bot không ghi ERP ngoài phiếu. Mỗi dòng: hành động, DocType, trường, đầu mục, chế độ Cấm / Cần duyệt / Tự làm. Dòng trỏ vào dữ liệu của app, phân quyền, tài khoản hay chứng từ submit bị chặn khi lưu." | "Không có dòng nào", "Cấm", "Cần duyệt", "Tự làm", "bị chặn khi lưu" |
| `user_templates` | "Mẫu cho hành động tạo tài khoản theo mẫu: tên mẫu và vai trò (mỗi dòng một vai trò). Không được chứa System Manager, Administrator, ERP AI Instructor, ERP AI Agent, Guest, All." | "tạo tài khoản theo mẫu", "System Manager", "Guest" |
| `excluded_title_prefixes` | "Mỗi dòng một tiền tố tiêu đề của bộ phận loại trừ, ví dụ [HR]. Phiếu có tiền tố này bị bỏ qua như phiếu nhóm loại trừ, không gửi cho model." | "Mỗi dòng", "[HR]", "không gửi cho model" |
| `field_*` | "Tên trường (fieldname) trên HD Ticket chứa <Tính chất phiếu / ...>. Để trống nếu site chưa có; phần phụ thuộc không chạy và ghi log. Tên không có trên phiếu thì không lưu được." (`field_due_date` thêm "kiểu Date hoặc Datetime") | "fieldname", "Để trống", "không lưu được" |
| `origin_board_value` | "Giá trị của trường Nguồn phát sinh nghĩa là Chỉ đạo BGĐ. Phiếu có giá trị này không bao giờ bị bot đổi trạng thái theo hai đường tự động. Cần đặt trường Nguồn phát sinh trước." | "Chỉ đạo BGĐ", "đổi trạng thái", "Nguồn phát sinh" |
| `reply_enabled`, `resolve_on_tasks_done_enabled`, `close_silent_f_enabled`, `kb_draft_enabled` | mỗi ô nêu việc, "mặc định tắt", và với ba ô đổi trạng thái/soạn bài: "chỉ bật sau khi đã đặt trường Nguồn phát sinh" | "mặc định tắt" |
| `close_silent_f_days`, `knowledge_search_limit`, `report_row_limit`, `review_sample_size`, `due_reminder_hours`, `ba_note_due_hours`, `task_due_days`, `max_tasks_per_run` | nêu đơn vị và khoảng như cột Ràng buộc | khoảng "từ a đến b" |
| `manuals_dir` | "Thư mục chứa file .md của bộ HDSD, tính từ thư mục apps/, ví dụ erpnext/docs. Để trống thì bot trả lời chưa có kho HDSD. File trong thư mục này không đọc được qua công cụ đọc mã nguồn." | "apps/", "Để trống", "chưa có kho HDSD", "mã nguồn" |
| `allowed_reports` | "Mỗi dòng một tên báo cáo bot được chạy (Script Report hoặc Query Report), theo quyền của tài khoản agent, chỉ đọc. Để trống thì bot không chạy báo cáo nào. Báo cáo dựa trên phiếu, comment, email bị chặn khi lưu." | "Mỗi dòng", "Để trống", "bị chặn khi lưu" |
| `coo_report_recipients` | "Mỗi dòng một email nhận báo cáo 08:00 hằng ngày. Để trống thì không gửi." | "08:00", "Để trống" |
| `monthly_reviewers` | "Mỗi dòng một tài khoản (email đăng nhập) nhận thông báo danh sách rà soát tháng. Để trống thì danh sách vẫn được tạo nhưng không thông báo." | "Mỗi dòng", "vẫn được tạo" |
| `d_ticket_watcher` | "Người (thường là IT) được thêm làm người theo dõi phiếu đầu mục D, một lần mỗi phiếu. Để trống thì không thêm." | "đầu mục D", "Để trống" |
| `kpi_targets` | "JSON mục tiêu 6 KPI theo giai đoạn: mỗi KPI có gd2 và gd4 là số không âm. Sai cú pháp hoặc thiếu KPI thì không lưu được." | "JSON", "gd2", "gd4", "không lưu được" |
| `agent_enabled_at`, `daily_report_sent_on`, `budget_alert_sent_month` | "Hệ thống tự ghi: ... không sửa được." | "Hệ thống tự ghi", "không sửa được" |
| `prompt_override_*` | "Để trống = dùng bản dựng sẵn. Nội dung thay <phần>; phải có các mục bắt buộc <liệt kê> và ≤ 20000 ký tự. Các câu cấm và khối năm quyền không bị ghi đè. Mỗi lần sửa được lưu vào Lịch sử ghi đè prompt." | "Để trống", "bắt buộc", "20000", "không bị ghi đè" |
| `prompt_revisions` | "Hệ thống tự ghi mỗi lần sửa ghi đè prompt: phần, người sửa, thời điểm, giá trị cũ. Không sửa được." | "Hệ thống tự ghi", "Không sửa được" |
| `permission_level` (sửa) | thêm câu: "Mức thực tế của từng phiếu trên đường danh mục trắng không vượt Mức tối đa của đầu mục; năm quyền mở rộng tính theo ô này." Bỏ câu "L3 thêm công cụ tạo, sửa bản ghi … khi bật ô Cho phép sửa code". | cũ (L0, L1, L2, L3, ngân sách) |

#### 2.1.1 Mặc định `kpi_targets` (bảng mục 5 của tài liệu chiến lược)

```json
{
  "first_response_minutes": {"gd2": 15, "gd4": 5},
  "complete_fields_pct": {"gd2": 100, "gd4": 100},
  "closed_without_human_pct": {"gd2": 10, "gd4": 30},
  "b_resolution_hours": {"gd2": 4, "gd4": 1},
  "c_task_in_3_days_pct": {"gd2": 80, "gd4": 100},
  "stale_over_5_days": {"gd2": 10, "gd4": 4}
}
```
`stale_over_5_days`: 21 phiếu hiện tại giảm 50% / 80% (làm tròn xuống). Hằng `KPI_IDS` (6 khóa trên, đúng thứ tự) đặt trong `erp_ai_setting.py`; `kpi.py` (U5a) import từ đó.

### 2.2 DocType con mới (U0, `istable: 1`, module "ERP AI agent")

**`ERP AI Catalog Rule`** (bảng `catalog_rules`) — một dòng danh mục (ADR-031 QĐ 1, A-2):

| fieldname | Kiểu | Bắt buộc | Ghi chú |
|---|---|---|---|
| `action` | Select (6 giá trị dưới) | có | hành động có tên hoặc "Đổi trường" |
| `target_doctype` | Link DocType | theo hành động | DocType đích (Đổi trường) hoặc DocType nhận trường mới (Tạo Custom Field) |
| `fields` | Small Text (mỗi dòng một fieldname) | theo hành động | chỉ cho "Đổi trường" |
| `categories` | Data | có | chữ A–F cách bằng dấu phẩy; controller chuẩn hóa về `A,B` (bỏ trùng, sắp xếp) |
| `mode` | Select `Cấm\nCần duyệt\nTự làm` | có | mặc định `Cần duyệt` |

Hằng trong `erp_ai_catalog_rule.py` (U7 import, không chép):

| Hằng | Giá trị Select (lưu nguyên chữ) | DocType đích | `target_doctype` | `fields` |
|---|---|---|---|---|
| `ACTION_CREATE_USER` | `Tạo tài khoản theo mẫu` | User (cố định) | phải trống | phải trống |
| `ACTION_ADD_TEAM_MEMBER` | `Thêm người vào nhóm Helpdesk` | HD Team (cố định) | phải trống | phải trống |
| `ACTION_ADD_HOLIDAY` | `Thêm ngày nghỉ` | Holiday List (cố định) | phải trống | phải trống |
| `ACTION_SET_ITEM_GROUP` | `Đổi nhóm hàng` | Item (cố định, chỉ `item_group`) | phải trống | phải trống |
| `ACTION_CREATE_CUSTOM_FIELD` | `Tạo Custom Field` | Custom Field (cố định) | bắt buộc: DocType nhận trường | phải trống |
| `ACTION_UPDATE_FIELDS` | `Đổi trường` | `target_doctype` | bắt buộc | bắt buộc, ≥ 1 |

`MODE_DENY = "Cấm"`, `MODE_NEEDS_APPROVAL = "Cần duyệt"`, `MODE_AUTO = "Tự làm"`. Hàm công khai `hard_ban_reason(doctype: str) -> str | None` (một nguồn cho lúc lưu và bộ thực thi U7, ADR-031 Ràng buộc): trả lý do khi `doctype` ∈ `read.denied_doctypes()` ∪ `site_api.DENIED_DOCTYPES` (tập cấm của chế độ thường; sau T59 là định nghĩa một-nguồn mà T59 công khai), hoặc `frappe.get_meta(doctype).is_submittable`; ngược lại `None`. Không viết tay tên DocType nào trong module này.

**`ERP AI User Template`** (bảng `user_templates`): `template_name` (Data, bắt buộc, duy nhất trong bảng, không phân biệt hoa thường), `roles` (Small Text, mỗi dòng một Role, ≥ 1), `note` (Small Text).

**`ERP AI Prompt Revision`** (bảng `prompt_revisions`, mọi trường read-only): `part` (Select `classify\nreasoning\ncategory_guide`), `changed_by` (Link User), `changed_at` (Datetime), `old_value` (Long Text), `new_length` (Int).

### 2.3 ERP AI Log — trường mới (U0, D-5; chỉ thêm, hành vi ghi ở đơn vị ghi chú)

| fieldname / thay đổi | Kiểu | Người ghi (đơn vị) | Người đọc | Nguồn |
|---|---|---|---|---|
| `created_labels` | Small Text (JSON `{ticket_type, agent_group, priority}`, chỉ khóa có giá trị) | runner, dòng `classify` (U4b) | ERP AI Accuracy (U4a) | AC-19 |
| `predicted_confidence_pct` | Int | runner (U1/U4b) | báo cáo, U1 | AC-22, D-14 |
| `split_requested` | Check | runner (U4b) | báo cáo (U5a), chống lặp AC-28 | AC-28 |
| `split_requests` | Small Text (JSON list) | runner (U4b) | — | AC-28 |
| `site_environment` | Data | `write_entry` (U3) | — | AC-10(b), ADR-033 QĐ 5 |
| `entry_type` thêm `bot_action` | Select | U3 | U3, U5a | ADR-033 QĐ 5 (dòng không phải lần chạy) |
| `trigger` thêm `requester_reply`, `kb_draft`, `scheduled_job`, `setting_save` | Select | U3, U6b | `runs_today` (U1) | ADR-033 QĐ 2, 4, 5 |
| `actions` Small Text → **Long Text** | Long Text | như cũ | như cũ | D-6 |
| Quyền: thêm `ERP AI Instructor` `read=1, report=1` | DocPerm | — | ba báo cáo trên ERP AI Log | AC-20, ADR-034 QĐ 8; Frappe đòi `report` trên `ref_doctype` |

`DOCTYPE_CONFIG["ERP AI Log"]`: `field_count` 38 → 43, cụm từ mới cho 5 trường và cho `entry_type`/`trigger`. `run_log.ENTRY_TYPES` và tập trigger hợp lệ **không** đổi ở đợt 0 (U3 đổi), nên chưa có dòng nào mang giá trị mới.

### 2.4 Trường tùy biến (install.py, U0)

| DocType | fieldname | Kiểu | Thuộc tính | Nguồn |
|---|---|---|---|---|
| HD Ticket | `ai_confidence_pct` | Int | read-only, permlevel 8, `module` app, đứng sau `ai_confidence` trong `_ai_field_specs` (dòng mẫu phiếu tự thêm như các trường AI khác) | AC-22, D-14 |
| HD Article | `ai_source_ticket` | Link HD Ticket | read-only, `search_index` 1, `module` app, sau `category`; `create_custom_fields(update=False)`; bỏ qua có cảnh báo logger nếu DocType HD Article chưa có | AC-45, D-15 |

### 2.5 DocType mới của U5a (module "ERP AI agent", không `istable`, không submit)

**`ERP AI KPI Week`** — một dòng mỗi tuần ISO; tên `KPI-<week_start ISO>` đặt trong `autoname` của controller; `week_start` `unique` (khóa chu kỳ của ADR-033 QĐ 6).

| fieldname | Kiểu | Ghi chú |
|---|---|---|
| `week_start` | Date, bắt buộc, unique | thứ Hai 00:00 |
| `week_end` | Date | Chủ nhật |
| `computed_at` | Datetime | |
| `first_response_median_min` | Float | rỗng khi mẫu 0 |
| `first_response_within_15_pct`, `first_response_within_5_pct` | Percent | |
| `first_response_sample` | Int | |
| `complete_fields_pct` / `complete_fields_sample` | Percent / Int | |
| `closed_without_human_pct` / `closed_sample` | Percent / Int | |
| `b_resolution_avg_hours` / `b_resolution_sample` | Float / Int | |
| `c_task_in_3_days_pct` / `c_task_sample` | Percent / Int | |
| `stale_over_5_days`, `stale_over_7_days` | Int | |

Quyền: System Manager và ERP AI Instructor `read`, `report`; không ai `create/write/delete` (job chạy phiên scheduler = Administrator).

**`ERP AI Review Month`** — tên `REV-<YYYY-MM>`; `month` (Data `YYYY-MM`, bắt buộc, unique), `period_start`, `period_end` (Date), `candidate_count` (Int), `items` (Table `ERP AI Review Item`). Quyền: System Manager và ERP AI Instructor `read`, `write`; không `create`, `delete`.

**`ERP AI Review Item`** (`istable`): `ticket` (Link HD Ticket, read-only), `verdict` (Select `\nĐúng\nSai`), `note` (Small Text), `reviewed_by` (Link User, read-only), `reviewed_at` (Datetime, read-only).

### 2.6 Báo cáo

| Báo cáo | Đơn vị | `ref_doctype` | `roles` |
|---|---|---|---|
| ERP AI Accuracy (sửa) | U4a | ERP AI Log | System Manager, ERP AI Instructor |
| ERP AI KPI Weekly (mới, Script Report) | U5a | ERP AI KPI Week | System Manager, ERP AI Instructor |
| ERP AI Cost (mới, Script Report) | U5a | ERP AI Log | System Manager, ERP AI Instructor |

Khối lượng (spec "Dữ liệu"): ≤ vài trăm phiếu và vài nghìn dòng nhật ký mỗi tháng; không thêm chỉ mục ngoài `unique` và `search_index` ở trên.

## 3. API / hợp đồng

### 3.1 Controller ERP AI Setting (U0) — `erp_ai_setting.py`

Thứ tự `validate` (sau `refuse_agent_write` của T65 khi đã merge):
1. `restore_self_managed_fields()` — mở rộng: `agent_enabled_at`, `daily_report_sent_on`, `budget_alert_sent_month` lấy lại từ `frappe.db.get_single_value(..., cache=False)`; `prompt_revisions` thay bằng các dòng đang có trong DB (người không thêm/sửa/xóa được).
2. Các kiểm cũ (nhãn khóa, `validate_mapping`, `routing_rules`, `code_change_apps`, `INT_LIMITS`, chỉ báo, điều kiện bật).
3. `INT_LIMITS` thêm: `confidence_threshold` (0..100), `auto_approve_streak` (1..100), `close_silent_f_days` (1..30), `knowledge_search_limit` (1..20), `report_row_limit` (1..100), `review_sample_size` (1..50), `due_reminder_hours` (1..168), `ba_note_due_hours` (1..168), `task_due_days` (1..30), `max_tasks_per_run` (1..20). Chữ lỗi như cũ: "<nhãn> phải từ a đến b".
4. `check_ticket_field_names()` (AC-24): mỗi `field_*` khác rỗng phải có trên `frappe.get_meta("HD Ticket")`.
   - E-1 `"Trường '{fieldname}' không có trên HD Ticket ({nhãn ô})"`
   - E-2 `field_due_date` phải là `Date`/`Datetime`: `"Trường Hạn hoàn thành phải có kiểu Date hoặc Datetime"`
   - E-3 `origin_board_value` có mà `field_origin` rỗng: `"Đặt giá trị Chỉ đạo BGĐ thì phải đặt tên trường Nguồn phát sinh"`
5. `check_catalog_rules()` (AC-29, ADR-031 QĐ 1), lỗi `"Danh mục dòng {idx}: {lý do}"`; lý do (E-4):
   - `"hành động không hợp lệ"` (Select ngoài 6 giá trị — Frappe chặn trước, giữ để thông điệp rõ khi dữ liệu nhập qua API);
   - `"hành động này không nhận DocType"` / `"hành động này cần DocType"`;
   - `"không có DocType {dt}"`;
   - `"DocType {dt} bị cấm cứng: {lý do của hard_ban_reason}"`;
   - `"hành động này không nhận danh sách trường"` / `"cần ít nhất một trường"` / `"trường {f} không có trên {dt}"`;
   - `"đầu mục phải là các chữ A–F cách nhau bằng dấu phẩy"`;
   - `"trùng với dòng {j}"` (cùng `action` + `target_doctype`).
6. `check_user_templates()` (AC-30 (1)), lỗi `"Mẫu tài khoản dòng {idx}: {lý do}"` (E-5): tên trống, tên trùng, không có vai trò nào, `"không có vai trò {r}"`, `"vai trò {r} bị cấm cho bot"` (∈ `site_api.FORBIDDEN_ROLES`).
7. `check_allowed_reports()` (AC-49, ADR-034 QĐ 3), mỗi dòng (E-6): `"Báo cáo '{r}' không có"`; `"Báo cáo '{r}' phải là Script Report hoặc Query Report"`; `"Báo cáo '{r}' đang tắt"`; `"Báo cáo '{r}' dựa trên {dt}, mang nội dung phiếu hoặc dữ liệu của app: bot không được chạy"` khi `ref_doctype` ∈ `TICKET_CONTENT_DOCTYPES` ∪ `read.denied_doctypes()`. Hằng `TICKET_CONTENT_DOCTYPES` (D-13) đặt trong file này; U6b import.
8. `check_manuals_dir()` (AC-47) E-7: rỗng → bỏ qua; ngược lại `source.resolve_safe_path(value)` phải trả đường dẫn và `os.path.isdir` đúng, khác chính `apps/`: `"Kho HDSD '{value}' phải là thư mục có sẵn dưới apps/"`. (U6a chỉ chặn **file** trong kho ở `resolve_safe_path`, nên kiểm thư mục này không bị chặn bởi chính giá trị đã lưu.)
9. `check_operation_people()` (E-8): mỗi dòng `coo_report_recipients` qua `frappe.utils.validate_email_address(line, throw=False)` → `"Người nhận báo cáo COO: '{x}' không phải email hợp lệ"`; mỗi dòng `monthly_reviewers` là User đang bật → `"Người rà soát: không có tài khoản '{x}' đang bật"`; `d_ticket_watcher` (nếu có) đang bật và khác `AGENT_USER` → `"Người theo dõi phiếu D phải là tài khoản người đang bật"`.
10. `check_kpi_targets()` (E-9): JSON object có đúng 6 khóa `KPI_IDS`, mỗi giá trị object có đúng `gd2`, `gd4` là số ≥ 0: `"Mục tiêu KPI: {đường dẫn khóa} {lỗi}"`; rỗng → lỗi kèm JSON mặc định (như `routing_rules`).
11. `check_prompt_overrides()` (AC-38) E-10, mỗi phần khác rỗng (sau `strip`):
    - dài > `PROMPT_OVERRIDE_MAX_CHARS = 20000` → `"Ghi đè prompt {nhãn phần} dài quá 20000 ký tự"`;
    - thiếu mục bắt buộc → `"Ghi đè prompt {nhãn phần} thiếu mục bắt buộc: {danh sách}"`. Hằng `PROMPT_REQUIRED_MARKERS`:
      - `classify`: 11 khóa JSON mà `parse_classification` đọc: `"dau_muc"`, `"do_tin_cay"`, `"ly_do"`, `"nhom"`, `"uu_tien"`, `"can_tach"`, `"cac_yeu_cau"`, `"do_phuc_tap"`, `"do_quan_trong"`, `"ly_do_diem"`, `"bo_phan"`;
      - `reasoning`: `**Nhận định:**`, `**Căn cứ:**`, `**Hướng xử lý:**`, `**Cần ai quyết:**`;
      - `category_guide`: một dòng bảng cho mỗi đầu mục, khớp `^\|\s*{X}\s*\|` (đa dòng) với X ∈ A..F.
    - Test buộc bản dựng sẵn (`CLASSIFY_PROMPT`, `CORE_PROMPT`, `CATEGORY_TABLE`) tự qua được kiểm của chính nó, nên danh sách không trôi khỏi mã.
12. `record_prompt_revisions()`: với mỗi phần mà giá trị khác giá trị trong DB, thêm một dòng `prompt_revisions` (`part`, `changed_by = frappe.session.user`, `changed_at = now_datetime()`, `old_value` = giá trị DB, `new_length`). Không có thay đổi → không thêm dòng.
13. `stamp_agent_enabled_at()`: `enabled` đổi 0 → 1 (so với DB) → `now_datetime()`; ngược lại giữ giá trị khôi phục ở bước 1.

`on_update` (chỉ chạy khi lưu thành công):
- `notify_permission_switches()` (AC-4, phần form; ADR-030 QĐ 7): so `get_doc_before_save()` với hiện tại cho mọi trường `Check` thuộc `section_permissions` (đọc từ meta, D-7). Có ít nhất một ô 0 → 1 → **một** `frappe.msgprint(message, title="Đã bật quyền mở rộng", indicator="orange")`, `message` gồm mỗi ô vừa bật một dòng `"<b>{label}</b>: {description}"` (escape HTML) và dòng cuối `"Môi trường site: {site_environment}"`. Không ô nào 0 → 1 → không gọi `msgprint`. Dòng nhật ký người bật: U3 thêm vào cùng hàm này.
- `warn_level_raise_without_gate()` (AC-18; A-8 không chặn): mức trước là `L0`, mức mới ≥ `L1`, và `l0_l1_gate().verdict != "Đạt"` → `frappe.msgprint("Kết luận cửa L0 → L1 của báo cáo ERP AI Accuracy (14 ngày gần nhất): {verdict}, {correct}/{labeled} phiếu có nhãn đúng. Mức vẫn được lưu.", title="Chưa đạt cửa L0 → L1", indicator="orange")`.

`erp_ai_setting.js` (U0): không thêm nút; chỉ `frm.set_df_property("prompt_revisions", "cannot_add_rows", 1)` và `cannot_delete_rows` để form không gợi ý sửa bảng tự quản (ranh giới thật ở server, bước 1).

### 3.2 `install.py` (U0)

- `_ensure_default_settings`: giữ nguyên cơ chế (điền khi dòng thiếu hoặc NULL); trường mới có `default` trong JSON nên tự được điền: 3 công tắc = 0, `site_environment` = `production`, 6 cap, số kỹ thuật, `kpi_targets`, `excluded_title_prefixes`, `daily_report_weekends` = 1. Thêm một dòng: `enabled` = 1 ∧ `agent_enabled_at` thiếu → `now_datetime()` (điền trường thiếu, ADR-006).
- `_ai_field_specs` thêm `ai_confidence_pct` (2.4).
- Hàm mới `_ensure_article_source_field()` gọi trong `ensure_setup` sau `_ensure_task_ticket_field`.

### 3.3 Hợp đồng cho đơn vị đợt sau (chỉ chốt tên, không thiết kế hành vi)

- `policy.py` (U1) là nơi đọc duy nhất của 3 công tắc mới, `site_environment`, `level_cap_*`, `confidence_threshold`; luật `POLICY_FIELDS` mở rộng ở U1 thêm các tên này và cho phép `erp_ai_setting.py` đúng như chữ ADR-030 Ràng buộc. Controller U0 không viết tên công tắc nào (D-7).
- Ghi đè prompt (U7): `classify` thay toàn bộ `CLASSIFY_PROMPT`; `reasoning` thay phần "CÁCH LÀM VIỆC" và "VIẾT COMMENT" của `CORE_PROMPT`, phần "GIỚI HẠN" và mọi khối quyền luôn là bản dựng sẵn và luôn được ghép sau; `category_guide` thay `CATEGORY_TABLE`. `prompts.py` nhận chuỗi qua tham số (ADR-011 QĐ 3).
- `BA_NOTE_MARKER = "**BA note**"` (U5a, `erp_ai/agent/ops_data.py`): comment BA note của U8 phải bắt đầu bằng chuỗi này; báo cáo 08:00 và nhắc mốc (U5b) nhận BA note bằng nó.
- `hard_ban_reason`, `TICKET_CONTENT_DOCTYPES`, `KPI_IDS`, hằng hành động và chế độ danh mục: import, không chép.

### 3.4 `hooks.py` sau đợt 0 (mỗi đơn vị thêm đúng dòng của mình)

```python
doc_events = {
	"HD Ticket": {...},  # giữ
	"Comment": {...},  # giữ
	"HD Article": {  # U6a
		"validate": "erp_ai.agent.article_guard.check_article_write",
		"on_trash": "erp_ai.agent.article_guard.check_article_delete",
	},
}
scheduler_events = {
	"hourly": ["erp_ai.tasks.reprobe_exhausted_keys"],
	"daily": ["erp_ai.tasks.recompute_monthly_spend", "erp_ai.tasks.check_privilege_escalation"],
	"cron": {
		"*/15 * * * *": ["erp_ai.agent.missed_scan.scan_missed_tickets"],  # U4a
		"0 8 * * *": ["erp_ai.schedules.enqueue_daily_report"],  # U5a
		"0 8 * * 1": ["erp_ai.schedules.enqueue_weekly_kpi"],  # U5a
		"0 8 1 * *": ["erp_ai.schedules.enqueue_monthly_review"],  # U5a
	},
}
```
Tên 2 đoạn cuối của mỗi hàm lịch là duy nhất (R-5: tên Scheduled Job Type). Sửa lịch cần `cmd.migrate`.

### 3.5 U4a — Phân loại, phần ngoài lõi

#### 3.5.1 `erp_ai/agent/missed_scan.py` (mới; không import gateway, runner)

- `find_missed_tickets(now: datetime) -> list[str]`: tên phiếu, theo `creation` tăng, tối đa `SCAN_BATCH = 50`. Điều kiện (AC-16, D-16):
  - `creation > agent_enabled_at` (rỗng → trả `[]`);
  - `creation ≤ now − SCAN_GRACE_MIN (5) phút`;
  - `status_category != "Resolved"` (A-D3);
  - `owner != AGENT_USER`;
  - không có dòng ERP AI Log `entry_type = "classify"` với `predicted_category` khác rỗng cho phiếu đó (lần chạy lỗi không có `predicted_category` nên phiếu được xếp lại);
  - không đủ cả 3 `CLASSIFICATION_FIELDS`;
  - `policy.can_send_ticket(name)` đúng (U2 mở rộng vị từ này, không sửa file này);
  - `policy.runs_today(name, now) < max_runs_per_ticket_per_day`.
- `scan_missed_tickets(now: datetime | None = None) -> None` (hàm `cron`): `policy.is_enabled()` sai → 1 dòng logger `"missed_scan: agent tắt, bỏ qua"`, return. Ngược lại với mỗi tên: `queue.enqueue_agent_run(name, TRIGGER_TICKET_INSERT)` (ADR-033 QĐ 2: xếp lại như trigger tạo phiếu; chống trùng bằng `job_id` + `deduplicate` của `queue`). Cuối: 1 dòng logger `"missed_scan: xếp {n} phiếu"`. Chạy ở hàng `default` (job ngắn, R-5 phương án A).

#### 3.5.2 `erp_ai/agent/routing.py` (sửa, thuần)

- `RouteDecision` thêm trường `watcher: str | None = None`.
- `decide_route(..., *, team_exists, is_excluded_team, is_active_agent, due_at: datetime | None = None, due_field_configured: bool = False, d_watcher: str | None = None, now: datetime | None = None)` — tham số mới đều có mặc định nên hai nơi gọi cũ không đổi hành vi (hợp đồng thêm, không sửa).
- `_priority` thêm, sau luật E và trước `max()` (AC-25):
  - A ∧ `importance == 3` → Urgent (đã có; độ quan trọng 3 = "chặn nghiệp vụ kế toán, kho" theo `CLASSIFY_PROMPT`);
  - B ∧ `due_at` ∧ `due_at − now ≤ 24 h` → ít nhất High;
  - D ∧ `due_at` → ít nhất High;
  - B hoặc D ∧ `not due_field_configured` → thêm `notes` `"chưa cấu hình trường Hạn hoàn thành, bỏ qua ngoại lệ theo hạn"` (runner ghi notes vào log như hiện nay).
  - "Ít nhất" = `max` theo `_rank`; không hạ mức đã cao hơn; [GẤP], F → Low, E không ghi giữ nguyên thứ tự ưu tiên hiện có (A-10).
- `watcher` (AC-27): category D ∧ `d_watcher` ∧ `is_active_agent(d_watcher)` → `d_watcher`; D ∧ không có `d_watcher` → `notes` `"chưa cấu hình người theo dõi phiếu D"`; khác D → `None`. "Đúng một lần" là việc của bên ghi (U4b: `follow_document` chỉ khi chưa có Document Follow).
- `response_overdue(created: datetime, first_responded_on: datetime | None, category: str | None, config: dict, now: datetime) -> bool` (AC-26): `first_responded_on` rỗng ∧ `config["expected_sla"][category]["response_min"]` có ∧ `now > created + response_min`. Đúng bằng mốc → chưa quá. Không biết đầu mục → `False`.
- `processing_deadline(category: str | None, resolution_by: datetime | None, due_at: datetime | None) -> datetime | None` (D-18): D, E có `due_at` → `due_at`; ngược lại `resolution_by`.

#### 3.5.3 ERP AI Accuracy (`erp_ai_accuracy.py`, `.json`)

- JSON: `roles` thêm `ERP AI Instructor` (AC-20).
- `execute(filters)` trả `columns, data, None, None, report_summary`.
- Cột (thay cột cũ, NFR-8): `category`, `predictions` (Int), `labeled` (Int), `correct` (Int), `accuracy_pct` (Percent = `correct/labeled`, rỗng khi `labeled = 0`), `failed_runs` (Int, chỉ có giá trị ở dòng "Tổng").
- Mẫu: mỗi phiếu lấy dòng `classify` thành công **đầu tiên** (`predicted_category` khác rỗng), `creation` trong khoảng lọc.
- Nhãn từng trường f ∈ {ticket_type, agent_group, priority} (AC-19, D-9): `created_labels[f]` nếu có; không thì `human_corrected_to[f]` nếu có; không thì không có nhãn. Chỉ so trường mà `predicted_<f>` khác rỗng (D/E để trống nhóm không bị tính là sai). Phiếu không còn trường nào để so → "chưa có nhãn" (không vào `labeled`, không vào mẫu 30). Phiếu có nhãn → đúng khi mọi trường so được đều bằng nhau.
- `failed_runs`: phiếu có dòng `classify` không có `predicted_category` trong khoảng lọc và không có dòng thành công.
- `report_summary` (AC-17, AC-18):
  - `Phân loại ≤ 5 phút`, `Phân loại > 5 phút`, `Chưa phân loại` trên phiếu tạo trong khoảng lọc (D-8): độ trễ = `creation` dòng thành công đầu tiên − `creation` phiếu; đúng 5:00 → "≤ 5"; phiếu `owner = AGENT_USER`, phiếu không gửi được (`can_send_ticket` sai), phiếu đủ 3 trường lúc tạo → không đếm; còn lại không có dòng thành công → "Chưa phân loại".
  - `Cửa L0 → L1` = `l0_l1_gate().verdict` kèm `correct/labeled`.
- `l0_l1_gate(now: datetime | None = None) -> GateResult` (dataclass `verdict, labeled, correct`), cửa sổ `(now − 14 ngày, now]` theo `creation` dòng `classify` thành công đầu tiên, không phụ thuộc bộ lọc: `labeled < 30` → `"Chưa đủ mẫu"`; `correct/labeled ≥ 0.85` → `"Đạt"`; còn lại `"Chưa đạt"`. Hằng `GATE_WINDOW_DAYS = 14`, `GATE_MIN_SAMPLE = 30`, `GATE_MIN_ACCURACY = 0.85` (số của tài liệu, NFR-5; không đưa vào cấu hình vì đổi là đổi nghĩa cửa).
- Đọc bằng `frappe.get_all` sau `has_permission(LOG_DOCTYPE, "report", throw=True)` như hiện có; chỉ trả số đếm, không nội dung phiếu.

#### 3.5.4 `classification.py` (AC-28, phần thuần)

`split_request_comment(classification) -> str | None`: `needs_split` ∧ `len(requests) ≥ 2` → chuỗi `"Phiếu này có vẻ gồm {n} yêu cầu:\n1. …\nn. …\nAnh/chị xác nhận có muốn tách thành các phiếu riêng không? Bot không tự tách phiếu."` (mỗi yêu cầu cắt 200 ký tự, tối đa 10 yêu cầu); ngược lại `None`.

### 3.6 U5a — Vận hành, phần ngoài lõi

#### 3.6.1 Cửa vào lịch `erp_ai/schedules.py` (mới)

`enqueue_daily_report()`, `enqueue_weekly_kpi()`, `enqueue_monthly_review()`: mỗi hàm một lời `frappe.enqueue("erp_ai.agent.<module>.<run_fn>", queue="long", timeout=LONG_JOB_TIMEOUT_S (1200), job_id="erp_ai::<việc>", deduplicate=True)` (R-5 phương án B, ADR-033 QĐ 6). Không truyền thời điểm: job tự tính khóa chu kỳ từ lịch.

#### 3.6.2 Khóa chu kỳ (tính từ lịch, không từ giờ chạy)

`ops_data.py`:
- `daily_cycle(now) -> date`: ngày của mốc 08:00 gần nhất ≤ `now` (chạy 02:00 → hôm qua).
- `weekly_cycle(now) -> date`: thứ Hai của mốc "thứ Hai 08:00" gần nhất ≤ `now`; tuần cần tính = tuần **trước** thứ Hai đó.
- `monthly_cycle(now) -> str`: `YYYY-MM` của mốc "ngày 1 08:00" gần nhất ≤ `now`; tháng cần rà = tháng trước đó.
- `category_by_ticket_type(mapping) -> dict[str, str]` (đảo `category_mapping`), `ticket_category(ticket_row, reverse_map) -> str | None`.
- `BA_NOTE_MARKER`.
- Mọi job nhận `now: datetime | None = None` (test truyền), mặc định `now_datetime()` (giờ `System Settings.time_zone`, R-5).

#### 3.6.3 Báo cáo 08:00 — `erp_ai/agent/daily_report.py`

`run_daily_report(now=None) -> None`:
1. Trong `filelock("erp_ai_daily_report", timeout=5)`; khóa bận → logger, return.
2. `cycle = daily_cycle(now)`. `daily_report_sent_on == cycle` → logger "đã gửi", return (NFR-3).
3. Không gửi cuối tuần khi `daily_report_weekends = 0` và `cycle` là thứ Bảy/Chủ nhật → logger, return.
4. Người nhận rỗng → logger `"daily_report: chưa có người nhận"`, return (AC-52; một lần mỗi ngày vì lịch một lần mỗi ngày).
5. `data = build_daily_report(anchor)` với `anchor = cycle 08:00`; `html = render_daily_report(data)`.
6. `frappe.sendmail(recipients, subject=f"[erp_ai] Báo cáo hằng ngày {cycle:%d/%m/%Y}", message=html, delayed=True)` rồi `frappe.db.set_single_value(SETTING_DOCTYPE, "daily_report_sent_on", cycle)` — cùng giao dịch; scheduler commit khi job trả về. Hàm này là chỗ ghi duy nhất của trường mốc (ADR-024 QĐ 3 mẫu, ADR-033 QĐ 6).
7. `frappe.ValidationError`/`frappe.OutgoingEmailError` ở bước 6 → `frappe.db.rollback()`, `frappe.log_error(TITLE_DAILY_REPORT_FAILED, <lý do không chứa nội dung phiếu>)`, return; không ném ra khỏi job (AC-52).
8. Logger 1 dòng: số phiếu mới, số quá mốc phản hồi (đây là "đánh dấu trong log" của AC-26, D-17).

`build_daily_report(anchor) -> dict` (thuần trên dữ liệu đọc; cửa sổ `[anchor − 24 h, anchor)`):

| Khóa | Nội dung | Nguồn |
|---|---|---|
| `new_by_category_priority` | đếm phiếu tạo trong cửa sổ theo (đầu mục, ưu tiên) | HD Ticket |
| `new_list` | `{name, subject?, category, priority}`; phiếu loại trừ: không có `subject`, có cờ `excluded` | `policy.can_send_ticket` (A-D5) |
| `due_soon`, `overdue` | phiếu đang mở có `processing_deadline` trong `(anchor, anchor + due_reminder_hours]` / `≤ anchor` | `routing.processing_deadline`, `field_due_date` |
| `response_overdue` | phiếu đang mở có `routing.response_overdue(..., anchor)` | `routing_rules` |
| `c_missing_ba_note` | phiếu C mở, tạo ≤ `anchor − ba_note_due_hours`, không có Comment của `AGENT_USER` bắt đầu bằng `BA_NOTE_MARKER` | Comment |
| `cd_missing_task` | phiếu C/D mở, tạo ≤ `anchor − task_due_days`, không Task nào có `ai_ticket` = phiếu | Task |
| `de_progress` | với D, E: `done` (Resolved trong cửa sổ), `in_progress` (đang mở), `overdue` | HD Ticket |
| `bot_actions` | đếm theo loại trên ERP AI Log ngày `anchor.date() − 1`: phân loại (`classify` có `applied`), gán (`classify` có `predicted_assignee` và `applied`), Task, comment, trả lời, đóng (mục hành động `ok` theo `ACTION_KIND_BY_TOOL`), đề xuất chờ duyệt/đã duyệt/bị từ chối (`change_step` propose/approve/reject), lỗi (`error` khác rỗng) | ERP AI Log |
| `cost_yesterday` | tổng `cost_usd` ngày hôm qua (6 chữ số) | ERP AI Log |

`ACTION_KIND_BY_TOOL` (hằng trong `daily_report.py`): `create_task` → Task; `post_comment` → comment; tool khác → "khác". U6b thêm tên tool trả lời và đóng khi có. Phiếu không còn đầu mục biết được → nhóm `"?"`.

`render_daily_report(data) -> str`: HTML bảng; mọi chuỗi từ dữ liệu qua `redact.redact_secrets` rồi `frappe.utils.escape_html`; phiếu loại trừ hiện `"#<name> (nhóm loại trừ)"`. Ngày không có phiếu vẫn gửi, mọi số = 0 (AC-52).

#### 3.6.4 KPI tuần — `erp_ai/agent/kpi.py`

- `compute_week(week_start: date, settings) -> dict` (thuần, D-11; `ws` = thứ Hai 00:00, `we` = `ws + 7 ngày`):

  | KPI | Tập phiếu | Giá trị | Mẫu 0 |
  |---|---|---|---|
  | 1 phản hồi đầu tiên | tạo trong `[ws, we)` | trung vị phút (`first_responded_on − creation`) trên phiếu có phản hồi; `% ≤ 15`, `% ≤ 5` trên **mọi** phiếu tạo trong tuần (chưa phản hồi = không đạt) | rỗng |
  | 2 đủ đầu mục, nhóm, ưu tiên | đang mở tại `we` (A-D2) | % có đủ `ticket_type`, `agent_group`, `priority` | rỗng |
  | 3 đóng không cần người | `resolution_date` trong `[ws, we)` | % phiếu mà (a) mọi Comment loại "Comment" do người khác `raised_by`, mọi Communication `Sent`, mọi ToDo gán phiếu (`assigned_by`) đều của `AGENT_USER`, và (b) ERP AI Log có mục hành động `ok` trên HD Ticket đó đặt `status` sang Resolved/Closed (A-14; app không đọc Version, ADR-024) | rỗng |
  | 4 xử lý B | đầu mục B, `resolution_date` trong `[ws, we)` | trung bình giờ (`resolution_date − creation`, giờ lịch) | rỗng |
  | 5 C có Task trong 3 ngày | đầu mục C, tạo trong `[ws − 3 ngày, we − 3 ngày)` (A-D4) | % có ≥ 1 Task `ai_ticket` = phiếu, Task `creation ≤ phiếu.creation + 72 h` (đúng 72 h tính đạt) | rỗng |
  | 6 tồn | đang mở tại `we` | số phiếu tuổi > 5 ngày; số > 7 ngày (đúng 5 ngày không tính) | 0 |

- `run_weekly_kpi(now=None) -> None`: `filelock("erp_ai_weekly_kpi")`; tuần đích `W = weekly_cycle(now) − 7 ngày`; tuần cần tính = các tuần từ `max(tuần sau dòng mới nhất, W − 7 tuần)` tới `W` chưa có dòng (D-10, tối đa 8); mỗi tuần `insert` một `ERP AI KPI Week`; `frappe.DuplicateEntryError` → bỏ qua tuần đó (đã có, NFR-3); logger 1 dòng.

#### 3.6.5 Rà soát tháng — `erp_ai/agent/monthly_review.py`

- `review_candidates(month: str) -> list[str]`: phiếu có ≥ 1 lần ghi của bot trong tháng: dòng `classify` có `applied = 1`, hoặc dòng có `actions` chứa ít nhất một mục `ok` đúng; bỏ phiếu `policy.can_send_ticket` sai; sắp theo tên.
- `pick_sample(candidates, month, size) -> list[str]`: `random.Random(month).sample(candidates, min(size, len))` (cùng tháng → cùng bộ, không phụ thuộc giờ chạy).
- `run_monthly_review(now=None) -> None`: `filelock`; `P` = tháng trước `monthly_cycle(now)`; `REV-P` đã có → logger, return (D-10: không bù tháng cũ hơn); `insert` `ERP AI Review Month` với `items`; người rà khác rỗng → `frappe.sendmail(..., subject=f"[erp_ai] Danh sách rà soát {P}", message=<số phiếu + liên kết /app/erp-ai-review-month/REV-P, không tiêu đề phiếu>, delayed=True)` cùng giao dịch; rỗng → logger.
- Controller `ERP AI Review Month.validate`: khi không phải bản mới, tập và thứ tự `ticket` của `items` phải trùng DB → `"Không được đổi danh sách phiếu của kỳ rà soát"`; dòng có `verdict` hoặc `note` đổi → `reviewed_by = frappe.session.user`, `reviewed_at = now_datetime()`.

#### 3.6.6 Báo cáo U5a

- ERP AI KPI Weekly: lọc `week_start` (tùy chọn; mặc định tuần mới nhất có dòng); 6 dòng theo `KPI_IDS`; cột `kpi` (Data), `this_week`, `last_week` (Data: số đã định dạng hoặc `"chưa có dữ liệu"`), `target_gd2`, `target_gd4` (từ `kpi_targets`), `unit`. Kiểm `has_permission("ERP AI KPI Week", "report", throw=True)`.
- ERP AI Cost: lọc `from_date`, `to_date` (bắt buộc), `group_by` ∈ {`Phiếu`, `Lần chạy`}; dòng phiếu: `ticket` (rỗng → `"(không gắn phiếu)"`), `runs` (số `run_id` khác nhau), `cost_usd` (Float, precision 6); dòng lần chạy: `run_id`, `ticket`, `started_at` (min `creation`), `cost_usd`. `report_summary`: tổng trong khoảng, tổng tháng hiện tại từ ERP AI Log, và `spent_this_month_usd` đang hiển thị. Chỉ mã phiếu, không tiêu đề.

### 3.7 U6a — Tri thức, hàm đọc

- `erp_ai/agent/redact.py` (mới): `redact_secrets(text: str | None) -> str` — thay giá trị khớp `SECRET_PATTERNS` bằng `"[đã che]"`: khóa `sk-ant-…`, `sk-…` (≥ 16 ký tự), `Bearer <token>`, `token <key>:<secret>` (khóa API Frappe), JWT `eyJ….….…`, và giá trị sau `api_key|api_secret|token|secret|password|passwd|pwd|mật khẩu` + `:`/`=` (giữ tên khóa). Một hàm dùng chung cho nhật ký, kết quả tool, Error Log, email (ADR-034 QĐ 2); đơn vị sau dùng lại.
- `erp_ai/agent/system_read.py` (mới, ngoài `tools/`, ADR-021 QĐ 4): `read_error_logs(since=None, until=None, keyword=None, limit=20) -> list[dict]` — mặc định `until = now`, `since = until − 24 h`; `until − since > 7 ngày` → `frappe.throw("Khoảng thời gian tối đa 7 ngày")`; `limit` 1..50; `keyword` 2..100 ký tự, LIKE có escape trên `method` hoặc `error`; `frappe.get_all("Error Log", ...)` sắp `creation` giảm dần; trả `{name, creation, method, error}` với `method`, `error` qua `redact_secrets`, `error` giữ 2000 ký tự **cuối**. Đây là đường bỏ quyền duy nhất của nhóm đọc mới (ADR-034 Ràng buộc).
- `erp_ai/agent/knowledge.py` (mới):
  - `tokenize(text) -> list[str]` (D-12).
  - `search_kb_articles(query: str, limit: int) -> list[dict]`: không có từ nào → `frappe.throw("Câu tìm cần ít nhất một từ dài 2 ký tự")`; lọc trước bằng `frappe.get_list("HD Article", filters={"status": "Published"}, or_filters=<LIKE từng từ trên title, content>, fields=[name, title, content, modified], limit_page_length=KB_SCAN_MAX (200))` **dưới phiên đang chạy** (không bỏ quyền); điểm = số từ của câu tìm có mặt nguyên từ trong `title + strip_html(content)` (giữ dấu; LIKE của MariaDB không phân biệt dấu nên chỉ là lọc thô); bỏ điểm 0; sắp điểm giảm, số từ khớp ở tiêu đề giảm, `modified` giảm; trả `limit` bài `{name, title, excerpt}`, `excerpt` 300 ký tự quanh từ khớp đầu, qua `redact_secrets`.
  - `search_manuals(query: str, limit: int, manuals_dir: str | None) -> list[dict] | None`: `manuals_dir` rỗng → `None` (tool U6b trả "chưa có kho HDSD"); duyệt `.md` trong kho qua `source.resolve_manual_path`, tối đa `MANUALS_MAX_FILES = 500`, mỗi file ≤ 1 MiB, ngân sách 10 s; cắt mục theo dòng bắt đầu bằng `#`; điểm như trên; trả `{document (đường dẫn tương đối trong kho), heading, line (1-based), excerpt}`.
- `erp_ai/agent/tools/source.py` (sửa): tách `_base_resolve(rel)` (các chốt hiện có); `resolve_safe_path(rel)` = `_base_resolve` và trả `None` khi đích là **file** nằm trong `manuals_root()`; hàm mới `resolve_manual_path(rel)` = `_base_resolve` ∧ nằm trong `manuals_root()`; `manuals_root()` đọc `manuals_dir` bằng `frappe.db.get_single_value` rồi `_base_resolve` (rỗng → `None`). `read_source`, `search_source`, `git_source` không đổi chữ ký; vì đều qua `resolve_safe_path` nên kho HDSD tự bị loại (ADR-034 QĐ 5).
- `erp_ai/agent/article_guard.py` (mới, AC-45 phần chặn, ADR-034 QĐ 6): `check_article_write(doc, method)`: phiên ≠ `AGENT_USER` → không làm gì; bản mới với `status != "Draft"` → `frappe.throw("Bot chỉ được tạo bài CSKT ở trạng thái nháp", frappe.PermissionError)`; bản cũ có `owner != AGENT_USER` → `frappe.throw("Bot không được sửa bài không do bot tạo", frappe.PermissionError)`; bản cũ với `status != "Draft"` → như thông báo đầu. `check_article_delete(doc, method)`: phiên = `AGENT_USER` → `frappe.throw("Bot không được xóa bài CSKT", frappe.PermissionError)`.

### 3.8 Phiên bản

Không có API công khai bị đổi: tham số mới của `decide_route` có mặc định; cột ERP AI Accuracy đổi là đổi có chủ ý theo AC-19 (báo cáo nội bộ, không có người gọi bằng mã); không method whitelist mới ở đợt 0.

## 4. Luồng

1. **Người lưu ERP AI Setting** (phiên người, ADR-033 QĐ 7): `validate` (3.1 bước 1–13) → lỗi ở bất kỳ bước nào: `ValidationError`, không lưu, không thông báo → lưu → `on_update`: thông báo bật quyền (nếu có ô 0 → 1), cảnh báo cửa L0 → L1 (nếu nâng từ L0 và chưa "Đạt"). Không gọi ra ngoài.
2. **Cài mới / migrate** (`cmd.migrate` → `after_migrate` → `ensure_setup`): đồng bộ DocType (3 bảng con, 3 DocType U5a, trường Setting, Log) → `_ensure_default_settings` điền trường thiếu → `agent_enabled_at` nếu đang bật → trường tùy biến HD Ticket, HD Article → đồng bộ `scheduler_events` (R-5). Chạy lần hai: 0 thay đổi.
3. **Quét 15 phút** (hàng `default`, phiên scheduler): `scan_missed_tickets` → `find_missed_tickets` → `enqueue_agent_run(…, ticket_insert)` sau commit → runner như phiếu mới (giới hạn ngày, ngân sách, điều kiện gửi do runner kiểm lại).
4. **08:00 / thứ Hai / ngày 1** (phiên scheduler): hàm `cron` của `schedules.py` xếp đúng một job hàng `long` (job_id cố định) → job tính khóa chu kỳ → kiểm khóa đã có → tính → gửi/ghi → khóa chu kỳ ghi **cùng giao dịch** với email/dòng → scheduler commit. Lỗi giữa chừng → rollback toàn bộ, lần chạy sau làm lại đúng một lần (08:00 ngày sau là chu kỳ mới, D-10).
5. **Bot lưu HD Article** (phiên agent, đường của U6b sau này): `validate` → `check_article_write` → chỉ `Draft` của chính bot qua được.
6. **Người tìm báo cáo** (Desk): Frappe kiểm `roles` của Report và `report` trên `ref_doctype` → `execute`.

Gọi ra ngoài: chỉ email qua Email Queue (`delayed=True`, không mở kết nối trong job); không HTTP, không Cổng model ở đợt 0. Job `long` có `timeout` 1200 s; job `cron` ở `default` 300 s (R-5).

## 5. Quyền

| Thao tác | Ai | Kiểm ở đâu |
|---|---|---|
| Sửa ERP AI Setting (mọi trường mới) | System Manager | DocPerm hiện có; M5 (`refuse_agent_write`, T65) chặn tài khoản agent mọi đường; bảng con theo cha |
| Ghi trường tự quản (`agent_enabled_at`, `daily_report_sent_on`, `budget_alert_sent_month`, `prompt_revisions`) | chỉ controller (người lưu → `stamp_*`, `record_*`) và đúng một hàm job cho mỗi mốc bằng `set_single_value` (phiên scheduler) | khôi phục ở `validate` bước 1 |
| Đọc ERP AI Accuracy, ERP AI Cost | System Manager, ERP AI Instructor | `roles` của Report + DocPerm `report` trên ERP AI Log (2.3) |
| Đọc ERP AI KPI Weekly, ERP AI KPI Week | System Manager, ERP AI Instructor | `roles` + DocPerm |
| Ghi kết luận rà soát | System Manager, ERP AI Instructor (`write` trên ERP AI Review Month) | DocPerm + controller khóa danh sách phiếu |
| Tạo KPI Week, Review Month | job (phiên scheduler) | không DocPerm `create` cho role nào; M5 nối khi T65 ở `develop` (ADR-033 QĐ 8) |
| Đọc Error Log | Lõi `system_read` (bỏ quyền có chủ ý, ADR-021 QĐ 4) | chỉ gọi từ tool U6b; tool đọc mới không có `ignore_permissions` (luật hiện có `agent/tools/**`) |
| Tìm CSKT | phiên đang chạy (tài khoản agent trong runner) | `frappe.get_list` theo quyền |
| Lưu HD Article dưới tài khoản agent | chỉ `Draft`, chỉ bài do bot tạo, không xóa | `article_guard` (server) |
| Vai trò tài khoản agent | không đổi | ADR-034 QĐ 2; test khẳng định tập role trước = sau |

## 6. Migration và rollback

**U0 (Single + 3 bảng con + ERP AI Log + 2 trường tùy biến)**
- Lên: `cmd.migrate` (đồng bộ JSON; 0 DDL cho trường Single; tạo 3 bảng con; ERP AI Log: 5 cột mới + `actions` `text → longtext`; trường tùy biến: DDL trên `tabHD Ticket`, `tabHD Article`) → `after_migrate` điền mặc định. Giá trị người đã đặt không đổi (ADR-006); (1), (4) giữ; (2), (3), (5) = 0 (AC-1).
- Xuống: revert commit của U0 rồi `cmd.migrate`. Trường Single biến khỏi meta; dòng `tabSingles` thừa vô hại và bị xóa ở lần người lưu form kế tiếp (`update_single` ghi lại theo meta). `remove_orphan_doctypes` xóa bản ghi DocType của 3 bảng con, **giữ** bảng dữ liệu (vô hại). Trường tùy biến: xóa bản ghi Custom Field `ai_confidence_pct`, `ai_source_ticket` (cột còn lại vô hại). `actions` `longtext → text`: trước khi xuống, kiểm `max(length(actions))` ≤ 65535 trên ERP AI Log; vượt thì **không** xuống cột này (giữ Long Text — nới kiểu không hại mã cũ).
- Đối soát (dán vào `acceptance.md`): (a) trước lên, chụp `select field, value from tabSingles where doctype='ERP AI Setting'` cho 27 trường cũ; sau lên và sau xuống-rồi-lên, giá trị 27 trường trùng từng dòng; (b) đếm dòng ERP AI Log trước = sau; (c) 49 trường mới có giá trị mặc định đúng bảng 2.1; (d) `ensure_setup` chạy lần hai: ảnh chụp `tabSingles` không đổi.
- Thời điểm: cuối đợt 0, khi không dev nào dùng site `miyano` (journal FEAT-004). Dữ liệu nhỏ, không cần lô.

**U5a (3 DocType mới)** — lên: `cmd.migrate` tạo bảng; xuống: revert + `cmd.migrate` (bản ghi DocType bị xóa, bảng giữ); đối soát: số dòng KPI Week, Review Month trước = sau lên lại. Không có dữ liệu cũ cần chuyển.

**U4a, U6a** — không đổi dữ liệu; `hooks.py` đổi → `cmd.migrate` để đồng bộ lịch; xuống = revert + `cmd.migrate` (Scheduled Job Type mất hàm sẽ bị Frappe tắt khi đồng bộ).

**Quan sát (STD-OPS-5):** mỗi việc theo lịch 1 dòng `frappe.logger("erp_ai")` mỗi lần chạy (đã chạy N, bỏ qua vì cấu hình rỗng, đã làm chu kỳ này); lỗi → Error Log tiêu đề hằng mới `TITLE_DAILY_REPORT_FAILED = "erp_ai: báo cáo hằng ngày lỗi"`, `TITLE_KPI_FAILED`, `TITLE_REVIEW_FAILED` (đặt trong module của việc, không sửa `constants.py`).

## 7. Touchpoints

Bảng file của `arch-impact.md` cho từng đơn vị ở cột "Phạm vi arch-impact". Mọi file test đi kèm (colocated, `test_{name}.py`) được ghi rõ.

### U0 — Nền cấu hình (arch-impact: `erp_ai_setting.json/.py/.js`, DocType con mới, `install.py`)

| file | change | Phạm vi arch-impact | ghi chú |
|---|---|---|---|
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json` | sửa | có | 49 trường, 7 section, chuyển 2 công tắc, mô tả `permission_level`, `code_change_enabled`, `unrestricted_enabled` |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py` | sửa | có | 3.1 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.js` | sửa | có | khóa thêm/xóa dòng `prompt_revisions` |
| `erp_ai/erp_ai_agent/doctype/erp_ai_catalog_rule/{__init__.py, erp_ai_catalog_rule.json, erp_ai_catalog_rule.py}` | mới | có (DocType con) | hằng hành động, `hard_ban_reason` |
| `erp_ai/erp_ai_agent/doctype/erp_ai_user_template/{__init__.py, .json, .py}` | mới | có | |
| `erp_ai/erp_ai_agent/doctype/erp_ai_prompt_revision/{__init__.py, .json, .py}` | mới | có | |
| `erp_ai/install.py` | sửa | có | 3.2 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json` | sửa | **không — lệch D-5** | 2.3; cần team-leader chấp nhận |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py` | sửa | test | |
| `erp_ai/tests/test_install.py` | sửa | test | migrate lên/xuống |
| `erp_ai/tests/test_doctype_descriptions.py` | sửa | test | `DOCTYPE_CONFIG` Setting, Log, 3 bảng con |
| `erp_ai/test_utils.py` | sửa | test hỗ trợ | thêm `keep_agent_settings(testcase)`: chụp `tabSingles` của Setting và các bảng con trong `setUp`, trả lại trong `addCleanup` (NFR-7) |

### U4a — Phân loại ngoài lõi (arch-impact: file việc quét mới, `hooks.py` (`cron`), report ERP AI Accuracy, `routing.py`, `classification.py`)

| file | change | Phạm vi | ghi chú |
|---|---|---|---|
| `erp_ai/agent/missed_scan.py` | mới | có (file việc quét) | 3.5.1 |
| `erp_ai/hooks.py` | sửa | có | dòng `*/15` |
| `erp_ai/erp_ai_agent/report/erp_ai_accuracy/erp_ai_accuracy.py`, `.json` | sửa | có | 3.5.3 |
| `erp_ai/agent/routing.py` | sửa | có | 3.5.2 |
| `erp_ai/agent/classification.py` | sửa | có | 3.5.4 |
| `erp_ai/agent/test_missed_scan.py` | mới | test | |
| `erp_ai/agent/test_routing.py`, `erp_ai/agent/test_classification.py`, `erp_ai/erp_ai_agent/report/erp_ai_accuracy/test_erp_ai_accuracy.py` | sửa | test | |

### U5a — Vận hành ngoài lõi (arch-impact: file việc theo lịch mới, `hooks.py`, DocType KPI tuần + rà soát (mới), Script Report KPI, chi phí (mới))

| file | change | Phạm vi | ghi chú |
|---|---|---|---|
| `erp_ai/schedules.py` | mới | có (Cửa vào lịch) | 3.6.1 |
| `erp_ai/agent/ops_data.py`, `daily_report.py`, `kpi.py`, `monthly_review.py` | mới | có (file việc theo lịch) | 3.6.2–3.6.5 |
| `erp_ai/hooks.py` | sửa | có | 3 dòng `cron` |
| `erp_ai/erp_ai_agent/doctype/erp_ai_kpi_week/{__init__.py, .json, .py}` | mới | có | |
| `erp_ai/erp_ai_agent/doctype/erp_ai_review_month/{__init__.py, .json, .py}`, `erp_ai/erp_ai_agent/doctype/erp_ai_review_item/{__init__.py, .json, .py}` | mới | có | |
| `erp_ai/erp_ai_agent/report/erp_ai_kpi_weekly/{__init__.py, .json, .py}`, `erp_ai/erp_ai_agent/report/erp_ai_cost/{__init__.py, .json, .py}` | mới | có | |
| `erp_ai/agent/test_daily_report.py`, `test_kpi.py`, `test_monthly_review.py`, `test_ops_data.py`; `erp_ai/tests/test_schedules.py`; `.../erp_ai_review_month/test_erp_ai_review_month.py`; `.../erp_ai_kpi_weekly/test_erp_ai_kpi_weekly.py`; `.../erp_ai_cost/test_erp_ai_cost.py` | mới | test | |
| `erp_ai/tests/test_doctype_descriptions.py` | sửa | test | 3 DocType mới (nếu luật mô tả áp cho mọi DocType của module) |

### U6a — Tri thức, hàm đọc (arch-impact: file Lõi mới, `tools/source.py`, `hooks.py` (`doc_events` HD Article))

| file | change | Phạm vi | ghi chú |
|---|---|---|---|
| `erp_ai/agent/redact.py`, `system_read.py`, `knowledge.py`, `article_guard.py` | mới | có (file Lõi mới) | 3.7 |
| `erp_ai/agent/tools/source.py` | sửa | có | |
| `erp_ai/hooks.py` | sửa | có | `doc_events` HD Article |
| `erp_ai/agent/test_redact.py`, `test_system_read.py`, `test_knowledge.py`, `test_article_guard.py` | mới | test | |
| `erp_ai/agent/tools/test_source.py` | sửa | test | |

**So khớp đường dẫn mới ↔ `structure.allowed_new_file_roots` = `["erp_ai", "docs", ".github"]`:**
```
erp_ai/erp_ai_agent/doctype/erp_ai_catalog_rule/*      -> erp_ai  OK
erp_ai/erp_ai_agent/doctype/erp_ai_user_template/*     -> erp_ai  OK
erp_ai/erp_ai_agent/doctype/erp_ai_prompt_revision/*   -> erp_ai  OK
erp_ai/agent/missed_scan.py, test_missed_scan.py       -> erp_ai  OK
erp_ai/schedules.py, erp_ai/tests/test_schedules.py    -> erp_ai  OK
erp_ai/agent/{ops_data,daily_report,kpi,monthly_review}.py + test_*.py -> erp_ai OK
erp_ai/erp_ai_agent/doctype/{erp_ai_kpi_week,erp_ai_review_month,erp_ai_review_item}/* -> erp_ai OK
erp_ai/erp_ai_agent/report/{erp_ai_kpi_weekly,erp_ai_cost}/* -> erp_ai OK
erp_ai/agent/{redact,system_read,knowledge,article_guard}.py + test_*.py -> erp_ai OK
docs/team/features/FEAT-007/design.md                  -> docs    OK
```
**So khớp với `protected_paths` = `[".env", ".env.*", "**/*.pem", "**/*.key", "license.txt"]`:** không đường dẫn nào ở trên có tên `.env*`, đuôi `.pem`/`.key` hay là `license.txt` → 0 trùng.

## 8. Test plan

Quy ước: chạy bằng `cmd.test_one` theo file, `cmd.test` trước merge; mọi test mới gọi `keep_agent_settings(self)` (NFR-7), tự tạo dữ liệu, truyền `now` thay đồng hồ thật (STD-TEST-6), không skip (STD-TEST-4).

### U0

| Tiêu chí | Test | Loại |
|---|---|---|
| AC-1 (cài mới: 5 công tắc tắt) | `erp_ai/tests/test_install.py::TestFeat007Migrate::test_fresh_install_five_switches_off` | integration |
| AC-1 (migrate: (1), (4) giữ; (2), (3), (5) = 0 khi (4) bật) | `test_install.py::TestFeat007Migrate::test_migrate_keeps_old_switches_new_switches_off` — xóa dòng `tabSingles` của trường mới, đặt `unrestricted_enabled=1`, `code_change_enabled=1`, chạy `ensure_setup` | integration |
| AC-1 (migrate lần hai không đổi) | `test_install.py::TestFeat007Migrate::test_second_migrate_changes_nothing` (ảnh chụp `tabSingles` bằng nhau) | integration |
| STD-OPS-2 (xuống: dòng thừa vô hại) | `test_install.py::TestFeat007Migrate::test_leftover_single_rows_dropped_on_next_human_save`; `::test_orphan_child_rows_do_not_break_get_single` | integration |
| STD-OPS-2 (lên/xuống thật trên site dev) | Kiểm có đầu ra: mục 6 "Đối soát" (a)–(d), dán vào `acceptance.md` | manual + lệnh |
| NFR-4 (mặc định an toàn, liệt kê từng giá trị) | `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py::TestFeat007Defaults::test_every_new_field_default` (bảng 2.1) | unit |
| AC-4 (thông báo khi bật, đúng tên, hậu quả, môi trường; mỗi ô một ca) | `test_erp_ai_setting.py::TestPermissionSwitchNotice::test_each_switch_on_shows_name_consequence_environment` (5 ca, chặn `frappe.msgprint`) | unit |
| AC-4 (lưu không đổi công tắc → không thông báo; tắt → không) | `::test_save_without_switch_change_no_notice`, `::test_switch_off_no_notice` | unit |
| AC-4 (Toàn quyền có câu gọi hàm tự do) | `::test_unrestricted_notice_has_call_method_caveat` | unit |
| AC-12 (cấu hình môi trường, mặc định production) | `TestFeat007Defaults::test_site_environment_default_production_and_options` | unit |
| AC-18 (cảnh báo nâng mức khi chưa Đạt; Đạt → không) | `test_erp_ai_setting.py::TestLevelRaiseWarning::test_raise_from_l0_not_passed_warns_and_saves`, `::test_raise_from_l0_passed_no_warning`, `::test_change_l1_to_l2_no_gate_warning` (giả `l0_l1_gate`) | unit |
| AC-22, AC-36 (ngưỡng, chuỗi duyệt: mặc định và biên) | `TestFeat007Limits::test_int_limits_edges` (mỗi trường mới: low−1 bị chặn, low, high, high+1 bị chặn) | unit |
| AC-24 (tên trường sai bị chặn; kiểu hạn sai; giá trị BGĐ thiếu trường) | `test_erp_ai_setting.py::TestTicketFieldNames::test_unknown_field_blocked`, `::test_due_field_must_be_date`, `::test_board_value_needs_origin_field`, `::test_existing_custom_field_saves` (test tạo Custom Field tạm) | integration |
| AC-26 (mốc phản hồi mặc định 15', 15', 1h, 1h, 1h, 5') | `test_erp_ai_setting.py::TestFeat007Defaults::test_response_targets_reuse_routing_rules` | unit |
| AC-29 (lưu 4 dòng cấm bị chặn: DocType app, phân quyền, chứng từ submit, hành động không có) | `test_erp_ai_setting.py::TestCatalogRules::test_four_hard_bans_blocked` | integration |
| AC-29 (hình dạng dòng: DocType/trường theo hành động, đầu mục, trùng; dòng hợp lệ lưu được) | `TestCatalogRules::test_row_shape_rules`, `::test_valid_rule_saves_and_categories_normalized` | unit |
| AC-29 (điều cấm cứng một nguồn) | `TestCatalogRules::test_hard_ban_follows_denied_doctypes_source` (thêm DocType giả vào `read.denied_doctypes` bằng patch → bị chặn) | unit |
| AC-30 (mẫu tài khoản: vai trò cấm, vai trò không có, tên trùng) | `test_erp_ai_setting.py::TestUserTemplates::test_forbidden_role_blocked` (6 vai trò), `::test_unknown_role_and_duplicate_name_blocked`, `::test_valid_template_saves` | unit |
| AC-31 (cap mặc định A L2, B L3, C L1, D L2, E L1, F L3) | `TestFeat007Defaults::test_level_caps_default` | unit |
| AC-38 (thiếu mục bắt buộc → chặn; quá 20000 → chặn) | `test_erp_ai_setting.py::TestPromptOverrides::test_missing_marker_blocked_each_part`, `::test_too_long_blocked` | unit |
| AC-38 (bản dựng sẵn qua kiểm của chính nó) | `TestPromptOverrides::test_builtin_prompts_pass_required_markers` | unit |
| AC-38 (lịch sử: người, thời điểm, giá trị cũ; không đổi → không dòng; người không sửa được lịch sử) | `TestPromptOverrides::test_revision_row_on_change`, `::test_no_revision_without_change`, `::test_revisions_restored_on_save` | integration |
| AC-44, AC-46, AC-63 (số mặc định 3, 5, 10) | `TestFeat007Defaults::test_every_new_field_default` | unit |
| AC-47 (kho HDSD phải là thư mục dưới apps/) | `test_erp_ai_setting.py::TestManualsDir::test_missing_or_outside_dir_blocked`, `::test_existing_dir_saves` (dùng `TempAppsRoot`) | unit |
| AC-49 (báo cáo không có, sai loại, đang tắt, dựa trên phiếu → chặn) | `test_erp_ai_setting.py::TestAllowedReports::test_unknown_type_disabled_ticket_based_blocked`, `::test_log_based_report_blocked`, `::test_safe_report_saves` | integration |
| AC-51, AC-59, AC-27 (email sai, user tắt, người theo dõi là agent → chặn) | `test_erp_ai_setting.py::TestOperationPeople::test_bad_email_blocked`, `::test_disabled_reviewer_blocked`, `::test_watcher_must_be_enabled_human` | unit |
| AC-55 (mục tiêu KPI: thiếu khóa, giá trị âm, JSON hỏng → chặn; mặc định hợp lệ) | `test_erp_ai_setting.py::TestKpiTargets::test_bad_targets_blocked`, `::test_default_targets_valid` | unit |
| ADR-033 QĐ 6 (mốc tự quản không bị người dời; `agent_enabled_at` đặt khi bật 0 → 1) | `test_erp_ai_setting.py::TestSelfManagedFeat007::test_watermarks_restored_on_human_save`, `::test_agent_enabled_at_stamped_on_enable_only` | integration |
| AC-20 (Instructor có `report` trên ERP AI Log) | `erp_ai/tests/test_install.py::TestFeat007Migrate::test_instructor_can_report_on_log` | integration |
| Mô tả ≤ 400 ký tự, cụm bắt buộc, section | `erp_ai/tests/test_doctype_descriptions.py` (các test hiện có, `DOCTYPE_CONFIG` mới) | unit |
| NFR-7 | `erp_ai/test_utils.py` dùng ở mọi lớp trên; `cmd.test` chạy hai lần liên tiếp cùng kết quả (kiểm có đầu ra ở verify) | lệnh |

### U4a

| Tiêu chí | Test | Loại |
|---|---|---|
| AC-16 (7 loại phiếu: đúng phiếu được xếp hàng) | `erp_ai/agent/test_missed_scan.py::TestMissedScan::test_seven_ticket_kinds` (tạo sau/trước khi bật, của agent, nhóm loại trừ, cờ không dùng AI, đủ 3 trường, hết lượt ngày, mới tạo < 5') | integration |
| AC-16 (lần chạy lỗi rồi quét → xếp lại) | `::test_failed_run_requeued` | integration |
| AC-16 (quét hai lần → một job mỗi phiếu, NFR-3) | `::test_two_scans_one_job_per_ticket` (giả `frappe.enqueue`, kiểm `job_id`) | integration |
| AC-16 (biên 5 phút; agent tắt; chưa có `agent_enabled_at`) | `::test_grace_edge_exactly_five_minutes`, `::test_agent_disabled_noop`, `::test_no_enabled_at_noop` | unit |
| AC-16 (khai báo lịch 15 phút) | `::test_cron_declared_every_15_minutes` (đọc `frappe.get_hooks("scheduler_events")["cron"]`) | unit |
| AC-17 (6 phiếu: 1', 5', 6', lỗi, chưa chạy, bị bỏ qua → 3 số; đúng 5' tính "≤ 5") | `erp_ai/erp_ai_agent/report/erp_ai_accuracy/test_erp_ai_accuracy.py::TestLatencySummary::test_six_tickets_three_numbers` | integration |
| AC-18 (7 ca cửa L0 → L1: 29 nhãn, 40/34, 40/33, 30/26, ngoài 14 ngày) | `test_erp_ai_accuracy.py::TestGate::test_not_enough_sample_29`, `::test_pass_exactly_85`, `::test_fail_82_5`, `::test_pass_30_26`, `::test_outside_window_ignored`; ca cảnh báo lưu: xem U0 `TestLevelRaiseWarning` | unit |
| AC-19 (6 loại phiếu: nhãn lúc tạo, sửa sau, im lặng, lỗi, D/E bỏ trống nhóm, hai nhãn khác nhau) | `test_erp_ai_accuracy.py::TestLabels::test_six_label_cases` | integration |
| AC-20 (Instructor chạy được; chỉ Agent bị từ chối; System Manager được) | `test_erp_ai_accuracy.py::TestAccess::test_three_accounts` (gọi `frappe.desk.query_report.run` dưới từng user) | integration |
| AC-25 (bảng chân trị ≥ 14 ca: 6 đầu mục × có/không điều kiện + 2 ca thiếu trường hạn) | `erp_ai/agent/test_routing.py::TestPriorityExceptions::test_truth_table` (subTest), `::test_missing_due_field_note` | unit |
| AC-25 (không hạ mức đã cao; [GẤP], F, E giữ) | `TestPriorityExceptions::test_existing_rules_kept` | unit |
| AC-26 (quá mốc, đúng mốc, đã phản hồi; D có/không Hạn hoàn thành) | `test_routing.py::TestResponseOverdue::test_over_exact_answered`, `::test_processing_deadline_d_with_and_without_due` | unit |
| AC-26 (đếm trong báo cáo hằng ngày) | xem U5a `test_daily_report.py::TestBuild::test_twelve_tickets_sections` | integration |
| AC-27 (D có cấu hình, C, D không cấu hình, người theo dõi không hoạt động) | `test_routing.py::TestDWatcher::test_d_configured`, `::test_other_category_none`, `::test_d_unconfigured_note`, `::test_inactive_watcher_none` | unit |
| AC-28 (4 yêu cầu → chữ comment; 1 yêu cầu → không; cắt 10 yêu cầu) | `erp_ai/agent/test_classification.py::TestSplitComment::test_four_requests`, `::test_single_request_none`, `::test_caps_at_ten` | unit |
| NFR-8 (đổi cột/ý nghĩa ERP AI Accuracy) | test cũ trong `test_erp_ai_accuracy.py` ghim "im lặng = đúng" được sửa theo AC-19, lý do ghi ở commit và `acceptance.md` | — |

### U5a

| Tiêu chí | Test | Loại |
|---|---|---|
| AC-51 (12 phiếu đủ loại → từng mục nội dung) | `erp_ai/agent/test_daily_report.py::TestBuild::test_twelve_tickets_sections` | integration |
| AC-51 (khai báo lịch 08:00, thứ Hai, ngày 1) | `erp_ai/tests/test_schedules.py::TestCron::test_cron_strings`; `::test_enqueue_long_fixed_job_id` | unit |
| AC-52 (người nhận rỗng; hai lần cùng ngày → 1 email; lỗi gửi → log, không ném; phiếu loại trừ có chuỗi gieo → 0 lần trong email; ngày trống vẫn gửi số 0) | `test_daily_report.py::TestRun::test_no_recipients_logs_only`, `::test_twice_same_day_one_email`, `::test_send_error_logged_not_raised_watermark_kept`, `::test_excluded_ticket_counts_only`, `::test_empty_day_sends_zeros` | integration |
| AC-52 / ADR-033 (chạy 02:00 → chu kỳ hôm qua; cuối tuần tắt) | `erp_ai/agent/test_ops_data.py::TestCycles::test_daily_weekly_monthly_cycles`; `test_daily_report.py::TestRun::test_weekend_skipped_when_off` | unit |
| NFR-6 (khóa giả trong tiêu đề phiếu → đã che trong email) | `test_daily_report.py::TestRun::test_secret_in_subject_redacted` | integration |
| AC-53 (KPI 1–3 trên 10 phiếu cố định, ca mẫu 0) | `erp_ai/agent/test_kpi.py::TestKpi::test_kpi1_median_and_rates`, `::test_kpi2_open_at_week_end`, `::test_kpi3_bot_only_closures`, `::test_zero_sample_none` | integration |
| AC-54 (KPI 4–6; biên đúng 72 giờ, đúng 5 ngày) | `test_kpi.py::TestKpi::test_kpi4_b_resolution_hours`, `::test_kpi5_task_within_72h_edge`, `::test_kpi6_stale_edges` | integration |
| AC-55 (tính tuần W hai lần → 1 dòng, cùng giá trị; W+1 so với W; bù tuần thiếu ≤ 8) | `test_kpi.py::TestRunWeekly::test_same_week_twice_one_row`, `::test_next_week_compares`, `::test_backfill_capped_at_eight` | integration |
| AC-56 (6 KPI một màn: tuần này, tuần trước, GĐ2, GĐ4; "chưa có dữ liệu") | `erp_ai/erp_ai_agent/report/erp_ai_kpi_weekly/test_erp_ai_kpi_weekly.py::TestReport::test_six_rows_columns` | integration |
| AC-56, AC-20 (quyền: Instructor được, chỉ Agent bị từ chối) | `test_erp_ai_kpi_weekly.py::TestReport::test_access_three_accounts` | integration |
| AC-56 (màn hình thật) | Kiểm có đầu ra: mở `/app/query-report/ERP AI KPI Weekly` bằng tài khoản chỉ có ERP AI Instructor, dán ảnh | manual |
| AC-59 (25 phiếu → 10 không trùng; 6 → 6; chạy lại → cùng bộ; nhóm loại trừ vắng; người rà rỗng → không thông báo, danh sách vẫn tạo) | `erp_ai/agent/test_monthly_review.py::TestReview::test_25_gives_10_unique`, `::test_6_gives_6`, `::test_rerun_same_set`, `::test_excluded_absent`, `::test_no_reviewers_list_still_created` | integration |
| AC-59 (kết luận, người rà; không đổi được danh sách) | `.../erp_ai_review_month/test_erp_ai_review_month.py::TestReviewMonth::test_verdict_sets_reviewer`, `::test_ticket_list_locked` | integration |
| AC-60 (3 phiếu × 4 lần chạy: tổng theo phiếu, theo lần chạy, tổng tháng = `spent_this_month_usd` sau `recompute_monthly_spend`; sai số 0 ở 6 chữ số) | `erp_ai/erp_ai_agent/report/erp_ai_cost/test_erp_ai_cost.py::TestCost::test_per_ticket_and_run_totals`, `::test_month_total_matches_spent` | integration |
| AC-20 (ERP AI Cost: ba tài khoản) | `test_erp_ai_cost.py::TestCost::test_access_three_accounts` | integration |
| ADR-033 Ràng buộc (lỗi giữa chừng → khóa chu kỳ không ghi, lần sau làm đúng một lần) | `test_kpi.py::TestRunWeekly::test_error_midway_no_row_then_once`; `test_monthly_review.py::TestReview::test_error_midway_no_row_then_once` | integration |

### U6a

| Tiêu chí | Test | Loại |
|---|---|---|
| AC-50 (lọc thời gian và từ khóa, giới hạn dòng, khoảng > 7 ngày bị từ chối) | `erp_ai/agent/test_system_read.py::TestErrorLogs::test_time_and_keyword_filter`, `::test_limit_bounds`, `::test_window_over_seven_days_refused` | integration |
| AC-50, NFR-6 (Error Log chứa khóa giả, mật khẩu giả → che) | `test_system_read.py::TestErrorLogs::test_seeded_secrets_masked` | integration |
| AC-50 (tập role tài khoản agent không đổi) | `test_system_read.py::TestErrorLogs::test_agent_roles_unchanged` | integration |
| NFR-6 (mẫu che: từng loại, giữ tên khóa, không che chữ thường) | `erp_ai/agent/test_redact.py::TestRedact::test_each_pattern`, `::test_plain_text_untouched` | unit |
| AC-46 (6 bài: 2 nháp, 1 lưu trữ → chỉ Published; thứ tự theo số từ khớp; hai từ đảo vẫn thấy; giới hạn; giữ dấu) | `erp_ai/agent/test_knowledge.py::TestKbSearch::test_only_published`, `::test_rank_by_matched_words`, `::test_reversed_two_words`, `::test_limit`, `::test_vietnamese_accents_distinguish` | integration |
| AC-46 (câu tìm rỗng) | `TestKbSearch::test_empty_query_refused` | unit |
| AC-47 (kho giả 3 tài liệu: khớp, không khớp, chưa cấu hình → `None`) | `test_knowledge.py::TestManuals::test_match_returns_document_heading_line`, `::test_no_match_empty`, `::test_unconfigured_none` | integration |
| AC-47 (file trong kho không đọc được qua `read_source`/`search_source`/`git_source`; thư mục kho vẫn lưu được) | `erp_ai/agent/tools/test_source.py::TestManualsExcluded::test_read_source_refuses_manual_file`, `::test_search_source_skips_manuals`, `::test_resolve_manual_path_only_inside` | integration |
| AC-45 phần chặn (dưới tài khoản agent: chèn Draft được; chèn Published, đổi sang Published, sửa bài của người, xóa → từ chối; người xuất bản bài nháp của bot được) | `erp_ai/agent/test_article_guard.py::TestArticleGuard::test_agent_insert_draft_ok`, `::test_agent_publish_refused`, `::test_agent_edit_human_article_refused`, `::test_agent_delete_refused`, `::test_human_publishes_bot_draft` | integration |
| ADR-034 Ràng buộc (`hooks.py` có HD Article; không `override_whitelisted_methods` trỏ `helpdesk.*`; không gọi `helpdesk.api.article.search`) | `test_article_guard.py::TestArticleGuard::test_hooks_registered`; `test_knowledge.py::TestKbSearch::test_no_helpdesk_search_import` | unit |

### Đối chiếu danh sách AC (Done criteria)

AC của đợt 0 theo bảng đơn vị build (`arch-impact.md`):
```
U0 : phần cấu hình Gói 1–6 (AC-1, AC-4 form, AC-12, AC-22, AC-24, AC-26, AC-29, AC-30, AC-31, AC-36, AC-38, AC-44, AC-46, AC-47, AC-49, AC-51, AC-55, AC-59, AC-63), test migrate lên/xuống
U4a: AC-16, AC-17, AC-18, AC-19, AC-20, AC-25, AC-26, AC-27, AC-28
U5a: AC-51, AC-52, AC-53, AC-54, AC-55, AC-56, AC-59, AC-60
U6a: hàm Error Log (AC-50), tìm CSKT (AC-46), tìm HDSD (AC-47), loại thư mục HDSD khỏi source.py (AC-47), hook HD Article (AC-45 phần chặn)
```
AC có ít nhất một dòng trong test plan ở trên:
```
U0 : AC-1, AC-4, AC-12, AC-18(cảnh báo), AC-20(quyền Log), AC-22, AC-24, AC-26, AC-27(cấu hình), AC-29, AC-30, AC-31, AC-36, AC-38, AC-44, AC-46, AC-47, AC-49, AC-51, AC-55, AC-59, AC-63, NFR-4, NFR-7, STD-OPS-2
U4a: AC-16, AC-17, AC-18, AC-19, AC-20, AC-25, AC-26, AC-27, AC-28
U5a: AC-51, AC-52, AC-53, AC-54, AC-55, AC-56, AC-59, AC-60, AC-20, NFR-6
U6a: AC-45, AC-46, AC-47, AC-50, NFR-6
```
Không AC nào của bảng thiếu test. Phần AC còn lại ở đơn vị sau: bảng ở mục 1.
