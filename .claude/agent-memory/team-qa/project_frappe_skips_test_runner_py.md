---
name: frappe-skips-test-runner-py
description: Frappe v15 `run-tests --app` silently skips any file named test_runner.py; always diff per-module junit vs --app junit before trusting cmd.test totals
metadata:
  type: project
---

Frappe v15 (`apps/frappe/frappe/test_runner.py:160`) skips every file named `test_runner.py` during `--app` discovery. In FEAT-001 (2026-11-11), `erp_ai/agent/test_runner.py` (52 tests) never ran in `cmd.test` or CI: `--app` reported 448 tests, while the per-module runs added up to 500. This led to a design-defect verdict (DD-2).

**Why:** `cmd.test` showing "OK" hid a whole layer of tests. The team-leader's "Ran 448 OK" was true but incomplete.

**How to apply:** In verify, run each covering module with `--junit-xml-output` and the `--app` run with junit too, then compare the test sets. A non-empty difference is a finding. Related: [[project-base-branch-missing]].
