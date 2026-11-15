---
name: bench-run-tests-exit-zero
description: On miyano, `bench run-tests --module` exits 0 even when tests FAIL/ERROR; evidence must be the OK/FAILED line or junit, never the exit code
metadata:
  type: project
---

Seen on 2026-11-12 (FEAT-003 verify): all 8 mutation runs of `bench --site miyano run-tests --module …` printed `FAILED (failures=N)` but returned `exit=0`.

**Why:** If you report "exit 0" as proof of green, a red suite can pass acceptance unnoticed.

**How to apply:** For every `cmd.test`/`cmd.test_one` row, paste the `Ran N` + `OK` line and parse `--junit-xml-output` for failure/error/skipped. Write the exit code down, but do not treat it as the verdict. Mutation spot checks in a detached worktree with `PYTHONPATH=<wt>` work (the worktree code is loaded). Each module run adds about 2 `Deleted` Comments (Email Account/Holiday List) as known noise. The live agent on miyano may also process real tickets during a run, so attribute any count delta before you call it a leak. Related: [[frappe-skips-test-runner-py]], [[qa-write-limits-and-site-data]].
