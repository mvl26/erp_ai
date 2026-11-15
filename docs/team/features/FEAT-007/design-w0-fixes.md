Feature: FEAT-007
Stage: design
Author-agent: designer
Date: 2026-11-14
Approved-by:
<!-- Cổng: G2b không áp dụng cho FEAT-007 (team.py: chỉ G5). Để trống. -->

# Sửa design đợt 0 theo rà soát kiến trúc — FEAT-007 (vòng 1/3)

## 0. Cách đọc

- File này **thắng** `design.md` ở mọi chỗ hai file khác nhau. Mỗi fix ghi: finding của `arch-review-design-w0.md`, (các) dòng `design.md` bị thay, và văn bản thay đầy đủ. Phần `design.md` không nhắc ở đây giữ nguyên.
- Không đổi spec, AC, luật nghiệp vụ hay ADR. Không đổi gì của U4a, U6a ngoài chỗ ghi rõ.
- Addendum đợt 1 viết song song trên `design.md` phải đối chiếu bảng "Tên chuyển chỗ" (mục 3) và việc hòa nhập (mục 4).

**Căn cứ đọc trực tiếp (đích đã biết, không qua Explore), 2026-11-14, `develop` @ `1918db2`:**
- `erp_ai/tests/test_architecture.py:69-80` `LAYER_RULES`: scope `erp_ai.agent` cấm import `erp_ai.erp_ai_agent`; `:109-113` scope `erp_ai.agent.policy` cấm `erp_ai.agent.tools`; `:118-120` `ENQUEUE_TARGETS` 2 chuỗi, 5 tham số bắt buộc; `:529-575` `check_single_enqueue_site` (mọi file trừ `agent/queue.py`), `check_enqueue_call_shape` (chữ lỗi "expected exactly two"); `:2325-2345` `test_enqueue_targets_pinned`, `test_enqueue_call_shape_requires_exactly_two_calls` (lớp `TestScannersCatchViolations`); `:1592` `ENTRY_TYPES_EXPECTED`, `:2126` `test_entry_types_unchanged`. Trên `team/FEAT-004` các khối này giữ nguyên chữ (chỉ dời dòng, ví dụ `:2799`).
- `erp_ai/agent/tools/read.py:4` import `erp_ai.agent.policy` → module nào vừa được `policy` import vừa import `tools.read` sẽ tạo vòng import.
- `erp_ai/agent/tools/site_api.py:32` (`develop`): `DENIED_DOCTYPES = (read.DENIED_DOCTYPES - {User}) | {PROPOSAL_DOCTYPE, "Custom Role"}`; `:36` `FORBIDDEN_ROLES`. `team/FEAT-004-task-59-r2` `site_api.py:26` `PERMISSION_DOCTYPES = {Custom Role, Custom DocPerm, DocType, Role}`, `:53` `always_denied_doctypes()`, `:59` `_denied_doctypes(ctx)`; `DENIED_DOCTYPES` không còn. `team/FEAT-004` chưa chứa T59-r2.
- `read.DENIED_DOCTYPES` (`develop`) không có `Role` → trên `develop` một dòng danh mục trỏ `Role` chỉ bị chặn sau T59.
- `team/FEAT-004`: `erp_ai/agent/agent_write_guard.py:29` `refuse_agent_write(doc)` (T65 đã merge); `erp_ai_log.py` gọi nó ở `before_insert`, `validate`, `on_trash`, `before_rename`; `run_log.write_entry` mở bằng `allow_agent_write()`. `develop` chưa có file này.
- `erp_ai/agent/queue.py` (trùng giữa hai nhánh): 2 lời `frappe.enqueue`, `JOB_TIMEOUT_S` = 600 từ `constants.py:40`.
- `erp_ai/constants.py` (71 dòng) là nơi hiện có của mọi hằng Select dùng chung giữa Lõi và controller (`LEVELS`, `CATEGORIES`, `CHANGE_STATUS_*`, `KEY_STATUS_*`, `TRIGGER_*`); không task mở nào của FEAT-004/FEAT-005 sửa nó.
- `erp_ai_log.json`: `entry_type` = `classify\nreason\nskip\nchange`, `trigger` = `ticket_insert\ncomment_mention\nchange_action`, `actions` = Small Text, 38 trường dữ liệu; `test_erp_ai_log.py:119-129` ghim tập role DocPerm = {System Manager, ERP AI Agent}.

## 1. Finding → nơi giải quyết

| # | Finding (`arch-review-design-w0.md`) | Giải quyết ở |
|---|---|---|
| 1 | blocker STD-DESIGN-6 — Lõi import hằng/hàm từ controller DocType (`design.md:198, 212, 307, 338`) | F-1; bảng tên chuyển chỗ mục 3; touchpoint U0 mục 5.1; test U0 mục 6.1 |
| 2 | blocker STD-DESIGN-2 — `frappe.enqueue` trong `erp_ai/schedules.py` (`design.md:415, 576`) | F-2; mục 3; touchpoint U5a mục 5.2; test U5a mục 6.2 |
| 3 | major STD-DESIGN-2 — `hard_ban_reason` dùng `site_api.DENIED_DOCTYPES` (`design.md:223`) | F-3; việc hòa nhập INT-1 (mục 4); test U0 mục 6.1 |
| 4 | major STD-DESIGN-2 — M5 trên 2 DocType mới của U5a không có chủ (`design.md:87, 519`) | F-4; việc hòa nhập INT-2 (mục 4); touchpoint U5a mục 5.2; test U5a mục 6.2 |
| 5 | Phán quyết D-5 (`erp_ai_log.json` ở U0; option chuyển U3/U6b; test Instructor) | F-5; mục 3 (option chuyển đơn vị); touchpoint U0; test U0 |
| 6 | Phán quyết D-6 (`actions` → Long Text, test mới, chiều xuống) | F-6; test U0 mục 6.1 |
| 7 | minor (tên test `test_excluded_ticket_counts_only`) | F-7; test U5a mục 6.2 |

## 2. Các fix

### F-1 — Lõi không import controller DocType (blocker 1, ADR-001, STD-DESIGN-6)

**Quyết định.** Hằng thuần đặt ở `erp_ai/constants.py` (nơi hiện có của hằng Select dùng chung); `hard_ban_reason` đặt ở module Lõi mới `erp_ai/agent/hard_bans.py`. Controller Setting, Lõi (`agent/**`, kể cả `agent/tools/**`) và report đều import từ hai chỗ này; không file nào dưới `erp_ai/agent/**` import `erp_ai.erp_ai_agent.*`. Lý do tách hai chỗ (không một module như gợi ý của review): `policy.py` (U7) phải đọc `MODE_*`, còn `hard_ban_reason` import `tools.read`, mà `read.py:4` import `policy` — để chung một module là vòng import `policy` → module → `tools.read` → `policy` và trái tinh thần luật `erp_ai.agent.policy` ↛ `erp_ai.agent.tools`. Chiều phụ thuộc đúng như review đòi (A-D6).

**Thay `design.md:198`** (câu cuối sau khối JSON) bằng:
> `stale_over_5_days`: 21 phiếu hiện tại giảm 50% / 80% (làm tròn xuống). Hằng `KPI_IDS` (6 khóa trên, đúng thứ tự) đặt trong `erp_ai/constants.py` (U0); `erp_ai_setting.py` (`check_kpi_targets`), `erp_ai/agent/kpi.py` và report ERP AI KPI Weekly (U5a) import từ đó.

