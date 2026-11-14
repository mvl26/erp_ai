Feature: FEAT-005
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 17 — FEAT-005 T17

Tech-lead chép từ tin trả về của reviewer (reviewer không ghi file).

- Diff: `git diff aaad5ec..a7c4ecf` (nhánh `team/FEAT-005-task-17`, 1 commit, `erp_ai/agent/tools/test_site_api.py` +7); merge `27341b8`
- Vòng: 1
- Verdict: approve

## Vòng 1 — approve (`aaad5ec..a7c4ecf`)

Lớp 1: đạt. `test_forbidden_roles_are_exactly_the_six_admin_roles_of_ac14` (`test_site_api.py:187-192`) so bằng nhau cả tập với sáu chuỗi chữ viết ra trong test, không dựng từ hằng `ROLE_*`, không lặp trên `FORBIDDEN_ROLES`; sáu chuỗi khớp sáu role của AC-14 [changed] (`constants.py:2-3` xác nhận giá trị `ROLE_AGENT`, `ROLE_INSTRUCTOR`). Chỉ file touchpoint, không sửa mã sản phẩm.

Checklist (10): 10/10 đạt. Không dấu skip; không phép khẳng định có sẵn nào bị đổi; test không đọc DB hay đồng hồ; commit `test(site_api): … (FEAT-005)`, không dòng ghi công AI.

- Phát hiện: không có, ở mọi mức.
- Bằng chứng của dev (task chỉ thêm test, đỏ bằng đột biến `site_api.py`, đã trả lại): bớt `"Guest"` → `AssertionError: frozenset({'ERP AI Agent', 'System Manage[44 chars]or'}) != {'ERP AI Agent', 'System Manager', 'All',[42 chars]est'}` / `FAILED (failures=1)`; thêm `"Blogger"` → `AssertionError: frozenset({'System Manager', 'ERP AI Inst[64 chars]st'}) != {'System Manager', 'ERP AI Instructor', '[42 chars]est'}` / `FAILED (failures=1)`; GREEN `Ran 1 test in 0.714s` / `OK`, cả module `Ran 74 tests in 25.185s` / `OK`.

## Tech-lead đã kiểm

- Sau merge `27341b8`, trong khóa `miyano-site.lock`: test_site_api `Ran 74 tests in 22.446s` / `OK`.
- `git diff --name-only aaad5ec..a7c4ecf` = `erp_ai/agent/tools/test_site_api.py` (đúng touchpoint).

## Không kiểm được từ diff

- Mọi phép từ chối role có đi qua `FORBIDDEN_ROLES` không: tech-lead đã `grep -rn "FORBIDDEN_ROLES" erp_ai --include=*.py` trên `8666a23`: dùng ở `site_api.py:178` (đường Role Profile và `roles`), `tasks.py:12,125` (dấu `[QUẢN TRỊ]`), `test_tasks.py:857`; test từ chối từng role thuộc FEAT-004 AC-31 (`test_refuses_each_forbidden_role`, `test_refuses_role_profile_holding_a_forbidden_role`) → không thiếu gì cho T17; qa đối chiếu lại ở verify.

## deferred

- Không có.
