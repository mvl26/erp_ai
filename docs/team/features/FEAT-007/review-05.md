Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 05 — FEAT-007 T5

- Diff: `git diff aff309d4d44b6ca7dc387eafd8b90f5d2971ee45..5b3fe27be4e8fc3381a1692f1b07c02bca9d7853` (đầu nhánh task khi merge; merge `631fa36` trên `team/FEAT-007`)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve

## Vòng 1 — approve

- Range: `aff309d..5b3fe27` (1 commit, 3 file, +33/−2), đúng 3 file của touchpoints.
- Bằng chứng của dev: RED (`erp_ai.tests.test_install`, trước khi sửa JSON) `FAIL: test_instructor_can_report_on_log (erp_ai.tests.test_install.TestFeat007Migrate.test_instructor_can_report_on_log)`, `AssertionError: 0 != 1`, `Ran 37 tests in 52.260s`, `FAILED (failures=1)`; `cmd.migrate` từ worktree dev xong (`Queued rebuilding of search index for miyano`); GREEN `test_install` `Ran 37 tests in 44.623s OK`, `test_erp_ai_log` `Ran 10 tests in 12.773s OK`, `test_architecture` `Ran 112 tests in 5.326s OK`, `test_doctype_descriptions` `Ran 12 tests in 0.580s OK`.
- Kết luận của reviewer: DocPerm thứ ba là `ERP AI Instructor` chỉ có `read=1`, `report=1` (cờ khác vắng mặt nên bằng 0), permlevel 0, không `if_owner`. Option `entry_type`, `trigger` không đổi. Commit ghi lý do nới tập role (NFR-8, STD-TEST-5).
- Bốn điểm tech-lead hỏi:
  - Test cũ còn chặt như trước: có. `test_no_role_can_write_or_delete` (`test_erp_ai_log.py:129`) chỉ nới tập role; vòng kiểm write/delete/submit/cancel/amend và các khẳng định cho System Manager, Agent giữ nguyên, nay phủ cả dòng mới.
  - Test mới đỏ khi có cờ thừa: có. `test_install.py:687-708` so đúng 13 quyền với `("read","report")` viết thẳng, trên dòng đã lưu lẫn trên quyền Frappe thật sự tính; kiểm đúng một dòng, permlevel 0, không `if_owner`. Bỏ `select` là vô hại (Frappe coi `select` nằm trong `read`, `permissions.py:193-197`).
  - Đồng bộ trên site đã cài mà không tăng `modified`: có. Frappe 15.126.1 nhập lại DocType khi hash file khác `migration_hash` (`import_file.py:132-140`); ba commit trước của file này cũng không tăng `modified` mà vẫn đồng bộ.
  - `report` cho gì ngoài đọc dòng (STD-SEC-4): không gì đáng lo. Report View và Script/Query Report còn cần `roles` của chính Report; xuất file bị `can_export` chặn phía server (`export=0`); in và email bằng 0. Instructor thấy mọi dòng (gồm chữ phiếu, lập luận) là do `read=1`, thiết kế đã nhận (`design-w0-fixes.md:153, 162`).

## Phát hiện (chỉ blocker/major)

Không có.

minor | — | — | 1 điểm nhỏ: `design-w0-fixes.md:160` đặt khẳng định "Instructor chỉ có read, report" trong `test_no_role_can_write_or_delete`, dev đặt ở `TestFeat007Migrate::test_instructor_can_report_on_log`; tiêu chí của `tasks.md` đạt, độ phủ như nhau | tùy dev

## Review checklist (10)
1. đạt 2. đạt 3. đạt (đỏ trước `0 != 1`; cờ thừa và dòng trùng được phủ; không skip) 4. đạt (test cũ không bị nới; test mới xóa và trả lại cache quyền, lớp gọi `keep_agent_settings`) 5. không áp dụng 6. đạt (quyền kiểm phía server) 7. đạt (chỉ thêm một dòng DocPerm; lùi commit rồi migrate thì dòng mất) 8. đạt 9. không áp dụng 10. đạt (`feat(log): … (FEAT-007)`, không trailer)

## Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| Trên site khác `miyano`, nếu ERP AI Log đã có dòng `Custom DocPerm` thì các dòng đó thay toàn bộ DocPerm của DocType (`meta.py:553-566`), dòng Instructor mới sẽ không có hiệu lực | Trên `miyano`: `test_instructor_can_report_on_log` đọc quyền hiệu lực từ site và xanh sau `cmd.migrate`, nên không có Custom DocPerm che. Với site khác: việc kiểm trước khi deploy (`select count(*) from "tabCustom DocPerm" where parent='ERP AI Log'`), ghi cho `/team:verify` và As-Built; không chặn tick. |
| Test, migrate, lint sau merge | Tech-lead chạy từ worktree `feat-007` sau merge `631fa36`: `cmd.migrate` lần 1 hỏng `LockTimeoutError: Failed to aquire lock: bench_migrate` (phiên khác đang migrate), lần 2 exit 0; `test_erp_ai_log` `Ran 10 tests in 6.679s OK`; `test_install` `Ran 37 tests in 67.041s OK`; `test_doctype_descriptions` `Ran 12 tests in 0.582s OK`; `test_architecture` `Ran 112 tests in 5.349s OK`. `cmd.lint`: chỉ `ruff-format` đỏ ở `erp_ai/test_change_decision.py` (nợ nền). |

## deferred

- (minor, tùy dev) 1 điểm nhỏ ở trên.
- (verify / As-Built) kiểm `Custom DocPerm` của ERP AI Log trên site đích trước khi deploy.
