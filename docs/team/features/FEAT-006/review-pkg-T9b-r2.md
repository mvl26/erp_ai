# Review package FEAT-006 T9b, vòng 2 (scoped re-review)

Repo: `/home/miyano/frappe-bench/apps/erp_ai`. FIX_BASE=1a870d5; head=team/FEAT-006-task-9b-rework1 (566f796).
Lệnh diff vòng sửa (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai diff 1a870d5..team/FEAT-006-task-9b-rework1`
Diff toàn task: `git -C /home/miyano/frappe-bench/apps/erp_ai diff 8a1bd31..team/FEAT-006-task-9b-rework1`
Stat vòng sửa: erp_ai/agent/routing.py (+5 -4), erp_ai/agent/test_routing.py (+13), erp_ai/erp_ai_agent/doctype/erp_ai_setting/test_erp_ai_setting.py (+7). Trong 4 touchpoint.

Findings vòng 1 (nguyên văn, cần đánh dấu ADDRESSED / NOT ADDRESSED):
1. major | STD-ERR-3 | erp_ai/agent/routing.py:287-290 | Thông báo trống bảo người quản trị "dán lại JSON mặc định (DEFAULT_ROUTING_RULES)": hằng Python mà người quản trị không thấy; trường không có default, description và docs không chứa nó; thông báo còn che cách đơn giản nhất là bản đã lưu không đổi. | Bỏ tên hằng; nói cấu hình đã lưu chưa đổi, tải lại trang giữ được; chỉ cách khôi phục mặc định ở nơi người quản trị tới được.
   Quyết định tech-lead (không mở rộng touchpoint): thông báo (a) không nhắc tên hằng, (b) nói bản đã lưu chưa đổi và tải lại trang, (c) chèn chính văn bản JSON mặc định vào thông báo; giữ cụm "JSON mặc định".
2. minor | — | routing.py:286 | `(raw or "").strip()` ném AttributeError (500) với giá trị không phải chuỗi, thay vì ValidationError (STD-ERR-2). | kiểm isinstance(raw, str) trước strip.

Ghi chú của vòng 1 mà tech-lead đã xử lý: loader trả `{}` cho cấu hình có khóa tiền tố rỗng là chủ đích (design 3.3 "Bộ nạp trả {} khi cấu hình sai"; chỉ ghi thẳng DB mới tới được); design.md 3.3 sẽ được bổ sung 2 hàng lỗi mới sau khi merge (ngoài touchpoint của T9b).
Chỉ chấm phạm vi vòng sửa (`FIX_BASE..HEAD`); ghi chú ngoài phạm vi vào `deferred`.
