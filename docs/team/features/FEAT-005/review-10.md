Feature: FEAT-005
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 10 — FEAT-005 T10

Tech-lead chép từ tin trả về của reviewer (reviewer không ghi file).

- Diff: `git diff 8ef96d5..e1c5ca0` (nhánh `team/FEAT-005-task-10`, 1 commit, `erp_ai/tasks.py` +14/−3, `erp_ai/tests/test_tasks.py` +96/−2); merge `46516b4`
- Vòng: 1
- Verdict: approve

## Vòng 1 — approve (`8ef96d5..e1c5ca0`)

Lớp 1: AC-14 ca (3) và A-19 đạt. Dấu `[QUẢN TRỊ] ` thêm khi role ∈ `FORBIDDEN_ROLES` được thêm hoặc gỡ (`tasks.py:119-125`); sắp ổn định đưa mục có dấu lên trước, giữ thứ tự `creation` trong từng nhóm (`tasks.py:157-158`); `_list_names` không đổi; `test_admin_role_marked_and_listed_first` đúng test kỳ vọng của task, so cả nội dung thư. Chỉ hai file touchpoint; không có gì của T11–T13.

Checklist (10): 10/10 đạt. Không phép khẳng định có sẵn nào bị đổi; mọi ghi của test được rollback ở `setUp`, `commit` bị patch để ném; `unrestricted_enabled`, role System Manager của user test, Role Profile và role test đều được trả lại; ngày gieo cố định (2031). Commit `feat(tasks): … (FEAT-005)`, không dòng ghi công AI, 0 dấu skip.

- Phát hiện blocker/major: không.
- minor | — | — | 2 điểm nhỏ: (a) STD-TEST-8 `test_admin_items_first_each_group_by_time` (`test_tasks.py:761-793`): thứ tự thời gian của nhóm `[QUẢN TRỊ]` trùng thứ tự chữ cái (`gỡ…08:12` trước `thêm…08:14`), sắp theo chữ trong nhóm đó vẫn xanh; sửa: đổi cho mục sớm hơn có chữ đứng sau; (b) `test_every_forbidden_role_is_marked_when_added_or_removed` lặp trên chính `site_api.FORBIDDEN_ROLES`, module này không ghim tập đó đúng 6 role của AC-14 | tùy dev

- Bằng chứng của dev: RED `FAIL: test_admin_role_marked_and_listed_first`, `AssertionError: '[QUẢN TRỊ] thêm role Guest cho add Guest (…)' not found in [...]`, `Ran 49 tests in 6.586s` / `FAILED (failures=8)`; GREEN cả module `Ran 49 tests in 5.649s` / `OK`; 5 đột biến đỏ (bỏ sắp, đảo thứ tự nhóm, không đánh dấu mục gỡ, `FORBIDDEN_ROLES - {"Guest"}`, đánh dấu mọi role).

## Tech-lead đã kiểm

- Sau merge `46516b4`, trong một lần giữ khóa `miyano-site.lock` (0 lệnh site ngoài khóa, migrate exit 0): test_tasks `Ran 49 tests in 4.974s` / `OK`.
- `git diff --name-only 8ef96d5..e1c5ca0` = `erp_ai/tasks.py`, `erp_ai/tests/test_tasks.py` (đúng touchpoint).

## Không kiểm được từ diff

- Có test nào ghim `FORBIDDEN_ROLES` đúng 6 role của AC-14 không: `git grep -n "FORBIDDEN_ROLES" -- erp_ai/agent/tools/test_site_api.py erp_ai/tests/test_architecture.py` trên `8ef96d5` không ra dòng nào (không test nào nêu hằng theo tên; có thể ghim bằng tên role). Hằng thuộc FEAT-004 (`site_api.py:31`), ngoài touchpoint của T10 → chuyển qa (verify) đối chiếu 6 role của AC-14; không chặn tick.
- `cmd.lint` cả repo: chạy ở T16 (dev báo `pre-commit run --all-files` Passed).

## deferred

- minor (a): ca thứ tự trong nhóm `[QUẢN TRỊ]` trùng thứ tự chữ cái (STD-TEST-8) → đưa vào handoff T11 (cùng file `test_tasks.py`) như việc tùy chọn; minor (b) → qa.
