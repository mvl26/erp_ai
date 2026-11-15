Feature: FEAT-007
Stage: architect
Author-agent: architect
Date: 2026-11-14
Approved-by:
<!-- G2b không áp dụng (team.py: chỉ G5). Để trống. -->

# Rà soát kiến trúc: design đợt 2a (U5b, U7a), FEAT-007

**Phán quyết tổng:**
- **U5b: approve kèm điều kiện.** Có 1 major (G-1, số đích enqueue), đã sửa xong ở mức hành vi trong file này. Tech-lead đưa điều kiện thẳng vào plan.
- **U7a: request-changes**, giới hạn ở 4 mục: 1.1–1.3, 3.7, 3.8 và dòng test `:381`. Không phải design-defect: khung Cửa vào → Lõi → Cổng model và các ADR-031 QĐ 1–9 vẫn giữ, nên không cần ADR mới. Có 3 major (H-1..H-3). Phần sửa của H-1 và H-2 đã chốt ở đây. H-3 (comment kết quả AC-28) đổi touchpoint và task của U7a, nên chờ người chọn ở phán quyết (6) rồi designer mới viết lại được.

File này **bổ sung** bảng 3.7 của `design-addendum-2-U5b.md` và bảng 3.11 của `design-addendum-2-U7a.md`. Tech-lead, designer U7b và designer U8 đọc cả ba file.

## Căn cứ (đọc trực tiếp ngày 2026-11-14, đích đã biết nên không gọi Explore)

| Câu hỏi | Kết quả | Nguồn |
|---|---|---|
| FEAT-004 AC-28 có task không | **Có.** T56 (`changes/result_comment.py`, `post_result`) và T57 (job gọi `post_result` sau mọi kết cục). Cả hai chưa tick và **ĐỖ từ round 66**: chưa có thiết kế "ai ghi comment kết quả, dưới tài khoản nào". Lý do: `HD Ticket.new_comment` từ chối người không phải agent Helpdesk, còn `frappe.set_user` trong `changes/` trái ADR-013. T48 đã gỡ phụ thuộc T57 | `.claude/worktrees/feat-004/docs/team/features/FEAT-004/tasks.md:636-645`, `:138-139`, `:161`, `:513-514` |
| ADR-013 về chuyển phiên | `erp_ai/agent/changes/**` không có `frappe.set_user`, `publish_realtime` | `docs/team/adr/ADR-013*.md:31`, `:55` |
| `change_decision` có so role riêng không | Không. Nó import controller đề xuất (`proposal_form`), nên đi qua `_decider` | `.claude/worktrees/feat-004/erp_ai/change_decision.py:10-11` |
| Tạo Custom Field có commit ngầm không | **Có.** `CustomField` gọi `frappe.db.updatedb(dt)`, rồi schema MariaDB gọi `frappe.db.sql_ddl`, mà hàm này `self.commit()` trước khi chạy DDL | `../frappe/frappe/custom/doctype/custom_field/custom_field.py:216`; `../frappe/frappe/database/mariadb/schema.py:63`, `:111`; `../frappe/frappe/database/database.py:422-425` |
| Luật ADR-005 trong `agent/tools/**` | AST cấm `ignore_permissions`, `db.set_value`, `db.sql` ghi, `set_user`, `get_all` | `erp_ai/tests/test_architecture.py:624-637` |
| Phép thử tĩnh FEAT-006 AC-9 | So **từ khóa con** trên tên khóa schema của mọi tool (`FORBIDDEN_ROUTE_PARAMETER_WORDS`, có `"user"`, `"owner"`, `"assign"`…). **Chưa có danh sách ngoại lệ nào** | `erp_ai/agent/tools/test_registry.py:19-33`, `:247-259` (commit `7e234d1`, FEAT-006) |
| Số đích enqueue | 2 hôm nay. U5a (đợt 0, F-2) nâng lên 5. U6b (đợt 1, Sửa 5) thêm `lifecycle.run_task_lifecycle` thành 6 | `design-w0-fixes.md:84`; `tasks.md:247`; `design-addendum-1-U6b-fixes.md:170-172` |
| Hằng `ACTION_*` của U0 | Đã có trong T8 (U0, chưa tick) theo `plan.md` "Ràng buộc chung". Không task U0 nào có `CHANGE_KIND_RECORD`, `ACTION_TARGET_DOCTYPES`, `TEST_SITE_ONLY_DOCTYPES`. Nhánh `team/FEAT-007` mới tới T1 | `tasks.md:65-69`; `git log team/FEAT-007` (`19e92a7`) |
| `_permlevel_refusal` của U2 | `(doctype, name, values, ctx) -> dict \| None`, riêng tư. Theo w1a (4), phủ cả Custom Field | `design-addendum-1-U2.md:160`; `arch-review-design-w1a.md:82-85` |
| `missed_scan.scan_missed_tickets` | Hàm `cron` `*/15`, phiên scheduler, hàng `default`. Dòng đầu là kiểm `policy.is_enabled()` | `design.md:367-377` |
| ADR-032 QĐ 3 | Quyền đọc đề xuất loại bản ghi cho agent Helpdesk qua hook quyền của chính DocType | `docs/team/adr/ADR-032.md:24` |

