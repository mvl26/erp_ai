# Review package FEAT-003 T4

- Repo: /home/miyano/frappe-bench/apps/erp_ai (read-only; `git -C`)
- BASE: f7dc6b1 (team/FEAT-003 with T3 merged). Task branch team/FEAT-003-task-4, head 42fbd10.
- Diff command: `git diff f7dc6b1..team/FEAT-003-task-4`; commits: `git log --oneline f7dc6b1..team/FEAT-003-task-4`
- Touchpoints allowed: erp_ai/tests/test_doctype_descriptions.py, erp_ai/erp_ai_agent/doctype/erp_ai_credential/erp_ai_credential.json
- Criteria: AC-1..AC-5, NFR-1 for ERP AI Credential (18 fields, 4 Section Breaks per design 2.1; `budget_month_usd` has "0" and "không giới hạn"; `api_key` no `sk-`). Sources: spec.md data table (lines 56-80), design.md 2.1, plan.md Ràng buộc chung.
- Also in scope (deferred minors of T3 review, same file): tighten phrase tokens that could never fail ("A", "F", "1", "0"), remove the dead `source == fieldname and value == description` skip. Check they were fixed without weakening any check.
