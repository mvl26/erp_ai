Feature: FEAT-006
Stage: build
Author-agent: tech-lead (tổng hợp từ reviewer)
Date: 2026-11-12
Approved-by:

# Review 17 — FEAT-006 T17 (`set_classification` dùng chung `decide_route`; `ToolContext.routing_config`)

- Diff: `git diff ebe8431..68da7fc` (nhánh `team/FEAT-006-task-17` 887fa2c + `team/FEAT-006-task-17-rework1` 68da7fc; merge `6ab22a8`)
- Vòng: 2 (1 vòng sửa)
- Verdict: approve

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix | vòng 2 |
|---|---|---|---|---|---|
| major | STD-DESIGN-2 | write_ticket.py:55-60 | D/E không bộ phận: lý do "không có bộ phận" từ `decision.notes` bị bỏ, `skipped` ghi sai "ánh xạ không có giá trị" | lấy lý do `agent_group` từ `decision.notes`; thêm assert lý do | ADDRESSED |

minor | — | — | (a) fallback `ctx.routing_config or {}` không có ca phân biệt (`decide_route` đã chặn `config or {}`); (b) STD-GIT-2: commit c1f7844 làm `reasons` bắt buộc nên `route_ticket.py:41` lỗi tại commit đó, 566e26f sửa; nhánh task giữ cả hai (merge `--no-ff`), đầu nhánh xanh.

## Điểm reviewer đã kiểm
- `decide_route` nhận điểm từ phiếu, `department=None`; chỉ dùng `ticket_type`/`agent_group`/`priority`; `ToolContext.routing_config` là trường cuối, mặc định `None`; schema tool không đổi; `resolve_ticket_values` không còn được import ở `write_ticket.py` (xóa hàm ở T18).
- Test đỏ khi bỏ `routing_config`/`importance` và khi bỏ nhánh D/E; mapping rỗng thật vẫn ra lý do cũ (ca riêng).

## Mục "không kiểm được từ diff" và phán quyết của tech-lead
- Runner có thêm `decision.notes` vào `skipped` sau `apply_route` không: design.md mục 4.2 (dòng 246) quy định `skipped_fields` = `skipped` của (u1) cộng `notes`; làm ở T20.
- Mâu thuẫn design.md dòng 108 ("không đọc bảng hệ thống trong `tools/`") và dòng 234 (`tools/` truyền `site_facts.is_active_agent`): nhiệm vụ quy định rõ `is_active_agent=site_facts.is_active_agent`; ghi cho designer chỉnh dòng 108 khi gộp.

## Deferred
- `route_ticket.apply_route` (route_ticket.py:41) gọi `_existing_values` không truyền `decision.notes`: D/E không bộ phận ghi "ánh xạ không có giá trị" trong `skipped` của `apply_route`; T20 thêm `notes` vào `skipped_fields`, nên cần kiểm ở T20 để tránh hai lý do mâu thuẫn trong cùng bản ghi (nếu có thì báo reviewer T20).
- Minor (a), (b) ở trên.

## Bằng chứng chạy (dev)
- RED vòng 1: `test_same_priority_as_route` `'Medium' != 'Urgent'`; `test_de_skips_team_without_department` `'T25 Nhóm' != None`. GREEN `erp_ai.agent.tools.test_write_ticket` Ran 36 OK; `cmd.test` đầu nhánh 887fa2c: Ran 782 tests, OK.
- RED vòng 2: `AssertionError: 'ánh xạ không có giá trị' != 'không có bộ phận'` (Ran 37, failures=1); GREEN Ran 37 OK; `cmd.test` đầu nhánh 68da7fc: `Ran 783 tests`, `OK`; lint sạch.
- Sau merge: `git diff --stat 68da7fc HEAD -- . ':!docs'` rỗng; `git diff --name-only ebe8431..68da7fc -- erp_ai` chỉ gồm 3 file touchpoint.

## Review checklist (10)
1–10: đạt (reviewer approve vòng 2).
