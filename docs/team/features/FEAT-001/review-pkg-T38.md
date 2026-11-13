# Review package FEAT-001 T38

BASE=609c12d  head=86b360c (branch team/FEAT-001-task-38)

Diff command (read-only, run from the repo root): `git diff 609c12d..team/FEAT-001-task-38`

## Commits
86b360c feat(eval): run classification with the runner's own request (FEAT-001)

Touchpoints: erp_ai/eval/run_eval.py, erp_ai/eval/test_run_eval.py.
Criterion: AC-1 (report printed in full), AC-3 (same prompt as the runner), D-22 (no ERP AI Log written). `run(path) -> dict`: rows that already carry `predicted_category` never reach the gateway; others use `build_classify_request` + `runner.CLASSIFY_MAX_TOKENS` + `parse_classification`; a gateway error on a row counts as unclassified (logger warning) and the run continues. Design 3.7, Amendments 2026-11-11.
Expected tests: test_run_uses_given_predictions_without_gateway, test_eval_and_runner_share_classify_request.
Check in particular: `run_eval` now imports `erp_ai.agent.runner` for CLASSIFY_MAX_TOKENS (layer rule: ADR-001..005 / design layering; T40 will scan imports). Judge whether that direction is allowed by design 3.x layering, and whether the constant belongs in constants.py instead.