## 1. Phán quyết từng addendum

| Addendum | Phán quyết | Lý do (ba ý) |
|---|---|---|
| `design-addendum-2-U5b.md` | **approve kèm K-1..K-5** | Đúng ADR-033 QĐ 1 (nhắc dưới tài khoản agent qua `enter_agent_session`), QĐ 3 (không import Cổng model, có luật lớp), QĐ 5 (mục dựng bằng `action_entry`, dòng `bot_action` chi phí 0), QĐ 6 (khóa chu kỳ lưu cùng giao dịch, có đủ hai test "chạy hai lần" và "lỗi giữa chừng"), QĐ 9 (email do lượt quét 15 phút gửi, phiên scheduler). Lệch một chỗ: số đích enqueue chưa tính U6b (G-1). Còn lại là minor. |
| `design-addendum-2-U7a.md` | **request-changes** (1.1–1.3, 3.7, 3.8, `:381`) | Đúng ADR-031 QĐ 1–9: một bộ thực thi, thứ tự kiểm đúng QĐ 2, một hàm chèn, một vị từ `can_decide`, "Sửa" ở phần trạng thái, dấu theo loại, không dùng khóa chung. Nhưng: áp dụng "một giao dịch" không đúng với hành động tạo Custom Field (H-1, STD-ERR-7). `_decider` so `ROLE_INSTRUCTOR` trái chính test Ràng buộc 4 của nó (H-2). Đoạn "không có task" về AC-28 sai sự thật, và test 4 kết cục bị đặt điều kiện (H-3). |

## 2. Findings

Định dạng: `severity | STD | ADR bị phá | file:line | mô tả | sửa`.

| # | severity | STD | ADR bị phá | file:line | mô tả | sửa |
|---|---|---|---|---|---|---|
| G-1 | major | STD-DESIGN-1 | ADR-033 QĐ 6; ADR-003/ADR-013 QĐ 2 (một chỗ enqueue, ghim đích) | `design-addendum-2-U5b.md:21`, `:52`, `:205-206`, `:331` | Addendum ghi `ENQUEUE_TARGETS` "5 → 6 sau U5a". U6b (đợt 1) đã nâng lên 6, nên đến lúc U5b (đợt 2) cắt nhánh, tuple là 6. Ghim "6 chuỗi" sẽ thiếu đích `lifecycle` và test kiến trúc đỏ ở cửa merge | phán quyết (2), K-1 |
| H-1 | major | STD-ERR-7 | ADR-031 QĐ 9 (đồng thời dựa vào phép chuyển có điều kiện + kiểm "trước" trong cùng giao dịch ghi); ADR-012 (máy trạng thái không kẹt) | `design-addendum-2-U7a.md:235-240`, `:426` (A-U7a-7), `:193` (savepoint) | `ACTION_CREATE_CUSTOM_FIELD` chạy DDL, và `sql_ddl` commit trước DDL (`database.py:422-425`). Commit này chốt luôn `Đang áp dụng` và giải phóng savepoint `erp_ai_catalog`. Nếu lỗi xảy ra sau DDL, `rollback` không đưa trạng thái về `Đã duyệt`. Khi đó `finish(waiting=Đã duyệt, Lỗi)` ném `InvalidTransition`, đề xuất kẹt ở `Đang áp dụng` trong khi Custom Field đã có. `rollback(save_point=…)` cũng ném vì savepoint không còn | D-1 |
| H-2 | major | STD-DESIGN-2 | ADR-031 Ràng buộc 4 ("không chỗ nào khác so role để quyết duyệt") | `design-addendum-2-U7a.md:245` × `:400` | `_decider` dùng "người có `ERP AI Instructor`" để chọn `DoesNotExistError` hay `PermissionError`. Test `test_no_role_compare_for_decisions` lại cấm `ROLE_INSTRUCTOR` trong controller. Hai dòng này không cùng xanh được: dev sẽ phải chọn hoặc giấu chữ | D-2 |
| H-3 | major | STD-TEST-2 | ADR-031 QĐ 3 ("cùng comment kết quả của FEAT-004 AC-28"); ADR-033 QĐ 1 (comment phiếu dưới tài khoản agent qua một hàm chuyển phiên) | `design-addendum-2-U7a.md:26`, `:40`, `:65`, `:381`, `:412` | Addendum viết "không có task" về AC-28, nhưng T56 và T57 có, và đang ĐỖ chờ đúng câu hỏi kiến trúc mà ADR-033 QĐ 1 đã trả lời. Test 4 kết cục "chỉ viết khi FEAT-004 AC-28 có mã" là một AC (AC-33) có điều kiện không ai giữ | phán quyết (6), D-3 |
| G-2 | minor | STD-TEST-5 | — | `design-addendum-2-U5b.md:113`, `:117`, `:350` (A-U5b-3) | Đổi `daily_report` sang `ticket_deadline` làm hạn kiểu Date thành 23:59:59 trong **báo cáo 08:00** của U5a. Nếu test U5a đang ghim cách hiểu cũ thì test đó phải sửa, kèm lý do (NFR-8) | K-3 |
| H-4 | minor | STD-DESIGN-1 | ADR-032 QĐ 3 | `design-addendum-2-U7a.md:217`, `:250`, `:290` | Comment chỉ người duyệt tới form (`Sửa`, `OPEN_PROPOSAL_LABEL`). Nhưng người được giao mà không có Instructor chưa có quyền đọc đề xuất cho tới khi hook quyền của ADR-032 QĐ 3 (U7b) có. Method POST vẫn chạy được (test AC-35 xanh), còn đường giao diện thì chết giữa U7a và U7b | D-6 |
| H-5 | minor | STD-DESIGN-2 | ADR-005 (luật AST `test_architecture.py:624`); w1a C-2 | `design-addendum-2-U7a.md:184-193` | `catalog.py` nằm trong `agent/tools/**` nên không được dùng `frappe.get_all`, `db.set_value`, `set_user` (phải dùng `db.exists`/`get_value`/`get_doc`). Nó cũng gọi `policy.site_environment()`, nên luật tên `site_environment` của C-2 phải cho phép lời gọi hàm đọc này | D-7 |

