---
name: project-base-branch-missing
description: erp_ai config says base_branch "main" but no local main exists (only develop); team-leader confirmed develop as the diff base on 2026-11-11
metadata:
  type: project
---

As of 2026-11-11, `.team/config.json` has `base_branch: "main"`, but there is no local `main` and no `origin/*` refs. `git diff main...` fails with exit 128. For FEAT-001 verify, the team-leader explicitly said the base is `develop` (merge-base 2932a2b).

**Why:** The skip-marker grep needs a valid base ref. A guessed base can't be traced.

Still true on 2026-11-12: for BUG-001 (branched from team/FEAT-001, whose code had not reached develop yet), the team-leader set the base to `team/FEAT-001`. The base depends on the branch each feature was cut from.

**How to apply:** Run `git rev-parse --verify <base_branch>` first. If it fails, use `develop` only when the team-leader says so in the delegation; otherwise escalate. Limit the skip-marker grep to `-- '*.py'`, because docs and profile files contain the marker strings as rule text. Related: [[frappe-skips-test-runner-py]].
