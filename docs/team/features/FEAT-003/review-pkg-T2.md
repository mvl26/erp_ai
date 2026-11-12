# Review package FEAT-003 T2

- Repo: /home/miyano/frappe-bench/apps/erp_ai (read-only; `git -C`)
- BASE: 1560098 (team/FEAT-003 with T1, T3 merged). Task branch team/FEAT-003-task-2, head 31c4b75.
- Diff command: `git diff 1560098..team/FEAT-003-task-2`; commits: `git log --oneline 1560098..team/FEAT-003-task-2`
- Touchpoints allowed: erp_ai/public/js/agent_status_indicator.js, erp_ai/tests/test_architecture.py
- Criteria: AC-6 (<= 1 click, panel title), AC-7 ("Chưa có"), AC-12 (textContent only); ADR-009 (the `call` allow-list: remove exactly `\bcall\b` from STATUS_SCRIPT_FORBIDDEN, add the 14 forbidden strings, pin signature `function setupForm({ doc, call, router })`); STD-TEST-5 (all old forbidden strings stay). Sources: tasks.md T2 block, design.md 3.3, 4, 8C, ADR-009, ADR-010, plan.md Ràng buộc chung.
- No cmd.test_js exists; the page is verified by static rules + reading the JS.
