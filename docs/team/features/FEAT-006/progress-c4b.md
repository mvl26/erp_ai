# Tiến độ chặng 4b (T20, T21, T22) — ghi riêng, gộp vào progress.md ở bước kế tiếp

Quy ước: dòng tick là sự thật trên đĩa; `BASE` là đầu `team/FEAT-006` ngay trước lần gọi dev đầu tiên của task. Khi resume, đọc cả file này cùng `progress.md` (tech-lead không có công cụ Edit ở chặng này nên không sửa `progress.md`; team-leader hoặc tech-lead chặng sau gộp khối dưới vào sau dòng T19).

- [x] T20 — BASE=77dce93, 2 vòng (1 vòng sửa; 1 DESIGN_CONFLICT giải bằng mở rộng touchpoint `test_agent_runner.py`), merge 31d1dba, review-20; cmd.test đầu nhánh task d9fad65: Ran 807 tests, OK
  - Quyết định: `value_before`/`value_after` lồng `{"ticket": {...}}` theo design 3.5 dòng 244 (T21 thêm "assign", T22 thêm "task").
  - Ghi chú nhánh: `team/FEAT-006-task-20` giữ cc82977 (worktree dev trước còn giữ); đầu thật là `team/FEAT-006-task-20-rework1` d9fad65.
- [x] T21 — BASE=b6d3504, 2 vòng (1 vòng sửa), merge f6a7f21, review-21; cmd.test đầu nhánh task 9dc0ca8: Ran 826 tests, OK
  - Mở rộng touchpoint: `erp_ai_setting.json` (description `auto_assign_enabled`), `test_doctype_descriptions.py`. Đầu thật là `team/FEAT-006-task-21-rework1`.
  - Concern: callback `after_commit`/realtime của `assign_to.add` không bị rollback savepoint hủy (thông báo ma rất hiếm, không rò dữ liệu).
  - Deferred cho designer: design 4.2 và tasks.md dòng 143 ghi savepoint `erp_ai_route` từng đơn vị; mã dùng `erp_ai_route_unit` lồng.
- [x] T22 — BASE=1b79b96, 2 vòng (1 vòng sửa), merge 5c6efd5, review-22; cmd.test đầu nhánh task 3db98bf: Ran 834 tests, OK
  - Đầu thật là `team/FEAT-006-task-22-rework1`. Bị từ chối không ném: không Task, không comment, chỉ log (deferred cho designer).

## Checkpoint C4 (trên đầu nhánh sau merge 5c6efd5; cây mã trùng 3db98bf)

- `cmd.test` (`bench --site miyano run-tests --app erp_ai`, dev chạy một mình trên đầu nhánh T22 rework 3db98bf): `Ran 834 tests in 157.432s`, `OK`. Tech-lead: `git diff --stat 3db98bf 5c6efd5 -- . ':!docs'` rỗng, tức cây mã sau merge trùng cây đã chạy xanh (role-policy chặn tech-lead chạy bench với PYTHONPATH).
- Đầu-cuối qua runner với FakeGateway (`TestRoutingTask::test_c_ticket_one_linked_task_assigned`): phiếu C → `actions` = `apply_route`, `assign_owner`, `create_routed_task`; 1 Task có ToDo của người cấu hình; phiếu gán đúng 1 người; `value_after` có `ticket`, `assign`, `task`; 0 comment; dòng info `assigned=1 task=1 comment=0 sla=ok`. SLA chỉ vào `actions` khi thiếu hoặc lệch (design 4.2 bước 2), do đó ca này `sla=ok` không có action `sla_check`; ca có `sla_check`: `TestRoutingSla::test_slow_sla_warning_in_log`, `test_no_sla_one_warning_one_comment`. Ưu tiên/nhóm từ điểm: `TestRoutingEndToEnd::test_priority_from_scores_through_runner`.
- Chưa chạy `migrate` ở C4: chặng 4b không đổi schema (chỉ `description` của `auto_assign_enabled`, JSON mô tả).
- Việc còn lại: T23..T26.

## Nhật ký chặng 4b

- 2026-11-12 T20: dev lần 1 DESIGN_CONFLICT (5 test cũ `TestRunnerL1Classification` đổi kỳ vọng theo design) → tech-lead mở rộng touchpoint; dev lần 2 DONE_WITH_CONCERNS; reviewer vòng 1 request-changes (3 major STD-TEST-6/2/8); dev sửa; vòng 2 approve; merge 31d1dba; 807 OK.
- 2026-11-12 T21: dev DONE (đột biến 13 test đỏ); reviewer vòng 1 request-changes (3 major: STD-TEST-8, STD-TEST-2 x2, đều ở test); dev sửa (chỉ test); vòng 2 approve; merge f6a7f21; 826 OK; khắc phục deferred review-19 (description `auto_assign_enabled`).
- 2026-11-13 T22: dev DONE; reviewer vòng 1 request-changes (2 major: STD-TEST-8 ca bị từ chối không ném, STD-TEST-6 đếm ToDo toàn site); dev sửa (chỉ test); vòng 2 approve; merge 5c6efd5; 834 OK.
- 2026-11-13 C4: dừng báo cáo sau T22; vai đã dùng: dev, reviewer (không tính lần gọi lại).
