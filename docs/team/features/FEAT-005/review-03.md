Feature: FEAT-005
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 03 — FEAT-005 T3

Tech-lead chép từ tin trả về của reviewer (reviewer không ghi file).

- Diff: `git diff 568daa5..7588d1e` (nhánh `team/FEAT-005-task-3`, 2 commit: `d737a01`, `7588d1e`; merge `e12e65d`)
- Vòng: 2
- Verdict: approve (vòng 2)

## Vòng 1 — request-changes (`568daa5..d737a01`)

Lớp 1 (khớp spec): `GENERIC_WRITE_TOOLS` suy từ `WRITE_TOOL_TARGETS` (test đọc nguồn, đỏ khi viết tay tên tool); `_record_snapshot` gọi ngay sau `actions.append` với `n = len(actions)`, luôn bỏ `_snapshot` trước `json.dumps`, khóa cũ của tool phiếu giữ nguyên. AC-13 (c): `test_snapshot_never_reaches_model`; ca (1), (d), ca (5): `test_create_user_snapshot_lists_both_roles`, `test_two_calls_same_tool_one_turn_two_snapshots`; Review focus 1 (lời gọi đầu bị từ chối → `#2`, không `#1`) có khẳng định. Chỉ hai file touchpoint.

- major | STD-TEST-2 | erp_ai/agent/test_agent_runner.py:1712 (và :1755/:1785) | Ý "`n = len(actions)`" (vị trí trong mọi mục hành động của lượt, design-amd2 §2) không có test nào làm vị trí khác với "số lần gọi cùng tool": đổi `runner.py:696` thành `sum(a["tool"] == name for a in actions)` thì 5 test vẫn xanh; T8 tra `<tool>#<i>` theo mọi mục nên sẽ mất ảnh chụp sau `post_comment` | Thêm lượt có tool ghi khác đi trước rồi `api_update_record` thành công; khẳng định đúng dict `{"api_update_record#2": …}`, không có `#1`
- minor | — | — | 1 điểm nhỏ: `test_generic_write_tools_derived_from_write_tool_targets` mở đầu bằng phép so hằng với chính biểu thức của mã | tùy dev

Bằng chứng của dev: RED `module 'erp_ai.agent.runner' has no attribute 'GENERIC_WRITE_TOOLS'`, `1 != 0` (`test_snapshot_never_reaches_model`), `Ran 83 tests` / `FAILED (failures=4, errors=6)`; GREEN `--case TestRunnerRecordSnapshots` `Ran 5 tests` / `OK`.

## Vòng 2 — approve (`d737a01..7588d1e`, re-review theo phạm vi)

- major STD-TEST-2: ADDRESSED (`test_agent_runner.py:1751` `test_position_counts_every_action_not_only_the_same_tool`: `post_comment` trước, `api_update_record` sau; so nguyên dict `{"api_update_record#2": …}`)
- minor: ADDRESSED (bỏ phép so thừa; giữ danh sách ghim và phép kiểm AST)
- Phát hiện mới: không có.

Bằng chứng của dev: đột biến bộ đếm theo tool → `{'api_update_record#1': …} != {'api_update_record#2': …}`, `Ran 6 tests ... FAILED (failures=1)`; trả lại → `Ran 6 tests in 3.992s OK`.

## Không kiểm được từ diff (tech-lead xử lý)

- Test có sẵn của F4-T63/T64 "xanh nguyên": site `miyano` đang bị ba phiên dùng chung nên chưa có lượt cả module nào sạch deadlock. Sau merge `e12e65d`, tech-lead chạy `cmd.test_one` test_agent_runner hai lượt trên `team/FEAT-005`:
  - lượt 1: `Ran 84 tests in 68.929s` / `FAILED (failures=10, errors=2)`: 2 `QueryDeadlockError`; 3 ca nhiễu cài đặt của dòng `baseline:`; 7 lần FAIL ở 5 ca dùng tool bản ghi thật (`test_fake_secret_never_in_actions_column`, `test_position_counts_every_action_not_only_the_same_tool`, `test_record_tool_action_carries_before_after_and_instructor` ×3 subTest, `test_record_tool_runs_for_real_and_the_log_names_the_record`, `test_two_calls_same_tool_one_turn_two_snapshots`)
  - lượt 2: `Ran 84 tests in 46.603s` / `FAILED (failures=3, errors=5)`: đúng 3 ca nhiễu cài đặt; 5 `QueryDeadlockError` ở 5 ca khác (đều xanh ở lượt 1); 5 ca FAIL của lượt 1 đều xanh
  - Phán: mọi ca ngoài 3 ca nhiễu cài đặt đã xanh ít nhất một lượt; FAIL không lặp lại của lượt 1 là nghi do deadlock bị `site_api._write` bắt thành `ok=false` (suspected, chưa chứng minh; dev T3 cũng thấy `test_record_tool_runs_for_real…` đỏ một lần). Theo quy tắc của lượt (chạy lại một lần, ghi chú) → tick T3. Một dòng `OK` nguyên vẹn của module chỉ có ở T16 khi cài đặt tạm để trống và site yên.
- Test tạo User cần role `Blogger` và `Knowledge Base Editor` có trên site: xanh ở cả hai lượt trên.

## deferred

Không có.
