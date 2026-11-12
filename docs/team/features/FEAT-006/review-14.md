Feature: FEAT-006
Stage: build
Author-agent: tech-lead (tổng hợp từ reviewer)
Date: 2026-11-12
Approved-by:

# Review 14 — FEAT-006 T14 (`apply_route` đầy đủ: quyền, từ chối, before/after, SLA do Helpdesk chọn)

- Diff: `git diff b74303f..809fac6` (nhánh `team/FEAT-006-task-14-rework1b`, commit 2f639c0 + aee788d + 809fac6; merge `8fdc05f`)
- Vòng: 2 (vòng 1 request-changes, 1 vòng sửa gồm một lần DESIGN_CONFLICT được giải, vòng 2 scoped re-review approve)
- Verdict: approve

## Phát hiện vòng 1
| severity | STD | file:line | description | fix | vòng 2 |
|---|---|---|---|---|---|
| major | STD-TEST-2 | erp_ai/agent/tools/route_ticket.py:44,49 | `before`/`after` liệt kê mọi trường được ghi, không phải trường đã đổi (phiếu đã `priority="Medium"` vẫn hiện); test khóa mục không đổi; tên test có "only" mà không khẳng định | chỉ giữ trường `doc.get(field) != value`; thêm ca phiếu đã `Medium` | ADDRESSED |
| major | STD-TEST-8 | erp_ai/agent/tools/test_route_ticket.py:176-179 | test giả `has_permlevel_access_to` bỏ qua `permission_type`; đổi `"write"` thành `"read"` ở mã mà test vẫn xanh | giả chỉ từ chối khi `write`; thêm ca dấu chỉ thiếu ghi | ADDRESSED |
| minor | — | test_route_ticket.py | mồi `priority` trùng mặc định; comment L0 sai; SLA `Default` của site không cách ly | `priority="Low"`; sửa comment; (c) dev bỏ qua, test phụ thuộc nay đặt `priority` tường minh | ADDRESSED (a)(b); (c) bỏ qua có ghi lý do |

## Đổi touchpoint (tech-lead, ghi ở progress.md)
Dev báo DESIGN_CONFLICT: hành vi đúng của tiêu chí ("`before`/`after` có đúng các trường đã đổi") làm 3 test của `erp_ai/agent/test_agent_runner.py` đỏ vì còn kỳ vọng `ai_complexity: 0`, `ai_importance: 0` trong `after`. Tech-lead mở rộng T14 đúng 1 file, chỉ sửa kỳ vọng (STD-TEST-5), cùng kiểu T1/T6/T11 đã được chấp nhận; dev sau sửa 3 kỳ vọng (bỏ hai khóa không đổi), `cmd.test` 764 OK.

## Phát hiện vòng 2
Không có blocker/major. minor: (1) `ai_score_reason` từ NULL sang `""` bị tính là "đã đổi" (`doc.get` trả `None`), nên 3 test runner phải kỳ vọng `"ai_score_reason": ""` trong `after` dù người dùng không thấy gì đổi; chuẩn hóa rỗng cho trường chữ sẽ gọn hơn; (2) tên `test_before_after_only_changed_fields_and_one_save` còn chữ "only" trong khi ca kiểm vắng mặt nằm ở test mới.

## Deferred
- Rủi ro tiềm ẩn ở `runner.py:276`: `applied=1` chỉ khi `result.get("after")` khác rỗng. Nay `after` có thể rỗng mà phiếu vẫn được lưu (dấu `ai_classified_by`, `ai_updated_at`); luồng hiện tại luôn có `ai_confidence` None → giá trị nên chưa lộ. T20 viết lại `_route` (cập nhật bản ghi `classify` một lần): dùng `result["ok"]` cho `applied`, không dùng `after` khác rỗng. Ghi vào handoff T20.
- Vòng lặp dấu `("ai_classified_by", "ai_updated_at")` ở `route_ticket.py:37`: chỉ `ai_classified_by` có ca riêng; thêm ca chỉ thiếu ghi trên `ai_updated_at`.
- design.md 3.4 nói `apply_route` từ chối khi thiếu quyền ghi MỘT trường; tasks.md T14 nói bỏ trường và ghi `skipped`; mã theo tasks.md cho 7 trường route/điểm và từ chối cho 2 trường dấu (đúng: không lưu giá trị AI mà không có dấu, giữ bảo vệ AC-7b). Chỉnh design 3.4 cho khớp.
- Bỏ lọc cách ly SLA `Default` của site trong các test không tự tạo SLA (các ca phụ thuộc nay đặt `priority` tường minh).
- `test_unchanged_field...` giả định `make_ticket(priority="Medium")` vẫn `Medium` lúc `apply_route`: đã chạy xanh.

## Bằng chứng chạy (dev)
- RED vòng 1: `FAIL: test_missing_field_permission_skipped ... {'ok': False, 'reason': 'thiếu quyền ghi trường priority'}` (10 test còn lại xanh ngay lần chạy đầu vì khung T1 đã có hành vi đó; dev chứng minh từng khẳng định bằng đột biến: bỏ kiểm `ai_classified_by` → `test_human_classified_refused` đỏ; bỏ kiểm permlevel từng trường → `test_missing_field_permission_skipped` đỏ; bỏ kiểm dấu → `test_missing_marker_permission_refused` lỗi; bỏ lọc giá trị có trên site → `test_value_missing_on_site_not_written` lỗi; bỏ `has_permission("write")` → `test_user_without_write_permission_refused` lỗi).
- RED vòng sửa: `AssertionError: 'priority' unexpectedly found in {'ticket_type': '', ..., 'priority': 'Medium', ...}` (`Ran 13 tests ... FAILED (failures=1)`); đột biến `"write"`→`"read"` ở :38/:41 → 2 test đỏ; `changed = list(values)` → test mới đỏ. RED của `test_agent_runner`: `Ran 56 tests ... FAILED (failures=3)`.
- GREEN: `erp_ai.agent.tools.test_route_ticket` Ran 13 OK; `erp_ai.agent.test_agent_runner` Ran 56 OK; `cmd.test` (`--app erp_ai`) trên đầu nhánh task 809fac6: `Ran 764 tests in 127.533s`, `OK`; lint pre-commit sạch.
- Sau merge: `git diff --stat 809fac6 HEAD -- . ':!docs'` rỗng.

## Review checklist (10)
1–10: đạt (reviewer approve vòng 2).
