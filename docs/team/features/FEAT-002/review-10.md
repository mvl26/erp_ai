Feature: FEAT-002
Stage: build
Author-agent: reviewer
Date: 2026-11-12
Approved-by:

# Review 10 — FEAT-002 T10

- Diff: `git diff 064b57e..team/FEAT-002-task-10` (vòng 2: `git diff 08bd1ec..team/FEAT-002-task-10`; vòng 3: `git diff b797c89..team/FEAT-002-task-10`)
- Vòng: 3 (max_rework=3; vòng 3 sạch)
- Verdict: approve

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major (vòng 1, ADDRESSED) | STD-TEST-8 | test_architecture.py:1600 | tự kiểm bộ quét xóa của install không truyền `fragment`; không có ca `delete_doc` đúng nhưng nằm ngoài `before_uninstall` | thêm ca `ensure_setup` chứa xóa duy nhất; truyền fragment |
| major (vòng 1, ADDRESSED) | STD-TEST-8 | test_architecture.py:1530 | nhánh `RUN_STATUS_FORBIDDEN_ATTRIBUTES` không có ca riêng (`frappe.cache.hset`, `get_value`, `db.set_single_value`) | thêm ca và kiểm fragment |
| major (vòng 1, ADDRESSED) | STD-TEST-8 | test_architecture.py:734 | luật `publish_realtime` bỏ sót `getattr`/`get_attr`/`import_module`, bí danh trong run_status, `import frappe as f` | quét chuỗi, giải bí danh bằng `resolved_name`, cấm gán lại; mỗi dạng một ca |
| major (vòng 2, ADDRESSED) | STD-TEST-8 | test_architecture.py:820 | bộ quét "không ghi" chỉ xét `ast.Attribute`, bỏ sót `from frappe import db; db.set_single_value` | xét `ast.Name \| ast.Attribute`, 2 ca mới |

## Review checklist (10)
1–10: đạt ở vòng 3. Chỉ sửa `erp_ai/tests/test_architecture.py`; không đổi mã sản phẩm.

## Bằng chứng dev
- ĐỎ: vòng 1 bảy đột biến mã sản phẩm đều đỏ đúng luật; vòng 2 9 ca mới đỏ (failures=9) trước khi nâng bộ quét; vòng 3 2 ca đỏ (failures=2, "scanner missed the violation").
- XANH: `tests.test_architecture` Ran 58 OK; lint đạt. Luật quét cây thật xanh: không dương tính giả trên mã hiện tại.
- Merge xem tasks.md.

## deferred
- Trong `run_status.py`, `getattr(frappe, "publish_realtime")(...)` bỏ qua kiểm `room=`/`after_commit=False` (quét chuỗi chỉ chạy ngoài run_status); hành vi được test chạy thật (`test_runner_status` kiểm room, nhánh rollback mất `done` nếu `after_commit=True`) che lại.
- minor: chuỗi ngoài run_status chưa truyền fragment; ca `from frappe import realtime as rt` chồng với luật import-module; ca R-1 `agent/policy.py` đã bị bộ quét cũ bắt; bản đồ hằng R-1 chỉ đọc `Assign` mức module; `from frappe import db as d` chưa có ca; `getattr(frappe, "db")` chưa bắt; tham số cục bộ trùng tên `db`/`cache` bị gắn cờ (thiên về an toàn).
