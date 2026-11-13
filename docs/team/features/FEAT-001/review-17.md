# Review 17 — FEAT-001 T21 (thẩm quyền theo người)

Diff: `git diff 8a5be57..team/FEAT-001-task-21` (head 3ed63de, chưa merge)

## Round 1 — design-defect (chưa approve, dừng theo build SKILL bước 9)

Phán quyết reviewer: design-defect. Design (§2 dòng 37, §3.3 dòng 224-225, D-24) giả định comment của phiếu nằm ở `HD Ticket Comment` và lấy tác giả từ `commented_by or owner`. Helpdesk 15.1.0 cài trên site ghi comment vào `Comment` lõi (`HD Ticket.new_comment` gọi `add_comment("Comment", ...)`; patch `migrate_hd_ticket_comment_to_comment`; `api/timeline.py` chỉ đọc `Comment`), và `commented_by` do client đặt được.

blocker | STD-TEST-2 | erp_ai/agent/authority.py:46 (và test_authority.py:31-45) | `latest_instructor` đọc `HD Ticket Comment`; trên site thật không có comment mới ở đó nên AC-7 "người ra lệnh gần nhất từ comment" vô hiệu; test chèn thẳng `HD Ticket Comment` nên không bắt được. | designer: chốt nguồn (`Comment`, reference_doctype=HD Ticket, comment_type=Comment, tác giả=`owner`); dev: truy vấn nguồn đó, dựng dữ liệu test qua `ticket.new_comment`/`add_comment`.
major | STD-SEC-4 | authority.py:52,62 | Tác giả lấy `commented_by or owner`; `commented_by` là Link tự do mà Agent ghi được → agent thường mạo danh người có thẩm quyền, nâng quyền/prompt injection. | Chỉ lấy từ `owner` (server đặt); `Comment.comment_email` cũng client đặt được, không dùng.
major | STD-TEST-8 | test_authority.py:54-57 | `_assigned_by_other` có hai guard chồng (`_assign` và filter `reference_name`); xóa một trong hai vẫn xanh. Thiếu: ToDo Closed, ToDo Cancelled, ToDo mới nhất sau gán lại. | Thêm (a) gán bởi ASSIGNER rồi ToDo Closed → dữ liệu; (b) ASSIGNEE tự gán trên Q khi P được gán bởi người khác → Q là dữ liệu; (c) ToDo cũ gán bởi người khác, ToDo mới tự gán → dữ liệu.
major | STD-TEST-2 | test_authority.py:50-51 | Ca D-16 `Guest`, `AGENT_USER` vẫn False dù bỏ khỏi `NEVER_AUTHORITY` (không có role/gán). | Cho AGENT_USER (và Guest) có `ROLE_INSTRUCTOR` và/hoặc được gán bởi ASSIGNER trên P rồi assertFalse.
minor: `except ValueError` không có lý do (STD-ERR-1); N+1 truy vấn trong label_comments/latest_instructor (≤ 30 comment); khóa `role` ghi đè `role` của người gọi chưa có test.

Cannot verify: site miyano còn nhận `HD Ticket Comment` mới không (đếm `HD Ticket Comment` so với `Comment` reference_doctype=HD Ticket); ảnh hưởng lên T1 `handlers.comment_after_insert` (doc_events trên HD Ticket Comment, trigger `comment_mention` có thể không bao giờ chạy) và T23/T24/T27 `list_comments`/`get_record`; user bị vô hiệu vẫn giữ role Instructor (spec im lặng).

Quyết định tech-lead: dừng T21, báo team-leader (design-defect). T21 chưa merge, nhánh `team/FEAT-001-task-21` giữ nguyên.
