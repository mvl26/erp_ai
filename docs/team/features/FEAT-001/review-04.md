# Review T4 (FEAT-001)

Verdict: approve (round 1, 0 rework)
Diff: `git diff a85f798..team/FEAT-001-task-4` (head 47dede6).
Reviewer: checklist 10/10, đủ 9 hàng của design 3.4.3, không có blocker hay major.
minor | — | — | 2 điểm: (a) `max(error_count, 1)` thừa; (b) `decide` thiếu type hint | dev's call (deferred)
Hợp đồng cho T15: `ApiFailure.kind` phải là đúng chuỗi "timeout" / "connection" cho lỗi không có status, nếu không `decide` rơi vào `unexpected`. `error_count` là giá trị MỚI đã tăng. Kiểm khi review T15.
Bằng chứng dev: RED (stub, 24 lỗi do thiếu hành vi), GREEN `Ran 6 tests OK`, `--app erp_ai` Ran 17 OK, pre-commit exit 0.
