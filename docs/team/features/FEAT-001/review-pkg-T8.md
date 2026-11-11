# Review package T8 (FEAT-001)

BASE=b27a20b, head=b80fb7b (branch team/FEAT-001-task-8)
Diff command: `git diff b27a20b..team/FEAT-001-task-8` in /home/miyano/frappe-bench/apps/erp_ai (also `git log --oneline b27a20b..team/FEAT-001-task-8`, `git diff --stat ...`).

## Task T8 criteria
DocType `ERP AI Credential` (child table, istable=1, module "ERP AI agent") with exactly the fields of design.md section 2.2; `api_key` is fieldtype Password (NFR-5); self-managed fields read_only (AC-19); `status` default "Hoạt động" with `read_only_depends_on: eval:doc.status!='Lỗi khóa'`; `try_order` default 10; `enabled` default 1. Uses status constants from erp_ai/constants.py.
Touchpoints: erp_ai/erp_ai_agent/doctype/__init__.py, erp_ai/erp_ai_agent/doctype/erp_ai_credential/{__init__.py, erp_ai_credential.json, erp_ai_credential.py, test_erp_ai_credential.py}.
