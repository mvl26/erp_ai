Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 05 — CHG-002 T5

- Diff: vòng 1 `git diff fd69e5f..8a21623`; vòng 2 (sửa) `git diff 8a21623..e5f7109` (nhánh `team/CHG-002-task-5`, còn giữ)
- Diff lượt 3 (đề bài mới theo `arch-ruling-2.md`, ADR-040 C-2): vòng 3 `git diff a6a6560..22fee8c` (cả task sau khi dev merge `team/CHG-002` vào nhánh, 3 file, +417/−0); vòng 4 (sửa) `git diff 22fee8c..4fc0217` (2 file, +79)
- Vòng: 4 lần review; theo quyết định 07:31 của team-leader bộ đếm vòng sửa của đề bài mới tính lại từ 0: đề bài cũ 2 vòng, đề bài mới 2 vòng (1 vòng sửa, max_rework = 3)
- Verdict của reviewer: vòng 1 request-changes; vòng 2 approve; vòng 3 request-changes; vòng 4 **approve**
- Trạng thái task: lượt 2 **DỪNG** sau vòng 2 (xem "Sau review"); lượt 3 merge `2e2b9ad`, **đã tick** (xem "Lượt 3" cuối file).

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

## Lượt 3 — đề bài mới theo `arch-ruling-2.md` (ADR-040 C-2)

### Vòng 3 — request-changes (`git diff a6a6560..22fee8c`)

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-8 | erp_ai/agent/changes/test_file_writer.py:261-271 (mã ở file_writer.py:27) | C-2 chỉ nhận đường dẫn khi bộ phân giải trả **đúng** `abspath` của nó; mọi ca symlink trong test đều trỏ ra `outside/`, nơi `resolve_safe_path` đã trả `None`, nên đổi `!= full` thành `is None` thì mọi test vẫn xanh và `make_parents` tạo thư mục qua symlink nằm trong gốc | Thêm symlink trong gốc (`myapp/inner_link -> myapp/`): `ValueError` cho `inner_link/x.py`, `inner_link/pkg/new.py`; ca `make_parents(myapp/inner_link/pkg/new.py)`: `ValueError`, 0 lời gọi `mkdir`, thư mục đích không đổi |
| major | STD-TEST-8 | erp_ai/agent/changes/file_writer.py:52-54 (test ở test_file_writer.py:232) | Hai phép kiểm sau `mkdir` che nhau: bỏ một trong hai thì mọi test vẫn xanh. Nhánh `islink` tới được (symlink tự trỏ: `realpath` của Python 3.12 trả nguyên đường dẫn) | Mỗi phép kiểm một ca: (a) symlink tự trỏ ở tầng 2, chỉ `islink` bắt; (b) tầng 1 đã tạo bị tráo thành symlink ra `outside` rồi mới tạo tầng 2, chỉ phép kiểm chuẩn bắt |

minor | — | — | 4 điểm nhỏ (xem deferred lượt 3) | tùy dev

Lớp 1: `_refuse_unless_canonical` đúng thân của phán quyết; `make_parents` kiểm trước và sau `mkdir`; `remove_empty_dirs` bỏ phép so `realpath`; `file_writer.py` không còn `realpath`, `commonpath`, `is_relative_to`, `readlink`; luật ADR-011 không đổi (diff của `test_architecture.py` 0 dòng xóa); chỉ ba file touchpoint. Lo ngại của dev về `patch` và ba hằng phụ ở `test_architecture.py`: reviewer nhận, không phải lỗi (cờ `FILE_WRITER_RECHECKS_ALL = False` chỉ có nghĩa khi điều kiện 4 đã viết và có test).

Bằng chứng của dev: RED `FAIL: test_symlinked_ancestor_refused_before_mkdir ... Lists differ: ['/tmp/tmph8mhslhd/apps/myapp/dir_out/pkg'] != []`, `AttributeError: … no attribute '_refuse_unless_canonical'` (`Ran 24 tests` / `FAILED (failures=1, errors=13)`); `test_architecture` `Ran 181 tests` / `FAILED (failures=11)`; GREEN `test_file_writer` `Ran 24 tests in 0.071s` / `OK`, `test_architecture` `Ran 181 tests in 14.452s` / `OK`.

### Vòng 4 — scoped re-review (`22fee8c..4fc0217`), approve

- Phát hiện 1: ADDRESSED. `test_symlink_inside_root_refused`, `test_symlink_inside_root_refused_before_mkdir`, `test_dir_under_symlink_inside_root_skipped`; đột biến `!= full` → `is None`: `FAILED (failures=5)`.
- Phát hiện 2: ADDRESSED. (a) `test_level_turned_self_loop_symlink_after_mkdir_rolls_back` (bỏ `islink`: `failures=1`); (b) `test_created_level_swapped_for_symlink_before_next_mkdir_rolls_back` (bỏ phép kiểm chuẩn thứ hai: `failures=1`).
- Chỉ sửa test; `file_writer.py` không đổi so với `22fee8c`. Hai ca tự kiểm thêm ở `test_architecture.py` (thân chỉ gọi `source.get_source_root()`; `remove_empty_dirs` thiếu phép kiểm lại): reviewer nhận.
- Blocker/major mới từ diff sửa: không.
- GREEN sau sửa: `test_file_writer` `Ran 29 tests` / `OK`, `test_architecture` `Ran 181 tests` / `OK`.
- Review checklist (10): 10/10 đạt.

### Không kiểm được từ diff (tech-lead đã xử lý hoặc chuyển tiếp)

- Module sau merge trên `team/CHG-002` @ `2e2b9ad` (08:36): `test_file_writer` `Ran 29 tests in 0.085s` / `OK`, `test_architecture` `Ran 181 tests in 14.383s` / `OK` (gồm `test_change_guard_uses_resolve_safe_path`, test đã đỏ ở lượt 2).
- Cả app sau merge (đợt 7, `2e2b9ad`, một lần giữ khóa 08:37–08:46 gồm `cmd.migrate` thoát 0): `Ran 1666 tests in 508.667s` / `FAILED (failures=6)`, đúng 6 test của dòng `baseline:`.
- Bố cục bench: nơi gọi phải truyền `full_path` dạng `realpath` (kết quả của `check_write_path`) → ghi vào lệnh giao T6 và T35.
- Xung đột văn bản với T23 ở `test_architecture.py`: T23 làm sau khi T5 merge, dev T23 merge `team/CHG-002` @ `2e2b9ad` vào nhánh trước khi sửa.

### deferred (lượt 3)

6. Phần trả lại tự lỗi vẫn che `ValueError` gốc (điểm 5 ở trên, còn mở).
7. Commit merge `d0ff3e5` trên nhánh task dùng thông điệp mặc định của git.
8. Trong test symlink tự trỏ, `assertEqual(os.listdir(self.apps.outside), ["plain.py"])` không bao giờ đỏ được; hai test dùng `assertRaises(ValueError)` không so thông điệp.
9. Cho T6: ca tự kiểm `rename_file` đã có ở T5; T6 đặt cờ `True`, bỏ lớp `patch` và các assert trạng thái `False`.
