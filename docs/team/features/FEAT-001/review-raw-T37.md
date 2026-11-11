# Review raw T37 — round 1 (request-changes)

Diff: `git diff b63a667..team/FEAT-001-task-37` (07cea99)

## Findings (verbatim from reviewer)
major | STD-DESIGN-5 | erp_ai/eval/export_tickets.py:25 | Adds a filter that requires all 3 `CLASSIFICATION_FIELDS` to be set. The spec and design do not ask for it, and it removes hand-labeled tickets that have an empty `agent_group`/`priority` from the eval without any notice. `test_export_skips_unlabeled_tickets` (erp_ai/eval/test_export_tickets.py:105) locks this behavior in. | Remove the `agent_group`/`priority` conditions. Either filter on nothing, or at most on `ticket_type` set, which matches `compute_metrics`' definition of a label. Change or delete the test to match.
major | STD-DESIGN-4 | erp_ai/eval/export_tickets.py:26 | The list of fields the send policy needs is copied by hand (`"ai_opt_out"` literal, plus `agent_group` arriving only by accident through `EXPORT_FIELDS`) instead of using `policy.SEND_POLICY_FIELDS`. If a field is added to the policy, `can_send_ticket(dict)` reads None for it and lets the ticket through (fail-open on NFR-4/A-9). | Use `fields=["name", *policy.SEND_POLICY_FIELDS, *EXPORT_FIELDS]` (deduplicate if needed), or pass `ticket.name` so the policy fetches its own fields. Add a test that would fail if a policy field were missing from the query.
minor | STD-TEST-6 | test_export_tickets.py:114-124 | inserts a `File` with `content`, which writes a physical public file under sites/<site>/public/files; rollback does not remove it. | Use `is_private=1` and remove the file in a cleanup, or make the attachment a DB-only record. (Do not delete site records beyond the file you created in the test itself; report if cleanup of existing residue is needed.)

## Tech-lead ruling
"Labeled" = `ticket_type` set (same definition as `compute_metrics`). Both majors go to rework round 1.
