Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 66 — FEAT-004 T66

- Diff: `team/FEAT-004-task-66` (head 2a71c92), base 02493b3 (head của T65, review riêng)
- Vòng: 1
- Verdict: approve

Lệnh git đã chạy (chỉ đọc):
```
git log --oneline 02493b3..team/FEAT-004-task-66        # 1 commit: 2a71c92
git diff --stat 02493b3..team/FEAT-004-task-66          # 3 file, +157 -4
git diff 02493b3..team/FEAT-004-task-66
git show team/FEAT-004:docs/team/features/FEAT-004/tasks.md | grep -n -A6 '^- \[ \] T66'
git show 02493b3:erp_ai/agent/agent_write_guard.py
git grep -n 'allow_agent_write\|AGENT_WRITE_FLAG\|erp_ai_agent_write_allowed' team/FEAT-004-task-66 -- erp_ai
git grep -n 'LOG_DOCTYPE\|"ERP AI Log"' team/FEAT-004-task-66 -- 'erp_ai/**/*.py'
git log -1 --format=%B 2a71c92
```
Đọc thêm ngoài diff (mỗi rủi ro một lần): `docs/team/adr/ADR-023.md` QĐ 5, 6 và Ràng buộc; `plan.md` mục "Chèn CHG-001" (dòng 217, 241, 247, 254); `frappe/model/document.py:223-259` (cờ `doc.flags` khởi tạo trước `init_from_dict`), `:415-430` (thứ tự `check_permission` → `_validate_links` → `before_insert`), `:1273-1300` (`before_validate` luôn chạy, `validate` bị bỏ khi `flags.ignore_validate`); `frappe/model/delete_doc.py` (`on_trash` bị bỏ khi `for_reload` hoặc `ignore_on_trash`).

Bằng chứng của dev: RED `test_run_log` 16 test, 10 failure (4 hook, 5 đường ghi "PermissionError not raised", test cờ `[None] != [True]`); GREEN `test_run_log` 16 OK, `test_erp_ai_log` 7 OK, `test_transitions` 42 OK, `test_architecture` 128 OK, `test_agent_write_guard` 5 OK; `test_runner_status` 39 test, ba lần chạy đều có lỗi `QueryDeadlockError`, chưa lần nào sạch. Reviewer không chạy test (site dùng chung).

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| — | — | — | Không có blocker/major. | — |

minor | — | — | 4 điểm nhỏ: (1) STD-SEC-4 `erp_ai_log.py:11` chặn lưu đặt ở `validate`, Frappe bỏ `validate` khi `doc.flags.ignore_validate` (`document.py:1289`) còn `before_validate` vẫn chạy; chưa thấy đường nào agent gọi được mà bật cờ đó (suspected) — chuyển/thêm `refuse_agent_write` vào `before_validate` và thêm subTest `doc.flags.ignore_validate=True; doc.save(ignore_permissions=True)` thì đóng hẳn; (2) STD-TEST-6 `test_run_log.py:320,323` hai subTest `frappe.client.insert` chỉ tới được hook khi tài khoản agent thật có quyền create ERP AI Log (role sống trên site, `check_permission` chạy trước `before_insert`), nếu role của agent bị thu (QĐ 6 gạch 3) test đỏ vì lý do khác chứ không vì bộ chặn; (3) STD-DOC-7 `run_log.py:35-36` docstring nói `write_entry` là "the one path by which the agent account may write ERP AI Log" trong khi `runner.py:537` vẫn sửa dòng log bằng `frappe.db.set_value` (không qua controller), nên ghi rõ "the one controller path"; (4) STD-STYLE-5 `test_run_log.py:362` `create=True` trong `patch.object` chỉ cần cho RED, giờ `before_insert` đã có | tùy dev

