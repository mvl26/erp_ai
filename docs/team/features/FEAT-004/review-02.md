Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 02 — FEAT-004 T2

- Diff: `git diff cb40420..team/FEAT-004-task-2` (1 commit `b359384`, 3 file, +103)
- Vòng: 1
- Verdict: approve

## Phát hiện (chỉ blocker/major)
Không có.

minor | — | — | 2 điểm nhỏ: `test_transitions.py:76` kiểm `.endswith(".invalid")` thừa vì dòng trên đã so cả địa chỉ; `test_transitions.py:63-64` không phân biệt được công thức với số 540 gõ tay | tùy dev

## Review checklist (10)
1–4 đạt; 5 không áp dụng (chỉ hằng số); 6–10 đạt.

## Bằng chứng của dev
- RED: `ImportError: cannot import name 'BOT_GIT_EMAIL' from 'erp_ai.constants'`
- GREEN: `Ran 4 tests in 0.003s` / `OK`; lint `pre-commit run --files` sạch

## Không kiểm được từ diff (tech-lead xử lý)
- Tên hằng có trùng hằng của FEAT-005 không: FEAT-005 chưa có trên nền; kiểm lúc `/team:plan FEAT-005 --insert` → deferred.
- `cmd.test` sau merge: xem dòng tick trong `tasks.md`.

## deferred
- Đối chiếu tên hằng với FEAT-005 khi build FEAT-005.
