# Review package FEAT-001 T10

BASE=8aaf703 .. team/FEAT-001-task-10 head 9512a0c
Commits: 9512a0c feat(agent): DocType ERP AI Log, append-only audit log (FEAT-001)
Command: `git diff 8aaf703..team/FEAT-001-task-10` (read it in full)

Stat:
- erp_ai/erp_ai_agent/doctype/erp_ai_log/__init__.py | 0
- erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.json | 253 +
- erp_ai/erp_ai_agent/doctype/erp_ai_log/erp_ai_log.py | 5 +
- erp_ai/erp_ai_agent/doctype/erp_ai_log/test_erp_ai_log.py | 121 +
4 files changed, 379 insertions(+)

Decisions that supersede design.md (journal docs/team/journal/FEAT-001.md):
- D4: git_source is log/blame only (no show/diff). Not relevant to this task.
- D6: USD money fields (here cost_usd) are Float precision 6 with "(USD)" in the label, never Currency.

Task criterion (tasks.md T10): AC-15 (all log fields of design 2.3), A-10 (no delete), ADR-004. autoname = hash; search_index on `ticket`, `run_id`; permissions per design 5.1: System Manager read/report/export, role `ERP AI Agent` read/create, nobody write/delete. Expected tests: creation under a role-agent account works; plain HD Agent gets PermissionError; no role has write/delete.
