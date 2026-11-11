# Scoped re-review FEAT-001 T26 round 2

FIX_BASE=3a7d884 .. team/FEAT-001-task-26 (head 0cea3ac). Diff: `git diff 3a7d884..team/FEAT-001-task-26`.
Old findings: docs/team/features/FEAT-001/review-raw-T26.md (major STD-TEST-2 + minors 1-3 + tech-lead ruling: commit guard on T25 class). Mark each ADDRESSED / NOT ADDRESSED.
Dev notes: major's two tests passed on old code (coverage gap, no behavior missing; no RED possible). Minor 1 skipped (needs shared constant outside touchpoints). Minors 2, 3 have RED tests. Guard added in TestWriteTicket.setUp, stop registered first so it runs after rollback.
