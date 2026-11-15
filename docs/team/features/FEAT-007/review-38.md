Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 38 — FEAT-007 T38

- Diff: `git diff a805842d416dd572403e7837d76ead11b8df24e3..team/FEAT-007-task-38` (vòng 1: 1 commit `cdaa40e`, 2 file +150/−4)
- Vòng: 2 (trần `max_rework` = 3); vòng 2: `git diff cdaa40e..45857b1`
- Verdict: approve (vòng 2); merge `7d10d0f` trên `team/FEAT-007` (lượt 8, 2026-11-15)

## Vòng 1 — request-changes

- Lệnh đã dùng (chỉ đọc): `git log --oneline a805842d..team/FEAT-007-task-38`, `git diff --stat …`, `git diff …`; `git show team/FEAT-007-task-38:` cho `erp_ai/agent/tools/source.py`, `erp_ai/test_utils.py`, `erp_ai/agent/tools/change_guard.py`, `erp_ai_setting.py`; `git grep resolve_safe_path|manuals_root|…` ở đầu nhánh; `git -C apps/frappe grep value_cache`.
- Bằng chứng của dev: RED với hàm giả trả `None`, 10 failure (`'/tmp/.../apps/myapp/docs/hdsd.md' is not None`, `Lists differ: ['myapp/code.py', 'myapp/docs/hdsd.md'] != ['myapp/code.py']`, `None != '/tmp/.../apps/myapp/docs/hdsd.md'`, `True is not false`, `Expected 'run' to not have been called. Called 3 times.`); GREEN một lần giữ khóa, migrate exit 0: `test_source` `Ran 119 tests in 7.288s OK`; `test_erp_ai_setting` `Ran 64 tests in 9.838s OK`; `test_architecture` `Ran 112 tests in 5.688s OK`.
- Lớp 1 (khớp spec): tiêu chí đạt. `_base_resolve`, `manuals_root()` (đọc cài đặt bằng `frappe.db.get_single_value`) và `resolve_manual_path` có đủ; `resolve_safe_path` chỉ trả `None` cho **file** trong `manuals_root()` như `design.md:492`; chữ ký `read_source`, `search_source`, `git_source` không đổi; ba test của Expect có đủ; không sửa ngoài touchpoints, không thừa.

### Phát hiện (chỉ blocker/major)

major | STD-TEST-8 | erp_ai/agent/tools/test_source.py:2350 (luật ở source.py:143) | Thiết kế nói chỉ **file** trong kho HDSD bị chặn: `design.md:492`, cùng câu trong ngoặc ở `design.md:308` (E-7) nói vì thế chính thư mục kho vẫn lưu được. Không test nào ghim vế `os.path.isfile(full)` của phép kiểm đó. `test_manuals_directory_itself_still_resolves` và ca `git log -- docs` qua được theo cả hai cách, vì `_inside(root, full)` đã loại `full == root`. Bỏ `isfile` và chặn mọi đường dẫn trong kho thì cả 119 test vẫn xanh. Bản đó sẽ từ chối sai một thư mục con của kho: lưu `manuals_dir` là thư mục con của kho đang lưu (E-7) sẽ hỏng, `git log -- docs/vi` cũng vậy. | Thêm một ca có thư mục con (`myapp/docs/vi/` chứa một file `.md`). Khẳng định `resolve_safe_path("myapp/docs/vi")` trả đúng thư mục đó, `git log -- docs/vi` được, và `read_source` trên `myapp/docs/vi/x.md` bị từ chối. | confirmed (lần theo từng test của lớp với đột biến bằng tay; không chạy test)

minor | — | — | 0 điểm | —

### Review checklist (10)

1. đạt 2. đạt (đúng 2 file touchpoints, không file mới) 3. **không đạt** (RED có dán, không skip/xfail, nhưng luật "chỉ file" chưa có test; symlink vào/ra, thư mục symlink, `manuals_dir` trống/thiếu/không an toàn, `..`, đường dẫn tuyệt đối, NUL, tên bí mật, đuôi không cho phép đều đã phủ) 4. đạt (test cũ không đổi; lớp mới gọi `keep_agent_settings`, dùng `TempAppsRoot`, rollback) 5. đạt 6. đạt (blame và dạng `HEAD:path` bị từ chối cho file HDSD; `git log` không cho `-p`) 7. đạt (chữ ký không đổi; hệ quả lên `change_guard` ở mục dưới) 8. đạt 9. đạt (không thêm phụ thuộc) 10. đạt (`feat(agent): … (FEAT-007)`, một commit, không trailer AI)

### Không kiểm được từ diff (vòng 1) — tech-lead xử lý trước khi tick

- Hệ quả lên `change_guard`: `change_guard.check_write_path` (`change_guard.py:151`) cũng đi qua `resolve_safe_path`. Bot sửa mã nay bị từ chối (`PATH_INVALID`) khi sửa một file HDSD **đã có**, nhưng vẫn **tạo** được file mới trong kho, vì đường dẫn chưa tồn tại thì không phải file. `design.md:492` và ADR-034 QĐ 5 không nói muốn cách nào → câu hỏi cho designer.
- Test cũ đọc cài đặt của site thật: khoảng 110 lớp test cũ của `test_source.py` và các test `change_guard` nay đọc `manuals_dir` của site. Phần lớn dùng `TempAppsRoot` (giá trị thật không phân giải được ở đó); test làm việc trên `apps/` thật sẽ đổi kết quả nếu site có `manuals_dir` trỏ một thư mục thật.
- Tốc độ `search_source`: gọi `manuals_root()` cho mỗi file đi qua; giá trị cài đặt có cache theo request nhưng mỗi file vẫn tốn thêm vài lời gọi `realpath`/`isfile`/`isdir`; không đo được từ diff có vừa ngân sách 30 giây hay không.
- Đối chiếu GREEN của dev (119 và 64 test; `TestManualsDir::test_existing_dir_saves` còn xanh).