## Layer 1 — khớp spec
- Returns của T66: controller gọi `refuse_agent_write(self)` ở `before_insert`, `validate`, `on_trash`, `before_rename` (`erp_ai_log.py:8-18`); ERP AI Log không submittable (không có `is_submittable` trong JSON) nên submit/cancel không áp dụng. `write_entry` bọc đúng lần `insert` (`run_log.py:56-58`), commit nằm ngoài khối. Đạt.
- Expect: đủ ba test được nêu tên, cộng `test_every_guarded_hook_refuses_the_agent`. Năm đường (insert, save, delete, `frappe.client.insert` chuỗi JSON có `L`, cờ giả trong dict) đều kiểm thông điệp từ chối riêng của bộ chặn (`assertRaisesRegex(... REFUSAL)`), không phải PermissionError chung, và so ảnh chụp (số dòng + nguyên dòng log) trước/sau.
- Ràng buộc ADR-023 "cờ chỉ đặt trong `run_log.py` và module tool đề xuất": `git grep` cho thấy ngoài `agent_write_guard.py` chỉ `run_log.py:5,57` gọi `allow_agent_write`. Đạt.
- Rủi ro plan dòng 247 (bộ chặn chặn nhầm runner): mã app ghi ERP AI Log ngoài `write_entry` chỉ có `runner.py:537` (`frappe.db.set_value`, không qua controller) nên không bị chặn; xác nhận cuối cần `cmd.test` (xem dưới).
- Không Missing / Extra / Misunderstood; chỉ 3 file trong touchpoints.

## Review checklist (10)
1. Đạt — đủ Returns/Expect của T66, không thêm phạm vi (STD-DESIGN-5, STD-TEST-2).
2. Đạt — 3 file đúng touchpoints, không file mới (STD-DESIGN-1, STD-STRUCT-1).
3. Đạt — RED 10 failure đúng hành vi mới rồi GREEN; có nhánh lỗi (`LinkValidationError` trong khối → cờ vẫn tắt, số dòng không đổi); không skip/xfail (STD-TEST-1, STD-TEST-8, STD-TEST-4).
4. Đạt — không sửa assertion cũ; mỗi đường dùng savepoint + rollback, `commit` bị chặn trong setUp; điểm phụ thuộc role sống của agent ghi ở minor (2) (STD-TEST-5, STD-TEST-6).
5. Đạt — không nuốt lỗi; context manager khôi phục cờ trong `finally` (T65) và test kiểm đường ngoại lệ (STD-ERR-1).
6. Đạt — kiểm theo user phiên, cờ chỉ ở `frappe.flags`, dict client không bật được; điểm `ignore_validate` ở minor (1) (STD-SEC-4).
7. Đạt — `write_entry(**fields)` giữ nguyên chữ ký và giá trị trả; không đổi schema (STD-DESIGN-3).
8. Đạt — tên theo profile, hằng số UPPER_CASE; leftover `create=True` ở minor (4) (STD-NAME-2, STD-STYLE-5).
9. Đạt — không thêm dependency (STD-DEP-1).
10. Đạt — 1 commit `feat(agent): ... (FEAT-004)`, không trailer AI, nhánh `team/FEAT-004-task-66` (STD-NAME-4, STD-NAME-5, STD-GIT-1, STD-GIT-8); không đổi hành vi người dùng thấy nên không cần README.

## Không kiểm được từ diff
- `cmd.test` cả app sau T66: `test_runner_status` chưa có lần chạy sạch (3 lần đều `QueryDeadlockError`), `test_agent_runner` không có trong bằng chứng. Plan bước 9 yêu cầu `cmd.test` xanh sau T67 — tech-lead cần một lần chạy sạch `test_agent_runner` và `test_runner_*` trước khi đánh dấu M5 xong, vì đây là chỗ lộ ra nếu runner ghi Log ngoài `write_entry` dưới tài khoản agent.
- Lint/format (`pre-commit run --all-files`): không có output trong gói review.
- `frappe.desk.form.save.savedocs` và đổi tên thật qua `frappe.rename_doc`: Ràng buộc "Test M5" của ADR-023 liệt kê `savedocs`; T66 không kiểm (task Expect cũng không nêu), `before_rename` chỉ kiểm qua `run_method`. Tech-lead xác nhận T68 phủ các đường này cho mọi DocType của app.
- Có đường nào agent gọi được (tool, `call_method`, Data Import) đặt `doc.flags.ignore_validate` hoặc `delete_doc(..., ignore_on_trash=True)` không — không thấy trong `erp_ai/agent/**` (`git grep` rỗng); đường qua Server Script/System Console ở chế độ toàn quyền thuộc phần chờ người quyết của ADR-023 QĐ 6.

## Deferred
- Không có (vòng 1).
