Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 45 — FEAT-004 T45

- Diff: vòng 1 `git diff 7e90e5e..25be823 -- erp_ai/agent/changes/` (mã nhận từ ngoài quy trình); vòng 2 `git diff 2276fa8..cddfd0e` (1 commit, 2 file, +660/-59; nhánh xếp chồng trên T46 đã approve); vòng 3 `git diff cddfd0e..beef39e` (1 file test)
- Vòng: 3 (max_rework=3)
- Verdict: approve

## Vòng 1 — request-changes (review C, mã nhận về)

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| blocker | STD-ERR-7 | erp_ai/agent/changes/apply_job.py:146-147 | `give_back()` chạy mà không kiểm `git_head == old_head` trước (D-17); git báo lỗi hoặc quá giờ nhưng commit đã vào thì job ghi `content_before` đè lên file đã commit; với file mới, `git rm --cached` stage việc xóa một đường dẫn đã commit; không lưu mã commit | đọc `git_head` trước; theo cây quyết định của T45 |
| major | STD-ERR-1 | erp_ai/agent/changes/apply_job.py:172-176 | `give_back` bỏ qua kết quả `git_unstage_new` và hash của `write_atomic`; không kiểm HEAD hay `read_git_state` nên `GIT_RESTORE_FAILED` không bao giờ xảy ra | kiểm từng bước |
| major | STD-DESIGN-2 | erp_ai/agent/changes/apply_job.py:151 | `parents != (git.head,)` là phép so chặt mà Sửa vòng 2 cấm | `len(parents)==1 and git_is_ancestor(old_head, parents[0]) is True` (đã làm ở T19) |
| major | STD-ERR-7 | erp_ai/agent/changes/apply_job.py:98-108 | Exception sau khi ghi và trước commit để `content_after` nằm trên đĩa; không có cờ `committed` (QĐ-B2 mục 4) | bọc riêng việc trả lại, chỉ khi `committed is False` |

Thiếu gần hết test của Expect (chỉ có ca commit lỗi cho file sửa và file mới).

## Vòng 2 — request-changes (`git diff 2276fa8..cddfd0e`)
- Blocker: ADDRESSED (`apply_job.py:436-450` `_commit_landed` đọc `git_head` trước; `None` → `GIT_ERROR` không trả lại; bằng → trả lại; đã dịch → đọc tóm tắt: không đọc được → `GIT_ERROR`; không phải bot → trả lại so với `head_now`, không lưu mã; là bot → kiểm sau; cờ `committed` chặn trả lại khi đã biết commit của bot)
- Major `give_back`: ADDRESSED (kiểm kết quả unstage, hash đọc lại bằng `base_hash`, `git_head == expected_head`, `read_git_state().refusal`; sai hay exception → `GIT_RESTORE_FAILED`, có test)
- Major exception: ADDRESSED (`apply_job.py:391-396`)
- Test thiếu: ADDRESSED (đủ 11 test của Expect và phụ lục 3, cùng test đọc lại sai cho file sửa và file mới, trả lại thất bại, đầu ra dài, `add` lỗi)
- NFR-8: đạt (`author_email` chỉ được so; `log_error` chỉ ghi tên đề xuất và tên lớp lỗi; `assert_no_human_email_stored` kiểm trên dòng nhật ký thật không rỗng và đề xuất)
- Câu mong đợi bị đổi (STD-TEST-5): được phép; chữ cũ không khớp bảng 3.2 (`design.md:366`)

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-8 | erp_ai/agent/changes/test_apply_job.py:638, apply_job.py:440 | Nhánh D-17 "HEAD == old_head → trả lại" không test nào ghim: HEAD nền của mọi fixture không phải commit của bot nên xóa dòng 440 thì nhánh "tác giả ≠ bot" cho cùng kết quả | subTest có HEAD nền là commit của bot rồi commit lỗi với HEAD không đổi |

minor | — | — | 4 điểm nhỏ: `apply_job.py:362` lỗi `git add` báo là "commit git lỗi…"; `git add` quá giờ thì `added` vẫn False nên không unstage; `write_atomic` ở dòng 355 nằm ngoài khối canh (có từ trước); `_give_back_after_crash` thiếu chú thích kiểu của `old_head` | tùy dev

## Vòng 3 — approve (`git diff cddfd0e..beef39e`)
- Phát hiện vòng 2: ADDRESSED (`test_apply_job.py:978-1010` `test_commit_failed_on_top_of_an_earlier_bot_commit_restores`: HEAD nền là commit của bot từ một lần áp dụng thật trước đó, không giả; kiểm `author_email()==BOT_GIT_EMAIL`; hai subTest file sửa và file mới; file được trả lại, đúng câu, HEAD không đổi, cây sạch, không `apply_commit_sha`, các bước `["approve","fail"]`)
- Phát hiện mới: không có

## Review checklist (10)
Đã phủ 10/10.

## Bằng chứng của dev
- Vòng 2 RED (23/62 ca đỏ trước khi sửa mã): `('Lỗi', 'git commit lỗi, file đã được trả lại như cũ') != ('Lỗi', 'không đọc được trạng thái git')`; `… != ('Đã áp dụng', None)`; `None != '7c91f53…'`; `'x = 2…' != 'x = 1…'`; GREEN `Ran 62 tests in 48.701s` / `OK`
- Vòng 3 RED (xóa dòng 440–441 một lần rồi bỏ): `FAILED (failures=2)`, `('Lỗi', 'commit không đúng nội dung đã duyệt, cần người kiểm') != ('Lỗi', 'commit git lỗi, đã trả file về như trước: fatal: lỗi giả')`; GREEN `Ran 63 tests in 76.987s` / `OK`

## Không kiểm được từ diff (tech-lead xử lý)
- `core.hooksPath` và môi trường git có giữ đầu ra của hook (có thể chứa email) khỏi dòng cuối đầu ra commit không: T48 (đang đỗ) kiểm 6 hook không chạy; ghi cho T48 thêm phép kiểm `failure_reason`.
- Commit đầu của `GitSandbox` có cha không: test của module xanh trên fixture đó (dòng GREEN).

## deferred
- Cho designer (không chặn): lý do ngắn lưu vào `failure_reason` là dòng cuối của đầu ra git (`<GIT_COMMIT_FAILED>[ (quá thời gian)]: <dòng cuối>`, ≤ 120 ký tự, theo design 3.5 dòng 468); dòng đó có thể mang đường dẫn tuyệt đối của máy chủ (vd lỗi `index.lock`) → STD-ERR-3; design cần nói cách làm sạch.
- T47: đường hoàn tác nay báo `GIT_COMMIT_FAILED` kèm dòng git mà chưa có test; hoàn tác còn truyền `result` nên đầu ra git lưu vào `command_output`; trả lại ở hoàn tác chưa kiểm HEAD.
