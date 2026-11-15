Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 22 — CHG-002 T22

- Diff: `git diff c2af4d7..6ca001d` (nhánh `team/CHG-002-task-22`, 1 commit, 2 file, +218/−8)
- Vòng: 1 (max_rework = 3)
- Verdict: **approve** → merge `a6502a0`, tick
- Lần gọi reviewer đầu (round 25) hết 25 lượt, không trả verdict; không tính là một vòng. Verdict dưới đây là của lần gọi lại (round 26).

## Vòng 1 — approve

Phát hiện blocker/major: không.

minor | — | — | 2 điểm nhỏ (xem deferred) | tùy dev

Lớp 1 (khớp đặc tả): đủ mọi tiêu chí của T22, chỉ hai file touchpoint.
- `CONTENT_FIELDS` thêm `command_list` (`erp_ai_change_proposal.py:34`).
- `validate` so dòng con (số dòng, thứ tự theo `idx`, 7 trường) với `get_doc_before_save()`, dùng lại câu có sẵn kèm `: operations` (`:103-104`).
- `_set_commit_message` của khối dùng `block_label` và `operations=` (`:119-126`).
- P-5 đúng từng chữ: chỉ bắt `ValueError`, dòng cảnh báo đúng, `frappe.logger("erp_ai").warning("erp_ai notes proposal=%s error=%s", self.name, type(exc).__name__)` (`:77-84`).
- Ba ca thêm của dev được nhận: `renumber_rows` (tráo `idx`, thứ tự danh sách không đổi), ca `TypeError` (đỏ nếu nới `except` thành `Exception`), `test_block_unchanged_resave_is_allowed`.

Bằng chứng của dev: RED `Ran 31 tests in 21.918s` / `FAILED (failures=13, errors=2)` (ví dụ `test_child_rows_immutable_after_insert (fieldname='operation'…'after_hash') → AssertionError: ValidationError not raised`, `test_block_commit_preview_lists_items → '…(myapp/myapp/a.py)…' != '…(2 file)…'`, `ValueError: restart_status không hỗ trợ: 'Không rõ'`); GREEN `test_erp_ai_change_proposal` `Ran 31 tests in 20.421s` / `OK`, `test_apply_block` `Ran 1 test in 1.235s` / `OK`, `test_apply_job` `Ran 117 tests in 139.692s` / `OK`, `test_propose_change` `Ran 32 tests in 24.380s` / `OK`, `test_change_decision` `Ran 10 tests in 9.303s` / `OK`, `test_architecture` `Ran 181 tests in 14.383s` / `OK`; L-1: 0.

Review checklist (10): 10/10 đạt.

## Không kiểm được từ diff (tech-lead đã xử lý)

- `_operation_rows(self.get_doc_before_save())` (`:103`) ném `AttributeError` nếu `validate` chạy ngoài `save()` trên đề xuất đã có: `git grep -nE 'run_method\("validate"\)|\.validate\(\)' -- erp_ai` trên `team/CHG-002` @ `990d7b3`, bỏ file test, in 0 dòng → không có nơi gọi nào như vậy trong mã sản phẩm.
- `make_block_proposal([], commands)` lưu loại khác `CHANGE_KIND_CODE`: `erp_ai/test_utils.py:691` đặt `CHANGE_KIND_COMMAND` cho khối chỉ có lệnh (T2).
- Ca `restart_status` hỏng ném trong `proposal_notes`: dòng RED của dev mang đúng thông điệp của T21 (`restart_status không hỗ trợ: 'Không rõ'`).
- Module sau merge trên `team/CHG-002` @ `990d7b3` (một lần giữ khóa 09:57–09:59, `cmd.migrate` thoát 0): `test_erp_ai_change_proposal` `Ran 31 tests in 20.379s` / `OK`, `test_apply_block` `Ran 1 test in 1.168s` / `OK`, `test_change_decision` `Ran 10 tests in 8.653s` / `OK`, `test_propose_change` `Ran 32 tests in 22.553s` / `OK`, `test_architecture` `Ran 184 tests in 14.289s` / `OK`.
- Cả app sau merge (đợt 10, `990d7b3`, một lần giữ khóa 10:02–10:11 gồm `cmd.migrate` thoát 0): `Ran 1704 tests in 516.395s` / `FAILED (failures=6)`, đúng 6 test của dòng `baseline:`.
- Lint: dev báo `pre-commit run --files` trên 2 file thoát 0; `cmd.lint` cả cây chạy ở T51.

## deferred

1. `test_erp_ai_change_proposal.py:476`: các ca 7 trường chỉ sửa `operations[0]`; một phép so chỉ "số dòng + dòng đầu" vẫn qua mọi test. Thêm một ca sửa trường ở dòng thứ hai.
2. `test_erp_ai_change_proposal.py:572`: `assertIn(call("erp_ai"), logger.call_args_list)` vá `frappe.logger` cho mọi tên; `logger.assert_called_once_with("erp_ai")` ghim chặt hơn.
