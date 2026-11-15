Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 45 — FEAT-007 T45

- Diff: `git diff c0ae410..5115ff9` (nhánh `team/FEAT-007-task-45`, 2 commit `dfafd00`, `5115ff9`); diff sửa vòng 2: `git diff dfafd00..5115ff9`
- Vòng: 2 (trần `max_rework` = 3)
- Verdict: approve

## Vòng 1 — request-changes

- Lệnh đã dùng (chỉ đọc): `git log --oneline c0ae410..dfafd00`, `git diff --stat c0ae410..dfafd00`, `git diff c0ae410..dfafd00`, `git show dfafd00` (thông điệp commit), `git show c0ae410:<path>` cho `erp_ai/agent/ops_data.py`, `erp_ai/constants.py`, `erp_ai/agent/runner.py`, `erp_ai/test_utils.py`, `erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json`; `git grep` trong `apps/helpdesk` (`new_comment`) và `apps/frappe` (`assign_to.py`).
- Range: 1 commit, 2 file mới (`kpi.py` +144, `test_kpi.py` +263), đúng touchpoints. Không đụng `protected_paths`, không marker skip/xfail.
- Bằng chứng của dev: RED (stub trả `{}`) 2 failures + 2 errors, `Ran 4 tests` `FAILED (failures=2, errors=2)`; GREEN `erp_ai.agent.test_kpi` `Ran 4 tests in 2.210s OK`, `erp_ai.tests.test_architecture` `Ran 112 tests in 3.137s OK`. Test không chạy lại ở đây (luật site).

### Layer 1 — đối chiếu định nghĩa (`design.md:459-465`, AC-53, A-14, A-D2)
- KPI 1: tập = phiếu `creation` trong `[ws, we)`; trung vị trên phiếu có `first_responded_on`; `% ≤ 15`, `% ≤ 5` chia cho **mọi** phiếu của tuần (chưa phản hồi = không đạt); mẫu = số phiếu tạo trong tuần; mẫu 0 → `None`. Khớp. Test bắt được: `<` thay `<=` ở 15 phút (40 thay 60), mẫu số chỉ phiếu đã phản hồi (75 thay 60), hai biên `ws − 1 s` / `we`.
- KPI 2: "đang mở tại `we`" = `creation < we` và (`resolution_date` rỗng hoặc `≥ we`) đúng A-D2 (`filters` AND `or_filters`); đủ = cả 3 trường khác rỗng. Khớp thiết kế. Test bắt được biên `resolution_date = we` và phiếu tạo đúng `we`; **không** bắt được việc bỏ `ticket_type` (major 1).
- KPI 3: tập = `resolution_date` trong `[ws, we)`; (a) Comment `comment_type = "Comment"` có `owner ∉ {AGENT_USER, raised_by}`, Communication `Sent` có `owner ≠ AGENT_USER`, ToDo có `assigned_by ≠ AGENT_USER` → có người; (b) mục `actions` của ERP AI Log `ok is True`, `doctype == "HD Ticket"`, `name == ticket`, `value_after.status ∈ {Resolved, Closed}`. Khớp `design.md:465`; hình dạng mục khớp `run_log.action_entry` và bảng mục của `design-addendum-1-U6b.md:109-110` (`resolve_on_tasks_done` `value_after={"status": "Resolved"}`, `close_silent_f` → `Closed`). Tác giả phía agent quyết bằng `owner` (Comment, Communication) và `assigned_by` (ToDo) đúng chữ thiết kế. Helpdesk bản đang cài ghi ghi chú của agent vào `Comment` (`hd_ticket.py:622` `self.add_comment("Comment", …)`, UI gọi `new_comment`), không vào `HD Ticket Comment`, nên nguồn comment của thiết kế đúng. Hai vế (b) `doctype`, `name` không có ca test (major 2).
- Khóa trả về: đúng 10 khóa KPI 1–3 của `design.md:261-265` (trừ `computed_at`, việc của `run_weekly_kpi` T47); không có khóa KPI 4–6. `KPI_IDS`, `category_by_ticket_type`, `ticket_category` không dùng: KPI 1–3 không cần đầu mục, không phải thiếu.
- Thiết kế không im lặng chỗ nào khiến mã không phán được; một rủi ro định nghĩa (ToDo của Assignment Rule) ghi ở bảng dưới cho designer, không chặn task.

## Phát hiện (chỉ blocker/major)

