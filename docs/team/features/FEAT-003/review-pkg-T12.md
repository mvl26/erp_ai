# Review package FEAT-003 T12

- Repo: /home/miyano/frappe-bench/apps/erp_ai (read-only; `git -C`)
- BASE: da2d63e. Task branch team/FEAT-003-task-12, head 866e577.
- Diff command: `git diff da2d63e..team/FEAT-003-task-12`; commits: `git log --oneline da2d63e..team/FEAT-003-task-12`
- Touchpoints allowed: erp_ai/public/js/agent_status_indicator.js, erp_ai/tests/test_architecture.py
- Criteria: AC-6 (Đóng button, one indicator), AC-7, AC-8 (label "Bot", B-8 guidance line, "Chưa có tin nào."), AC-11 (d)(g) (stale results dropped; indicator moves into the panel slot when open and back to document.body when closed). Sources: tasks.md T12 block, design.md 3.3 (fixed strings) and 4 (F1, reload), ADR-009, ADR-010, plan.md Ràng buộc chung (textContent only, no innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/new Function, no storage, no setInterval, no number 600, one window.__erpAiAgentStatus, querySelector only '#app', every `call(` literal first argument in PANEL_METHODS).
- STD-TEST-5: no existing check removed or weakened in test_architecture.py.
- Known deferred from T2 review: panel stays open when narrowed (T14 onResize); do not flag T14 items.
