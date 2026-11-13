# Review T26 — Luật kiến trúc ADR-019..021 và 2 bảo vệ tĩnh (FEAT-006)

Verdict: approve (vòng 2 của 2; 1 vòng sửa). Vòng 1 request-changes: xem `review-26-round1.md`.
BASE=2cd3ba3; đầu nhánh task `team/FEAT-006-task-26-rework1` = 136abf5; merge e5d9b38.
Diff vòng 1: `git diff 2cd3ba3..4ad5b17 -- erp_ai`; diff vòng sửa (scoped): `git diff 4ad5b17..136abf5 -- erp_ai`; cả task: `git diff 2cd3ba3..136abf5 -- erp_ai`.
Touchpoint: chỉ `erp_ai/tests/test_architecture.py` (mã sản xuất không đổi). Tầng 1: 10/10.

## Vòng 1: findings
- major 1 STD-TEST-2 (`assign_agent` không bị quét), major 2 STD-TEST-2 (`db_update` không bị quét), major 3 STD-TEST-8 (`doc.set("response_by")` và hằng chứa tên trường SLA không bị quét).
- Minor a, b, c, d, f làm trong vòng sửa; e bỏ qua có chủ đích (không quét comment `#`).

## Vòng 2 (scoped): 3 major và minor a, b, c, d, f đều ADDRESSED; không finding mới ở mức blocker/major.

## cmd.test
- `erp_ai.tests.test_architecture`: Ran 97 tests, OK (dev, đầu nhánh task 136abf5).
- `bench --site miyano run-tests --app erp_ai` (dev chạy một mình trên 136abf5): Ran 880 tests, OK. Tech-lead: `git diff --stat 136abf5 team/FEAT-006 -- . ':!docs'` rỗng, cây mã sau merge e5d9b38 trùng cây đã xanh.

## Quyết định của tech-lead cho mục "không kiểm được từ diff"
- Đầu ra đỏ/xanh của dev: dán ở `dev-T26.md`, `dev-T26-r2.md`; C5 chạy lại toàn bộ.
- install.py không ghi literal `auto_assign_enabled` (reviewer xác nhận bằng grep): ổn.

## Deferred
- Cho designer: ADR-019 Ràng buộc nhắc "tên bộ phận của bảng 16.2" không xuất hiện trong `erp_ai/agent/`, design dòng 479 và tasks.md T26 chỉ giữ tên người; ADR-020 "mã của bước định tuyến" gồm `runner._route` nhưng bộ quét `.save()` chỉ phủ `route_ticket.py` (runner không có `.save()` hôm nay).
- Minor (reviewer vòng 2, dev tùy): `assign_agent` khớp cả tên kết thúc bằng nó (`unassign_agent`); `_creates_todo` báo "creates" cả `get_doc("ToDo", name)`; docstring `check_assign_to_only_in_route_module` còn mô tả cũ; `getattr(doc, "db_update")()` và handler bọc `lambda`/`partial` chưa bắt; dạng đối số từ khóa (`db_set(fieldname="response_by")`, `set_value(..., fieldname=...)`, `get_doc(doctype="ToDo")`) và tên trường trong giá trị dict/default đối số chưa quét.