`minor | — | — | 3 điểm nhỏ: (a) U7a :131 agent_session khôi phục bằng frappe.set_user(previous); luật test_set_user_agent_only_in_enter_agent_session của U1 phải chỉ bắt set_user với AGENT_USER, dev ghim bằng một ca. (b) U7a :255 đổi cách _entry_values (hàm của U3) chọn hàng; cần một test hồi quy giữ nguyên các hàng U3 cho tool cũ. (c) U5b :200-201 budget_alert phải luôn đứng đầu scan_missed_tickets, vì nhánh lỗi của nó rollback toàn bộ giao dịch; ghi một dòng chú thích và để test test_runs_budget_alert_and_enqueues_due_checks khẳng định thứ tự gọi | dev's call`

## 3. Điều kiện

### U5b (tech-lead đưa thẳng vào task)

| # | Điều kiện | Kiểm xong (có đầu ra) |
|---|---|---|
| K-1 | `ENQUEUE_TARGETS` = tuple trên `team/FEAT-007` lúc cắt nhánh, **nối thêm ở cuối** `"erp_ai.agent.due_checks.run_due_checks"`. Theo thứ tự đợt, đó là 7 chuỗi. `test_enqueue_targets_pinned` ghim đúng tuple đó. Văn bản "5 → 6" (`:205`, `:331`) đọc là "N → N+1". Lý do ghim ghi trong commit: ADR-033 QĐ 6 cộng phán quyết (2) này | `cmd.test_one` `erp_ai/tests/test_architecture.py` xanh sau rebase; `grep -c "frappe.enqueue(" erp_ai/agent/queue.py` = `len(ENQUEUE_TARGETS)` |
| K-2 | Điều kiện bắt đầu: U4a (`missed_scan.py`) và U5a (`ops_data.py`, `daily_report.py`, `queue.py` F-2) đã merge vào `team/FEAT-007`; U6b (`queue.py`, `test_architecture.py`) đã merge; U8 AC-62 (BA note) đã merge. Thiếu điều nào thì `DESIGN_CONFLICT`, dừng | journal ghi commit merge của từng đơn vị |
| K-3 | Task sửa `daily_report.py`: nếu test U5a hỏng vì A-U5b-3 thì sửa assertion kèm dòng lý do "A-U5b-3, AC-58 cùng helper". Không đổi gì khác trong `build_daily_report` ngoài 3 chỗ gọi | `cmd.test_one` `erp_ai/agent/test_daily_report.py` xanh; diff `daily_report.py` chỉ chạm 3 chỗ gọi |
| K-4 | `budget_alert.py` không bao giờ gọi `enter_agent_session` hay `authority.*`. Dòng `bot_action` của nó ghi dưới phiên scheduler (phán quyết (3)) | AST: 0 tham chiếu `enter_agent_session` trong `budget_alert.py` (thêm vào `TestBoundaries`) |
| K-5 | Thứ tự merge `test_architecture.py` trong đợt 2: U5b và U7a sửa hai vùng rời nhau (`ENQUEUE_TARGETS`/`LAYER_RULES` và `TestCatalogArchitecture`/danh sách C-2). Đơn vị merge sau phải rebase rồi chạy `cmd.test_one` cho file này trước khi merge | đầu ra dán journal |

### U7a (designer sửa addendum; các dòng dưới thắng addendum)

