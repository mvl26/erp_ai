Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 47 — FEAT-004 T47

- Diff: `git diff 7c2a3af..485f09c` (nhánh `team/FEAT-004-task-47`; 1 commit; 2 file, +562/-76)
- Lệnh đã dùng: `git log --oneline 7c2a3af..team/FEAT-004-task-47`, `git diff --stat 7c2a3af..team/FEAT-004-task-47`, `git diff 7c2a3af..team/FEAT-004-task-47 -- <file>`, `git show 485f09c:<file>`, `git grep -n ... 485f09c`, `git log -1 --format=... 485f09c`
- Vòng: 1
- Verdict: request-changes

## Vòng 1 — request-changes
Lớp 1: khớp design 4.4 bước 4, 6 và `design-addendum-3.md` QĐ-B2 mục 1–4, QĐ-B5 phía hoàn tác. `apply_job.py:510-520`: `read_git_state.refusal` → `Lỗi`, rồi `git_is_ancestor` (`None` → `GIT_ERROR`, `False` → `GIT_NOT_ANCESTOR`) trước mọi lần ghi; không kiểm "nhánh trùng" (ADR-022 QĐ 6). Commit hoàn tác lỗi dùng lại `_commit_landed` (HEAD không đổi → trả lại so với `old_head`; commit của người → so với `head_now`; HEAD không đọc được hoặc tóm tắt không đọc được → `GIT_ERROR`, không trả lại); cờ `committed`; kiểm sau với `state.branch`; `_fail_after_commit`/`_give_back_after_crash` dùng chung qua tham số `action`, `record`, `give_back`. `result` không còn được truyền vào `_Stop` nên đầu ra git không vào `command_output` (design 3.5). Các test Expect đều có (`test_undo_postcheck_unreadable_keeps_commit_and_fails` đã có sẵn từ T20, `test_apply_job.py:1785`). Mọi điểm "Ghi cho dev T47" đã xử lý. Không ngoài touchpoint.

Test: phần lớn sẽ đỏ khi bỏ hành vi — nhánh "HEAD == old_head" được ghim vì HEAD nền là commit bot (`author_email == BOT_GIT_EMAIL`); so HEAD với `head_now` được ghim ở subTest hoàn tác của `test_commit_failed_while_human_commit_moved_head_restores`; `state.branch` khác `target_branch` được ghim ở `test_undo_postcheck_branch_is_the_checked_out_branch`; `None` khác `False` được ghim ở `test_undo_ancestor_unreadable_fails_with_git_error`. Một lỗ hổng:

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-8 | erp_ai/agent/changes/test_apply_job.py:1880-1915 (kiểm `apply_job.py:516`) | Thứ tự đối số `git_is_ancestor(repo, apply_commit_sha, old_head)` không bị test nào ghim. Trong mọi test chạm phép kiểm này, HEAD lúc hoàn tác hoặc bằng commit áp dụng (bằng nhau → True cả hai chiều), hoặc ở nhánh rẽ (`other_head`, không ai là tổ tiên của ai → False cả hai chiều); `test_undo_ancestor_unreadable...` khẳng định `args[1:] == (apply_commit, apply_commit)` — hai giá trị bằng nhau. Đảo đối số vẫn xanh toàn bộ, nhưng sẽ từ chối `GIT_NOT_ANCESTOR` mọi lần hoàn tác sau khi người commit thêm trên nhánh — đúng trường hợp thường gặp nhất của AC-20 / ADR-022 QĐ 6. Không có test nào "người commit sau áp dụng, rồi hoàn tác thành công" (commit tay trong `test_undo_accepted_when_bot_commit_lands_after_human_commit` xảy ra sau phép kiểm tổ tiên). | Thêm test (cả 2 KINDS): sau `undo_requested`, `commit_file(APP, "pkg/human.py", ...)` trên cùng nhánh rồi mới `run_change(name, "undo")` → `Đã hoàn tác`, `HEAD~1` = commit tay, `HEAD~2` = commit áp dụng; và/hoặc ở test `None` dựng HEAD ≠ commit áp dụng để `args[1:]` là hai giá trị khác nhau theo đúng thứ tự `(apply_commit, head)`. Certainty: confirmed (đã duyệt mọi lời gọi `run_change(name, "undo")` trong file ở `485f09c`). |

