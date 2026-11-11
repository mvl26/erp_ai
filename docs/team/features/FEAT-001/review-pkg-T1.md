# Review package T1 (FEAT-001)

Task: T1 Walking skeleton. Branch: team/FEAT-001-task-1. BASE=34e4c8f. Head=cfb160b.

Commits (git log --oneline 34e4c8f..team/FEAT-001-task-1):
- c03d70f feat(agent): walking skeleton ticket handler to queue to runner with fake gateway (FEAT-001)
- cfb160b fix(agent): guard handler when ERP AI Setting is not migrated yet (FEAT-001)

Stat (git diff --stat 34e4c8f..team/FEAT-001-task-1):
 erp_ai/agent/__init__.py, agent/queue.py, agent/runner.py, constants.py, gateway/__init__.py,
 handlers.py, hooks.py, test_handlers.py, test_utils.py  (9 files, +266/-9)

Diff to review (run from /home/miyano/frappe-bench/apps/erp_ai, read-only):
    git diff 34e4c8f..team/FEAT-001-task-1

Criteria (tasks.md T1): AC-5(a) main path, NFR-1, NFR-2: ticket insert -> exactly 1 frappe.enqueue with queue="long",
timeout=600, enqueue_after_commit=True, deduplicate=True; run_for_ticket with FakeGateway -> exactly 1 call_model;
saving a ticket never calls call_model. Allowed touchpoints: erp_ai/constants.py, hooks.py, handlers.py,
agent/__init__.py, agent/queue.py, agent/runner.py, gateway/__init__.py, test_utils.py, test_handlers.py.
Design: docs/team/features/FEAT-001/design.md (section 3 constants, 3.2 enqueue, 3.4.1 ModelResult).
Test command (worktree form): R=$(git rev-parse --show-toplevel) && cd /home/miyano/frappe-bench && PYTHONPATH="$R" bench --site miyano run-tests --module erp_ai.test_handlers
