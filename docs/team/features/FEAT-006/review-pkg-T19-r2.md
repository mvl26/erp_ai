# Review package FEAT-006 T19, vòng 2 (scoped re-review)

Repo: `/home/miyano/frappe-bench/apps/erp_ai`. FIX_BASE=0f6e89f; head=team/FEAT-006-task-19-rework1 (c4d821f; dev gom nhánh thành MỘT commit từ BASE a62944e, nên không còn commit đỏ ở giữa).
Lệnh diff phần sửa (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai diff 0f6e89f..team/FEAT-006-task-19-rework1 -- erp_ai`
Toàn bộ T19: `git -C /home/miyano/frappe-bench/apps/erp_ai diff a62944e..team/FEAT-006-task-19-rework1 -- erp_ai` (cây mã ngoài 2 file test trên không đổi so với vòng 1).

Finding vòng 1 cần đánh dấu ADDRESSED / NOT ADDRESSED:
1. major | STD-TEST-6 | test_runner_routing.py:183 (`test_l1_no_score_writes_zero_logs_no_score`) + test_agent_runner.py:241 | runner nay đọc `routing_rules` nhưng `RunnerTestBase.setUp` không đặt, nên `assertFalse(predicted_assignee)` và kiểm prompt không có `departments` chỉ qua khi site miyano chưa cấu hình định tuyến. Sửa: thêm `routing_rules=make_routing_rules()` vào `set_agent_settings` của `RunnerTestBase.setUp` (hoặc `RoutingTestBase` + test_agent_runner:241).
2. minor (reviewer) | test L0 chỉ kiểm `ai_complexity`: thêm kiểm `ai_importance`, `ai_score_reason` (dev đã làm).

Mục (b) của vòng 1 ("routing_rules là chuỗi rỗng thay vì NULL thì mỗi lần chạy ghi 'routing_rules không hợp lệ'") do tech-lead xử lý riêng: T9b đã chặn lưu rỗng (bộ kiểm từ chối) và `after_migrate` gieo mặc định; ghi vào `deferred`, không thuộc vòng này.
Chỉ xét diff sửa; ghi chú ngoài phạm vi vào `deferred`.
