Feature: BUG-002
Stage: build
Author-agent: tech-lead
Date: 2026-11-12
Approved-by:

# Tasks BUG-002

Cỡ M, nhánh `team/BUG-002` (từ `team/FEAT-002` + merge `team/BUG-001`). Bug-fix: 19 test đang đỏ trên site `miyano` là bằng chứng tái hiện (RED dán trước khi sửa). Chạy tuần tự T1 -> T2 -> T3 (cùng site dùng chung; chỉ một dev chạy bench một lúc). Không đổi mã sản phẩm; cần đổi -> `DESIGN_CONFLICT`.

Preflight: cặp task chung tệp/giao diện: T1/T3 có thể cùng chạm helper test dùng chung nếu có -> chạy tuần tự, T3 phụ thuộc T1, T2. Không mâu thuẫn tự thân.

- [x] T1 — test_tasks.TestCheckPrivilegeEscalation tự dựng trạng thái (Has Role của agent đặt về tập cho phép trong transaction test, log/cấu hình test tự tạo; rollback) — files: erp_ai/tests/test_tasks.py — test: erp_ai/tests/test_tasks.py — depends: —
- [x] T2 — test_erp_ai_accuracy (TestAccuracyTenLogSample...) lọc dòng log theo bản ghi/khoảng thời gian của chính test, độc lập log và khóa thật — files: erp_ai/erp_ai_agent/report/erp_ai_accuracy/test_erp_ai_accuracy.py — test: erp_ai/erp_ai_agent/report/erp_ai_accuracy/test_erp_ai_accuracy.py — depends: —
- [x] T3 — điều tra rò commit ngầm (DDL auto-commit trong test_install/test_handlers ghi thật cấu hình/role xuống site): chỉ khi tái hiện bằng ảnh chụp trước/sau, sửa test để không rò (+ test chứng minh); không tái hiện -> báo bằng chứng, không sửa — files: erp_ai/tests/test_handlers.py, erp_ai/tests/test_install.py — test: erp_ai/tests/test_handlers.py, erp_ai/tests/test_install.py — depends: T1, T2

Progress T1: BASE=b8f9485228d2a8d2873e58bdac329b429e5a43b1 (team/BUG-002), nhánh task team/BUG-002-task-1
Progress T2: BASE=f433fe9da7705d0a3bd112a24dd8838f1d794122 (team/BUG-002), nhánh task team/BUG-002-task-2
Progress T3: BASE=3baa88ba60e13faa67075fbd6e1c697da37e4648 (team/BUG-002), nhánh task team/BUG-002-task-3

Receives/Returns: không có hàm mới; các test nhận site `miyano` với dữ liệu sống và trả kết quả xanh không phụ thuộc dữ liệu đó.

Tiêu chí chung:
- RED trước (19 test đỏ, dán đầu ra), XANH sau; không weakening, không skip/xfail, không xóa assertion.
- Mỗi test để lại site nguyên vẹn: ảnh chụp `ERP AI Setting`, `Has Role` của agent, số đếm HD Team/HD Ticket/ERP AI Log/Comment/HD Form Script trước = sau.
- Toàn bộ `cmd.test` trên `team/BUG-002` sau merge: `Ran >=591 ... OK`.

One-file-one-owner: test_tasks.py -> T1; test_erp_ai_accuracy.py -> T2; test_handlers.py, test_install.py -> T3.