**Thay `design.md:212`** (câu dẫn bảng hằng) bằng:
> Hằng trong `erp_ai/constants.py` (U0; controller Setting, `policy` và bộ thực thi U7 import, không chép). `erp_ai_catalog_rule.py` chỉ còn lớp `Document` rỗng, không hằng, không hàm:

Bảng `design.md:214-221` giữ nguyên.

**Thay `design.md:223`**: văn bản đầy đủ ở F-3 (một đoạn thay cho cả finding 1 và 3).

**Thay `design.md:307`** (bước 7 của `validate`) bằng:
> 7. `check_allowed_reports()` (AC-49, ADR-034 QĐ 3), mỗi dòng (E-6): `"Báo cáo '{r}' không có"`; `"Báo cáo '{r}' phải là Script Report hoặc Query Report"`; `"Báo cáo '{r}' đang tắt"`; `"Báo cáo '{r}' dựa trên {dt}, mang nội dung phiếu hoặc dữ liệu của app: bot không được chạy"` khi `ref_doctype` ∈ `TICKET_CONTENT_DOCTYPES` ∪ `read.denied_doctypes()`. Hằng `TICKET_CONTENT_DOCTYPES` (D-13) đặt trong `erp_ai/constants.py`; controller này và tool U6b import từ đó.

**Thay `design.md:338`** bằng:
> - `KPI_IDS`, `TICKET_CONTENT_DOCTYPES`, `ACTION_*` (6), `CATALOG_ACTIONS`, `MODE_*` (3), `CATALOG_MODES` ở `erp_ai/constants.py`; `hard_ban_reason` ở `erp_ai/agent/hard_bans.py`: import, không chép. Không module nào dưới `erp_ai/agent/**` import `erp_ai.erp_ai_agent.*` (ADR-001, `test_architecture.py::TestArchitecture::test_layer_imports`). Tên còn ở controller (`PROMPT_REQUIRED_MARKERS`, `PROMPT_OVERRIDE_MAX_CHARS`, `INT_LIMITS`) và ở report ERP AI Accuracy (`l0_l1_gate`, `GateResult`, `GATE_*`) chỉ controller, report và test của chúng được dùng; đơn vị Lõi nào cần một tên trong số đó thì addendum của đơn vị ấy chuyển tên xuống `erp_ai/constants.py` hoặc `erp_ai/agent/` trước khi dùng. `erp_ai/agent/policy.py` không import `erp_ai.agent.hard_bans` (vòng import qua `read.py:4`).

**Thay ghi chú dòng `design.md:550`** (touchpoint `erp_ai_catalog_rule/*`): `"lớp Document rỗng; hằng ở constants.py, hard_ban_reason ở agent/hard_bans.py (F-1)"`. Touchpoint U0 đầy đủ: mục 5.1.

**`erp_ai/constants.py` (U0, sửa) — khối thêm ở cuối file** (một khối liền để gộp với nhánh khác dễ):
- `ACTION_CREATE_USER`, `ACTION_ADD_TEAM_MEMBER`, `ACTION_ADD_HOLIDAY`, `ACTION_SET_ITEM_GROUP`, `ACTION_CREATE_CUSTOM_FIELD`, `ACTION_UPDATE_FIELDS` — giá trị như bảng `design.md:214-221`.
- `CATALOG_ACTIONS` = tuple 6 hằng trên theo thứ tự bảng; `MODE_DENY = "Cấm"`, `MODE_NEEDS_APPROVAL = "Cần duyệt"`, `MODE_AUTO = "Tự làm"`; `CATALOG_MODES = (MODE_DENY, MODE_NEEDS_APPROVAL, MODE_AUTO)`. Option Select `action`, `mode` của `erp_ai_catalog_rule.json` = `"\n".join(...)` của hai tuple (test ghim, mục 6.1); bước "hành động không hợp lệ" của `check_catalog_rules` so với `CATALOG_ACTIONS`.
- `KPI_IDS = ("first_response_minutes", "complete_fields_pct", "closed_without_human_pct", "b_resolution_hours", "c_task_in_3_days_pct", "stale_over_5_days")`.
- `TICKET_CONTENT_DOCTYPES = ("HD Ticket", "HD Ticket Comment", "Comment", "Communication", "File")` (D-13).

### F-2 — Mọi `frappe.enqueue` ở `agent/queue.py` (blocker 2, ADR-003 Ràng buộc nới bởi ADR-013, ADR-033 QĐ 2, 6)

**Thay toàn bộ mục 3.6.1 (`design.md:413-415`)** bằng:

> #### 3.6.1 Hàm xếp hàng ở `erp_ai/agent/queue.py` (sửa) và Cửa vào lịch `erp_ai/schedules.py` (mới)
>
> `agent/queue.py` thêm (ADR-003 QĐ 2, ADR-013 QĐ 2, mở rộng bởi ADR-033 QĐ 6):
> - Hằng `SCHEDULED_JOB_TIMEOUT_S = 1200` (R-5 phương án B; số thời gian riêng của job theo lịch, không đổi `JOB_TIMEOUT_S`).
> - `enqueue_daily_report_job() -> None`: đúng một lời `frappe.enqueue("erp_ai.agent.daily_report.run_daily_report", queue="long", timeout=SCHEDULED_JOB_TIMEOUT_S, enqueue_after_commit=True, job_id="erp_ai::daily_report", deduplicate=True)`.
> - `enqueue_weekly_kpi_job() -> None`: như trên, đích `"erp_ai.agent.kpi.run_weekly_kpi"`, `job_id="erp_ai::weekly_kpi"`.
> - `enqueue_monthly_review_job() -> None`: như trên, đích `"erp_ai.agent.monthly_review.run_monthly_review"`, `job_id="erp_ai::monthly_review"`.
> - Không truyền kwarg nào khác (không `now`): job tự tính khóa chu kỳ từ lịch (3.6.2). Đích là chuỗi; `queue.py` không import ba module job. `enqueue_agent_run`, `enqueue_change_job` không đổi.
>
> `erp_ai/schedules.py`: `enqueue_daily_report()`, `enqueue_weekly_kpi()`, `enqueue_monthly_review()` — mỗi hàm một dòng gọi hàm `*_job` tương ứng (`from erp_ai.agent import queue`); không gọi, không import `enqueue`/`enqueue_doc` (`check_single_enqueue_site`). Tên trong `hooks.py` (3.4, `design.md:356-358`) giữ nguyên.
>
> `erp_ai/tests/test_architecture.py` (U5a, sửa đúng ba chỗ):
> - `ENQUEUE_TARGETS` thêm 3 chuỗi đích trên (tổng 5).
> - `check_enqueue_call_shape`: chữ lỗi `"expected exactly two enqueue calls"` → `f"expected exactly {len(ENQUEUE_TARGETS)} enqueue calls, one per target"`; docstring dẫn "ADR-003/ADR-013 QĐ 2, ADR-033 QĐ 6".
> - `TestScannersCatchViolations::test_enqueue_targets_pinned` ghim tuple 5 chuỗi; `test_enqueue_call_shape_requires_exactly_two_calls` đổi tên thành `test_enqueue_call_shape_requires_one_call_per_target` (ca: thiếu một đích, thừa một lời gọi; khớp chữ `"one per target"`). Lý do sửa ghim ghi trong commit: ADR-033 QĐ 6 (NFR-8, STD-TEST-5).

