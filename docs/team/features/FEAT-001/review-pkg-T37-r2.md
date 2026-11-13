# Review package FEAT-001 T37 round 2 (scoped re-review)

FIX_BASE=07cea99  head=62c3460 (branch team/FEAT-001-task-37)
Fix diff (read-only): `git diff 07cea99..team/FEAT-001-task-37`
Old findings: docs/team/features/FEAT-001/review-raw-T37.md (major STD-DESIGN-5 filter beyond spec; major STD-DESIGN-4 hand-copied policy fields; minor STD-TEST-6 physical File left behind). Ruling: "labeled" = ticket_type set only.
Mark each ADDRESSED / NOT ADDRESSED; out-of-scope notes go to `deferred`.
Dev's claim: new test test_export_queries_every_send_policy_field has no RED on old code (it passed there), guard mutation (dropping `*policy.SEND_POLICY_FIELDS`) turns it red; File is now is_private=1 with cleanup removing only that file.
