---
name: order-dependent-tests
description: Tests here that pass in whole-app runs but fail alone (or the reverse); compare per-module vs --app before calling a red real
metadata:
  type: project
---

On 2026-11-14 (FEAT-004 @ ba89ab3), three tests depended on run order or failed in the same way on every run:
- `test_gateway::TestApiKeyLeak::test_api_key_never_leaks` fails ALONE: it patches `frappe.logger` and checks `.called`. The first `get_single("ERP AI Setting")` loads the controller, which imports `agent/tools/source.py`, and that file calls `frappe.logger(...)` when it is imported. In whole-app runs it is green. It is red on develop too.
- `test_erp_ai_log::test_no_role_can_write_or_delete` fails only in the whole-app run, because an extra `ERP AI Instructor` perm shows up in the meta. It is green alone.
- `test_route_ticket::test_sla_chosen_by_complexity_condition` and `test_ticket_panel::test_thread_ignores_non_comment_types` hit deadlock 1213 on all 3 runs.

**Why:** if you go only by "it failed once", you can blame the feature for an ordering artifact. If you go only by "it passed in the app run", you can miss a real isolation bug.
**How to apply:** for any red result, compare the per-module junit with the --app junit and with a develop run before you classify it. A red with the same message 3 times is not random environment noise. See [[project_frappe_skips_test_runner_py]] and [[project_bench_run_tests_exit_zero]].
