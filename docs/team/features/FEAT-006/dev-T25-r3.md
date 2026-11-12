# dev T25 round 3 (final)

Branch: team/FEAT-006-task-25-rework2 (from team/FEAT-006-task-25-rework1; rework1 is checked out in another worktree).

## Change
`erp_ai/eval/test_run_eval.py`: `TestRunEvalRun.setUp` now seeds
`set_agent_settings(category_mapping=json.dumps(DEFAULT_CATEGORY_MAPPING), routing_rules=make_routing_rules())`.
Tests that need their own mapping/routing still override inside the test. No other test behavior changed.

## Proof (temporary scratch subclass, deleted, not committed)
Subclass of `TestRunEvalRun` that writes a foreign site config (mapping ticket_type "Weird" for A-F, routing_rules "{}") before the base setUp.

- Before the fix: 26 tests, FAILED (failures=5): test_gateway_error_on_one_row_counts_unclassified_and_run_continues, test_run_classifies_rows_without_prediction_and_prints_report, test_run_counts_cut_off_reply_in_token_metrics, test_run_uses_given_predictions_without_gateway, test_unparseable_reply_counts_unclassified.
- After the fix: 26 tests, OK.

## Verification
- `bench --site miyano run-tests --module erp_ai.eval.test_run_eval` -> Ran 22 tests, OK
- `bench --site miyano run-tests --app erp_ai` (alone) -> Ran 860 tests, OK
- `pre-commit run --files erp_ai/eval/test_run_eval.py` -> all hooks Passed/Skipped

## Note
`test_eval_and_runner_share_classify_request` still passes its own explicit mapping; the routing_rules now come from the setUp seed.
