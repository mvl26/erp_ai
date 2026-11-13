# Review package FEAT-006 T14, vòng 2 (scoped re-review)

Repo: `/home/miyano/frappe-bench/apps/erp_ai`. FIX_BASE=2f639c0; head=team/FEAT-006-task-14-rework1b (809fac6; đi qua aee788d của nhánh -rework1).
Lệnh diff vòng sửa (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai diff 2f639c0..team/FEAT-006-task-14-rework1b`
Diff toàn task: `git -C /home/miyano/frappe-bench/apps/erp_ai diff b74303f..team/FEAT-006-task-14-rework1b`
Commit vòng sửa: aee788d (route_ticket.py, test_route_ticket.py), 809fac6 (test_agent_runner.py).
Touchpoint T14: erp_ai/agent/tools/route_ticket.py, erp_ai/agent/tools/test_route_ticket.py; tech-lead mở rộng thêm đúng 1 file `erp_ai/agent/test_agent_runner.py`, CHỈ sửa kỳ vọng `after` (bỏ khóa `ai_complexity`/`ai_importance` không đổi khỏi 3 test) vì hành vi mới "before/after chỉ trường đã đổi" làm 3 test đó đỏ (STD-TEST-5, cùng kiểu mở rộng T1/T6/T11 đã được chấp nhận; ghi ở progress.md "Đổi touchpoint").

Findings vòng 1 (nguyên văn; đánh dấu ADDRESSED / NOT ADDRESSED):
1. major | STD-TEST-2 | route_ticket.py:44,49 | `before`/`after` liệt kê mọi trường được ghi thay vì trường đã đổi (ví dụ phiếu đã có `priority="Medium"` vẫn hiện); `test_scores_written_readable_by_agent_role_user` (:112) khóa mục không đổi; `test_before_after_only_changed_fields_and_one_save` (:209) tên có "only" nhưng không khẳng định thiếu trường không đổi. | Chỉ giữ trường `doc.get(field) != value` trong `before`/`after`, vẫn ghi `values` và save một lần; thêm ca phiếu đã `priority="Medium"` khẳng định `"priority"` không có trong before/after.
2. major | STD-TEST-8 | test_route_ticket.py:176-179 | Test giả `has_permlevel_access_to` từ chối `priority` và `ai_score_reason` bất kể `permission_type`; ca role thật (:159) không có cả đọc lẫn ghi ở permlevel 8; đổi `"write"` thành `"read"` ở route_ticket.py:38/:41 mà mọi test vẫn xanh. | Giả chỉ từ chối khi `permission_type == "write"`, còn `read` đi qua hàm gốc; thêm ca dấu từ chối khi chỉ thiếu ghi trên `ai_classified_by` mà vẫn đọc được.
3. minor (a) :207 mồi `priority` trùng giá trị mặc định (đổi `_ticket(priority="Low")`); (b) comment :285 "L0 writes no score" sai; (c) SLA `Default` của site không bị cách ly (dev bỏ qua, các test phụ thuộc nay đặt `priority` tường minh).

Quyết định tech-lead: "đã đổi" = giá trị khác trước, không phải "đã ghi"; thiếu quyền ghi ở hai trường dấu (`ai_classified_by`, `ai_updated_at`) vẫn từ chối cả lần ghi (design 3.4 sẽ chỉnh sau, ghi `deferred`).

Chỉ chấm phạm vi `FIX_BASE..HEAD`; ghi chú ngoài phạm vi vào `deferred`.
