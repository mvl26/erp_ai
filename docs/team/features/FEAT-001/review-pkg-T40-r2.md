# Review package FEAT-001 T40 round 2 (scoped re-review)

FIX_BASE=c32cdae  head=ac31460 (branch team/FEAT-001-task-40)
Fix diff (read-only): `git diff c32cdae..team/FEAT-001-task-40`
Old findings: docs/team/features/FEAT-001/review-raw-T40.md (major import allowlist; major log_error without message; minors). Dev also did the cheap minors (aliased subprocess/os imports, os.exec*/spawn*, constants.SETTING_DOCTYPE and get_doc forms, `;` in SELECT, gateway/agent importing erp_ai.erp_ai_agent). Not done: importlib string imports, TestCase base, assertCaught name, prefix oddity.
Real tree reported clean against the new rules (no product code changed). Mutations run by dev: `import erpnext` appended to alerts.py and a one-argument log_error appended -> both caught.
Mark each ADDRESSED / NOT ADDRESSED; new findings as `severity | STD | file:line | description | fix`; out-of-scope notes go to `deferred`.
