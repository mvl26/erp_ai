Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 66 — FEAT-007 T66

- Diff: `git diff 7821d401614544b778d8a13505e82fa35477a337..ddc8507` (nhánh `team/FEAT-007-task-66`; 1 commit, 2 file +110/−1)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve; merge `aef271c` trên `team/FEAT-007`
- File này do tech-lead viết từ báo cáo của reviewer (reviewer chỉ đọc, không ghi file).

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED `FAIL: test_each_field_maps_to_its_flag` và `FAIL: test_missing_fields_read_off`, `AssertionError: False is not true : policy has no permission_switches`, `Ran 40 tests in 1.899s FAILED (failures=2)`; GREEN `Ran 40 tests in 1.833s OK`; `test_architecture` `Ran 181 tests in 15.636s OK`.
- Nhận xét của tech-lead về RED: đỏ vì `policy` chưa có `permission_switches` (thiếu hành vi), báo bằng assertion, không phải lỗi import.
- Tier 1 (đối chiếu spec): đạt. Đủ `RECORD_TOOLS_FIELD`, `ACT_NOW_FIELD`, `ONE_CLICK_APPROVAL_FIELD`, `UNRESTRICTED_FIELD`, `PERMISSION_SWITCH_FIELDS` theo thứ tự (1)..(5), `PermissionSwitches` (frozen), `permission_switches(settings)`; tên trùng U1 3.1 và "Ràng buộc chung". `unrestricted` dùng lại `unrestricted_enabled`, `code_change` dùng lại `change_settings(settings).enabled` (`U1.md:122`). Trường thiếu đọc là tắt, không ném lỗi. Không gì ngoài touchpoints.
- Checklist (10): 1 đạt (AC-3 phần đọc: bật riêng từng công tắc, đổi chỗ hai trường là đỏ; AC-1 phần đọc) · 2 đạt · 3 đạt (ca biên: `object()`, `frappe._dict()`, 0/None/"", bản ghi đã lưu, frozen) · 4 đạt (`keep_agent_settings`, rollback; giá trị mong đợi viết cứng trong `FIELD_FLAGS`) · 5 đạt · 6 đạt · 7 đạt · 8 đạt (`git grep`: ngoài `policy.py` không file `.py` nào trừ test đọc thẳng năm trường) · 9 không áp dụng · 10 đạt (1 commit `feat(policy): … (FEAT-007)`).

### Findings

Không có blocker, không có major.

- minor | STD-TEST-8 | `erp_ai/agent/test_policy.py` (`test_missing_fields_read_off`, dòng đầu) | so `PermissionSwitches() == PermissionSwitches(*off.values())` với toàn `False`, nên đổi thứ tự field của dataclass vẫn xanh dù "Ràng buộc chung" ghi thứ tự vị trí | dựng bằng 5 đối số vị trí kiểu one-hot rồi đọc lại theo tên

### Không kiểm được từ diff — tech-lead giải

- `cmd.lint`: `pre-commit run --all-files` trên `team/FEAT-007` @ `aef271c`, mọi hook `Passed`.
- Test sau merge (`aef271c`, một lần giữ khóa site, `MIGRATE_EXIT=0`): `test_policy` `Ran 40 tests in 1.767s OK`; `test_architecture` `Ran 181 tests in 15.367s OK`.

## deferred

- Minor STD-TEST-8 trên (dev's call). Các task kế cùng file `test_policy.py` (T67..T71) nhận finding này ở mục "finding hay lặp" của lời giao.
