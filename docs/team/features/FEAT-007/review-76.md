Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 76 — FEAT-007 T76

- Diff vòng 1: `git diff caa555a7158708ed8ff377c864da338ea7a9464a..c3c3a85` (nhánh `team/FEAT-007-task-76`; 3 commit `39bc62c` test, `4070686` test, `c3c3a85` mã; 2 file +270/−48, đều là touchpoint)
- Diff vòng 2 (soát lại có phạm vi): `git diff c3c3a85..45fa915` (2 commit `b116907` test, `45fa915` refactor; 2 file +18/−5)
- Vòng: 2 (một vòng sửa; trần `max_rework` = 3)
- Verdict: approve (vòng 2); merge `5c1957f` trên `team/FEAT-007`
- File này do tech-lead ghi từ báo cáo của reviewer (vai reviewer không ghi file dưới `docs/`); chữ finding của reviewer giữ nguyên.

## Vòng 1 — changes-requested

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED (sau `39bc62c`, `4070686`), `MIGRATE_EXIT=0`: `test_grant_matrix_matches_snapshot`: `AttributeError: module 'erp_ai.agent.tools.registry' has no attribute 'grant'`; `test_each_switch_alone_adds_only_its_declared_set`: `... no attribute 'GrantInputs'`; `test_grant_inputs_maps_context_fields`: `AttributeError: 'ToolContext' object has no attribute 'grant_inputs'`; `test_bridge_change_switch_still_brings_record_tools`: `TypeError: ToolContext.__init__() got an unexpected keyword argument 'record_tools'`; `test_grant_functions_take_change_enabled_without_default`: `... no attribute '_legacy_inputs'`; 2 failure (`_granted_specs`, trường context); `Ran 46 tests in 1.527s FAILED (failures=2, errors=57)`. GREEN @ `c3c3a85`, một lần giữ khóa, `MIGRATE_EXIT=0`: test_registry `Ran 46 tests in 1.418s OK`, test_site_api `Ran 77 tests in 25.909s OK`, test_tasks `Ran 71 tests in 9.567s OK`, test_propose_change `Ran 32 tests in 24.584s OK`, test_agent_runner `Ran 110 tests in 31.073s OK`, test_architecture `Ran 182 tests in 16.342s OK`. `git grep -n permission_level -- erp_ai/agent/tools/registry.py`: không dòng nào.

Theo từng mục checklist (10):

1. Phạm vi (STD-DESIGN-5, STD-TEST-2): Returns làm đủ. Không còn `_granted_specs`, không có `permission_level`. Cầu `record_tools or change_enabled` có kèm chú thích T82. Không gì của T77 lọt vào: không `ASK_TOOL_NAMES`, không vế dưới ngưỡng hay vượt ngân sách trong bảng, `act_now_block`/`ask_only_block` mặc định False, `record_block` chưa có `¬unrestricted_block`. Một mục của Returns không test nào ghim (major 1).
2. Touchpoint (STD-DESIGN-1, STD-STRUCT-1): chỉ `registry.py`, `test_registry.py`; không file mới. Import một chiều `registry → policy`.
3. Test trước, biên, không skip (STD-TEST-1/8/4): hai commit test đứng trước commit mã. RED đúng lý do. Biên có: L0, mức lạ `LX`, không người ra lệnh, L1/L2 với công tắc (2), (4), đường chính L0.
4. Không nới test, lặp lại được (STD-TEST-5/6): mọi khẳng định cũ bị đổi đều là chỗ Expect nêu tên.
5. Lỗi và biên (STD-ERR-1/2/5): chữ từ chối giữ nguyên.
6. Bảo mật (STD-SEC-1/3/4/6): phân quyền chuyển vào `grant` với cùng điều kiện.
7. Hợp đồng (STD-DESIGN-3, STD-OPS-2): chữ ký bốn tham số cũ giữ qua `_legacy_inputs`; trường mới của `ToolContext` đứng sau `unrestricted`, đều có mặc định. Không migrate.
8. Tên, cấu trúc, mã chết (STD-NAME-2, STD-STYLE-4/5): `unrestricted_granted` là tên thiết kế dùng (`U1.md:168`).
9. Phụ thuộc (STD-DEP-1/3/5): không thêm.
10. Commit và tài liệu (STD-NAME-5, STD-GIT-1/8): đúng dạng, không dòng ghi công AI.

Phép kiểm riêng: cả tám test của Expect có mặt, bảy cái ghim đúng thứ nó nêu. Snapshot 32 dòng so tên tool theo thứ tự, `names()` và ba cờ theo luật tên; không so thân schema (CI-5 đạt). Luật `check_registry_has_one_grant_function` @ `caa555a`: chỉ `grant` đọc `GRANT_TABLE` và gọi `_all_specs`; ba nơi tiêu thụ đều gọi `grant`.

Findings:

