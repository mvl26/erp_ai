# dev-T25 — Eval offline: khớp ưu tiên, nhóm, phân bố điểm, trần token (FEAT-006)

Nhánh: `team/FEAT-006-task-25` (từ `team/FEAT-006` 601ebe7). Chạm: `erp_ai/eval/run_eval.py`, `erp_ai/eval/test_run_eval.py`.

## Đã làm
- `_predict(row, routing, mapping)` trả 7 khóa; request dùng `build_classify_request(..., departments(routing))`; route qua `decide_route` import từ `erp_ai.agent.routing` (cùng hàm runner) với `site_facts.team_exists`, `policy.is_excluded_team`, `site_facts.is_active_agent`. Lỗi gateway: mọi giá trị None; trả lời không đọc được: category/priority None nhưng giữ `output_tokens`, `stop_reason`.
- `compute_metrics` (vẫn thuần) thêm `priority`, `team`, `score_distribution` (bin 0..3 luôn đủ), `classify_output_tokens_max`, `classify_max_tokens_hits` (đúng `stop_reason == "max_tokens"`). Khóa dòng: nhãn `priority`/`agent_group`; dự đoán `predicted_priority`/`predicted_agent_group`/`predicted_complexity`/`predicted_importance`; `output_tokens`, `stop_reason`.
- `format_report` in 4 khối mới; `run` đọc `routing_rules` (`load_routing_config`). Ngưỡng 0,85/0,70 không thành cổng.

## RED (trước khi có mã)
`Ran 21 tests ... FAILED (failures=2, errors=7)`: `KeyError: 'priority'`, `KeyError: 'classify_output_tokens_max'`, `AttributeError: module 'erp_ai.eval.run_eval' has no attribute 'decide_route'`, `TypeError: _predict() takes 1 positional argument but 3 were given`, `AssertionError 'Priority match: 100.0% (1/1)' not found`.

## GREEN
`erp_ai.eval.test_run_eval`: `Ran 21 tests ... OK`. `--app erp_ai`: `Ran 859 tests ... OK`. `pre-commit run --files ...`: tất cả Passed.

## Đột biến (đỏ rồi hoàn tác)
1. Đếm cả dòng thiếu nhãn trong `_match` -> `{'count': 1,...} != {'count': 0,...}`, `(5, 2) != (3, 2)`.
2. Đếm cả dự đoán None -> `(4, 2) != (3, 2)`.
3. `SCORE_BINS = range(1, 4)` -> `{1: 2, 2: 0, 3: 1} != {0: 1, 1: 2, 2: 0, 3: 1}`.
4. `classify_max_tokens_hits` đếm mọi `stop_reason` khác None -> `5 != 2`.
5. Eval truyền `{}` thay `routing` cho `decide_route` -> `test_eval_uses_runner_route_function` đỏ (đối số khác runner).

## Seen but not touched
Không có. Lệnh eval thật trên site dev thuộc qa (AC-15).