**Thay `design.md:504`** (luồng 4) bằng:
> 4. **08:00 / thứ Hai / ngày 1** (phiên scheduler): hàm `cron` của `schedules.py` gọi hàm `*_job` của `agent/queue.py` → xếp đúng một job hàng `long` (`job_id` cố định, `deduplicate`, sau commit) → job tính khóa chu kỳ → kiểm khóa đã có → tính → gửi/ghi → khóa chu kỳ ghi **cùng giao dịch** với email/dòng → scheduler commit. Lỗi giữa chừng → rollback toàn bộ, lần chạy sau làm lại đúng một lần (08:00 ngày sau là chu kỳ mới, D-10).

**Thay câu cuối `design.md:508`** bằng: "Job `long` có `timeout` `SCHEDULED_JOB_TIMEOUT_S` = 1200 s (`agent/queue.py`); job `cron` ở `default` 300 s (R-5)."

**Thay dòng touchpoint `design.md:576`** và thêm `agent/queue.py`, `agent/test_queue.py`, `tests/test_architecture.py`: touchpoint U5a đầy đủ ở mục 5.2. **Thay test `design.md:676`**: mục 6.2.

**Gộp khi merge:** `test_architecture.py` xung đột chữ với `team/FEAT-004` (+802 dòng, T68 còn mở) và FEAT-005 T14; khi merge `develop` vào `team/FEAT-007`, gộp tay, giữ phần của hai nhánh kia và ba chỗ sửa trên.

### F-3 — `hard_ban_reason` dẫn xuất từ một nguồn, theo tên của T59 (major 1, ADR-031 Ràng buộc, ADR-023 QĐ 3)

**Thay toàn bộ `design.md:223`** bằng:

> `MODE_DENY`, `MODE_NEEDS_APPROVAL`, `MODE_AUTO`, `CATALOG_MODES`, `CATALOG_ACTIONS` ở `erp_ai/constants.py` (F-1).
>
> Hàm công khai `hard_ban_reason(doctype: str) -> str | None` đặt trong module Lõi mới `erp_ai/agent/hard_bans.py` — một nguồn cho kiểm lúc lưu (U0) và bộ thực thi (U7) (ADR-031 Ràng buộc). Module chỉ import `frappe`, `erp_ai.agent.tools.read`, `erp_ai.agent.tools.site_api`; **không chứa chuỗi tên DocType nào** (grep của ADR-031; test mục 6.1). Xét theo thứ tự, trả lý do đầu tiên khớp:
> 1. `doctype ∈ read.denied_doctypes()` → `"DocType bị cấm với bot (dữ liệu của app, tài khoản hoặc dữ liệu nhạy cảm)"`;
> 2. `doctype ∈ PERMISSION_SET` → `"DocType phân quyền"`;
> 3. `frappe.get_meta(doctype).is_submittable` → `"chứng từ submit"`;
>
> ngược lại `None`. DocType không tồn tại là lỗi của bên gọi (`frappe.DoesNotExistError` từ `get_meta`); controller kiểm `"không có DocType {dt}"` trước (3.1 bước 5).
>
> `PERMISSION_SET` = tập DocType phân quyền công khai của `site_api`:
> - Trên nhánh nền `develop` @ `1918db2` (chưa có T59): `site_api.DENIED_DOCTYPES` (tên đang có; phần nó thêm vào `read.denied_doctypes()` là `Custom Role`).
> - Từ lần merge `develop` (đã có `team/FEAT-004` gồm T59) vào `team/FEAT-007`: **bắt buộc** `site_api.PERMISSION_DOCTYPES` — việc INT-1 (mục 4). Nếu lúc build U0 nhánh nền đã có `site_api.PERMISSION_DOCTYPES`, U0 dùng ngay tên này và INT-1 chỉ còn bước kiểm.
> - Không dùng `site_api.always_denied_doctypes()` (tập của chế độ Toàn quyền, đã nằm trong `read.denied_doctypes()`) hay `site_api._denied_doctypes(ctx)` (hàm riêng).
>
> `FORBIDDEN_ROLES` cho `check_user_templates` vẫn là `site_api.FORBIDDEN_ROLES` (tên trùng giữa hai nhánh).

**Thay test `design.md:634`** bằng hai dòng:
- `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py::TestCatalogRules::test_hard_ban_follows_denied_doctypes_source` — ca (a) DocType giả thêm vào `read.denied_doctypes` bằng patch → bị chặn; (b) `Custom Role` (chỉ có trong tập của `site_api`) → bị chặn với lý do `"DocType phân quyền"` hoặc lý do 1; (c) **từ INT-1:** `Role` → bị chặn với `"DocType phân quyền"`.
- `erp_ai/agent/test_hard_bans.py::TestHardBanReason` (mới): `::test_reasons_in_order` (DocType của module app → lý do 1; `Custom Role` → bị chặn; một DocType submittable có sẵn tìm bằng `frappe.get_all("DocType", {"is_submittable": 1, "istable": 0}, limit=1)` → `"chứng từ submit"`; `ToDo` → `None`), `::test_no_doctype_literal_in_module` (mọi hằng chuỗi trong AST của `hard_bans.py` không trùng tên DocType nào trên site), `::test_permission_doctypes_banned` (**từ INT-1:** mỗi tên trong `site_api.PERMISSION_DOCTYPES` → `"DocType phân quyền"` hoặc lý do 1).

**Điều kiện xong (sau INT-1):** `grep -c "DENIED_DOCTYPES" erp_ai/agent/hard_bans.py` = 0; hai test trên xanh có ca `Role`.

### F-4 — M5 cho `ERP AI KPI Week`, `ERP AI Review Month` có chủ và thời điểm (major 2, ADR-033 QĐ 8, ADR-023 QĐ 5)

**Thay câu "Kiểm M5 ... (arch-impact)." trong `design.md:87`** bằng:
> Kiểm M5 (`refuse_agent_write` của `erp_ai/agent/agent_write_guard.py`, FEAT-004 T65) cho `ERP AI KPI Week` và `ERP AI Review Month` thuộc U5a, là việc INT-2 (mục 4): nhánh nền lúc build U5a đã có `agent_write_guard.py` → làm ngay trong U5a; chưa có → làm trong lần merge `develop` (đã có `team/FEAT-004`) vào `team/FEAT-007`. `team/FEAT-007` không được merge vào `develop` trước khi INT-2 xong.

**Thêm vào cuối `design.md:270`** (quyền `ERP AI KPI Week`): "Controller gọi `refuse_agent_write(self)` là dòng đầu của `before_insert`, `validate`, `on_trash`, `before_rename(self, old, new, merge=False)` (mẫu `erp_ai_log.py` của `team/FEAT-004`; INT-2)."

**Thêm vào cuối `design.md:272`** (quyền `ERP AI Review Month`): "Controller gọi `refuse_agent_write(self)` là dòng đầu của `before_insert`, `validate` (trước kiểm khóa danh sách phiếu 3.6.5), `on_trash`, `before_rename` (INT-2). `ERP AI Review Item` được che theo cha (bảng con chỉ ghi qua cha)."

**Thay dòng `design.md:519`** bằng:
> | Tạo KPI Week, Review Month; ghi kết luận rà soát | job (phiên scheduler) tạo; người rà (phiên người) ghi kết luận | không DocPerm `create` cho role nào; M5: `refuse_agent_write` ở 4 hook của hai DocType (INT-2), `ERP AI Review Item` theo cha (ADR-033 QĐ 8, ADR-023 QĐ 5) |

Test: mục 6.2 (dòng "ADR-033 QĐ 8 / M5"). Không phiên agent nào của FEAT-007 cần ghi hai DocType này, nên không có `allow_agent_write()` mới (ADR-033 QĐ 8).

### F-5 — Phạm vi `erp_ai_log.json` ở U0 (phán quyết D-5)

