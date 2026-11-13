# Review package FEAT-001 T23 round 2 (scoped re-review, FIX_BASE 104a1c8..d62e8ce, branch team/FEAT-001-task-23)

Diff command (authoritative, read-only git): `git diff 104a1c8..team/FEAT-001-task-23 -- erp_ai`
Full task diff for context: `git diff c7df05b..team/FEAT-001-task-23 -- erp_ai`

Old findings to mark ADDRESSED / NOT ADDRESSED (round 1, verbatim):
1. major | STD-TEST-8 | registry.py:128 | savepoint-rollback test stays green if `rollback(save_point=...)` is changed to a full `rollback()`; need a second pre-existing Note that must survive.
2. major | STD-DESIGN-2 | test_registry.py:64 | `ignore_permissions=True` under erp_ai/agent/tools/** (ADR-005 grep rule).
3. major | STD-DESIGN-5 | registry.py:44-48 | ModuleNotFoundError skip in `_all_specs` silently drops a tool group; remove it, import modules directly (lazily).
4. minors: (1) test named `test_execute_rejects_tool_not_granted_and_bad_arguments` missing; (2) key in `reason` unbounded (reason <= 200); (3) unused JSON_TYPES number/object; (5) `patch.stopall()`.

Touchpoints: erp_ai/agent/tools/__init__.py, registry.py, test_registry.py.
Context for point 3: real `_all_specs()` works only once read.py/write_ticket.py (T24/T25) and `source.TOOLS` (T27) exist; tests patch it; T27 line in tasks.md states this.
