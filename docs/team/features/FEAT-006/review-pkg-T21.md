# Review package FEAT-006 T21 (runner (u2) gán người và (u4) comment), vòng 1

Repo: `/home/miyano/frappe-bench/apps/erp_ai`. BASE=b6d3504; head=team/FEAT-006-task-21 (8de1908).
Lệnh diff (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai diff b6d3504..team/FEAT-006-task-21 -- erp_ai`
Commits: `git -C /home/miyano/frappe-bench/apps/erp_ai log --oneline b6d3504..team/FEAT-006-task-21`; stat: `git -C /home/miyano/frappe-bench/apps/erp_ai diff --stat b6d3504..team/FEAT-006-task-21`.

Touchpoint T21: erp_ai/agent/runner.py, erp_ai/agent/test_runner_routing.py. Mở rộng được tech-lead chấp nhận: erp_ai/erp_ai_agent/doctype/erp_ai_setting/erp_ai_setting.json (chỉ `description` của `auto_assign_enabled`, deferred của review-19), erp_ai/tests/test_doctype_descriptions.py (cụm khóa của trường đó), erp_ai/agent/test_agent_runner.py (không cần sửa).

Tiêu chí: dòng T21 của `docs/team/features/FEAT-006/tasks.md` (dòng 146-149): AC-6, AC-7 (a)(b)(c)(d), AC-8 (đúng 1 comment), AC-11 (đúng 1 comment `NO_SLA`), AC-14, AC-16. (u2) chỉ khi `auto_assign` và L1+, `existing = site_facts.ticket_assignments` xét SAU (u1): có người → action `assign_owner` `ok=false` kèm `rule`; `decision.assignee is None` → `ok=false` theo note + `ASSIGN_REQUEST` "cấu hình không có người hợp lệ"; còn lại `assign_owner`, ngoại lệ/`ok=false` → "gán người không thành công". (u4) gom `lines` → `post_routing_comment`, tối đa 1 comment; chỉ khi `lines` khác rỗng; ngoại lệ → `ok=false`, không thử lại. Người được gán ghi bằng user ID trong `actions` và `predicted_assignee`. Dòng info có `assigned=`, `comment=`. `value_before/after` lồng `{"ticket": ...}`, thêm "assign".
Expect: `TestRoutingAssign` (4 ca), `TestRoutingNoOverride` (5 ca), `TestRoutingSla::test_no_sla_one_warning_one_comment`.
Design: design.md cùng thư mục (3.5, 4.2, 4.3, 5).

Điểm cần soi: (1) mỗi khẳng định đỏ khi bỏ đúng hành vi (dev báo đột biến bỏ `if result:`/`if auto_assign:`/`if existing:` làm 13 test đỏ); (2) savepoint lồng `erp_ai_route_unit` bên trong `erp_ai_route` có đúng (rollback một đơn vị không mất đơn vị khác, ngoại lệ không rò nội dung phiếu); (3) comment tối đa 1, không đăng khi `lines` rỗng; (4) `description` của `auto_assign_enabled` khớp hành vi thật (xét sau (u1); Task chỉ khi bot tự gán, chưa có Task, chia sẻ bật) và không quá 400 ký tự; (5) test độc lập cấu hình site (STD-TEST-6); (6) kỳ vọng cũ bị đổi (hai test dòng info; test NO_SLA bỏ khẳng định "0 comment") có nới lỏng không.
Ruling cũ giữ nguyên: khi (u1) lỗi hoặc `ok=false`, `decision.notes` không vào `skipped_fields`; (u2)-(u4) và kiểm SLA không chạy nên không có comment NO_SLA trong trường hợp đó (design 4.2 bước 1).