- major | STD-TEST-2 | `erp_ai/agent/tools/test_registry.py:757-761` | Returns says "`execute_tool` dùng `grant(context.grant_inputs()).specs`", and Expect says "gọi đúng một lần với `context.grant_inputs()`". The only context the test uses is `_context("L2", "boss@x.com", change_enabled=True, unrestricted=True)`, with every new field at its default. For that context, `context.grant_inputs()` gives the same `GrantInputs` as `_legacy_inputs("L2", True, True, True)`: same levels, has_instructor True, switches (unrestricted, record_tools, code_change) = True, the rest False. So if `execute_tool` stayed on `grant(_legacy_inputs(context.effective_level, bool(context.instructor), context.change_enabled, context.unrestricted))`, `assert_called_once_with` still passes. No other `execute_tool` call in the file sets `record_tools`, `main_path_level` or `act_now`, and the architecture rule only checks that `grant` is called. That mutation stays green in this diff. | Use a context where the two builders differ, e.g. `dataclasses.replace(context, change_enabled=False, record_tools=True, act_now=True, main_path_level="L1")`. Better, also add one behavior check: with `record_tools=True, change_enabled=False` at L3 with an instructor, `api_list_records` is not `NOT_GRANTED`; with `main_path_level="L0"`, a task tool is `NOT_GRANTED`.
- minor | — | — | 2 small points: (a) `grant` derives the flags from `granted_groups` (the groups of the returned specs) instead of the `groups` set. The result is the same as long as every group has at least one spec, but it is a step away from the design's "nhóm … được cấp". (b) In `unrestricted_granted`, `effective_level in LEVELS[1:]` replaces `!= LEVELS[0]`; inside `grant` this is the same because step (1) runs first. | dev's call

Mục "không kiểm được từ diff" của reviewer: reviewer không chạy test; `test_architecture` xanh ở `c3c3a85` và năm module ngoài touchpoint xanh trên cầu chỉ dựa vào dòng GREEN của dev; "57 errors" trên 46 test hợp với lỗi theo subTest, không xác nhận được từ diff.

## Vòng 2 — approve (soát lại có phạm vi, `c3c3a85..45fa915`)

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED đột biến (`execute_tool` chuyển về `grant(_legacy_inputs(context.effective_level, bool(context.instructor), context.change_enabled, context.unrestricted))`, không commit, rồi `git restore`), `MIGRATE_EXIT=0`: `FAIL: test_execute_asks_the_one_grant_function … AssertionError: expected call not found.`; `FAIL: test_execute_grants_by_the_context_fields_not_the_legacy_switches …`; `Ran 47 tests in 1.234s FAILED (failures=2)`. GREEN @ `45fa915`, một lần giữ khóa, `MIGRATE_EXIT=0`: test_registry Ran 47 tests, OK; test_site_api Ran 77 tests, OK; test_tasks Ran 71 tests, OK; test_propose_change Ran 32 tests, OK; test_agent_runner Ran 110 tests, OK; test_architecture Ran 182 tests, OK.
- major STD-TEST-2 (`test_registry.py:757-761`): ADDRESSED. Ở `test_registry.py:757-768` context của test đặt `record_tools=True`, `act_now=True`, `main_path_level="L1"`, `change_enabled` để False; dòng 765 khẳng định `context.grant_inputs() != _legacy_inputs("L2", True, False, True)`, nên `assert_called_once_with` không còn qua được nếu `execute_tool` dùng hàm dựng cũ. Test hành vi mới `test_execute_grants_by_the_context_fields_not_the_legacy_switches` (`:770-775`): L3, có người ra lệnh, `record_tools=True`, `change_enabled=False` → `api_list_records` không phải NOT_GRANTED; `main_path_level="L0"` ở L3 → `create_task` NOT_GRANTED. Cả hai đỏ nếu bỏ hành vi; RED đột biến của dev khớp.
- minor (a): ADDRESSED. `registry.py:145-147` đọc tập `groups`.
- minor (b) (`registry.py:101`): không đổi, dev quyết; kết quả trong `grant` như nhau.
- Commit refactor `45fa915` so với checklist: cờ lấy từ "nhóm được cấp" đúng chữ thiết kế; `act_now_block`, `ask_only_block` vẫn False; không vế vượt ngân sách hay dưới ngưỡng, không gì của T77 lọt vào; snapshot 32 dòng (`:723-725`) ghim ba cờ theo tên tool; hành vi không đổi vì mọi nhóm của `GRANT_TABLE` có ít nhất một spec. Mục 1-10: đạt.
- Finding mới: không. Ngoài phạm vi (deferred): không.
- Không kiểm được từ diff: GREEN sáu module ở `45fa915` chỉ là bằng chứng của dev; `api_list_records` trên `Note` (`:772`) chạy handler thật trên dữ liệu site, test chỉ khẳng định kết quả không phải NOT_GRANTED nên không phụ thuộc dữ liệu.

## Kết luận của tech-lead

- Chạy test: sau merge `5c1957f`, một lần giữ khóa site, `MIGRATE_EXIT=0`: test_registry `Ran 47 tests in 1.177s OK`, test_site_api `Ran 77 tests in 24.234s OK`, test_tasks `Ran 71 tests in 8.714s OK`, test_propose_change `Ran 32 tests in 23.590s OK`, test_agent_runner `Ran 110 tests in 29.829s OK`, test_architecture `Ran 183 tests in 16.415s OK`. Không còn mục nào mở.
- minor (b): không mở vòng sửa.
