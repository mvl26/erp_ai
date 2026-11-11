# Review package FEAT-001 T20 round 2 (scoped re-review, FIX_BASE 300988e..bea59c9, branch team/FEAT-001-task-20)

Diff command (authoritative, read-only git): `git diff 300988e..team/FEAT-001-task-20 -- erp_ai`
Full task diff for context: `git diff 1d6976e..team/FEAT-001-task-20 -- erp_ai`

Old findings to mark ADDRESSED / NOT ADDRESSED (docs/team/features/FEAT-001/review-pkg-T20.md round 1, verbatim):
1. major | STD-TEST-8 | erp_ai/agent/test_policy.py:93-96 | `test_contains_keyword_ignores_case` only uses default lowercase keyword; keyword-side `.casefold()` never decisive. | add a case with configured keyword `@AI` and content `@ai`.
2. major | STD-DESIGN-4 | erp_ai/install.py:18 | `OPT_OUT_FIELD` defined twice. | install.py imports it from policy (touchpoint extended to install.py by tech-lead).
3. minor (a)-(d): real clock in runs_today tests; 00:00 boundary untested; useless `- {""}` at policy.py:37; `can_send_ticket(None)` raises.

Touchpoints now: erp_ai/agent/policy.py, erp_ai/agent/test_policy.py, erp_ai/install.py. Ignore docs/ files in the commit.
