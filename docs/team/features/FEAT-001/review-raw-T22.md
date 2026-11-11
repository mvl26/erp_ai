# Review T22 — round 1: request-changes (reviewer text, verbatim findings)

major | STD-ERR-2 | erp_ai/agent/run_log.py:13-17 | write_entry accepts a call with `entry_type` or `trigger` left out. Frappe `_set_defaults` (document.py:419/978) then fills each Select with its first option (create_new.py:117-118). So an entry with no type is silently stored as `classify`, which AC-11's "latest classify row" lookup and the AC-12 report both count, and a missing trigger becomes `ticket_insert`. Every row make_log_entry creates already gets trigger=ticket_insert without anyone choosing it. write_entry is the only way into the log (ADR-004), so it is the boundary that must reject this | in write_entry, raise ValueError when `fields.get("entry_type")` is not in (classify, reason, skip) or `fields.get("trigger")` is not in (ticket_insert, comment_mention). Add tests "entry_type omitted -> ValueError" and "trigger omitted -> ValueError" (both red on current code). Add `"trigger": "ticket_insert"` to make_log_entry's defaults.

minor (dev's call):
(a) STD-TEST-2 test_run_log.py:60: `assertNotRegex(name, r"^ERP-AI-LOG|^\d+$")` is loose; prefer `assertRegex(name, r"^[0-9a-f]{10}$")`.
(b) STD-DESIGN-5 run_log.py:17: `{"doctype": LOG_DOCTYPE, **values}` lets a caller's `doctype=` override the target. Write `{**values, "doctype": LOG_DOCTYPE}`.
(c) STD-DOC-7 run_log.py:9: docstring should mention PermissionError and that unknown fields are dropped by Frappe.
(d) STD-TEST-2 run_log.py:14: no test covers `ensure_ascii=False` (non-ASCII JSON value).
(e) STD-TEST-8 test_run_log.py:93: no own assertion, relies on setUp guard; add commit assert_not_called.
(f) STD-TEST-2 test_run_log.py:74: "omits_json_fields_when_absent" protects no code.

Cannot verify: red/green output (tech-lead gets from dev); that no pre-existing User `erpai-test-run-log-*@example.com` on miyano (checked by tech-lead via dev).