major | STD-TEST-8 | erp_ai/agent/test_kpi.py:182-183 | Vế `ticket_type` của `COMPLETE_FIELDS` (`kpi.py:17`) không có ca: cả 4 phiếu đang mở đều có `ticket_type`, chỉ hai phiếu mồi (không mở) có `ticket_type=None`. Bỏ `"ticket_type"` khỏi `COMPLETE_FIELDS` thì 4 phiếu mở vẫn ra 2/4 = 50.0, test vẫn xanh (đã tính trên dữ liệu của test) | thêm một phiếu đang mở tại `we` chỉ thiếu `ticket_type` (hai trường kia đủ) và sửa kỳ vọng (mẫu 5, 40.0); mỗi trường trong 3 trường có đúng một phiếu mở chỉ thiếu trường đó | confirmed

major | STD-TEST-8 | erp_ai/agent/test_kpi.py:221-231 | Hai vế `action.get("doctype") == TICKET` và `action.get("name") == row.ticket` của `_bot_closed` (`kpi.py:128-129`) không có ca: mọi mục mồi bị loại bởi `ok` hoặc `value_after.status` (mục `post_comment` không có `value_after`). Bỏ một trong hai vế, test vẫn xanh; khi đó một mục `ok` đặt `status` "Closed" trên DocType khác (vd. ToDo) hoặc trên phiếu khác được tính là bot đóng phiếu, trái `design.md:465` "trên HD Ticket đó" | thêm hai phiếu có vệt chỉ-bot: một có mục `ok`, `value_after={"status": "Closed"}`, `doctype="ToDo"`, `name=<phiếu>`; một có mục `ok` đóng `HD Ticket` nhưng `name=<phiếu khác>`; cả hai không được tính (mẫu 10, 20.0) | confirmed

minor | — | — | 2 điểm nhỏ: (a) STD-TEST-8: ba nhánh dự phòng của `_actions` (`kpi.py:136-144`: JSON hỏng, không phải list, phần tử không phải dict) không có ca; (b) STD-DESIGN-4: `kpi.py:98` so `owner` với `raised_by` nguyên văn, trong khi U6b đã định phép so người tạo là `extract_email_id(...)` + `casefold` (`design-addendum-1-U6b.md:258`); `raised_by` viết hoa khác từ email thì comment của chính người tạo bị tính là người | tùy dev

## Review checklist (10)
1. chưa đạt (major 1, 2: hai tiêu chí của AC-53 chưa được test ghim đủ; không có phần thừa) 2. đạt (2 file của touchpoints, `erp_ai/agent/`) 3. chưa đạt (RED có trước; thiếu ca cho 3 vế, major 1–2, minor a; không skip/xfail) 4. đạt (tuần năm 2001 riêng mỗi test, `keep_agent_settings`, rollback trong `addCleanup`; ngày truyền tường minh) 5. đạt (đầu vào là ngày do job truyền; `except ValueError` có lý do ở docstring) 6. đạt (chỉ đọc, `get_all` có tham số; kết quả chỉ là số) 7. đạt (hàm mới, chưa ai gọi; khóa trùng trường DocType) 8. đạt (`ws`/`we` là tên của thiết kế; không mã chết) 9. đạt (không thêm) 10. đạt (`feat(agent): … (FEAT-007)`, không trailer, nhánh `team/FEAT-007-task-45`)

## Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| Chạy `cmd.test_one` cho `erp_ai/agent/test_kpi.py` và `erp_ai/tests/test_architecture.py` sau merge (reviewer không chạy test, luật site) | |
| Rủi ro định nghĩa KPI 3 (cho designer, không chặn T45): ToDo do Assignment Rule tạo có `assigned_by = frappe.session.user` (`apps/frappe/frappe/desk/form/assign_to.py:111`), tức Administrator/khách/người tạo khi phiếu vào bằng email hoặc cổng; theo `design.md:465` mọi ToDo như vậy làm phiếu "có người", nên nếu Helpdesk tự gán theo luật (spec mục GĐ0 "Assignment Rule theo bảng mục 3") thì KPI 3 có thể luôn gần 0. Cần designer nói rõ ToDo có `assignment_rule` có tính là hành động phía agent không | |
| Mục hành động thật của `resolve_on_tasks_done`, `close_silent_f` (U6b, chưa build) phải có `doctype="HD Ticket"`, `name=<phiếu>`, `value_after.status`; KPI 3 phụ thuộc hình dạng đó | |

## deferred

