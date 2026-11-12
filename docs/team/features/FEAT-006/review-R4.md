# Review R4 — FEAT-006 rework 1

Verdict: approve (1 vòng, 0 finding blocker/major/minor).
Diff: `git diff 8c8741d..team/FEAT-006-rw1-r4 -- erp_ai` (commit 7002d0f, 5 file).

- (a) `(model or "").startswith(...)` tại `erp_ai/gateway/__init__.py:154`; test `test_classify_with_no_model_anywhere_raises_gateway_error_not_attribute_error` đỏ (AttributeError) rồi xanh, khẳng định GatewayError `bad_request` và không gửi `thinking`.
- (b) description `model_classify` và `model_classify_default` (≈220 ký tự) nói chỉ `claude-haiku-*` tắt thinking, model khác có thể bị cắt ở trần token; dữ liệu ghim cập nhật, đỏ rồi xanh.

Mục "không kiểm chứng được từ diff" (chạy lại test): tech-lead xác nhận cây `erp_ai/` của đầu merge 661eca9 giống hệt đầu dev 7002d0f (`git diff --stat` rỗng), dev đã chạy `cmd.test` trên 7002d0f: `Ran 885 tests in 161.130s` / `OK`; pre-commit 5 file đổi: pass. Hook role-policy không cho tech-lead chạy `bench` trong worktree nên không chạy lại.

deferred: không có.
