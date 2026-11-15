Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 179 — FEAT-007 T179

- Diff: `git diff 09b5438..fc09fb2` (nhánh `team/FEAT-007-task-179`; 2 commit `18c76c3` test, `fc09fb2` mã; 2 file +191/−19, đều là touchpoint)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve
- File này do tech-lead ghi từ báo cáo của reviewer (vai reviewer không ghi file dưới `docs/`); chữ của reviewer giữ nguyên ý, finding giữ nguyên văn. Ghi trước khi merge.
- Ghi chú số task: `design-w1-fixes-15.md` gọi task này là "T176"; theo quyết định 10:58 (b) của team-leader mọi chữ "T176" của file đó đọc là T179.

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED (chỉ test, trên mã T51): `Ran 10 tests in 2.882s` / `FAILED (failures=2, errors=5)`; `test_due_lists_carry_deadline`: phần tử không có khóa `deadline`, chênh lệch in `+   'deadline': datetime.datetime(2002, 5, 6, 11, 0)`; `test_empty_priority_counted_as_unknown`: `KeyError: '?'`; `test_reopened_ticket_not_done`: `AssertionError: {'done': 1, 'in_progress': 1, 'overdue': 0} != {'done': 0, ...}`; `test_due_field_not_on_ticket_uses_resolution_by`, trường không có: `pymysql.err.OperationalError: (1054, "Unknown column 'erpai_test_no_such_field' in 'SELECT'")`; cùng test, trường `subject`: `TypeError: combine() argument 1 must be datetime.date, not str`; `test_twelve_tickets_sections` và `test_no_due_field_uses_resolution_by`: `KeyError: 'deadline'`. Đỏ của đột biến (bỏ `"comment_type": "Comment"`, không commit, rồi trả lại): `MIGRATE_EXIT=0`, `Ran 10 tests in 2.835s` / `FAILED (failures=1)`, `test_ba_note_other_comment_type_not_counted`: `AssertionError: Lists differ: [] != ['43070']`. GREEN: `MIGRATE_EXIT=0`; `test_daily_report`: `Ran 10 tests in 2.859s` / `OK`; `test_architecture`: `Ran 185 tests in 17.194s` / `OK`.

Các phép kiểm chính của reviewer (theo thứ tự lời giao, dùng 6/16 lượt):

1. Commit và touchpoint: chỉ `daily_report.py` và `test_daily_report.py` đổi (191/19); commit test `18c76c3` đứng trước commit mã `fc09fb2`; hai tiêu đề đúng `type(scope): description (FEAT-007)`, không dòng ghi công (STD-GIT-8). Không file mới, không khóa mới của dict báo cáo.
2. Mã so với dòng Returns: `DUE_FIELD_TYPES` và chú thích một dòng khớp Điểm 3; docstring module khớp Điểm 1 (a) từng chữ; `deadline` chỉ thêm ở nhánh phiếu gửi được của `_items` khi `with_deadline=True`, chỉ `due_soon` và `overdue` truyền cờ đó; `deadline` là `row.deadline`, đúng giá trị `processing_deadline(...)` đã dùng để xếp phiếu vào danh sách; phiếu loại trừ không mang `deadline` lẫn `subject` (AC-52); `_priority` đổi ưu tiên rỗng thành `"?"` ở cả số đếm và phần tử, kể cả phiếu loại trừ; `done` thêm lọc `status_category = "Resolved"`; `_due_field` ghi một cảnh báo, mỗi lần dựng một lần, đúng chữ Điểm 3, chỉ ghi tên trường, không `log_error`, không ghi Setting; giữ bộ lọc `comment_type: "Comment"`; không import controller (ADR-001), không gán mới vào ngày SLA; `order_by="creation asc, name asc"` không đổi.
3. Test so với dòng Expect: đủ năm test mới đúng tên; từng cái đỏ khi thiếu mã tương ứng: `test_due_lists_carry_deadline` (mốc `resolution_by` của E là anchor + 2 ngày, khác hạn Date 2002-05-05 23:59:59, nên đổi sang `resolution_by` sẽ đỏ; dict chính xác của phiếu loại trừ bắt được `deadline` lọt); `test_due_field_not_on_ticket_uses_resolution_by` (subtest trường không có phủ `field is None`, subtest `subject` phủ phép kiểm kiểu trường; danh sách lời gọi cảnh báo so chính xác nên phải đúng một lần); `test_reopened_ticket_not_done` (bỏ lọc mới cho `done` 1); `test_empty_priority_counted_as_unknown` (`KeyError: '?'` trên mã T51); `test_ba_note_other_comment_type_not_counted` (đỏ của đột biến có trong bằng chứng). `test_excluded_ticket_number_only_in_every_list` thêm phiếu loại trừ sắp hạn và khóa `"due_soon"`, dict chờ chính xác nên `deadline` hay `subject` lọt sẽ đỏ. Thay đổi duy nhất ở khẳng định có sẵn là các phép kiểm `deadline` mới trong `test_twelve_tickets_sections` và `test_no_due_field_uses_resolution_by`, thiết kế đòi (STD-TEST-5 đạt). Mỗi test tự tạo dữ liệu, truyền `anchor` cố định, có `keep_agent_settings` và rollback (STD-TEST-6 đạt). Không dấu skip.
4. Xử lý lỗi và biên: không có try/except; lối lùi là một phép kiểm trường tường minh nên không che lỗi khác (STD-ERR-1 đạt); cảnh báo chỉ mang tên trường đã cấu hình, không nhạy cảm (STD-SEC-6 đạt).
5. Còn lại: không phụ thuộc mới, không vỡ hợp đồng, không mã chết.

