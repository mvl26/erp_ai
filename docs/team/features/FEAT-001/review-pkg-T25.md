# Review package FEAT-001 T25 (BASE e50754a..5ca4748, branch team/FEAT-001-task-25)

Diff command (authoritative, read-only git): `git diff e50754a..team/FEAT-001-task-25`

Commit: 5ca4748. Files: erp_ai/agent/tools/write_ticket.py (new), erp_ai/agent/tools/test_write_ticket.py (new).

Task: T25 line in tasks.md; design 3.5 (set_classification), 5.2, ADR-005. Criteria: AC-10, AC-8, ADR-005 #2.
Rules to check: no `ignore_permissions` anywhere under erp_ai/agent/tools/**; no `frappe.db.commit` (execute_tool savepoint); write allowed only after `has_permission("write")` and `has_permlevel_access_to(field, "write")`; tool takes no DocType/field names from the model; tests run as non-Administrator users.

Dev evidence (raw): RED 7 of 11 failed on a stub; GREEN Ran 12 OK; full app Ran 249 OK; pre-commit exit 0; 4 guard mutations each red.

Run `git diff e50754a..team/FEAT-001-task-25` for the verbatim code.
