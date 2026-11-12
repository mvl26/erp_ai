Feature: FEAT-006
Stage: build
Author-agent: tech-lead (tổng hợp từ reviewer)
Date: 2026-11-12
Approved-by:

# Review 16 — FEAT-006 T16 (`create_routed_task` và `create_task` đặt `ai_ticket`)

- Diff: `git diff 24f04a4..a24b9a2` (nhánh `team/FEAT-006-task-16`, commit a24b9a2; merge `7fdf122`)
- Vòng: 1
- Verdict: approve

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| — | — | — | không có | — |

minor | — | — | (a) `_assert_refused` chỉ kiểm có lý do, không kiểm đúng câu lý do của từng ca nên đổi chỗ hai câu trong `_task_refusal` vẫn xanh; (b) `test_sharing_disabled_raises` bắt mọi `frappe.ValidationError`, không kiểm thông báo "tắt chia sẻ tài liệu" (rủi ro thấp: chỉ `assign_to.py:124` phản ứng với công tắc); (c) `TestCreateTask.setUp` chép bộ khung commit-guard/rollback có ở lớp test khác.

## Điểm reviewer đã kiểm
- Hợp đồng trả về khớp design 3.4; ba điều kiện từ chối đi qua `_task_refusal` dùng chung; lỗi chia sẻ KHÔNG bị bắt (`assign_to.add` ở `route_ticket.py:106` sau `task.insert()`; `frappe.throw` ở `assign_to.py:124-131` là `ValidationError`).
- `subject` cắt 140; `description` = link phiếu + dòng điểm qua `escape_html`; không khóa/cấu hình thô (NFR-4).
- Không có `ignore_permissions`, `ignore_share_permission`, `_add(`, `add_docshare`; `assign_to.add` chỉ gọi ở `route_ticket.py`.
- Refactor giữ hành vi: `apply_route` dùng `_existing_values` cùng thứ tự và câu lý do; `create_task` giữ thứ tự kiểm.
- Test chia sẻ chạy qua `assign_to` thật dưới `pin_agent_roles`: hàng DocShare read=1, `has_permission` đúng với người được giao.

## Deferred
- Minor (a)(b)(c) ở trên.
- AC-13 (i) (runner rollback Task + ToDo và đăng một comment `ASSIGN_REQUEST`) thuộc T22; T16 chỉ bảo đảm ném lỗi lên.
- Chưa có kiểm tĩnh "`assign_to.add` chỉ ở `route_ticket.py`" và cấm bỏ qua chia sẻ (`test_assign_to_only_in_route_module`, `test_no_share_bypass`): thuộc T26.
- Test chia sẻ phụ thuộc dòng Custom DocPerm Task/ERP AI Agent của T12 (if_owner=1, share=1) và việc role `Agent` của Helpdesk không có quyền đọc Task trên site; sai điều kiện thì test đỏ, không xanh giả.

## Bằng chứng chạy (dev)
- RED (khung trả `{"ok": False, "reason": "chưa cài"}`): `test_route_ticket` `Ran 28 tests ... FAILED (failures=6, errors=1)`: `test_assignee_without_projects_user_gets_share` → `False is not true : {'ok': False, 'reason': 'chưa cài'}`; `test_sharing_disabled_raises` → `ValidationError not raised`; `test_write_ticket`: `test_sets_ai_ticket` → `AssertionError: None != '43072'`.
- Đột biến (đỏ rồi hoàn tác xanh): bỏ `escape_html` → `test_description_escaped_and_has_scores`; bỏ `ai_ticket` → `test_task_references_ticket` và `test_sets_ai_ticket`; bỏ `assign_to.add` → `test_assignee_without_projects_user_gets_share`, `test_assign_to_add_called_on_task_with_one_todo`, `test_sharing_disabled_raises`; bắt ngoại lệ chia sẻ → `test_sharing_disabled_raises`; bỏ cắt 140 → `test_subject_cut_to_140_chars`; bỏ kiểm DocType → `test_no_task_doctype_refused`; bỏ kiểm đọc phiếu → `test_no_ticket_read_permission_refused`; bỏ kiểm tạo Task → `test_no_task_create_permission_refused`.
- GREEN: `erp_ai.agent.tools.test_route_ticket` Ran 28 OK (18 cũ + 10 mới); `erp_ai.agent.tools.test_write_ticket` Ran 34 OK; `cmd.test` (`--app erp_ai`) trên đầu nhánh task a24b9a2: `Ran 780 tests in 129.264s`, `OK`; lint pre-commit sạch.
- Sau merge: `git diff --stat a24b9a2 HEAD -- . ':!docs'` rỗng.

## Review checklist (10)
1–10: đạt (reviewer approve vòng 1).
