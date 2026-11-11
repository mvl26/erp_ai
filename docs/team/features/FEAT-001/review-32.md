# review-32 — FEAT-001 T19 (bằng chứng khóa API không rò rỉ)

Verdict: approve (2 rounds). Round 1 request-changes: major STD-TEST-8 (sink `frappe.logger` không được bắt trên đường ngoại lệ lạ) + 4 minors; chi tiết: review-raw-T19.md. Round 2 (FIX_BASE=d0a125b, head 84e794c): ADDRESSED (minor 3, 4 deferred sang T28).
Mã sản phẩm không đổi (không tìm thấy rò rỉ). Mutation (ghi `exc` vào warning) làm test đỏ `{'frappe.logger': 1} != {}`.
Diff: `git diff 466648c..team/FEAT-001-task-19`; merge b2fdf26.
cmd.test (qua dev T28, cây gồm T19): `--app erp_ai` Ran 304 tests OK hai lần liên tiếp.
Counts HD Team/HD Ticket/User/ERP AI Log/Error Log trước = sau (4/3/8/0/195).

## deferred
- ERP AI Log search chỉ thấy bản ghi của chính test (bằng chứng thật cần runner T28/T29).
- test_gateway nhập erp_ai.agent.run_log (phụ thuộc ngược trong test).
- Không có test nào chạy đường `send_notice` (429/quota) nên `logger.info` chưa được thử.
- Dữ liệu rò: Error Log tăng từ 145 lên 195 do các lần chạy mutation của dev T19 (lần 1); chưa dọn vì không được phép xóa; cần người xử lý.
