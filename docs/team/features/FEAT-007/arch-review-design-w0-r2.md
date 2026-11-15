Feature: FEAT-007
Stage: architect
Author-agent: architect
Date: 2026-11-14
Approved-by:
<!-- Cổng: G2b không áp dụng cho FEAT-007 (team.py: chỉ G5). Để trống. -->

# Rà soát kiến trúc vòng 2 — design đợt 0 sau `design-w0-fixes.md` — FEAT-007

**Phán quyết: approve** — kèm hai ràng buộc C-1, C-2 (mục 4) mà tech-lead đưa thẳng vào task của plan; không cần thêm vòng designer, không cần quay lại architect.

Đầu vào: `design-w0-fixes.md` (376 dòng, thắng `design.md`), `arch-review-design-w0.md` (vòng 1), `design.md` ở các dòng bị thay, ADR-001, ADR-003, ADR-013, ADR-023, ADR-024, ADR-030..ADR-034. Căn cứ đọc trực tiếp trên `develop` @ `1918db2` (đích đã biết, không qua Explore), 2026-11-14:
- `erp_ai/constants.py`: 71 dòng, **0** dòng `import`/`from` → module lá. Đã được import bởi `agent/policy.py:9`, `agent/queue.py:3`, `agent/tools/*.py`, `gateway/*`, controller `erp_ai_change_proposal.py:9`, `install.py`, `tasks.py`.
- `agent/policy.py:1-9` chỉ import thư viện chuẩn, `frappe`, `erp_ai.constants`. `agent/tools/read.py:4` import `erp_ai.agent.policy`; `read.py:141` có `denied_doctypes()`.
- `test_architecture.py:69-113` `LAYER_RULES`: `erp_ai.agent` ↛ `erp_ai.erp_ai_agent`; `erp_ai.agent.tools` ↛ `gateway`, `runner`, `queue`, `changes`; `erp_ai.agent.policy` ↛ `erp_ai.agent.tools`. Không luật nào cấm `erp_ai.agent.<module>` → `erp_ai.agent.tools` hay `erp_ai.agent.tools` → `erp_ai.agent.<module khác>`.
- `test_architecture.py:548-574` `check_enqueue_call_shape`: trả lỗi đếm **sớm** khi `len(calls) != len(ENQUEUE_TARGETS)`, trước kiểm "first argument" và "each of". `:2347-2362` `test_enqueue_call_shape_requires_each_target_once` dựng thân 2 lời gọi, `test_enqueue_call_shape_rejects_target_outside_set` dựng thân 2 lời gọi; `:2364-2375` `..._requires_five_parameters_on_each_call` dựng đủ `len(ENQUEUE_TARGETS)` lời gọi.
- ADR-031 Ràng buộc (`ADR-031.md:45`); ADR-033 QĐ 6 (`ADR-033.md:30-34`), QĐ 8 (`:50`); ADR-034 QĐ 3 (`ADR-034.md:23`).

## 1. Rà soát (ba câu)

REVIEW: ok
Các fix gỡ cả hai blocker của vòng 1: không còn module nào dưới `erp_ai/agent/**` import `erp_ai.erp_ai_agent.*` (ADR-001, F-1) và ba lời `frappe.enqueue` của job theo lịch về `agent/queue.py` với đủ năm tham số, đích ghim, `job_id` cố định + `deduplicate` (ADR-003 Ràng buộc nới bởi ADR-013, ADR-033 QĐ 6, F-2), còn hai major có chủ, thời điểm và cửa merge kiểm được (ADR-031 Ràng buộc + ADR-023 QĐ 3 qua INT-1; ADR-033 QĐ 8 + ADR-023 QĐ 5 qua INT-2). Phán quyết D-5, D-6 được chép đủ bốn ràng buộc mỗi bên (ADR-033 QĐ 5, ADR-024 QĐ 1 và Ràng buộc, ADR-004) và A-D6 được chấp nhận vì `erp_ai/constants.py` là module lá mà mọi tầng đã import. Còn một lỗ ở phạm vi test của F-2 (hai scanner test hiện có đỏ khi `ENQUEUE_TARGETS` có 5 đích) và một lỗ kiểm của ADR-031 (`hard_bans.py` có thể nhập tập tên DocType viết tay từ `constants.py` mà test AST không thấy), cả hai siết bằng C-1, C-2 ở plan, không đổi thiết kế.

