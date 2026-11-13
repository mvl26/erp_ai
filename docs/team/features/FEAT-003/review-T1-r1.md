# Review T1 round 1 (reviewer verdict, verbatim; tech-lead wrote the file because the reviewer role cannot write under docs/)

Verdict: request-changes. BASE 8c6d925..team/FEAT-003-task-1 head ca3e0cc. Checklist 10/10 covered. Touchpoints 4/4, no skip markers. AC-7 passes, ADR-010 D2 passes, STD-TEST-5 passes (test_architecture.py only adds erp_ai.ticket_panel to gateway/agent forbidden lists, one new LAYER_RULES row, 3 scanner cases; every old forbidden string remains).

## Findings
major | STD-TEST-2 | erp_ai/tests/test_ticket_panel.py:91-95 | AC-13 (spec line 251, design 8B) names HD Contact, but only Website User and Guest are tested. Those two and the inactive-agent case (:110-114) are each refused by both `is_agent()` and `has_permission`, because the HD Ticket hook returns False when `not is_agent(user)` (hd_ticket.py:1360). Deleting the `is_agent()` check (ticket_panel.py:24-26) leaves every test green. Only a non-agent who can read the ticket shows this: an HD Contact with role "HD Customer" who is the ticket's `raised_by`/`contact` | add that case: `make_ticket(raised_by=<email>)`, assert first that `is_agent()` is False and `has_permission` is True, then expect `PermissionError`

minor | (1) the empty/wrong-type `ticket` -> `ValidationError` branch (ticket_panel.py:60-61) has no test. (2) `apply_fieldlevel_read_permissions` (:52) is only tested with a user who has permlevel 8, so deleting it stays green. (3) the Datetime test uses `format_datetime` itself as the expected value (test:77); hard-code the string. (4) the reason strings of the gateway/agent rules (test_architecture.py:46,60) don't mention ticket_panel, and the ticket_panel rule has only the gateway scanner case. (5) an import inside a test body (test:104) | dev's call

## Cannot verify from the diff (tech-lead resolves)
- No red-then-green output in the package (dev report has it: RED 7 failed 1 error for missing behavior; GREEN test_ticket_panel Ran 8 OK, test_architecture Ran 58 OK; lint clean).
- `date_format` of site miyano decides whether minor (3) slips through.
- Whether `make_ticket` in setUp starts erp_ai jobs the rollback does not undo.
