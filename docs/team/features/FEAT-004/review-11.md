Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 11 — FEAT-004 T11

- Diff: `git diff 5f65835..team/FEAT-004-task-11` (1 commit `54871b2`; 3 file, +418/−15)
- Vòng: 1 (max_rework=3)
- Verdict: approve

## Vòng 1 — approve
Không có blocker/major.

minor | — | — | 2 điểm nhỏ: (a) `test_architecture.py:633` docstring ghi mọi lời gọi của `process_runner` "có hình dạng bọc timeout" nhưng luật chỉ kiểm `start_new_session`/`cwd`/`env` (design dòng 935 chỉ đòi ba thứ đó, nên chỉ là câu chữ); (b) `process_runner.py:82` thiếu chương trình `timeout` (`FileNotFoundError`) cũng đặt `not_found`, nên T21 sẽ hiện "không tìm thấy bench" | tùy dev

## Review checklist (10)
1–10 đạt. `run_bench` đúng hình dạng design 4.3; kiểm quá giờ (mã diệt và thời gian ≥ hạn) có ca ở cả hai vế, biên 120.0 và 119.9; `127 → not_found`; cắt 399 + 1 dòng, mỗi dòng ≤ 1000 ký tự; `ENV_ALLOWLIST` và `OUTPUT_MAX_LINES = source.READ_MAX_LINES` đúng tasks.md; không có `bench_runner.py` (D-12); chưa có hàm git ghi (T43). Luật kiến trúc đổi đúng design dòng 935; assertion FEAT-006 không đổi (STD-TEST-5), `ENTRY_TYPES_EXPECTED` không đụng.

## Bằng chứng của dev
- RED: `test_process_runner` `FAILED (failures=19, errors=3)`, vd `test_output_cut_to_400_lines: AssertionError: 1001 != 400`; `test_architecture` `FAILED (failures=17)`
- GREEN: `test_process_runner` `Ran 12 tests … OK`; `test_architecture` `Ran 100 tests … OK`; lint sạch
- Sau merge `9580564`: `cmd.test` `Ran 1016 tests in 169.982s` / `OK`

## Không kiểm được từ diff (tech-lead xử lý)
- `timeout -s KILL` có diệt tiến trình con của bench không: `timeout` của coreutils (không `--foreground`) tự lập nhóm tiến trình và gửi tín hiệu cho cả nhóm; chỉ kiểm bằng mock ở task này, chạy thật ở T21/T22. Không phải thiếu sót của T11.
- Backstop của Python chỉ diệt tiến trình `timeout`: đúng phác thảo D-3, là lựa chọn của design.
- `cmd.test` sau merge: đã chạy, xanh (dòng trên).

## deferred
- Câu hỏi design cho T21 (designer sửa trước T21): design 4.3 bước 4 tính `limit = max(0, int(deadline − now))`; `run_bench` ném `ValueError` khi `limit_s` ngoài 1..540 (đúng, vì `timeout -s KILL 0` là không giới hạn) → hết hạn thì đề xuất thành `Lỗi` với lý do `ValueError` thay vì "quá thời gian" (AC-10). Sửa: `limit < 1` → `Lỗi` "quá thời gian" trước khi gọi `run_bench`, hoặc `max(1, …)` như git.
