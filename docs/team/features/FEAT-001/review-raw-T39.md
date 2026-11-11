# Review raw T39 — round 1 (request-changes)

Diff: `git diff a947607..team/FEAT-001-task-39` (1b69de0)

## Findings (verbatim from reviewer)
major | STD-TEST-5 | erp_ai/erp_ai_agent/report/erp_ai_accuracy/test_erp_ai_accuracy.py:120-131 | `test_empty_predicted_and_corrected_values_are_equal` sets both `predicted_agent_group` and the corrected `agent_group` to None. `frappe.db.set_value` writes NULL, so the comparison is None vs None, which is equal with or without normalization. Removing `or ""` at erp_ai_accuracy.py:106 keeps the test green, so the test cannot fail. In real data a "" vs None mismatch would then be miscounted as a correction. | Make the two sides differ: predicted `""` with corrected None, and predicted None with corrected `""` (one subTest each). Show red with `or ""` removed, then green.

minor (dev's call): (a) pending boundary (`creation` exactly at now - 7d) has no case (STD-TEST-8). (b) last line of `test_report_record_is_system_manager_only_script_report`: `has_permission("Report", doc=report, user=plain)` is False because the user has no roles at all; the roles assertion above it covers it, so drop or sharpen the line. (c) `frappe.log_error` patched in setUp though nothing calls it.

## Tech-lead ruling
Fix the major and minor (a); (b) and (c) if trivial. Interpretation (1) accepted: design 2.5 says 6 rows A-F + Tổng, 3.8 says sample = 0 -> empty; the dev's dual behaviour (`data == []` only when the range holds no prediction at all; otherwise `accuracy_pct = None`) stands, recorded as a design question for the designer. Open design questions (not findings): unparseable `human_corrected_to` with all predicted fields empty; first edit within 7d followed by an edit back to the predicted value counts as "not corrected".
