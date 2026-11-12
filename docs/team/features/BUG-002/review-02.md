Feature: BUG-002
Stage: review
Author-agent: reviewer
Date: 2026-11-12
Approved-by:

# Review 02 — BUG-002 T2 (test báo cáo độ chính xác cách ly khỏi log sống)

- Verdict: approve (vòng 1, không làm lại; max_rework=3)
- Lệnh diff: `git diff f433fe9..team/BUG-002-task-2` (một tệp, +3 dòng: `erp_ai/erp_ai_agent/report/erp_ai_accuracy/test_erp_ai_accuracy.py`).
- Bằng chứng dev: RED `Ran 13 tests ... FAILED (failures=4)` (`Lists differ: [{'category': 'A', 'predictions': 0, ...}] != []`, `2 != 1`); GREEN `Ran 13 tests in 0.410s ... OK`.
- Cách sửa: setUp đổi `entry_type` của mọi dòng `classify` hiện có thành `reason` trong transaction của test (rollback ở cleanup); báo cáo chỉ đọc đúng truy vấn `_fetch_predictions` nên cô lập đầy đủ (reviewer xác nhận).
- Ảnh chụp site trước/sau: không đổi ngoài `Comment` +N (bootstrap runner).
- Merge: `3baa88b` trên `team/BUG-002`.

## deferred
- Rủi ro còn lại (chuyển T3): nếu có commit ngầm/DDL chen vào giữa test thì UPDATE sẽ ghi thật. T3 thêm số đếm dòng `classify` của ERP AI Log vào ảnh chụp để chứng minh không rò.
- minor: UPDATE quét toàn bảng (entry_type không có index), khóa hàng đến khi rollback; rủi ro thấp.
