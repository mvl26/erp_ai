Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 08 — FEAT-004 T8

- Diff: `git diff 3aa363f..team/FEAT-004-task-8` (2 commit `9b2a7fc`, `4f2996b`; 2 file)
- Vòng: 2 (max_rework=3)
- Verdict: approve (vòng 1: request-changes)

## Vòng 1 — request-changes (`git diff 3aa363f..9b2a7fc`)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-8 | erp_ai/agent/tools/change_guard.py:47-50,57-58 (test: test_change_guard.py:182) | ba nhánh `return None` của `_git_common_dir` quyết định "không phải erp_ai" (bộ chặn cho ghi) mà không có test: tệp `.git` có dòng đầu không phải `gitdir:`, lỗi đọc/giải mã tệp `.git`, `commondir` có nhưng không đọc được | thêm ca: `.git` là tệp chữ rác; tệp byte không phải UTF-8; `gitdir:` trỏ thư mục quản trị có `commondir` là thư mục; mỗi ca trả `None` không raise |

minor | — | — | 3 điểm nhỏ: (a) `:78-82` dò mọi `.git` tổ tiên tới `/`; (b) `:45-46` `readline()` không giới hạn cỡ, không kiểm loại tệp; (c) `:51` `gitdir:` tương đối tính từ thư mục realpath | tùy dev

## Vòng 2 — approve (re-review theo phạm vi, `git diff 9b2a7fc..team/FEAT-004-task-8`)
- Phát hiện 1: ADDRESSED (`test_unreadable_git_pointer_leads_to_no_repo_without_raising`, dòng `junk`, `binary`, `dircommon`, `huge`)
- Ba điểm minor (a), (b), (c): dev sửa cả ba, mỗi điểm có test đỏ trên mã cũ
- Phát hiện mới: không có blocker/major

minor | — | — | 2 điểm nhỏ: giới hạn 4096 byte của `_first_line` không phải giới hạn của git (nghi là 1 MiB trong `setup.c`), chú thích `change_guard.py:12-13,39` nói sai; `os.path.getsize` (`:42`) nằm ngoài `try` | tùy dev

## Review checklist (10)
1–10 đạt sau vòng 2.

## Bằng chứng của dev
- Vòng 1 RED: `Ran 16 tests in 0.044s` / `FAILED (failures=24)`, ví dụ `AssertionError: None != 'không được sửa app erp_ai hoặc kho git của nó'`; GREEN: `Ran 16 tests in 0.034s` / `OK`
- Vòng 2 RED mẫu: `ERROR (app='junk') ValueError: junk`, `FAIL (app='dircommon') AssertionError: '/tmp/.../apps/erp_ai/.git' is not None`; GREEN: `Ran 20 tests … OK`; lint sạch

## Không kiểm được từ diff (tech-lead xử lý)
- `test_running_erp_ai_package_repo_refused` mới chạy trong worktree (`.git` là tệp); bố cục `.git` là thư mục (cây chính, CI) chưa có bằng chứng chạy → deferred cho qa (chạy `cmd.test_one` từ cây chính sau khi nhánh được checkout ở đó).
- Test đó đòi gói `erp_ai` đang chạy là một checkout git: CI cài app không có `.git` thì đỏ → deferred cho devops.

## deferred
- Con trỏ `.git` 4 KiB–1 MiB được git chấp nhận nhưng bộ chặn coi là "không phải repo" (minor vòng 2): ghi vào As-Built/debt.
