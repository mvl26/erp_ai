Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 31 — FEAT-007 T31

- Diff: `git diff f7da325..8fc42d5` (nhánh `team/FEAT-007-task-31`, 2 commit `ecab454`, `8fc42d5`; 2 file, +49/−4)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve

## Vòng 1 — approve

- Lệnh đã dùng (chỉ đọc): `git log --oneline f7da325..8fc42d5`; `git diff --stat f7da325..8fc42d5`, `git diff f7da325..8fc42d5`, `git diff --check f7da325..8fc42d5` (exit 0); `git show ecab454 --stat`, `git show 8fc42d5 --stat` (commit message); `git show 8fc42d5:<test file>`, `git show 8fc42d5:erp_ai_accuracy.py`, `git show 8fc42d5:erp_ai_accuracy.json`, `git show 8fc42d5:erp_ai_log.json` (phần `permissions`); `git grep` trong `erp_ai` @ `8fc42d5` (role Instructor, `desk_access` trong `install.py`, chỗ khác ghim `ERP AI Accuracy` hoặc `Custom Role`); `git grep` trong `apps/frappe` (`frappe/desk/query_report.py`: `get_report_doc`, `run`, `_run`; `frappe/core/doctype/report/report.py`: `is_permitted`). Tài liệu: `tasks.md` dòng 1-25 và khối T31; `design.md` mục 3.5.3 (dòng 385-400); `spec.md:182` (AC-20), `:151` (NFR-8); grep AC-20 trong `spec-addendum-*.md` và `design-w0-fixes*.md`.
- Bằng chứng của dev: commit 1 RED `ERROR: test_three_accounts (account='ERP AI Instructor')` `frappe.exceptions.PermissionError: You don't have access to Report: ERP AI Accuracy`, `Ran 39 tests in 3.600s FAILED (errors=1)`; sau khi sửa JSON `Ran 39 tests in 3.517s FAILED (failures=1)`: `FAIL: test_report_record_is_system_manager_only_script_report` `AssertionError: Lists differ: ['System Manager', 'ERP AI Instructor'] != ['System Manager']`. Commit 2 GREEN: `test_erp_ai_accuracy` `Ran 39 tests in 3.788s OK`; `test_architecture` `Ran 112 tests in 3.235s OK`; `test_erp_ai_log` `Ran 10 tests in 1.570s OK`. Đột biến dev báo: thêm ERP AI Agent vào `roles` → `AssertionError: True is not false`.
- Lớp 1 (khớp spec):
  - Đủ: `erp_ai_accuracy.json` thêm `ERP AI Instructor` vào `roles`, đúng dòng Returns và `design.md:395`; `modified` nâng lên `2026-11-14 12:00:02` để `migrate` nạp lại JSON. `TestAccess::test_three_accounts` gọi `frappe.desk.query_report.run` dưới ba tài khoản, mỗi tài khoản đúng một role ngoài các role tự động: đủ Expect và `design.md:662`.
  - Không thừa: chỉ 2 file, đúng touchpoints. Không hiểu sai.
  - STD-TEST-5 cho việc sửa test cũ `test_report_record_is_system_manager_only_script_report` → `test_report_record_is_script_report_for_system_manager_and_instructor`: spec ủng hộ. `spec.md:182` (AC-20) yêu cầu người chỉ có role `ERP AI Instructor` "mở và chạy được báo cáo ERP AI Accuracy"; phép khẳng định cũ `roles == ["System Manager"]` ghim quy tắc trước AC-20, nên đây không phải sửa test cho khớp hành vi sai. `design.md:395` cũng ghi `roles` thêm Instructor. Các addendum không đổi AC-20. Phép khẳng định sau khi sửa vẫn chặt (bằng nhau cả danh sách và thứ tự). Đúng một phép khẳng định đổi; năm phép còn lại của test (`report_type`, `ref_doctype`, `module`, `is_standard`, `has_permission`) giữ nguyên. Lý do AC-20 / NFR-8 / STD-TEST-5 ghi trong message của `8fc42d5`. Lưu ý: NFR-8 (`spec.md:151`) liệt kê một số test cụ thể, test này không có trong danh sách; NFR-8 nói "sửa theo đúng AC tương ứng" và AC-20 là AC tương ứng. DoD (`spec.md:294`) yêu cầu ghi test này vào `acceptance.md`.
