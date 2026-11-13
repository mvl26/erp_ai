# Review package FEAT-001 T26

BASE=a902d83 .. team/FEAT-001-task-26 (head 3a7d884)

Commits:
3a7d884 feat(agent): set_resolution_hint, post_comment, create_task tools (FEAT-001)

Diff: run `git diff a902d83..team/FEAT-001-task-26` and `git diff --stat a902d83..team/FEAT-001-task-26` in /home/miyano/frappe-bench/apps/erp_ai.
Files: erp_ai/agent/tools/write_ticket.py, erp_ai/agent/tools/test_write_ticket.py (touchpoints exactly).

Task criterion (T26): AC-8 (`create_task` chỉ khi có người ra lệnh; thiếu quyền → `ok=false`), A-5, D-14.
Returns: `set_resolution_hint(args, ctx)`, `post_comment(args, ctx)` (core `Comment` qua `ticket.new_comment`, kiểm quyền tạo `Comment`; D8), `create_task(args, ctx)` (dòng đầu `description` có tên và đường dẫn phiếu; không có người ra lệnh hoặc không có DocType `Task` → `ok=false`); `TOOLS` đủ 4 tool, `create_task` nhóm `task_write`.
Handlers must not call frappe.db.commit (execute_tool savepoint). Tests must not commit or leave records on site miyano (STD-TEST-6); fixtures prefix.
Note: the dev also edited the existing T25 test `test_tool_spec_schema_takes_no_doctype_or_field_names` (tool-name list). The T25 test class (HD Team created in setUp, fixtures prefix "T25") has no commit guard; judge whether that is in scope as a leak risk.