| # | Điều kiện | Kiểm xong |
|---|---|---|
| D-1 | **Bỏ A-U7a-7.** `_run_record` theo dạng của `_run_in_lock`, chỉ khác là **không** lấy `filelock` (ADR-031 QĐ 9 giữ): (1) `begin_apply`, rồi `_recheck_record`, rồi **commit** `Đang áp dụng`; (2) `catalog.execute`/`undo` (kiểm "trước" và ghi cùng một giao dịch); (3) `finish(APPLYING, …)` + commit. Ngoại lệ không lường ở (2)–(3) → `rollback`, rồi `finish(APPLYING hoặc UNDOING, Lỗi, …)`, commit. Trong `catalog.execute`, nhánh `ACTION_CREATE_CUSTOM_FIELD` không dựa vào rollback savepoint sau `insert`: lỗi sau `insert` → `refused` `UNEXPECTED_ERROR`, và mục hành động ghi `value_after = {"present": frappe.db.exists(...)}` để người đối soát thấy trường đã có hay chưa | `TA::TestApplyRecord::test_custom_field_error_after_insert_not_stuck` (stub lỗi sau `insert` → `Lỗi`, không kẹt `Đang áp dụng`, mục có `present`); `test_unexpected_error_rolls_back_to_failed` đổi kỳ vọng sang trạng thái kết thúc `Lỗi` từ `APPLYING` |
| D-2 | `_decider` không chứa `ROLE_INSTRUCTOR`. Nhánh "không có đề xuất" dùng `authority.can_decide(user, CHANGE_KIND_CODE, None)` (đúng khi và chỉ khi Instructor, không thuộc `NEVER_AUTHORITY`) để chọn `DoesNotExistError` hay `PermissionError` | `TArch::test_no_role_compare_for_decisions` và `TP::test_unknown_name_non_instructor_permission_error` cùng xanh |
| D-3 | Sửa 1.1 `:26`, 1.2 `:40`, 1.3 `:65` theo căn cứ trên (T56, T57 có, đang ĐỖ). Viết lại phần AC-28 theo nhánh mà người chọn ở phán quyết (6). Test `:381` **không có điều kiện**: là test bắt buộc của U7a | addendum sửa; `grep -n "chỉ viết khi" design-addendum-2-U7a.md` = 0 |
| D-4 | `constants.py` vào touchpoint U7a, theo phán quyết (4) | — |
| D-5 | Dùng `site_api.permlevel_refusal(doctype, values, *, name=None) -> str \| None` theo phán quyết (5). Thay chữ ký `stored=` ở `:62`, `:186` | `TC::TestUpdateFields::test_permlevel_on_custom_field_refused` xanh, không chép luật |
| D-6 | Hook quyền đọc ADR-032 QĐ 3 thuộc **U7b**. U7a và U7b vào `develop` cùng lượt merge cuối đợt 2. QA nghiệm thu đường giao diện của AC-34, AC-35 (người được giao mở form, bấm "Sửa và duyệt") sau khi U7b merge. U7a không thêm DocPerm nào | ghi trong plan đợt 2; ma trận AC-35 của U7a vẫn chạy qua POST |
| D-7 | `catalog.py` chỉ dùng `frappe.db.exists`, `frappe.db.get_value`, `frappe.get_doc` để đọc (luật ADR-005). Danh sách cho phép của C-2 (`check_site_environment_readers`) thêm "lời gọi `policy.site_environment(`" (khuyến nghị) hoặc thêm `catalog.py` kèm một dòng lý do | `cmd.test_one` `erp_ai/tests/test_architecture.py` xanh với `catalog.py` thật |
| D-8 | Danh sách ngoại lệ AC-9, theo phán quyết (7) | — |

## 4. Phán quyết (1)–(9)

**(1) U5b sửa `ops_data.py`, `daily_report.py`, `missed_scan.py`. Chủ: U5b, đợt 2. Chấp nhận A-U5b-1.** Ô "file việc theo lịch" của hàng U5b (`arch-impact.md:183`) là cùng loại file mà hàng U5a (`:174`) tạo ra. `missed_scan.py` là việc quét 15 phút của U4a (`:173`), và ADR-033 QĐ 9 chỉ đích danh "việc quét 15 phút" là nơi gửi email vượt ngân sách. Gắn vào đó là đọc đúng ADR, không phải mượn file. Phương án `schedules.py` cộng `hooks.py` thêm một hàm `cron` cùng khóa `*/15` và phải `cmd.migrate`, mà không có lợi ích kiến trúc nào. Ràng buộc:
- Vùng sửa: `ops_data.py` thêm 3 hàm và **chuyển** phép BA note của U5a vào `tickets_with_ba_note` (một phép, STD-DESIGN-4); `daily_report.py` chỉ 3 chỗ gọi; `missed_scan.py` chỉ khối đầu `scan_missed_tickets`.
- Không đơn vị đợt 2 nào khác sửa ba file này (U7a, U8 không chạm), nên không có thứ tự merge.
- Điều kiện bắt đầu K-2.

