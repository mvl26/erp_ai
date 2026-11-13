# review-34 — FEAT-001 T28 (runner: chốt tài khoản, điều kiện dừng, phân loại L0)

Verdict: approve (3 rounds). Round 1 request-changes: 3 major (STD-TEST-8 seed bằng mặc định 5; STD-TEST-2 AC-9 thiếu comment count/ai_*; STD-DESIGN-4 RUN_DEADLINE_S) + 4 minors; review-raw-T28.md. Round 2 request-changes: major STD-ERR-4 mới (skip entry ticket=None mất tên phiếu); review-raw-T28-r2.md. Round 3 (FIX_BASE=d1c88e9, head 2273b1e): approve.
Nợ bắt buộc đã xử lý: trạng thái cầu dao sống sót khi lượt hỏng (commit trong `finally` của `_call_model` chỉ khi not in_test, không rollback ở except; hai test đỏ khi bỏ commit hoặc thêm rollback). Chấp nhận sửa 1 test của test_handlers.py ngoài touchpoint (spec đổi: runner dừng khi tắt).
Diff: `git diff b2fdf26..team/FEAT-001-task-28`; merge d5e0eef.
cmd.test (qua dev, cây gồm T27+T28): `--app erp_ai` Ran 311 tests OK (hai lần ở round 2 và một lần ở round 3).
Counts HD Team/HD Ticket/User/ERP AI Log/Error Log trước = sau (4/3/8/0/195).

## deferred (T29/T30)
- Ghi tool và cập nhật dòng `classify` (`applied`, `value_*`) phải cùng lúc hoặc ghi log trước: commit của `_call_model` sau mỗi lượt cũng commit ghi tool của lượt trước; ngoại lệ giữa chừng để lại ticket đã đổi với `applied=0`. `applied = 1` chỉ khi `after` không rỗng (nợ T25).
- `except Exception` nuốt deadlock 1213 nên retry của Frappe không chạy (chấp nhận theo D-20).
- Khi chạy lượt hỏng giữa chừng, thay đổi chưa commit vẫn được framework commit khi job trả về thường.
