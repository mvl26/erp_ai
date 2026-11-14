Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 63 — FEAT-004 T63

- Diff: `git diff 7c2a3af..team/FEAT-004-task-63` (head `0009fde`, 1 commit; 4 file, +228/-46). Lệnh đã chạy: `git log --oneline 7c2a3af..team/FEAT-004-task-63`, `git diff --stat 7c2a3af..team/FEAT-004-task-63`, `git diff 7c2a3af..team/FEAT-004-task-63`, `git show 7c2a3af:erp_ai/agent/tools/{registry,read,source,write_ticket,propose_change,site_api}.py`, `git grep` tên cũ/hàm cấp trên `team/FEAT-004-task-63`, `git show team/FEAT-004-task-63:erp_ai/agent/{prompts.py,test_agent_runner.py,tools/test_site_api.py}`, `git show team/FEAT-004:docs/team/...` (tasks.md, ADR-023, ADR-011, plan.md, spec.md, review-chg001.md)
- Vòng: 1 (max_rework=3)
- Verdict: request-changes

## Vòng 1 — request-changes
Lớp 1: khớp T63 Returns, ADR-023 QĐ 4 + Ràng buộc, ADR-011 QĐ 2, 3, 6. `registry.py` còn đúng một hàm cấp `_granted_specs(level, has_instructor, change_enabled, unrestricted)` và một `GRANT_TABLE` 6 dòng; `site_admin` = (code ∧ L3 ∧ người ra lệnh) ∨ `_unrestricted_grant`, `site_unrestricted` = `_unrestricted_grant` (toàn quyền ∧ mức ≠ L0 ∧ người ra lệnh); `_unrestricted_specs`, `get_unrestricted_tool_schemas`, `UNRESTRICTED_GROUPS` đã bỏ; `execute_tool` gọi một lần `_granted_specs` (`registry.py:187-189`); runner gọi `get_tool_schemas(*grant)` đúng một chỗ, ba cờ khối prompt lấy từ `grants_*` (`runner.py:585-594`). Không phần thừa, chỉ chạm 4 file touchpoints.

Đối chiếu bộ tool cấp với mã nền (`7c2a3af`): mã cũ = `get_tool_schemas(level, inst, code)` rồi nối các tool `site_admin`/`site_unrestricted` chưa có (thứ tự `_all_specs`). Thứ tự module `read → source → write_ticket → propose_change → site_api` và trong `site_api.TOOLS` 4 tool `site_admin` đứng trước 3 tool `site_unrestricted`, nên phép nối cũ và phép lọc một lần mới cho cùng danh sách, cùng thứ tự. Tự tính đủ 32 tổ hợp từ mã nền: khớp từng dòng `GRANT_SNAPSHOT` (`test_registry.py:642-679`) — L0 và không người ra lệnh chỉ còn 10 tool gốc (hoặc rỗng ở L0); toàn quyền ở L1–L3 có người ra lệnh = gốc + `create_task` + 4 bản ghi + 3 toàn quyền; code ∧ L3 ∧ người ra lệnh = gốc + `create_task` + 3 đề xuất + 4 bản ghi (+3 toàn quyền nếu bật cả hai). Prompt: cờ `site_admin_tools` nay là True ở các tổ hợp chỉ có toàn quyền (trước False), nhưng `build_reason_system` (`prompts.py:327-329`) bỏ `SITE_ADMIN_TOOLS_BLOCK` khi `unrestricted_tools` và `ACT_NOW_BLOCK` đã bật theo `unrestricted_tools`, nên chuỗi prompt giống từng byte ở mọi tổ hợp (AC-1, ADR-011 QĐ 3).

Test trước mã: `test_grant_matrix_matches_snapshot` viết cứng 32 dòng và đỏ khi bỏ bất kỳ vế nào của `_unrestricted_grant` (bỏ `has_instructor` → `(False, True, "L1", False)` sai; bỏ `or _unrestricted_grant` ở `site_admin` → mất 4 bản ghi ở các dòng toàn quyền) và kiểm cả `_granted_specs` lẫn 3 hàm `grants_*`; `test_unknown_level_grants_like_l0` phủ mức lạ; `test_execute_asks_the_one_grant_function` ghim 4 đối số; `test_runner_asks_registry_once` đỏ với mã cũ (RED của dev: `get_tool_schemas('L3', True, True)`); `test_over_budget_l3_keeps_unrestricted_tools` phủ AC-2 (c) ở runner. Thay đổi `test_registry.py:307-314` (chữ ký 4 tham số) theo spec mới, không để khớp hành vi sai.

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-GIT-2 | erp_ai/agent/tools/test_site_api.py:308-311 | `TestUnrestrictedGrant.names` vẫn gọi `registry.get_unrestricted_tool_schemas` đã bị xóa ở commit này → `test_switch_grants_every_record_tool_at_any_level_above_l0_with_instructor` lỗi `AttributeError` ngay khi gộp T63; `cmd.test` của `team/FEAT-004` đỏ. File ngoài touchpoints của T63 (đúng là dev không sửa, STD-DESIGN-1) — tech-lead đã xếp vòng 2 sau T59. Đã xác nhận bằng `git grep` trên `0009fde` | vòng 2: đổi `names` sang `get_tool_schemas(level, has_instructor, False, unrestricted)` và giữ kỳ vọng hiện có; không gộp T63 vào `team/FEAT-004` trước vòng 2 (hoặc gộp cùng lúc) |

