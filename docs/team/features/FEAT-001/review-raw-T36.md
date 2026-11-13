# Review raw T36 — round 1 (request-changes)

Diff: `git diff 920be6c..team/FEAT-001-task-36` (72b026a)

## Findings (verbatim from reviewer)
major | STD-SEC-4 | erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.py:109 | `@frappe.whitelist()` with no `methods` lets `check_keys` run on GET, and Frappe does no CSRF check on GET (`auth.py:93`). The endpoint changes state: `probe_credential` updates key status through the breaker and makes a paid outbound call for every key. So a cross-site link opened by a logged-in System Manager can trigger probes and status changes. `test_check_keys_whitelisted_for_post` (test_erp_ai_setting.py:323) only checks that the function is whitelisted, so it would still pass with GET allowed. | Use `@frappe.whitelist(methods=["POST"])`. In the test, assert `frappe.allowed_http_methods_for_whitelisted_func[erp_ai_setting.check_keys] == ["POST"]`. The JS `frappe.call` already sends POST.

minor (dev's call): (1) erp_ai_setting.py:121 raw `label` goes into `frappe.throw` shown as HTML; escape with `frappe.utils.escape_html(label)` (STD-SEC-3). (2) names `one` (test:315) and `r` (js:8) say little (STD-NAME-6). (3) `PROBE_RESULT_FIELDS` declared below the class mid-module (STD-STYLE-4).

## Tech-lead ruling
Round 1: fix the major and minor 1 (security); minors 2-3 if trivial.
