# Review package FEAT-006 T7, vòng 2 (scoped re-review)

BASE=686aa3f; head=team/FEAT-006-task-7 (3388d50, một commit squash thay cb7c008).
Chỉ xét fix: `git -C /home/miyano/frappe-bench/apps/erp_ai diff cb7c008..3388d50` (toàn bộ vẫn là `git diff 686aa3f..3388d50`, 2 file).

Findings vòng 1 cần đánh dấu ADDRESSED / NOT ADDRESSED:
1. major | STD-TEST-2 | test_routing.py:87-96,128 | D/E bỏ qua dùng DEFAULT_CATEGORY_MAPPING có nhóm rỗng nên test không phát hiện việc lấy nhóm từ ánh xạ; cần ánh xạ mồi cho D/E.
2. major | STD-TEST-2 | test_routing.py:104-106 | A/B/C/F chỉ chạy với team_exists=True, is_excluded_team=False; cần ca ngược để ghim "như hiện nay".
Minor dev đã làm: comment nguồn gốc `_normalize`; ca `test_de_config_key_case_and_spaces`.
Dev báo đã phá mã tạm để chứng minh test mới đỏ (rồi hoàn tác); kiểm test hiện tại có thực sự đỏ nếu mã bị phá như vậy (đột biến trong đầu).
Ngoài phạm vi → `deferred`.
