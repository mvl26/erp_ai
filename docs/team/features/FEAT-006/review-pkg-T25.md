# Review package FEAT-006 T25 (eval offline: khớp ưu tiên, nhóm, phân bố điểm, trần token), vòng 1

Repo: `/home/miyano/frappe-bench/apps/erp_ai` (worktree `.claude/worktrees/feat-006`). BASE=601ebe7; head=team/FEAT-006-task-25 (b0df8e3).
Lệnh diff (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/feat-006 diff 601ebe7..team/FEAT-006-task-25 -- erp_ai`
Commits: `git -C ... log --oneline 601ebe7..team/FEAT-006-task-25`; stat: `git -C ... diff --stat 601ebe7..team/FEAT-006-task-25`.

Commits:
- b0df8e3 feat(eval): priority/team match, score distribution, token ceiling (FEAT-006)

Stat (mã): run_eval.py +93, test_run_eval.py +216.

Touchpoints cho phép: erp_ai/eval/run_eval.py, erp_ai/eval/test_run_eval.py.

Tiêu chí (tasks.md T25, spec AC-15, D-8, A-8): `_predict(row, routing, mapping)` trả category/complexity/importance/priority/agent_group/output_tokens/stop_reason; `compute_metrics` (hàm thuần) thêm `priority`, `team` ({count, correct, accuracy}; bỏ dòng thiếu nhãn hoặc dự đoán None), `score_distribution` (0..3), `classify_output_tokens_max`, `classify_max_tokens_hits`; `format_report` in 4 khối; `run` đọc `routing_rules`; eval dùng CÙNG hàm route với runner (`decide_route`) — không viết lại R1–R5. Ngưỡng 0,85/0,70 chỉ để đọc. Expect: `TestRunEval::test_priority_team_match_and_score_distribution`, `TestRunEvalRun::test_eval_uses_runner_route_function`. Lệnh eval thật là của qa.
Dev báo bằng chứng đột biến trong `docs/team/features/FEAT-006/dev-T25.md` (nhánh task).
