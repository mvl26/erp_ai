# review-31 — FEAT-001 T26 (set_resolution_hint, post_comment, create_task)

Verdict: approve (2 rounds). Round 1 request-changes: major STD-TEST-2 (create_task chỉ thử với role Projects User, không phải ROLE_AGENT theo D-14) + 3 minors; chi tiết: review-raw-T26.md. Round 2 (FIX_BASE=3a7d884, head 0cea3ac): ADDRESSED (trừ minor 1, deferred); thêm commit guard cho lớp test T25 theo phán quyết tech-lead.
Diff: `git diff a902d83..team/FEAT-001-task-26`; merge 57704e5.
cmd.test (qua dev T27): `--app erp_ai` Ran 309 tests OK hai lần liên tiếp.
Counts HD Team/HD Ticket/User/Task trước = sau (4/3/8/0).

## deferred
- minor STD-DESIGN-4: literal "ai_resolution_hint"/"Task" trùng ở write_ticket.py và install.py (cần hằng chung ngoài touchpoint).
- Comment sau insert gửi thông báo @mention: nội dung do model sinh có thể mention người dùng; chính sách thuộc T28/T31.
