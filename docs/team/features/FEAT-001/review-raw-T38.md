# Review raw T38 — round 1 (request-changes)

Diff: `git diff 609c12d..team/FEAT-001-task-38` (86b360c)

## Findings (verbatim from reviewer)
major | STD-TEST-5 | erp_ai/eval/test_run_eval.py:299-314 (test_mapping_comes_from_setting_with_default_fallback) | The rows are symmetric: one "Custom A" row and one default-type A row. Under the custom mapping the custom row is labeled and the default row is skipped. Under the default mapping the reverse happens. Both give labeled=1, skipped_unlabeled=1, per_category A count=1. So if run() ignored the Setting and always used DEFAULT_CATEGORY_MAPPING, the test would stay green; only the "" fallback half can fail. | Make the row mix uneven, for example 2 "Custom A" rows + 1 default-type row. Assert (2,1) with the Setting set and (1,2) after `category_mapping=""`. Optionally also give the custom rows different predictions so per_category differs.

minor (dev's call): (1) run_eval.py:155 `json.loads` per line gives no line number on a bad file (STD-ERR-2). (2) run_eval.py:137 the warning logs the ticket `subject` (customer text) as context; use the row's line number instead (STD-ERR-4/SEC-6). (3) test_run_eval.py imports both `from erp_ai.eval import run_eval` and `from erp_ai.eval.run_eval import ...` (STD-STYLE-4).

## Tech-lead ruling
Round 1: fix the major and minors 1-2 (cheap), minor 3 if trivial.
Debt (not T38): move CLASSIFY_MAX_TOKENS to constants.py or prompts.py so eval does not load the runner; eval -> agent.runner direction is allowed by ADR-001 (T40 `test_layer_imports` must not ban it).
