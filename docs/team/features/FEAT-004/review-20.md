Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 20 — FEAT-004 T20

- Diff: vòng 1 `git diff 7e90e5e..25be823 -- erp_ai/agent/changes/` (mã nhận từ ngoài quy trình); vòng 2 `git diff beef39e..f90ed31` (1 commit, 2 file, +449/-63; nhánh `team/FEAT-004-task-20` xếp chồng trên T45 đã approve)
- Diff vòng 3: `git diff f90ed31..d6a885c` (cả task: `git diff beef39e..d6a885c`)
- Vòng: 3 (max_rework=3)
- Verdict: approve (vòng 3)

## Vòng 3 — approve (`git diff f90ed31..d6a885c`, 1 commit, 2 file)
- Phát hiện vòng 2 (STD-DESIGN-2): ADDRESSED (`apply_job.py:219`: dòng hash đã lưu và dòng xem trước thông điệp commit chỉ chạy khi `action == ACTION_APPLY`; hoàn tác giữ người chạy `undo_by`, role, digest, bộ chặn với `(proposal.app,)`, không kiểm công tắc)
- Phía áp dụng vẫn đủ 7 dòng của bảng 4.3 theo thứ tự; test áp dụng không nằm trong diff
- Test mới đỏ được khi dòng tương ứng chạy lại ở hoàn tác: `test_undo_does_not_rebuild_the_commit_message_preview` (`test_apply_job.py:1633`), `test_undo_does_not_recheck_the_stored_content_after_hash` (`:1645`), `test_undo_guard_allows_only_the_proposal_app` (`:1663`); thêm kiểm `_undo_code` không được gọi khi kiểm lại từ chối (`:1617`)
- Phát hiện mới: không có blocker/major
- Bằng chứng của dev: RED `('Lỗi', 'nội dung đề xuất đã bị sửa sau khi duyệt') != ('Đã hoàn tác', None)`, `('Lỗi', 'nội dung lưu không khớp dấu') != ('Đã hoàn tác', None)`, `Ran 80` / `FAILED (failures=2)`; xóa dòng bộ chặn của kiểm lại một lần: `[guard refusal] Expected '_undo_code' to not have been called. Called 1 times.`; GREEN `Ran 80 tests in 83.081s` / `OK`
- Không kiểm được từ diff: `apply_job.py:215` `settings` không gán khi hoàn tác một đề xuất không phải code (sẽ `NameError`); `request_undo` (T14, review-14) chỉ nhận `Thay đổi code` ở `Đã áp dụng` nên đường này không tới được; ghi cho T47 thêm một test ghim

## Vòng 1 — request-changes (review C, mã nhận về)

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-SEC-4 | erp_ai/agent/changes/apply_job.py:112-115 | Đường hoàn tác bỏ qua kiểm `session.user == undo_by`, role và digest | chạy cùng các kiểm lại, không kiểm công tắc |
| major | STD-DESIGN-2 | erp_ai/agent/changes/apply_job.py:233,243-244 | Kiểm sau không có kiểm blob (`content_before` hoặc `None`) và nhánh; chưa xử lý QĐ-B2; khóa nhật ký `hash` thay vì `sha256/head/commit/branch` | như T19 |

Test của Expect đủ 6 nhưng yếu: `test_undo_refused_when_file_changed_after_apply` không kiểm 0 commit; `test_undo_new_file_removes_from_disk_and_tree` không chứng minh đường dẫn rời cây.

## Vòng 2 — request-changes (`git diff beef39e..f90ed31`)
- Phát hiện 1: ADDRESSED (`apply_job.py:192-217`; người chạy là `undo_by`; role, digest, bộ chặn `read_git=False`; không kiểm công tắc; mỗi dòng có subTest riêng trong `test_undo_rechecks_fail_without_writing`, cùng `test_undo_checks_the_undoer_not_the_approver`, `test_undo_allowed_with_switch_off`)
- Phát hiện 2: ADDRESSED (`apply_job.py:302-332`, `532-552`; `_postcheck` dùng chung: cha, tổ tiên, đường dẫn, nhánh, blob; lỗi đọc theo QĐ-B2 giữ `undo_commit_sha`, không trả lại; khóa QĐ-B5; mỗi điều kiện một subTest)
- Test yếu: ADDRESSED (kiểm 0 commit cho cả file sửa và file mới; `ls-tree`, `ls-files`, `--name-status D`)
- Câu mong đợi bị đổi: không vi phạm STD-TEST-5 (`file đã đổi sau khi áp dụng, không hoàn tác` trùng `design.md:667`)

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-DESIGN-2 | erp_ai/agent/changes/apply_job.py:224-233 | Khi hoàn tác, `_recheck` chạy cả dòng "bản xem trước thông điệp commit" của 4.3 bước 4.2; design 4.4 bước 2 chỉ nêu người hoàn tác, role, digest, bộ chặn. Dòng này dựng lại `apply_message(...)` từ mã hôm nay và so với `commit_message` lưu lúc duyệt: đổi `change_text.apply_message` hay `APPROVER_PLACEHOLDER` về sau sẽ chặn hoàn tác mọi đề xuất đã áp dụng trước đó, với lý do sai `nội dung đề xuất đã bị sửa sau khi duyệt`; commit hoàn tác không dùng `commit_message`; không test nào phủ dòng này ở hoàn tác | chỉ chạy dòng này khi `action == ACTION_APPLY`, hoặc designer thêm vào 4.4 bước 2 kèm test hoàn tác |

minor | — | — | 6 điểm nhỏ: hoàn tác cũng chạy `sha256(content_after) == after_hash` (`apply_job.py:219-221`), vô hại nhưng ngoài 4.4 bước 2; bộ chặn được gọi hai lần cùng đối số (`:209`, `:504`), subTest "bộ chặn từ chối" vẫn xanh khi xóa dòng kiểm lại; kiểm sau dùng `state.branch` (đúng ADR-022 QĐ 6) nhưng chưa test nào phân biệt với `target_branch`; `allowed_apps = (proposal.app,)` ở `:203` chưa được ghim; `settings` không gán ở nhánh lệnh khi hoàn tác (`:215`, không tới được); câu từ chối role của hoàn tác dùng lại `người duyệt không còn quyền` | tùy dev

## Review checklist (10)
Đã phủ 10/10.

## Bằng chứng của dev
- Vòng 2 RED: `Ran 76 tests … FAILED (failures=21, errors=6)`, vd `('Đã hoàn tác', None) != ('Lỗi', 'sai người chạy job')`, `{'hash': …} != {'sha256': …}`, `30 != 5`; GREEN `Ran 77 tests in 80.232s` / `OK`

## Không kiểm được từ diff (tech-lead xử lý)
- `commit_message` và `ticket` có thuộc 14 trường của digest không: `tasks.md` T13 ghi digest gồm `commit_message` (14 trường theo design 2.3); `ticket` có hay không thì tech-lead chưa đọc được trong phiên này → ghi cho vòng 3.

## deferred
- T47: từ chối git trước khi ghi hoàn tác, kiểm tổ tiên (`GIT_NOT_ANCESTOR`, `GIT_ERROR`), commit hoàn tác lỗi còn trả lại mà không kiểm `git_head == old_head` (cùng lỗi blocker của T45, phía hoàn tác).
- Cho designer: câu từ chối role riêng cho người hoàn tác; dòng `after_hash` ở hoàn tác.
