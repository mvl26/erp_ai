# Review T25 vòng 1 — request-changes

Diff: `git -C /home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/feat-006 diff 601ebe7..team/FEAT-006-task-25 -- erp_ai` (b0df8e3). Checklist 10/10; lớp 1 đạt (đủ 7 khóa `_predict`; eval dùng cùng `decide_route` với đúng thứ tự đối số của runner; chỉ đọc site); lớp 2 có 3 major.

## Findings (nguyên văn từ reviewer)

1. major | STD-TEST-2 | `erp_ai/eval/test_run_eval.py:499-503` (and `run_eval.py:202`, `:239`) | The criterion says eval calls `decide_route` with the same arguments as the runner, including `mapping`. But the parity test sets `category_mapping = json.dumps(DEFAULT_CATEGORY_MAPPING)`, so the mapping loaded from the setting is identical to the default. If `_predict` passed `DEFAULT_CATEGORY_MAPPING` to `decide_route` instead of `mapping` (or `run` called `_predict(row, routing, DEFAULT_CATEGORY_MAPPING)`), the test would stay green. `test_predict_returns_route_and_token_fields` passes the default itself. `test_mapping_comes_from_setting_with_default_fallback` gives every row a `predicted_category`, so it never reaches `_predict`. | Seed a custom mapping in the parity test that differs from the default in `agent_group` and `priority` for the classified category, for example A -> `{"agent_group": "HR", "priority": "Low"}`. Then assert the eval's `predicted_agent_group` and `predicted_priority` come from that mapping, in addition to comparing the call args.

2. major | STD-TEST-8 | `erp_ai/eval/test_run_eval.py:457-467` | For the unparseable reply, the test checks `stop_reason` but never checks `output_tokens`. That value comes from the fake's default usage (0) and is never asserted. If `output_tokens=` were dropped from `run_eval.py:195`, the test would stay green. This is the case D-8 cares about most: a reply cut off at `max_tokens` is exactly the reply that fails to parse, and `classify_output_tokens_max` would then miss the ceiling. | Use `make_model_result(text="{\"dau_muc\": \"A\", \"do_tin", usage={"output_tokens": 600}, stop_reason="max_tokens")` and assert `(unparsed["output_tokens"], unparsed["stop_reason"]) == (600, "max_tokens")`. Ideally also add one run-level row so it is counted in `classify_output_tokens_max` and `classify_max_tokens_hits`.

3. major | STD-TEST-6 | `erp_ai/eval/test_run_eval.py:469-492` | `test_run_reports_priority_team_scores_and_tokens` sets neither `category_mapping` nor `routing_rules`, and `TestRunEvalRun.setUp` sets neither. The team expectation `(3, 2)` therefore depends on the live mapping on site `miyano` giving A/B/F = "IT". This goes against spec A-13: "Không test nào dựa vào dữ liệu site". | Call `set_agent_settings(category_mapping=json.dumps(<test mapping>), routing_rules=make_routing_rules())` in this test, or in `TestRunEvalRun.setUp`.

minor (dev tự quyết): ở test parity, khẳng định cuối và comment `test_run_eval.py:520-521` ("importance 2 raises A (High) to High") không phân biệt được `importance_priority` với mapping vì cùng cho High; comment nói quá điều test kiểm.

## Cannot verify (tech-lead xử lý)

- Giá trị `category_mapping`/`routing_rules` thật trên site `miyano` (finding 3): sửa bằng gieo cấu hình trong test.
- Lệnh eval thật và `classify_output_tokens_max` thật: thuộc qa (AC-15).
