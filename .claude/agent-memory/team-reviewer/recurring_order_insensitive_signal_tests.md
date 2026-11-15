---
name: recurring-order-insensitive-signal-tests
description: FEAT-002 recurring defect - signal-order tests stay green when a design decision's "before X" is swapped for "after X"; check ordering against the work itself, not only the signal list
metadata:
  type: project
---

2026-11-12 (FEAT-002 T4, T5): the signal-sequence tests compare only the list of emitted signals, so moving `status.working(...)` from before the tool/model call to after it leaves the list unchanged and the test green (T5: `working` before `_run_tool`, `working(CLASSIFY_STEP)` before the classify model call, D-4).

2026-11-14 (FEAT-004 T57): `commits_at_post` recorded but only compared to `commits_after`; with commit AND rollback mocked, "final status kept after the catch's rollback" holds even if the final-status commit (apply_job lock path / end of `_run_in_lock`) is deleted. Check: does a recorder capture the stored status at each commit, before the risky step?

2026-11-15 (CHG-002 T34): design 4.2 "step 4 (disk hash, all rows) before step 5 (git)" - no test trips a stale row AND a git refusal together, so swapping/interleaving the two loops stays green. Same check as T14: one input tripping both adjacent steps.
2026-11-14 (FEAT-005 T11): "advance watermark before the job's commit" untested; the job tests patch commit to raise and run with `in_test`, so the commit branch never runs and moving the write after commit stays green. Check: does any test set `in_test` False and record state inside a `commit` side_effect?

2026-11-15 (CHG-002 T14): "first reason found wins" check order; RESTART_PLACE vs RESTART_WITHOUT_PY never both triggered (RESTART_PLACE rows all use a `.py` file), so swapping the two rules stays green. Check: for each adjacent pair of rules, is there one input that trips both?

2026-11-15 (CHG-002 T36): §4.2 step 8 "record_commit then frappe.db.commit() (before finish)" untested; BlockApplyTestCase.setUp patches db.commit to a no-op and no test reads its calls, so deleting/moving the commit stays green. Same for `_give_back_after_crash` on a pre-commit crash (no test raises between write and commit).

**Why:** a design decision that names an alternative (`Sai thì: dời ... xuống sau ...`) has to be pinned by a test that fails under that alternative; a pure sequence comparison cannot see "before vs after the work".

**How to apply:** for every "before X" ordering in design/AC, mentally apply the alternative and check whether a test records state *at the moment X runs* (e.g. `FakeGateway(on_call)` -> `signals_on_model_call`, a `wraps=` patch on `runner.execute_tool`). If not, major STD-TEST-2.
