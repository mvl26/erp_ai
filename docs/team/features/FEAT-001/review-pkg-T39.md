# Review package FEAT-001 T39

BASE=a947607  head=1b69de0 (branch team/FEAT-001-task-39)

Diff command (read-only, run from the repo root): `git diff a947607..team/FEAT-001-task-39`

## Commits
1b69de0 feat(report): ERP AI Accuracy script report (FEAT-001)

Touchpoints (6 files): erp_ai/erp_ai_agent/report/__init__.py, erp_ai_accuracy/__init__.py, erp_ai_accuracy.json, erp_ai_accuracy.py, erp_ai_accuracy.js, test_erp_ai_accuracy.py.
Criterion: AC-12, A-12, D-17, NFR-9 (measurement). `execute(filters) -> (columns, data)`; filters from_date, to_date; columns category, predictions, corrected, pending, accuracy_pct; rows A-F + "Tổng"; sample = 0 -> empty; a correction after 7 days is not counted; a correction back to the predicted value is not a correction. Design 3.8, spec AC-12.
Dev's interpretations to judge against spec/design: (1) data == [] only when the date range holds no prediction at all; otherwise a row whose sample (predictions - pending) is 0 shows accuracy_pct = None. (2) A correction after 7 days counts as correct; exactly +7d still counts as a correction; unparseable JSON counts as a correction; empty and null are equal when comparing. (3) Only categories A-F are counted. (4) execute() also checks has_permission("ERP AI Log", "report") server-side.
Migrate creates the Report record (expected side effect). Check SQL parameterisation, quoting of the `trigger` keyword if used, and the report JSON (roles, ref_doctype, is_standard, module).
