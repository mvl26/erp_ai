# Review T19 — round 1: request-changes (verbatim findings)

major | STD-TEST-8 | erp_ai/gateway/test_gateway.py:915 (sink at erp_ai/gateway/__init__.py:107) | On the "unexpected exception" path the only store the gateway writes is the `erp_ai` file logger (`warning("gateway unexpected %s key=%s", ...)`). `stores_containing` never captures `frappe.logger`. Changing that line to log `exc` would write the marker (`boom <marker>`) to logs/erp_ai.log, and the test would stay green. NFR-5 names "nhật ký" (logs), AC-14 says "every record produced". The same gap covers `send_notice` (logger info) on the quota paths. | In setUp, patch `frappe.logger` (`self.logger = self.enterContext(patch.object(frappe, "logger"))`) and add `found["logger"] = int(marker in repr(self.logger.mock_calls))`. Then paste the red output with the leak planted in that warning, followed by the green run.

minor (dev's call):
(1) test_gateway.py:856 the "Error Log" DB query can never match because log_error is patched at :842: dead code; drop it or comment.
(2) No assertion that each sink was actually used on the 401/529 paths (`self.sendmail.called`, `self.log_error.called`, `last_error` non-empty); otherwise checks go silently empty.
(3) ERP AI Log search only sees what the test's own write_entry call writes (:884) = same as "gateway output"; real proof needs T28 runner (note only).
(4) gateway test imports erp_ai.agent.run_log: test-only reverse dependency (STD-DESIGN-6 spirit).
