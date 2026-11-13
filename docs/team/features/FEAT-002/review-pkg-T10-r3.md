# Review package FEAT-002 T10 round 3 (scoped re-review)

FIX_BASE b797c89 .. team/FEAT-002-task-10 (head b8f6a3f). Diff: `docs/team/features/FEAT-002/review-pkg-T10-r3.diff` (`git diff b797c89..team/FEAT-002-task-10`, 1 file, +3/-1).

## Round 2 finding to mark ADDRESSED / NOT ADDRESSED
major STD-TEST-8 test_architecture.py:820: writes-nothing scanner checked only ast.Attribute; `from frappe import db; db.set_single_value(...)` and `from frappe import cache; cache().hset(...)` slipped through. Required: check `ast.Name | ast.Attribute`; add both cases with "uses frappe.db" / "uses frappe.cache".

## Dev evidence (raw)
RED with the two cases before the fix: failures=2 ("scanner missed the violation" x2). GREEN after: tests.test_architecture Ran 58 OK (live-tree rules included); pre-commit passes.
