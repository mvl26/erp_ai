# Review package FEAT-001 T38 round 2 (scoped re-review)

FIX_BASE=86b360c  head=b542d64 (branch team/FEAT-001-task-38)
Fix diff (read-only): `git diff 86b360c..team/FEAT-001-task-38`
Old findings: docs/team/features/FEAT-001/review-raw-T38.md (major STD-TEST-5 symmetric mapping test; minors: JSON line number, subject in warning log, duplicate import style).
Mark each ADDRESSED / NOT ADDRESSED; out-of-scope notes go to `deferred`. Dev's evidence for the major: mutation making run() use DEFAULT_CATEGORY_MAPPING turns the strengthened test red (1,2) != (2,1).
