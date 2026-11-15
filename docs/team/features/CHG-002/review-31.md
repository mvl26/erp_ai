Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 31 — CHG-002 T31

- Diff: `git diff fd69e5f..f2fa5a1` (nhánh `team/CHG-002-task-31`, 1 commit, còn giữ, CHƯA merge)
- Diff vòng 2 (lượt 3, sau `design-addendum-5.md` P-2): `git diff a6a6560..8697aad` (cả task sau khi dev merge `team/CHG-002` vào nhánh, 2 file, +217)
- Vòng: 2 (max_rework = 3)
- Verdict: vòng 1 **design-defect** → tech-lead dừng T31, báo team-leader; vòng 2 **approve** → merge `5f418c1`, tick (xem "Vòng 2" cuối file)

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-8 | erp_ai/agent/changes/result_comment.py:119-126 (từ design.md:400) | Thiết kế cho phép khối chỉ có lệnh `["restart"]` (design.md:316, R-5; R-6 ở design.md:75); §4.2 bước 11 chạy §4.4, tức gửi comment này. Khối đó không có commit: `apply_commit_sha` rỗng, `applied_branch` null, `app` có thể rỗng (design.md:161). Comment sẽ thành "commit  trên nhánh None của app None …" và bảo người chạy `git -C apps/None revert --no-edit ` (không sha). §3.7 và RQ-4 không có câu chữ cho ca này, dev không tự sửa được | Designer thêm vào §3.7 một biến thể cho khối không có commit (ví dụ "Đề xuất {tên} đã áp dụng: {m} lệnh bench. Hệ thống sắp restart bench. Nếu site không lên sau vài phút: chạy `bench restart`."), hoặc phán khối chỉ có lệnh không gửi comment trước restart; rồi T31 thêm ca và test |

minor | — | — | 3 điểm nhỏ (xem deferred) | tùy dev

Mã khớp AC-46 (b) như §3.7 và A3 RQ-4 viết: chữ đúng từng ký tự (sha 12 ký tự ở câu đầu, sha đủ trong lệnh `revert`), `undo` dùng `undo_commit_sha` và chữ "hoàn tác", cùng lời gọi `add_comment(COMMENT_TYPE_INFO, text)` như `post_result`, dưới user phiên, không `set_user`, không mở đầu bằng `kết quả đề xuất`, lỗi ghi thì `log_error` và trả `None`, không đọc `upstream_ref`.

## Điểm mở do dev nêu: "0 lần `publish_realtime`" (A3 RQ-4 dòng 84)
- Test `test_info_comment_session_user_not_result_prefix` patch cả `frappe.publish_realtime` và `frappe.realtime.publish_realtime`, assert danh sách lời gọi đúng bằng `[("doc_update","Comment",row.name), ("list_update",None,None)]`; một lời phát riêng nào thêm cũng làm test đỏ.
- "0 lần" theo nghĩa đen không đạt được ở Frappe 15.126.1: `add_comment` tạo và `insert` Comment trong một biểu thức (frappe/model/document.py:1619-1629); mọi `insert` chạy `notify_update` (document.py:1341-1343, 1375-1385) phát `doc_update` và `list_update`; `Comment.notify_change` chỉ phát `docinfo_update` cho Like, Assigned, Comment, Attachment, không cho Info (comment.py:85-97).
- Test có sẵn `test_post_result_publishes_no_realtime` (test_result_comment.py:265-286) ghim đúng hai sự kiện đó.
- Chấm: không phải lỗi của diff; là câu chữ thiếu chính xác của thiết kế, không chặn. Designer nên sửa A3 RQ-4 dòng 84 và dòng Expect của T31 thành "0 lời gọi của riêng nó; chỉ còn `doc_update`/`list_update` của Frappe cho Comment mới".