**Thay dòng D-5 `design.md:63`** bằng:
> | D-5 | Trường mới của ERP AI Log | U0 sửa `erp_ai_log.json` chỉ phần "chỉ thêm": 5 cột (`created_labels`, `predicted_confidence_pct`, `split_requested`, `split_requests`, `site_environment`), `actions` → Long Text (D-6), DocPerm `ERP AI Instructor`. Option `entry_type`/`trigger` mới **không** ở U0: đi cùng commit đổi hằng (U3, U6b) | Architect chấp nhận có ràng buộc (`arch-review-design-w0.md:23-42`); lệch bảng file arch-impact đã được chấp nhận. |

**Thay dòng `design.md:238` và `:239`** (xóa khỏi bảng U0) bằng bảng phân đơn vị sau, đặt ngay dưới bảng 2.3:

| Option Select của ERP AI Log | Đơn vị | Cùng một commit với |
|---|---|---|
| `entry_type` thêm `bot_action` | U3 | `run_log.ENTRY_TYPES`, `ENTRY_TYPES_EXPECTED` và `test_entry_types_unchanged` trong `test_architecture.py` (căn cứ sửa ghim ADR-019 QĐ 7: ADR-033 QĐ 5), cụm từ `DOCTYPE_CONFIG["ERP AI Log"]` của `entry_type` |
| `trigger` thêm `setting_save`, `scheduled_job` | U3 | hằng trigger của `run_log.py` (`run_log.TRIGGERS` hoặc tập trigger của dòng `bot_action` nếu U3 tách), cụm từ của `trigger` |
| `trigger` thêm `requester_reply`, `kb_draft` | U6b | `run_log.TRIGGERS`, `queue.VALID_TRIGGERS`, cụm từ của `trigger` |

Ràng buộc kiểm được: option `entry_type`/`trigger` trong `erp_ai_log.json` chỉ đổi trong commit có đổi `erp_ai/agent/run_log.py` (và `erp_ai/agent/queue.py` cho trigger của runner) — reviewer của U3, U6b kiểm bằng diff của commit; ở U0, `test_entry_types_unchanged` hiện có phải xanh (mục 6.1).

**Thay dòng `design.md:241`** bằng:
> | Quyền: thêm DocPerm `ERP AI Instructor` **đúng** `read=1`, `report=1`; `create`, `write`, `delete`, `export`, `print`, `email`, `share`, `submit`, `cancel`, `amend` = 0 | DocPerm | — | ba báo cáo trên ERP AI Log | AC-20, ADR-034 QĐ 8 (Hệ quả "Instructor cần `report` trên `ref_doctype`"); append-only của ADR-004/ADR-024 giữ nguyên |

**Thay `design.md:243`** bằng:
> `DOCTYPE_CONFIG["ERP AI Log"]["field_count"]` = số thật trên nhánh nền + 5 (trên `develop` @ `1918db2`: 38 → 43); cụm từ mới chỉ cho 5 trường mới. Ở đợt 0 `run_log.ENTRY_TYPES`, các tập trigger và option `entry_type`/`trigger` **đều không đổi**; chưa dòng nào mang giá trị mới.

**Thay ghi chú dòng touchpoint `design.md:554`**: cột "Phạm vi arch-impact" = `"có — phán quyết D-5 của architect"`; ghi chú `"2.3: 5 cột, actions Long Text, DocPerm Instructor; không đổi option"`. Thêm touchpoint `erp_ai/erp_ai_agent/doctype/erp_ai_log/test_erp_ai_log.py` (sửa). Danh sách đầy đủ: mục 5.1.

**Test (mục 6.1):** `test_erp_ai_log.py::TestERPAILog::test_no_role_can_write_or_delete` đổi tập role thành {System Manager, ERP AI Agent, ERP AI Instructor} và khẳng định Instructor chỉ có `read`, `report`; khẳng định của System Manager, ERP AI Agent giữ nguyên. Lý do (NFR-8, STD-TEST-5): AC-20 đổi quyền; ghi ở commit và `acceptance.md`.

**Ghi cho As-Built (writer):** người có `ERP AI Instructor` (COO, người rà soát) xem được mọi dòng ERP AI Log trên Desk (Report View), gồm `reasoning`, `error`, giá trị trước/sau đã bỏ trường mật.

**Thứ tự merge:** phần U0 của `erp_ai_log.json` không xung đột chữ (trùng byte giữa `develop` và `team/FEAT-004`; không task mở nào của FEAT-004/FEAT-005 sửa). `test_doctype_descriptions.py` đụng FEAT-005 T7 ở khóa `ERP AI Setting` → gộp tay khi merge. Phần chuyển sang U3 đi theo thứ tự của U3 (sau FEAT-004 T68 và FEAT-005 T14, cùng sửa `test_architecture.py`).

### F-6 — `actions` Small Text → Long Text ở U0 (phán quyết D-6)

**Thay dòng D-6 `design.md:64`** bằng:
> | D-6 | Kiểu trường `actions` (ADR-024 Bối cảnh, ADR-033 Hệ quả) | Small Text → Long Text ở U0; chỉ đổi `fieldtype` | Architect chấp nhận (`arch-review-design-w0.md:44-54`): DDL nới một chiều, không mất dữ liệu, không đổi mã đọc/ghi; T64 chỉ tạo ra kích thước, không sửa JSON, nên không cần chủ T64 xác nhận. |

**Thay dòng `design.md:240`** bằng:
> | `actions` Small Text → **Long Text** | Long Text | như cũ: `run_log.write_entry`, `insert` + `commit` trong cùng lời gọi, không cắt, không thêm giới hạn kích thước | như cũ | D-6; chỉ đổi `fieldtype` — không đổi tên, vị trí trong `field_order`, `read_only`, hình dạng list JSON của mục (ADR-033 QĐ 5, ADR-024 QĐ 1). Ảnh chụp đầy đủ vẫn ở `value_before`/`value_after` (FEAT-005 design-amd2 D-3); Long Text không mở đường gộp vào `actions` |

**`design.md:529` (chiều xuống của `actions`) giữ nguyên chữ**; thêm câu: "Bước kiểm `max(length(actions)) ≤ 65535` và nhánh 'vượt thì giữ Long Text' được ghi vào kế hoạch rollback của As-Built (STD-OPS-1, STD-OPS-2)."

**Test U0 mới** (mục 6.1): `test_erp_ai_log.py::TestActionsLongText::test_write_entry_actions_over_65535_bytes_round_trips` (`run_log.write_entry(entry_type="reason", trigger="ticket_insert", actions=[...])` với mục chứa chữ tiếng Việt nhiều byte, `len(json.dumps(actions, ensure_ascii=False).encode("utf-8")) > 65535`; ghi được; `frappe.db.get_value(LOG_DOCTYPE, name, "actions")` trùng chuỗi đã ghi), `::test_actions_fieldtype_long_text` (`frappe.get_meta(LOG_DOCTYPE).get_field("actions").fieldtype == "Long Text"`), `::test_actions_column_is_longtext` (`information_schema.columns.data_type` của cột `actions` trong `tabERP AI Log` = `longtext`, bằng chứng migrate đã chạy).

**Đưa sớm (tùy team-leader, kiến trúc cho phép):** thay đổi một dòng `fieldtype` cùng ba test trên có thể vào `develop` sớm hơn dưới dạng commit độc lập; nếu không, cửa sổ rủi ro tràn 64 KB chỉ ở site dev, đóng khi đợt 0 merge, trước G5.

### F-7 — Tên test khớp hành vi email 08:00 (minor)

