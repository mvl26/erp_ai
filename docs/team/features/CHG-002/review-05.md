Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 05 — CHG-002 T5

- Diff: vòng 1 `git diff fd69e5f..8a21623`; vòng 2 (sửa) `git diff 8a21623..e5f7109` (nhánh `team/CHG-002-task-5`, còn giữ)
- Vòng: 2 (max_rework = 3)
- Verdict của reviewer: vòng 1 request-changes; vòng 2 approve
- Trạng thái task: **CHƯA merge, DỪNG** (xem "Sau review"): mã đúng thiết kế nhưng một luật kiến trúc có sẵn đỏ vì tên hàm thiết kế bắt buộc.

## Vòng 1 — request-changes
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-8 | erp_ai/agent/changes/file_writer.py:45 | Phép kiểm "file nằm ngoài app_dir" không có test và không gì khác chặn: bỏ phép kiểm thì `make_parents(root/other/x/new.py, root/myapp)` tạo `apps/other`, `apps/other/x`, cả 9 test vẫn xanh | Thêm ca `TestMakeParents` với file ở app bên cạnh (hoặc ngay dưới `apps/`): `ValueError`, không gì được tạo dưới `self.apps.root` |
| major | STD-TEST-8 | erp_ai/agent/changes/file_writer.py:57,61 | Nhánh `islink(current)` sau `mkdir` không có test và phần trả lại hỏng: `os.rmdir` lên symlink ném `NotADirectoryError`, thư mục tạo trước đó còn lại, lỗi không phải `ValueError` như A-3.1 | Trả lại bằng `os.unlink` cho symlink; thêm ca patch `file_writer.os.mkdir` để tầng hai thành symlink ra `self.apps.outside`: `ValueError`, tầng một đã gỡ, `outside` chỉ còn `["plain.py"]` |

minor | — | — | 5 điểm nhỏ (xem deferred) | tùy dev

## Vòng 2 — scoped re-review (`8a21623..e5f7109`), approve
- Phát hiện 1: ADDRESSED. `test_file_writer.py:207-214` `test_file_outside_app_dir_raises` (hai ca: `other/x`, `loose`); bỏ phép kiểm ở `:45` thì đỏ `ValueError not raised` (đầu ra của dev khớp phép dò của reviewer).
- Phát hiện 2: ADDRESSED. `file_writer.py:59-65` trả lại bằng `os.unlink` cho symlink, `os.rmdir` cho thư mục; `test_file_writer.py:216-231` `test_level_turned_symlink_after_mkdir_rolls_back`; RED trước khi sửa `NotADirectoryError: [Errno 20] Not a directory: '…/apps/myapp/a/b'`; GREEN `Ran 21 tests in 0.101s` / `OK`.
- Blocker/major mới từ diff sửa: không.

## Review checklist (10), sau vòng 2
1. Đạt. Ba hàm đúng A-3.1; `write_atomic`, `_refuse_git_dir`, `remove_created` chưa đụng (T6).
2. Đạt. Đúng 2 file touchpoint.
3. Đạt sau vòng 2 (vòng 1 trượt vì hai nhánh ném lỗi không có test).
4. Đạt. Mọi test trên `TempAppsRoot`.
5. Đạt sau vòng 2 (phần trả lại ném lại lỗi gốc).
6. Đạt.
7. Đạt. Chỉ thêm hàm.
8. Đạt, kèm minor.
9. Đạt.
10. Đạt. `feat(changes): …`, `fix(changes): … (CHG-002)`, không dòng AI.

## Sau review — đỏ sau merge, tech-lead dừng task
- Merge thử `b69a702` rồi chạy module của đợt trên `team/CHG-002`: `erp_ai.tests.test_architecture` `Ran 179 tests in 14.403s` / `FAILED (failures=1)`: `FAIL: test_change_guard_uses_resolve_safe_path … 'agent/changes/file_writer.py:24: _refuse_unsafe_path() is a second path resolver (ADR-011)'`.
- Nguyên nhân là task, không phải merge: luật ADR-011 ("ngoài `source.py` không hàm nào mang tên giống `resolve_safe_path`, không mã nào kiểm gốc") bắt đúng hàm `_refuse_unsafe_path` mà `design-addendum-1.md` A-3.1 bắt buộc (tên và ba phép kiểm). Dev và reviewer không chạy module kiến trúc vì file đó ngoài touchpoint và lúc đó nhiều dev dùng chung site.
- Đã lấy merge của T5 ra khỏi `team/CHG-002` (nhánh chưa đẩy đi đâu; `git reset --hard f46ebf2` rồi merge lại T15, T19; hai commit của T5 còn nguyên trên `team/CHG-002-task-5`).
- Tính là review trượt (bước 9 của skill build: thiếu sót thật). Tech-lead không tự đổi tên hàm hay sửa luật: đây là xung đột giữa addendum-1 A-3.1 và luật của ADR-011 → báo team-leader (designer/architect phán: đổi tên hàm và cách kiểm, hoặc thêm ngoại lệ có tên vào luật).

## Không kiểm được từ diff
- Câu hỏi thiết kế của reviewer (vòng 1): A-3.1 kiểm **sau** `mkdir`, nên với một thành phần là symlink `make_parents` tạo thư mục bên ngoài gốc apps rồi mới gỡ; kiểm `realpath(current) == current` trên phần đã tồn tại **trước** `mkdir` thì không chạm gì bên ngoài → chuyển designer cùng điểm trên.
- design.md dòng 499 gọi `make_parents(dst)` một tham số; plan "Shared constraints" và T5 dùng hai tham số `(full_path, app_dir)` → T35 theo plan.

## deferred
1. `islink(app)` ở `file_writer.py:42` chưa có ca.
2. `test_keeps_nonempty_and_preexisting` có `isdir(preexisting)` luôn đúng (`test_file_writer.py:227`).
3. STD-STYLE-4: `APP_DIR_BEFORE` chen giữa hai hằng `VIETNAMESE_CRLF_*`.
4. STD-DOC-7: docstring `make_parents` chưa nói `ValueError` và phần trả lại.
5. Phần trả lại tự lỗi (`rmdir`/`unlink` ném) thì lỗi đó che `ValueError` gốc; A-3.1 không nói ca này.
