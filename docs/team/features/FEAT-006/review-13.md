Feature: FEAT-006
Stage: build
Author-agent: tech-lead (tổng hợp từ reviewer)
Date: 2026-11-12
Approved-by:

# Review 13 — FEAT-006 T13 (`site_facts`: 5 phép đọc hệ thống chỉ-đọc)

- Diff: `git diff 5688f13..388f562` (nhánh `team/FEAT-006-task-13-rework1`, commit fc10afc + 388f562; merge `43cca1f`)
- Vòng: 2 (vòng 1 request-changes, 1 vòng sửa, vòng 2 scoped re-review approve)
- Verdict: approve

## Phát hiện vòng 1
| severity | STD | file:line | description | fix | vòng 2 |
|---|---|---|---|---|---|
| major | STD-TEST-2 | erp_ai/agent/test_site_facts.py:40-54 | Bỏ bộ lọc `reference_type: "HD Ticket"` trong `ticket_assignments` mà mọi test vẫn xanh (không có ToDo mồi khác `reference_type`) | thêm ToDo mồi `reference_type="Task"`, `reference_name=self.ticket`, Open | ADDRESSED |
| minor | — | site_facts.py:40 | bộ lọc `parent=sla` chỉ được dữ liệu sẵn của site bảo vệ | gieo SLA mồi cùng `priority` khác giờ | ADDRESSED |
| minor | — | test_site_facts.py | ca ghim role không kiểm tiền đề "Agent không đọc được SLA" | khẳng định `has_permission(...)` là False trước | ADDRESSED |
| minor | — | site_facts.py / test_site_facts.py | `order_by` chưa khóa; docstring nói "frappe.db" trong khi dùng `get_all`; tên test khẳng định nhiều hơn điều kiểm | `assertEqual` có thứ tự; sửa docstring; thêm khẳng định dưới `pin_agent_roles` | ADDRESSED |

## Phát hiện vòng 2
Không có blocker/major. minor: dòng docstring `site_facts.py:3` dài 113 ký tự (> 110, E501 đang bị bỏ qua nên lint qua); comment `test_site_facts.py:100-101` nói chưa chính xác với thứ tự tăng dần (test vẫn đỏ đúng).

## Deferred
- `applied_sla` trả `resolution_s=None` khi phiếu có `sla` mà không có `priority`: T20 (kiểm SLA) phải xử lý None, theo design 4.2 bước 2 gọi `sla_lag` ngay.
- Kết quả `site_facts` không được đưa cho mô hình hay comment (ADR-021 QĐ 4): do các nơi gọi ở T20/T25 giữ.
- Hai khẳng định phụ thuộc trạng thái site `miyano` (quyền DocPerm của role Agent trên HD Service Level Agreement; chèn SLA mồi thứ hai): đã chạy xanh trên `miyano`.

## Bằng chứng chạy (dev)
- RED vòng 1: 5 test đỏ vì khẳng định trên bản khung trả giá trị sai (ví dụ `None != {'sla': ..., 'priority': 'High', 'resolution_s': 28800}`, `False is not true`), không phải lỗi import.
- Đột biến vòng sửa (đỏ rồi hoàn tác xanh): bỏ lọc `reference_type` → `FAIL test_assignments_include_closed_exclude_cancelled` ("Lists differ"); bỏ lọc `parent` → `FAIL test_applied_sla_reads_priority_row` (`277200.0 != 28800`); `order_by="creation desc"` → `FAIL test_assignments_include_closed_exclude_cancelled`.
- GREEN: `erp_ai.agent.test_site_facts` Ran 7 OK; `cmd.test` (`--app erp_ai`) trên đầu nhánh task 388f562: `Ran 751 tests`, `OK`; lint pre-commit sạch.
- Sau merge: `git diff --stat 388f562 HEAD -- . ':!docs'` rỗng.

## Review checklist (10)
1–10: đạt (reviewer approve vòng 2).
