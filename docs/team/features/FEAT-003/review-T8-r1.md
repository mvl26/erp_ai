# Review T8 round 1 (reviewer verdict, verbatim; written by tech-lead)

Verdict: request-changes. BASE da2d63e..team/FEAT-003-task-8 head b55f0f6. AC-14, NFR-4 and read-side STD-OPS-5 implemented; edits inside the 2 touchpoints. `test_read_writes_nothing_and_calls_no_gateway` would fail on any set_value/insert/delete (transaction_writes), gateway call, or enqueue.

major | STD-TEST-2 | erp_ai/tests/test_ticket_panel.py:307-315 | `test_read_logs_ids_only_at_debug` adds only 2 comments, and both pass the B-5 filter (keyword or bot). So `messages=2` would still pass if the code logged the count before filtering (`len(items)` from `get_activity_timeline`, which already returns only comments). The `<n>` value is not pinned | add a third plain comment with no keyword by a human, and keep asserting `messages=2`

minor (dev's call): (1) neither log test puts the keyword value (`KEYWORD`) or the bot's display name in its leak list, though design section 5 forbids logging both; (2) in the `no_read` path of the denied test, `logger.debug.assert_not_called()` is not checked again after `reset_mock`.

Cannot verify: red output (dev reported RED 1 failure test_read_logs_ids_only_at_debug; GREEN 20 OK; full 625 OK); whether patching `frappe.logger` module-wide catches Frappe's own `info` calls and makes `logger.info.assert_not_called()` fail by accident.
