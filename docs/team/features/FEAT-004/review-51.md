Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 51 — FEAT-004 T51

- Diff: `git diff 66ddf58..team/FEAT-004-task-51` (2 commit `d727371`, `1cdd4a6`; 2 file)
- Vòng: 2 (max_rework=3)
- Verdict: approve (vòng 1: request-changes)

## Vòng 1 — request-changes (`git diff 66ddf58..d727371`)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-ERR-2 | erp_ai/test_utils.py:421 | `_write` chỉ kiểm `rel` so với `realpath(repo(app))`, không kiểm `app` so với `self.root`; `app` là đường dẫn tuyệt đối hoặc `../../..` thì `write_unstaged`/`stage`/`commit_file` ghi ra ngoài thư mục tạm (kể cả vào repo thật) trước khi `git()` từ chối (NFR-9) | gom kiểm `app` của `git()` vào `_repo_dir(app)` và gọi đầu tiên trong `_write`; thêm ca `app="/abs/outside"`, `app=".."` đòi `ValueError` và không có gì được ghi |

minor | — | — | 5 điểm nhỏ: (1) `add_remote` không kiểm `name`; (2) test chụp trạng thái không kiểm `timeout`; (3) gọi `mark_in_progress("rebase-merge")`/`install_marker_hooks` hai lần ném `FileExistsError`, thư mục hook chung của `erp_ai` và `erp_ai-wt`; (4) hằng khai báo sau lớp; (5) chưa test nào thấy dấu `commit-msg` | tùy dev

## Vòng 2 — approve (re-review theo phạm vi, `git diff d727371..team/FEAT-004-task-51`)
- Phát hiện 1: ADDRESSED (`_repo_dir(app)` tại `test_utils.py:408-415`, `_write` gọi trước ở `:439`; `test_git_sandbox_write_refuses_app_outside_root`)
- 5 điểm minor: dev sửa cả năm, có test
- Phát hiện mới: không có. Không test nào trong diff sửa ghi được vào repo thật hay ra ngoài thư mục tạm.

minor | — | — | 1 điểm nhỏ: bằng chứng RED chỉ dán cho ca `_write` và tên remote | tùy dev

## Review checklist (10)
1–10 đạt sau vòng 2. 4 điểm theo dõi từ review T36 đã làm (hook mặc định không chạy, `_write` giữ `rel` trong repo, `GIT_CEILING_DIRECTORIES`, dọn `host`).

## Bằng chứng của dev
- Vòng 1 RED: `FAILED (failures=17, errors=34)`: `AttributeError: 'GitSandbox' object has no attribute 'add_remote'`, `AssertionError: AssertionError not raised`; GREEN: `test_source` `Ran 50 tests in 2.186s` / `OK`
- Vòng 2 RED: `(helper='write_unstaged', app='/tmp/tmpbw9mpv57') AssertionError: ValueError not raised`, `Lists differ: ['escape.py'] != []`; GREEN: `test_source` `Ran 54 tests ... OK`, `test_change_guard` `Ran 10 tests ... OK`; `git -C apps/hrms status --porcelain` rỗng

## Không kiểm được từ diff (tech-lead xử lý)
- Mixin và `test_real_core_repos_snapshot_reads_the_four_core_repos` cần 4 repo lõi thật là checkout git: runner CI chưa kiểm → deferred cho devops.
- Phiên khác đổi HEAD/trạng thái repo lõi trong lúc lớp test chạy thì mixin báo đỏ ở `tearDownClass` (rủi ro site/bench dùng chung) → theo dõi ở `cmd.test`, ghi `debt.md` nếu xảy ra.
- Mixin chỉ thấy HEAD và `status --porcelain` (đúng NFR-9, design 8.5).

## deferred
- `remote_dir` và `install_marker_hooks` dựng đường dẫn từ `app` chưa kiểm riêng (hiện `git(app, …)` chạy trước nên không lọt).
