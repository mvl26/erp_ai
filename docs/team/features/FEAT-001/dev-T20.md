
## Round 2 fixes
1. Keyword-side casefold -> test_contains_keyword_ignores_case_of_configured_keyword (trigger_keyword="@AI", content "@ai"). Mutation (policy.py `keyword.casefold()` -> `keyword`): `FAIL: test_contains_keyword_ignores_case_of_configured_keyword`, Ran 21, FAILED (failures=1). Restored: Ran 21, OK.
2. Duplicate OPT_OUT_FIELD -> install.py now imports it from erp_ai.agent.policy (no cycle; erp_ai.tests.test_install Ran 13, OK).
c. Removed `- {""}`; d. can_send_ticket(None) -> False (test_empty_ticket_cannot_send); b. test_runs_today_counts_creation_exactly_at_midnight (fixed `now`).
Full `--app erp_ai`: Ran 143, 7 errors, all "Assignment Rule IT - Support Rotation not found" (test_handlers, test_ticket_delete, test_install in full-run order; test_install passes alone) - environmental, outside touchpoints. pre-commit: all Passed.
