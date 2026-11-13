# Scoped re-review FEAT-001 T27 round 2

FIX_BASE=87f6f4b .. team/FEAT-001-task-27 (head 2103201). Diff: `git diff 87f6f4b..team/FEAT-001-task-27`.
Old findings: docs/team/features/FEAT-001/review-raw-T27.md (major STD-TEST-5 + minors 1-3). Mark each ADDRESSED / NOT ADDRESSED.
Dev notes: old `{}` test replaced by TestRealToolsRunWithoutCommit (seeds ERPAI-TEST-T27 data under commit guard; all 11 tools run with minimal valid args, each asserts ok). Mutation (commit() planted in create_task) turned test_every_real_handler_runs_without_committing red; reverted. Minor 1: source.py imports read._schema (private cross-module). Minor 2: enum = sorted(GIT_SUBCOMMANDS) -> ["blame","log"].
