# Review T28 — round 2 (scoped): request-changes (verbatim)

Majors 1-3 and minors 1-3 of round 1: ADDRESSED. Minor 4: partly; the fix introduced:

major | STD-ERR-4 | erp_ai/agent/runner.py:89 (test pins it at test_runner.py:169-184) | When the ticket is missing, the skip entry is written with `ticket=None`. The row then has only a random run_id, the trigger and `not_sendable`, so nothing says which ticket was gone. Before the fix, the Error Log line still held `ticket=<name>`, so the fix loses traceability. It also goes against design 2.3: the log is the audit trail, and its `ticket` field keeps a deleted ticket's name (D-29). | Keep the name. Either write this entry without link validation (a `write_entry` option) — NOT allowed here, run_log.py is outside the T28 touchpoints — or, inside runner.py only, record it as e.g. `error=f"ticket_missing {ticket_name}"`. Update the test to assert the name is recorded.

minor (dev's call): (a) test_runner.py:231-232 `create=True` in patch.object is not needed and would hide a renamed import; (b) test_runner.py:193 seeds `ai_confidence="Cao"`, same as the stub output; seed "Thấp".