## Vòng 2 — approve (scoped re-review; CHƯA merge)

- Diff: `git diff cdaa40e..team/FEAT-007-task-38` (đầu `45857b1`, 1 commit, 1 file `test_source.py` +12; `source.py` không đổi).
- Lệnh đã dùng (chỉ đọc): `git log --oneline cdaa40e..team/FEAT-007-task-38`, `git diff --stat …`, `git diff …`, `git log -1 --format='%an%n%B' 45857b1`, `git show team/FEAT-007-task-38:` cho `test_source.py` (dòng 2290-2420), `source.py` (dòng 95-175), `test_utils.py` (`def write`).
- Bằng chứng của dev: RED của đột biến bỏ `isfile` (không commit): `AssertionError: None != '/tmp/tmpqys2grl8/apps/myapp/docs/vi'`, `Ran 120 tests in 9.696s FAILED (failures=1)`; GREEN một lần giữ khóa, migrate exit 0: `test_source` `Ran 120 tests in 9.936s OK`; `test_erp_ai_setting` `Ran 64 tests in 16.608s OK`; `test_architecture` `Ran 112 tests in 5.994s OK`.
- Finding vòng 1 (major STD-TEST-8, `test_source.py:2350`, luật ở `source.py:143`): **ADDRESSED**. Test mới `test_manuals_subdirectory_resolves_but_its_files_do_not` ở `test_source.py:2356` ghi `myapp/docs/vi/x.md` rồi khẳng định: `resolve_safe_path("myapp/docs/vi")` trả đúng thư mục con (dòng 2360); file đó phân giải ra `None` và `read_source` từ chối (2361-2362); `git log -- docs/vi` được, `git log -- docs/vi/x.md` bị từ chối (2364-2366). Reviewer lần tay: bỏ `os.path.isfile(full)` ở `source.py:143` thì `_inside` (`source.py:105`) trả True cho thư mục con, hàm trả `None`, hỏng `assertEqual` ở 2360 và phép `git log -- docs/vi` (`source.py:257`); khớp dòng RED của dev.
- Phát hiện mới: không có.

minor | — | — | 0 điểm | —

- Review checklist (10), chỉ diff sửa: 1–10 đạt (mục 2: một file touchpoint, `source.py` không đổi; mục 4: không phép khẳng định cũ nào đổi, dùng `setUp` của lớp; mục 10: `test(agent): … (FEAT-007)`, một commit, không trailer AI).
- Không kiểm được từ diff (vòng 2): số GREEN của dev (reviewer không chạy test); ba điểm của vòng 1 còn mở (xem trên).
- Trạng thái: lượt build 7 dừng ở trần 6 merge nên nhánh `team/FEAT-007-task-38` @ `45857b1` CHƯA merge, T38 chưa tick. Lượt sau: merge, một lần giữ khóa chạy `cmd.migrate` rồi `cmd.test_one` cho `test_source`, `test_erp_ai_setting`, `test_architecture`; tech-lead viết kết luận cho ba mục "không kiểm được" của vòng 1 trước khi tick.

## Kết luận của tech-lead (lượt 8, 2026-11-15, trước khi tick)

- Merge: `7d10d0f` (`git merge --no-ff team/FEAT-007-task-38`, 2 file +162/−4, không xung đột). Sau merge, một lần giữ khóa site, `MIGRATE_EXIT=0`: `test_source` `Ran 120 tests in 4.330s OK`; `test_erp_ai_setting` `Ran 74 tests in 4.378s OK`; `test_architecture` `Ran 112 tests in 3.388s OK`; `test_change_guard` `Ran 35 tests in 1.349s OK`. `cmd.lint`: chỉ `ruff-format` đỏ ở `erp_ai/test_change_decision.py` (nợ nền).
- Đối chiếu GREEN của dev: khớp (120 test của `test_source`; `test_erp_ai_setting` nay 74 test vì T15, T16 đã merge sau đó, `TestManualsDir` còn xanh).
- Hệ quả lên `change_guard`: không phải thiếu sót của T38. Mã làm đúng chữ `design.md:492` (chỉ **file** trong kho bị chặn); việc bot sửa mã còn tạo được file mới trong kho là chỗ thiết kế im lặng, đã chuyển designer (quyết định 00:59 (d) của team-leader, `design-w0-fixes-4.md`). `test_change_guard` xanh sau merge.
- Test cũ đọc cài đặt của site thật: không phải thiếu sót của task; trên site hiện tại `test_source` (120) và `test_change_guard` (35) đều xanh. Rủi ro còn lại, chưa thử: site lưu `manuals_dir` trỏ một thư mục thật dưới `apps/` thì test nào đọc file thật trong thư mục đó sẽ đổi kết quả; ghi cho `/team:verify`.
- Tốc độ `search_source`: chưa đo. Đọc mã (`source.py:123-147`): mỗi file đi qua thêm một lần `get_single_value` (có cache theo request) và vài lời gọi `realpath`/`isdir`; T38 không có tiêu chí thời gian riêng. Không chặn; để `/team:verify` đo trong ngân sách 30 giây của `search_source` nếu cần.

## deferred

- Không có finding minor. Ba điểm trên (designer: `change_guard`; verify: `manuals_dir` thật, tốc độ) không thuộc phạm vi task.
