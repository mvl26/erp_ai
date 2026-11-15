Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 24 — CHG-002 T24

- Diff: `git diff 990d7b3..120873f` (nhánh `team/CHG-002-task-24`, 2 commit `df35ac6` + `120873f`, 3 file)
- Vòng: 1 của đề bài theo `arch-ruling-3.md` = ADR-040 C-4 (max_rework = 3); lần gọi dev đầu (round 27) dừng `DESIGN_CONFLICT`, chưa từng review
- Verdict: **approve** → merge `98f31cb`, tick

## Vòng 1 — approve

Phát hiện blocker/major: không. Minor: 0.

Lớp 1 (khớp đặc tả): đủ tiêu chí, chỉ ba file touchpoint.
- Mọi nhánh trả khóa `status` (không ở `Đã gửi`, `restart_sent_at` rỗng, không có kết luận, `False`, có kết luận); không `dict(...)`, không khóa là biến, không dict gán dần; luật ADR-012 không đổi; `transitions.py` không bị sửa.
- `_decider(name)` chạy đầu tiên, đúng hàm của `approve` / `reject` / `undo`; không có luật quyền thứ hai.
- P-4: đọc `restart_status` và `restart_sent_at` một lần; `outcome` tính từ đúng `restart_sent_at` đó; giá trị đã đọc truyền vào `sent_at=`.
- `False` → đọc lại `restart_status`, không ghi logger; logger `erp_ai restart proposal=%s status=%s` chỉ khi ghi được.
- Hai ca ghim thêm vào `shapes` đúng từng chữ của `arch-ruling-3.md`.

Đột biến trong đầu của reviewer: bỏ điều kiện trạng thái, bỏ chặn `restart_sent_at` rỗng, bỏ nhánh `value is None`, trả sai giá trị ở nhánh `False`, đọc lại mốc gửi trước khi ghi, kiểm quyền tại chỗ thay `_decider` → mỗi cái có test đỏ. Biên hạn (`== RESTART_TIMEOUT_S` chưa kết luận, `+1` → `Chưa xác nhận`) được ghim; `now_datetime` được vá.

Bằng chứng của dev: lần gọi 1 (`df35ac6`) RED (với stub) `Ran 41 tests` / `FAILED (failures=25)`; GREEN `test_erp_ai_change_proposal` `Ran 41 tests in 29.274s` / `OK`, `test_change_decision` `Ran 10 tests in 9.006s` / `OK`, `test_transitions` `Ran 76 tests in 31.863s` / `OK`. Lần gọi 2 (`120873f`) RED `AssertionError: {'name': 'AICHG-00001', 'restart_status': 'Đã xác nhận'} != {'name': 'AICHG-00001', 'status': 'Đã xác nhận'}`, `Ran 41 tests in 60.717s` / `FAILED (failures=14)`; GREEN `test_erp_ai_change_proposal` `Ran 41 tests in 60.996s` / `OK`, `test_architecture` `Ran 184 tests in 25.040s` / `OK`, `test_transitions` `Ran 76 tests in 56.920s` / `OK`, `test_change_decision` `Ran 10 tests in 18.859s` / `OK`.

Review checklist (10): 10/10 đạt.

## Không kiểm được từ diff (tech-lead đã xử lý)

- Lint (dòng import của controller ~98 ký tự): dev báo `pre-commit run --files` trên ba file, mọi hook `Passed` hoặc `Skipped`; `cmd.lint` cả cây chạy lại ở cuối lượt / T51.
- `design.md:326` và `design-addendum-1.md:124` còn chữ `{"name", "restart_status"}`: `arch-ruling-3.md` đã giao designer đưa vào addendum sau; `tasks.md` đã ghi C-4 thắng.
- T25 phải đọc `r.message.status`: đã ghi vào Returns và Expect của T25 và vào lệnh giao T25 (round 32).
- Reviewer không chạy test. Module và cả app sau merge: dòng progress của T24 trong `tasks.md` (đợt merge 11, `349560d`).

## deferred

Không có.
