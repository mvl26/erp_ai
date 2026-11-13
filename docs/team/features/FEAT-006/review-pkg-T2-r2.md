# Review package FEAT-006 T2, vòng 2 (scoped re-review, thay gói cũ)

BASE=686aa3f; head=team/FEAT-006-task-2 (60630c4, MỘT commit squash; đã kiểm `git status` sạch).
Lần giao trước sai (commit không chứa bản sửa); lần này toàn bộ bản sửa đã nằm trong commit.
Phần fix (so với vòng 1 đã review, 7388e1d): `git -C /home/miyano/frappe-bench/apps/erp_ai diff 7388e1d..60630c4`. Toàn bộ: `git diff 686aa3f..60630c4` (2 file).

Findings vòng 1 + vòng 2 cần đánh dấu ADDRESSED / NOT ADDRESSED:
1. major | STD-TEST-8 | test_utils.py:186-197 + tests/test_test_utils.py:40-63 | vòng lặp thêm role còn thiếu trong `pin_agent_roles` không test nào chạy; cần ca xóa `Agent` / `ERP AI Agent`, tập ghim đầy đủ, sau doCleanups các dòng bằng `before_rows`.
2. major (suspected) | STD-TEST-6 | `pin_agent_roles` | cache role agent không bị xóa khi `restore` lỗi giữa chừng; sửa: `addCleanup(frappe.clear_cache, user=AGENT_USER)` đứng sau khôi phục (dev báo đã làm, có ca `test_pin_agent_roles_clears_cache_even_when_restore_fails`).
Minor: count check ở restore; tên `SLA_RESPONSE_HOURS_BY_PRIORITY`; ca `| AUTOMATIC_ROLES` kiểm sau doCleanups; xóa Assignment Rule bằng `delete_doc`/dòng con; chốt commit. `PREFIX` trùng `test_agent_runner.py:36` để lại (ngoài touchpoint).
Bằng chứng dev: `erp_ai.tests.test_test_utils` 11 test OK; `cmd.test` 687 OK; Has Role agent 99 trước = 99 sau; ca mới đỏ khi bỏ addCleanup (`Called 0 times`).
