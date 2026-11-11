# Review 29 — FEAT-001 T25 (tool ghi `set_classification`)

- Verdict: approve (vòng 2; 1 vòng rework)
- Diff: `git diff e50754a..team/FEAT-001-task-25 -- erp_ai` (head 7ea9807); merge a8800c8
- Vòng 1 request-changes: major STD-TEST-6 (`delete_doc("HD Team")` → on_trash commit, rò dữ liệu); major STD-TEST-2 (`get_datetime(None)` luôn truthy). Vòng 2 (FIX_BASE 5ca4748): cả hai ADDRESSED; minor đã sửa. (Lần re-review đầu hết lượt không có báo cáo, chạy lại.)
- Bằng chứng dev: RED 7/11 test (stub); GREEN test_write_ticket Ran 13 OK; mọi đột biến guard đều đỏ
- Sau merge (qua dev, site không dùng song song): `--app erp_ai` Ran 275 tests OK hai lần liên tiếp; pre-commit exit 0; không còn dữ liệu T25 trên miyano

## Findings
Không còn blocker/major.

## Deferred
- T29: `set_classification` trả `ok=true`, `after={}` khi mọi trường bị bỏ qua; runner chỉ đặt `applied = 1` khi `after` không rỗng.
- minor: comment ở test_write_ticket.py:105 nói refusal ở `ticket_type` nhưng không có assert; tearDownClass chưa liệt kê CUSTOMER/OUTSIDER.
- Mẫu dọn tài nguyên khác với T20c (rollback + kiểm vắng mặt thay vì commit guard); chấp nhận được vì kiểm không loại dữ liệu có sẵn.
