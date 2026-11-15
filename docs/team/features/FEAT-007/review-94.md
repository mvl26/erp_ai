Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 94 — FEAT-007 T94

- Diff: `git diff 43ae572..5f3f31a` (nhánh `team/FEAT-007-task-94`; 1 commit, 2 file +161/−3)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve; merge `8bf4461` trên `team/FEAT-007`
- File này do tech-lead viết từ báo cáo của reviewer (reviewer chỉ đọc, không ghi file).

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED `test_tasks`, 5 test đỏ vì assertion: `AssertionError: Lists differ: [] != [('Quyền mở rộng đang bật', 'Quyền mở rộng[63 chars]ch')]` (two_switches); `...[] != [('Quyền mở rộng đang bật', 'Quyền mở rộng đang bật: Toàn quyền (khẩn cấp)')]` (all_off); `...[] != [('Quyền mở rộng đang bật', ...)]` (no_log_row_keeps_watermark); `AssertionError: 0 != 1` (error_later_rolls_back); `FAILED (failures=5)`; GREEN `Ran 71 tests in 9.476s` `OK`; `test_architecture` `Ran 181 tests in 15.386s` `OK`.
- Nhận xét của tech-lead về RED: đỏ vì cảnh báo chưa được phát (danh sách rỗng), tức thiếu hành vi.
- Tier 1 (đối chiếu spec): đạt. `PERMISSION_SWITCHES_ON_SUBJECT` ở `erp_ai/tasks.py:40`; `_enabled_permission_switches()` theo `U3.md` 3.7 (`get_single` → `policy.permission_switches` → `astuple` ghép với `PERMISSION_SWITCH_FIELDS` → `meta.get_label`); là phần tử thứ năm của `checks` (`tasks.py:306-307`), cùng khối try, giao dịch và filelock; không đọc mốc, không ghi dòng ERP AI Log; `tasks.py` không viết tên trường nào. Test thêm `test_switch_condition_is_the_fifth` ghim chữ "thứ năm" của Returns.
- Checklist (10): 1 đạt · 2 đạt (sửa `setUp` có sẵn của `TestCheckPrivilegeEscalation` nằm trong touchpoint và cần thiết: công tắc đang bật trên site sẽ thêm cảnh báo vào assertion của lớp đó) · 3 đạt (mỗi công tắc được ghim với nhãn của nó ở ít nhất một test; hai công tắc không kề nhau đặt ngược thứ tự; chạy hai lần cùng cửa sổ; lỗi khi đẩy mốc thì email cảnh báo rollback, có ca đối chứng) · 4 đạt (`keep_agent_settings`, chặn commit, `now=RUN_AT`) · 5 đạt · 6 đạt · 7 đạt · 8 đạt · 9 đạt (chỉ `dataclasses` và `erp_ai.agent.policy`) · 10 đạt (1 commit `feat(tasks): ... (FEAT-007)`).

### Findings

Không có blocker, không có major.

- minor | STD-TEST-8 | `erp_ai/tests/test_tasks.py:1689` | `reads.call_count == 2` chỉ bọc `tasks.read_privilege_watermark`; nếu helper gọi thẳng `erp_ai_setting.read_privilege_watermark` thì khẳng định "không đọc mốc" vẫn xanh (một lần đọc là vô hại, assertion mốc cuối vẫn bắt được mọi dịch chuyển) | bọc cả hàm gốc

### Không kiểm được từ diff — tech-lead giải

- RED/GREEN là đầu ra của dev: tech-lead chạy lại sau merge `8bf4461`, một lần giữ khóa site, `MIGRATE_EXIT=0`: `test_tasks` `Ran 71 tests in 9.010s OK`; `test_architecture` `Ran 181 tests in 15.523s OK`.
- Luật `POLICY_FIELDS` của `test_architecture` có quét `tasks.py` hay không: chưa đọc luật; `test_architecture` xanh trên nhánh sau merge, và reviewer xác nhận bằng mắt `tasks.py` không viết tên trường nào. Chuyển T83 (luật kiến trúc của U1) kiểm phạm vi quét.
- C-9 của arch-review (tập trường đọc từ meta ở `erp_ai_setting.py` phải bằng `policy.PERMISSION_SWITCH_FIELDS`) thuộc task controller của U3 (T87), không thuộc T94.
- `cmd.lint`: `pre-commit run --all-files` trên `2aed7d6` (sau merge T94 và T84), mọi hook `Passed`.

## deferred

- Minor trên (dev's call).
