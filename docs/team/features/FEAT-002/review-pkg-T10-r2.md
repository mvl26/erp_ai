# Review package FEAT-002 T10 round 2 (scoped re-review)

FIX_BASE 08bd1ec .. team/FEAT-002-task-10 (head b797c89, 2 commits). Diff: `docs/team/features/FEAT-002/review-pkg-T10-r2.diff` (`git diff 08bd1ec..team/FEAT-002-task-10`). Only erp_ai/tests/test_architecture.py.

## Round 1 findings to mark ADDRESSED / NOT ADDRESSED
1. major STD-TEST-8: install self-test `assertCaught` without fragment; no case with the single correct delete_doc outside before_uninstall.
2. major STD-TEST-8: `RUN_STATUS_FORBIDDEN_ATTRIBUTES` branch not isolated by any case (frappe.cache.hset/get_value, frappe.db.set_single_value).
3. major STD-TEST-8: publish_realtime rule misses (a) string forms getattr/get_attr/import_module outside run_status, (b) aliased/rebound publish_realtime inside run_status (room=/after_commit=False, R-1 room scanner), (c) `import frappe as f; f.realtime`.
4. minors: hooks AGENT_STATUS_SCRIPT_NAME case, ROOM constant, split self-test per scanner, line length.

## Dev evidence (raw summary)
RED on 9 new cases against old scanners (failures=9) then GREEN: tests.test_architecture Ran 58 OK; pre-commit passes. Mutations (drop owner check; drop FORBIDDEN_ATTRIBUTES branch; drop string scan; drop binding check) each turn exact cases red. Product-code mutations (publish_realtime in runner.py, delete_doc/f.cache.hset/`publish = f.publish_realtime` in run_status.py) each red then restored; live rule tests stay green on current code.
