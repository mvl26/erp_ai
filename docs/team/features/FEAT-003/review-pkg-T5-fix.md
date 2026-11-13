# Scoped re-review package FEAT-003 T5 round 2

- Repo: /home/miyano/frappe-bench/apps/erp_ai (read-only; `git -C`)
- Task branch team/FEAT-003-task-5. Round-1 head 15d4aa3. Fix commit 3765c3e.
- Fix diff: `git diff 15d4aa3..team/FEAT-003-task-5` (erp_ai_log.json, tests/test_doctype_descriptions.py)
- Old findings to mark ADDRESSED / NOT ADDRESSED: docs/team/features/FEAT-003/review-T5-r1.md (4 majors on meaning vs writer code, 4 minors). Re-check each reworded description against the writer code it cites (runner.py, authority.py, write_ticket.py, tasks.py) -- the previous round's wording was wrong in 4 places.
- The dev also changed the shared test harness (collect all missing phrases instead of stopping at the first; added test_forbidden_phrases_absent): check it did not weaken the checks of T3/T4 entries.
