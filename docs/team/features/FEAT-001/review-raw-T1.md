# Review T1 round 1 (verbatim findings) - request-changes

major | STD-DESIGN-2 | erp_ai/handlers.py:8-12 | The handler has `try/except frappe.DoesNotExistError: return` (commit cfb160b). Design 4.1 (ADR-003): the handler contains only pre-checked reads, no try/except that swallows errors. Root cause: the hook is registered in T1 but the DocType is created in T9. | Replace the try/except with an explicit check before the read: `if not frappe.db.exists("DocType", SETTING_DOCTYPE): return`. The guard is temporary; T31 (owner of handlers.py) removes it once T9 has created the DocType.

minor | STD-TEST-6 | erp_ai/test_handlers.py:14 | `_real_get_single_value` captured at import time (stale db binding suspected) | capture it inside `_setting_value`
minor | STD-TEST-8 | handlers.py:15 | `doc.owner == AGENT_USER` branch has no T1 test (T31 covers it) | optional
minor | STD-NAME-6 | erp_ai/test_utils.py:4 | parameter `kw` | optional (name is from tasks.md)
minor | - | test_handlers.py | enqueue test does not assert job_id | optional

Cannot verify from the diff: red-then-green output; cmd.lint; helpdesk suite stays green with the hook.