**(2) `ENQUEUE_TARGETS` cộng dồn theo thứ tự merge; mỗi đơn vị nối ở cuối.** Số đích là số trên `team/FEAT-007` lúc đơn vị cắt nhánh, cộng số đích của chính đơn vị. Tuple ghim theo thứ tự merge:

| Bước | Đơn vị (đợt) | Đích thêm | Tổng |
|---|---|---|---|
| 0 | FEAT-004 (`develop`) | `run_for_ticket`, `run_change` | 2 |
| 1 | U5a (0, F-2) | `daily_report`, `weekly_kpi`, `monthly_review` | 5 |
| 2 | U6b (1, Sửa 5) | `lifecycle.run_task_lifecycle` | 6 |
| 3 | U5b (2) | `due_checks.run_due_checks` | **7** |

U7a, U7b, U8 không thêm đích (dùng `enqueue_change_job`, `enqueue_agent_run` có sẵn). Nếu thứ tự merge thực tế đổi (U6b trễ sau U5b), đơn vị merge sau rebase, nối đích của mình vào cuối tuple đang có và ghim tổng mới. Không đơn vị nào ghim một con số viết sẵn trong addendum. `check_enqueue_call_shape` đã dùng `len(ENQUEUE_TARGETS)` từ F-2 nên không sửa.

**(3) `budget_alert.py` chạy dưới phiên scheduler. Xác nhận.** ADR-033 QĐ 9 ("phiên scheduler, khóa = tháng"), QĐ 6 (mốc ghi bằng `set_single_value` trong phiên scheduler, cùng giao dịch với tác động) và QĐ 1 (phiên agent không bao giờ ghi ERP AI Setting) cùng buộc như vậy. Bước 1 từ chối phiên agent là đúng Ràng buộc 2.
- Dòng `bot_action` của việc này được ghi dưới phiên scheduler. Hàng "ERP AI Log dòng không phải lần chạy … agent (job)" của QĐ 7 nói về job phía phiếu (phạm vi QĐ 1). Email ngân sách không phải ghi phía phiếu, nên KPI 3 không bị ảnh hưởng.
- M5 chỉ chặn tài khoản agent. `write_entry` của U3 chạy trong `allow_agent_write()` nên ghi được dưới mọi phiên. Chuyển sang phiên agent chỉ để ghi dòng này sẽ thêm một lần chuyển phiên mà không chốt thêm gì.
- Không cần ADR mới. As-Built ghi "dòng `budget_alert` có `owner` = người dùng scheduler". Ràng buộc K-4.

**(4) Ba hằng `CHANGE_KIND_RECORD`, `ACTION_TARGET_DOCTYPES`, `TEST_SITE_ONLY_DOCTYPES`. Chủ: U7a, đợt 2. `erp_ai/constants.py` vào touchpoint U7a, đúng 3 hằng.** Không giao U0 (T8 đang build):
- `CHANGE_KIND_RECORD` phải vào **cùng commit** với option mới của `change_kind` trong JSON đề xuất (U7a). Tên có trước giá trị option là tên trước khi tồn tại (cùng lý do w1a (2) không cho U1 liệt kê sẵn trigger).
- Hai hằng còn lại chỉ U7a, U7b, U8 dùng. Đặt ở U0 là mã chết suốt đợt 0–1 và đổi task đang chạy.
- Cách đặt: nối vào cuối khối FEAT-007 của `constants.py` (sau khối T8 và trigger của U6b). `constants.py` giữ 0 dòng import (T8, A-D6). Giá trị `ACTION_TARGET_DOCTYPES` đúng cột "DocType đích" của `design.md:214-221`.
- Đặt ở `constants.py`, không ở `catalog.py`, là đúng ADR-031 Ràng buộc 7: module danh mục không viết tay tên DocType. `TEST_SITE_ONLY_DOCTYPES` là danh sách nghiệp vụ của AC-12, khác nghĩa với `site_api.PERMLEVEL_DOCTYPES` (vector phân quyền), nên hai tập cùng chứa `"Custom Field"` không phải trùng định nghĩa.
- Thứ tự sửa `constants.py`: U0 (T8) → U6b (trigger) → U7a. Ba đợt khác nhau nên không xung đột.

**(5) `site_api.permlevel_refusal` công khai. Chủ: U2, đợt 1 (bổ sung C-6 của w1a).** U2 tách `_permlevel_refusal` thành:
- `permlevel_refusal(doctype: str, values: dict, *, name: str | None = None) -> str | None`: thuần theo luật C-6, không `ctx`. `name` khác None thì đọc giá trị đã lưu bên trong `site_api` (`property` của Property Setter, `permlevel` của Custom Field). Trả `PERMLEVEL_REASON` hoặc `None`.
- `_permlevel_refusal(doctype, name, values, ctx)` giữ chữ ký cũ: `ctx.unrestricted` → `None`; ngược lại `reason = permlevel_refusal(doctype, values, name=name)` → `_fail(reason, doctype)` nếu có.
- `PERMLEVEL_DOCTYPES`, `PERMLEVEL_REASON` công khai (đã có ở C-6).

