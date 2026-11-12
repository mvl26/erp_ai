# Review package FEAT-006 T26 (luật kiến trúc ADR-019..021 và bảo vệ tĩnh), vòng 1

Repo: `/home/miyano/frappe-bench/apps/erp_ai` (worktree `.claude/worktrees/feat-006`). BASE=2cd3ba3; head=team/FEAT-006-task-26 (4ad5b17).
Lệnh diff (chỉ-đọc): `git -C /home/miyano/frappe-bench/apps/erp_ai/.claude/worktrees/feat-006 diff 2cd3ba3..team/FEAT-006-task-26 -- erp_ai`
Commits: `git -C ... log --oneline 2cd3ba3..team/FEAT-006-task-26`; stat: `git -C ... diff --stat 2cd3ba3..team/FEAT-006-task-26`.

Commits:
- 4ad5b17 test(arch): T26 routing rules of ADR-019..021 and static guards (FEAT-006)

Stat (mã): erp_ai/tests/test_architecture.py +497/-2 (cộng 1 file docs/team dev-T26.md, ngoài phạm vi review mã).

Touchpoint cho phép: erp_ai/tests/test_architecture.py. Mã sản xuất không được đổi.

Tiêu chí (tasks.md T26, spec AC-10, AC-14, AC-7c, ADR-019..021 Ràng buộc): `POLICY_FIELDS` thêm `auto_assign_enabled`; trong `TestArchitecture`: test_route_module_not_in_tool_modules_and_has_no_tools, test_route_module_single_ticket_save, test_assign_to_only_in_route_module, test_no_share_bypass (`ignore_share_permission`, `assign_to._add(`, `add_docshare`, `frappe.share.add`), test_auto_assign_switch_only_in_policy, test_entry_types_unchanged, test_assign_field_not_used_for_decision (`"_assign"` trong `erp_ai/agent/**`), test_route_module_bypass_rules_apply, test_feature_never_assigns_sla_dates, test_no_default_people_in_agent_python (Việt, Tiến, Hiếu, Lan, Hà, Thư, Chi, `ai.agent` dạng tên người; "Việt Nam", "Tiếng Việt" trong prompts.py là trùng chữ); mỗi luật có ca trong `TestScannersCatchViolations` chứng minh bộ quét bắt được vi phạm. Là test bảo vệ nên cần kiểm: bộ quét có thật sự bắt (không rỗng, không bị allowlist nuốt), không báo nhầm trên mã hiện có, allowlist không rộng quá mức.
Bằng chứng đột biến của dev: `docs/team/features/FEAT-006/dev-T26.md` (nhánh task).