minor | — | — | 1 điểm nhỏ: subTest "commit times out" của `test_undo_commit_failure_restores_applied_bytes` có `output=""` nên phép kiểm `command_output` rỗng ở subTest đó không thể đỏ (subTest "commit fails" vẫn ghim) | tùy dev

## Review checklist (10)
1. Đúng và đủ spec, không thừa — đạt (STD-DESIGN-5, STD-TEST-2).
2. Trong touchpoints; không file mới — đạt (STD-DESIGN-1, STD-STRUCT-1).
3. Test đỏ trước (RED của dev có), lỗi/biên được phủ, không skip — trượt một phần: thứ tự đối số tổ tiên chưa ghim (STD-TEST-8, major trên).
4. Không sửa assertion cho khớp sai; test độc lập (sandbox mới mỗi subTest, rollback) — đạt (STD-TEST-5, STD-TEST-6). `assert_no_human_email_stored(row_count=...)` chỉ thêm tham số, giá trị mặc định giữ 2.
5. Lỗi được xử lý: không nuốt lỗi; exception thứ hai khi trả lại được ghi log; git ghi có `limit_s` theo deadline — đạt (STD-ERR-1, STD-ERR-5, STD-ERR-7).
6. Không bí mật; đầu ra git không lưu; không lộ email người (NFR-8 được kiểm) — đạt (STD-SEC-1, STD-SEC-6).
7. Hợp đồng: `_git_commit` bị bỏ, `_give_back`/`_fail_after_commit`/`_give_back_after_crash` đổi chữ ký — đều nội bộ module, mọi nơi gọi đã sửa; không đổi schema — đạt (STD-DESIGN-3).
8. Tên, cấu trúc, style; không mã chết (`_git_commit` đã gỡ) — đạt (STD-NAME-2, STD-STYLE-4, STD-STYLE-5).
9. Không phụ thuộc mới — đạt (STD-DEP-1).
10. Commit `feat(changes): ... (FEAT-004)`, nhánh `team/FEAT-004-task-47`, không trailer AI — đạt (STD-NAME-4, STD-NAME-5, STD-GIT-8).

## Bằng chứng của dev
- RED: `AssertionError: Tuples differ: ('Đã hoàn tác', None) != ('Lỗi', 'commit áp dụng không còn nằm trong lịch sử nhánh đang checkout')` (1 trong 18 assertion đỏ)
- GREEN: `Ran 95 tests in 196.073s` / `OK`
- `cmd.test` chưa chạy (site dùng chung; tech-lead chạy sau merge). Reviewer không chạy test.

## Không kiểm được từ diff (tech-lead xử lý)
- `git commit --only -- <đích>` thật khi thất bại với file đã xóa (hoàn tác file mới) có để lại thay đổi trong index thật hay không: test chỉ stub `git_commit_only`; kiểm `worktree_changes() == ""` chỉ có ở nhánh stub.
- `cmd.test` toàn app sau merge (`_give_back`/`_fail_after_commit` đổi chữ ký, phía áp dụng T45 đi qua cùng hàm).

## deferred
- `_recheck` (`apply_job.py:215`): đề xuất lệnh ở nhánh hoàn tác vẫn đọc `settings` chưa gán; hiện được chặn bởi `request_undo` (test mới `test_request_undo_refuses_a_command_proposal`). Ngoài phạm vi T47.
- Nhánh hoàn tác file mới khi `os.path.lexists(full)` vẫn đúng sau `remove_created` → `WRITE_MISMATCH` không gọi trả lại/kiểm HEAD (mã cũ, không đổi trong diff).
