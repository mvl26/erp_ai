# Review package FEAT-001 T17 round 2 (scoped re-review, FIX_BASE 7bc7f0c..1125d18, branch team/FEAT-001-task-17)

Diff command (authoritative, read-only git): `git diff 7bc7f0c..team/FEAT-001-task-17 -- erp_ai`
Full task diff for context: `git diff e50754a..team/FEAT-001-task-17 -- erp_ai`

Old findings to mark ADDRESSED / NOT ADDRESSED (round 1, verbatim):
1. major | STD-TEST-8 | test_gateway.py:368-369 | setUp seeded `max_keys_per_call=3`, `request_timeout_s=60` equal to the defaults; use non-default values and add fallback cases.
2. major | STD-TEST-2 | test_gateway.py:414-415 | `latency_ms` only checked isinstance/>=0; assert an exact value with a patched clock.
3. major | STD-TEST-8 | test_gateway.py:559 | notification failure: `frappe.log_error` in the except could be replaced by `pass`; `_alarm_no_key` try/except untested; assert log_error is called and a no_key GatewayError still raised when send_alarm fails.
4. major | STD-TEST-8 | test_gateway.py:506 | `from None` on the bad_request raise untested; assert `__cause__ is None` and `__suppress_context__`.
5. minors: (1) exception type in the notification-failure log; (3) log when a key has no stored secret.

Touchpoints: erp_ai/gateway/__init__.py, erp_ai/gateway/test_gateway.py (plus the approved deletion in erp_ai/tests/test_handlers.py from round 1).
