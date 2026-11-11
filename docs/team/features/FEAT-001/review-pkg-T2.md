# Review package T2 (FEAT-001)

Diff command: `git diff a351af1..team/FEAT-001-task-2` (BASE=a351af1, head 136af20)
Commits: 136af20 feat(agent): block duplicate agent job in same transaction (FEAT-001)
Stat: erp_ai/agent/queue.py (+24/-2), erp_ai/agent/test_queue.py (+67 new)

The full diff is obtained with the command above (run it in /home/miyano/frappe-bench/apps/erp_ai; the branch is local).
Criteria (tasks.md T2): same-transaction duplicate enqueue returns False without frappe.enqueue; pending set `frappe.flags.erp_ai_pending_job_ids` cleared at after_commit/after_rollback; trigger outside {ticket_insert, comment_mention} -> ValueError; same signature; re-enqueue after rollback works.
Touchpoints: erp_ai/agent/queue.py, erp_ai/agent/test_queue.py.
