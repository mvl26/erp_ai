---
name: claimed-tests-missing-from-diff
description: FEAT-002/003 - fix rounds that stop halfway - a claimed test missing from the diff, or an import/mock handle added for an assertion that was never written
metadata:
  type: project
---

2026-11-12 (FEAT-002 T5 r2): dev reported a new test `test_unhashable_step_never_throws` guarding a new `try/except TypeError` in `run_status.working`; the fix diff and HEAD contain no such test (test_run_status.py had 6 tests before and after).

2026-11-12 (FEAT-003 T11 r2, 2nd time a fix round stops halfway): fix commit adds `TITLE_RUN_FAILED` import and `self.log_error = ...start()` for the round-1 "log_error not asserted" minor, but no assertion uses either (ruff F401 is ignored in pyproject, so lint stays clean). Grep each new import/handle for a use site.

2026-11-12 (FEAT-006 T2 r2, 3rd form): the "squash" head f8c37d3 has the same tree as the round-1 head 7388e1d (`git rev-parse A^{tree} B^{tree}`); the fix only existed uncommitted in the task worktree (`git -C <wt> diff HEAD`). Dev evidence said 10 tests, but HEAD had 8. Return NEEDS_CONTEXT.

2026-11-15 (CHG-002 T25, 4th form): dev declared `L-1: 3` (three edited subtests) but the commit body `git log --format=%b` had 0 `test-shape:` lines that addendum-2 L-1 point 5 requires (missing line = merge blocker per that rule).

2026-11-15 (CHG-002 T25 r2, 2nd time after T9 `3a56462`): a `test-shape:` line named a subtest that does not exist ("confirm wording"); an empty commit fixed the name. Check every `[<subtest>]` in a test-shape line against `subTest(rule="...")` at head; only the newest commit's list counts (addendum-4 L-2).

2026-11-15 (CHG-002 T28, 3rd time a trace mismatch): dev declared `L-1: 2, L-2: 0`; diff had 3 test-shape (enum test unlisted) and 3 L-2c drops the task itself ordered, with no `test-drop:` lines (wip commits from interrupted devs carry none). Count edits per test vs. body lines; addendum-4 line 41 makes a mismatch merge-blocking.

2026-11-15 (CHG-002 T30, 4th trace mismatch): 4 `test-shape:` lines lack the required tail `— design §x.y (addendum-2 L-1)`; compare each line to the full L-1 point 5 template, not only old→new.

**Why:** the reviewer only sees the package; a claimed test that does not exist leaves the new code unguarded.

**How to apply:** for every test named in dev evidence, `git show <head>:<file> | grep -n "def test_"` and compare with FIX_BASE. Missing test + new production branch = major STD-TEST-1. Related: [[recurring-order-insensitive-signal-tests]].
