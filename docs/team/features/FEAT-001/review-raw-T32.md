# Review raw T32 — round 1 (request-changes)

Diff: `git diff 221187b..team/FEAT-001-task-32` (d03c508)

## Findings (verbatim from reviewer)
major | STD-TEST-8 | erp_ai/tests/test_handlers.py:411 (test_ticket_without_classify_log_saves_without_error) + erp_ai/handlers.py:53 | Nothing tests the `"entry_type": "classify"` filter in `_latest_classify_log`. If you remove it, every test still passes. In the one test with a non-classify row, the row has no `predicted_category`, so the `no_prediction` check gives the same result and hides the missing filter. In production the runner writes `reason` rows (turn 1..N) after the `classify` row, so without the filter the "latest" row would be a `reason` row with no prediction and AC-11 would never be recorded. | Add a test: make a `classify` row (predicted "A"), then a newer `reason` row of the same ticket. Save a priority change. Assert the `classify` row has `human_corrected_to` and the `reason` row does not, and that `ai_classified_by` = "Người". Check it goes red when the filter is removed.

minor (dev's call): (1) test_handlers.py:373 `creation="2099-01-01 00:00:00"` has no effect (Frappe overwrites `creation` on insert); pin the older row with `frappe.db.set_value(LOG_DOCTYPE, older_log, "creation", <past>, update_modified=False)`. (2) handlers.py:63-79 validate never resets `doc.flags.erp_ai_human_corrected` on early-return paths; set it False at the top of validate. (3) handlers.py:87-89 `no_classify_log` branch in on_update is unreachable; two queries per correction (validate could pass the row name in the flag) (STD-DESIGN-5). (4) handlers.py:19 `TRIGGER_HUMAN_CORRECTION` defined locally; other TRIGGER_* live in constants.py (STD-NAME-7).

Cannot verify (tech-lead): Frappe 15 order of `validate_higher_perm_levels` vs the doc validate hook: `ai_classified_by` is permlevel 8; every test uses `ignore_permissions=True`, so none covers a real HD Agent form save without permlevel-8 write.

## Tech-lead ruling
Round 1: fix the major; minors 1 and 2 are cheap, do them; 3-4 if trivial (4 only if constants.py move is a one-liner: it is outside the touchpoints, so keep the local constant and defer). ALSO verify the permlevel-8 question: add a test that saves the HD Ticket as a real HD Agent session user (no `ignore_permissions`, user without permlevel-8 write) changing a classification field, and show whether `ai_classified_by` ends as "Người" and the log row is updated; if the permlevel logic reverts the value, report it as DESIGN_CONFLICT with the evidence rather than working around it.
