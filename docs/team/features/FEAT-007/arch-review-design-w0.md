Feature: FEAT-007
Stage: architect
Author-agent: architect
Date: 2026-11-14
Approved-by:
<!-- Cổng: G2b không áp dụng cho FEAT-007 (team.py: chỉ G5). Để trống. -->

# Rà soát kiến trúc design.md đợt 0 (U0, U4a, U5a, U6a) — FEAT-007

Đầu vào: `design.md` (724 dòng), `arch-impact.md`, ADR-023, ADR-024, ADR-030..ADR-034, `FEAT-004/plan.md` + `tasks.md` trên `team/FEAT-004` (T62–T68), `FEAT-005/tasks.md` + `design-amd2.md`. Căn cứ đọc trực tiếp (đích đã biết, không qua Explore), 2026-11-14:
- `erp_ai_log.json` trùng byte giữa `develop` (`1918db2`) và `team/FEAT-004` (`05989a7`); `actions` = Small Text, `entry_type` = `classify\nreason\nskip\nchange`, DocPerm chỉ System Manager và ERP AI Agent.
- T64 chỉ sửa `runner.py` + `test_agent_runner.py` (`tasks.md:657`); T66 (controller ERP AI Log, `run_log.py`) đã merge vào `team/FEAT-004`; task duy nhất từng sửa `erp_ai_log.json` là T4 (đã xong). FEAT-005 T1–T16 không sửa `erp_ai_log.json`; FEAT-005 giữ ảnh chụp đầy đủ ở `value_before`/`value_after` (Code), không ở `actions` (`design-amd2.md:158-159`).
- `test_architecture.py:69-80` (LAYER_RULES, ADR-001): `erp_ai.agent` không được import `erp_ai.erp_ai_agent`. `:118-120`, `:529` (ADR-003 Ràng buộc, nới bởi ADR-013): `frappe.enqueue` chỉ ở `agent/queue.py`, đích ghim 2 hàm, đủ 5 tham số. `:1592`, `:1831-1856` (ADR-019 QĐ 7 + ADR-012 QĐ 6): `run_log.ENTRY_TYPES` **và** option `entry_type` của JSON phải đúng 4 giá trị.
- `test_erp_ai_log.py:119-129`: ghim tập role của DocPerm ERP AI Log = {System Manager, ERP AI Agent}.
- `team/FEAT-004-task-59-r2` `site_api.py:26,53,59-63`: không còn `DENIED_DOCTYPES`/`ALWAYS_DENIED_DOCTYPES`; thay bằng `PERMISSION_DOCTYPES`, `always_denied_doctypes()`, `_denied_doctypes(ctx)`.
- `team/FEAT-004` thêm 802 dòng vào `test_architecture.py`; `agent/queue.py` không đổi.

## Rà soát (ba câu)

REVIEW: fix
Design đợt 0 khớp ADR-030 (năm công tắc mặc định 0, thông báo đọc meta D-7, không viết tên công tắc ngoài chỗ được phép), ADR-031 QĐ 1 (danh mục và điều cấm cứng trên ERP AI Setting), ADR-033 QĐ 3, 6, 7 (lịch `cron`, khóa chu kỳ cùng giao dịch, mốc chỉ hàm của việc ghi bằng `set_single_value` trong phiên scheduler), ADR-034 QĐ 2–6, 8 (Error Log ở Lõi ngoài `tools/`, báo cáo chặn lúc lưu, guard HD Article, `roles` có Instructor) và ADR-024 (không đọc `Version`, mẫu mốc khôi phục khi người lưu). Nhưng design phá ADR-001 ở `design.md:198, 212, 307, 338` (module Lõi `erp_ai/agent/**` import hằng/hàm từ controller DocType, LAYER_RULES cấm) và phá ADR-003/ADR-013 ở `design.md:415` (`frappe.enqueue` trong `erp_ai/schedules.py`, ngoài `agent/queue.py`), cả hai làm `test_architecture.py` đỏ ngay ở build. D-5 được chấp nhận có tách phần option `entry_type`/`trigger` sang đơn vị đổi hằng của `run_log.py`, D-6 được chấp nhận kèm test và chốt chiều xuống đã có ở `design.md:529`; sửa bốn finding dưới đây trong `design.md` là build được, không cần quay lại architect.

## Phán quyết D-5 (U0 sửa `erp_ai_log.json`)

