Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 47 — FEAT-004 T47

- Diff: `git diff 7c2a3af..485f09c` (nhánh `team/FEAT-004-task-47`; 1 commit; 2 file, +562/-76)
- Lệnh đã dùng: `git log --oneline 7c2a3af..team/FEAT-004-task-47`, `git diff --stat 7c2a3af..team/FEAT-004-task-47`, `git diff 7c2a3af..team/FEAT-004-task-47 -- <file>`, `git show 485f09c:<file>`, `git grep -n ... 485f09c`, `git log -1 --format=... 485f09c`
- Diff vòng 2: `git diff 485f09c..4359e7d` (1 commit; 1 file, +19/-1)
- Vòng: 2
- Verdict: approve (vòng 1: request-changes)

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

## Vòng 2 — approve
- Lệnh đã dùng: `git log --oneline 485f09c..team/FEAT-004-task-47`, `git diff --stat 485f09c..team/FEAT-004-task-47`, `git diff 485f09c..team/FEAT-004-task-47`, `git log -1 --format='%an <%ae>%n%B' 4359e7d`, `git rev-parse team/FEAT-004-task-47` (= `4359e7d`).
- Chỉ xét diff sửa: 1 commit `test(changes): lock the argument order of the undo ancestor check with a human commit after apply (FEAT-004)`, chỉ đụng `erp_ai/agent/changes/test_apply_job.py`; không đổi mã sản phẩm.

| Phát hiện vòng 1 | Trạng thái | Bằng chứng |
|---|---|---|
| major STD-TEST-8 — thứ tự đối số `git_is_ancestor(repo, apply_commit_sha, old_head)` không được ghim | ADDRESSED | `test_apply_job.py:1901-1915` test mới `test_undo_accepted_after_a_human_commit_on_the_same_branch` (cả 2 KINDS): commit tay trên cùng nhánh sau áp dụng → `Đã hoàn tác`, `HEAD~1` = commit tay, `HEAD~2` = commit áp dụng. Commit áp dụng là tổ tiên của HEAD nhưng không ngược lại, nên đảo đối số → `False` → `GIT_NOT_ANCESTOR` → đỏ. `test_apply_job.py:1920,1933`: test `None` dựng HEAD ≠ commit áp dụng và khẳng định `args[1:] == (apply_commit, human_head)` — hai giá trị khác nhau, đúng thứ tự. RED của dev khớp: đảo đối số → `FAILED (failures=3)` (2 subTest + "Tuples differ" ở test mock). |

Lớp 1: đúng phần sửa đã yêu cầu (AC-20, ADR-022 QĐ 6), không thừa, trong touchpoint.

### Review checklist (10) — vòng 2
1. Đúng và đủ phần sửa, không thừa — đạt (STD-DESIGN-5, STD-TEST-2).
2. Chỉ sửa file test đã có trong touchpoint; không file mới — đạt (STD-DESIGN-1, STD-STRUCT-1).
3. RED có (đảo đối số có chủ đích → 3 failures); phủ đường "người commit sau áp dụng"; không skip/xfail — đạt (STD-TEST-1, STD-TEST-8, STD-TEST-4).
4. Assertion `(apply_commit, apply_commit)` đổi thành `(apply_commit, human_head)` vì dựng thêm commit tay, không phải để khớp hành vi sai; test mới dùng sandbox mỗi subTest — đạt (STD-TEST-5, STD-TEST-6).
5. Không đổi mã xử lý lỗi — không áp dụng/đạt (STD-ERR-1).
6. Không bí mật; email trong commit tay là của sandbox — đạt (STD-SEC-1, STD-SEC-6).
7. Không đổi hợp đồng — đạt (STD-DESIGN-3).
8. Tên test nêu rõ hành vi; chú thích đúng nội dung; style theo file — đạt (STD-NAME-2, STD-STYLE-4, STD-STYLE-5).
9. Không phụ thuộc mới — đạt (STD-DEP-1).
10. Commit `test(changes): ... (FEAT-004)`, nhánh `team/FEAT-004-task-47`, không trailer AI — đạt (STD-NAME-4, STD-NAME-5, STD-GIT-8).

### Bằng chứng của dev (vòng 2)
- RED: đảo hai đối số có chủ đích → `FAILED (failures=3)`; `('Lỗi', 'commit áp dụng không còn nằm trong lịch sử nhánh đang checkout') != ('Đã hoàn tác', None)` cho cả 2 KINDS; test mock "Tuples differ" với hai sha sai thứ tự.
- GREEN: cả module `Ran 96 tests`, 14 errors đều `QueryDeadlockError` (site dùng chung); chạy lại 14 test theo tên `Ran 14 tests ... OK`.
- Reviewer không chạy test. Tech-lead nên chạy `cmd.test` toàn app sau merge để xác nhận 14 deadlock là do site dùng chung, không do test.

