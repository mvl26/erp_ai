Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 36 — FEAT-007 T36

- Diff: `git diff a805842..3d89bc4` (nhánh `team/FEAT-007-task-36`, 1 commit `3d89bc4`, 2 file mới +253)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve

## Vòng 1 — approve

- Lệnh đã dùng (chỉ đọc): `git log --oneline a805842..team/FEAT-007-task-36`, `git diff --stat`, `git diff`, `git log -1 --format=%B`, `git show team/FEAT-007-task-36:.team/profile.json`, `git grep` các hàm trợ giúp ở đầu nhánh; đọc `apps/frappe/frappe/model/db_query.py:1265-1330`, `frappe/database/mariadb/database.py:240-257`, `frappe/query_builder/utils.py:111-117`.
- Bằng chứng của dev: RED với hàm giả trả sai: `AssertionError: Lists differ: [] != ['3cf2e1cd64eb', 'dd8bca8cb3e8', '712b8bf45538']`, `Ran 8 tests in 0.887s FAILED (failures=8)`; GREEN `test_system_read` `Ran 8 tests in 1.180s OK`, `test_architecture` `Ran 112 tests in 6.077s OK`.
- Lớp 1 (khớp spec): mọi vế của AC-50 có mã và có test: cửa sổ mặc định 24 giờ gồm cả hai đầu, 7 ngày được nhận và 7 ngày + 1 µs bị từ chối, `limit` 1..50, `keyword` 2..100, LIKE escape cho `\`, `%`, `_`, `error` giữ 2000 ký tự cuối. Che trước, cắt sau đúng Chèn 3 / 3a (`system_read.py:67-68`, test `TestReadErrorLogs::test_secret_at_tail_cut_masked`). NFR-6, STD-SEC-3 đạt: từ khóa đi vào như tham số (`prepare_query`, `query_builder/utils.py:111-117`). Đủ 7 test của Expect, thêm `test_error_keeps_last_2000_chars`. Diff chỉ chạm 2 file touchpoints; module nằm ngoài `tools/` (ADR-021 QĐ 4), không `@frappe.whitelist`, không import `erp_ai.erp_ai_agent`.

### Câu hỏi của tech-lead: `frappe.qb` thay `frappe.get_all` (`design.md:487`)

Reviewer xếp là cách làm chấp nhận được, không phải finding, không phải design-defect của task này:

- Qua `get_all`, giá trị LIKE bị nhân đôi mọi `\` và đổi `%` thành `%%` (`db_query.py:1283-1286`), rồi đi qua `frappe.db.escape(value, percent=False)` (`db_query.py:1313`), nhân đôi `\` lần nữa. `\%` do dev viết tới MariaDB thành một dấu `\` thật theo sau là ký tự đại diện; `get_all` cũng không thêm được mệnh đề `ESCAPE`.
- Vì vậy "LIKE có escape" và "`frappe.get_all`" của dòng 487 không cùng đúng được; tiêu chí nghiệm thu (AC-50) thắng.
- Tính chất bỏ quyền mà ADR-034 đòi vẫn giữ: `qb` không kiểm quyền; `test_agent_roles_unchanged` chứng minh tiền đề (`has_permission("Error Log", "read")` của agent là False mà vẫn có dòng).
- Test giết các đột biến đã thử: bỏ từng phép thay escape, đặt phép thay `\` cuối cùng, đổi `|` thành `&` hoặc bỏ một vế khớp.

### Phát hiện (chỉ blocker/major)

Không có blocker, không có major.

minor | — | — | 3 điểm nhỏ: (a) `system_read.py:52` thêm `name desc` làm phép xếp phụ mà thiết kế không nhắc (vô hại, giữ thứ tự ổn định); (b) `limit` không được kiểm kiểu, `True` hay `"5"` không bị từ chối ở đây (tầng công cụ mới là biên đầu vào); (c) chữ lỗi của `limit`, `keyword` do dev đặt vì thiết kế không cho chữ | tùy dev

### Review checklist (10)

1. đạt (trừ điểm nhỏ (a)) 2. đạt 3. đạt (RED rồi GREEN; hai biên của thời gian, `limit`, `keyword`, phép cắt 2000 ký tự; không skip) 4. đạt (không test cũ nào đổi; `NOW` cố định năm 2001 và `now_datetime` được patch; dòng gieo bị xóa bằng `frappe.db.delete` trong cleanup vì Error Log là MyISAM, rollback không xóa) 5. đạt 6. đạt (từ khóa có tham số; đường bỏ quyền theo ADR-034; `method`, `error` được che) 7. đạt (hai module mới; chữ ký và khóa trả về khớp Returns) 8. đạt (không dòng nào quá 110 ký tự; docstring khớp mã) 9. đạt 10. đạt (`feat(agent): … (FEAT-007)`, một commit, không trailer AI)

## Không kiểm được từ diff — kết luận của tech-lead

- Reviewer không chạy test → tech-lead chạy sau merge trên `team/FEAT-007` @ `95d44d4` (dưới khóa site): `test_system_read` `Ran 8 tests in 1.404s OK`, `test_architecture` `Ran 112 tests in 6.250s OK`. Việc dọn của `pin_agent_roles` khi phiên còn là `AGENT_USER`: hai lần chạy (dev, tech-lead) đều xanh và các module chạy sau trong cùng lượt giữ khóa (`test_architecture`) không lệch vai trò → không phải lỗ.
- Lint: `cmd.lint` trên `team/FEAT-007` @ `e920c08` (đã gồm T36): chỉ `ruff-format` đỏ ở `erp_ai/test_change_decision.py` (nợ nền); hai file của T36 sạch.
- `since`/`until` dạng chuỗi làm hàm này ném `TypeError`: việc đổi chuỗi sang datetime thuộc task công cụ đọc Error Log của đợt 1 (U6b). Không chặn T36; chuyển team-leader ghi vào kế hoạch đợt 1 như một dòng Receives của task đó.
- Chữ thiết kế cần sửa (designer, không chặn): `design.md:487` ghi `frappe.qb`; luật kiến trúc ADR-034 (grep `ignore_permissions` / `frappe.get_all("Error Log"` trong `tools/`) cần bắt cả dạng `frappe.qb.DocType("Error Log")`.

## deferred

- 3 điểm nhỏ ở trên; điểm (b) được xử lý ở tầng công cụ (U6b).
