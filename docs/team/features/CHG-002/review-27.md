Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 27 — CHG-002 T27

- Diff: `git diff a70a273..fa330af` (nhánh `team/CHG-002-task-26`, 1 commit, 2 file, +286/−9)
- Gói: T26 (sửa vòng 1) + T27 cùng nhánh, một reviewer chấm cả gói; verdict của T26 ở `review-26.md`
- Vòng: 1 (max_rework = 3)
- Verdict: **approve** → merge cùng T26 (sha ở dòng progress của T27 trong `tasks.md`), tick

## Vòng 1 — approve

Phát hiện blocker/major: không.

minor | — | — | 5 điểm nhỏ (xem deferred) | tùy dev

Lớp 1 (AC-36, AC-40, AC-41, AC-50; §4.1 bước 2): đạt, đúng hai file touchpoint.
- Đủ 13 test Expect, cộng ca "thư mục cha là file" (`test_propose_change.py:~1462`, 3 subtest) và `test_delete_symlink_refused` (`:1396`).
- `isfile` và không `islink` → `NOT_REGULAR_FILE` (`propose_change.py:~249-250`); `& 0o111` → `EXECUTABLE_FILE` (`:~251-252`); đọc `TEXT_MAX_BYTES + 1` byte rồi `text_refusal`; đích đổi tên đã `lexists` → `EXISTS` (`:~287-288`); diff của Xóa so với `/dev/null`, Đổi tên là hai dòng `rename` (`_op_diff :~306-313`); `FileOp` từ `change_guard`; đường dẫn đầy đủ từ `check_write_path(...).full_path`.
- Thứ tự phép kiểm (bộ chặn đường dẫn → file thường → bit thực thi → đọc byte và `text_refusal`): thiết kế không định thứ tự giữa các phép này, và đây là thứ tự duy nhất chạy được; bẩn / chưa theo dõi rơi vào `check_block` ở bước 3 (design.md:473).
- Mọi ca từ chối qua `assert_refused_whole` (`:1029-1033`): `{ok: False, reason}`, 0 đề xuất, 0 comment, snapshot git không đổi.
- Mã chỉ đọc file; không nhập `agent/changes`; không thêm `.insert(` hay `commonpath`.

Bằng chứng của dev: RED (chỉ có test) `Ran 61 tests in 75.910s` / `FAILED (failures=15)` (ví dụ `test_delete_directory_refused`: `…loại mục phải là edit, create, delete hoặc rename'} != {…đường dẫn không phải file thường'}`; `test_create_under_a_parent_that_is_a_file_refused`: `True is not false : {'ok': True, 'proposal': 'AICHG-00001', …}`); GREEN `test_propose_change` `Ran 61 tests in 76.641s` / `OK`, `test_registry` `Ran 41 tests in 2.725s` / `OK`, `test_apply_block` `Ran 9 tests in 12.903s` / `OK`, `test_change_decision` `Ran 10 tests in 18.933s` / `OK`, `test_architecture` `Ran 195 tests in 27.397s` / `OK`, `test_apply_job` `Ran 117 tests in 206.938s` / `OK`. L-1: 0, L-2: 0, test-input (luật mới): 0.

Review checklist (10): 10/10 đạt.

## OPEN (chờ phán; không phải finding vì hành vi từ chối tự nó đúng)

- OPEN-1, ca "thư mục cha là file" (`propose_change.py:~212-217`, `:~227-228`, `:~289-290` trả `change_guard.PATH_INVALID`): thiết kế không có chữ (design.md:472 chỉ nêu `lexists` → `EXISTS`; design.md:284). (a) giữ `PATH_INVALID`, designer thêm một câu vào §4.1 bước 2 và bảng §3.1; (b) hằng mới (ví dụ `PARENT_NOT_DIR`) thành một luật của `check_write_path` để `check_block` lúc áp dụng cũng bắt (ngoài touchpoint T27).
- OPEN-2, lý do cho symlink khi Xóa: design.md:245 ghi symlink → `NOT_REGULAR_FILE`, nhưng §3.2 bước 6 (design.md:289) cho `PATH_SYMLINK` trước, nên nhánh `islink` không ca nào chạm tới qua tool. (a) sửa design.md:245 (symlink nhận `PATH_SYMLINK` từ bộ chặn, `islink` là lớp phòng thủ, test `:1396` ghim `PATH_SYMLINK`); (b) giữ :245, bộ chặn bỏ luật 6 cho thành phần cuối của mục Xóa (nới bộ chặn).

Cả hai điểm đưa lên team-leader trong báo cáo lượt 4.

## Không kiểm được từ diff (tech-lead đã xử lý)

- Cha bị đổi thành file sau lúc đề xuất (lúc áp dụng §4.2 bước 4 chỉ kiểm `lexists` của đích; trông vào `file_writer` từ chối): T35 (đã review) ghi qua `make_parents` / `write_atomic` có kiểm lại đường dẫn (ADR-040 C-2) và trả lại ngược khi lỗi; CHƯA có ca test riêng cho đúng tình huống này: ghi thành việc cho lệnh giao T36 / T39.
- Ghim metadata commit của khối (không email / URL / token, `BOT_AUTHOR`, "(không hiện tên)"): T43 chỉ nêu remote, refs, nhánh, hook. CHƯA có trong Expect của task nào cho khối: ghi thành điểm mở cho `/team:plan --insert` hoặc bổ sung Expect của T36 (báo cáo lượt 4).
- Đích đổi tên trùng đường dẫn với một mục khác trong cùng khối: thuộc `check_block` (T12 `BLOCK_PATH_TWICE`, đã tick).
- Module và cả app sau merge: dòng progress của T27 trong `tasks.md` (đợt merge 16).

## deferred

1. `test_delete_symlink_refused` (`:1402`) chấp nhận bất kỳ lý do nào (xanh từ RED); ghim lý do thật sau khi có phán OPEN-2.
2. `test_delete_executable_refused` chỉ dùng `0o744`; thêm ca `0o654`.
3. Xóa một file rỗng cho phần diff rỗng (`difflib` không in gì) (suspected).
4. `new_path` của `_row` lấy `normpath` của đầu vào, `file_path` lấy `guard.rel_path`.
5. `_removed_text` lặp 5 dòng đọc byte và `text_refusal` của `_edited_op` (STD-DESIGN-4).