## Review checklist (10)
1. Đạt về diff so với thiết kế; thiết kế thiếu ca khối không có commit (major trên).
2. Đạt. Đúng 2 file touchpoint.
3. Đạt. RED `AttributeError`, `errors=7` (6 test mới, một test có 2 subTest); GREEN `OK`.
4. Đạt. Test cũ không đổi.
5. Đạt. `except` rộng có ghi lý do trong docstring, log tên đề xuất, hành động, lớp lỗi (thiếu rollback: minor 3).
6. Đạt. Không đọc `upstream_ref`; có `escape_html`; token, host, `://`, `@`, `.git` gieo sẵn đều được assert vắng mặt cho cả hai hành động.
7. Đạt. Chỉ thêm; `post_result`, `result_lines` chưa đụng (T32).
8. Đạt.
9. Đạt.
10. Đạt. `feat(changes): … (CHG-002)`, không dòng AI.

## Không kiểm được từ diff
- Chưa chạy cả app (nhánh chưa merge).
- T38: nơi gọi có gửi comment, commit DB rồi mới khởi chạy, và bỏ qua khi không có `restart` hay không.
- T49: luật AST 0 `publish_realtime` ở `result_comment.py`.
- Khối chỉ có lệnh có được điền `app`, `applied_branch` hay không: tùy cách designer phán điểm major.

## deferred
1. `result_comment.py:121`: test đặt `applied_branch` và `target_branch` cùng giá trị, nên bỏ nhánh dự phòng vẫn xanh.
2. `:138`: trong ba điều kiện chặn chỉ "không có ticket" có test.
3. `:142`: `except` không rollback hay savepoint; `add_comment` lỗi sau INSERT thì nơi gọi vẫn commit Comment trong khi Error Log nói ghi thất bại (`apply_job._post_result:123` thì rollback trước khi log) — nghi vấn.

## Vòng 2 — approve (lượt 3, `git diff a6a6560..8697aad`)
- Phát hiện major STD-TEST-8 (`result_comment.py:119-126`, khối không có commit ra "commit  trên nhánh None của app None"): ADDRESSED. `result_comment.py:123-129` chọn sha của hành động; sha `None` hoặc `""` → mẫu không commit của addendum-5 P-2 đúng từng ký tự, không đọc `app`, nhánh; ghim bởi `test_command_only_apply_notice_has_no_commit_branch_app`, `test_undo_without_commit_notice_text` (mỗi test chạy cả `None` và `""`). Chữ khi có commit không đổi so với `f2fa5a1`.
- Test thêm ngoài lệnh giao `test_apply_without_commit_comment_on_ticket`: reviewer nhận (ca duy nhất bắt lỗi "lấy sha nào có" thay vì sha của hành động).
- `test_info_comment_session_user_not_result_prefix`: assertion giữ nguyên, chỉ đổi docstring và chú thích theo câu RQ-4 mới.
- Blocker/major mới: không.
- Bằng chứng của dev: RED `FAIL: test_command_only_apply_notice_has_no_commit_branch_app … (sha=None)` (`Ran 15 tests in 6.556s` / `FAILED (failures=6)`); GREEN `test_result_comment` `Ran 15 tests in 7.309s` / `OK`, `test_architecture` `Ran 179 tests in 14.094s` / `OK`.
- Review checklist (10): 10/10 đạt.

### Không kiểm được từ diff (tech-lead đã xử lý hoặc chuyển tiếp)
- Cả app sau merge (đợt 6, `5f418c1`): `Ran 1645 tests in 519.329s` / `FAILED (failures=6)`, đúng 6 test của dòng `baseline:`.
- Lint: dev báo `pre-commit run --files` trên 2 file qua mọi hook; `cmd.lint` cả cây chạy ở T51.
- T38 (nơi gọi gửi notice đúng 1 lần cho khối chỉ có `["restart"]`, commit DB trước khi khởi chạy) và T49 (luật AST 0 `publish_realtime`): thuộc Expect của hai task đó, chưa tới.

### deferred (vòng 2)
Ba điểm deferred của vòng 1 còn mở (addendum-5 mục 4: tùy dev).