**Chấp nhận có ràng buộc; một phần chuyển đơn vị.** Bảng đơn vị của `arch-impact.md` bỏ sót `erp_ai_log.json`; gom phần "chỉ thêm" vào U0 đúng lý do AR-3 (một lần sửa JSON cho nhiều đơn vị đọc), nên được.

Ở lại U0 (`design.md:233-237, 240-241`):
- 5 cột `created_labels`, `predicted_confidence_pct`, `split_requested`, `split_requests`, `site_environment`: chỉ thêm, không ai ghi ở đợt 0, không đổi hình dạng mục hành động (ADR-033 QĐ 5 giữ `site_environment` ở mức dòng).
- `actions` → Long Text (D-6, dưới đây).
- DocPerm `ERP AI Instructor`: **đúng** `read=1`, `report=1`; `create`, `write`, `delete`, `export`, `print`, `email`, `share` = 0 (ADR-034 QĐ 8, Hệ quả "Instructor cần `report` trên `ref_doctype`"). Tính append-only của ADR-004/ADR-024 giữ nguyên.

Chuyển khỏi U0 (`design.md:238-239, 243`):
- Option `bot_action` của `entry_type` → **U3**, cùng một commit với `run_log.ENTRY_TYPES` và `ENTRY_TYPES_EXPECTED` trong `test_architecture.py` (`check_entry_types_unchanged` đòi JSON = hằng = ghim; ADR-033 QĐ 5 là căn cứ sửa ghim ADR-019 QĐ 7). Để ở U0 thì `test_entry_types_unchanged` đỏ ngay ở đợt 0.
- Option `trigger` mới → cùng commit với hằng chấp nhận nó: `setting_save`, `scheduled_job` ở U3 (`run_log.TRIGGERS`); `requester_reply`, `kb_draft` ở U6b (`run_log.TRIGGERS`, `queue.VALID_TRIGGERS`). Option Select là định nghĩa thứ hai của tập giá trị; không để JSON nhận giá trị mà `write_entry` từ chối.

Ràng buộc (kiểm được):
1. Grep: option `entry_type`/`trigger` trong `erp_ai_log.json` chỉ đổi trong commit có đổi `run_log.py` (và `queue.py` cho trigger của runner).
2. Touchpoint U0 thêm `erp_ai/erp_ai_agent/doctype/erp_ai_log/test_erp_ai_log.py`: `test_no_role_can_write_or_delete` đổi tập role thành {System Manager, ERP AI Agent, ERP AI Instructor}, khẳng định Instructor chỉ có `read`, `report` (lý do NFR-8: AC-20 đổi quyền); test hiện có của ERP AI Agent và System Manager giữ nguyên.
3. `DOCTYPE_CONFIG["ERP AI Log"]["field_count"]` = số thật trên nhánh nền + 5.
4. As-Built ghi: người có `ERP AI Instructor` (COO, người rà soát) xem được mọi dòng ERP AI Log trên Desk (Report View), gồm `reasoning`, `error`, trước/sau đã bỏ trường mật.

**Hệ quả thứ tự merge so với `team/FEAT-004`:** `erp_ai_log.json` không có task mở nào của FEAT-004 (T64 chỉ `runner.py`; T66 đã merge, chỉ `erp_ai_log.py`, `run_log.py`) hay FEAT-005, và trùng byte giữa hai nhánh, nên phần U0 không xung đột chữ; vẫn vào `develop` sau `team/FEAT-004` như mọi đơn vị đợt 0. `test_doctype_descriptions.py` đụng FEAT-005 T7 ở khóa khác (`ERP AI Setting`), gộp tay khi merge. Phần chuyển sang U3 đi theo thứ tự của U3: sau FEAT-004 (T68 sửa `test_architecture.py`) và sau phần ADR-024 của FEAT-005 (T14 sửa `test_architecture.py`).

## Phán quyết D-6 (`actions` Small Text → Long Text)

**Chấp nhận có ràng buộc, giữ ở U0.** Căn cứ: ADR-024 Bối cảnh và ADR-033 Hệ quả đã nêu rủi ro tràn 64 KB; sau T64 mỗi mục ghi có `value_before`/`value_after` (T62: tới 20 trường × 200 ký tự), và sau FEAT-005 T5 một lần `write_entry` lỗi vì tràn làm **hoàn tác cả lượt**. Nới kiểu là DDL một chiều, không mất dữ liệu, không đổi mã đọc/ghi. "Chồng lấn T64" chỉ là ngữ nghĩa (T64 tạo ra kích thước), không phải chồng file: T64 không sửa JSON. Không cần chủ T64 xác nhận.

