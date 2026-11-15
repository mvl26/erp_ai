---
name: site-read-via-mariadb
description: Read-only site data on miyano is reachable with `bench --site miyano mariadb -e "SELECT ..."` from the bench root; known helpdesk test residue on the site (2026-11-12)
metadata:
  type: project
---

`cd /home/miyano/frappe-bench && bench --site miyano mariadb -e "SELECT ..."` works for qa (no hook block, no run-tests hooks, no DB writes). Use it when team-leader asks qa to read site data in place of researcher (FEAT-006, 2026-11-12).

**Why:** researcher's role-policy blocks every `cmd.*` slot starting with `cd ../.. &&`; `run-tests` would also fire erpnext before_tests writes.

**How to apply:** quote backticked table names; use `LIKE BINARY` for Vietnamese label searches (default collation ignores accents, e.g. "hạn" matches "Phân"). Known site state 2026-11-12: helpdesk test residue SLA `SLA Priority` (enabled, condition on High/Urgent/Low) + `Test Holiday List`; 0 HD Agent; teams IT and "Nhân sự & Hành chính" link to Assignment Rules that do not exist. Re-check before relying on it. See [[project_qa_write_limits_and_site_data]].