- (minor, tùy dev) 2 điểm nhỏ ở trên.
- (designer, không chặn) `design.md:465`: ToDo của Assignment Rule; phép so người tạo (nguyên văn hay `extract_email_id` + `casefold`).
- (U6b / verify) hình dạng mục hành động đóng phiếu thật khớp `_bot_closed`.

## Vòng 2 — approve

- Lệnh đã dùng (chỉ đọc): `git log --oneline c0ae410..5115ff9`, `git diff --stat c0ae410..5115ff9`, `git diff --stat dfafd00..5115ff9`, `git diff dfafd00..5115ff9`, `git show 5115ff9:erp_ai/agent/test_kpi.py` (helper `_ticket`, `_close_action`, `_bot_only_trail`, hai test KPI 2/3), `git show 5115ff9:erp_ai/agent/kpi.py`, `git show -s --format='%an%n%B' 5115ff9`, `git diff c0ae410..5115ff9 | grep -nE 'skip|xfail|expectedFailure'` (không kết quả).
- Range sửa: 1 commit `5115ff9`, chỉ `erp_ai/agent/test_kpi.py` (+14 −4); `kpi.py` không đổi. Trong touchpoints, không đụng `protected_paths`, không marker skip/xfail.
- Bằng chứng của dev: RED đột biến (bỏ `"ticket_type"` khỏi `COMPLETE_FIELDS` → `60.0 != 40.0`; bỏ vế `doctype == TICKET` → `30.0 != 20.0`; bỏ vế `name == row.ticket` → `30.0 != 20.0`; mỗi lần `Ran 4 tests` `FAILED (failures=1)`); GREEN `erp_ai.agent.test_kpi` `Ran 4 tests in 3.235s OK`, `erp_ai.tests.test_architecture` `Ran 112 tests in 3.273s OK`. Test không chạy lại ở đây (luật site); các con số đột biến đã tính lại trên dữ liệu của test và khớp.

### Phát hiện vòng 1
- major 1 (STD-TEST-8, `test_kpi.py:182-183`) — ADDRESSED, `erp_ai/agent/test_kpi.py:181-182,189-190`: thêm phiếu tạo `ws + 6 ngày`, chưa giải quyết, chỉ thiếu `ticket_type`. Tập mở tại `we` = 5 phiếu, đủ 2 → 40.0. Bỏ `ticket_type` → 3/5 = 60.0; bỏ `agent_group` hay `priority` cũng → 60.0. Mỗi trường trong 3 trường giờ có đúng một phiếu mở chỉ thiếu trường đó.
- major 2 (STD-TEST-8, `test_kpi.py:221-231`) — ADDRESSED, `erp_ai/agent/test_kpi.py:234-241,249-250`: `other_doctype` (vệt chỉ-bot, mục `ok`, `name` = phiếu, `status` "Closed", chỉ khác `doctype="ToDo"`) và `other_ticket` (vệt chỉ-bot, mục `ok`, `HD Ticket`, "Resolved", chỉ khác `name` = `bot_closed`). Mẫu 10, đạt 2 → 20.0. Bỏ vế `doctype` → `other_doctype` được tính, 30.0; bỏ vế `name` (hoặc nới thành `name in names`) → `other_ticket` được tính, 30.0. Mỗi mồi chỉ trượt đúng một vế, không bị vế khác che.

### Mới trong diff sửa
- Không có blocker/major mới. Kỳ vọng vẫn là hằng số viết tay; mồi mới dùng lại helper sẵn có, tuần 2001 riêng của từng test.

### Review checklist (10) — vòng 2
1. đạt (hai tiêu chí AC-53 còn hở đã được ghim; không phần thừa) 2. đạt (chỉ `test_kpi.py`) 3. đạt (RED đột biến có trước GREEN; đủ ca cho 3 vế của vòng 1; không skip/xfail; minor a vòng 1 vẫn để dev quyết) 4. đạt (không đổi kỳ vọng để khớp hành vi sai: mẫu số tăng đúng theo phiếu thêm; độc lập, tuần riêng) 5. đạt (mã không đổi) 6. đạt (không đổi) 7. đạt (không đổi) 8. đạt (tên `other_doctype`, `other_ticket` nói rõ nghĩa; không mã chết) 9. đạt (không thêm) 10. đạt (`test(agent): … (FEAT-007)`, không trailer, cùng nhánh)

### deferred (vòng 2)
- Giữ nguyên ba mục deferred ở trên (minor a/b; ToDo của Assignment Rule; hình dạng mục đóng phiếu của U6b). Bảng "Không kiểm được từ diff" giữ nguyên, cột phải để trống cho tech-lead.
