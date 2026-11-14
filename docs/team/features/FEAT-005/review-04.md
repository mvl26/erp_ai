Feature: FEAT-005
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 04 — FEAT-005 T4

Tech-lead chép từ tin trả về của reviewer (reviewer không ghi file).

- Diff: `git diff e12e65d..61d6b97` (nhánh `team/FEAT-005-task-4`, 1 commit, chỉ `erp_ai/agent/test_agent_runner.py` +159; merge `9add0dc`)
- Vòng: 1
- Verdict: approve

## Vòng 1 — approve

Lớp 1 (khớp spec): đạt. Ba tên test khớp tasks.md T4 và design-amd2 §8. Ca kiểm (2), AC-13 (a)(b): before/after ghim nguyên `[gỡ, giữ]` và `[giữ, thêm]`, role giữ không nằm trong hiệu, kiểm cả dòng Has Role trong DB. Ca (3): Holiday List trước/sau ghim nguyên, hiệu `([thiếu], [mới])`. Ca (4), AC-13 (c), NFR-3: 30.000 ký tự > `TOOL_RESULT_MAX_CHARS`, so từng byte cả trước và sau, kiểm giá trị DB.

Task chỉ thêm test nên bằng chứng đỏ là ba đột biến tạm trên mã sản phẩm (đã trả lại): `before = after` → `test_update_user_role_list_diff_shows_removed_and_added` FAIL; `_snapshot` bỏ dòng con → `test_holiday_list_missing_old_date_seen_in_diff` FAIL (`holidays: []`); cắt 20.000 ký tự → `test_30000_char_field_stored_byte_identical` FAIL. GREEN `--case TestRunnerRecordSnapshots` `Ran 9 tests` / `OK`.

Không để lại dòng: `RunnerTestBase.setUp` có `addCleanup(frappe.db.rollback)` và chặn `frappe.db.commit`.

- Phát hiện blocker/major: không có.
- minor | — | — | 2 điểm nhỏ: test 30.000 ký tự kiểm cùng một điều ba lần; các phép kiểm `row_diff` không thêm gì khi before/after đã ghim nguyên (vẫn có giá trị làm tài liệu cho ý (b)) | tùy dev

## Không kiểm được từ diff (tech-lead xử lý)

- "Giống từng byte" của AC-13 ca (4): test so giá trị sau khi giải JSON, không so byte thô của cột (cột lưu JSON có thể escape). Phán: không chặn tick (design-amd2 §2 nói "giá trị … không cắt"); chuyển qa xác nhận cách đọc ca (4) ở verify.
- Trường con của `Holiday List` ghim đúng `holiday_date`, `description`, `weekly_off`: đúng trên site `miyano` (test xanh); site khác có Custom Field trên bảng con sẽ đỏ. Ghi vào rủi ro cho As-Built.
- Sau merge `9add0dc`, tech-lead chạy `cmd.test_one` test_agent_runner: `Ran 87 tests in 46.266s` / `FAILED (failures=3, errors=4)` = 3 ca nhiễu cài đặt của dòng `baseline:` + 4 `QueryDeadlockError` ở `TestRunnerReasoning` (phiên khác trên cùng site); lượt cả module của dev trên cùng mã: `Ran 87 tests` / `FAILED (failures=3)`.

## deferred

Không có.