`design.md:444, 455` giữ nguyên (email liệt kê `"#<mã> (nhóm loại trừ)"`, không tiêu đề, không nội dung — AC-52 cho phép số đếm và số phiếu; A-D5). **Thay tên test ở `design.md:677`**: `test_daily_report.py::TestRun::test_excluded_ticket_counts_only` → `::test_excluded_ticket_number_only_no_subject` (khẳng định: mã phiếu có trong email; tiêu đề/nội dung có chuỗi gieo xuất hiện 0 lần).

## 3. Tên chuyển chỗ (đối chiếu với addendum đợt 1)

| Tên | Đường dẫn cũ (`design.md`) | Đường dẫn mới |
|---|---|---|
| `KPI_IDS` | `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py` | `erp_ai/constants.py` |
| `TICKET_CONTENT_DOCTYPES` | `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py` | `erp_ai/constants.py` |
| `ACTION_CREATE_USER`, `ACTION_ADD_TEAM_MEMBER`, `ACTION_ADD_HOLIDAY`, `ACTION_SET_ITEM_GROUP`, `ACTION_CREATE_CUSTOM_FIELD`, `ACTION_UPDATE_FIELDS` | `erp_ai/erp_ai_agent/doctype/erp_ai_catalog_rule/erp_ai_catalog_rule.py` | `erp_ai/constants.py` |
| `MODE_DENY`, `MODE_NEEDS_APPROVAL`, `MODE_AUTO` | `erp_ai/erp_ai_agent/doctype/erp_ai_catalog_rule/erp_ai_catalog_rule.py` | `erp_ai/constants.py` |
| `hard_ban_reason` | `erp_ai/erp_ai_agent/doctype/erp_ai_catalog_rule/erp_ai_catalog_rule.py` | `erp_ai/agent/hard_bans.py` |
| ba lời `frappe.enqueue` của job theo lịch | `erp_ai/schedules.py` (`enqueue_daily_report`, `enqueue_weekly_kpi`, `enqueue_monthly_review`) | `erp_ai/agent/queue.py` (`enqueue_daily_report_job`, `enqueue_weekly_kpi_job`, `enqueue_monthly_review_job`); ba hàm của `schedules.py` giữ tên, chỉ gọi chúng |
| `LONG_JOB_TIMEOUT_S` (1200) | `erp_ai/schedules.py` | `erp_ai/agent/queue.py`, **đổi tên** `SCHEDULED_JOB_TIMEOUT_S` |
| option `entry_type` `bot_action` | U0 (`erp_ai_log.json`) | U3 (cùng file) |
| option `trigger` `setting_save`, `scheduled_job` | U0 | U3 |
| option `trigger` `requester_reply`, `kb_draft` | U0 | U6b |

Tên **mới** (không chuyển): `CATALOG_ACTIONS`, `CATALOG_MODES` (`erp_ai/constants.py`); 3 chuỗi thêm vào `ENQUEUE_TARGETS` (`erp_ai/tests/test_architecture.py`). Giá trị `job_id` (`erp_ai::daily_report`, `erp_ai::weekly_kpi`, `erp_ai::monthly_review`) và đường dẫn hàm `cron` trong `hooks.py` không đổi.

Tên **ở lại** (không chuyển, chỉ controller/report/test dùng): `PROMPT_REQUIRED_MARKERS`, `PROMPT_OVERRIDE_MAX_CHARS`, `INT_LIMITS` (`erp_ai_setting.py`); `l0_l1_gate`, `GateResult`, `GATE_WINDOW_DAYS`, `GATE_MIN_SAMPLE`, `GATE_MIN_ACCURACY` (`erp_ai/erp_ai_agent/report/erp_ai_accuracy/erp_ai_accuracy.py`); `BA_NOTE_MARKER` (`erp_ai/agent/ops_data.py`, vốn đã ở Lõi). Addendum đợt 1 dùng tên nào trong nhóm controller/report từ một module `erp_ai/agent/**` → phải chuyển trước (F-1, thay `design.md:338`).

## 4. Việc hòa nhập sau FEAT-004 (có chủ, có thời điểm)

Điều kiện chung: `team/FEAT-004` đã vào `develop`, rồi `develop` được merge vào `team/FEAT-007`. Tech-lead đặt mỗi việc thành một task của plan (designer không đánh số task). Nếu lúc build đơn vị chủ, nhánh nền đã có tên/file cần dùng, việc làm luôn trong đơn vị đó và ở đây chỉ còn bước kiểm.

| Việc | Đơn vị chủ | Touchpoint | Điều kiện xong (kiểm có đầu ra) |
|---|---|---|---|
| INT-1 — `hard_ban_reason` trỏ `site_api.PERMISSION_DOCTYPES` (F-3) | U0 | `erp_ai/agent/hard_bans.py`, `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py`, `erp_ai/agent/test_hard_bans.py` | `grep -c "DENIED_DOCTYPES" erp_ai/agent/hard_bans.py` = 0; `test_hard_ban_follows_denied_doctypes_source` (có ca `Role`), `test_permission_doctypes_banned` xanh qua `cmd.test_one` |
| INT-2 — M5 trên `ERP AI KPI Week`, `ERP AI Review Month` (F-4) | U5a | `erp_ai/erp_ai_agent/doctype/erp_ai_kpi_week/erp_ai_kpi_week.py`, `erp_ai/erp_ai_agent/doctype/erp_ai_review_month/erp_ai_review_month.py`, `.../erp_ai_kpi_week/test_erp_ai_kpi_week.py`, `.../erp_ai_review_month/test_erp_ai_review_month.py` | `grep -c "refuse_agent_write(self)"` = 4 ở mỗi controller; test M5 mục 6.2 xanh qua `cmd.test_one` |

Nhắc gộp tay ở cùng lần merge (không phải việc mới): `erp_ai_setting.py` (T65 thêm `refuse_agent_write` — giữ là dòng đầu của `validate`, trước bước 1 của 3.1), `test_architecture.py` (F-2), `test_doctype_descriptions.py` (FEAT-005 T7).

**Cửa merge:** `team/FEAT-007` không vào `develop` khi INT-1 hoặc INT-2 chưa đạt điều kiện xong, hoặc `cmd.test` trên nhánh đã gộp chưa xanh. Nếu T59 không còn công khai tập phân quyền dưới tên nào khi FEAT-004 vào `develop` → dừng, báo team-leader (`DESIGN_CONFLICT` với ADR-031 Ràng buộc), không giữ `DENIED_DOCTYPES`.

## 5. Touchpoints đợt 0 sau sửa

### 5.1 U0 (thay toàn bộ bảng `design.md:545-558`)

