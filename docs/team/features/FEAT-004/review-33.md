Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 33 — FEAT-004 T33

- Diff: `git diff cb40420..team/FEAT-004-task-33` (1 commit `42887cd`, 1 file, +22)
- Vòng: 1
- Verdict: approve

## Phát hiện (chỉ blocker/major)
Không có.

minor | — | — | 2 điểm nhỏ: `:409` đăng ký `addCleanup(frappe.db.rollback)` lần nữa dù `setUp:62` đã có; kiểm `desk_access` ở `:411` lặp một phần `:394` | tùy dev

## Review checklist (10)
1–4 đạt; 5 không áp dụng (chỉ test); 6–10 đạt. `install.py` không đổi; test FEAT-006 không đổi.

## Bằng chứng của dev
- RED (ép `desk_access = 0` tạm thời trước bước cài đặt, dòng đó không nằm trong commit): `AssertionError: 0 != 1` → `FAILED (failures=1)`
- GREEN: `Ran 33 tests in 27.164s` / `OK`; lint sạch

## Không kiểm được từ diff (tech-lead xử lý)
- Người duyệt mở được form đề xuất: cần quyền read của `ERP AI Instructor` trên `ERP AI Change Proposal` → T12 (`test_proposal_json_permissions_...`).
- Gán role cho người thật trên site: việc của quản trị sau G4 (UNVERIFIED).

## deferred
- Ghi nhận của dev: `install._ensure_roles` không đặt lại `desk_access` của role đã có (khớp D-11, không sửa).
