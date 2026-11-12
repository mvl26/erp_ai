Feature: BUG-001
Stage: build
Author-agent: tech-lead
Date: 2026-11-12
Approved-by:

# Tasks BUG-001

Cỡ S, một task. Không có cặp task chung file (preflight: 1 task, không mâu thuẫn).

- [x] T1 — 400 "Your credit balance is too low…" → `_quota()` (cùng Action hàng 6) — files: erp_ai/gateway/breaker.py, erp_ai/gateway/test_breaker.py — test: erp_ai/gateway/test_breaker.py — depends: —

Progress T1: BASE=cda9aa1b733514654d7684a904a7ef1159e754a4 (team/BUG-001), nhánh task team/BUG-001-task-1

Receives: `ApiFailure(status=400, message_prefix="Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing…"[:100])`
Returns: `Action(QUOTA, None, True, "message", "quota")` (giống hàng 6).

Tiêu chí:
- Test bảng có ca mới "row6 400 credit balance" (prefix thật, cắt 100 ký tự như `client.py:55` `MESSAGE_PREFIX_LENGTH`): đỏ trước (assertion), xanh sau.
- Ca "row8 400 other" vẫn là `bad_request`.
- Chỉ sửa trong touchpoints; không đổi `design.md` FEAT-001 (ghi chú ở BUG-001 artifacts).

One-file-one-owner: breaker.py, test_breaker.py -> T1.
