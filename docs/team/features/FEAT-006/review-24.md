# Review T24 — approve (vòng 3)

Feature: FEAT-006 · Task: T24 (test chốt: chống chèn lệnh, quyền ghim, thông tin nhạy cảm, schema tool) · Reviewer: team:reviewer · Số vòng: 3 (2 vòng sửa; max_rework=3, không vượt)

Lệnh diff: vòng 1 `git diff 9135b85..team/FEAT-006-task-24` (8439972); vòng 2 `git diff 8439972..team/FEAT-006-task-24-rework1 -- erp_ai` (1cb487e); vòng 3 `git diff 1cb487e..team/FEAT-006-task-24-rework2 -- erp_ai` (6788b93). Merge 0ab015a. Mã sản xuất không đổi (`git diff --stat 9135b85 HEAD -- erp_ai ':!*test_*'` rỗng).

## Verdict: approve

- Vòng 1: request-changes, 2 major STD-TEST-2: NFR-4 gieo khóa vào hàng credential mà lần chạy không đọc; AC-17 chỉ phủ một ca (`review-24-round1.md`).
- Vòng 2: AC-17 ADDRESSED (ghim role ở `RoutingTestBase.setUp` + test role set = tập ghim); NFR-4 NOT ADDRESSED ở đường comment (`review-24-round2.md`).
- Vòng 3: ADDRESSED (khóa trong `prefixes` + ca NO_SLA đăng đúng 1 comment; đột biến nối `routing_config` vào comment làm test đỏ). Không finding mới. Khác defect giữa các vòng (mỗi vòng một chỗ rò khác nhau), không lặp cùng defect hai vòng.

## Kiểm bằng lệnh thật

- Dev (vòng 3): `erp_ai.agent.test_runner_routing` Ran 61 OK; `bench --site miyano run-tests --app erp_ai` Ran 851 tests OK (đầu nhánh task 6788b93); pre-commit pass.
- Tech-lead: `git diff --stat 6788b93 HEAD -- . ':!docs'` rỗng sau merge 0ab015a (cây mã trùng cây đã chạy xanh).

## Deferred

- Subtest bad-rules tạo phiếu bằng `make_ticket` khi agent đã bật (pattern có sẵn).
- designer: `value_before` chỉ có `ticket` vs design 3.5 (`assign`/`task`); mở rộng hàng test-plan 493 ("gieo vào credential") thành "mọi đầu vào cấu hình lần chạy đọc".
- minor (d) `_schema_keys` không đi qua `anyOf`/`oneOf`/`additionalProperties`/`enum`; (e) AC-9 priority "High" trùng giữa mapping và R-rule.
