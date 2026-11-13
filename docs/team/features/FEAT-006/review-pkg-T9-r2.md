# Review package FEAT-006 T9, vòng 2 (scoped re-review)

BASE=8c5af9c; head=team/FEAT-006-task-9 (1e3f45d; thêm một commit lên a692a70).
Chỉ xét fix: `git -C /home/miyano/frappe-bench/apps/erp_ai diff a692a70..1e3f45d` (toàn bộ vẫn là `git diff 8c5af9c..1e3f45d`, 2 file).

Findings vòng 1 cần đánh dấu ADDRESSED / NOT ADDRESSED:
1. major | STD-TEST-8 | test_routing.py:379 (routing.py:182-184, 200, 228, 231, 167) | thiếu ca cho (a) `assignees.<cat>` sai dạng; (b) tên bộ phận rỗng; (c) `expected_sla` loại lạ / mục không phải object / khóa lạ `resolution`; (d) giá trị người không phải chuỗi; (e) khóa gốc không phải object (`assignees`/`departments`/`expected_sla` là list, `importance_priority` là list); bộ nạp phải không ném với đầu vào lồng sai.
Minor dev đã làm: ca nạp cấu hình một phần đủ 4 khóa; bộ nạp không kiểm user; comment cũ ở routing.py:82; mặc định có `"[tracecore]": ""`.
Dev báo phá từng dòng bảo vệ để chứng minh đỏ (TypeError/AttributeError/ValidationError not raised), rồi hoàn tác. Kiểm lại bằng đột biến trong đầu: mỗi ca mới có thật sự đỏ khi bỏ đúng dòng bảo vệ của nó không.
Bằng chứng dev: `erp_ai.agent.test_routing` 31 OK; `cmd.test` 710 OK; lint pass.
Ngoài phạm vi -> `deferred`.
