# Review package FEAT-003 T10

- Repo: /home/miyano/frappe-bench/apps/erp_ai (read-only; use `git -C`)
- BASE: 1f6787c. Task branch team/FEAT-003-task-10, head 8df8ba2.
- Diff: `git diff 1f6787c..team/FEAT-003-task-10`; commits: `git log --oneline 1f6787c..team/FEAT-003-task-10`
- Touchpoints allowed: erp_ai/ticket_panel.py, erp_ai/tests/test_ticket_panel.py
- Criteria: AC-9 invariant (stored content must pass contains_keyword), ADR-010 Amendment 1 (QĐ 7), STD-OPS-5 send part (info logs "erp_ai panel send ticket=... comment=... keyword_added=...", "denied method=send ... reason=<not_agent|no_read|agent_user>", "send rejected ... reason=keyword_not_storable"; no content, no email, no keyword). Sources: tasks.md T10 block, design.md 3.2, ADR-010.
- Things to check: sanitize_html parameters versus frappe/core/doctype/comment/comment.py:69-74 (Comment.validate also passes disallowed_tags; is leaving it out a gap for the stored form?); the error message must not contain the keyword; new_comment not called on rejection; tests fail under mutation (remove the check; check on the unsanitized form).
- Review against the Review checklist (10). Reply with verdict first line approve or request-changes.
