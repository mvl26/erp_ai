Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 10 — CHG-002 T10

- Diff: vòng 1 `git diff 5f418c1..a75fa84` (2 file, +171/−4); vòng 2 (sửa) `git diff a75fa84..ef028c7` (2 file, +15/−5); nhánh `team/CHG-002-task-10`
- Vòng: 2 (max_rework = 3)
- Verdict: vòng 1 request-changes; vòng 2 **approve** → merge `50c5f80`, tick

## Vòng 1 — request-changes

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-ERR-2 | erp_ai/agent/tools/change_guard.py:216-220 | Symlink rồi `..` lọt cả hai bước mới: bước 6 chạy trên `os.path.normpath(join(root, rel_path))`, phép này bỏ `link/..` như chữ, còn `realpath` đi theo symlink trước rồi mới áp `..`. Ca cụ thể: `myapp/deep_link -> myapp/vendor/lib/deep`, đích `myapp/deep_link/../x.py` → `reason=None`, `full_path` nằm trong kho git lồng (trái ADR-040 "repo lồng trong app") | Từ chối `PATH_SYMLINK` khi `os.path.normpath(os.path.join(root, rel_path)) != full`; bước 7 xét trên cùng thư mục với `full`; thêm dòng `link/../x.py` (dạng thường và dạng kho lồng) |

minor | — | — | 1 điểm nhỏ: nhánh "isdir else dirname" của `_is_nested_repo` (`change_guard.py:165`) cho cùng kết quả với việc đi lên thẳng từ phần tồn tại | tùy dev

Lớp 1: bước 6, 7 đúng thứ tự thiết kế; `PATH_SYMLINK`, `NESTED_REPO` đúng chữ §3.1; dùng lại `_common_dirs_upward(nearest_only=True)`; `source.resolve_safe_path` vẫn là bộ phân giải duy nhất (ADR-011); đủ bốn test Expect; một dòng `test-shape:` (`sh_link.py` `None` → `PATH_SYMLINK`, khớp addendum-4 P-1.1); L-1: 1, L-2: 0.

Lo ngại của dev (con trỏ `.git` không đọc được trong thư mục con bị từ chối là `NESTED_REPO` khi app có repo đọc được; ở chính thư mục app thì qua): reviewer không tính là lỗi (thiết kế không nói; cả hai kết cục đều về phía an toàn).

Bằng chứng của dev: RED `Ran 44 tests` / `FAILED (failures=21)` (ví dụ `test_any_text_extension_allowed: AssertionError: None != 'đường dẫn đi qua symlink'`); GREEN `test_change_guard` `Ran 44 tests` / `OK`, `test_propose_change` `Ran 32 tests` / `OK`, `test_apply_job` `Ran 117 tests` / `OK`, `test_apply_block` `Ran 1 test` / `OK`, `test_architecture` `Ran 179 tests` / `OK`.

Ghi chú của tech-lead: design.md:289 viết "`os.path.normpath(join(root, rel_path))` của phần đang tồn tại khác `realpath`"; cách sửa của reviewer vẫn là đúng phép so đó (với `realpath` của đường dẫn gốc), chỉ chặt hơn ở ca `link/..`, nên giao dev sửa, không báo `design-defect`.

## Vòng 2 — scoped re-review (`a75fa84..ef028c7`), approve

- Phát hiện 1: ADDRESSED. Bước 6 (`change_guard.py:219`) từ chối khi `normpath(join(root, rel_path)) != full`; bước 7 (`:221`) xét trên `_existing_part(full)`; dòng mới `test_change_guard.py:520-521` (`myapp/deeper_link/../x.py`, `myapp/sub/deep_link/../x.py`) và `:612` (`myapp/deep_link/../x.py`, dạng kho lồng); RED `AssertionError: None != 'đường dẫn đi qua symlink'`, `Ran 44 tests` / `FAILED (failures=3)`. Không dòng cũ nào đổi (`myapp/sub/../ok.py` vẫn được nhận, symlink treo vẫn bị từ chối).
- Điều dev báo (`myapp/pkg_link/../x.py` với `pkg_link` trỏ xuống đúng một tầng vẫn được nhận): không phải lỗi; design.md:289 cũng nhận, đường dẫn thật trùng đường dẫn chuẩn hóa, mọi bước sau chạy trên chính đường dẫn đó.
- Blocker/major mới từ diff sửa: không.
- GREEN sau sửa: `test_change_guard` `Ran 44` / `OK`, `test_propose_change` `Ran 32` / `OK`, `test_apply_job` `Ran 117` / `OK`, `test_apply_block` `Ran 1` / `OK`, `test_architecture` `Ran 179` / `OK`.
- Review checklist (10): 10/10 đạt.

## Không kiểm được từ diff (tech-lead đã xử lý hoặc chuyển tiếp)

- Module sau merge trên `team/CHG-002` @ `50c5f80` (một lần giữ khóa 09:30–09:33, `cmd.migrate` thoát 0): `test_change_guard` `Ran 44 tests in 0.860s` / `OK`, `test_propose_change` `Ran 32 tests in 24.160s` / `OK`, `test_apply_block` `Ran 1 test in 1.360s` / `OK`, `test_architecture` `Ran 181 tests in 14.274s` / `OK`, `test_apply_job` `Ran 117 tests in 139.242s` / `OK`.
- Cả app sau merge (đợt 9, `50c5f80`, một lần giữ khóa 09:35–09:44 gồm `cmd.migrate` thoát 0): `Ran 1687 tests in 519.426s` / `FAILED (failures=6)`, đúng 6 test của dòng `baseline:`; không module nào khác gọi `check_write_path` đổi lý do.
- Lint: dev báo `pre-commit run --files` trên 2 file qua mọi hook; `cmd.lint` cả cây chạy ở T51.
- Vòng lặp symlink (`myapp/loop.py -> loop.py`): `realpath` không chặt để nguyên, bước 6 cho qua (mã cũ cũng vậy; nghi vấn). Tech-lead: không mở vòng mới cho T10; lớp ghi đã có phép chặn riêng (`remove_file` từ chối `islink`, T6; `make_parents` có ca symlink tự trỏ, T5) → ghi vào lệnh giao T6 (thêm ca `write_atomic` lên đích là symlink tự trỏ) và báo team-leader như một câu hỏi cho designer.

## deferred

1. Docstring `change_guard.py:184` và chú thích test `test_change_guard.py:500` nói "mọi symlink trên phần tồn tại" bị từ chối, trong khi ca `pkg_link` ở trên được nhận.
2. Thân commit `ef028c7` nói `sub/../ok.py` và `missing/../ok.py` vẫn được nhận nhưng diff sửa không thêm dòng nào cho hai ca đó (dòng `sub/../ok.py` đã có từ trước).
3. Con trỏ `.git` không đọc được: chưa có test ghim, thiết kế chưa nói.
4. Vòng lặp symlink ở bước 6 (xem trên).
