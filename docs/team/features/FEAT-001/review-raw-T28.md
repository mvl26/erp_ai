# Review T28 — round 1: request-changes (verbatim findings)

major | STD-TEST-8 | erp_ai/agent/test_runner.py:41 | The tests seed `max_runs_per_ticket_per_day=5`, which equals the DocType default (erp_ai_setting.json:51). If runner.py:71 hard-coded 5 instead of reading the Setting, test_sixth_run_same_day_no_call and test_fifth_run_same_day_still_calls would stay green. AC-15 and NFR-3 require this limit to be editable. 3rd time in FEAT-001. | Seed a limit that is not the default (e.g. 2): 2 seeded runs -> skip `daily_limit`, 1 -> one call.

major | STD-TEST-2 | erp_ai/agent/test_runner.py:26,139-144 | AC-9 (spec:122) and the design 8 row require "số comment … và các trường AI của phiếu trước = sau". TICKET_FIELDS checks only the 3 classification fields, status, subject and modified. It never compares the number of `Comment` rows on the ticket or the `ai_*` fields (ai_classified_by, ai_confidence, ai_updated_at, ai_resolution_hint). | Add the ticket's `Comment` count (filters from `authority.ticket_comment_filters`) and the `ai_*` fields to the before/after comparison.

major | STD-DESIGN-4 | erp_ai/agent/runner.py:20,76 | `RUN_DEADLINE_S = 540` repeats a value that design 4.3/D-5 defines as `JOB_TIMEOUT_S − JOB_SAFETY_MARGIN_S` (constants.py:24-25; queue.py already uses JOB_TIMEOUT_S). | `deadline = time.monotonic() + JOB_TIMEOUT_S - JOB_SAFETY_MARGIN_S`, drop RUN_DEADLINE_S (test that the deadline passed to the gateway follows the constants, e.g. patch JOB_TIMEOUT_S).

minor (dev's call):
(1) No test pins guard order (disabled+not sendable -> no log, b before c; not sendable + over limit -> not_sendable, c before d).
(2) test_runner.py:227 `test_over_budget_l3_is_not_l0_for_comment_mention` only sets L1, no budget: name does not match (STD-NAME-6).
(3) runner.py:80 literal "L0" where `LEVELS` exists.
(4) Ticket deleted before job runs: `not_sendable` skip entry fails Link validation on `ticket` -> TITLE_RUN_FAILED instead of a skip entry. Handle or test (e.g. do not write a Link to a missing ticket) if cheap.

Approved aspects: breaker-state debt (commit in finally of _call_model, no rollback in except) sound and tested for real; step order (a)-(e) matches design; L0 writes nothing to the ticket; test_handlers.py edit accepted (tech-lead ruling).

Notes for T29/T30 (carried in tasks.md): on normal return the framework commits, so a failed run's uncommitted work persists; each turn's commit also commits the previous turn's tool writes -> an exception after a successful set_classification but before the classify entry is updated leaves ticket changed with applied=0: T29 must do the tool write and the log update together, or log first; `except Exception` catches deadlock 1213 so Frappe retry never runs (accepted under D-20).
