Feature: FEAT-007
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 75 — FEAT-007 T75

- Diff: `git diff 2aeb6f6..121186e` (nhánh `team/FEAT-007-task-75`; 2 commit `02bff19` test, `121186e` mã; 6 file +72/−9, đều là touchpoint)
- Vòng: 1 (trần `max_rework` = 3)
- Verdict: approve; merge `232ff4f` trên `team/FEAT-007`
- File này do tech-lead ghi từ báo cáo của reviewer (vai reviewer không ghi file dưới `docs/`); chữ của reviewer giữ nguyên ý, finding giữ nguyên văn.
- Trái nhịp, ghi rõ: merge `232ff4f` (13:17:54) có TRƯỚC file này. Lần review đầu của round 101 chạy trong một ngữ cảnh skill build tách riêng; ngữ cảnh đó kết thúc khoảng 13:18 mà không trả báo cáo, nên verdict của lần đó không còn. Bản dưới đây là lần review gọi lại ở round 102 (reviewer mới, cùng khoảng diff, lời giao không nói task đã merge). Tick T75 chỉ làm sau khi có verdict này và test sau merge xanh.

## Vòng 1 — approve

- Bằng chứng của dev (đưa nguyên văn cho reviewer): RED trên `02bff19`, `MIGRATE_EXIT=0`: `TypeError: enqueue_agent_run() got an unexpected keyword argument 'comment_name'` (3 test), `FAIL: test_comment_mention_without_comment_name_raises (kwargs={}) … AssertionError: ValueError not raised`, `KeyError: 'comment_name'`, `TypeError: run_for_ticket() got an unexpected keyword argument 'comment_name'`; test_queue `Ran 14 tests … FAILED (failures=3, errors=7)`, test_handlers `Ran 32 tests … FAILED (errors=1)`. GREEN, `MIGRATE_EXIT=0` ở mọi lần giữ khóa: test_queue `Ran 14 tests OK`, test_handlers `Ran 32 tests OK`, test_ticket_panel `Ran 36 tests OK`, test_agent_runner `Ran 110 tests OK`, test_architecture `Ran 185 tests OK`; pre-commit exit 0.

Các phép kiểm chính của reviewer:

1. Commit: commit test `02bff19` đứng trước commit mã `121186e`; hai tiêu đề đúng `type(scope): description (FEAT-007)`; không dòng ghi công AI; diff chỉ chạm sáu file của `files:`.
2. Mã sản phẩm: `queue.py:15` đúng chữ ký của `U1.md:211`; `queue.py:18-19` ném `ValueError` trước khi dựng job id hay chạm cờ pending; `job_id` giữ `erp_ai::{ticket}::{trigger}`, `deduplicate=True` giữ, `comment_name=` truyền vào `frappe.enqueue`; `runner.py:115` khớp `U1.md:257`, truyền tên xuống `_run`; `_run` giữ `comment_name=None` mặc định và chưa dùng (T80 dùng), nên lời gọi hai tham số ở `test_runner_status.py:817` còn chạy; `handlers.py:119` truyền `comment_name=doc.name` (`U1.md:212`). Kiểm ngoài diff bằng `git grep` ở `121186e`: nơi gọi `enqueue_agent_run` còn lại là `handlers.py:46` với `ticket_insert`, `ValueError` mới không tới được; mọi nơi gọi `run_for_ticket` khác truyền hai tham số.
3. Test (không thêm dấu skip nào): `test_comment_mention_job_carries_comment_name` và `test_comment_mention_without_comment_name_raises` nằm trong lớp `TestEnqueueAgentRun` (ba dạng rỗng: thiếu, `None`, `""`; kiểm không job nào được xếp và cờ pending không đặt, chữ cờ khớp `PENDING_JOB_IDS_FLAG` ở `queue.py:5`); `test_mention_enqueues_with_comment_name` nằm trong `TestCommentHandler`, đỏ khi trả lại handler cũ. Test thêm: `test_ticket_insert_without_comment_name_enqueues`, lớp `TestRunForTicketCommentName` (cả mặc định `None`).
4. Khẳng định có sẵn bị đổi, chấm theo STD-TEST-5 (không cái nào đổi để khớp hành vi sai): `test_queue.py:23-25` lời gọi `other_trigger` nay truyền `comment_name` (do `ValueError` mới, `U1.md:211`); `test_queue.py:37,49` `test_enqueue_parameters` truyền và chờ `comment_name="COMMENT-1"` (hình dạng enqueue của `U1.md:211`); `test_queue.py:~116` `assert_called_once_with` của `TKT-7` chờ thêm `comment_name=None` (cùng thay đổi spec); `test_handlers.py:308-309` thêm `doc.name` vào setup, không khẳng định nào đổi; `test_ticket_panel.py:732` đúng một dòng như dòng "Chèn 11", không khẳng định nào đổi. Các chỗ khác của `test_queue.py` trong commit mã chỉ là gập dòng của formatter.
5. Lỗi, bảo mật, hợp đồng, tên: phép kiểm đầu vào mới là kiểm ở biên (STD-ERR-2), không thêm `catch`; không bí mật, không đổi hợp đồng, không phụ thuộc mới; không mã chết (tham số `_run` chưa dùng nằm trong spec).

