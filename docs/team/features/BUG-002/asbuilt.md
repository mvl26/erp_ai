Feature: BUG-002
Stage: asbuilt
Author-agent: writer
Date: 2026-11-12
Approved-by:

# As-Built BUG-002 — Test của FEAT-001 không còn phụ thuộc dữ liệu sống của site

Bug-fix cỡ M, chỉ đổi test; không đổi mã sản phẩm, schema hay API. Nhánh `team/BUG-002` (từ `team/FEAT-002` + merge `team/BUG-001`).

## Đã đổi gì
- `erp_ai/tests/test_tasks.py` (T1): `TestCheckPrivilegeEscalation` tự dựng trạng thái trong `setUp`, bên trong transaction của test: đặt `Has Role` của tài khoản agent về đúng tập cho phép, đổi chủ sửa của các bản ghi quyền do agent sở hữu về Administrator (`_neutralize_agent_rows()`), tắt Server Script/Webhook do agent sở hữu. Rollback ở cleanup. Assertion giữ nguyên; `test_allowed_roles_do_not_alarm` được mở rộng (thêm role tự động `Desk User`).
- `erp_ai/erp_ai_agent/report/erp_ai_accuracy/test_erp_ai_accuracy.py` (T2): `TestAccuracyTenLogSample` và lớp cùng nền đổi `entry_type` các dòng `classify` có sẵn thành `reason` trong transaction (rollback ở cleanup) để báo cáo chỉ thấy dòng test tự tạo. Kỳ vọng không đổi.
- T3: không có diff (xem Điều tra).
- Mã sản phẩm: không đổi do BUG-002. `erp_ai/gateway/breaker.py` trong diff so với `team/FEAT-002` đến từ merge BUG-001 (xem As-Built BUG-001).

## Kết quả
- Trước sửa trên `miyano`: `test_tasks` `Ran 33 … FAILED (failures=12, errors=3)`; accuracy `Ran 13 … FAILED (failures=4)` (review-01, review-02).
- Sau sửa: `bench --site miyano run-tests --module erp_ai.tests.test_tasks` → `Ran 34 … OK`; module accuracy → `Ran 13 … OK`; `bench --site miyano run-tests --app erp_ai` → `Ran 592 tests … OK` (acceptance BUG-002, verdict accepted). Xanh trên site có dữ liệu thật (tài khoản agent 99 role, `ERP AI Log` 35 dòng).
- Không có skip/xfail mới, không xóa/nới assertion.

## Điều tra rò (intake ý 3)
- Không tái hiện rò từ test. Ảnh chụp site (ERP AI Setting, Has Role của agent, số đếm các DocType chính, băm nội dung) trước = sau từng module và sau toàn suite; chỉ `Comment` +2 mỗi lượt chạy module (dòng `Deleted` của Email Account/Holiday List do bootstrap của test runner, nhiễu đã biết).
- Cơ chế bảo vệ (kiểm tĩnh): các `frappe.db.commit` trong tasks/run_log/runner nằm sau `if not frappe.flags.in_test`; `test_handlers` vá `frappe.db.commit` và rollback ở cleanup; `test_install` vá `frappe.db.updatedb` thành no-op nên không có DDL tự commit.
- `permission_level = L0` thấy lúc 13:49–13:51 chưa quy được nguồn cho lượt chạy test nào. Giả thuyết chưa chứng minh: sửa tay `ERP AI Setting` hoặc `bench migrate`/`after_migrate` chạy `ensure_setup` với mặc định L0. Hiện site là `L3`.

## Việc của người (ngoài phạm vi)
- Tài khoản agent còn 99 role (97 role thêm bằng một lần lưu User, không do test); cần người rà và gỡ role thừa.

## Nợ sau G4
- Hai minor hoãn đã ghi vào `docs/team/debt.md`: `test_tasks.py:339-347` (STD-TEST-5), `test_tasks.py:197` (STD-STYLE-5).
- CHANGELOG: đã thêm dòng `Fixed` (BUG-002). README/tài liệu người dùng: không có hành vi người dùng đổi, không sửa.
