Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 09 — CHG-002 T9

- Diff: `git diff a83923b..3a56462` (nhánh `team/CHG-002-task-9`, 2 commit `da795ea` và `3a56462` (rỗng, chỉ sửa một tên test trong dòng `test-shape:`), 3 file, +146/−23; CHƯA merge)
- Vòng: 1 (max_rework = 3)
- Verdict: design-defect (dev cũng trả `DESIGN_CONFLICT`)

## Vòng 1 — design-defect
Mã đúng và theo §3.2; hai test lỗi cũ không sửa được theo addendum-2 L-1 như đang viết.

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| blocker | STD-TEST-5 | erp_ai/agent/tools/test_propose_change.py:430 | Dòng `test-shape:` thứ 6 đổi ĐẦU VÀO (`pkg/tool.exe` → `pkg/.gitattributes`), không chỉ giá trị ghim; L-1 điểm 3 chỉ cho đổi giá trị, điểm 5 coi dòng không khớp là chặn merge. Không có cách sửa chỉ-giá-trị: `tool.exe` nay là lệnh tạo hợp lệ, dòng đó sẽ sinh đề xuất và làm hỏng `assert_nothing_created()` | Cần phán quyết dưới đây; cách đổi của dev (cùng thay đổi §3.1, giữ đường lỗi, giá trị lấy từ `change_guard.GIT_DIR`) là ứng viên tốt để nhận nguyên |
| blocker | STD-DESIGN-1 | erp_ai/agent/changes/test_apply_job.py:1734-1745 | `TestUndoCode::test_undo_rechecks_fail_without_writing [guard refusal]` đỏ trên nhánh task (`AssertionError: Tuples differ: ('Đã hoàn tác', None) != ('Lỗi', 'đuôi file không được phép')`). Phần dựng của nó patch `source.DUOI_CHO_PHEP`, thứ bộ chặn không còn đọc (`change_guard.py:163-164` đã xóa), nên hoàn tác thành công. File ngoài touchpoint của T9; merge khi đỏ là trái STD-CI-2 | Sau phán quyết, tech-lead thêm file vào T9; đổi phần dựng, ví dụ `patch.object(source, "TEN_CAM", re.compile(re.escape(os.path.basename(REL))))`, và lý do thành `change_guard.NAME_FORBIDDEN` |

minor | — | — | 4 điểm nhỏ (xem deferred) | tùy dev

Thứ tự `check_write_path` so với §3.2 (`change_guard.py:176-196`): bước 1 `PATH_INVALID` đúng; bước 2 `APP_NOT_ALLOWED` rồi "thư mục app không có → `PATH_INVALID`" (thiết kế không nói chỗ của luật thư mục, mã đặt sau bước 2); bước 3 `APP_FORBIDDEN` đúng; bước 4 `license.txt` rồi `text_refusal` (tên bí mật, rồi `.git*`); bước 5 `PATH_GIT_PATTERN` đúng; bước 6–7 thuộc T10.

Sáu dòng `test-shape:` so với L-1 điểm 2, 3: dòng 1–5 khớp (`test_refusal_wording_matches_design_table`, `test_double_refusal_returns_earlier_reason_of_table_order`, `test_refuses_extension_outside_read_list_even_for_new_file`, `TestCheckWritePathGit::test_refuses_git_pattern_names`, `test_each_guard_refusal_creates_zero_proposals`); dòng 6 `test_new_file_errors_exists_and_no_parent` KHÔNG khớp (blocker 1).

Test đỏ ở `test_apply_job`: đổi chỉ giá trị ghim không làm nó xanh đúng nghĩa (kết quả chỉ-giá-trị duy nhất là `('Đã hoàn tác', None)`, biến dòng từ chối thành dòng thành công, xóa phép kiểm đường lỗi duy nhất của bộ chặn lúc hoàn tác; L-1 điểm 3 cấm). Cần phần dựng mới và lý do ghim mới. Phần dựng đằng nào cũng phải đổi: T49 xóa `DUOI_CHO_PHEP`, lúc đó `patch.object` ném `AttributeError`.

