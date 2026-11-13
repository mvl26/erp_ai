# Review package FEAT-001 T40

BASE=a0039d0  head=c32cdae (branch team/FEAT-001-task-40)

Diff command (read-only, run from the repo root): `git diff a0039d0..team/FEAT-001-task-40`

## Commits
c32cdae test(architecture): static scans, CI installs required apps (FEAT-001)

Touchpoints: erp_ai/tests/test_architecture.py (new), .github/workflows/ci.yml.
Criterion: ADR-001..005, NFR-1, NFR-5, DoD "CI green" (D-23). Tests: layer imports, single enqueue call site, no `.save()` on settings, tools never bypass permissions, subprocess only in the source tool, level/send-policy fields only in policy, handlers do not import gateway/runner, secret-handling rules, no legacy ticket comment or spoofable author, CI installs required apps (`helpdesk` v15.1.0, `erpnext` version-15, `telephony`, `bench init` version-15).
Dev's notes: scan = erp_ai/**/*.py minus test_*.py, tests/, test_utils.py (eval/ IS scanned); the legacy-comment rule also scans .json/.js/.html; documented exceptions: read.py COMMENT_HIDDEN_FIELDS (comment_email, comment_by) allowed per design 3.5 amendment 1c, `get_all("DocType", ...)` metadata reads in tools allowed, eval -> agent.runner allowed (ADR-001). Telephony has no version-15 branch (only develop) so ci.yml uses its default branch. 24 scanner tests feed synthetic violating/clean code; 8 real mutations were run by dev and each tripped the expected test.
Judge: are the exceptions justified by design, can each scanner be fooled (aliased imports, `from x import y`, string concatenation), are scanner tests non-vacuous, is ci.yml change minimal (no action version bump, no change to other workflows).