Ràng buộc:
1. Chỉ đổi `fieldtype` của `actions`; không đổi tên, vị trí, `read_only`, hình dạng list JSON của mục (ADR-033 QĐ 5, ADR-024 QĐ 1 đọc mục). Không thêm cắt/giới hạn kích thước trong `write_entry`; `insert` + `commit` cùng lời gọi giữ nguyên (ADR-024 Ràng buộc).
2. Long Text không mở đường đưa ảnh chụp đầy đủ vào `actions`: ảnh chụp đầy đủ vẫn ở `value_before`/`value_after` theo FEAT-005 design-amd2 D-3; muốn gộp là quyết định của FEAT-005, không phải U0.
3. Test U0 thêm (hiện `design.md:614-648` chưa có dòng nào cho D-6): `write_entry` với `actions` > 65 535 byte (chữ tiếng Việt nhiều byte) ghi được và đọc lại trùng; meta `actions.fieldtype == "Long Text"`.
4. Chiều xuống theo đúng `design.md:529`: kiểm `max(length(actions)) ≤ 65535` trước khi trả kiểu; vượt thì giữ Long Text (revert một phần). Ghi vào kế hoạch rollback của As-Built (STD-OPS-1, STD-OPS-2).

**Hệ quả thứ tự merge so với `team/FEAT-004`:** không xung đột chữ (JSON trùng byte, không task mở nào sửa). Ngữ nghĩa: từ lúc `team/FEAT-004` (T64) vào `develop` tới lúc đợt 0 của FEAT-007 vào `develop`, site dev chạy T64 trên Small Text — lượt nhiều lời gọi ghi có thể tràn (sau FEAT-005 T5: cả lượt bị hoàn tác, có Error Log `TITLE_RUN_FAILED`). Kiến trúc cho phép (không bắt buộc) team-leader đưa riêng thay đổi một dòng này vào `develop` sớm hơn dưới dạng commit độc lập kèm test ở ràng buộc 3; nếu không, cửa sổ rủi ro chỉ ở site dev và đóng khi đợt 0 merge, trước G5.

## Điểm khác của design.md phá ADR

