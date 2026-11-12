# Tiến độ chặng 4b (T20, T21, T22) — ghi riêng, gộp vào progress.md ở checkpoint C4

Quy ước: dòng tick là sự thật trên đĩa; `BASE` là đầu `team/FEAT-006` ngay trước lần gọi dev đầu tiên của task.

- [x] T20 — BASE=77dce93, 2 vòng (1 vòng sửa; 1 DESIGN_CONFLICT giải bằng mở rộng touchpoint `test_agent_runner.py`), merge 31d1dba, review-20; cmd.test đầu nhánh task d9fad65: Ran 807 tests, OK
  - Quyết định: `value_before`/`value_after` lồng `{"ticket": {...}}` theo design 3.5 dòng 244 (T21 thêm "assign", T22 thêm "task").
  - Ghi chú nhánh: `team/FEAT-006-task-20` giữ cc82977 (worktree dev trước còn giữ); đầu thật là `team/FEAT-006-task-20-rework1` d9fad65.
- [x] T21 — BASE=b6d3504, 2 vòng (1 vòng sửa), merge f6a7f21, review-21; cmd.test đầu nhánh task 9dc0ca8: Ran 826 tests, OK
  - Mở rộng touchpoint: `erp_ai_setting.json` (description `auto_assign_enabled`), `test_doctype_descriptions.py`. Đầu thật là `team/FEAT-006-task-21-rework1`.
  - Concern: callback `after_commit`/realtime của `assign_to.add` không bị rollback savepoint hủy (thông báo ma rất hiếm, không rò dữ liệu).
  - Deferred cho designer: design 4.2 và tasks.md dòng 143 ghi savepoint `erp_ai_route` từng đơn vị; mã dùng `erp_ai_route_unit` lồng.

## Nhật ký chặng 4b
- 2026-11-12 T20: dev lần 1 DESIGN_CONFLICT (5 test cũ `TestRunnerL1Classification` đổi kỳ vọng theo design) → tech-lead mở rộng touchpoint; dev lần 2 DONE_WITH_CONCERNS; reviewer vòng 1 request-changes (3 major STD-TEST-6/2/8); dev sửa; vòng 2 approve; merge 31d1dba; 807 OK.
- 2026-11-12 T21: dev DONE (đột biến 13 test đỏ); reviewer vòng 1 request-changes (3 major: STD-TEST-8, STD-TEST-2 x2, đều ở test); dev sửa (chỉ test); vòng 2 approve; merge f6a7f21; 826 OK; khắc phục deferred review-19 (description `auto_assign_enabled`).
