# Review 09 — T8 (DocType ERP AI Credential)

- Verdict: approve (vòng 1)
- Số vòng: 1
- Diff: `git diff b27a20b..team/FEAT-001-task-8`; merge aac62a0
- Checklist (10): 10/10; 18 trường khớp design 2.2 từng trường

## Findings
Không có blocker/major.

## Đã giải quyết "không kiểm được từ diff"
- Red/green: dev dán đỏ (5 test thất bại vì thiếu DocType), `migrate` exit 0, xanh 5 test; sau merge `migrate` exit 0, `--app erp_ai` Ran 85 tests OK, pre-commit exit 0.

## Deferred
- minor: test chưa ghim đầy đủ tập trường/options/precision (dev tự quyết).
- Cho T9: `budget_month_usd` kiểu Currency không có `options` nên theo tiền tệ site; kiểm khi làm `monthly_budget_usd`. AC-19 chỉ được bảo vệ phía server khi `ERPAISetting.validate` khôi phục trường tự quản (T9).