## 2. Từng finding của vòng 1

| # | Finding vòng 1 | Kết quả | Dòng `design-w0-fixes.md` |
|---|---|---|---|
| 1 | blocker STD-DESIGN-6 — Lõi import hằng/hàm từ controller (`design.md:198, 212, 307, 338`) | **Đã giải quyết bởi F-1.** Hằng → `erp_ai/constants.py`, `hard_ban_reason` → `erp_ai/agent/hard_bans.py`; controller, Lõi, report import từ hai chỗ này; luật "tên còn ở controller/report phải chuyển xuống trước khi Lõi dùng" chặn tái phát ở đợt 1. | 42 (quyết định), 45, 48, 55, 58 (thay `:338`, gồm `policy` ↛ `hard_bans`), 62-66 (khối hằng), 186-201 (bảng tên chuyển chỗ), 223, 228-229 (touchpoint), 301 (test `test_layer_imports`) |
| 2 | blocker STD-DESIGN-2 — `frappe.enqueue` trong `erp_ai/schedules.py` (`design.md:415, 576`) | **Đã giải quyết bởi F-2** về mã: `schedules.py` chỉ gọi `queue.*_job`, `queue.py` không import module job, `ENQUEUE_TARGETS` +3. **Phạm vi test chưa đủ** → C-1 (mục 4). | 70-86 (3.6.1 mới), 88-91 (luồng 4, timeout), 95 (gộp tay), 193-194, 243-244, 250-251, 327-329 |
| 3 | major STD-DESIGN-2 — `hard_ban_reason` dùng `site_api.DENIED_DOCTYPES` (`design.md:223`) | **Đã giải quyết bởi F-3 + INT-1.** Thứ tự lý do, `PERMISSION_SET` theo nhánh nền, bắt buộc `site_api.PERMISSION_DOCTYPES` sau merge FEAT-004, cấm `_denied_doctypes(ctx)`, điều kiện grep = 0, ca `Role`, dừng `DESIGN_CONFLICT` nếu T59 không công khai tập. Siết thêm C-2. | 99-115, 118-119 (ca `Role`), 121 (grep), 209 (INT-1), 214 (cửa merge) |
| 4 | major STD-DESIGN-2 — M5 của `ERP AI KPI Week`, `ERP AI Review Month` không có chủ (`design.md:87, 519`) | **Đã giải quyết bởi F-4 + INT-2.** Chủ U5a, 4 hook là dòng đầu, Item theo cha, không `allow_agent_write()` mới (ADR-033 QĐ 8), test dưới tài khoản agent và phiên scheduler/người, cửa merge. | 126, 128, 130, 133, 135, 210, 214, 342-343 |
| 5 | minor — tên test email 08:00 | **Đã giải quyết bởi F-7.** | 182, 331 |
| D-5 | Ràng buộc 1-4 của phán quyết D-5 | **Đã giải quyết bởi F-5.** RB 1 (option chỉ đổi cùng commit `run_log.py`/`queue.py`): 144-150; RB 2 (test Instructor chỉ `read`, `report`): 153, 160, 314; RB 3 (`field_count` + 5): 156; RB 4 (As-Built): 162. `test_entry_types_unchanged` xanh, không sửa ở U0: 315. | 139-164 |
| D-6 | Ràng buộc 1-4 của phán quyết D-6 | **Đã giải quyết bởi F-6.** RB 1, 2 (chỉ đổi `fieldtype`, không cắt, ảnh chụp đầy đủ ở `value_before`/`value_after`): 172; RB 3 (test > 65 535 byte, meta, cột `longtext`): 176, 316-317; RB 4 (chiều xuống vào rollback As-Built): 174, 286. | 166-178 |

