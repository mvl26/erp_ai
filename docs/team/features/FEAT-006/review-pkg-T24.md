# Review package FEAT-006 T24 (test chốt: chống chèn lệnh, quyền ghim, thông tin nhạy cảm, schema tool), vòng 1

Repo: `/home/miyano/frappe-bench/apps/erp_ai` (worktree `.claude/worktrees/feat-006`). BASE=9135b85; head=team/FEAT-006-task-24 (8439972).
Lệnh diff (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/feat-006 diff 9135b85..team/FEAT-006-task-24 -- erp_ai`
Commits: `git -C ... log --oneline 9135b85..team/FEAT-006-task-24`; stat: `git -C ... diff --stat 9135b85..team/FEAT-006-task-24`.

Commits:
- 7e234d1 test(routing): chống chèn lệnh, quyền ghim, khóa giả, schema tool (FEAT-006)
- 8439972 docs(team): dev-T24 báo cáo đột biến (FEAT-006)

Stat (mã): test_runner_routing.py +353, tools/test_registry.py +70. Mã sản xuất KHÔNG đổi (kiểm: `git diff --stat 9135b85..team/FEAT-006-task-24 -- erp_ai ':!*test_*'` phải rỗng).

Touchpoints cho phép: erp_ai/agent/test_runner_routing.py, erp_ai/agent/tools/test_registry.py.

Tiêu chí (tasks.md T24): AC-9 (nội dung phiếu không điều khiển route), AC-16 (mọi ghi có trước/sau; từ chối có lý do), AC-17 (role đã ghim; `check_privilege_escalation` trước = sau), NFR-4 (khóa giả không rò vào comment/nhật ký/Task). Đây là test bảo vệ: có thể xanh ngay; bằng chứng "đỏ đúng lý do" là bảng đột biến ở `docs/team/features/FEAT-006/dev-T24.md` (trong nhánh task). Test cần: `TestRoutingInjection::test_ticket_text_does_not_steer_route`, `TestRoutingLog::test_every_write_in_actions_with_before_after`, `test_refusals_have_ok_false_reason`, `TestRoutingPermissions::test_success_cases_under_pinned_roles`, `test_privilege_findings_unchanged`, `TestRoutingEndToEnd::test_fake_key_absent_from_comment_log_task`; `TestRegistry::test_no_tool_schema_takes_person_sla_priority_or_score`, `test_route_functions_not_executable_as_tools`.
Dev báo concern: `_configure_c` mức module nhân đôi `TestRoutingTask._configure_c` (STD-DESIGN-4 cần xét).