**design-defect:** `design-addendum-2.md:78` (L-1 điểm 3) và `design.md:811` (§8.3, chỉ ghi "8 đuôi … (`PC`)") không nói gì về test lỗi cũ có đầu vào trở thành hợp lệ khi một luật §3.2 bị gỡ. T9 có hai test như vậy. Gợi ý một dòng phụ lục: "Khi §3.2 gỡ một luật, dòng lỗi cũ được đổi đầu vào hoặc phần dựng sang đầu vào gần nhất còn bị một luật §3.1 từ chối, giữ đường lỗi; dòng `test-shape:` ghi đầu vào cũ → đầu vào mới"; nêu tên hai test; cho đổi tên test ở minor 1.

Ghi chú thiết kế (không chặn, cho designer):
1. Thứ tự trong bước 4: mã kiểm `license.txt` trước `text_refusal`, design.md:287 viết `text_refusal` trước. `myapp/.github/license.txt` vì vậy cho `NAME_FORBIDDEN`, test mới ghim điều đó; khớp "tên trước git" (AC-51), cần designer xác nhận.
2. Bỏ bước đuôi thì chính thư mục app (`"myapp"`) qua `check_write_path` với `reason=None`; trước đây chỉ luật đuôi chặn nó. design.md:293 không phủ ca này.
3. (từ dev) Luật "thư mục app không có" đặt sau `APP_NOT_ALLOWED` để ca PC `("a", "app không có trong danh sách được sửa")` không lật sang `PATH_INVALID`; `erp_ai` có trong danh sách mà không có thư mục nhận `PATH_INVALID`.

## Review checklist (10)
1. Đạt phần mã (AC-44, AC-50, AC-51, AC-52; 5 test của Expect có đủ, có dòng mồi `my.gitignore`, `notes.git`, `.gi/`, `git/`, `flat.py`). 2. Đạt (3 file touchpoint). 3. Đạt (RED 10 lỗi đúng lý do). 4. KHÔNG đạt: blocker 1 (L-1 điểm 3). 5. Đạt. 6. Đạt. 7. Đạt. 8. Đạt, trừ minor 1. 9. Đạt. 10. Đạt, trừ minor 4.

## Không kiểm được từ diff
- `test_apply_job` xanh trên BASE `a83923b` (L-1 điểm 4b cần): đợt merge 3 chạy cả app trên `a83923b` chỉ đỏ đúng 6 test của dòng `baseline:`, nên test đó xanh trên BASE (tech-lead đã đối chiếu).
- Các phép kiểm sau (tạo "đã tồn tại", xóa/đổi tên `NOT_REGULAR_FILE`, đọc của sửa, `file_writer.remove_file` / `write_atomic`) có từ chối đích là thư mục app ở cả lúc đề xuất và lúc áp dụng không: chưa đọc; cho designer (ghi chú 2).
- Ảnh hưởng cả app của chữ `GIT_DIR` mới: `git grep` chỉ thấy câu cũ ở các file đã chạm và dòng `test_apply_job`; chưa có lần chạy cả app (task chưa merge).
- Cho T10: dòng `myapp/sh_link.py` ở `test_change_guard.py:217` sẽ lật từ `None` sang `PATH_SYMLINK` khi bước 6 vào.

## deferred
1. STD-NAME-6 `test_change_guard.py:206`: `test_refuses_extension_outside_read_list_even_for_new_file` nay khẳng định được nhận, tên nói ngược; L-1 cấm đổi tên, gộp vào phán quyết.
2. `test_propose_change.py:317`: dòng `tool.sh` không còn là từ chối của bộ chặn và lặp dòng `missing.py` ở `:323`.
3. `:317` dùng chữ `"file không tồn tại"` thay vì `propose_change.NOT_FOUND` (L-1 "lấy từ hằng nếu hằng có"); byte trùng, kiểu của file là chữ viết thẳng.
4. `3a56462` là commit rỗng; khi merge, dòng `test-shape:` đã sửa phải nằm trong thân commit của task (STD-GIT-2).
