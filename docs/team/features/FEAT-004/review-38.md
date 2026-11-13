Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 38 — FEAT-004 T38

- Diff: `git diff 36ef522..team/FEAT-004-task-38` (1 commit `18b5cff`; 2 file, +570)
- Vòng: 1 (max_rework=3)
- Verdict: design-defect (T38 ĐỖ, chưa merge, chưa rework; chặn T39, T42)

## Vòng 1 — design-defect
Lớp 1: AC-18 và D-20 làm đúng thứ tự design 3.2 bước 1–6; bước 7 (upstream/ahead) để T39 đúng tasks.md. Chỉ 2 file touchpoint. 8 câu từ chối trùng từng byte với bảng 3.2. Mọi lời gọi qua `run_git_read` với lệnh con là hằng.

### Phán về ADR-022 QĐ 4 (filter): design-defect, không phải blocker của diff này
- `git status` băm lại file đích đã theo dõi mỗi khi dữ liệu stat không khớp index: sau mọi lần sửa, khi mốc thời gian trùng, và ở mọi lần chạy vì `--no-optional-locks` không cho git lưu index đã làm mới.
- Băm lại chạy `convert_to_git`, tức chạy lệnh `filter.<driver>.clean` / `filter.<driver>.process` khai trong `.git/config` của chính repo đích; thuộc tính `filter=` đến từ `.gitattributes` trong cây hoặc `.git/info/attributes`.
- `git_global_options(read=True)` và `git_env` không chặn được: `GIT_CONFIG_GLOBAL=/dev/null` và `NOSYSTEM` vẫn để `.git/config` có hiệu lực (ADR-022:22 tự ghi). Ca thực tế: `git lfs install --local`.
- `status` còn đi vào submodule, filter của chúng cũng chạy.
- Phía ghi (T43: `add`, `commit --only`) chạy clean filter trên file đích ở mọi lần.
- Các lệnh đọc khác ở đây (`rev-parse`, `check-ignore`) không đọc nội dung file.
- Độ chắc: xác nhận từ mã git (`ce_compare_data` → `index_fd` → convert); reviewer không chạy thử (vai chỉ đọc).
- Dev làm đúng design 3.2 bước 6 và danh sách tùy chọn "định nghĩa một chỗ"; sửa cần quyết định design. Phương án: từ chối khi file đích có thuộc tính `filter` (cần thêm lệnh đọc như `check-attr` vào tập cho phép); `--attr-source=<cây rỗng>` (git 2.43 có, nhưng không phủ `info/attributes`); `--ignore-submodules=all`.

### Phán về pathspec: không phải lỗi của diff; chữ design lệch
- Design ghi `-- <rel>` cho cả hai lệnh. Diff dùng `./<rel>` cho `check-ignore` (lệnh này thoát 128 khi có `:` đầu) và `:(literal)<rel>` cho `status`.
- `<rel>` trần là pathspec glob: file đích tên `f*.py` sẽ khớp file bẩn khác và phá "file khác bẩn không chặn". Dạng của diff đúng; `test_read_git_state_pathspec_is_literal` đỏ nếu bỏ một trong hai.
- Designer cập nhật design 3.2 bước 5 và 6 theo hai dạng này.

### Phát hiện (dev sửa trong vòng sau khi design chốt)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-8 | erp_ai/agent/tools/source.py:513 (`any(existing[1:])`); `GIT_STATE_FILES` ở source.py:91 | `rebase-apply` là một trong 5 tệp "đang dở" của design bước 4 nhưng không ca nào tạo nó; chỉ vị trí argv được ghim, nên đổi lát cắt thành `existing[1:5]` vẫn xanh. Nguyên nhân: test plan chỉ nêu 4 tệp và `mark_in_progress` từ chối `rebase-apply` | trong test_source.py thêm ca tạo thư mục ở `git rev-parse --git-path rebase-apply` và mong `EXPECTED_GIT_IN_PROGRESS`; đặt ngoài hoặc cạnh test 13 subTest |

minor | — | — | 3 điểm nhỏ: `_git_refused(reason)` ở source.py:428 thiếu type hint; không có ca cho đầu ra top-level `"{repo}\n\n"` (vế `not all(lines)`, source.py:481); regex nhận HEAD 64 hex trong khi design ghi 40 | tùy dev

## Review checklist (10)
Đã phủ 10/10; ngoài major trên và design-defect, phần còn lại đạt: 13 subTest đúng thứ tự design; 8 ca thứ tự kiểm có hai lý do cùng lúc; mọi nhánh mã thoát, quá giờ, đầu ra không đọc được có ca kèm số lần gọi; đầu vào được kiểm trước mọi lệnh git; không skip.

## Bằng chứng của dev
- RED: `FAIL: test_read_git_state_refusals [staged] AssertionError: GitState(refusal=None, …) != GitState(refusal='file đích có thay đổi chưa commit', …)`
- GREEN: `test_source` "Ran 88 tests … OK", `test_architecture` "Ran 98 tests … OK"; lint sạch

## Không kiểm được từ diff (tech-lead xử lý)
- Hành vi filter chưa chạy thử: sau khi design chốt, thêm test sandbox có filter trong `.git/config` ghi tệp đánh dấu (giao dev ở vòng sửa).
- Repo thuộc user hệ điều hành khác ("dubious ownership", `safe.directory`) làm `rev-parse` thoát 128 → hiện thành `GIT_NOT_REPO`; phụ thuộc triển khai → deferred cho devops/architect.
- `cmd.test` sau merge: chưa có vì chưa merge.

## deferred
- Design 3.2 bước 5–6: ghi pathspec `./<rel>` và `:(literal)<rel>` (designer).
