---
name: qa-write-limits-and-site-data
description: role-policy hook blocks qa from writing journal/scratchpad; miyano site data (agent roles, live ERP AI Log) makes test_tasks/accuracy red independent of features
metadata:
  type: project
---
role-policy hook lets team:qa write only docs/team/features/**, .team/current.json, .claude/agent-memory/**. It blocks writes to docs/team/journal/*.md and to scratchpad scripts. Run read-only DB queries as `env/bin/python - <<'EOF'` (stdin) from /home/miyano/frappe-bench/sites. Hand journal lines to team-leader.

On miyano (2026-11-12), `erp_ai.tests.test_tasks.TestCheckPrivilegeEscalation` (15) and `TestAccuracyTenLogSample` (4) are red on FEAT-001 and FEAT-002 code alike, because they depend on live site data. The cause: a User save at 2026-11-12 11:21 by session chuvanhieu357@gmail.com gave the agent 97 extra roles, incl. System Manager (Version spr34j6nam). Logged as BUG-002.

**Why:** Has Role.creation copies the parent's creation, so you can only attribute who added a role by reading `tabVersion` (ref_doctype=User). Single doctypes (ERP AI Setting) have no Version rows; use `ERP AI Log.stop_reason` timestamps instead.
**How to apply:** If the full suite is red, first compare its failing set with this baseline (also see [[project_frappe_skips_test_runner_py]]). Attribute site-data changes through tabVersion, not creation.
