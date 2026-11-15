Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 52 — CHG-002 T52

- Diff: vòng 1 `git diff a6a6560..c97fbda` (2 file, +100/−17); vòng 2 (sửa) `git diff c97fbda..6c78fdf` (2 file, +24/−3); nhánh `team/CHG-002-task-52`
- Vòng: 2 (max_rework = 3)
- Verdict: vòng 1 request-changes; vòng 2 **approve** → merge `c2af4d7`, tick
- Task chèn ở build lượt 3 (`design-addendum-5.md` P-3, P-4).

## Vòng 1 — request-changes

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-8 | erp_ai/agent/changes/test_transitions.py:1219 (phép chặn ở erp_ai/agent/changes/transitions.py:365) | Ca `stored=None` của `test_stale_sent_at_writes_nothing` vẫn xanh khi xóa phép chặn `not row.restart_sent_at or`: `get_datetime(None)` trả giờ thật, lớp test chỉ vá `transitions.now_datetime`, nên giờ hôm nay khác `stale` và hàm vẫn trả `False` | Thêm ca lưu `restart_sent_at = None`, vá `frappe.utils.data.now_datetime` trả `SENT_AT`, gọi `confirm_restart(..., sent_at=SENT_AT)`, assert `False` và `assertNothingChanged`; cho thấy đỏ khi bỏ phép chặn |

minor | — | — | 1 điểm nhỏ: `sent_at` không phải ngày giờ (ví dụ int) không ra `ValueError` như docstring | tùy dev

Lớp 1 (khớp đặc tả): P-3 (thứ tự kiểm 1 → 2 → 3) và P-4 (chỉ-từ-khóa, bắt buộc, `ValueError` khi rỗng, một `_lock` đọc thêm `restart_sent_at`, so bằng `get_datetime`) đúng thiết kế; đủ ba test của addendum-5; 4 dòng `test-shape:` khớp 4 test chỉ thêm đối số `sent_at=`; `finish`, `log_step` (hứa với FEAT-007, A3 RQ-2) không đổi.

Phần thêm ngoài chữ của P-4 (`restart_sent_at` đã lưu rỗng → `False`): reviewer nhận, không phải mở rộng phạm vi (đọc sát chữ P-4 thì `get_datetime(None)` = "bây giờ" có thể trùng `sent_at`). Tech-lead ghi vào journal như một chỗ siết có chủ ý của P-4.

Bằng chứng của dev: RED `FAIL: test_request_undo_refused_for_other_kind_when_applied … InvalidTransition not raised`, `TypeError: confirm_restart() got an unexpected keyword argument 'sent_at'`, `Ran 74 tests` / `FAILED (failures=4, errors=28)`; GREEN `test_transitions` `Ran 74 tests` / `OK`, `test_architecture` `Ran 179 tests` / `OK`, `test_change_decision` `Ran 10 tests` / `OK`, `test_erp_ai_change_proposal` `Ran 25 tests` / `OK`.

## Vòng 2 — scoped re-review (`c97fbda..6c78fdf`), approve

- Phát hiện 1: ADDRESSED. `test_transitions.py:1230` `test_missing_stored_sent_at_writes_nothing_even_when_now_equals_sent_at` (lưu `None`, vá `frappe.utils.data.now_datetime`, hai giá trị kết luận); RED bằng đột biến (bỏ phép chặn): `AssertionError: True is not False` ×2, `Ran 76 tests` / `FAILED (failures=4, errors=1)`; đã trả lại phép chặn.
- Minor dev nhận sửa: `transitions.py:360` `isinstance(sent_at, datetime | str)` nếu không thì `ValueError` (chạy được trên Python 3.10); test `test_non_date_sent_at_raises_value_error` (int, float, list) đỏ trước.
- Blocker/major mới từ diff sửa: không.
- GREEN sau sửa: `test_transitions` `Ran 76 tests` / `OK`, `test_architecture` `Ran 179 tests` / `OK`.
- Review checklist (10): 10/10 đạt.

## Không kiểm được từ diff (tech-lead đã xử lý hoặc chuyển tiếp)

- Cả app sau merge (đợt 8, `team/CHG-002` @ `c2af4d7`, 09:00–09:09): `Ran 1683 tests in 528.543s` / `FAILED (failures=6)`, đúng 6 test của dòng `baseline:`.
- T24 (chưa làm): controller phải truyền nguyên `restart_sent_at` đã đọc (`datetime` hoặc `str`) vào `sent_at=`; đã có trong dòng "Thêm theo addendum-5 P-4" của T24.
- FEAT-007: P-3 nay từ chối mọi loại khác `Thay đổi code` ở cả cạnh `Đã áp dụng`; phiên FEAT-007 phải chèn nhánh của họ trước bước 2 khi hai nhánh gặp nhau (addendum-5 P-3) → báo team-leader.
- Lint: dev báo `pre-commit run --files` trên 2 file qua mọi hook; `cmd.lint` cả cây chạy ở T51.

## deferred

1. Commit `6c78fdf` mang loại `test(...)` nhưng có sửa mã chạy ở `transitions.py:360` (`fix` đúng hơn).
2. Chuỗi không phải ngày giờ (ví dụ `"garbage"`) vẫn qua phép kiểm kiểu, phụ thuộc `get_datetime`.
