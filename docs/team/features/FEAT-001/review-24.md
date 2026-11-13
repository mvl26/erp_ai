# Review 24 — FEAT-001 T16 (cổng: chọn khóa và ghi trạng thái khóa)

- Verdict: approve (vòng 2; 1 vòng rework)
- Diff: `git diff 0c5e216..team/FEAT-001-task-16` (head 696b2c8); merge e50754a
- Vòng 1 request-changes: major STD-TEST-8 (guard `limit_reset_at` không test: dòng seed mang `None`). Vòng 2 (FIX_BASE 545d4be): ADDRESSED; kèm quyết định tech-lead: `apply_failure(..., request_id=None)`; minor idx tie-break và `fields=["*"]` cũng đã sửa
- Bằng chứng dev: RED Ran 22 (errors=12, stub); GREEN test_gateway Ran 23 OK; `--app erp_ai` Ran 199 OK; pre-commit exit 0; 23 đột biến một nhánh đều đỏ

## Findings
Không còn blocker/major.

## Deferred (cho T17)
- T17 phải truyền `request_id` (từ `RawReply.request_id`/lỗi API) vào `apply_failure`; `ApiFailure` không có trường này nên quên thì im lặng.
- T17 truyền cho `decide()` đúng `error_count` cũ + 1 (apply_failure tự đọc DB và cộng 1); D-21 (chỉ báo khi đổi trạng thái) cần trạng thái cũ do T17 đọc trước `apply_failure`; `apply_failure` không gửi thông báo.
- T17 chuẩn hóa `usage` None → 0 trước `compute_cost` (review-19).
- Design 3.4.3: ghi nhận `apply_success` xóa `paused_until` (cần, không phải scope creep) khi asbuilt.
- minor: docstring `apply_failure` chưa nhắc `request_id`; `error_count` đọc-rồi-ghi không khóa hàng (hai worker có thể mất một lần đếm).
