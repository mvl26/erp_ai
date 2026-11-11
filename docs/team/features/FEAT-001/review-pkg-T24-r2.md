# Review package FEAT-001 T24 round 2 (scoped re-review, FIX_BASE a19f376..f4e21a9, branch team/FEAT-001-task-24)

Diff command (authoritative, read-only git): `git diff a19f376..team/FEAT-001-task-24 -- erp_ai`
Full task diff for context: `git diff 0c5e216..team/FEAT-001-task-24 -- erp_ai`

Old findings to mark ADDRESSED / NOT ADDRESSED (round 1, verbatim):
1. major | STD-TEST-8 | read.py:69,168 | `apply_fieldlevel_read_permissions` only tested as Administrator (early return); need a non-Administrator/permlevel case for BOTH get_record and get_ticket.
2. major | STD-DESIGN-2 | read.py:72 | get_ticket did not cap description at 6000 chars; use prompts' helper/constant and test 6500 -> 6000.
3. minors (1) hard-code the 11 denied names; (2) limit=1 filter-before-limit case and backslash branch; (3) get_fullname + prompts.COMMENT_MAX_CHARS; (4) bound echoed doctype; (5) unique token instead of "printer"; (6) `# noqa` reason.

Known by tech-lead (record as deferred, not a blocker): `frappe.get_list` doubles backslashes again (db_query.py:1286), so a literal `%`, `_`, `\` in a search query never matches (fails safe: no wildcard injection). The dev removed positive tests that could not pass instead of weakening them.

Touchpoints: erp_ai/agent/tools/read.py, erp_ai/agent/tools/test_read.py. Note: the fix commit was made by the tech-lead from the dev's worktree changes (dev was told not to commit).