minor | — | — | 3 điểm nhỏ: (1) STD-DESIGN-5 `registry.py:90-133` thêm mặc định `unrestricted: bool = False` cho `_granted_specs`, `get_tool_schemas` và 3 `grants_*` trong khi Returns của T63 ghi 4 đối số không mặc định và `change_enabled` cố ý không có mặc định (`test_registry.py:314`); hướng an toàn (quên → không cấp) và giữ được các lời gọi 3 đối số ngoài touchpoints (`test_propose_change.py:54,388`, `test_run_status.py:45`, `test_site_api.py:46,326`) — nên ghi lý do cạnh chữ ký hoặc bỏ mặc định khi các file kia được sửa; (2) STD-TEST-8 `test_registry.py:307-314` không đưa `grants_site_admin_tools`, `grants_unrestricted_tools` vào kiểm chữ ký và không ghim mặc định của `unrestricted`; (3) STD-TEST-8 `test_registry.py:742-745` ca được cấp chỉ kiểm `!= NOT_GRANTED` — thêm kiểm khóa `ok`/lý do của handler (ví dụ bản ghi không có) | tùy dev

## Review checklist (10)
Đã phủ 10/10.
1. Đúng và đủ task, không thừa (STD-DESIGN-5, STD-TEST-2): đạt — đủ 5 Expect: ma trận 32, mức lạ, `execute_tool` từ chối `api_delete_record`, AC-32 đọc meta, runner một lời gọi, vượt ngân sách L3 → L1 còn toàn quyền.
2. Trong touchpoints, không file mới (STD-DESIGN-1, STD-STRUCT-1/2): đạt.
3. Test đỏ trước; cạnh (L0, mức lạ, thiếu người ra lệnh, vượt ngân sách); không skip/xfail (STD-TEST-1/8/4): đạt — không có `skip_markers` trong diff.
4. Không đổi test để khớp hành vi sai; test độc lập (STD-TEST-5/6): đạt — test runner đặt mọi cấu hình cấp trong `setUp`, không đọc site chung; `TestGrantTable` rollback.
5. Lỗi và kiểm đầu vào (STD-ERR-1/2/5): đạt — `execute_tool` vẫn kiểm cấp rồi kiểm schema trước handler, savepoint giữ.
6. Bảo mật (STD-SEC-1/3/4/6): đạt — không đường cấp nào rộng hơn trước (32 tổ hợp khớp mã nền); không bí mật, không chạm `protected_paths`.
7. Hợp đồng (STD-DESIGN-3, STD-OPS-2): trượt (STD-GIT-2 ở trên) — bỏ `get_unrestricted_tool_schemas` là theo ADR-023 nhưng còn một lời gọi trong `test_site_api.py`.
8. Tên, cấu trúc, style, không mã chết (STD-NAME-1/2, STD-STYLE-4/5): đạt.
9. Không thêm phụ thuộc (STD-DEP-1/3/5): đạt.
10. Commit `refactor(registry): … (FEAT-004)`, nhánh `team/FEAT-004-task-63`, không dòng ghi công AI (STD-NAME-4/5, STD-GIT-1/8): đạt; STD-GIT-2 xem phát hiện.

## Bằng chứng của dev
- RED: `test_registry` `TypeError: get_tool_schemas() takes 3 positional arguments but 4 were given`, `AssertionError: True is not false : _unrestricted_specs`; `test_agent_runner` `test_runner_asks_registry_once` nhận `Actual: get_tool_schemas('L3', True, True)`.
- GREEN: `test_registry` `Ran 41 tests` OK; `test_agent_runner` `Ran 75 tests` chưa xanh trọn trong 8 lần (14–61 `QueryDeadlockError` mỗi lần trên site chung; mỗi test đạt ít nhất một lần trừ 3 test `auto_assign` đã biết).
- Reviewer không chạy test (site `miyano` dùng chung); gợi ý: `cmd.test_one` cho `erp_ai/agent/tools/test_registry.py`, `erp_ai/agent/test_agent_runner.py`, và sau vòng 2 `erp_ai/agent/tools/test_site_api.py`.

## Không kiểm được từ diff (tech-lead xử lý)
- `test_agent_runner` chưa có một lần chạy xanh trọn (deadlock trên site chung): cần một lần chạy riêng module khi site rảnh để xác nhận hai test mới cùng các test cũ xanh trong cùng một lần.
- AC-32 "người không có quyền → lỗi quyền": test chỉ đọc `meta.permissions` (đúng Expect của T63); `Custom DocPerm` trên site có thể mở thêm quyền ghi mà test này không thấy — nếu cần, kiểm ở T65 (ghi thử dưới user không phải System Manager).
- T68 (`check_registry_has_one_grant_function`) sẽ ghim tĩnh việc runner gọi `get_tool_schemas` đúng một chỗ; hiện chỉ có kiểm động bằng mock.

## deferred
- (không có)
