# Review package FEAT-001 T32 round 2 (scoped re-review)

FIX_BASE=d03c508  head=7a16d44 (branch team/FEAT-001-task-32)
Fix diff (read-only): `git diff d03c508..team/FEAT-001-task-32`
Old findings: docs/team/features/FEAT-001/review-raw-T32.md (major STD-TEST-8 untested entry_type filter; minors 1-4; plus the permlevel-8 verification).
Mark each ADDRESSED / NOT ADDRESSED; out-of-scope notes go to `deferred`. Minor 4 (local TRIGGER_HUMAN_CORRECTION) deferred by ruling.
Dev's claim on permlevel 8: Frappe runs validate_higher_perm_levels before the validate hooks, so the hook's `ai_classified_by` survives; shown by a test saving as a real "Agent"-role user without ignore_permissions, plus a test patching `Document.get_permlevel_access` to drop level 8 (control: a typed `ai_confidence` is reset while `ai_classified_by` still ends "Người"). Judge whether those tests are sound and not masked.
