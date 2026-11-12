# Review package FEAT-006 T20 (runner `_route` (u1) đầy đủ và kiểm SLA), vòng 1

Repo: `/home/miyano/frappe-bench/apps/erp_ai`. BASE=77dce93; head=team/FEAT-006-task-20-r2 (581a6b3; đầu nhánh trực tiếp trên cc82977, nhánh `team/FEAT-006-task-20` giữ cc82977 vì worktree dev trước còn giữ).
Lệnh diff (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai diff 77dce93..team/FEAT-006-task-20-r2 -- erp_ai`
Commits: `git -C /home/miyano/frappe-bench/apps/erp_ai log --oneline 77dce93..team/FEAT-006-task-20-r2` (cc82977 dev lần 1: runner + test_runner_routing, để lại 5 test cũ đỏ; 581a6b3 dev lần 2: sửa kỳ vọng 5 test cũ và dạng lồng của value_before/after).
Stat: `git -C /home/miyano/frappe-bench/apps/erp_ai diff --stat 77dce93..team/FEAT-006-task-20-r2`

Touchpoint T20: erp_ai/agent/runner.py, erp_ai/agent/test_runner_routing.py. Mở rộng được tech-lead chấp nhận (kỳ vọng cũ đổi theo design, STD-TEST-5, kiểu T14/T19): erp_ai/agent/test_agent_runner.py (5 test `TestRunnerL1Classification`: thêm `sla_check` vào actions, note `assignee` trong skipped_fields, từ chối ghi `ok=false` + lý do; và `value_before/after` lồng `{"ticket": ...}` theo design 3.5 dòng 244).

Tiêu chí: dòng T20 của `docs/team/features/FEAT-006/tasks.md` (dòng 140-144): AC-3, AC-4, AC-11, AC-12, AC-16, AC-18, D-6, D-7, D-9, D-16, NFR-2; (u1) ném lỗi hoặc `ok=false` thì dừng (u2)-(u4) và kiểm SLA, actions ghi `ok=false` + lớp ngoại lệ (không nội dung phiếu); kiểm SLA chạy ở L1+ dù công tắc bật hay tắt; một lần cập nhật bản ghi `classify` (`applied`, `actions`, `value_before/after`, `skipped_fields`, `error`); dòng `erp_ai route ...` info; commit một lần khi không chạy test; câu `NO_SLA` gom vào `lines`, comment gửi ở T21 (T20 KHÔNG gửi comment).
Dặn từ review trước: `applied` theo `result["ok"]`; `applied_sla` có thể trả `resolution_s=None` khi có `sla` mà không `priority`; `skipped_fields` = `skipped` của (u1) + `decision.notes`, không có hai lý do mâu thuẫn (review-17).
Expect: `TestRoutingEndToEnd::test_priority_from_scores_through_runner`, `test_changed_importance_table_used_next_run`, `test_no_helpdesk_config_records_created`; `TestRoutingSla::test_slow_sla_warning_in_log`, `test_broken_sla_condition_stops_route_cleanly`.
Design: design.md cùng thư mục (mục 3.5, 4.2, 4.3).

Điểm cần soi: (1) mỗi khẳng định đỏ khi bỏ đúng hành vi nó khóa; (2) ngoại lệ ở (u1) được bắt, rollback savepoint, job vẫn chạy bước suy luận (D-16), không rò nội dung phiếu vào `actions`/log; (3) `applied` = `result["ok"]`; (4) `resolution_s=None` không làm vỡ kiểm SLA; (5) kiểm SLA không ghi, chạy cả khi công tắc tắt; (6) việc sửa kỳ vọng 5 test cũ có thực sự khớp design hay là nới; (7) dạng lồng `{"ticket": ...}` có phù hợp mọi nơi đọc `value_before/after` trong `erp_ai/` (grep).
