Feature: FEAT-005
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 02 — FEAT-005 T2

Tech-lead chép từ tin trả về của reviewer (reviewer không ghi file).

- Diff: `git diff 4e6ddf1..1ca7e1c` (nhánh `team/FEAT-005-task-2`, 2 commit: `0c0a9e7`, `1ca7e1c`; merge `568daa5`)
- Vòng: 2
- Verdict: approve (vòng 2)

## Vòng 1 — request-changes (`4e6ddf1..0c0a9e7`)

Lớp 1 (khớp spec): mọi ý của Returns có trong mã, chỉ hai file touchpoint. Tạo: `before=None`, `after` đúng khóa của `values`, không cắt. Sửa: `before` chụp trước `doc.update`. Xóa: mọi trường có giá trị kể cả dòng con và `creation`, `after=None`. Submit/hủy: `docstatus` hai đầu. Từ chối/lỗi (4 kiểm trước, `validate` ném, `TypeError`): không có `_snapshot`; `call_method` không có. Sáu test có sẵn bị sửa (so qua `_without_snapshot(result)`): đạt STD-TEST-5, giá trị kỳ vọng `value_before`/`value_after` không đổi, hợp đồng đổi theo design §3.1.

- major | STD-TEST-2 | erp_ai/agent/tools/site_api.py:269 (`_snapshot_fields`), test_site_api.py:975 | Không test nào phủ ý "tạo/sửa = khóa của `values` ∪ `SNAPSHOT_TABLES.get(doctype, ())`": đổi `_snapshot_fields` thành `tuple(values)`, hoặc truyền `written` (có giá trị ép) thay `values`, mọi test vẫn xanh | Thêm test `patch.dict(site_api.SNAPSHOT_TABLES, {"Note": ("seen_by",)})` khẳng định `seen_by` có ở `before` và `after`; thêm ca tạo trên DocType có `FORCED_VALUES` khẳng định khóa ảnh chụp đúng bằng `name` + khóa của `values`
- minor | — | — | 3 điểm nhỏ: docstring `_without_snapshot` nhắc việc runner bỏ `_snapshot` (đến T3 mới có); `delete()` lặp phép lọc "trường có giá trị" của `_deleted_values`; "`after` sau `save()`" chưa tách khỏi "sau `doc.update`" | tùy dev

Bằng chứng của dev: RED `KeyError: '_snapshot'`, `'_snapshot' not found in {'ok': True, …}`, `Ran 64 tests` / `FAILED (failures=1, errors=1)`; GREEN `Ran 64 tests in 49.682s` / `OK`.

## Vòng 2 — approve (`0c0a9e7..1ca7e1c`, re-review theo phạm vi)

- major STD-TEST-2: ADDRESSED (`test_site_api.py:556` `test_update_snapshot_holds_the_doctype_tables_and_the_saved_values`; `:531` `test_snapshot_keys_are_the_given_values_not_the_forced_ones` trên Webhook)
- minor 1: ADDRESSED (`test_site_api.py:75`)
- minor 2: ADDRESSED (`_filled_fields` ở `site_api.py:199`, hai nơi gọi giữ cờ `as_dict` riêng)
- minor 3: ADDRESSED (`test_site_api.py:566-579`: `Note.validate` giả đổi `content` trong `save()`)
- Phát hiện mới: không có. Minor: không có.

Bằng chứng của dev (đột biến): `_snapshot_fields` → `tuple(values)` → `FAIL: test_update_snapshot_holds_…`, `failures=1`; `written` thay `values` → `FAIL: test_snapshot_keys_are_the_given_values_not_the_forced_ones`; `after` trước `save()` → `'TEST model gửi' … != … 'TEST đã chuẩn hóa'`; trả lại → `Ran 66 tests in 36.326s OK`.

## Không kiểm được từ diff (tech-lead xử lý)

- Tới khi T3 merge, `runner._run_tool` (`runner.py:699`) vẫn `json.dumps(outcome)` nguyên vào `tool_result`: ảnh chụp đầy đủ tới ngữ cảnh model trên `team/FEAT-005`. Phán: không chặn tick T2 (T3 là task kế trong chuỗi, có test `test_snapshot_never_reaches_model`); `team/FEAT-005` KHÔNG được merge vào `develop` trước khi T3 tick.
- Sau merge `568daa5`, tech-lead chạy trên `team/FEAT-005`: test_site_api `Ran 66 tests in 41.433s` / `OK`; test_agent_runner (T2 không sửa runner) ba lượt: lượt 1 nhiều `ERROR` và lượt 2 `Ran 78 tests` / `FAILED (errors=1)` đều `QueryDeadlockError (1213)` do phiên khác trên cùng site; lượt 3 `Ran 78 tests in 18.609s` / `FAILED (failures=3)`, đúng ba ca nhiễu cài đặt đã ghi ở dòng `baseline:` (`test_l1_all_fields_skipped_reasons_logged_saves_ai_fields_applied_one`, `test_l1_applies_mapping_confidence_and_hint`, `test_l1_empty_route_still_saves_ai_fields_applied_one`, đỏ khi `auto_assign_enabled=1` lưu trên site). Không ca nào thuộc T2. `cmd.test` cả app với cài đặt tạm để trống chạy ở T16.

## deferred

Không có.
