# Review T23 — approve (vòng 2)

Feature: FEAT-006 · Task: T23 (prompt suy luận: bảng routing dựng từ cấu hình) · Reviewer: team:reviewer · Số vòng: 2 (1 vòng sửa)

Lệnh diff: vòng 1 `git diff 1117974..team/FEAT-006-task-23 -- erp_ai` (a123a3a); vòng 2 (scoped) `git diff a123a3a..team/FEAT-006-task-23-rework1 -- erp_ai` (2a8cf58). Merge 1d35b81.

## Verdict: approve

- Vòng 1: request-changes, 2 major STD-TEST-8 (dòng E không được khẳng định, fixture `team` trùng tên bộ phận, thiếu ca gộp/khử trùng; test runner chỉ phủ nguồn `default` của `_config_users`), chi tiết ở `review-23-round1.md`.
- Vòng 2: cả hai ADDRESSED (4 đột biến đỏ rồi xanh: `== "D"`, khóa dict thay `d["team"]`, bỏ dòng `prefixes`, bỏ dòng `head`; 4 minor cũng xử lý). Không finding mới.

## Kiểm bằng lệnh thật

- Dev: `test_classification` Ran 34 OK; `test_agent_runner` Ran 57 OK; `bench --site miyano run-tests --app erp_ai` Ran 841 tests OK (đầu nhánh task 2a8cf58); pre-commit pass.
- Tech-lead: `git diff --stat 2a8cf58 HEAD -- . ':!docs'` rỗng sau merge 1d35b81; `git grep -n ROUTING_TABLE -- erp_ai` rỗng.

## Deferred

- Không có. Lưu ý cho T26: quét tên người phải theo ranh giới từ ("Việt Nam", "Tiếng Việt" là trùng chữ trong `prompts.py`).
