Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 25 — CHG-002 T25

- Diff: `git diff 349560d..857800b` (nhánh `team/CHG-002-task-25`, 3 commit `7aa851c` + `42a4c90` + `857800b` (rỗng, chỉ mang thân), 2 file)
- Vòng: 2 (max_rework = 3)
- Verdict: **approve** ở vòng 2 → merge `3e1cddd`, tick

## Vòng 1 — request-changes (`git diff 349560d..7aa851c`)

blocker | STD-TEST-5 | commit `7aa851c` (thân) | Dev khai "L-1: 3" (ba subtest của `test_form_script_static_rules` bị sửa: `:1495`, `:1529`, `:1623`) nhưng thân commit có 0 dòng `test-shape:`; addendum-2 L-1 điểm 5 đòi mỗi test một dòng. Sửa thứ ba còn đổi kiểu so từ `assertIn` sang `assertEqual` đếm (L-1 điểm 3 "giữ kiểu so"). | Thêm một commit (không viết lại lịch sử) có ba dòng `test-shape:` đúng mẫu.

minor | — | — | 3 điểm nhỏ (xem deferred) | tùy dev

Đạt ở vòng 1: `undo_allowed` phủ `Đã áp dụng` và `Lỗi` có `apply_commit_sha` mà chưa có `undo_commit_sha`, cả hai đòi `Thay đổi code`; hộp xác nhận nêu số mục, dòng "Lệnh trong khối không hoàn tác được" khi có lệnh; `confirm_restart` gọi từ `onload`, chỉ khi `Đã gửi` && `has_role("ERP AI Instructor")`, callback đọc `r.message.status` (ADR-040 C-4), so với `frm.doc.restart_status`, khác mới `frm.reload_doc()`; không `frappe.realtime`, không `open_doc:`. `_condition_holds` đánh giá chính biểu thức JS thật, mỗi điều kiện có subtest phủ định riêng.

Bằng chứng của dev (vòng 1): RED `test_calls_confirm_restart_only_when_sent`: `AssertionError: 0 != 1`; `test_confirm_restart_called_only_for_instructor` ×4 `condition not found in the form script`; `Ran 46 tests in 55.840s` / `FAILED (failures=10)`; GREEN `test_erp_ai_change_proposal` `Ran 46 tests in 65.940s` / `OK`, `test_architecture` `Ran 185 tests in 19.891s` / `OK`.

## Vòng 2 — approve (`git diff 7aa851c..857800b`, 1 file, +3/−1)

- ADDRESSED | STD-TEST-5 | thân commit mới nhất `857800b` có đủ ba dòng `test-shape:`; tên subtest khớp đúng `subTest(rule=…)` ở `:1495`, `:1527`, `:1619`; `:1628` trở lại `assertIn`, phép đếm `assertEqual(…, 2)` ở `:1630` là assertion thêm, khớp `undo_confirm_message` (`.js:60-73`). `42a4c90` ghi sai tên subtest thứ ba; `857800b` sửa lại, không viết lại lịch sử.

Lỗi mới trong các dòng đổi: không.

Bằng chứng của dev (vòng 2): không có RED (chỉ trả kiểu so, mã sản phẩm không đổi); GREEN `test_erp_ai_change_proposal` `Ran 46 tests in 29.357s` / `OK`, `test_architecture` `Ran 185 tests in 14.839s` / `OK`.

## Không kiểm được từ diff (tech-lead đã xử lý)

- `test_form_diff_covers_every_item` chỉ chứng minh form giữ nguyên `diff` đã lưu (helper test dựng `diff`); việc tool gộp đủ mọi mục thuộc T26: Expect của T26 đã ghi `test_edit_and_create_block_one_proposal_rows_in_order` so trường `diff` của bản ghi cha bằng đúng chuỗi gộp (lệnh giao T26, round 38).
- `onload` chạy một lần cho mỗi tài liệu trong một phiên trang; mở lại form trong cùng phiên mà không tải lại trang thì không kiểm restart lần nữa, còn design §4.4 bước 5 ghi "khi form được mở". CHƯA xử lý được ở build (cần trình duyệt thật / designer): điểm mở trong báo cáo lượt 4, giao qa thử ở bước nghiệm thu.
- `confirm_restart` ném lỗi cho Instructor (ví dụ `NEVER_AUTHORITY`) thì hiện hộp lỗi mặc định của Frappe: quyền kiểm ở server (T24 đã tick), ngoài diff này.
- Module và cả app sau merge: dòng progress của T25 trong `tasks.md` (đợt merge 13, `0499815`).

## deferred

1. `.js:62-66`: đề xuất khối một mục sẽ đọc "Hoàn tác khối 1 mục?"; thiết kế không có câu cho ca này.
2. `test_erp_ai_change_proposal.py:1647`: `_undo_shown` luôn truyền vai trò Instructor mà điều kiện hoàn tác không đọc.
3. Dòng `test-shape:` thứ nhất không nêu tên subtest cũng đổi; chú thích `:1529` dài 142 byte.
