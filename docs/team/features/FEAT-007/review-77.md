Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 77 — FEAT-007 T77

- Diff: `git diff 5c1957fabf3bb13c8c8a5c12a2e051e1d088fd09..5c4398e` (nhánh `team/FEAT-007-task-77`; 2 commit `5509ef1` test, `5c4398e` mã; 2 file +191/−16, đều là touchpoint)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve; merge `9601204` trên `team/FEAT-007`
- File này do tech-lead ghi từ báo cáo của reviewer (vai reviewer không ghi file dưới `docs/`); chữ của reviewer giữ nguyên ý, finding giữ nguyên văn.

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED 1 (commit test `5509ef1` trên mã T76), `MIGRATE_EXIT=0`: `ImportError: cannot import name 'ASK_TOOL_NAMES' from 'erp_ai.agent.tools.registry'` (không có dòng `Ran`). RED 2 (chỉ thêm `ASK_TOOL_NAMES`, chưa commit): `test_act_now_block_needs_a_power_group` 3 subtest `AssertionError: False is not True`; `test_below_threshold_grants_read_and_ask_tool_only` `Lists differ`; `test_over_budget_with_all_switches_equals_l1_all_off` ×2; `test_record_block_hidden_when_unrestricted_granted` `Tuples differ: (True, True) != (True, False)`; `test_unrestricted_at_l1_not_over_budget_is_granted`; `test_grant_matrix_matches_snapshot` 7 subtest; `Ran 55 tests in 1.291s FAILED (failures=15)`. GREEN @ `5c4398e`, một lần giữ khóa, `MIGRATE_EXIT=0`: test_registry `Ran 55 tests in 1.251s OK`, test_site_api `Ran 77 tests in 26.883s OK`, test_agent_runner `Ran 110 tests in 30.711s OK`, test_architecture `Ran 183 tests in 16.224s OK`, test_propose_change `Ran 32 tests in 24.169s OK`, test_tasks `Ran 71 tests in 8.702s OK`. `git grep -n permission_level -- erp_ai/agent/tools/registry.py`: không dòng nào.

Các phép kiểm chính của reviewer:

1. Bảng `U1.md:170-177` và bước (3), từng vế: khớp hết. `read` luôn cấp; `ticket_write` = `¬below_threshold` (`registry.py:116`); `task_write` = `has_instructor ∧ main_path_level ∈ L1..L3 ∧ ¬below_threshold` (`:117-122`); `change_propose` = `code_change ∧ effective_level == L3 ∧ has_instructor ∧ ¬below_threshold` (`:123-129`); `site_admin` = `((record_tools ∧ L3 ∧ has_instructor) ∨ u) ∧ ¬below_threshold` (`:131-137`); `site_unrestricted` = `u`, với `u` (`:101-109`) = `unrestricted ∧ effective_level > L0 ∧ has_instructor ∧ ¬over_budget ∧ ¬below_threshold`; bước (3) (`:157-162`) lấy spec từ `_all_specs()` theo thứ tự, giữ nhóm được cấp cộng spec `ticket_write` có tên trong `ASK_TOOL_NAMES` khi dưới ngưỡng; `ASK_TOOL_NAMES = frozenset({"post_comment"})` (`:98`); không có `permission_level`.
2. Năm cờ `U1.md:181-187`: khớp hết. `record_block` = `site_admin ∧ ¬unrestricted_block`; `act_now_block` = `switches.act_now ∧ (groups ∩ {change, site_admin, unrestricted} ≠ ∅)`; `ask_only_block` = `below_threshold` ("mức > L0" do lối ra sớm L0/mức lạ ở `:153-154` bảo đảm).
3. Lần theo đột biến (đọc mã): bỏ `¬below_threshold` ở bất kỳ nhóm nào hay ở `u` → `test_below_threshold_grants_read_and_ask_tool_only` đỏ; bỏ `¬over_budget` ở `u` → ba test vượt ngân sách đỏ; bỏ phần cộng của bước (3) → thiếu `post_comment`, test dưới ngưỡng đỏ (subtest vá hằng chứng minh mã đọc hằng lúc gọi); bỏ `¬unrestricted_block` ở `record_block` → 6 dòng snapshot và test `record_block` đỏ; bỏ vế `act_now` → hai ca đỏ; bỏ `CHANGE_GROUP` hay `SITE_ADMIN_GROUP` khỏi tập act-now → ca "(3)+(4) ở L3", "(3)+(2) ở L3" đỏ; nới act-now sang `task_write` → ca "(3) một mình", "(3)+(5)" đỏ; ép `ask_only_block` False/True → test dưới ngưỡng/snapshot đỏ. Ba đột biến sống sót, không cái nào đổi được hành vi: `UNRESTRICTED_GROUP` trong tập act-now (`u` kéo theo `site_admin`), `inputs.below_threshold` ở bước (3) (không dưới ngưỡng thì `ticket_write` đã cấp đủ), `spec.group == "ticket_write"` ở bước (3) (tên tool duy nhất). Không phải finding.
4. RED đúng lý do: RED 1 là `ImportError` chờ đợi; RED 2 có 15 failure khớp bốn nguyên nhân đỏ của dòng Expect. Ba trong tám test của Expect đã xanh trên mã T76 (`test_record_on_act_now_off…`, `test_category_c_cap_keeps_code_tools_at_l3`, `test_l1_main_path_has_no_erp_write_tools`): hợp với dòng Expect, chúng ghim hành vi AC-6, AC-31, AC-32 mà T76 đã có và vẫn đỏ được khi mã đọc sai mức.
5. Test snapshot: chỉ đổi kỳ vọng `record_block`, `act_now_block` đúng như `U1.md:396` và dòng Expect; không gì bị nới.
6. `grants_*`, `_grants_group`, `_legacy_inputs` không đổi; `ASK_TOOL_NAMES` là tên mức module mới duy nhất.
7. Touchpoint: chỉ hai file.

