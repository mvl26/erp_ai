# Review T26 — round 1: request-changes (verbatim findings)

major | STD-TEST-2 | erp_ai/agent/tools/test_write_ticket.py:242 | The criterion includes D-14 (the agent role gets a Task Custom DocPerm with read/create/write and `if_owner=1`). But the only positive `create_task` test (`test_create_task_creates_task_with_ticket_link_in_first_line`, :396) gives the test agent `Projects User`. The production AGENT_USER does not have that role: install.py:49 grants only `ERP AI Agent` + `Agent`, and Task create comes only from the `if_owner=1` Custom DocPerm (install.py:164-185). So `create_task` is never shown to work under the permissions it will really run with. | In setUp, give T26_AGENT `ROLE_AGENT` instead of "Projects User" (the Custom DocPerm is on miyano after migrate). For a refusal case, add a user with `Agent` only, without `ROLE_AGENT`.

minor (dev's call):
(1) STD-DESIGN-4: "ai_resolution_hint" and "Task" literals in write_ticket.py:9-10 duplicate install.py:103/165-185.
(2) set_resolution_hint returns `after = args["text"]` but Frappe sanitizes Text Editor value on save, so `after` can differ from what is stored (write_ticket.py:69).
(3) description joins ticket link and text with "\n\n" inside a Text Editor (HTML) field; UI shows one line, path not clickable (write_ticket.py:94).

Deferred / in-scope by tech-lead ruling: T25 class `TestWriteTicket` creates an HD Team in setUp without a commit guard (review-28 rule). Tech-lead rules: add the guard (patch.object(frappe.db, "commit", side_effect=AssertionError) in setUp, stopped after rollback cleanup) in this rework; same file.
