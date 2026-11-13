# Scoped re-review package FEAT-001 T12 round 2 (FIX_BASE 86ca6ca..021440c, branch team/FEAT-001-task-12)

Diff command (authoritative): `git diff 86ca6ca..team/FEAT-001-task-12`
Commit: 021440c fix(install): isolate T12 tests from migrated ai fields and template rows (FEAT-001)
Stat: erp_ai/install.py (+14 -15 approx; 29 lines), erp_ai/tests/test_install.py (+27 -3); 41 insertions, 18 deletions

Old findings to mark ADDRESSED / NOT ADDRESSED: see docs/team/features/FEAT-001/review-16.md "Round 1":
- major STD-TEST-5 (setUp must reset the ai_* Custom Fields and template rows so the create path runs in the rolled-back transaction; assert rows 2-6 of the template)
- minor STD-DESIGN-4 (single field list), minor STD-TEST-8 (HD Customer meta check), minor STD-TEST-6 (assert on warning.call_args)

Summary of the fix diff:
- install.py: new `_ai_field_specs()` is the single AI field list; the section's `insert_after` is set in `_ensure_ticket_custom_fields`; template rows derive from `_ai_field_specs()` minus `ai_section`.
- test_install.py setUp: patches `frappe.db.updatedb` (Custom Field creation otherwise does ALTER TABLE = implicit commit, which leaked the deletes; columns already exist from migrate), deletes `ai_*` Custom Fields and Default template `ai_*` rows, `frappe.clear_cache(doctype="HD Ticket")`, then `ensure_setup()`.
- HD Customer check now uses `frappe.get_meta("HD Ticket")`: each AI field `permlevel == 8` and no HD Customer read perm at permlevel 8.
- test_existing_template_row_preserved asserts rows 2-6: order, `visible_to == "Agents"`, `required == 0`, `editable_after_creation` 1 only for ai_opt_out.
- warning test asserts message contains "not found" and arg is the template name.

Dev evidence (RED mutations reverted afterwards): removing `permlevel` -> `0 != 8 : ai_section`; dropping `_ensure_ticket_custom_fields()` -> 10 errors "Field ai_resolution_hint does not exist"; `visible_to` Everyone -> 10 errors "internal and cannot be shown to customers" (Helpdesk validation fires in setUp). GREEN test_install Ran 10 OK; `--app erp_ai` Ran 119 OK; migrate x2 exit 0; pre-commit passed.
