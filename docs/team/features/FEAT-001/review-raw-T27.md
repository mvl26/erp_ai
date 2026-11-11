# Review T27 — round 1: request-changes (verbatim findings)

major | STD-TEST-5 | erp_ai/agent/tools/test_registry.py:266-271 | `test_real_tools_run_through_execute_tool_without_committing` passes `{}` to every real tool. The schema validator refuses the 9 tools with required keys before their handlers run. So no write handler (set_classification, set_resolution_hint, post_comment, create_task) runs under the commit guard. Only get_ticket and list_comments run, and only their missing-ticket refusal path. `assertFalse(result["ok"] and required)` can never fail. The comment "raises AssertionError if any handler commits" overstates the test, and the T23 debt "no handler commits" is not proven at runtime. Helpers outside TOOL_MODULES (classification, authority, policy, Helpdesk `ticket.new_comment`) are also outside the static `.commit(` scan. | Either give each tool minimal valid arguments on a ticket seeded in setUp and assert the handler was reached (reason does not start with "tham số không hợp lệ" and is not "không được cấp"), or delete the test and rely on the static scan, recording its limit.

minor (dev's call):
(1) STD-DESIGN-4: source.py:281 `_schema` is a byte-for-byte copy of read.py:194 `_schema`; reuse one (only if inside touchpoints; read.py is NOT a touchpoint, so import it from read or leave and note).
(2) STD-DESIGN-4: git_source enum ["log","blame"] literal next to GIT_SUBCOMMANDS: two sources of truth; derive from one.
(3) Commit message says "10 tools" but there are 11 and registry.py unchanged (amend not needed if rework commit message is correct).

Tech-lead note: the ticket seeded in setUp must be created under the commit guard with rollback cleanup (STD-TEST-6); no HD Team deletes; prefix "ERPAI-TEST-".
