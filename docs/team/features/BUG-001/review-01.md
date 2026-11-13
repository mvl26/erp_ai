Feature: BUG-001
Stage: build
Author-agent: tech-lead
Date: 2026-11-12
Approved-by:

# Review 01 — BUG-001 T1

- Verdict: approve (reviewer độc lập, ngữ cảnh mới; 1 vòng, 0 rework; Review checklist 10/10)
- Rounds: 1 (max_rework=3)
- Diff: `git diff cda9aa1b733514654d7684a904a7ef1159e754a4..team/BUG-001-task-1` (commit 283b174; merge f11bc3c vào team/BUG-001)
- Touchpoints: chỉ `erp_ai/gateway/breaker.py`, `erp_ai/gateway/test_breaker.py`.

## Bằng chứng dev (red -> green)
- RED: `Ran 6 tests, FAILED (failures=1)`: test_breaker_table [row6 400 credit balance] AssertionError: Action(new_status=None, ..., 'bad_request') != Action(new_status='Hết hạn mức', ..., 'quota') (assertion, không phải lỗi import).
- GREEN: test_breaker `Ran 6 tests ... OK`; test_gateway `Ran 61 tests ... OK`.
- Lint: pre-commit trên 2 file qua.
- Prefix: "Your credit balance is too low" = 30 ký tự < `MESSAGE_PREFIX_LENGTH` = 100 (client.py:7), vừa khi bị cắt.

## Findings
Không có blocker/major.
- minor | — | test_breaker.py | gợi ý thêm ca 422 với CREDIT_PREFIX; giá trị thấp (cùng một điều kiện ở breaker.py:57) | deferred

## Resolve "không kiểm được từ diff"
- Red/green và lint: có trong báo cáo dev (trên); `cmd.test` đầy đủ không chạy được bởi tech-lead (hook role-policy chặn lệnh ghép; xem journal).
- Hành vi thật trên site (chuyển `Hết hạn mức`, gửi tin, chuyển khóa): gateway/__init__.py:110 gọi `decide` không đổi chữ ký/Action; thuộc verify.

## Deferred
- design.md FEAT-001 §3.4.3 hàng 6 cần thêm "hoặc `Your credit balance is too low`" để bảng khớp mã. Không sửa trong T1 (tài liệu FEAT-001); ghi chú ở đây, writer/As-Built BUG-001 hoặc designer xử lý.