| file | change | Phạm vi arch-impact | ghi chú |
|---|---|---|---|
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json` | sửa | có | 49 trường, 7 section, chuyển 2 công tắc, mô tả `permission_level`, `code_change_enabled`, `unrestricted_enabled` |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py` | sửa | có | 3.1; import hằng từ `erp_ai.constants`, `hard_ban_reason` từ `erp_ai.agent.hard_bans` (F-1) |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.js` | sửa | có | khóa thêm/xóa dòng `prompt_revisions` |
| `erp_ai/erp_ai_agent/doctype/erp_ai_catalog_rule/{__init__.py, erp_ai_catalog_rule.json, erp_ai_catalog_rule.py}` | mới | có (DocType con) | `.py` = lớp `Document` rỗng; option `action`/`mode` theo `CATALOG_ACTIONS`/`CATALOG_MODES` |
| `erp_ai/erp_ai_agent/doctype/erp_ai_user_template/{__init__.py, .json, .py}` | mới | có | |
| `erp_ai/erp_ai_agent/doctype/erp_ai_prompt_revision/{__init__.py, .json, .py}` | mới | có | |
| `erp_ai/constants.py` | sửa | không — F-1 (blocker 1) | khối hằng FEAT-007 cuối file |
| `erp_ai/agent/hard_bans.py` | mới | không — F-1, F-3 | `hard_ban_reason`; INT-1 |
| `erp_ai/install.py` | sửa | có | 3.2 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json` | sửa | có — phán quyết D-5 | 5 cột, `actions` Long Text, DocPerm Instructor; không đổi option |
| `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py` | sửa | test | INT-1 thêm ca `Role` |
| `erp_ai/agent/test_hard_bans.py` | mới | test | F-3 |
| `erp_ai/erp_ai_agent/doctype/erp_ai_log/test_erp_ai_log.py` | sửa | test | F-5, F-6 |
| `erp_ai/tests/test_install.py` | sửa | test | migrate lên/xuống |
| `erp_ai/tests/test_doctype_descriptions.py` | sửa | test | `DOCTYPE_CONFIG` Setting, Log (+5), 3 bảng con |
| `erp_ai/test_utils.py` | sửa | test hỗ trợ | `keep_agent_settings(testcase)` (NFR-7) |

### 5.2 U5a (thay toàn bộ bảng `design.md:574-583`)

| file | change | Phạm vi | ghi chú |
|---|---|---|---|
| `erp_ai/schedules.py` | mới | có (Cửa vào lịch) | 3.6.1 sau F-2: chỉ gọi `queue.*_job`, không `enqueue` |
| `erp_ai/agent/queue.py` | sửa | có — F-2 (blocker 2) | `SCHEDULED_JOB_TIMEOUT_S`, 3 hàm `*_job` |
| `erp_ai/agent/ops_data.py`, `daily_report.py`, `kpi.py`, `monthly_review.py` | mới | có (file việc theo lịch) | 3.6.2–3.6.5; `kpi.py` import `KPI_IDS` từ `erp_ai.constants` |
| `erp_ai/hooks.py` | sửa | có | 3 dòng `cron` (đường dẫn không đổi) |
| `erp_ai/erp_ai_agent/doctype/erp_ai_kpi_week/{__init__.py, .json, .py}` | mới | có | `autoname`; M5 4 hook (INT-2) |
| `erp_ai/erp_ai_agent/doctype/erp_ai_review_month/{__init__.py, .json, .py}`, `erp_ai/erp_ai_agent/doctype/erp_ai_review_item/{__init__.py, .json, .py}` | mới | có | `validate` khóa danh sách; M5 4 hook ở Review Month (INT-2); Item theo cha |
| `erp_ai/erp_ai_agent/report/erp_ai_kpi_weekly/{__init__.py, .json, .py}`, `erp_ai/erp_ai_agent/report/erp_ai_cost/{__init__.py, .json, .py}` | mới | có | KPI Weekly import `KPI_IDS` từ `erp_ai.constants` |
| `erp_ai/tests/test_architecture.py` | sửa | có — F-2 | `ENQUEUE_TARGETS` +3, chữ lỗi, 2 test ghim; gộp tay với FEAT-004/FEAT-005 |
| `erp_ai/agent/test_queue.py` | sửa | test | F-2 |
| `erp_ai/agent/test_daily_report.py`, `test_kpi.py`, `test_monthly_review.py`, `test_ops_data.py` | mới | test | |
| `erp_ai/tests/test_schedules.py` | mới | test | |
| `erp_ai/erp_ai_agent/doctype/erp_ai_kpi_week/test_erp_ai_kpi_week.py` | mới | test | M5 (INT-2) |
| `erp_ai/erp_ai_agent/doctype/erp_ai_review_month/test_erp_ai_review_month.py` | mới | test | + M5 (INT-2) |
| `erp_ai/erp_ai_agent/report/erp_ai_kpi_weekly/test_erp_ai_kpi_weekly.py`, `erp_ai/erp_ai_agent/report/erp_ai_cost/test_erp_ai_cost.py` | mới | test | |
| `erp_ai/tests/test_doctype_descriptions.py` | sửa | test | 3 DocType mới (nếu luật mô tả áp cho mọi DocType của module) |

### 5.3 U4a, U6a

Không đổi so với `design.md:560-570, 585-593`. U4a vẫn xếp hàng qua `queue.enqueue_agent_run` (hợp lệ); `missed_scan.py`, `knowledge.py`, `system_read.py`, `article_guard.py`, `redact.py` không import gì từ `erp_ai.erp_ai_agent`.

### 5.4 So khớp đường dẫn mới do file này thêm

`structure.allowed_new_file_roots` = `["erp_ai", "docs", ".github"]`:
```
erp_ai/agent/hard_bans.py                                              -> erp_ai  OK
erp_ai/agent/test_hard_bans.py                                         -> erp_ai  OK
erp_ai/erp_ai_agent/doctype/erp_ai_kpi_week/test_erp_ai_kpi_week.py    -> erp_ai  OK
docs/team/features/FEAT-007/design-w0-fixes.md                         -> docs    OK
```
`protected_paths` = `[".env", ".env.*", "**/*.pem", "**/*.key", "license.txt"]`: không đường dẫn nào ở trên (và ở 5.1, 5.2) có tên `.env*`, đuôi `.pem`/`.key` hay là `license.txt` → 0 trùng.

## 6. Test plan đợt 0 sau sửa

Quy ước như `design.md:612` (chạy bằng `cmd.test_one` theo file, `cmd.test` trước merge; `keep_agent_settings(self)`; truyền `now`; không skip).

### 6.1 U0 (thay toàn bộ bảng `design.md:616-648`)