Dùng `name=` thay `stored=` của U7a (`:62`) để phép đọc giá trị đã lưu chỉ ở một chỗ (STD-DESIGN-4). U7a luôn gọi ở chế độ thường. Nếu U2 đã merge mà chưa có tên công khai, plan đợt 2 thêm một task tách hàm (chỉ tách, không đổi hành vi) trên `site_api.py` + `test_site_api.py`, đặt trước task bộ thực thi của U7a. U7a không chép luật.

**(6) Comment kết quả AC-33 / FEAT-004 AC-28.** Sự thật: T56 (`result_comment.py`, `post_result`) và T57 (job gọi sau mọi kết cục) có trong plan FEAT-004 nhưng **ĐỖ**, vì không có câu trả lời "ghi dưới tài khoản nào".

Câu trả lời kiến trúc đã có:
- ADR-033 QĐ 1 và QĐ 7 (hàng "Comment … lỗi"): comment phiếu do app tạo ghi dưới **tài khoản agent**, vào phiên đó qua **một** hàm chuyển phiên dùng chung (`enter_agent_session` của U1). Mẫu "chuyển phiên chỉ quanh lần ghi, trả lại phiên" là `authority.agent_session()` của U7a (3.2).
- `result_comment.py` gọi `with authority.agent_session(): ticket.new_comment(...)` **sau** `finish`, lỗi comment không đổi kết cục (T57, STD-ERR-1). Không có `frappe.set_user` nào trong `changes/` (ADR-013 Ràng buộc giữ), không ghi dưới phiên người duyệt.

Hệ quả: T56 chỉ build được sau U1, mà U1 lại cắt sau khi FEAT-004 merge. Vậy AC-28 không làm được trong FEAT-004 mà vẫn đúng ADR-013 và ADR-033, trừ khi FEAT-004 tự lập hàm chuyển phiên thứ hai (trái ADR-033 Ràng buộc 1).

**Khuyến nghị (người quyết, theo FEAT-004 spec N-7):** FEAT-004 bỏ AC-28, gỡ T56, T57. U7a nhận `result_comment.py` (file mới trong `erp_ai/agent/changes/`) cùng các lời gọi `post_result` ở **mọi** điểm kết thúc của `run_change`, cả code/bench (`_run_in_lock`, gồm `LOCK_BUSY`) lẫn 4 kết cục của `_run_record`, theo tiêu chí T56 nguyên văn cộng một dòng cho loại bản ghi. Analyst `--amend` FEAT-007 để phủ AC-28 cho mọi loại.

Theo từng nhánh, U7a dùng lại và thêm:

| | Nhánh A: người giữ AC-28 ở FEAT-004 (FEAT-004 phải tự chuyển phiên qua `authority.py`, rồi U1 gộp vào `enter_agent_session`) | Nhánh B (khuyến nghị): AC-28 sang U7a |
|---|---|---|
| U7a dùng lại | `result_comment.post_result` của T56, nguyên tên, một bộ dựng chữ cho mọi loại | `authority.agent_session`, `enter_agent_session` (U1) |
| U7a thêm | gọi `post_result` ở 4 kết cục của `_run_record`; nhánh chữ loại bản ghi (hành động, đích, lý do) trong `result_comment.py`; `result_comment.py` + test vào touchpoint | tạo `result_comment.py` + `test_result_comment.py`; lời gọi ở mọi điểm kết thúc trong `apply_job.py` |
| Bất biến cả hai nhánh | một bộ dựng comment kết quả, một lời gọi mỗi kết cục; không đường comment thứ hai trong `_run_record`; test `:381` bắt buộc | như trên |

`arch-impact.md:181` (U7 phụ thuộc "T56") đọc theo nhánh được chọn. Team-leader chuyển câu hỏi N-7 cho người. Câu này chặn D-3, không chặn U5b.

**(7) Danh sách ngoại lệ của phép thử tĩnh FEAT-006 AC-9. Chủ: U7a, đợt 2. File `erp_ai/agent/tools/test_registry.py` đã có trong touchpoint U7a (`:339`).**
- U7a thêm **một** hằng `ROUTE_WORD_EXCEPTIONS: tuple[tuple[str, str], ...]` (cặp tool, khóa) ngay sau `FORBIDDEN_ROUTE_PARAMETER_WORDS`. `test_no_tool_schema_takes_person_sla_priority_or_score` bỏ qua đúng các cặp đó. Làm trong cùng commit với `catalog_tools.py`.
- Hiện chỉ một cặp chạm từ cấm: `("catalog_add_team_member", "user")`. Các khóa `email`, `first_name`, `last_name` của `catalog_create_user` không khớp từ nào nên **không** đưa vào. Công cụ bản ghi của FEAT-004 nhận khóa chung (`doctype`, `values`) nên hiện không cần ngoại lệ. Đây là danh sách duy nhất ADR-031 Ràng buộc 8 nói tới; ai cần thêm thì nối vào nó.
- Thêm `::test_route_word_exceptions_are_live`: mỗi cặp phải có trong schema thật và phải chạm một từ cấm, để danh sách không giữ dòng chết.

