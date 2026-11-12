Feature: BUG-002
Stage: intake
Author-agent: team-leader
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Intake BUG-002 — Test của FEAT-001 phụ thuộc dữ liệu sống của site, đỏ khi site có dữ liệu dùng thật

- Yêu cầu gốc: phát hiện khi verify FEAT-002 (`docs/team/features/FEAT-002/acceptance.md`, bảng "Lỗi ghi nhận", dòng major BUG-002); người đã đồng ý mọi đề xuất của đội để chạy xong FEAT-002 và FEAT-003 (2026-11-12: "tôi đồng ý mọi đề xuất").
- Nguồn: hội thoại / acceptance FEAT-002
- Loại việc: bug
- Playbook: bug-fix
- Size: M
- Mode: decide
- Lý do chọn playbook/cỡ: Hành vi lệch chuẩn STD-TEST-6 (test phải tự dựng dữ liệu, không phụ thuộc dữ liệu sống) và tái hiện được — trên site `miyano`, `bench --site miyano run-tests --module erp_ai.tests.test_tasks` → `Ran 33 … FAILED (failures=12, errors=3)` và module `erp_ai.erp_ai_agent.report.erp_ai_accuracy.test_erp_ai_accuracy` → `Ran 13 … FAILED (failures=4)`, giống hệt trên code `team/FEAT-001` cùng dữ liệu site (log so sánh `cur_*.log` / `f001_*.log` trong scratchpad, acceptance FEAT-002 mục "Kiểm chung"); cỡ M vì chạm 2–4 tệp test (`erp_ai/tests/test_tasks.py:172-301`, `erp_ai/erp_ai_agent/report/erp_ai_accuracy/test_erp_ai_accuracy.py`, có thể `erp_ai/tests/test_handlers.py:234`, `erp_ai/tests/test_install.py:247,255`) và có một câu hỏi điều tra (ý 3 dưới đây), không đổi schema/API.
- Skill tạm: không cần
- Ngân sách: max_agents_per_feature = 10; feature_budget_usd = không giới hạn

## Tái hiện (2026-11-12, site `miyano`)
- Thông báo lỗi chính:
  - `frappe.exceptions.ValidationError: User 'ai.agent@miyano.com.vn' already has the role 'System Manager'` (3 error)
  - `AssertionError: Expected 'send_alarm' to not have been called. Called 1 times.` (5), `2 != 1` (5), `4 != 3`, `0 != 5`
  - `'ERP AI Agent' not found in 'Tài khoản agent có role ngoài danh sách cho phép: thừa role Academics User, …'`
  - accuracy: `Lists differ: [{'category': 'A', 'predictions': 0, …}] != []`, `11 != 10`
- Dữ liệu sống làm test đỏ: tài khoản agent có 99 role (97 role thêm bằng một lần lưu User lúc 11:21 trong phiên quản trị của người — không phải do test); `ERP AI Log` có dòng thật từ phiếu 43067/43068; bảng khóa có dòng thật "Chính".

## Kết quả mong đợi
1. Toàn bộ `bench --site miyano run-tests --app erp_ai` xanh bất kể dữ liệu sống của site (role thật của tài khoản agent, log thật, khóa thật, cấu hình thật), giữ nguyên ý nghĩa từng test.
2. Test tự dựng trạng thái cần thiết trong transaction của nó (vd đặt role của agent về đúng tập cho phép trong test rồi rollback; lọc log theo bản ghi test tạo hoặc khoảng thời gian riêng) và không để lại thay đổi nào trên site.
3. Điều tra (QA ý 3): lúc 13:49–13:51 site có `permission_level = L0` mà không rõ nguồn; có lượt chạy test lúc 13:36/13:37. Các commit trong mã app đã có `if not frappe.flags.in_test` (`erp_ai/agent/runner.py:73-74`, `erp_ai/agent/run_log.py:31-32`), nhưng MariaDB tự commit khi có DDL (vd `create_custom_fields`/ALTER TABLE trong `ensure_setup` mà test gọi). Dev kiểm có đường "commit ngầm" nào làm thay đổi cấu hình/role của test (vd `test_handlers.py:234` đặt L0, `test_install.py:247,255` đặt L2/NULL) bị ghi thật xuống site không; nếu có, sửa test để không rò (và test chứng minh).

## Phạm vi
- Trong: các tệp test nêu trên và helper test dùng chung; nếu cần, một chỉnh nhỏ để tách phần DDL khỏi transaction của test.
- Ngoài: đổi hành vi sản phẩm (`tasks.check_privilege_escalation`, report accuracy, install); dọn dữ liệu site (role thừa, cấu hình, Error Log) — việc của người.

## Ràng buộc
- Như FEAT-001/FEAT-002: commit local trên `team/BUG-002`, không push, không đụng `develop`/`main`; G1–G4 tắt, G5 bật.
- Nhánh: `team/BUG-002` tạo từ `team/FEAT-002` (sau commit As-Built của FEAT-002), rồi merge `team/BUG-001` vào (đưa sửa lỗi hết credit và `docs/team/defects.md` vào cùng một dòng nhánh); FEAT-003 sẽ build trên `team/BUG-002`.
- Không đổi cấu hình `ERP AI Setting`, role hay dữ liệu thật trên `miyano`. Nếu một lần chạy test của đội làm đổi chúng, khôi phục đúng ảnh chụp trước lần chạy và báo lại.
- Không in khóa API; không ghi email cá nhân vào artifact.

## Đổi cỡ (nếu có)
- —
