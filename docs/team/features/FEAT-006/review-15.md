Feature: FEAT-006
Stage: build
Author-agent: tech-lead (tổng hợp từ reviewer)
Date: 2026-11-12
Approved-by:

# Review 15 — FEAT-006 T15 (`assign_owner` và `post_routing_comment`)

- Diff: `git diff 6b4b9f7..e3e2500` (nhánh `team/FEAT-006-task-15`, commit e3e2500; merge xem dòng tick ở progress.md)
- Vòng: 1
- Verdict: approve

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| — | — | — | không có | — |

minor | STD-TEST-8 | test_route_ticket.py (`test_no_read_permission_refused`, `deny_read`) | `deny_read` bỏ qua đối số user nên mã kiểm sai người (kiểm quyền của người được gán thay vì người gọi) vẫn qua; design mục 5 nói người gọi | chỉ từ chối khi user là None hoặc user phiên là `AGENT_USER`. Ca ToDo = 0 trong cùng test không thể đỏ vì `add` bị mock.

## Tra lời các điểm của gói
Câu cố định khớp design 3.6 từng byte (`git grep -F`). `assign_to.add` của Frappe chỉ chia sẻ khi người được gán thiếu quyền đọc (`assign_to.py:123-133`); Helpdesk `hd_ticket.py:1381-1384` cấp đọc cho người trong `_assign`, nên người được gán là HD Agent không bị chia sẻ phiếu kể cả khi `restrict_tickets_by_agent_group` bật; test khóa bằng đếm DocShare = 0 và `assert_called_once_with` đúng đối số.

## Deferred
- Minor: `deny_read` ở `test_no_read_permission_refused` (xem trên); ca ToDo = 0 không thể đỏ.
- T21 chỉ gọi `post_routing_comment` khi `lines` khác rỗng (`post_routing_comment([], ctx)` sẽ đăng comment rỗng).
- Comment Helpdesk hiển thị HTML nên các dòng nối bằng `"\n"` hiện thành một dòng; theo design 3.6 như viết; nếu muốn tách dòng là quyết định thiết kế (`<br>`).
- Chưa có kiểm tĩnh giữ `assign_to.add` chỉ ở `route_ticket.py` (`test_assign_to_only_in_route_module`, `test_no_share_bypass` do kế hoạch test xếp ở task sau, T26).

## Bằng chứng chạy (dev)
- RED: dựng khung trả sai trước: `test_ticket_never_shared_one_todo_one_notification` → `{'ok': False, 'reason': 'stub'} != {'ok': True, 'assignee': ...}`; `test_lines_joined_in_one_comment` → `KeyError: 'ok'`; `test_no_read_permission_refused` xanh trên khung (khung đã từ chối), chỉ kiểm bằng đột biến.
- Đột biến (đỏ rồi hoàn tác xanh): thêm cờ vào đối số `assign_to.add` → `test_ticket_never_shared_one_todo_one_notification` đỏ; bỏ kiểm `read` → `test_no_read_permission_refused` đỏ; một comment mỗi dòng và bỏ một dòng khỏi `lines` → `test_lines_joined_in_one_comment` đỏ.
- GREEN: `erp_ai.agent.tools.test_route_ticket` Ran 18 OK (gồm 13 test của T14); `cmd.test` (`--app erp_ai`) trên đầu nhánh task e3e2500: `Ran 769 tests in 128.570s`, `OK`; lint pre-commit sạch.
- Sau merge: `git diff --stat e3e2500 HEAD -- . ':!docs'` rỗng.

## Review checklist (10)
1–10: đạt (reviewer approve vòng 1).