Checklist (10): 1 đạt (AC-6 cờ, AC-7, AC-22, AC-31, AC-32; không thừa); 2 đạt; 3 đạt (commit test trước; biên L0, không người ra lệnh, L2 nhóm đóng, mọi công tắc tắt dưới ngưỡng, vượt ngân sách có và không có người ra lệnh; không skip); 4 đạt; 5 đạt (hàm thuần, giữ chốt mức lạ/L0); 6 đạt (phân quyền hẹp lại); 7 đạt (đường bốn tham số cũ không đổi; cờ mới của `Grant` chưa có nơi đọc trước T82); 8 đạt; 9 không thêm phụ thuộc; 10 đạt.

Findings: không (không blocker, không major, không minor).

Mục "không kiểm được từ diff" của reviewer:

- Lần chạy GREEN, RED 2, và việc trạng thái mã của RED 2 chỉ có thêm `ASK_TOOL_NAMES`: chỉ có đầu ra của dev.
- `test_site_api.py`, `test_agent_runner.py` không đổi (diff cho thấy); chúng xanh thì diff không cho thấy.
- Tên trường của `PermissionSwitches` (`act_now`, `one_click_approval`, `record_tools`, `code_change`, `unrestricted`) có khớp `policy.py` không: reviewer suy từ test dựng được, không đọc `policy.py`.

## Kết luận của tech-lead

- Chạy test: sau merge `9601204`, một lần giữ khóa site, `MIGRATE_EXIT=0`: test_registry `Ran 55 tests in 1.370s OK`, test_site_api `Ran 77 tests in 25.356s OK`, test_agent_runner `Ran 110 tests in 33.808s OK`, test_architecture `Ran 183 tests in 17.336s OK`, test_propose_change `Ran 32 tests in 62.084s OK`, test_tasks `Ran 71 tests in 26.441s OK`.
- Tên trường `PermissionSwitches`: `plan-w1.md` "Ràng buộc chung" ghi `PermissionSwitches(unrestricted, record_tools, act_now, code_change, one_click_approval)` (T66 đã tick, `review-66.md`); `test_registry` dựng dataclass thật bằng các tên đó và xanh sau merge, nên khớp.
- RED 2 đo trên trạng thái chưa commit: không kiểm lại được; RED 1 (commit test, `ImportError`) là bằng chứng "test trước" đã commit. Không mở vòng sửa.