**(8) `policy.py`, `runner.py` làm touchpoint của U7a. Chấp nhận**, ghi nhận đây là thiếu sót của bảng `arch-impact.md:181`: `design.md:124` và w0-fixes F-1 đã giao `policy.py` cho U7, hợp đồng U3 3.10 đã giao `WRITE_TOOL_TARGETS`. Thứ tự và vùng (nối bảng w1a (5)):

| File | Thứ tự | Vùng của U7a |
|---|---|---|
| `erp_ai/agent/policy.py` | U1 → U2 → U6b → **U7a** → U8 (nếu cần) | chỉ 3.1: `CATALOG_RULES_FIELD`, `USER_TEMPLATES_FIELD`, `CatalogRule`, `catalog_rules`, `user_template_roles`. `policy` không import `hard_bans`, `tools` |
| `erp_ai/agent/runner.py` | U1 → U2 → U3 → U4b → U6b → **U7a** | chỉ `PROPOSE_TOOLS`, điều kiện ghi bước `propose`, 6 dòng `WRITE_TOOL_TARGETS`, phép chọn hàng trong `_entry_values` (kèm test hồi quy hàng U3, minor (b)) |
| `erp_ai/agent/tools/registry.py` | U1 → U6b → **U7a** → U8 | `TOOL_MODULES`, `ToolSpec.group`, một dòng `GRANT_TABLE` |

`prompts.py` (khối danh mục) là của U7b. U5b không chạm các file này nên chạy song song với U7a được.

**(9) A-U7a-3 (tự gán rồi duyệt đề xuất bản ghi).** Về kiến trúc thì trung lập: ADR-031 QĐ 5 đặt điều kiện "có ToDo mở giao phiếu", không nói ai gán. Cả hai cách đều nằm trọn trong `authority.is_assigned`, không đổi chữ ký `can_decide`/`is_assigned`, không đổi hợp đồng U7b.
- Mặc định của addendum đúng chữ AC-35 (a), giữ cho build.
- Đây là **luật nghiệp vụ**, architect không quyết. Hệ quả cần người biết: mọi agent Helpdesk tự gán được phiếu đều thành người duyệt được đề xuất bản ghi của phiếu đó, và danh mục cộng điều cấm cứng là lớp chặn duy nhất (ADR-031 Hệ quả; `arch-impact.md:193-194`).
- `NEEDS_ANSWER` không chặn, team-leader chuyển analyst/người: có chấp nhận "tự gán rồi tự duyệt" không. Nếu không, thêm vế `assigned_by ≠ user` vào `is_assigned` cộng một ca test; không gì khác đổi.

## 5. Hợp đồng U7a mà U7b, U8 dựa vào được (không đổi)

Giữ nguyên tên, chữ ký và nghĩa như `design-addendum-2-U7a.md:261-282`:
- `authority.can_decide(user, change_kind, ticket_name) -> bool`, `authority.is_assigned(user, ticket_name) -> bool` (thân có thể thêm vế ở (9), chữ ký không đổi), `authority.agent_session()`.
- Method controller `approve`, `reject`, `undo` (`name=None`), `approve_with_edit(name=None, edited_args=None)`, trả `{"name", "status"}`, POST.
- `transitions.approve(name, user, *, edited=None) -> str`.
- `catalog.CatalogRequest`, `CheckResult`, `ExecResult`, `ActionHandler`; `check`, `execute`, `undo`, `check_edit`, `effective_args`, `rule_mode`; `ACTION_HANDLERS`, `RESTORABLE_ACTIONS`; chữ `OUT_OF_CATALOG`, `RULE_DENIED`, `TEST_SITE_ONLY`, `NO_CHANGE`, `STALE_TARGET`.
- `catalog_tools.GROUP = "catalog"`, `CATALOG_WRITE_TOOL_NAMES` (6 tên), điểm chen "Tự làm" trước bước 4 của `_propose`.
- Dòng `catalog` của `GRANT_TABLE` (`main_path_level ≥ L2 ∧ ¬below_threshold`).
- `propose_change.insert_proposal(ctx, values) -> dict`.
- `policy.CatalogRule`, `catalog_rules`, `user_template_roles`.
- Trường đề xuất của `:280` (`change_kind`, `catalog_action`, `category`, `confidence_pct`, `change_status`, `decided_by`, `decided_at`, `approved_with_edit`, `edited_args`, `undo_by`, `undo_at`, `finished_at`, `reversible`).
- Hằng `CHANGE_KIND_RECORD`, `ACTION_TARGET_DOCTYPES`, `TEST_SITE_ONLY_DOCTYPES` ở `erp_ai/constants.py` (chủ U7a, phán quyết (4)).
- Bước nhật ký: `approve` mang trước/sau của lần sửa; `apply`/`stale`/`fail`/`undo` mang đúng 1 mục `action_entry`.

