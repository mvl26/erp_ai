Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 12 — CHG-002 T12

- Diff: `git diff 349560d..bf9fd9f` (nhánh `team/CHG-002-task-12`, 1 commit, 2 file)
- Gói: T12 + T13 cùng nhánh, một reviewer chấm cả gói; verdict của T13 ở `review-13.md`
- Vòng: 1 (max_rework = 3)
- Verdict: **approve** → merge `0444d89` (cùng T13), tick

## Vòng 1 — approve

Phát hiện blocker/major: không.

minor | — | — | 5 điểm nhỏ của cả gói (xem deferred) | tùy dev

Lớp 1 (AC-36, AC-39, D-9): đạt, đúng hai file touchpoint.
- Đủ `BlockCheck`, `OpTarget`, chữ ký `check_block`; `diff_text` chỉ nhận theo từ khóa, không có mặc định.
- Đủ 9 hằng, câu chữ khớp bảng §3.1.
- Thứ tự §3.2 bước 1–2: rỗng → số mục → số lệnh; từng mục: hình dạng → trùng/lồng → `check_write_path(read_git=not at_apply)` → từng `new_dirs` qua `check_write_path(rel, new_file=True, read_git=False)` → cùng app với mục 1. Tiền tố `mục {n} ({path}): ` đúng.
- Đủ 10 test của Expect, mỗi test ở cả hai thời điểm. Phần của T14 (luật lệnh/restart, `OP_FIELDS` cho đường dẫn rỗng) không bị lấn. Không sửa test cũ nào (L-2 không áp dụng).
- Mã mới không dùng `commonpath` / `is_relative_to`, không nhập `agent/changes`.

Đột biến trong đầu của reviewer: `>` thành `>=` ở hai phép đếm, đổi thứ tự đếm và kiểm mục, đảo tên app trong `BLOCK_TWO_APPS`, bỏ kiểm đích đổi tên khác app, bỏ `normpath`, tiền tố chung bị coi là lồng (`pkg` / `pkg2`), bỏ `read_git` → đều có test đỏ; vòng kiểm `new_dirs` được ghim bởi `test_each_new_dir_checked_on_its_own`.

Review checklist (10): 10/10 đạt (mục "test viết trước" chấm sau khi có bằng chứng, xem dưới).

## Không kiểm được từ diff (tech-lead đã xử lý)

- RED/GREEN (dev lần gọi 1 hết 60 lượt, không báo cáo): dev lần gọi 2 tái tạo, 0 commit. RED (mã `349560d` + test của `bf9fd9f`): 87 lỗi `AttributeError: module 'erp_ai.agent.tools.change_guard' has no attribute 'check_block'`, 1 lỗi `… no attribute 'BLOCK_TOO_MANY_OPS'`, `Ran 65 tests in 1.468s` / `FAILED (errors=88)`. GREEN (`bf9fd9f`): `test_change_guard` `Ran 65 tests in 3.159s` / `OK`, `test_propose_change` `Ran 33 tests in 26.071s` / `OK`, `test_apply_block` `Ran 1 test in 1.283s` / `OK`, `test_architecture` `Ran 185 tests in 15.191s` / `OK`.
- Lint (dòng `BLOCK_TOO_LARGE` ~110 ký tự): `pre-commit run --files` trên hai file thoát 0, ruff linter và formatter `Passed`.
- Thư mục cha đã tồn tại nhưng là file (`myapp/README.md/x.py`): `_new_dirs` dừng ở `lexists`, lỗi chỉ hiện lúc ghi; đưa vào lệnh giao T27 (bước "đã tồn tại" của tool, §4.1 bước 2) để có ca test.
- Module và cả app sau merge: dòng progress của T12 trong `tasks.md` (đợt merge 12, `0444d89`).

## deferred

1. Thiếu test ghim `diff_text` bắt buộc và chỉ nhận theo từ khóa (`change_guard.py:417`, STD-TEST-2).
2. `_syntax_reason` nhánh `.json` không bắt `MemoryError` (`change_guard.py:356`; design chỉ nêu `ValueError` cho JSON).
3. `zip(paths, new_files, strict=False)` khó đọc (`change_guard.py:391`).
4. Chưa ghim thứ tự giữa số mục và số lệnh (51 mục + 7 lệnh), và hai-app trước nội dung.
5. `assertIn("2 MiB", TEXT_TOO_LARGE_REFUSAL)` ở `test_change_guard.py:1621` chỉ kiểm hằng của chính test.
