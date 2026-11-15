Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 23 — CHG-002 T23

- Diff: vòng 1 `git diff 2e2b9ad..cce6675` (cả task sau khi dev merge `team/CHG-002` vào nhánh, 3 file, +333/−3); vòng 2 (sửa) `git diff cce6675..c85fe54` (2 file, +12/−2); nhánh `team/CHG-002-task-23`
- Vòng: 2 (max_rework = 3)
- Verdict: vòng 1 request-changes; vòng 2 **approve** → merge `990d7b3`, tick
- Lần gọi dev đầu (build lượt 2, round 7) trả `DESIGN_CONFLICT` (`psutil`, `redis` đụng luật ADR-001), chưa review; phán ở `arch-ruling-2.md` Phán quyết 2 = ADR-040 C-3.

## Vòng 1 — request-changes

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-8 | erp_ai/agent/changes/test_restart_check.py:58 | Hai `except` hẹp ở `restart_check.py:36` (`except psutil.Error`) và `:44` (`except NO_EVIDENCE_ERRORS`) chỉ được test bằng lỗi nằm trong bộ (`ConnectionError`, `NoSuchProcess`, `AccessDenied`). Đổi một trong hai thành `except Exception` thì cả 7 test và module kiến trúc vẫn xanh, trong khi ADR-040 C-3 nêu đúng phép đổi đó là lý do của ngoại lệ `redis` ("che cả lỗi lập trình, làm 'không có bằng chứng' thành bằng chứng sai") | Mỗi hàm thêm một lỗi ngoài bộ phải lan ra: `patch(GET_WORKERS, side_effect=ValueError("bug"))` + `assertRaises(ValueError)` trên `workers_started()`; `patch.object(restart_check.psutil, "Process", side_effect=ValueError)` + `assertRaises` trên `web_started()`. Chỉ sửa test |

minor | — | — | 4 điểm nhỏ (xem deferred) | tùy dev

Lớp 1 (khớp đặc tả): hợp đồng `outcome` / `epoch_*` / `web_started` / `workers_started` đúng Returns (A-6); `NAMED_LIBRARY_IMPORTS`, phần đổi của `check_import_boundaries`, `check_restart_check_library_use` và mọi ca tự kiểm của `arch-ruling-2.md` "Luật kiến trúc" có đủ; `ALLOWED_TOP_LEVEL_MODULES`, nhánh `anthropic` và khối luật `file_writer` không đổi; hai file T23 không đổi so với `ad729a7`. Mỗi điều kiện của `check_restart_check_library_use` có một ca chỉ nó bắt.

Lựa chọn của dev (vi phạm "file không còn" kiểm trên đĩa `PACKAGE_ROOT / rel`, không kiểm trong `sources`): reviewer nhận, không phải lỗi (ở lần chạy thật `sources` nạp từ cùng `PACKAGE_ROOT`; cả hai biến thể sai đều có ca bắt; đã ghi trong docstring).

Bằng chứng của dev: lần gọi 1 RED (stub) `Ran 7 tests` / `FAILED (failures=7)`, GREEN `Ran 7 tests in 0.006s` / `OK`; lần gọi 2 RED trên luật chưa sửa `FAIL: test_layer_imports — 'agent/changes/restart_check.py:12: imports psutil, not stdlib/frappe/helpdesk/erp_ai (ADR-001: no other app or library)'`, RED của ca tự kiểm với stub `Ran 184 tests` / `FAILED (failures=25)`; GREEN `test_architecture` `Ran 184 tests in 14.538s` / `OK`, `test_restart_check` `Ran 7 tests in 0.005s` / `OK`.

## Vòng 2 — scoped re-review (`cce6675..c85fe54`), approve

- Phát hiện 1: ADDRESSED. `test_restart_check.py:75-82` `test_programming_error_is_not_no_evidence` (`ValueError` từ `get_workers` phải lan ra khỏi `workers_started()`; `ValueError` từ `psutil.Process` phải lan ra khỏi `web_started()`); RED bằng đột biến: `:36` → `except Exception`: `FAIL: test_programming_error_is_not_no_evidence ... AssertionError: ValueError not raised`, `Ran 8 tests` / `FAILED (failures=1)`; `:44` → `except Exception`: cùng dòng đỏ. `restart_check.py` không đổi.
- Minor dev nhận sửa: dòng `outcome(SENT, BEFORE_DEADLINE, SENT + 2, SENT)` ghim phép `>` chặt ở phía worker; `RESTART_CHECK_FILE`, `RESTART_CHECK_LIBRARIES` suy ra từ `NAMED_LIBRARY_IMPORTS` (hết chữ lặp).
- Blocker/major mới từ diff sửa: không.
- GREEN sau sửa: `test_restart_check` `Ran 8 tests` / `OK`, `test_architecture` `Ran 184 tests` / `OK`.
- Review checklist (10): 10/10 đạt.

## Không kiểm được từ diff (tech-lead đã xử lý hoặc chuyển tiếp)

- Module sau merge trên `team/CHG-002` @ `990d7b3` (một lần giữ khóa 09:57–09:59, `cmd.migrate` thoát 0): `test_restart_check` `Ran 8 tests in 0.006s` / `OK`, `test_architecture` `Ran 184 tests in 14.289s` / `OK` (gồm `test_layer_imports`, test đã đỏ ở lượt 2, và khối luật `file_writer` của T5 sau khi hai nhánh gặp nhau).
- Cả app sau merge (đợt 10, `990d7b3`, một lần giữ khóa 10:02–10:11 gồm `cmd.migrate` thoát 0): `Ran 1704 tests in 516.395s` / `FAILED (failures=6)`, đúng 6 test của dòng `baseline:`.
- Lint: dev báo `pre-commit run --files` trên 3 file qua mọi hook; `cmd.lint` cả cây chạy ở T51.
- Python 3.10 (CI): reviewer đọc cú pháp, không thấy tên nào chỉ có từ 3.11; chỉ job CI cho thấy được → ghi vào T51.
- Bằng chứng web trên site dev: `web_started` đọc `os.getppid()`; dưới supervisor đó là gunicorn master, dưới `bench start` / werkzeug thì tiến trình cha là tiến trình khác. Đây là giả định của design §4.4, đo sau G4 → báo team-leader.

## deferred

1. `check_restart_check_library_use` không bắt phương thức được tham chiếu mà không gọi (`k = p.kill; k()`) hay `getattr(psutil, "process_iter")`; phán quyết chỉ nêu lời gọi và tham chiếu thuộc tính.
2. Các ca tự kiểm dùng `sources` rút gọn của `check_import_boundaries` nay phụ thuộc việc `restart_check.py` có trên đĩa (đã ghi trong docstring).
