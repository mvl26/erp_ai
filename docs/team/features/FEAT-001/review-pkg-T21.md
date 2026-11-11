# Review package FEAT-001 T21 (BASE 8a5be57..3ed63de, branch team/FEAT-001-task-21)

Diff command (authoritative, read-only git): `git diff 8a5be57..team/FEAT-001-task-21`

Commits:
- 3ed63de feat(agent): per-person authority and comment labels (FEAT-001)

Stat: erp_ai/agent/authority.py (+65, new), erp_ai/agent/test_authority.py (+92, new); 157 insertions

Contents:
- authority.py: `NEVER_AUTHORITY = {Administrator, Guest, AGENT_USER}`; `is_instruction(author, ticket_name)` (never-authority -> False; has `ERP AI Instructor` role -> True; else `_assigned_by_other`: author in the ticket's `_assign` and the latest non-Cancelled ToDo for that ticket/author has `assigned_by` set and != author); `latest_instructor(ticket_name)` (comments by creation desc, author = `commented_by or owner`; first with authority; else ticket owner if it has authority; else None); `label_comments(ticket_name, comments)` (new dicts with `role` = "chỉ thị" | "dữ liệu", input untouched).
- test_authority.py: 6 tests (the 5 in tasks.md plus test_label_comments); setUp creates roles/users/tickets inside a transaction with addCleanup(rollback).

Dev evidence: RED 1 ImportError (module missing), RED 2 with a stub: 4 assertion failures; GREEN `Ran 6 tests OK`; mutation (`_assigned_by_other` always True) -> test_self_assigned_is_data fails, reverted; pre-commit passed.

Run `git diff 8a5be57..team/FEAT-001-task-21` for the verbatim code.
