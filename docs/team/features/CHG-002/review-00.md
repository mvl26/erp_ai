Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 00 — CHG-002 T0

- Diff: `git diff a689b8d..203c7f0` (nhánh `team/CHG-002-task-0`, đã merge vào `team/CHG-002` ở `dd444ad`)
- Vòng: 1 (max_rework = 3)
- Verdict: approve

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| — | — | — | 0 blocker, 0 major | — |

minor | — | — | 0 điểm nhỏ | tùy dev

## Review checklist (10)
1. Đạt. Mọi giá trị task nêu đều có assert: mã thoát 0, `diff-tree … HEAD` = `D\tmyapp/a.py`, `ls-files` rỗng, file staged khác vẫn staged, in phiên bản git; thêm kiểm `HEAD~1` là HEAD cũ. Không sửa mã sản phẩm.
2. Đạt. Một file, đúng touchpoint `erp_ai/agent/changes/test_process_runner.py`; không file mới.
3. Đạt. Test đặc tả: xanh ngay lần đầu là kết quả hợp lệ (đầu `tasks.md`). Không skip/xfail/only.
4. Đạt. Mỗi test một repo tạm của `GitSandbox`, gỡ bằng `addCleanup`; `git_env` bỏ HOME và cấu hình global.
5. Đạt. Không có mã sản phẩm đổi; assert mang `outcome.output`.
6. Đạt. Không bí mật, không chạm `protected_paths`.
7. Đạt. Hợp đồng không đổi.
8. Đạt. Tên theo profile; `print` là yêu cầu của tiêu chí.
9. Đạt. Không thêm phụ thuộc.
10. Đạt. Commit `test(changes): … (CHG-002)`, không dòng AI; nhánh `team/CHG-002-task-0`.

## Ghi chú của reviewer
- Tiêu chí ghi cả "`status --porcelain` rỗng" lẫn "file staged khác vẫn staged"; hai câu không cùng đúng theo nghĩa đen. Test kiểm `status --porcelain -- myapp/a.py` rỗng và toàn bộ status đúng bằng `A  myapp/staged.py`: cách đọc chặt nhất khớp cả hai.

## Không kiểm được từ diff, tech-lead đã xử lý
- Reviewer không chạy test: dev `Ran 18 tests in 0.116s` / `OK` (module `erp_ai.agent.changes.test_process_runner`; 17 test ở nền + 1 mới); sau merge `cmd.test` trên `team/CHG-002` @ `dd444ad`: `Ran 1565 tests in 504.679s` / `FAILED (failures=6)`, đúng 6 test của dòng `baseline:` (nền: 1564 test, cùng 6 test đỏ).
- Lint: dev chạy `pre-commit run --files erp_ai/agent/changes/test_process_runner.py`, mọi hook Passed hoặc Skipped.
- Kết quả chỉ ghim cho git 2.43.0 (phiên bản test in ra); runner có git khác phải chạy lại test này.

## deferred
- Không có.
