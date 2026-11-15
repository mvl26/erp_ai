---
name: shared-site-acceptance
description: How to get a clean whole-app run on the shared dev site miyano during verify (lock, settings, Report, lint on a clone, MyISAM Error Log)
metadata:
  type: project
---

On the shared site `miyano` (several feature worktrees migrate it), a clean acceptance run needs ONE hold of
`flock -w 1800 .team/miyano-site.lock`: migrate from the feature worktree (`PYTHONPATH=<worktree>`), force-import
Report `ERP AI Accuracy` from the branch JSON, blank `auto_assign_enabled` / `code_change_apps` of ERP AI Setting,
run `cmd.test`, then restore all three and read back. Verified FEAT-005 2026-11-14: `Ran 1564 tests` / `OK`.

**Why:** other branches leave their Report JSON and settings on the site; three runner tests go red when
`auto_assign_enabled=1`; concurrent sessions cause `QueryDeadlockError`. Migrating from one branch deletes the
other branch's DocTypes as "Orphaned" (seen with FEAT-007 doctypes) — environment, not a defect.

**How to apply:**
- Reuse the tech-lead hold recipe (scratchpad `t16/hold.sh` pattern); judge from your own log.
- Run `cmd.lint` (`pre-commit run --all-files`) on a throwaway `git clone` at the verified commit, so formatter
  hooks cannot edit the worktree.
- `tabError Log` is MyISAM on miyano: anything "rolled back with the alarm" excludes Error Log rows; tests leave
  Error Log rows behind (~40 per whole-app run).
- Related: [[team-qa-verdict-notes]]
