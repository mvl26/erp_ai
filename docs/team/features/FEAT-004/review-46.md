Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 46 — FEAT-004 T46

- Diff: vòng 1 `git diff 7e90e5e..25be823 -- erp_ai/agent/changes/` (mã nhận từ ngoài quy trình); vòng 2 `git diff 9de6b69..2276fa8` (1 commit, 2 file, +119/-19; nhánh xếp chồng trên T19 đã approve)
- Vòng: 2 (max_rework=3)
- Verdict: approve

## Vòng 1 — request-changes (review C, mã nhận về)

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-DESIGN-2 | erp_ai/agent/changes/apply_job.py:47-55,132 | `GIT_MOVED_REASONS` đưa `index.lock`, HEAD detached, `MERGE_HEAD`, file bị ignore, `.git` mất, đích bẩn về `Hết hiệu lực`; ADR-022 QĐ 7 và T46 ghi `Lỗi`, chỉ đổi nhánh là `Hết hiệu lực` | từ chối git → `Lỗi`; chỉ ca nhánh là `Hết hiệu lực` |

Thiếu test của Expect: `test_git_precheck_fails_at_apply_without_write_or_commit` (5 subTest), `test_index_lock_fails_fast`. Từ review T19: `read_git_state` chưa có `limit_s`; `BRANCH_CHANGED` chưa là chữ `GIT_BRANCH_CHANGED` của bảng 3.2.

## Vòng 2 — approve (`git diff 9de6b69..2276fa8`)
- Phát hiện 1: ADDRESSED (`apply_job.py:323-324` mọi `state.refusal` kết thúc `Lỗi`; `GIT_MOVED_REASONS` đã bỏ; chỉ ca nhánh ở `:326-327` là `Hết hiệu lực`)
- Test thiếu: ADDRESSED (`test_apply_job.py:326-364` đủ 5 subTest, mỗi ca kiểm `Lỗi` + đúng câu viết tay, không ghi, không add, không commit, file nguyên, các bước `["approve","fail"]`; `:366-383` xong dưới `GIT_TIMEOUT_S`, tệp khóa còn; test nhánh `:210-227` kiểm đầu `main` và `other` không đổi, cây sạch, `["approve","stale"]`)
- `limit_s` và chữ nhánh: ADDRESSED (`apply_job.py:323` `limit_s=_git_limit(deadline)`, ghim bằng test 30 / 5 / 1; `GIT_BRANCH_CHANGED` ở `:55` trùng design dòng 364)
- STD-TEST-5: hai test đổi sang tên của Expect, thân một test không đổi; một câu mong đợi đổi theo bảng 3.2
- Phát hiện mới: không có

minor | — | — | 2 điểm nhỏ: docstring `_git_limit` (`apply_job.py:250`) còn nói "git write"; test giới hạn patch `time.monotonic` cả tiến trình | tùy dev

## Review checklist (10)
Đã phủ 10/10.

## Bằng chứng của dev
- RED: `('Hết hiệu lực', 'kho git đang bị khóa (index.lock)…') != ('Lỗi', …)` và cùng kiểu cho detached, `MERGE_HEAD`, bị ignore sau, gỡ `.git`; `'…đã đổi từ lúc đề xuất' != '…đã đổi kể từ lúc đề xuất'`; `AssertionError: None != 30`, `None != 5`, `None != 1`
- GREEN: `Ran 46 tests in 31.930s` / `OK`

## Không kiểm được từ diff (tech-lead xử lý)
- subTest `spent=COMMAND_TIMEOUT_S+50` khẳng định `Đã áp dụng` cả khi đã quá hạn: ghim một điểm design chưa chốt cho nhánh code (`limit < 1` → "quá thời gian" mới chốt cho lệnh bench, phụ lục 2 QĐ-A3) → ghi deferred cho designer; assertion này phải đổi khi design chốt.

## deferred
- Cho designer: hết ngân sách thời gian ở nhánh code (xem trên).
- T45/T47: `git_add_new`, `git_unstage_new` và commit hoàn tác còn dùng `GIT_TIMEOUT_S` không theo `deadline`.
