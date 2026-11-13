# Review package FEAT-001 T16 round 2 (scoped re-review, FIX_BASE 545d4be..696b2c8, branch team/FEAT-001-task-16)

Diff command (authoritative, read-only git): `git diff 545d4be..team/FEAT-001-task-16`
Full task diff for context: `git diff 0c5e216..team/FEAT-001-task-16`

Old findings to mark ADDRESSED / NOT ADDRESSED (round 1, verbatim):
1. major | STD-TEST-8 | test_gateway.py:271,284 | removing the guard `if reset_at is not None:` (credentials.py:106) stays green because the rows start with `limit_reset_at = None`; seed a fixed datetime and check unchanged after apply_success.
2. minor (1) the `idx` tie-break only goes red by chance; patch `frappe.db.get_all` to return rows in reverse idx order.
3. minor (2) `fields=["*"]` returned the masked api_key column; use an explicit field list.
4. Tech-lead decision: `apply_failure` gets optional `request_id=None` (last_error `"<kind> status=<s> request_id=<id>"`).

Touchpoints: erp_ai/gateway/credentials.py, erp_ai/gateway/test_gateway.py, erp_ai/test_utils.py.
