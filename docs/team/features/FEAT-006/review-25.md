# Review T25 — approve (vòng 3)

Feature: FEAT-006 · Task: T25 (eval offline: khớp ưu tiên, nhóm, phân bố điểm, trần token) · Reviewer: team:reviewer · Số vòng: 3 (2 vòng sửa; max_rework=3, không vượt)

Lệnh diff: vòng 1 `git diff 601ebe7..team/FEAT-006-task-25 -- erp_ai` (b0df8e3); vòng 2 `git diff b0df8e3..team/FEAT-006-task-25-rework1 -- erp_ai` (f790a29); vòng 3 `git diff f790a29..team/FEAT-006-task-25-rework2 -- erp_ai` (e8db035). Merge 89523a1. Chỉ `run_eval.py` và `test_run_eval.py` đổi.

## Verdict: approve

- Vòng 1: request-changes, 3 major (STD-TEST-2 mapping trùng mặc định nên không bắt được lỗi truyền sai; STD-TEST-8 `output_tokens` của phản hồi cụt không được khẳng định; STD-TEST-6 test dựa mapping sống của site) — `review-25-round1.md`.
- Vòng 2: 3 major ADDRESSED; finding mới STD-TEST-6 (test mới của vòng sửa lại đọc mapping sống) — `review-25-round2.md`.
- Vòng 3: ADDRESSED bằng seed `category_mapping` + `routing_rules` ở `TestRunEvalRun.setUp` (cũng sửa 5 test deferred). Không finding mới. Mỗi vòng là một lỗi khác, không lặp cùng defect hai vòng liên tiếp ngoài họ "dựa dữ liệu site" ở vòng 2 → vòng 3 (khác test).

## Kiểm bằng lệnh thật

- Dev (vòng 3): `erp_ai.eval.test_run_eval` Ran 22 OK; `bench --site miyano run-tests --app erp_ai` Ran 860 tests OK (đầu nhánh task e8db035); pre-commit pass; lớp chạy trên cấu hình site lạ (subclass tạm, không commit): 26/26 sau seed, 5 đỏ trước seed.
- Tech-lead: `git diff --stat e8db035 HEAD -- . ':!docs'` rỗng sau merge 89523a1.

## Deferred

- minor: `test_run_reports_priority_team_scores_and_tokens` (:494-496) lặp seed đã có ở setUp.
- Lệnh eval thật và `classify_output_tokens_max` thật: qa (AC-15).
