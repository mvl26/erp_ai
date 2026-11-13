# Review package FEAT-006 T23 (prompt suy luận: bảng routing dựng từ cấu hình), vòng 1

Repo: `/home/miyano/frappe-bench/apps/erp_ai` (worktree `.claude/worktrees/feat-006`). BASE=1117974; head=team/FEAT-006-task-23 (a123a3a).
Lệnh diff (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/feat-006 diff 1117974..team/FEAT-006-task-23 -- erp_ai`
Commits: `git -C ... log --oneline 1117974..team/FEAT-006-task-23`; stat: `git -C ... diff --stat 1117974..team/FEAT-006-task-23`.

Commits:
- a123a3a feat(prompts): build routing table from config for the reason prompt (FEAT-006)

Stat (mã): prompts.py 73, runner.py 26, test_agent_runner.py 25, test_classification.py 57.

Touchpoints cho phép: erp_ai/agent/prompts.py, erp_ai/agent/runner.py, erp_ai/agent/test_classification.py, erp_ai/agent/test_agent_runner.py.

Tiêu chí: AC-14 (prompt hiện người mới sau khi đổi cấu hình; không tên người viết cứng trong `.py`), ADR-019 Ràng buộc. Returns (tasks.md T23): xóa `ROUTING_TABLE`; `build_routing_table(mapping, config, names) -> str` (cùng cột với 16.2; `names` = {user ID: get_fullname}); `build_reason_system(prompt_digest, routing_table="")` (rỗng thì bỏ phần routing); `runner._reason` truyền bảng dựng từ cấu hình; `test_agent_runner.py` sửa chỗ gọi theo chữ ký mới. Expect: `TestPrompts::test_routing_table_shows_configured_people`, `test_reason_system_without_routing_table` xanh.
Đặc tả: tasks.md dòng T23; design.md dòng ~147; D-11.
