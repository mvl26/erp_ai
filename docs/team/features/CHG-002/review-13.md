Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 13 — CHG-002 T13

- Diff: `git diff bf9fd9f..b9ce1d1` (nhánh `team/CHG-002-task-12`, 1 commit, 2 file)
- Gói: T12 + T13 cùng nhánh, một reviewer chấm cả gói; verdict của T12 ở `review-12.md`
- Vòng: 1 (max_rework = 3)
- Verdict: **approve** → merge `0444d89` (cùng T12), tick

## Vòng 1 — approve

Phát hiện blocker/major: không. Minor: gộp ở `review-12.md` mục deferred.

Lớp 1 (AC-43 trần, AC-46 a): đạt.
- `BLOCK_TOO_LARGE` dựng đúng công thức A-1.3.
- Tổng byte: trước + sau trên mọi mục (thiếu tính 0), đổi tên tính hai lần, cộng `diff_text`; phép so `>` nên đúng bằng trần thì nhận.
- Trần mỗi file chỉ qua `text_refusal`; `change_guard.py` không nhập `TEXT_MAX_BYTES`.
- `compile(after, rel, "exec", dont_inherit=True)` cho đích `.py`, `json.loads` cho đích `.json`, cho Sửa, Tạo, đích Đổi tên; `RecursionError` và `MemoryError` cho dòng 0.
- Đủ 7 test của Expect, mỗi test ở cả hai thời điểm.

Đột biến trong đầu của reviewer: đếm ký tự thay byte (`é`), đếm đổi tên một lần, không đếm `before` của mục xóa, không cộng `diff_text`, biên ±1, compile `before` hoặc tên nguồn đổi tên, bỏ `dont_inherit`, bỏ `except RecursionError`, bỏ kiểm trần file trước tổng khối, kiểm cú pháp trước `text_refusal` → đều có test đỏ.

Review checklist (10): 10/10 đạt (mục "test viết trước" chấm sau khi có bằng chứng, xem dưới).

## Không kiểm được từ diff (tech-lead đã xử lý)

- RED/GREEN (dev lần gọi 1 hết 60 lượt, không báo cáo): dev lần gọi 2 tái tạo, 0 commit. RED (mã `bf9fd9f` + test của `b9ce1d1`): `AttributeError: … no attribute 'BLOCK_TOO_LARGE'`; `FAIL: test_py_syntax_error_refused_with_line (ops=[('Tạo', 'myapp/bad.py', None)], at_apply=False)` → `AssertionError: None != 'mục 1 (myapp/bad.py): file .py không biên dịch được: dòng 2'`; `FAIL: test_json_invalid_refused_with_line …` → `None != 'mục 1 (myapp/a.json): file .json không phải JSON hợp lệ: dòng 3'`; `FAIL: test_total_counts_diff_bytes (at_apply=False)` → `None != 'tổng nội dung của khối (kể cả diff) lớn hơn 8 MiB'`; `Ran 74 tests in 4.968s` / `FAILED (failures=62, errors=2)`. GREEN (`b9ce1d1`): `test_change_guard` `Ran 74 tests in 5.034s` / `OK`, `test_propose_change` `Ran 33 tests in 23.939s` / `OK`, `test_apply_block` `Ran 1 test in 1.275s` / `OK`, `test_apply_job` `Ran 117 tests in 138.734s` / `OK`, `test_architecture` `Ran 185 tests in 15.045s` / `OK`.
- Lint: `pre-commit run --files` trên hai file thoát 0.
- Python 3.10 của CI: ca `"-" * 100000` trông đợi `MemoryError` ("Parser stack overflowed"); máy bench là 3.12.3, bản 3.10 trước 3.10.2 có thể sập tiến trình. CHƯA xử lý được trên máy này (không có 3.10): ghi thành điểm mở cho T51 / CI trong báo cáo lượt 4, không chặn merge (test xanh trên máy bench, `cmd.test` cả app đúng baseline).
- Module và cả app sau merge: dòng progress của T13 trong `tasks.md` (đợt merge 12, `0444d89`).

## deferred

Xem `review-12.md` (5 điểm của cả gói).
