# Review package FEAT-001 T21 round 2 (scoped re-review, FIX_BASE 3f85124..0a0ff08, branch team/FEAT-001-task-21)

Diff command (authoritative, read-only git): `git diff 3f85124..team/FEAT-001-task-21 -- erp_ai`
Full task diff for context: `git diff 1d6976e..team/FEAT-001-task-21 -- erp_ai`

Old findings to mark ADDRESSED / NOT ADDRESSED (round 1 review, verbatim):
1. major | STD-TEST-8 | erp_ai/agent/authority.py:61 | removing the ToDo filter `allocated_to: author` (and `reference_type: HD Ticket`) keeps every test green; need cases where a newer ToDo of another user (or another reference_type) exists on the same ticket.
2. minor (a) limit=1 and limit=50 never accepted in a test; (b) fetch_ticket_comments never run as a non-Administrator user (get_list vs get_all).

Touchpoints: erp_ai/agent/authority.py, erp_ai/agent/test_authority.py. Ignore docs/ files in the commit. Note: authority.py is unchanged in the fix commit.
