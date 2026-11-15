Feature: CHG-002
Stage: build
Author-agent: reviewer
Date: 2026-11-15
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 08 — CHG-002 T8

- Diff: `git diff 349560d..b52edfa` (nhánh `team/CHG-002-task-8`, 2 commit `8068f1f` + `b52edfa`, 2 file)
- Vòng: 2 (max_rework = 3)
- Verdict: **approve** ở vòng 2 → merge `cde391b`, tick

## Vòng 1 — request-changes (`git diff 349560d..8068f1f`)

major | STD-DESIGN-2 | erp_ai/agent/changes/process_runner.py:175 | Chỉ bắt `(subprocess.TimeoutExpired, OSError)`; thân commit tự ghi "other errors propagate". design.md:338 ghi "không bao giờ ném lỗi", tasks.md T8 ghi "không ném lỗi"; nơi gọi ở T38 dựa vào đó (ném lỗi thì `record_restart` không chạy, `restart_status` rỗng ngoài bốn giá trị của ADR-040 QĐ 7). Docstring `:162` thu hẹp lời hứa của thiết kế. | `except Exception as error: return False, type(error).__name__`; sửa docstring thành "never raises".

major | STD-TEST-5 | erp_ai/agent/changes/test_process_runner.py:685-687 | `test_error_outside_the_design_list_is_not_swallowed` ghim hành vi trái design.md:338 và không có trong Expect. | Viết lại thành `test_unlisted_error_returns_class_name`: `ValueError` → `(False, "ValueError")`, thêm ca `SubprocessError`.

minor | — | — | 2 điểm nhỏ (xem deferred) | tùy dev

Đạt ở vòng 1: `RESTART_ARGV` đúng A-5; tham số `run()` đúng §3.4:335; `(True, None)` khi thoát 0; tên lớp lỗi cho `FileNotFoundError`, `TimeoutExpired`, `OSError`; mã thoát khác 0 trả `"CalledProcessError"` (reviewer phán: đủ chữ §3.4:337, không phải design-defect); không test nào chạy `bench restart` thật.

Bằng chứng của dev (vòng 1): RED `AttributeError: … no attribute 'RESTART_ARGV'`, `… no attribute 'launch_restart'`, `Ran 26 tests in 0.292s` / `FAILED (errors=13)`; GREEN `test_process_runner` `Ran 26 tests in 0.337s` / `OK`, `test_architecture` `Ran 185 tests in 25.349s` / `OK`.

## Vòng 2 — approve (`git diff 8068f1f..b52edfa`, +12/−5)

1. ADDRESSED | STD-DESIGN-2 | `process_runner.py:175`: `except Exception as error: return False, type(error).__name__`; docstring `:162` "Never raises: any error returns (False, <error class name>)…". `KeyboardInterrupt` / `SystemExit` vẫn truyền lên (không phải lớp con của `Exception`).
2. ADDRESSED | STD-TEST-5 | `test_process_runner.py:685-694`: `test_unlisted_error_returns_class_name` với hai subtest (`ValueError`, `SubprocessError`), mỗi cái kiểm `run.assert_called_once()`.

Lỗi mới trong các dòng đổi: không.

Bằng chứng của dev (vòng 2): RED `subprocess.SubprocessError: popen failed`, `ValueError: embedded null byte`, `Ran 26 tests in 0.200s` / `FAILED (errors=2)`; GREEN `test_process_runner` `Ran 26 tests in 0.198s` / `OK`, `test_architecture` `Ran 185 tests in 15.189s` / `OK`.

## Không kiểm được từ diff (tech-lead đã xử lý)

- `setsid -f` trên máy thật có trả 0 ngay sau fork không (util-linux 2.39.3, ADR-040:61): không kiểm trong build (lệnh giao cấm `bench restart`); ghi cho qa ở bước nghiệm thu (điểm mở trong báo cáo lượt 4).
- T38, T47 có dựa vào hành vi truyền lỗi không: T47 (đã merge) chỉ kiểm hình dạng tĩnh; T38 stub `launch_restart` (đưa vào lệnh giao T38).
- Module và cả app sau merge: dòng progress của T8 trong `tasks.md` (đợt merge 13, `0499815`).

## deferred

1. Khi mã thoát khác 0, `returncode` bị bỏ, log chỉ có `CalledProcessError`.
2. Thân commit `8068f1f` còn câu "other errors propagate" (đã bị `b52edfa` thay; không viết lại lịch sử).
