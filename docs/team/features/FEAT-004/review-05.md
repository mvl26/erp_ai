Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 05 — FEAT-004 T5

- Diff: `git diff dee2daa..team/FEAT-004-task-5` (2 commit `944b250`, `d62f6ec`; 3 file)
- Vòng: 2 (max_rework=3)
- Verdict: design-defect (T5 ĐỖ, chưa merge; chặn T6, T18, T29)

## Vòng 1 — design-defect + 1 major (`git diff dee2daa..944b250`)
Lớp 1: Returns đạt. 3 câu từ chối trùng từng chữ design 3.6; bỏ dòng trùng/rỗng; app lõi qua khi có thư mục; `POLICY_FIELDS` 6 tên, giữ `auto_assign_enabled`; hàm FEAT-006 không đổi.

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major (design-defect) | STD-DESIGN-6 | erp_ai/agent/policy.py:9 | Vòng import policy → tools.source (source.py:9 import `tools.read._schema`) → tools.read (read.py:4 import policy) → policy. Design ép cạnh mới: 3.6 đặt `validate_change_apps` ở policy và bắt kiểm `apps/<x>`; 3.6 và 8.2 (`test_apps_root_single_function`) coi `source.get_source_root` là hàm gốc duy nhất. `LAYER_RULES` không có luật nào bắt được | designer chọn cạnh để cắt (xem vòng 2) |
| major | STD-DESIGN-5 | erp_ai/agent/policy.py:116-122 | `change_settings` lặng lẽ bỏ `erp_ai` và tên sai regex; Returns và design 3.6 không yêu cầu; design 3.2:296 mong "`erp_ai` có trong `allowed_apps` vẫn bị `APP_FORBIDDEN`"; docstring nói quá | trả `_change_app_lines(...)` không lọc, bỏ test cũ, sửa docstring |

minor | — | — | 1 điểm nhỏ: hằng `APP_NAME` chứa regex → `APP_NAME_PATTERN` | tùy dev
- `test_runs_today_ignores_change_rows` không thể đỏ trước (bộ lọc `classify|reason` có sẵn, ADR-012 QĐ 6 bảo giữ); là test ghim hồi quy, đỏ được khi thêm `change` vào bộ lọc → không là phát hiện.

## Vòng 2 — design-defect còn mở (re-review theo phạm vi, `git diff 944b250..team/FEAT-004-task-5`)
- Phát hiện 1 (STD-DESIGN-6): NOT ADDRESSED (dev được dặn không đổi mã, chỉ đo). Đo trên nhánh task, mỗi lệnh một tiến trình mới: `env/bin/python -c "import erp_ai.agent.tools.read"` → thoát 1, `ImportError: cannot import name '_schema' from partially initialized module 'erp_ai.agent.tools.read' (most likely due to a circular import)` (source.py dòng 9); `-c "import erp_ai.agent.policy"` → thoát 0; test_read `Ran 27 tests … OK`, test_registry `Ran 32 tests … OK`, test_agent_runner `Ran 57 tests … OK` (xanh chỉ nhờ thứ tự import). Dev không sửa được trong T5: hai cạnh còn lại (source→read, read→policy) có từ `dee2daa`, ngoài `files:` của T5.
  - Quyết định designer phải chọn: (a) khuyến nghị: chuyển `_schema` từ read.py sang registry.py (chỉ import `erp_ai.constants`), source.py và read.py import từ đó; không đổi hợp đồng, nhưng read.py, source.py, registry.py vào touchpoint; (b) chuyển kiểm tồn tại `apps/<x>` khỏi policy sang controller `ERPAISetting.validate` (viết lại dòng `validate_change_apps` của 3.6); (c) import trong thân hàm KHÔNG chấp nhận (giấu vòng, vẫn trái STD-DESIGN-6). Phương án nào cũng thêm test kiến trúc import `erp_ai.agent.tools.read` ở tiến trình mới.
- Phát hiện 2 (STD-DESIGN-5): ADDRESSED (`policy.py:116-121` không lọc; `test_policy.py:257-260` `test_change_settings_keeps_names_validate_would_refuse`; đổi tên `APP_NAME_PATTERN`)
- Phát hiện mới: không có blocker/major

## Review checklist (10)
Đã phủ 10/10; còn mở mục 1/8 (STD-DESIGN-6) do design.

## Bằng chứng của dev
- Vòng 1 RED: test_policy `Ran 35 tests … FAILED (errors=28)` (`AttributeError: module 'erp_ai.agent.policy' has no attribute 'validate_change_apps'`); test_architecture `FAILED (failures=2)` "scanner missed the violation"; GREEN: test_policy `Ran 35 tests in 2.272s` / `OK`; test_architecture `Ran 108 tests in 1.739s` / `OK`
- Vòng 2 RED: `AssertionError: Tuples differ: ('myapp',) != ('erp_ai', '../x', 'myapp')`, `FAILED (failures=1)`; GREEN: test_policy `Ran 35 tests in 5.862s` / `OK`; test_architecture `Ran 108 tests in 1.772s` / `OK`

## Không kiểm được từ diff (tech-lead xử lý)
- `test_change_guard` có phủ `allowed_apps` chứa `erp_ai` và `../x` không (bộ chặn nay là lớp duy nhất cho giá trị ghi vượt validate): T8 có `test_erp_ai_refused_even_when_listed_in_temp_root`; ca `../x` kiểm lại khi T42 làm.
- Ai import `tools.read` trước trong worker/`frappe.get_attr` ở prod: thuộc quyết định design ở trên.

## deferred
- Không có.
