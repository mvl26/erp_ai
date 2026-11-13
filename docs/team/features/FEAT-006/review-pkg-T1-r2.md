# Review package FEAT-006 T1, vòng 2 (scoped re-review)

BASE=d8fb3e9; head=team/FEAT-006-task-1 (a759792, một commit đã squash từ 57f7d4a + 4ecde9f + sửa).
Chỉ xét fix: so cây a759792 với cây của 4ecde9f (vòng 1, đã review):

    git -C /home/miyano/frappe-bench/apps/erp_ai diff 4ecde9f..a759792

Tính ra nội dung toàn bộ vẫn là `git diff d8fb3e9..a759792` (9 file, cùng touchpoint).

Findings vòng 1 cần đánh dấu ADDRESSED / NOT ADDRESSED:
1. major | STD-TEST-5 | test_agent_runner.py:550-551 | ca bị nới (assertNotIn thay vì khớp chính xác `value_after` và `actions`).
2. major | STD-NAME-6 | test_agent_runner.py:537,572 | tên test nói applied_zero trong khi assertion là applied == 1.
3. major | STD-GIT-2 | commit wip 57f7d4a vào lịch sử | squash thành một commit `feat(routing): ... (FEAT-006)` (kiểm `git log --oneline d8fb3e9..a759792`).
Minor: dev đổi 2 comment ADR-019 → ADR-020 QĐ 1/QĐ 6; không đổi chữ ký `_route` (chờ T19/T20 thêm `auto_assign, subject`); trùng LINKED_DOCTYPES để T16.
Ngoài phạm vi: ghi chú mới (nếu có) vào `deferred`, không mở rộng vòng.
Đầu ra thật từ tech-lead (chạy lại sau khi sửa): xem journal/review-01.md sau khi merge.
