# Review package FEAT-003 T14

- Repo: /home/miyano/frappe-bench/apps/erp_ai (read-only; use `git -C`)
- BASE: 1f6787c. Task branch team/FEAT-003-task-14, head 9225b22.
- Diff: `git diff 1f6787c..team/FEAT-003-task-14`; commits: `git log --oneline 1f6787c..team/FEAT-003-task-14`
- Touchpoints allowed: erp_ai/public/js/agent_status_indicator.js, erp_ai/tests/test_architecture.py
- Criteria: AC-11 (a)(b)(c)(e)(f)(g), NFR-3, AC-14 (no storage, no polling). Sources: tasks.md T14 block, design.md 3.3 and 4 (F3, F4), spec.md AC-11; payload keys docinfo_update frappe comment.py:59-67,85-104 and doc_update document.py:1370-1385.
- Things to check: handler conditions match the real payload keys; reconnect reload only when open; reset() and onResize behaviour; the static pins are anchored at use sites so deleting any wiring goes red (STD-TEST-2; dev reports 20 mutations red); no existing check loosened.
- Review against the Review checklist (10). Reply with verdict first line approve or request-changes.
