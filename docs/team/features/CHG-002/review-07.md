Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 07 — CHG-002 T7

- Diff: `git diff 7967ec7..a192233` (nhánh `team/CHG-002-task-6`, 1 commit `a192233`, 5 file, +156/−34)
- Gói: T6 + T7 cùng nhánh, một reviewer chấm cả gói; verdict của T6 ở `review-06.md`
- Vòng: 1 (max_rework = 3)
- Verdict: **approve** → merge `98b0e5c` (cùng T6), tick

## Vòng 1 — approve

Phát hiện blocker/major: không.

minor | — | — | 2 điểm nhỏ (xem deferred) | tùy dev

Lớp 1 (khớp đặc tả): đủ tiêu chí.
- Chữ ký `git_commit_only(repo_root, rels: tuple[str, ...], …)`.
- `_check_commit_rels` đòi tuple khác rỗng, từng phần tử qua `_check_git_rel` (tách từ `_check_git_write_call`), từ chối đường dẫn trùng.
- argv kết thúc `"--", *sorted(rels)`; `add` và `rm` truyền `(rel,)`; hai lời gọi trong `apply_job.py` truyền `(rel,)`.
- Luật kiến trúc: commit nhận 1..N đường dẫn sau `--`, spread chỉ được sau `--`; `add` / `rm` đúng 1 đường dẫn, không spread.
- 3 dòng `test-shape:` khớp `L-1: 3`; `test_change_decision.py` không bị sửa.

Đột biến trong đầu của reviewer: bỏ `sorted`, bỏ kiểm trùng, nới kiểm tuple (ca list), bỏ vòng kiểm từng phần tử (11 ca "second element"), commit chỉ đường dẫn đầu, cho `add` nhận N đường dẫn, ép commit về đúng 1 → mỗi cái có test đỏ.

Bằng chứng của dev: RED `test_process_runner`: `ValueError: rel must be a plain relative file path inside the repo: ('myapp/a.py', …)`, `FAIL: test_empty_or_duplicate_rels_refused [rels a string]` / `AssertionError: ValueError not raised` / `Ran 21 tests in 0.281s` / `FAILED (failures=1, errors=27)`; RED `test_architecture` `Ran 185 tests in 25.382s` / `FAILED (failures=7)`; GREEN `test_process_runner` `Ran 21 tests in 0.354s` / `OK`, `test_architecture` `Ran 185 tests in 24.539s` / `OK`, `test_apply_job` `Ran 117 tests in 208.040s` / `OK`, `test_change_decision` `Ran 10 tests in 18.792s` / `OK`, `test_apply_block` `Ran 1 test in 1.904s` / `OK`.

Review checklist (10): 10/10 đạt.

## Không kiểm được từ diff (tech-lead đã xử lý)

- Đích đổi tên phải được `git add` trước commit (`commit --only` từ chối đường dẫn chưa theo dõi; §8.0 chỉ ghi "c.py (mới, đã add)"): không phải thiếu sót của T7. Việc add đích đổi tên thuộc bước ghi của khối (T35, §4.2 bước 6; `arch-preflight-1.md` hàng T35: `git_add_new` từng đường dẫn); tech-lead đưa câu này vào lệnh giao T35, T36.
- Luật kiến trúc không đọc được bên trong spread sau `--`, nên phép chặn pathspec magic `:` cho commit nhiều đường dẫn chỉ còn lúc chạy (`_check_git_rel`, có ca test "starts with :"); §8.2 không đòi kiểm tĩnh. Ghi để architect biết (điểm mở trong báo cáo lượt 4), không chặn T7.
- Reviewer không chạy test. Module sau merge trên `team/CHG-002` @ `98b0e5c`: xem `review-06.md`.
- Cả app của đợt merge: dòng progress của T7 trong `tasks.md`.

## deferred

1. `git_commit_only` kiểm `rels[0]` hai lần (`_check_commit_rels` rồi `_check_git_write_call`).
2. Ca `"rels a string"` không ghim phép kiểm tuple (phần tử `.` vẫn bị luật đường dẫn bắt); ca list đã đủ.
