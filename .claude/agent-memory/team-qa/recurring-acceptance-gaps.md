---
name: recurring-acceptance-gaps
description: Recurring reasons qa cannot write `accepted` in erp_ai (shared site miyano deadlocks, no Playwright, migration up/down/up skipped) and how by-reference verifies were handled
metadata:
  type: project
---

As of 2026-11-14, the same gaps keep blocking a clean qa `accepted` in erp_ai:
- Shared site `miyano`: parallel `run-tests` from other sessions cause `QueryDeadlockError 1213`; no whole-app `cmd.test` has ever been `OK` (FEAT-004). `bench run-tests` exits 0 even when red, so read the `Ran`/`OK|FAILED` line and junit counts.
- `ui: false`, no Playwright: criteria that ask qa to open a link in a real browser or view a Helpdesk ticket page stay NOT VERIFIABLE.
- Migration up/down/up (STD-OPS-2) not run by qa because the site lock is busy.

**Why:** the human accepted FEAT-004 on 2026-11-14 "with existing evidence" while qa kept `rework`; CHG-001 (FEAT-004 Amendment 2) was then verified by reference with no re-run, and qa again wrote `rework` for the same reasons.

**How to apply:** for a by-reference verify, check that the evidence commit is an ancestor of the commit under check and diff the code between them. Keep qa's own verdict separate from the human's waiver, and name an owner for each gap (team-leader: exclusive site; qa: migrate; human: screenshots).
