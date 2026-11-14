Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 19 — FEAT-004 T19

- Diff: vòng 1 `git diff 7e90e5e..25be823 -- erp_ai/agent/changes/` (mã nhận từ ngoài quy trình); vòng 2 `git diff db0ce2c..b5b3353`; vòng 3 `git diff b5b3353..9de6b69` (cả task: `git diff db0ce2c..9de6b69`, 2 commit, 2 file)
- Vòng: 3 (max_rework=3)
- Verdict: approve

## Vòng 1 — request-changes (review C, mã nhận về)

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-DESIGN-2 | erp_ai/agent/changes/apply_job.py:151 | Kiểm sau thiếu kiểm nhánh và `git_blob == content_after` (ADR-022 QĐ 1 bước 5); sai thì dùng `COMMIT_UNEXPECTED`, không lưu `apply_commit_sha`; `RuntimeError` của `git_commit_summary` rơi vào đường lỗi chung (QĐ-B2 mục 1) | theo design 4.3 bước 3.5 và QĐ-B2 |
| major | STD-DESIGN-2 | erp_ai/agent/changes/apply_job.py:160-167 | Gọi git trước, dấu file sau, ngược D-19; câu hết hiệu lực không đúng chữ design | dấu file trước khi đọc git; đúng chữ |
| major | STD-DESIGN-2 | erp_ai/agent/changes/apply_job.py:206-207 | Khóa nhật ký `{"hash"}`/`{"hash","commit"}`; QĐ-B5 đòi `before={sha256, head}`, `after={sha256, commit, branch}` | dùng khóa QĐ-B5 |

Thiếu test của Expect: `test_apply_writes_exact_approved_bytes`, phần "1 file staged khác" của `test_apply_creates_one_commit_with_only_target_path`, `test_two_proposals_same_file_second_is_stale`, `test_apply_and_undo_rows_carry_commit_sha` (phần `apply`), `test_postcheck_unreadable_keeps_commit_and_fails`.

## Vòng 2 — request-changes (`git diff db0ce2c..b5b3353`)
- Phát hiện 1: ADDRESSED (`apply_job.py:281-311` `_apply_postcheck`: 1 cha, `git_is_ancestor(...) is True`, `paths == (rel,)`, nhánh, `git_blob == content_after`; bắt `RuntimeError` tường minh; sai → `Lỗi` `GIT_COMMIT_MISMATCH`, không trả lại file, giữ `apply_commit_sha`; dùng `git_is_ancestor` là theo design 4.3 bước 3.5 [vòng 2] và subTest QĐ-B2 của T19, không phải vượt phạm vi)
- Phát hiện 2: ADDRESSED (`apply_job.py:320-326`; `TARGET_CHANGED` đúng chữ design 4.3 bước 3.1)
- Phát hiện 3: ADDRESSED (`apply_job.py:268-278`, `359-375`)
- Test thiếu: ADDRESSED (`test_apply_job.py:292-499`; mỗi điều kiện kiểm sau có ca riêng, 5 subTest)
- Assertion cũ bị sửa ở `test_apply_job.py:186`: được phép, design 4.3 bước 3.1 ghi đúng câu đó

| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-8 | erp_ai/agent/changes/apply_job.py:50,351; test_apply_job.py | Returns mục (3) không có test: câu `WRITE_MISMATCH` đổi thành "đọc lại sau khi ghi không khớp" nhưng không test nào ghim; đặt lại chữ cũ hoặc bỏ nhánh thì test vẫn xanh | test patch `write_atomic` trả hash khác `after_hash`; kiểm `Lỗi`, đúng câu, 0 commit, 1 dòng `fail` |

minor | — | — | 3 điểm nhỏ: `WRITE_MISMATCH` cũng dùng ở hoàn tác (`apply_job.py:395`), design 4.4 không cho chữ, T20 quyết; `test_git_commit_limit_comes_from_the_job_deadline` patch `time.monotonic` cả tiến trình; `_apply_record` vẫn truyền `after` khi không có commit (QĐ-B5 cho phép) | tùy dev

## Vòng 3 — approve (`git diff b5b3353..9de6b69`, 1 file, +21)
- Phát hiện vòng 2: ADDRESSED (`test_apply_job.py:256-275` `test_read_back_hash_mismatch_fails_without_a_commit`; so trạng thái và đúng câu trong một tuple, số commit không đổi, các bước `["approve","fail"]`)
- Phát hiện mới: không có

## Review checklist (10)
Đã phủ 10/10.

## Bằng chứng của dev
- Vòng 2 RED: `'file đã đổi từ lúc đề xuất' != 'file đích đã đổi kể từ lúc đề xuất'`; `{'hash': …} != {'sha256': …}`; `Expected 'read_git_state' to not have been called. Called 1 times.`; `('Đã áp dụng', None) != ('Lỗi', 'commit không đúng nội dung đã duyệt, cần người kiểm')`; GREEN `Ran 42 tests in 30.085s` / `OK`
- Vòng 3 RED (đặt lại chữ cũ một lần rồi bỏ): `AssertionError: Tuples differ: ('Lỗi', 'ghi file không khớp') != ('Lỗi', 'đọc lại sau khi ghi không khớp')`; GREEN `Ran 43 tests in 43.825s` / `OK`, `Ran 43 tests in 28.864s` / `OK`

## Không kiểm được từ diff (tech-lead xử lý)
- Một lần chạy của dev vòng 3 có 1 ERROR ở `test_command_runs_with_the_stored_arguments`, dev không in thông báo. Reviewer: không gì trong diff làm test đó phụ thuộc thứ tự hay trạng thái. Dev T46 chạy lại cả module trên nền này: `Ran 46 tests in 31.930s` / `OK`, test đó xanh → coi là nhiễu site chung; nếu lặp lại thì ghi `docs/team/debt.md` (STD-TEST-7).

## deferred
- T46: nhánh code còn đưa từ chối git về `Hết hiệu lực`; `read_git_state` chưa có `limit_s`; `BRANCH_CHANGED` chưa là `GIT_BRANCH_CHANGED` của bảng 3.2 (đã giao T46).
- T45: test đọc lại sai chưa kiểm file được trả lại (`apply_job.py:347-350`); T45 kiểm `self.read() == BEFORE` và cây làm việc sạch.
