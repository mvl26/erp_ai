# Review package FEAT-006 T9, vòng 3 (scoped re-review)

BASE=8c5af9c; head=team/FEAT-006-task-9 (989c37d; thêm một commit lên 1e3f45d).
Chỉ xét fix: `git -C /home/miyano/frappe-bench/apps/erp_ai diff 1e3f45d..989c37d` (toàn bộ vẫn là `git diff 8c5af9c..989c37d`, 2 file).

Finding vòng 2 cần đánh dấu ADDRESSED / NOT ADDRESSED:
1. major | STD-TEST-8 | test_routing.py:393,451 (routing.py:183-184) | mới kiểm bảo vệ đầu tiên của `assignees.<cat>`; thiếu ca cho `default` không phải chuỗi/thiếu và `prefixes` không phải object, cả bộ kiểm (ValidationError) lẫn bộ nạp (không ném, `{}`).
Minor dev đã làm: siết thông điệp ca "importance root list".
Dev báo phá từng bảo vệ để chứng minh đỏ (AttributeError ở :187; KeyError 'default'), rồi hoàn tác. Chỉ có thay đổi ở test_routing.py.
Bằng chứng dev: `erp_ai.agent.test_routing` 31 OK; `cmd.test` 710 OK; lint pass.
Ngoài phạm vi -> `deferred` (đã có: routing.py:202-203 `departments.<d>` team/head).
