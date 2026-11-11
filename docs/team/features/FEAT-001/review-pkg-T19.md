# Review package FEAT-001 T19

BASE=466648c .. team/FEAT-001-task-19 (head d0a125b). Diff: `git diff 466648c..team/FEAT-001-task-19` (only erp_ai/gateway/test_gateway.py; product code unchanged because the test found no leak).

Task criterion (T19): AC-14 (phần khóa), NFR-5. Expect: test_api_key_never_leaks (khóa giả có chuỗi nhận diện; đường thành công, 401, ngoại lệ lạ; tìm trong ERP AI Log, Comment, Error Log, email đã gửi, `last_error` → 0 kết quả).
Test data rule: no records left on miyano; the final test patches frappe.log_error so it writes no Error Log rows.
Reviewer: check that each path's assertion would go red if that path leaked (STD-TEST-8), that searches are real (not vacuous, e.g. Error Log/Comment queries use the key string properly), and that the test does not leave records.
