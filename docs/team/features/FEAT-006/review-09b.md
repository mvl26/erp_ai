Feature: FEAT-006
Stage: build
Author-agent: tech-lead (tổng hợp từ reviewer)
Date: 2026-11-12
Approved-by:

# Review 9b — FEAT-006 T9b (bộ kiểm `routing_rules`: từ chối trống và khóa tiền tố rỗng)

- Diff: `git diff 8a1bd31..566f796` (nhánh `team/FEAT-006-task-9b-rework1`, commit 1a870d5 + 566f796; merge `4dc14d7`)
- Vòng: 2 (vòng 1 request-changes, 1 vòng sửa, vòng 2 scoped re-review approve)
- Verdict: approve

## Phát hiện vòng 1
| severity | STD | file:line | description | fix | vòng 2 |
|---|---|---|---|---|---|
| major | STD-ERR-3 | erp_ai/agent/routing.py:287-290 | Thông báo trống nhắc tên hằng Python `DEFAULT_ROUTING_RULES` mà người quản trị không thấy, và che việc bản đã lưu không đổi | bỏ tên hằng; nói bản đã lưu chưa đổi, tải lại trang; đưa chính JSON mặc định vào thông báo (quyết định tech-lead, không mở rộng touchpoint) | ADDRESSED |
| minor | STD-ERR-2 | erp_ai/agent/routing.py:286 | `(raw or "").strip()` ném AttributeError (500) với giá trị không phải chuỗi | kiểm `isinstance(raw, str)` | ADDRESSED |

## Phát hiện vòng 2
Không có blocker/major. minor: không test nào khóa câu nhắc "tải lại trang" (dev tự quyết).

## Deferred
- Từ reviewer vòng 2: `install._ensure_default_settings` chỉ ghi mặc định khi DB là NULL; một site đang lưu `""` sẽ gặp lỗi "không được để trống" khi lưu bất kỳ trường Setting nào cho tới khi dán JSON từ thông báo. Site `miyano` đã có JSON mặc định (C2), không dính.
- design.md mục 3.3: bảng lỗi chưa có 2 hàng mới (trống; khóa tiền tố rỗng). Ngoài touchpoint của T9b; ghi vào design khi gộp.
- Cần kiểm một lần trên `miyano`: JSON nhiều dòng trong hộp thoại lỗi có đọc được không (vô hại nếu dồn dòng, dán vẫn hợp lệ).
- Bộ nạp trả `{}` cho cấu hình có khóa tiền tố rỗng là chủ đích (design 3.3 "bộ nạp trả {} khi cấu hình sai"; chỉ ghi thẳng DB mới tới được).

## Bằng chứng chạy (dev)
- RED vòng 1: `test_routing` 11 failure (3 trống, 8 khóa rỗng) + `test_erp_ai_setting` 3 failure, tất cả "ValidationError not raised" (thiếu hành vi, không phải lỗi import).
- RED vòng sửa: `test_routing` `Ran 49 tests ... FAILED (failures=1, errors=3)`: `AttributeError: 'dict'/'int'/'list' object has no attribute 'strip'`, và không tìm thấy JSON mặc định trong thông báo.
- GREEN: `erp_ai.agent.test_routing` Ran 49 OK; `test_erp_ai_setting` Ran 25 OK; `cmd.test` (`--app erp_ai`) trên đầu nhánh task 566f796: `Ran 744 tests in 118.752s`, `OK`; lint pre-commit sạch.
- Sau merge: `git diff --stat 566f796 HEAD -- . ':!docs'` rỗng (cây mã trùng đầu nhánh đã chạy xanh).

## Review checklist (10)
1–10: đạt (reviewer approve vòng 2).