- Test đỏ được không (đối chiếu Frappe: `_run` → `get_report_doc` → `Report.is_permitted()` theo Has Role, rồi `has_permission(ref_doctype, "report")`, rồi `execute` → `has_permission(LOG_DOCTYPE, "report", throw=True)`):
  - Subtest Instructor: bỏ Instructor khỏi `roles` → `PermissionError` (đúng RED của dev); bỏ DocPerm `report` của Instructor trên Log (T5) → cũng đỏ.
  - Subtest Agent: chỉ `assertRaises` thì vẫn xanh khi Agent bị thêm vào `roles` (Agent không có `report` trên Log); dev thêm `assertFalse(is_permitted())` nên điều kiện `roles` được ghim riêng.
  - Subtest System Manager: bỏ System Manager khỏi `roles` → đỏ.
  - `_user_with_only` khẳng định tập role thực tế. Độc lập (STD-TEST-6): user tạo trong transaction và rollback ở cleanup; `set_user("Administrator")` ở cleanup; lớp mới gọi `keep_agent_settings(self)`.

### Phát hiện (chỉ blocker/major)

Không có blocker hay major.

minor | — | — | 2 điểm nhỏ: (1) STD-GIT-2: commit `ecab454` đỏ một mình (phép khẳng định cũ, để lại có chủ ý trong lúc chờ `DESIGN_CONFLICT`); khi merge thì squash, hoặc chấp nhận có chủ ý rằng lịch sử có một commit đỏ; (2) STD-TEST-6: `Report.is_permitted()` cho một bản ghi Custom Role của site cho "ERP AI Accuracy" thay `roles` của JSON, nên cả test lẫn hành vi phụ thuộc việc bản ghi đó không có trên site | tùy dev / tech-lead

### Review checklist (10)

1. đạt (AC-20 cho ERP AI Accuracy phủ bằng 3 tài khoản) 2. đạt (2 file trong touchpoints, không file mới) 3. đạt (RED `PermissionError` trên tài khoản Instructor; có nhánh từ chối; không skip/xfail/only) 4. đạt (việc sửa có AC-20 làm căn cứ; phụ thuộc Custom Role ghi ở minor) 5. không áp dụng (không đổi mã chạy thật) 6. đạt (quyền mở đúng theo spec; `execute` vẫn kiểm `report` trên Log phía server) 7. đạt (JSON chuẩn, `modified` đã nâng; không chỗ nào khác ghim `roles` của báo cáo) 8. đạt 9. không có phụ thuộc mới 10. đạt (`type(scope): … (FEAT-007)`, không trailer AI; commit trung gian đỏ: minor)

## Không kiểm được từ diff — tech-lead xử lý trước khi tick

| Mục | Kết luận của tech-lead |
|---|---|
| `cmd.migrate` rồi `cmd.test_one` cho `test_erp_ai_accuracy.py`, `test_architecture.py`, `test_erp_ai_log.py` sau merge | đạt: trên `team/FEAT-007` @ `a3bddb8`, một lần giữ khóa site: migrate exit 0; `Ran 39 tests in 3.655s OK`; `Ran 112 tests in 3.296s OK`; `Ran 10 tests in 1.310s OK` |
| Site `miyano` không có Custom Role cho Report "ERP AI Accuracy" | không truy vấn riêng; `TestAccess::test_three_accounts` xanh sau merge trên `miyano` (Instructor chạy được, `is_permitted()` của Agent sai) nên không có bản ghi nào đang ghi đè theo hướng làm sai kết quả; để `/team:verify` kiểm trên màn hình |
| Đưa test đổi tên (lý do AC-20 / NFR-8) vào danh sách "test bị sửa vì spec đổi" của `acceptance.md` (DoD `spec.md:294`) | chuyển `/team:verify`; đã ghi ở dòng `progress:` của T31 và báo team-leader |
| Cách merge: squash hoặc ghi rõ `ecab454` đỏ một mình (STD-GIT-2) | merge `--no-ff` như mọi task khác, giữ 2 commit; chấp nhận có chủ ý: `ecab454` đỏ ở đúng một test cũ, commit kế `8fc42d5` xanh; ghi ở `tasks.md` |

## deferred

- (minor, STD-GIT-2) lịch sử nhánh có một commit đỏ một mình (`ecab454`).
- (verify) Custom Role của site cho báo cáo; mục `acceptance.md` cho test đổi tên.
