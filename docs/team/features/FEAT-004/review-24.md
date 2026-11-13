Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 24 — FEAT-004 T24

- Diff: `git diff cb40420..team/FEAT-004-task-24` (1 commit `2b004ff`, 2 file, +76/-2)
- Vòng: 1
- Verdict: approve

## Phát hiện (chỉ blocker/major)
Không có.

minor | — | — | 1 điểm nhỏ: `test_classification.py:369-376` chỉ kiểm vài cụm từ của `CHANGE_TOOLS_BLOCK`, không so nguyên khối với chữ design 3.7 (xóa dòng "Chỉ người có vai trò ERP AI Instructor duyệt…" thì test vẫn xanh) | tùy dev

## Review checklist (10)
1–4 đạt; 5 không áp dụng; 6–10 đạt. Khối trùng design 3.7 từng dòng (16 dòng, `grep -Fx`); `change_tools=False` cho chuỗi trùng bản FEAT-006.

## Bằng chứng của dev
- RED: `FAILED (errors=2)`: `AttributeError: module 'erp_ai.agent.prompts' has no attribute 'CHANGE_TOOLS_BLOCK'`, `TypeError: build_reason_system() got an unexpected keyword argument 'change_tools'`
- GREEN: `Ran 36 tests in 0.012s` / `OK`; lint sạch ở lần chạy thứ hai

## Không kiểm được từ diff (tech-lead xử lý)
- Nền `cb40420` có phải bản FEAT-006 mà AC-1 nói: đúng, `erp_ai/` ở `cb40420` giống hệt `f039112` (đầu `team/FEAT-006`), chỉ khác `docs/`.
- Runner có truyền `change_tools=` không: việc của T29.

## deferred
- So nguyên khối `CHANGE_TOOLS_BLOCK` với design 3.7 (minor).