**Không dựa vào cho tới khi chốt:**
- Giao dịch bên trong `_run_record` (đổi theo D-1, chỉ là chi tiết bên trong).
- Đường comment kết quả: chỉ `result_comment.post_result` là tên ổn định, chủ file theo (6).
- Chữ ký `site_api.permlevel_refusal` là bản ở (5), không phải `stored=` của `:62`.
- Hook quyền ADR-032 QĐ 3 là của U7b (D-6).

## 6. ADR có bị phá không

| ADR | U5b | U7a |
|---|---|---|
| ADR-001 | Không (luật lớp 3.6) | Không (bộ thực thi không gọi Cổng model) |
| ADR-005 | Không chạm `tools/` | Không, nếu giữ D-7. Ngoại lệ tên DocType hẹp đúng ADR-031 |
| ADR-012, ADR-013 | Không chạm | H-1 làm kẹt máy trạng thái ở một hành động (D-1). Không `set_user` trong `changes/` (giữ, kể cả với (6)) |
| ADR-023 | M5 không mở đường mới | M5 đường 2 giữ (một `insert_proposal`); M2 kiểm trước khi chuyển phiên |
| ADR-030 | Ngân sách sống (QĐ 2) | Dòng cấp `catalog` đúng QĐ 3 |
| ADR-031 | — | QĐ 1–9 giữ. Ràng buộc 4 bị H-2 (D-2); Ràng buộc 8 thực hiện ở (7) |
| ADR-032 | — | QĐ 3 để U7b (D-6) |
| ADR-033 | QĐ 6 lệch số đích (G-1); QĐ 7 đọc theo (3) | QĐ 1 cho comment kết quả theo (6) |
| ADR-034 | Vị từ `can_send_ticket` (U2 mở rộng), Notification Log chỉ có mã | Vị từ `is_ticket_record_excluded` ở bước 3 của `check` |

## 7. Tự phản biện

Đã dựng các cặp task cùng tuân mọi ADR và phán quyết trên mà vẫn xung đột, rồi siết lại:
1. U6b và U5b mỗi bên ghim tuple theo con số trong addendum của mình, nên test kiến trúc đỏ ở lần merge sau. Đã siết bằng (2): ghim theo tuple lúc cắt nhánh, nối ở cuối.
2. Task `_run_record` tự viết comment kết quả, rồi T57 (hoặc task AC-28 sau này) viết bộ dựng thứ hai trong `_run_in_lock`. Kết quả là hai chữ, hai đường chuyển phiên. Đã siết bằng (6): một `post_result`, một lời gọi mỗi kết cục.
3. Task bộ thực thi U7a chép luật `permlevel` vì U2 chỉ có hàm riêng. Đã siết bằng (5): U2 công khai hàm thuần.
4. T8 (U0) và U7a cùng thêm `CHANGE_KIND_RECORD`, hoặc U0 thêm tên mà option JSON chưa có. Đã siết bằng (4): chỉ U7a, cùng commit với JSON.
5. Tạo Custom Field commit ngầm giữa giao dịch, đề xuất kẹt `Đang áp dụng`. Đã siết bằng D-1.
6. U7a đăng liên kết form, U7b cấp quyền đọc sau; nếu U7a vào `develop` một mình thì người được giao bấm liên kết chết. Đã siết bằng D-6: merge cùng lượt, nghiệm thu giao diện sau U7b.
7. Task U7a nối `email`, `first_name` vào ngoại lệ AC-9 "cho đủ", còn task sau tưởng chúng cần thiết. Đã siết bằng `test_route_word_exceptions_are_live` ở (7).

Sau khi siết, không còn cặp nào trong phạm vi U5b, U7a. U7b, U8 (AC-64) sẽ được rà ở lần gọi sau, khi đó kiểm D-6 và ADR-031 QĐ 4, QĐ 8.

## Việc tiếp

- Tech-lead: đưa K-1..K-5 vào plan U5b; U5b chạy được khi đủ K-2.
- Designer: sửa U7a theo D-1..D-8, phần AC-28 viết sau khi người chọn nhánh (6).
- Team-leader chuyển hai câu cho người/analyst, cả hai không chặn U5b:
  - FEAT-004 N-7 (AC-28 ở đâu). Câu này chặn D-3.
  - A-U7a-3 (tự gán rồi tự duyệt). Câu này không chặn.
- Không cần ADR mới.