Checklist (10): 10/10 đạt.

Findings: không blocker, không major.

- minor | — | — | 3 small points: (1) no test checks that an empty `field_due_date` logs no warning (Điểm 3 case 1); (2) `test_reopened_ticket_not_done` passes `status="Open"`, which `_ticket` already defaults to; (3) the `_priority` docstring names the category constant `UNKNOWN_CATEGORY` for a priority, which follows the design but reads oddly | dev's call

Mục "không kiểm được từ diff" của reviewer:

- `opening_date` có thật là trường Date của HD Ticket trong bản Helpdesk đã cài không: test dựa vào đó, lần GREEN cho thấy có.
- `test_architecture` xanh (185 test theo đầu ra của dev): reviewer không chạy.
- pre-commit qua: chỉ theo lời dev.

## Kết luận của tech-lead

- Merge `7d789a9` trên `team/FEAT-007` (sau khi file này có verdict và T177 đã tick). Chạy test sau merge, một lần giữ khóa site, `MIGRATE_EXIT=0`: test_daily_report `Ran 10 tests in 2.739s OK`, test_architecture `Ran 185 tests in 16.464s OK`.
- `opening_date`: `apps/helpdesk/helpdesk/helpdesk/doctype/hd_ticket/hd_ticket.json:293-294` có `"fieldname": "opening_date"`, `"fieldtype": "Date"` (tech-lead đọc file của bản Helpdesk đã cài).
- pre-commit: sửa lại lúc 14:45: repo không cài hook pre-commit nào (`.git/hooks` chỉ có file mẫu), nên không commit nào "đi qua hook". Bằng chứng đứng được: `cmd.lint` cả cây @ `32fa2bb` (chứa T179) do một dev chạy: hook đỏ duy nhất là ruff-format trên `erp_ai/agent/knowledge.py` (của T177), hai file của T179 không bị hook nào sửa; sau khi T177 sửa, `cmd.lint` cả cây @ `ac8386b` (cùng cây với đầu nhánh `ed341b9`): 12 hook Passed, `LINT_EXIT=0`.

## deferred

- minor (1): chưa có test "trường hạn rỗng thì không ghi cảnh báo" (Điểm 3 ca 1) → T52 hoặc T53 thêm khi chạm `test_daily_report.py` (vào lời giao dev).
- minor (2): `status="Open"` thừa trong `test_reopened_ticket_not_done` → không việc.
- minor (3): docstring `_priority` nêu `UNKNOWN_CATEGORY` cho ưu tiên (theo thiết kế) → As-Built.
