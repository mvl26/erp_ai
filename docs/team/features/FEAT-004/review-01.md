Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 01 — FEAT-004 T1

- Diff: `git diff cb40420..team/FEAT-004-task-1` (1 commit `86852bd`, 1 file `dev-notes.md`, +101)
- Vòng: 1
- Verdict: approve

## Phát hiện (chỉ blocker/major)
Không có.

minor | — | — | 2 điểm nhỏ: `dev-notes.md:24` thiếu mã thoát của lần migrate 1; `dev-notes.md:38` ghi "20 dòng cuối" nhưng khối có 19 dòng | tùy dev

## Review checklist (10)
1–2 đạt; 3–5 không áp dụng (bước đo, không có mã); 6–10 đạt.

## Bằng chứng của dev (bước đo, không có RED/GREEN)
- migrate 35.514 / 39.767 / 38.007 s; build `erp_ai` 2.180 / 1.634 / 1.645 s; build `hrms` 18.408 / 17.389 / 18.016 s; lớn nhất 39.767 s ≤ 540 s → đạt
- `git -C apps/hrms status --porcelain` rỗng trước và sau; `frappe`, `erpnext`, `helpdesk` không build, ghi UNVERIFIED (quyết định team-leader 2026-11-13)

## Không kiểm được từ diff (tech-lead xử lý)
- `sites/assets/erp_ai` sau khi đo: tech-lead chạy `readlink` 2026-11-13 → `/home/miyano/frappe-bench/apps/erp_ai/erp_ai/public` (đã trở về cây chính).
- HEAD/`status` của `frappe`, `erpnext`, `helpdesk` trước/sau: không ghi ở T1; T34 và qa so (NFR-9).
- Số đo là migrate không đổi schema; migrate sau khi đổi DocType JSON chưa đo riêng (dư ~13 lần) → deferred.

## deferred
- `design.md:736` và ADR-013 còn ghi "chưa đo": writer đưa số vào As-Built.
- `bench build --app` với `PYTHONPATH` trỏ worktree đổi liên kết `sites/assets/erp_ai` của site chung: không task nào khác được chạy `bench build`.
