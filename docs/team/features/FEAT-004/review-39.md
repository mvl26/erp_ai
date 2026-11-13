Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 39 — FEAT-004 T39

- Diff: `git diff 99f17b6..team/FEAT-004-task-39` (1 commit `8ff4278`; 2 file, +696/-3)
- Vòng: 1 (max_rework=3)
- Verdict: design-defect (T39 ĐỖ, chưa merge; mã không cần đổi; chặn T42, T19)

## Vòng 1 — design-defect
Lớp 1: AC-17, AC-20, AC-21, NFR-8 và luật 3 cờ (`--filters`, `--textconv`, `--ext-diff`) đều có; chỉ 2 file touchpoint. Một câu Returns không thể đạt.

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| design-defect | STD-DESIGN-2 | docs/team/features/FEAT-004/tasks.md (Returns của T39) và design.md:920 | Returns và dòng test plan AC-21 ghi `branch.<n>.remote` là URL → `upstream_ref = "(remote không tên)"`. Design 3.2 bước 7 (design.md:348) chỉ đọc upstream qua `rev-parse @{upstream}`, mã khác 0 là "không theo" (`""`/0), và cấm đọc `.git/config`. Với remote là URL, git không có ref remote-tracking và thoát 128, nên design không bao giờ sinh được giá trị mặt nạ. Mã trả `("", 0)`; `test_branch_remote_set_to_url_never_leaks_it` ghim điều đó và kiểm URL xuất hiện 0 lần (khớp AC-21, NFR-8). `test_upstream_with_url_like_name_is_masked` phủ ca khác: remote có tên chứa `@` | designer viết lại câu Returns và dòng 920: "URL remote → không theo, `""`/0, URL không xuất hiện"; không đổi mã |
| design gap | STD-DOC-7 | design.md:333-336, 622-623 | Hai ca lỗi chưa có cách xử lý: (1) `git_commit_summary` và `git_blob` ném `RuntimeError(GIT_ERROR)` khi git lỗi hoặc quá giờ; chữ ký design và Receives của T19/T45/T20/T47 không nói; bước 3.4/3.5 không nói việc ném trong lúc kiểm sau nghĩa là gì; luật T45 "exception sau ghi → trả lại" sẽ ghi `content_before` đè lên file ĐÃ commit; (2) `git_head` trả `None` cả khi chưa có commit lẫn khi quá giờ; ở bước 3.4, `None ≠ old_head` đẩy luồng vào nhánh "HEAD đã dịch" | designer ghi ở 3.2 và 4 Receives đó: `RuntimeError` trong kiểm sau → `GIT_COMMIT_MISMATCH` (hoặc `GIT_ERROR`), không trả lại; `git_head is None` → `GIT_ERROR` |

Các điểm đã chấm:
- Giá trị trả về khớp chữ ký Returns: `git_head` → `None` khi lỗi/quá giờ/chưa có commit; `git_is_ancestor` → `None` khi mã khác 0/1, quá giờ, sha không có; `git_blob` → `None` chỉ khi git thoát 128 cho đường dẫn sau khi commit đã được xác nhận, còn lại ném; `git_commit_summary` luôn ném khi lỗi. Mỗi nhánh có subTest kèm số lần gọi.
- Metadata commit từ `rev-list` (`%H %P %ae`), đường dẫn từ `diff-tree`, nhánh từ `rev-parse`, blob từ `cat-file`, tổ tiên từ `merge-base`; cả 5 thuộc `GIT_READ_SUBCOMMANDS`. 3 cờ bị từ chối ở dạng đầy đủ, viết tắt và `=value`, 0 tiến trình con; dạng `--no-` vẫn qua.
- Test cũ chỉ đổi 2 chỗ (thêm lời gọi bước 7 vào danh sách mong đợi; `good_runs` thành staticmethod thêm một lần chạy mã 128): mở rộng, không nới assertion (STD-TEST-5 đạt).

minor | — | — | 3 điểm nhỏ: test mới gọi `GitSandbox._write` (hàm riêng); `git_blob(repo, "HEAD", …)` phân giải HEAD ba lần (nơi gọi của design truyền `s.commit`); mặt nạ `@` che cả tên nhánh thật có `@` | tùy dev

## Review checklist (10)
Đã phủ 10/10; ngoài design-defect, phần mã đạt.

## Bằng chứng của dev
- RED: `FAIL: test_run_git_read_rejects_filter_textconv_ext_diff_flags (...TestGitReadOptions...) (flag='--filters')` → `AssertionError: ValueError not raised`; `AttributeError: module 'erp_ai.agent.tools.source' has no attribute 'git_blob'`
- GREEN: test_source `Ran 110 tests in 7.664s` / `OK`; test_architecture `Ran 107 tests in 1.494s` / `OK`; lint sạch

## Không kiểm được từ diff (tech-lead xử lý)
- Task sau (T45, T47) có giữ `author_email` (email người) khỏi log, trường, comment không (NFR-8): ghi vào handoff T45/T47.
- `git_source` vẫn đưa `log` qua đường riêng có `--no-ext-diff --no-textconv`: ngoài diff.
- `cmd.test` sau merge: chưa có vì chưa merge.

## deferred
- Không có.
