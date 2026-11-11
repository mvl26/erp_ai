# Review package FEAT-001 T37

BASE=b63a667  head=07cea99 (branch team/FEAT-001-task-37)

Diff command (read-only, run from the repo root): `git diff b63a667..team/FEAT-001-task-37`

## Commits
07cea99 (eval export of labeled tickets, FEAT-001)

Touchpoints: erp_ai/eval/export_tickets.py, erp_ai/eval/test_export_tickets.py.
Criterion: AC-2, A-9, NFR-4. `export(path) -> int`: JSONL, exactly 6 keys (subject, description, ticket_type, agent_group, priority, owner), no attachments; realpath inside the app repo -> ValueError("Không ghi dữ liệu phiếu vào repo"); tickets excluded by `policy.can_send_ticket` (excluded team, opt-out) are skipped; works when the agent is disabled. "Labeled" = ticket_type, agent_group and priority all set (dev's reading; judge it against spec AC-2).
Expected tests: test_export_skips_excluded_team, test_export_skips_opt_out_and_runs_when_disabled, test_export_refuses_path_inside_repo.