| Tiêu chí | Test | Loại |
|---|---|---|
| AC-1 (cài mới: 5 công tắc tắt) | `erp_ai/tests/test_install.py::TestFeat007Migrate::test_fresh_install_five_switches_off` | integration |
| AC-1 (migrate: (1), (4) giữ; (2), (3), (5) = 0 khi (4) bật) | `test_install.py::TestFeat007Migrate::test_migrate_keeps_old_switches_new_switches_off` | integration |
| AC-1 (migrate lần hai không đổi) | `test_install.py::TestFeat007Migrate::test_second_migrate_changes_nothing` | integration |
| STD-OPS-2 (xuống: dòng thừa vô hại) | `test_install.py::TestFeat007Migrate::test_leftover_single_rows_dropped_on_next_human_save`; `::test_orphan_child_rows_do_not_break_get_single` | integration |
| STD-OPS-2 (lên/xuống thật trên site dev) | Kiểm có đầu ra: `design.md` mục 6 "Đối soát" (a)–(d), gồm bước `max(length(actions))` của chiều xuống, dán vào `acceptance.md` | manual + lệnh |
| NFR-4 (mặc định an toàn) | `erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py::TestFeat007Defaults::test_every_new_field_default` | unit |
| AC-4 (thông báo khi bật; mỗi ô một ca) | `test_erp_ai_setting.py::TestPermissionSwitchNotice::test_each_switch_on_shows_name_consequence_environment` | unit |
| AC-4 (không đổi / tắt → không thông báo) | `::test_save_without_switch_change_no_notice`, `::test_switch_off_no_notice` | unit |
| AC-4 (Toàn quyền có câu gọi hàm tự do) | `::test_unrestricted_notice_has_call_method_caveat` | unit |
| AC-12 | `TestFeat007Defaults::test_site_environment_default_production_and_options` | unit |
| AC-18 (cảnh báo nâng mức) | `test_erp_ai_setting.py::TestLevelRaiseWarning::test_raise_from_l0_not_passed_warns_and_saves`, `::test_raise_from_l0_passed_no_warning`, `::test_change_l1_to_l2_no_gate_warning` | unit |
| AC-22, AC-36 (biên) | `TestFeat007Limits::test_int_limits_edges` | unit |
| AC-24 | `test_erp_ai_setting.py::TestTicketFieldNames::test_unknown_field_blocked`, `::test_due_field_must_be_date`, `::test_board_value_needs_origin_field`, `::test_existing_custom_field_saves` | integration |
| AC-26 (mốc phản hồi mặc định) | `TestFeat007Defaults::test_response_targets_reuse_routing_rules` | unit |
| AC-29 (4 dòng cấm bị chặn) | `test_erp_ai_setting.py::TestCatalogRules::test_four_hard_bans_blocked` | integration |
| AC-29 (hình dạng dòng; dòng hợp lệ lưu được) | `TestCatalogRules::test_row_shape_rules`, `::test_valid_rule_saves_and_categories_normalized` | unit |
| AC-29 (option Select = hằng, một nguồn) | `TestCatalogRules::test_select_options_match_constants` (option `action`, `mode` của JSON = `CATALOG_ACTIONS`, `CATALOG_MODES`) | unit |
| AC-29, ADR-031 (điều cấm cứng một nguồn; F-3) | `TestCatalogRules::test_hard_ban_follows_denied_doctypes_source` (ca a, b; ca c `Role` từ INT-1) | unit |
| ADR-031 Ràng buộc (`hard_ban_reason`: thứ tự lý do; không tên DocType viết tay; tập phân quyền của T59) | `erp_ai/agent/test_hard_bans.py::TestHardBanReason::test_reasons_in_order`, `::test_no_doctype_literal_in_module`, `::test_permission_doctypes_banned` (từ INT-1) | unit / integration |
| ADR-001 (Lõi không import controller; F-1) | `erp_ai/tests/test_architecture.py::TestArchitecture::test_layer_imports` (hiện có, phải xanh trên nhánh có U0) | unit |
| AC-30 | `test_erp_ai_setting.py::TestUserTemplates::test_forbidden_role_blocked`, `::test_unknown_role_and_duplicate_name_blocked`, `::test_valid_template_saves` | unit |
| AC-31 | `TestFeat007Defaults::test_level_caps_default` | unit |
| AC-38 (thiếu mục, quá dài) | `test_erp_ai_setting.py::TestPromptOverrides::test_missing_marker_blocked_each_part`, `::test_too_long_blocked` | unit |
| AC-38 (bản dựng sẵn qua kiểm) | `TestPromptOverrides::test_builtin_prompts_pass_required_markers` | unit |
| AC-38 (lịch sử) | `TestPromptOverrides::test_revision_row_on_change`, `::test_no_revision_without_change`, `::test_revisions_restored_on_save` | integration |
| AC-44, AC-46, AC-63 | `TestFeat007Defaults::test_every_new_field_default` | unit |
| AC-47 | `test_erp_ai_setting.py::TestManualsDir::test_missing_or_outside_dir_blocked`, `::test_existing_dir_saves` | unit |
| AC-49 (báo cáo; `TICKET_CONTENT_DOCTYPES` từ `constants`) | `test_erp_ai_setting.py::TestAllowedReports::test_unknown_type_disabled_ticket_based_blocked`, `::test_log_based_report_blocked`, `::test_safe_report_saves` | integration |
| AC-51, AC-59, AC-27 | `test_erp_ai_setting.py::TestOperationPeople::test_bad_email_blocked`, `::test_disabled_reviewer_blocked`, `::test_watcher_must_be_enabled_human` | unit |
| AC-55 (`KPI_IDS` từ `constants`) | `test_erp_ai_setting.py::TestKpiTargets::test_bad_targets_blocked`, `::test_default_targets_valid` | unit |
| ADR-033 QĐ 6 | `test_erp_ai_setting.py::TestSelfManagedFeat007::test_watermarks_restored_on_human_save`, `::test_agent_enabled_at_stamped_on_enable_only` | integration |
| AC-20 (Instructor có `report` trên ERP AI Log) | `erp_ai/tests/test_install.py::TestFeat007Migrate::test_instructor_can_report_on_log` | integration |
| AC-20, D-5 (DocPerm Log: đúng 3 role; Instructor chỉ `read`, `report`) | `erp_ai/erp_ai_agent/doctype/erp_ai_log/test_erp_ai_log.py::TestERPAILog::test_no_role_can_write_or_delete` (sửa, NFR-8) | integration |
| D-5 (U0 không đổi `entry_type`) | `erp_ai/tests/test_architecture.py::TestArchitecture::test_entry_types_unchanged` (hiện có, phải xanh, không sửa ở U0) | unit |
| D-6 (`actions` > 65 535 byte ghi và đọc lại trùng) | `test_erp_ai_log.py::TestActionsLongText::test_write_entry_actions_over_65535_bytes_round_trips` | integration |
| D-6 (meta Long Text; cột `longtext` sau migrate) | `test_erp_ai_log.py::TestActionsLongText::test_actions_fieldtype_long_text`, `::test_actions_column_is_longtext` | unit / integration |
| Mô tả ≤ 400 ký tự, cụm bắt buộc, section, `field_count` Log = nền + 5 | `erp_ai/tests/test_doctype_descriptions.py` (test hiện có, `DOCTYPE_CONFIG` mới) | unit |
| NFR-7 | `erp_ai/test_utils.py` dùng ở mọi lớp trên; `cmd.test` chạy hai lần liên tiếp cùng kết quả (kiểm có đầu ra ở verify) | lệnh |

### 6.2 U5a (thay toàn bộ bảng `design.md:673-690`)

