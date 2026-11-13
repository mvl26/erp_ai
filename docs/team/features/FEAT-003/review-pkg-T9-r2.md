# Review package FEAT-003 T9 round 2 (scoped re-review)

- Repo: /home/miyano/frappe-bench/apps/erp_ai (read-only; use `git -C`)
- BASE: c3f32b5. Task branch team/FEAT-003-task-9, head 68ad1a1.
- Full diff: `git diff c3f32b5..team/FEAT-003-task-9`; fix only: `git diff 7cb9853..68ad1a1`; commits: `git log --oneline c3f32b5..team/FEAT-003-task-9`
- Touchpoints allowed: erp_ai/ticket_panel.py, erp_ai/tests/test_ticket_panel.py
- Criteria: AC-9, AC-13 (send), design.md 3.2 steps 1-3 and 5, tasks.md T9 block. T10 items (sanitize, send log) are out of scope.
- Round 1 findings to check, verbatim in docs/team/features/FEAT-003/review-T9-r1.md: two majors (escape test passes without html.escape; keyword hard-coded "@ai" not caught). Mark each ADDRESSED / NOT ADDRESSED. Mutate the code to prove the new tests go red (remove html.escape; hard-code " @ai") and revert. Out-of-scope notes go to `deferred`.
- Review against the Review checklist (10). Write your verdict to docs/team/features/FEAT-003/review-T9-r2-verdict.md or return it in your reply.
