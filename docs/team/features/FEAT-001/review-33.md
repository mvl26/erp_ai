# review-33 — FEAT-001 T27 (registry nối 11 tool, ma trận bộ tool)

Verdict: approve (2 rounds). Round 1 request-changes: major STD-TEST-5 (test "không commit" truyền `{}` nên handler ghi không chạy) + 3 minors; chi tiết: review-raw-T27.md. Round 2 (FIX_BASE=87f6f4b, head 2103201): tất cả ADDRESSED; mutation (commit() trong create_task) làm test chạy-thật đỏ.
Ghi chú: tổng 11 tool (read 4, source 3, ticket_write 3, task_write 1), không phải 10 như tasks.md.
Diff: `git diff 57704e5..team/FEAT-001-task-27`; merge c1fc09a.
cmd.test (qua dev T28 trên cây gồm T27): `--app erp_ai` Ran 311 tests OK hai lần liên tiếp.
Counts HD Team/HD Ticket/User/Task trước = sau (4/3/8/0).

## deferred
- source.py nhập `_schema` private từ read.py (nên chuyển thành helper công khai).
- write_ticket.py còn bản `_schema` inline thứ ba.
- Test chạy search/read/git_source trên checkout thật, cần `.git` thật ở đường dẫn app.
- ci.yml chỉ cài erp_ai, chưa cài helpdesk (có từ trước T27; T40 xử lý).