## 3. Phán quyết A-D6 (hằng ở `erp_ai/constants.py`, không ở module mới dưới `erp_ai/agent/`)

**Chấp nhận.** Gợi ý vòng 1 ("một module dưới `erp_ai/agent/`") là phương tiện; đích của finding là chiều phụ thuộc Cửa vào → Lõi, không Lõi → controller (ADR-001). `constants.py` đạt đích đó tốt hơn:
- Là module lá (0 dòng import), đã được `policy`, `queue`, `tools/*`, `gateway`, controller và `install` import → không sinh cạnh phụ thuộc mới nào, không vòng (STD-DESIGN-6), không tạo nơi thứ hai cho cùng loại hằng (STD-STRUCT-3, STD-DESIGN-4).
- Vòng import designer nêu là có thật: `policy` (U7 đọc `MODE_*`) → module chung → `tools.read` → `read.py:4` → `policy`; đồng thời làm `policy` phụ thuộc bắc cầu vào `erp_ai.agent.tools`, trái hướng luật `erp_ai.agent.policy` ↛ `erp_ai.agent.tools` (`test_architecture.py:109-113`). Tách hằng thuần (lá) khỏi hàm có I/O (`hard_bans.py`, dưới `agent/`) là cách đúng.
- `hard_bans.py` dưới `erp_ai/agent/` import `tools.read`, `tools.site_api`: chiều Lõi → tools, hợp lệ; bộ thực thi U7 dưới `agent/tools/` import `erp_ai.agent.hard_bans`: không luật nào cấm, không vòng vì `read`, `site_api` không import `hard_bans`.

Ràng buộc kèm phán quyết (kiểm được):
1. `erp_ai/constants.py` giữ là module lá: khối FEAT-007 không thêm dòng `import`/`from` nào (grep `^import\|^from` trong file = 0 sau U0).
2. `erp_ai/agent/policy.py` không import `erp_ai.agent.hard_bans` (đã ghi ở dòng 58); `policy` đọc `MODE_*`, `CATALOG_*` chỉ từ `erp_ai.constants`.

## 4. Chỗ mới phá ADR do fix gây ra, và ràng buộc siết

| severity | STD | file:line | mô tả | sửa |
|---|---|---|---|---|
| major | STD-TEST-5 | docs/team/features/FEAT-007/design-w0-fixes.md:83-86, 329 | F-2 ghi "sửa đúng ba chỗ" của `test_architecture.py` và coi các scanner test khác là "hiện có". Với 5 đích, `check_enqueue_call_shape` trả lỗi đếm sớm (`test_architecture.py:554-555`), nên `test_enqueue_call_shape_requires_each_target_once` (thân 2 lời gọi, chờ "each of") và `test_enqueue_call_shape_rejects_target_outside_set` (thân 2 lời gọi, chờ "first argument") đỏ ở U5a; dev phải sửa test ngoài phạm vi đã ghi, không có lý do ghi sẵn. Đây là công cụ kiểm của ADR-003/ADR-013 Ràng buộc | **C-1** (plan, task U5a có `test_architecture.py`): sửa thêm hai test đó để thân luôn có đúng `len(ENQUEUE_TARGETS)` lời gọi — `requires_each_target_once`: thay một đích bằng bản trùng của đích khác, vẫn khẳng định "each of", không "first argument"; `rejects_target_outside_set`: thay một đích bằng đích lạ/không phải hằng chuỗi, vẫn khẳng định "first argument". Không nới `check_enqueue_call_shape` ngoài đổi chữ lỗi ở dòng 85. Lý do sửa ghi trong commit: ADR-033 QĐ 6 (STD-TEST-5). Điều kiện xong: `cmd.test_one` của `erp_ai/tests/test_architecture.py` xanh, lớp `TestScannersCatchViolations` không mất ca nào |
| major | STD-DESIGN-2 | docs/team/features/FEAT-007/design-w0-fixes.md:103, 119 | ADR-031 Ràng buộc cấm tập tên DocType viết tay trong module danh mục. `test_no_doctype_literal_in_module` chỉ quét chuỗi trong AST của `hard_bans.py`; sau F-1, `constants.py` chứa cả hằng danh mục lẫn tập tên DocType (`TICKET_CONTENT_DOCTYPES`, `*_DOCTYPE`), nên một task sau (U7) có thể thêm tập cấm viết tay vào `constants.py` và `hard_bans.py` import nó mà test vẫn xanh | **C-2** (plan, task U0 có `test_hard_bans.py`): `test_no_doctype_literal_in_module` khẳng định thêm tập module mà `hard_bans.py` import ⊆ {`frappe`, `erp_ai.agent.tools.read`, `erp_ai.agent.tools.site_api`} (đúng câu ở dòng 103, nay có test). `TICKET_CONTENT_DOCTYPES` là tập của ADR-034 QĐ 3 (báo cáo), không phải điều cấm cứng của danh mục; `hard_bans.py` và bộ thực thi U7 không dùng nó để quyết điều cấm |

