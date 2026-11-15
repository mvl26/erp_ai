Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 32 — CHG-002 T32

- Diff: `git diff 990d7b3..2433431` (nhánh `team/CHG-002-task-32`: `fc01f10` + merge `8fced8d` không mang thay đổi + `2433431`; 2 file, +956/−8)
- Vòng: 1 của đề bài theo `design-addendum-7.md` (max_rework = 3); lần gọi dev đầu (round 21) dừng `DESIGN_CONFLICT`, chưa từng review
- Verdict: **approve** → merge `349560d`, tick

## Vòng 1 — approve

Phát hiện blocker/major: không.

minor | — | — | 1 điểm nhỏ (xem deferred) | tùy dev

Lớp 1 (khớp đặc tả): đủ AC-45 (R-2), AC-49; chỉ hai file touchpoint.
- Chữ ký `result_lines(fields, *, doc=None)`; `_outcome_line` vẫn chạy trước (khối ở trạng thái không phải kết cục vẫn `ValueError`, có test); nhánh khối chỉ khi `doc is not None and block.is_block(doc)`; `post_result` gọi `frappe.get_doc` sau kiểm phiếu và truyền `doc=doc`.
- Nhánh khối chỉ đọc `COMMAND_RESULT_KEYS` của `command_results`, `restart_status`, `app`; không đọc `output`, nội dung file, `diff`, `upstream_ref`; `RESULT_FIELDS` không đổi; `block.py` không nhập `result_comment`.
- P7-1..P7-8 đủ: nhãn `block_label` hoặc `{m} lệnh bench`; tình trạng mục theo hai sha (xét sha hoàn tác trước); lý do in một lần, gắn mục n theo `ITEM_REASON` với biên `1 ≤ n ≤ len`; nhóm 3 hai sha hoặc bỏ; nhóm 4 bỏ ở lượt hoàn tác chưa có commit hoàn tác; nhóm 5 đủ bảy hàng, chỉ đọc `restart_status` ở `Đã áp dụng` / `Đã hoàn tác`; nhóm 6 bốn gợi ý đúng thứ tự, nối `, `, `{site}` = `frappe.local.site`; `RESTART_TIMEOUT_S` nhập, không viết số 11.
- `command_results` hỏng hoặc `restart_status` lạ → `ValueError` đúng chữ addendum. Dạng cũ: sáu hàng ghim qua `post_result`.

Đủ 12 tên test của Expect; M1–M6 và hai biến thể so đúng chuỗi qua `post_result`. Đột biến trong đầu của reviewer (chỉ lấy sha áp dụng cho "đã đổi file", bỏ luật hoàn tác chưa commit, đọc `restart_status` ở mọi trạng thái, `ITEM_REASON` thiếu `ghi` hoặc `\(`, bỏ biên số mục, bỏ `.lower()`, bỏ `new_path`, bỏ điều kiện "chạy xong mã 0", đổi thứ tự nhóm hoặc gợi ý) đều có test đỏ.

Bằng chứng của dev: `fc01f10` (test ghim dạng cũ) xanh trên mã cũ `Ran 16 tests in 7.235s` / `OK`; `2433431` RED 85 lỗi `TypeError: result_lines() got an unexpected keyword argument 'doc'`, 17 failure, `Ran 27 tests in 24.769s` / `FAILED (failures=17, errors=85)`; GREEN `test_result_comment` `Ran 27 tests in 24.856s` / `OK`, `test_architecture` `Ran 184 tests in 24.918s` / `OK`.

Review checklist (10): 10/10 đạt.

## Không kiểm được từ diff (tech-lead đã xử lý)

- Comment hiện `đã gửi` / `lỗi khởi chạy` chỉ khi `post_result` chạy sau `record_restart` và commit DB: là việc của T38, đã ghi vào Returns và Expect của T38 (addendum-7 P7-7, P7-8).
- Comment `Đã hoàn tác` hiện mã thoát của lượt hoàn tác chỉ khi job hoàn tác ghi `command_results` của chính nó: là việc của T40, đã ghi vào Returns và Expect của T40 (P7-6).
- Reviewer không chạy test. Module và cả app sau merge: dòng progress của T32 trong `tasks.md` (đợt merge 11, `349560d`).

## deferred

1. `result_comment.py` `_command_results`: `json.loads(stored or "[]")` ném `TypeError` (không phải `ValueError`) nếu `command_results` đã là list Python trên doc trong bộ nhớ; không xảy ra qua `post_result` (luôn nạp doc từ DB).