Checklist (10): 10/10 đạt.

Findings: không blocker, không major.

- minor | — | — | 3 small points: (a) the class names in Expect (`TestEnqueue`, `TestCommentHook`) differ from the real ones (`TestEnqueueAgentRun`, `TestCommentHandler`), and dev correctly used the existing classes; (b) `02bff19` was not formatter-clean (lines too long), fixed by the wraps in `121186e`, so STD-STYLE-1 applies to the test commit only; (c) a whitespace-only `comment_name` passes `not comment_name`, which the design ("rỗng", empty) allows | dev's call

Mục "không kiểm được từ diff" của reviewer:

- Reviewer không chạy test; RED và GREEN chỉ có đầu ra của dev.
- Reviewer không kiểm luật lint có bắt tham số `_run` chưa dùng hay không; dev báo pre-commit exit 0.
- Tên lớp ở dòng Expect có phải chỉ là cách viết tắt hay không: để tech-lead xác nhận.
- Ghi chú quy trình: một lệnh `grep` rộng trên `tasks.md` của reviewer in ra vài dòng `progress:` của task khác; reviewer không đọc dòng `progress:` của T75. Reviewer dùng 11/14 lượt.

## Kết luận của tech-lead

- Chạy test: sau merge `232ff4f`, một lần giữ khóa site, `MIGRATE_EXIT=0`: test_queue `Ran 14 tests in 0.011s OK`, test_handlers `Ran 32 tests in 6.253s OK`, test_ticket_panel `Ran 36 tests in 17.580s OK`, test_agent_runner `Ran 110 tests in 29.989s OK`, test_architecture `Ran 185 tests in 16.403s OK`; mọi `TEST_EXIT=0`. Lint: không chạy lại ở tech-lead; `cmd.lint` cả cây thuộc cuối lượt.
- Tên lớp: dòng Expect ghi `TestEnqueue::…`, `TestCommentHook::…`; ba tên test của Expect có đủ, nằm trong lớp có sẵn của hai file. Nhận như hiện có (không tạo lớp trùng mục đích, STD-STRUCT-3); không mở vòng sửa.
- Nhịp merge trước review: xem dòng "Trái nhịp" ở đầu file; đã báo team-leader ở dòng DỪNG lượt 16.

## deferred

- minor (a): chữ tên lớp ở dòng Expect của T75 → As-Built.
- minor (b): commit test chưa qua formatter → ghi chú cho lời giao dev (chạy `cmd.format` trước mỗi commit).
- minor (c): `comment_name` chỉ có khoảng trắng → không việc; thiết kế chỉ nói "rỗng".