| severity | STD | file:line | mô tả | sửa |
|---|---|---|---|---|
| blocker | STD-DESIGN-6 | docs/team/features/FEAT-007/design.md:198, 212, 307, 338 | `KPI_IDS` đặt trong `erp_ai_setting.py` cho `erp_ai/agent/kpi.py` import; hằng hành động/chế độ và `hard_ban_reason` đặt trong `erp_ai_catalog_rule.py` cho bộ thực thi U7 (`erp_ai/agent/tools/`, ADR-031 QĐ 2) import; `TICKET_CONTENT_DOCTYPES` trong `erp_ai_setting.py` cho tool U6b import. Lõi → controller DocType là phụ thuộc ngược ADR-001; `test_architecture.py:69-80` đỏ | Đặt các hằng và `hard_ban_reason` trong một module dưới `erp_ai/agent/` (tên do designer chọn; `hard_ban_reason` đã import `read`, `site_api` nên đặt dưới `agent/` là hợp lệ); controller Setting và Catalog Rule import từ đó. Sửa cả bảng touchpoint U0 |
| blocker | STD-DESIGN-2 | docs/team/features/FEAT-007/design.md:415, 576 | `erp_ai/schedules.py` gọi `frappe.enqueue` trực tiếp: phá ADR-003 Ràng buộc (nới bởi ADR-013: mọi `enqueue` chỉ trong `agent/queue.py`, đích ghim, đủ 5 tham số; `test_architecture.py:118-120, 529`) và tinh thần ADR-033 QĐ 2 (mọi xếp hàng qua `agent/queue.py`) | Ba hàm xếp job `long` nằm trong `agent/queue.py` (đủ `queue`, `timeout`, `enqueue_after_commit`, `job_id`, `deduplicate`); `schedules.py` chỉ gọi chúng. Thêm `erp_ai/agent/queue.py`, `erp_ai/agent/test_queue.py`, `erp_ai/tests/test_architecture.py` (`ENQUEUE_TARGETS` +3 đích, thông điệp dẫn ADR-033 QĐ 6) vào touchpoint U5a. Merge: `test_architecture.py` xung đột với 802 dòng của `team/FEAT-004` (T68 còn mở) và FEAT-005 T14 — gộp tay khi merge `develop` vào `team/FEAT-007` |
| major | STD-DESIGN-2 | docs/team/features/FEAT-007/design.md:223 | `hard_ban_reason` dùng `site_api.DENIED_DOCTYPES`; trên `team/FEAT-004-task-59-r2` tên này không còn (`PERMISSION_DOCTYPES`, `_denied_doctypes(ctx)`). ADR-031 Ràng buộc đòi dẫn xuất từ `read.denied_doctypes()` và tập DocType phân quyền của `site_api` (ADR-023 QĐ 3), một nguồn | Viết `hard_ban_reason` = `read.denied_doctypes()` ∪ tập phân quyền công khai của `site_api` ∪ submittable. Trên nhánh nền `develop` dùng tên hiện có; khi merge `develop` (sau FEAT-004) vào `team/FEAT-007` bắt buộc trỏ sang `site_api.PERMISSION_DOCTYPES`; điều kiện xong: grep `DENIED_DOCTYPES` trong module chứa `hard_ban_reason` = 0, `test_hard_ban_follows_denied_doctypes_source` (`design.md:634`) thêm một ca DocType phân quyền (`Role`) |
| major | STD-DESIGN-2 | docs/team/features/FEAT-007/design.md:87, 519 | Kiểm M5 cho `ERP AI KPI Week`, `ERP AI Review Month` "nối khi T65 ở `develop`" nhưng không gán task hay thời điểm. ADR-033 QĐ 8 + ADR-023 QĐ 5: mọi DocType của module app có kiểm danh tính; đợt 0 vào `develop` khi chưa nối là mở DocType ghi được dưới tài khoản agent | Ràng buộc: nối `refuse_agent_write` ở `before_insert`, `validate`, `on_trash`, `before_rename` của hai DocType (bảng con theo cha) **trong** lần merge `develop` vào `team/FEAT-007` sau FEAT-004, trước khi `team/FEAT-007` vào `develop`; test dưới tài khoản agent: insert/save/delete → `PermissionError`; job dưới phiên scheduler và người rà (phiên người) vẫn ghi được |
| minor | — | — | 1 điểm nhỏ: `design.md:444, 455` liệt kê "#<mã> (nhóm loại trừ)" trong email 08:00 trong khi ADR-034 QĐ 1 ghi "(chỉ đếm)" và test `design.md:677` tên `test_excluded_ticket_counts_only`. AC-52 cho phép "số đếm và số phiếu, không tiêu đề hay nội dung" (luật nghiệp vụ thắng); đọc ADR-034 QĐ 1 cho email 08:00 theo AC-52 — không phải lỗi kiến trúc, chỉ cần tên test khớp hành vi | dev's call |

Không phá: ADR-024 (không đọc `Version` — KPI 3 `design.md:465`; mẫu mốc `design.md:435`); ADR-030 Ràng buộc tên công tắc (`design.md:335`, D-7); ADR-033 QĐ 1 (đợt 0 không ghi phía phiếu), QĐ 6 (khóa chu kỳ `design.md:417-425, 435, 470, 476`), Ràng buộc "chạy hai lần / lỗi giữa chừng" (`design.md:656, 677, 690`); ADR-034 Ràng buộc Error Log ngoài `tools/` (`design.md:487`), `source.py` loại kho HDSD (`design.md:492`), HD Article (`design.md:493`), `roles` báo cáo (`design.md:280-282`); ADR-023 M5 cho bảng con của Setting (theo cha); ADR-001 cho `erp_ai_setting.py` → `agent/tools/source.py`, `site_api` (chiều Cửa vào → Lõi, hợp lệ).

## Tự phản biện

- U0 thêm `bot_action` vào JSON theo design, U3 sau đó thêm vào `run_log.ENTRY_TYPES` → đợt 0 đỏ `test_entry_types_unchanged`: chặn bằng ràng buộc D-5 số 1.
- U5a thêm `frappe.enqueue` ở `schedules.py`, U6b sau đó thêm trigger vào `queue.py` → hai chỗ xếp hàng, ghim đích lệch: chặn bằng finding 2.
- U0 viết `hard_ban_reason` theo `site_api.DENIED_DOCTYPES` của `develop`, FEAT-004 merge xóa tên → `ImportError` lúc lưu Setting sau merge: chặn bằng finding 3 (điều kiện grep).
- T64 ghi mục lớn, U0 chưa vào `develop` → tràn, cả lượt hoàn tác: chấp nhận ở site dev, có lối đưa riêng sớm (D-6).
Sau khi siết, không còn cặp nào tìm được.
