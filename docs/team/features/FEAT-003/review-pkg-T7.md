# Review package FEAT-003 T7

- Repo: /home/miyano/frappe-bench/apps/erp_ai (read-only; `git -C`)
- BASE: 3cfa6bf. Task branch team/FEAT-003-task-7, head 32dd12e.
- Diff command: `git diff 3cfa6bf..team/FEAT-003-task-7`; commits: `git log --oneline 3cfa6bf..team/FEAT-003-task-7`
- Touchpoints allowed: erp_ai/ticket_panel.py, erp_ai/tests/test_ticket_panel.py
- Criteria: AC-8 (thread selection B-5: core Comment type "Comment" and (owner == AGENT_USER or policy.contains_keyword(content)); old -> new; author = full name; is_bot; created_at formatted; text = html_to_plain_text; no email, no instructor/data labels), AC-12 server side (no markup survives into the page text channel). Sources: tasks.md T7 block, design.md 3.1, ADR-010 Decision 5, plan.md Ràng buộc chung (no ignore_permissions/set_user/get_all/db.sql/commit; no `.new_comment(` yet).
- Note for the reviewer: the page renders every message with textContent only (AC-12); judge whether leaving a literal `<script>` text in `text` after html_to_plain_text is acceptable given that and the spec/design wording for AC-8/AC-12.
