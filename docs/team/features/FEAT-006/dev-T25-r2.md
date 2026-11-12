# dev T25 vòng 2 — fix review-25-round1

Nhánh: team/FEAT-006-task-25-rework1 (tách từ team/FEAT-006-task-25 vì nhánh gốc đang checkout ở worktree khác). Chỉ sửa `erp_ai/eval/test_run_eval.py`; `run_eval.py` không đổi (không có bug thật).

## Finding 1 (major, STD-TEST-2): mapping tùy biến trong test parity
- Thay đổi: `test_eval_uses_runner_route_function` gieo mapping A -> agent_group HR, priority Low; importance 1 (không nâng ưu tiên) nên Low/HR chỉ đến từ mapping; thêm `eval_route.call_args.args[2] == mapping`; nhãn dòng eval priority Low, agent_group HR, khẳng định cả priority và team (1, 1).
- Đột biến: `_predict` gọi `decide_route(..., DEFAULT_CATEGORY_MAPPING, ...)` -> ĐỎ `test_eval_uses_runner_route_function` (Tuples differ ... 'HR','Low' vs 'IT','High'). `run` gọi `_predict(row, routing, DEFAULT_CATEGORY_MAPPING)` -> ĐỎ cùng test. Hoàn tác -> xanh.

## Finding 2 (major, STD-TEST-8): phản hồi cụt không parse được
- Thay đổi: `test_predict_failures_give_none_fields` dùng text JSON cụt, usage output_tokens 600, stop_reason max_tokens, khẳng định `(600, "max_tokens")`; thêm `test_run_counts_cut_off_reply_in_token_metrics` (classify_output_tokens_max 600, classify_max_tokens_hits 1, unclassified 1).
- Đột biến: bỏ `output_tokens=` ở nhánh sau khi gọi model -> ĐỎ 4 test: `AssertionError: Tuples differ: (None, 'max_tokens') != (600, 'max_tokens')`; `test_run_counts_cut_off_reply_in_token_metrics`: `0 != 600`; (+ test_predict_returns_route_and_token_fields, test_run_reports_priority_team_scores_and_tokens). Hoàn tác -> xanh.

## Finding 3 (major, STD-TEST-6): không dựa vào dữ liệu site
- Thay đổi: `test_run_reports_priority_team_scores_and_tokens` gọi `set_agent_settings(category_mapping=json.dumps(DEFAULT_CATEGORY_MAPPING), routing_rules=make_routing_rules())`.
- Đột biến: đổi mapping gieo (A -> HR) -> ĐỎ `Tuples differ: (3, 1) != (3, 2)`, chứng minh kết quả lấy từ mapping gieo, không từ site. Hoàn tác -> xanh.

## Minor
Comment dòng ~524 viết lại đúng điều test kiểm (importance 1 không tạo sàn ưu tiên, Low/HR chỉ từ mapping).

## Lệnh và đầu ra cuối
- `bench --site miyano run-tests --module erp_ai.eval.test_run_eval` -> Ran 22 tests, OK
- `bench --site miyano run-tests --app erp_ai` (chạy một mình) -> Ran 860 tests, OK
- `pre-commit run --files erp_ai/eval/test_run_eval.py` -> tất cả Passed/Skipped (ruff linter, formatter Passed)