Không phá (đã đối chiếu các fix):
- ADR-001: `schedules.py` (Cửa vào) → `agent.queue` (Lõi); controller Setting → `erp_ai.agent.hard_bans`; report → `erp_ai.constants`; `queue.py` giữ đích là chuỗi, không import ba module job (dòng 79). Đúng chiều.
- ADR-003/ADR-013: một chỗ `enqueue` (`check_single_enqueue_site` không đổi), mỗi đích một lời gọi đủ 5 tham số; `SCHEDULED_JOB_TIMEOUT_S` ở `queue.py` là hằng một nơi dùng, không đổi `JOB_TIMEOUT_S` của `constants.py` (dòng 75).
- ADR-023 QĐ 3, QĐ 5: một nguồn tập phân quyền (INT-1), M5 lặp theo module trên hai DocType mới (INT-2), cửa merge `team/FEAT-007` → `develop` (dòng 214).
- ADR-024: không đổi đọc mục hành động, không đọc `Version`; `insert` + `commit` cùng lời gọi giữ nguyên (dòng 172).
- ADR-030: khối hằng mới không chứa tên công tắc.
- ADR-031: thứ tự lý do, không tên DocType trong `hard_bans.py`, vai trò cấm từ `site_api.FORBIDDEN_ROLES` (dòng 115), dừng `DESIGN_CONFLICT` nếu T59 không công khai tập (dòng 214).
- ADR-032: không chạm.
- ADR-033 QĐ 2, 6, 7, 8: hàm `cron` chỉ xếp một job `long` cố định; khóa chu kỳ cùng giao dịch (dòng 89); không `allow_agent_write()` mới (dòng 135). QĐ 5: option `entry_type`/`trigger` đi cùng commit đổi hằng (dòng 144-150).
- ADR-034 QĐ 3, 8: `TICKET_CONTENT_DOCTYPES` (D-13, đã chấp nhận vòng 1) ∪ `read.denied_doctypes()` chặn lúc lưu (dòng 55); DocPerm Instructor chỉ `read`, `report` (dòng 153).

## 5. Tự phản biện

- U7 thêm tập cấm viết tay vào `constants.py`, `hard_bans.py` import → test AST vẫn xanh: chặn bằng C-2.
- U5a thêm 3 đích, dev không đụng hai scanner test → `cmd.test` đỏ, dev sửa assertion tùy ý: chặn bằng C-1 (cách sửa và chữ khẳng định được ghim).
- Addendum đợt 1 cho một module Lõi dùng `l0_l1_gate` của report: dòng 58, 201 bắt chuyển tên trước; `test_layer_imports` đỏ nếu quên.
- U6b thêm trigger vào `queue.VALID_TRIGGERS`: không đổi số lời `enqueue` (một lời trong `enqueue_agent_run`), C-1 không bị ảnh hưởng.
- U3 (`ENTRY_TYPES_EXPECTED`) và U5a (`ENQUEUE_TARGETS`) cùng sửa `test_architecture.py` ở hai khối khác nhau: chỉ gộp chữ, không mâu thuẫn ngữ nghĩa.
Sau khi siết, không còn cặp task nào tuân mọi ADR mà vẫn xung đột.
