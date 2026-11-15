Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 35 — CHG-002 T35

- Diff: `git diff 9dae095..0fd89db` trên `team/CHG-002-task-35` (2 commit `5e3fdb0`, `0fd89db`; 2 file, +573/−4); nhánh xếp chồng trên T34, `9dae095` là merge `team/CHG-002` vào nhánh task
- Vòng: 2 vòng sửa (max_rework = 3), thêm một lần chấm lại toàn bộ ở lượt 5
- Verdict: **approve** → merge `9b0422b` (sau T34), tick

Ghi chú về nguồn: verdict của vòng 1 và vòng 2 nằm trong phiên build lượt 4, phiên đó bị cắt khi máy khởi động lại lúc 17:38 trước khi file này được viết. Hai vòng đó chép lại từ các dòng `round 43`, `round 44`, `round 45` của `tasks.md`. Vì không còn bản verdict nào trên đĩa, lượt 5 gọi một reviewer mới chấm lại toàn bộ từ commit; phần dưới là kết quả của lần chấm đó.

## Vòng 1 — request-changes (`5e3fdb0`, round 44)

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-8 | `test_apply_block.py` | năm điều kiện của "trả lại trọn" không có ca riêng | mỗi điều kiện một ca cô lập |

## Vòng 2 — approve (`0fd89db`, round 45)

1/1 ADDRESSED (`0fd89db` chỉ có test).

## Chấm lại toàn bộ ở lượt 5 — approve (`git diff 9dae095..0fd89db`)

Tầng 1 (đúng đặc tả): đạt.
- Thứ tự ghi: `_write_item` theo bảng §4.2 bước 6, theo `idx`; `test_give_back_reverse_order_with_kind_arguments` ghim dãy lời gọi và đối số của cả chiều ghi lẫn chiều trả.
- Trả lại: đổi tên trả bằng `write_atomic(nguồn, before, new_file=True)` rồi `remove_file(đích)`; `git_add_new` / `git_unstage_new` từng đường dẫn, gỡ theo thứ tự ngược; chỉ bốn hàm của `file_writer`, không thêm hàm.
- Lý do lỗi `ghi mục k (path) lỗi, đã trả mọi file về như trước` so với câu viết tay.
- Đủ 5 test Expect, gồm A-3.3 `TestDelete::test_parent_swapped_to_symlink_after_check_zero_deleted_outside`.
- Năm điều kiện "trả lại trọn" mỗi điều kiện một ca trong `test_each_give_back_check_alone_reports_restore_failed`.

Phát hiện blocker/major: không.

minor | — | — | 3 điểm nhỏ: (a) `apply_job.py:382-384` `git add` quá thời gian sau khi đã stage thì đường dẫn không vào `staged`, không được gỡ, job vẫn báo "đã trả mọi file về như trước" (STD-ERR-7, nghi ngờ); (b) `apply_job.py:223-224` nhánh `_run` khi trả lại sau ghi trọn bị hỏng không có test (tạm tới T36); (c) `read_git_state` ở bước trả lại dùng hạn mặc định, không dùng `_git_limit(deadline)` | tùy dev

## Review checklist (10)
1 đạt · 2 đạt (chỉ hai touchpoint) · 3 đạt (không có RED của dev trong gói; test đỏ khi bỏ hành vi; không skip) · 4 đạt · 5 đạt · 6 đạt · 7 đạt · 8 đạt · 9 đạt · 10 đạt (`type(scope): … (CHG-002)`, không dòng AI).

## Không kiểm được từ diff (tech-lead đã xử lý)

- Module trên `0fd89db` sau `migrate` (một lần giữ khóa 18:28–18:34): `test_apply_block` `Ran 27 tests in 27.849s` / `OK`, `test_apply_job` `Ran 117 tests in 142.455s` / `OK`, `test_architecture` `Ran 195 tests in 16.258s` / `OK`.
- Sau merge `9b0422b` (19:36–19:42): `test_apply_block` `Ran 28 tests in 28.021s` / `OK`, `test_apply_job` `Ran 117 tests in 135.214s` / `OK`, `test_block` `Ran 10` / `OK`, `test_architecture` `Ran 195` / `OK`.
- Cả app, đợt merge 17, `team/CHG-002` @ `c44bf86` (19:42–19:53): `Ran 1853 tests in 619.227s` / `FAILED (failures=6)`, đúng 6 test của dòng `baseline:`.
- Quyền thực thi của file: file Xóa và nguồn Đổi tên có bit thực thi bị từ chối từ lúc đề xuất (`change_guard.EXECUTABLE_FILE`, T12 và T27), nên đường trả lại bằng `write_atomic(new_file=True)` không gặp file có bit x qua tool. CHƯA kiểm: `check_block(at_apply=True)` có xét lại bit x cho đề xuất đã lưu hay không; ghi thành điểm mở cho T43 (test nghiệm thu "không lọt khóa") và báo cáo lượt 5.
- Thứ tự merge: T35 merge sau T34 (`b8451bc` rồi `9b0422b`).

## deferred

1. minor (a) ở trên: mục chỉ mục còn sót sau `git add` quá thời gian. Chuyển cho T43 (git an toàn sau áp dụng) xem xét.
2. minor (b), (c) ở trên.
