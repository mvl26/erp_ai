# Review 35 — FEAT-001 T31 (Handler: điều kiện xếp job cho phiếu và comment)

Verdict: approve
Vòng: 1 (không rework)
Diff: `git diff a39ee7c..team/FEAT-001-task-31` (976a1fa; 3 file: handlers.py, hooks.py, tests/test_handlers.py)
Reviewer: team:reviewer, checklist (10) đủ 10/10; không blocker, không major.

## Tầng 1
Khớp design 3.1/3.2 và Amendments D8: `ticket_before_insert` đặt cờ `erp_ai_prefilled`; `ticket_after_insert` theo thứ tự bật -> owner -> `can_send_ticket` -> không prefilled; `comment_after_insert` thoát sớm bước 0 chỉ bằng thuộc tính, tác giả chỉ `doc.owner`. Guard tạm `frappe.db.exists("DocType", SETTING_DOCTYPE)` đã bỏ. Mỗi test chạm đúng guard của nó (reviewer kiểm từng guard); dev báo đã chạy mutation 10 guard, mỗi guard đỏ.

## Bằng chứng dev
RED: 18 test, failures=5, errors=3 (thiếu `comment_after_insert`, `ticket_before_insert`, 0 != 1) -> GREEN: `Ran 18 tests OK` x3; test_queue 5, test_policy 21, test_ticket_delete 2 OK. Đếm HD Team/HD Ticket/User/ERP AI Log/Error Log: 4/3/8/0/195 trước = sau.

## Minor (deferred)
- STD-OPS-5 handlers.py:42,64: log "enqueued" cả khi `enqueue_agent_run` trả False; nên log giá trị trả về.
- STD-DESIGN-4 handlers.py:13: `TICKET_DOCTYPE` định nghĩa ở module thứ ba (install.py, write_ticket.py đã có); gom về constants.py.
- STD-NAME-2 tests/test_handlers.py:78: dùng `SETTING_DOCTYPE` thay chuỗi "ERP AI Setting".

## Không kiểm được từ diff (tech-lead xử lý)
- Thứ tự hook D-4 (before_insert của erp_ai chạy trước `before_validate` của Helpdesk): được test_new_unclassified_ticket_enqueues_one_job kiểm thật khi chạy xanh; xanh trong lượt dev (18 OK x3).
- Giả định Helpdesk không tự `frappe.enqueue` khi insert phiếu/comment và `Comment.before_insert` của Helpdesk cho AGENT_USER/Info đi qua: các test tương ứng xanh trên site thật nên giả định đứng được; kiểm lại khi chạy cmd.test.
- `can_send_ticket(doc)` nhận Document: thuộc T20.