### deferred (vòng 2)
- Không có điểm mới. Minor vòng 1 (subTest "commit times out" có `output=""`) giữ nguyên, tùy dev.

## Phần phụ lục 4 (T47b, 2026-11-14) — `_git_short_line`

Tech-lead chép từ tin trả về của reviewer. Việc này do `design-addendum-4.md` giao cho T47 sau khi T47 gốc đã merge; làm trên `team/FEAT-004-task-47b` → `-47b-r2` → `-47b-r3`.

- Diff vòng 1: `git diff 73f346d..46ec724` (2 commit `8b06f46`, `46ec724`; 2 file, +124/−6)
- Diff vòng 2: `git diff 46ec724..2d96466` (1 commit; `test_apply_job.py` +21)
- Vòng: 2 · Verdict: approve (vòng 1: request-changes)

### Vòng 1 — request-changes
- Layer 1: QĐ-D1, QĐ-D2 làm đúng chữ (dòng cuối không rỗng, `Cc` → khoảng trắng, che rồi mới cắt 120, rỗng → chỉ câu không có `: `; cả 3 chỗ gọi `_commit_failed_reason` ở `apply_job.py:399,407,580`); 3 test có tên như phụ lục; đổi đầu vào `test_long_git_output…` theo phụ lục; đổi một phép kiểm T48 (`test_apply_job.py:2737`) theo phán round 75.

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-2 | erp_ai/agent/changes/test_apply_job.py:774-801 (luật ở apply_job.py:259-262) | Hai phần của luật che không được ghim: `~` (đầu vào duy nhất `~/x`, `~/y` đã bị `/` che) và ngưỡng "≥ 20" cùng các ký tự `_+-` của `GIT_KEY_LIKE` (chỉ có chuỗi 40 ký tự chữ-số); đổi `{20,}` thành `{7,}`..`{40,}` vẫn xanh | Thêm subTest: từ có `~` không có `/`; từ 20 ký tự bị che và 19 ký tự giữ nguyên; từ chỉ đạt 20 qua `_` hoặc `-` |

minor | — | — | 2 điểm nhỏ: `assertNotIn(HOOK_OUTPUT, …)` ở vòng lặp T48 không còn đỏ được sau khi email bị che; `GitSandbox` thứ hai dựng thừa ở subTest "apply" | dev's call

- Bằng chứng của dev: RED `FAILED (failures=10)`, `'/tmp/…/apps/custom_app' unexpectedly found in 'commit git lỗi, đã trả file về như trước: fatal: https://x-token-FAKE@host/r.git real.person@example.com /tmp/…/index.lock'`; commit 2 RED `'hook-output-T48 real.person@example.com pre-commit' not found in '… hook-output-T48 … pre-commit'`; GREEN `Ran 112 tests` FAILED (errors=2, `QueryDeadlockError`), 2 ca chạy lại theo tên `Ran 2 tests` OK.

### Vòng 2 — approve (chỉ diff sửa)
- major STD-TEST-2: **ADDRESSED** — `test_git_short_line_masks_each_rule_member_alone` (`test_apply_job.py:804-822`): `HEAD~1`, `~miyano`, từ 20 ký tự (che), 19 ký tự (giữ), `ab_…`, `ab-…`, `ab+…`, `C:\x`, `token=abc`; kỳ vọng viết `"…"` trực tiếp.
- Bằng chứng của dev (đột biến, khôi phục sau mỗi lần; `apply_job.py` trùng byte với `46ec724`): bỏ `~` → `'lỗi HEAD~1 cuối' != 'lỗi … cuối'`; `{21,}` → `'lỗi Ab3dEf6hIj9lMn2pQr5t cuối' != 'lỗi … cuối'`; `{19,}` → `'lỗi … cuối' != 'lỗi Ab3dEf6hIj9lMn2pQr5 cuối'`; GREEN cả module `Ran 113 tests … FAILED (errors=42)` (cả 42 là `QueryDeadlockError`, phiên khác chạy cả app cùng lúc), 42 tên chạy lại `Ran 43 tests … OK`.
- Phát hiện mới (blocker/major): không có.

### Không kiểm được từ diff → tech-lead
- Phán round 75 có trong `tasks.md` (commit `a3848b0`, sau BASE của review).
- Dòng `:2746` xanh: xem kết quả `cmd.test` cả app sau merge `fad39a3` trong `tasks.md`.

### Deferred (cho designer)
- Chữ "dòng chỉ gồm từ bị che + rỗng → `""`" của phụ lục 4 lệch với QĐ-D1 bước 2–3 (cho `… … …`); dev theo QĐ-D1.
- Chỉ che `Cc`; ký tự định dạng (`Cf`, ví dụ U+200B) có thể cắt một token thành các đoạn < 20.
- Trong test hook của T48, commit hỏng ở khóa ref nên dòng cuối có thể là lỗi của git dù hook có chạy hay không; các phép `NotIn` ở vòng lặp đó có thể yếu (có từ trước phần này).
