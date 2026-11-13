# Review 15 — FEAT-001 T14 (alerts)

- Verdict: approve (vòng 1, 0 vòng rework)
- Diff: `git diff 7415abd..team/FEAT-001-task-14` (head 8fb14a8); merge cbaf7c7
- Bằng chứng dev: RED ImportError rồi đỏ mức assertion (3 failures, 2 errors) với stub; GREEN `Ran 5 tests OK`; cmd.test sau merge: `Ran 116 tests ... OK`, pre-commit exit 0

## Findings
Không có blocker/major.

## Deferred
- minor STD-TEST-2: `test_content_never_contains_configured_api_keys` không thể đỏ (alerts.py không đọc khóa); bằng chứng NFR-5 thật nằm ở T19 `test_api_key_never_leaks`.
- minor STD-TEST-8: test notice chưa assert nội dung log/`message`.
- Cho T17/T18/T39: `frappe.sendmail` ném `OutgoingEmailError` khi chưa có Email Account gửi mặc định, `send_alarm` ném sau khi đã ghi Error Log; gateway/tasks phải quyết định ảnh hưởng lên đường lỗi của mình.
- Cần người xem (T9 scope): `alert_recipients` chưa được validate địa chỉ email (STD-ERR-2).
