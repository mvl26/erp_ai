Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 37 — CHG-002 T37

- Diff: `git diff 238544c..09cf681` trên `team/CHG-002-task-37` (1 commit, 3 file, +389/−37); `238544c` = `git merge-base team/CHG-002 team/CHG-002-task-37`
- Vòng: 1 (max_rework = 3)
- Verdict: **design-defect** ở vòng 1 → DỪNG T37, nhánh giữ lại, CHƯA merge, CHƯA tick; chờ designer phán

## Vòng 1 — design-defect, kèm 1 major sửa được (`git diff 238544c..09cf681`)

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| design-defect | STD-DESIGN-1 | `erp_ai/agent/changes/apply_job.py:1059-1068` (và `_Stop` ở `:1046`, `:1057`, chỗ bỏ `after`) | khối có cả mục file lẫn lệnh: dòng nhật ký áp dụng nhận `value_after = {exit_code, duration_ms, output}`; dict `{"commit","branch","files"}` mà `design.md` §6 dòng 673 đòi bị mất, vì `record_commit` không ghi dòng nhật ký nào nên dict đó không nằm ở dòng nào. Ba nguồn ràng buộc không cùng đúng được trong touchpoint: §6; Returns của T37 (`exit_code`, `duration_ms`, `command_output` của lệnh cuối, cần `result=`); hợp đồng T15 của `transitions.finish` (`transitions.py:411-413`, `_git_values` ở `:289`) từ chối `result` đi cùng `after`. Dev tự chọn một bên thay vì dừng `DESIGN_CONFLICT` | designer chọn: (a) cho `finish` nhận cả các giá trị lệnh lẫn `after` (mở lại T15, thêm `transitions.py` vào touchpoint, dòng nhật ký lưu dict commit cùng `command_results`); hoặc (b) sửa §6 cho khối có lệnh. Sau đó thêm test ghim `value_before` / `value_after` của dòng áp dụng cho khối có mục và lệnh, ở cả đường thành công lẫn đường dừng |
| major | STD-ERR-1 | `erp_ai/agent/changes/apply_job.py:138-141` (gọi ở `:122`) | `_log_counts` chạy sau khi trạng thái cuối đã commit, không có `try`; nó gọi `operations_of` / `commands_of`, hai hàm này ném `ValueError` hoặc `JSONDecodeError` khi `command_list` không đọc được. `_recheck_block` (`:316-319`) gọi cùng hai hàm và `_run_in_lock` cố ý đổi lỗi đó thành `Lỗi`; đúng ở job đó `run_change` lại ném lần nữa: dòng logger duy nhất của bước 12 không được ghi, job vỡ sau khi đã có kết quả. `_post_result` ngay trên có chắn ca này (suspected: chỉ tới được nếu một đề xuất như vậy được đưa vào hàng đợi) | bọc phần đếm, ghi `-` cho ba giá trị như `_post_result`; thêm test: đề xuất có `command_list` không đọc được kết `Lỗi` và vẫn ghi đúng một dòng `erp_ai change` |

minor | — | — | 3 điểm nhỏ: `test_apply_job.py:2993` còn ghi áp dụng đưa khối có lệnh tới `OP_UNKNOWN` (nay sai, đường vòng không còn cần); không có test "còn dưới 1 s trước lệnh 1 sau commit" (`last is None`, `_Stop` không có kết quả); lỗi bất ngờ từ `run_bench` ở khối chỉ có lệnh rơi vào `except` chung và mất `command_results` đã gom | tùy dev

Tầng 1: các tiêu chí khác đạt (lệnh chạy đúng thứ tự đã lưu, bỏ `restart`; mỗi lệnh nhận phần ngân sách còn lại; dưới 1 s thì không chạy; lệnh j lỗi hoặc quá giờ thì dừng, giữ sha và file; các giá trị đơn là của lệnh cuối đã chạy; dòng logger thêm `ops` / `commands` / `restart`; AC-54 phủ bởi `TestOneApproval`). Nhánh `OP_UNKNOWN` của T36 đã gỡ (`apply_job.py:250`); khối rỗng vẫn bị `BLOCK_EMPTY` chặn sớm hơn (`change_guard.py:463`). Không gì khởi chạy `restart`.

Phán về bốn điểm dev nêu: (1) còn dưới 1 s: nhận (khớp bước 9, Returns, P7-6). (2) `value_after` giữ kết quả lệnh cuối: design-defect ở trên. (3) cách đếm của logger: nhận (bước 12 không nói `commands=` có tính `restart` không). (4) comment ở `test_apply_job.py:2992`: cũ, minor.

`test_apply_job.py` ngoài touchpoint: được phép theo luật `tasks.md` dòng 19; chỉ đổi giá trị ghim, giữ kiểu so; 4 dòng `test-shape:` và 1 dòng `test-input:` khớp diff (L-1: 4, L-2: 1).

Bằng chứng của dev: RED (trước khi viết mã) `Tuples differ: ('Lỗi', 'loại mục phải là edit, create, delete hoặc rename') != ('Lỗi', 'lệnh 2 (bench --site miyano clear-cache): lệnh trả mã 3')`, `[0.5 s left] Lists differ: [] != [['--site', 'miyano', 'clear-cache']]`, `Ran 55 tests` / `FAILED (failures=8)`; GREEN `test_apply_block` `Ran 55` / `OK`, `test_apply_job` `Ran 117` / `OK`, `test_block` `Ran 10` / `OK`, `test_architecture` `Ran 195` / `OK`. Số đo `bench build` chưa lấy: tech-lead dời sang T51 (không chạy build trên site dùng chung khi phiên FEAT-007 đang test).

## Review checklist (10)
1 trượt (STD-DESIGN-1, dòng nhật ký §6) · 2 đạt · 3 đạt · 4 đạt · 5 trượt (STD-ERR-1) · 6 đạt · 7 đạt (hợp đồng `finish` được giữ, chính vì thế mới có design-defect) · 8 đạt (1 comment cũ) · 9 đạt · 10 đạt.

## Không kiểm được từ diff (tech-lead CHƯA xử lý, để lại cho lượt sau cùng phán quyết)

- Có đề xuất nào với loại lạ hoặc `command_list` hỏng tới được `run_change` không (xác nhận major): cần đọc các chỗ `enqueue`.
- `BlockApplyTestCase` có vá `frappe.db.commit` (có, xem `review-36.md` vòng 1 phát hiện 2); phép so thứ tự `db_commits_at` với `recorded_at` dựa vào `call_count`.
- Có chỗ nào ngoài diff đọc `value_after` của dòng áp dụng và chờ `commit` / `files` (đường hoàn tác, màn hình kiểm toán): quyết định giữa (a) và (b), việc của designer.
- Module trên `09cf681`: tech-lead chưa chạy lại (chỉ có GREEN của dev).

## Điểm chờ phán (gửi team-leader, 21:30)

Câu hỏi cho designer: dòng nhật ký áp dụng của khối có cả mục file lẫn lệnh mang gì ở `value_after`, ở đường thành công và ở đường dừng giữa chừng (lệnh j lỗi hoặc quá giờ)? (a) mở lại hợp đồng `transitions.finish` của T15 để nhận cả hai; (b) sửa `design.md` §6 cho khối có lệnh. Sau phán quyết: một lần gọi dev trên `team/CHG-002-task-37` làm cả phần phán quyết lẫn major STD-ERR-1, rồi re-review vòng 2.
