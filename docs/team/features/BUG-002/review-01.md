Feature: BUG-002
Stage: review
Author-agent: reviewer
Date: 2026-11-12
Approved-by:

# Review 01 — BUG-002 T1 (test_tasks cách ly khỏi dữ liệu sống)

- Verdict: approve (sau 1 vòng làm lại; max_rework=3)
- Vòng 1: request-changes — major STD-TEST-6 (setUp chưa vô hiệu hóa bản ghi quyền `modified_by`=agent và Server Script/Webhook `owner`=agent), minor STD-STYLE-5/STD-TEST-8 (guard chết, thiếu ca automatic-role).
- Vòng 2 (scoped re-review): finding 1 ADDRESSED, finding 2 ADDRESSED; không lỗi mới ở mức blocker/major.
- Lệnh diff: `git diff b8f9485..team/BUG-002-task-1b` (tệp duy nhất `erp_ai/tests/test_tasks.py`); sửa vòng 1: `git diff c004ee8..team/BUG-002-task-1b`.
- Bằng chứng dev: RED `Ran 33 tests ... FAILED (failures=12, errors=3)`; sau sửa `erp_ai.tests.test_tasks` -> `Ran 34 tests in 1.087s ... OK`; test mới đỏ khi helper là no-op (`Called 2 times`).
- Ảnh chụp site trước/sau: `ERP AI Setting`, Has Role của agent (99), số đếm HD Team/HD Ticket/ERP AI Log/HD Form Script/Custom DocPerm/Server Script/Webhook/Error Log không đổi; chỉ `Comment` tăng +N (dòng `Deleted` của Email Account/Holiday List do bootstrap của test runner, chuyển cho T3 điều tra).
- Merge: `f433fe9` trên `team/BUG-002`. `cmd.test` toàn bộ chạy một lần ở cuối (một dev tại một thời điểm trên site dùng chung).

## deferred
- minor: test tên "setup neutralizes" tự gọi helper nên bỏ lệnh gọi ở setUp vẫn xanh; guard `frappe.db.exists("DocType", ...)` luôn đúng trên Frappe v15. Không chặn.
