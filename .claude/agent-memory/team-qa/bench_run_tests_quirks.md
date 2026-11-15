---
name: bench-run-tests-quirks
description: bench run-tests --app on this project: exit code 0 even on FAILED, skips files named test_runner.py; run whole app once with --junit-xml-output and read the XML
metadata:
  type: feedback
---

`bench --site miyano run-tests --app erp_ai` must not be trusted by exit code alone: it can exit 0 when tests FAILED, and `--app` does not pick up a file literally named `test_runner.py`. Count failures/errors from the junit XML (`--junit-xml-output <scratch>/x.xml`) and the "Ran N tests ... FAILED/OK" line.

**Why:** team-leader warned about this on FEAT-006 verify (2026-11-13); an earlier qa fork died mid-run and lost everything.
**How to apply:** one full-app run with junit per verify; to test a worktree branch, prefix `PYTHONPATH=<worktree>`; site miyano is shared — one suite at a time. Write acceptance.md after every 4–5 criteria. See [[feat-006-verify-notes]].
