# Review package FEAT-003 T6

- Repo: /home/miyano/frappe-bench/apps/erp_ai (read-only; `git -C`)
- BASE: 3cfa6bf. Task branch team/FEAT-003-task-6, head 51804f0.
- Diff command: `git diff 3cfa6bf..team/FEAT-003-task-6`; commits: `git log --oneline 3cfa6bf..team/FEAT-003-task-6`
- Touchpoints allowed: erp_ai/agent/policy.py, erp_ai/agent/test_policy.py
- Criteria: AC-9, AC-15 (`contains_keyword` body not changed by one line; only `get_trigger_keyword() -> str` added, reads trigger_keyword exactly as contains_keyword does; empty -> ""). Sources: tasks.md T6 block, design.md 3.2, ADR-010 Amendment 1.