| Tiêu chí | Test | Loại |
|---|---|---|
| AC-51 (12 phiếu → từng mục) | `erp_ai/agent/test_daily_report.py::TestBuild::test_twelve_tickets_sections` | integration |
| AC-51 (khai báo lịch 08:00, thứ Hai, ngày 1) | `erp_ai/tests/test_schedules.py::TestCron::test_cron_strings` | unit |
| AC-51, F-2 (mỗi hàm `cron` gọi đúng hàm `*_job` của `queue` một lần, không `enqueue` trực tiếp) | `test_schedules.py::TestCron::test_each_cron_calls_its_queue_function` (thay `test_enqueue_long_fixed_job_id`) | unit |
| ADR-003/ADR-013 QĐ 2, ADR-033 QĐ 6 (3 job: đích, `queue="long"`, `timeout=1200`, `enqueue_after_commit=True`, `job_id` cố định, `deduplicate=True`, không kwarg khác) | `erp_ai/agent/test_queue.py::TestEnqueueScheduledJobs::test_each_job_shape` (subTest ×3, chặn `frappe.enqueue`) | unit |
| ADR-003/ADR-013 (một chỗ enqueue; 5 đích ghim; mỗi đích một lời gọi đủ 5 tham số) | `erp_ai/tests/test_architecture.py::TestArchitecture::test_single_enqueue_call_site` (hiện có); `TestScannersCatchViolations::test_enqueue_targets_pinned` (sửa: 5 chuỗi), `::test_enqueue_call_shape_requires_one_call_per_target` (đổi tên từ `..._requires_exactly_two_calls`), `::test_enqueue_call_shape_accepts_runner_and_change_job` (hiện có) | unit |
| ADR-003 (runner, job áp dụng không đổi) | `test_queue.py::TestEnqueueAgentRun::test_runner_enqueue_unchanged`, `TestEnqueueChangeJob::test_enqueue_change_job_shape` (hiện có) | unit |
| AC-52 (người nhận rỗng; hai lần → 1 email; lỗi gửi → log, không ném; phiếu loại trừ chỉ mã phiếu; ngày trống số 0) | `test_daily_report.py::TestRun::test_no_recipients_logs_only`, `::test_twice_same_day_one_email`, `::test_send_error_logged_not_raised_watermark_kept`, `::test_excluded_ticket_number_only_no_subject` (F-7), `::test_empty_day_sends_zeros` | integration |
| AC-52 / ADR-033 (chu kỳ; cuối tuần tắt) | `erp_ai/agent/test_ops_data.py::TestCycles::test_daily_weekly_monthly_cycles`; `test_daily_report.py::TestRun::test_weekend_skipped_when_off` | unit |
| NFR-6 | `test_daily_report.py::TestRun::test_secret_in_subject_redacted` | integration |
| AC-53 | `erp_ai/agent/test_kpi.py::TestKpi::test_kpi1_median_and_rates`, `::test_kpi2_open_at_week_end`, `::test_kpi3_bot_only_closures`, `::test_zero_sample_none` | integration |
| AC-54 | `test_kpi.py::TestKpi::test_kpi4_b_resolution_hours`, `::test_kpi5_task_within_72h_edge`, `::test_kpi6_stale_edges` | integration |
| AC-55 | `test_kpi.py::TestRunWeekly::test_same_week_twice_one_row`, `::test_next_week_compares`, `::test_backfill_capped_at_eight` | integration |
| AC-56 | `erp_ai/erp_ai_agent/report/erp_ai_kpi_weekly/test_erp_ai_kpi_weekly.py::TestReport::test_six_rows_columns` | integration |
| AC-56, AC-20 | `test_erp_ai_kpi_weekly.py::TestReport::test_access_three_accounts` | integration |
| AC-56 (màn hình thật) | Kiểm có đầu ra: mở `/app/query-report/ERP AI KPI Weekly` bằng tài khoản chỉ có ERP AI Instructor, dán ảnh | manual |
| AC-59 | `erp_ai/agent/test_monthly_review.py::TestReview::test_25_gives_10_unique`, `::test_6_gives_6`, `::test_rerun_same_set`, `::test_excluded_absent`, `::test_no_reviewers_list_still_created` | integration |
| AC-59 (kết luận, khóa danh sách) | `erp_ai/erp_ai_agent/doctype/erp_ai_review_month/test_erp_ai_review_month.py::TestReviewMonth::test_verdict_sets_reviewer`, `::test_ticket_list_locked` | integration |
| ADR-033 QĐ 8 / M5 (INT-2: dưới tài khoản agent, kể cả khi tạm có System Manager như `test_agent_write_guard.py`, insert/save/delete/rename → `PermissionError`, DB không đổi) | `erp_ai/erp_ai_agent/doctype/erp_ai_kpi_week/test_erp_ai_kpi_week.py::TestKpiWeekAgentGuard::test_every_guarded_hook_refuses_agent`, `::test_agent_insert_save_delete_refused`; `test_erp_ai_review_month.py::TestReviewMonthAgentGuard::test_every_guarded_hook_refuses_agent`, `::test_agent_insert_save_delete_refused` | integration |
| ADR-033 QĐ 7, 8 (phiên scheduler vẫn tạo; người rà vẫn ghi kết luận) | `test_erp_ai_kpi_week.py::TestKpiWeekAgentGuard::test_scheduler_session_inserts`; `test_erp_ai_review_month.py::TestReviewMonthAgentGuard::test_scheduler_session_creates`, `::test_reviewer_session_writes_verdict` | integration |
| AC-60 | `erp_ai/erp_ai_agent/report/erp_ai_cost/test_erp_ai_cost.py::TestCost::test_per_ticket_and_run_totals`, `::test_month_total_matches_spent` | integration |
| AC-20 (ERP AI Cost) | `test_erp_ai_cost.py::TestCost::test_access_three_accounts` | integration |
| ADR-033 Ràng buộc (lỗi giữa chừng) | `test_kpi.py::TestRunWeekly::test_error_midway_no_row_then_once`; `test_monthly_review.py::TestReview::test_error_midway_no_row_then_once` | integration |

### 6.3 U4a, U6a

Không đổi so với `design.md:650-669, 692-705`. Dòng AC-26 của U4a trỏ `test_daily_report.py::TestBuild::test_twelve_tickets_sections` (tên không đổi).

### 6.4 Đối chiếu AC (Done criteria)

AC đợt 0 theo bảng đơn vị build (`arch-impact.md`), không đổi:
```
U0 : AC-1, AC-4 form, AC-12, AC-22, AC-24, AC-26, AC-29, AC-30, AC-31, AC-36, AC-38, AC-44, AC-46, AC-47, AC-49, AC-51, AC-55, AC-59, AC-63; migrate lên/xuống
U4a: AC-16, AC-17, AC-18, AC-19, AC-20, AC-25, AC-26, AC-27, AC-28
U5a: AC-51, AC-52, AC-53, AC-54, AC-55, AC-56, AC-59, AC-60
U6a: AC-45 (chặn), AC-46, AC-47, AC-50
```
AC có ít nhất một dòng test sau sửa:
```
U0 : AC-1, AC-4, AC-12, AC-18, AC-20, AC-22, AC-24, AC-26, AC-27, AC-29, AC-30, AC-31, AC-36, AC-38, AC-44, AC-46, AC-47, AC-49, AC-51, AC-55, AC-59, AC-63, NFR-4, NFR-7, STD-OPS-2 (+ ADR-001, ADR-031, D-5, D-6)
U4a: AC-16, AC-17, AC-18, AC-19, AC-20, AC-25, AC-26, AC-27, AC-28 (không đổi)
U5a: AC-20, AC-51, AC-52, AC-53, AC-54, AC-55, AC-56, AC-59, AC-60, NFR-6 (+ ADR-003/013/033 QĐ 6, ADR-033 QĐ 8 / M5)
U6a: AC-45, AC-46, AC-47, AC-50, NFR-6 (không đổi)
```
Không AC nào của bảng thiếu test; không dòng test nào bị bỏ, chỉ một dòng đổi tên (F-7) và một dòng thay (F-2, `test_enqueue_long_fixed_job_id`).

## 7. Assumptions decided by the team

- **A-D6** — Hằng thuần ở `erp_ai/constants.py`, không ở một module mới dưới `erp_ai/agent/` như chữ của gợi ý review. Vì: (a) đây là nơi hiện có của mọi hằng Select dùng chung giữa Lõi và controller (STD-STRUCT-3, STD-DESIGN-4), Lõi và controller đều đã import nó; (b) một module chung cho hằng và `hard_ban_reason` tạo vòng import với `policy` (`read.py:4`). Chiều phụ thuộc đúng như finding đòi: không còn Lõi → controller. Nếu architect muốn đặt dưới `agent/`, việc sửa chỉ là đổi đường dẫn trong bảng mục 3.
- **A-D7** — Hàm xếp hàng mới có hậu tố `_job` để không trùng tên với ba hàm `cron` của `schedules.py`; giá trị `job_id` giữ như `design.md:415`.
- **A-D8** — INT-1, INT-2 có điều kiện theo nội dung nhánh nền lúc build (đã có tên/file của FEAT-004 thì làm luôn), để không làm hai lần.
- Không có câu hỏi nghiệp vụ mới.
