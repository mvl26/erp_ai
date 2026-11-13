Feature: FEAT-004
Stage: build
Author-agent: reviewer
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Review 43 — FEAT-004 T43

- Diff: `git diff 9580564..team/FEAT-004-task-43` (2 commit `e16f7da`, `db23020`; 3 file)
- Vòng: 2 (max_rework=3)
- Verdict: approve (vòng 1: request-changes)

## Vòng 1 — request-changes (`git diff 9580564..e16f7da`)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major | STD-TEST-8 | erp_ai/agent/changes/test_process_runner.py (ca "rel pathspec magic", `:(glob)*.py`) / process_runner.py:84 | Ca duy nhất bắt đầu bằng `:` cũng chứa `*`, nên kiểm glob cũng từ chối nó. Bỏ `":"` khỏi `rel.startswith(("-", "/", ":"))` thì test vẫn xanh; nhánh từ chối pathspec magic chưa được kiểm | thêm ca chỉ có `:` như `":(top)x.py"` hoặc `":x.py"`, không có ký tự glob |
| major | STD-DESIGN-2 | erp_ai/agent/changes/process_runner.py:143 (`env=env` trong `_run_wrapped`) + erp_ai/tests/test_architecture.py (`test_subprocess_call_shape_accepts_git_writes_in_process_runner`) | Sau khi gộp, `env=` được dựng ở nơi gọi, không ở `subprocess.run(...)`. Luật kiến trúc (`timeout_wrapped_call_problems`, design 8.2 "env= không chứa os.environ") chỉ còn thấy tên `env`, nên `_run_wrapped(..., env=dict(os.environ))` về sau vẫn xanh. Test tự kiểm của luật dùng hình dạng inline của design, thứ file thật không còn | thêm cho luật một ca cho từ khóa `env=` (và `cwd=`) của `_run_wrapped(` trong process_runner.py kèm ca xấu bị bắt, hoặc đưa `env=` về inline |

minor | — | — | 2 điểm nhỏ: `"\0" in repo_root` (process_runner.py:69) không bao giờ quyết định gì vì `os.path.isdir` đã trả False; kiểm subject một dòng chặn `\n` nhưng để lọt `\r` | tùy dev

## Vòng 2 — approve (re-review theo phạm vi, `git diff e16f7da..team/FEAT-004-task-43`)
- Phát hiện 1: ADDRESSED (`test_process_runner.py:451-452`, ca `":(top)x.py"` và `":x.py"`; chỉ tiền tố `":"` từ chối chúng)
- Phát hiện 2: ADDRESSED (`test_architecture.py:652-657`, `699-709`, test `2395-2426`: mọi lời gọi `_run_wrapped(` trong process_runner.py đi qua `cwd_env_problems`; 7 ca xấu gồm `env=dict(os.environ)`; `cwd`, `env` chỉ nhận theo tên)
- Luật FEAT-006 không đổi: `timeout_wrapped_call_problems` chỉ được tách, trả cùng kết quả
- Phát hiện mới: không có blocker/major

minor | — | — | 2 điểm nhỏ: câu lỗi ở process_runner.py:87 còn ghi "without NUL" trong khi nay chặn cả `\r`, `\n`; kiểm `"\0" in repo_root` đã bỏ (thừa, ca "repo with NUL" vẫn phủ) | tùy dev

## Review checklist (10)
1–10 đạt sau vòng 2. Đuôi argv đúng bảng design 3.5; mọi lệnh bọc `timeout -s KILL`, `cwd=repo_root`, `env=source.git_env(identity=True)`, nhóm tiến trình riêng, `timeout=limit_s + GIT_BACKSTOP_EXTRA_S`; đầu ra ≤ 20 dòng; không `-a`/`--amend`; không `user.name`/`AGENT_USER`. Hành vi `run_bench` và assertion của T11 không đổi.

## Bằng chứng của dev
- Vòng 1 RED: `AttributeError: module 'erp_ai.agent.changes.process_runner' has no attribute 'git_commit_only'`; GREEN: `test_process_runner` 17 OK, `test_architecture` 101 OK; lint sạch
- Vòng 2 RED: "ValueError not raised" cho 2 ca `:` ở cả 3 hàm khi bỏ `":"`; `test_architecture` `FAILED (failures=7)` "scanner missed the violation"; GREEN: `test_process_runner` `Ran 17 tests … OK`, `test_architecture` `Ran 102 tests … OK`; lint sạch
- Sau merge `78d9887`: `cmd.test` `Ran 1023 tests in 185.253s` / `OK`

## Không kiểm được từ diff (tech-lead xử lý)
- `os.path.isdir` từ chối đường dẫn có NUL: Python của bench là 3.12.3 (hành vi có từ 3.8) → đạt.
- Luật lệnh con và hình dạng argv của T44 có đọc được `["add"]` truyền vào `_run_git_write` không: việc của T44, ghi vào handoff T44.
- Câu hỏi clean filter (ADR-022 QĐ 4): xem review-38, đang ở architect.

## deferred
- Khoảng trống design (designer chọn, không chặn T43): `_check_git_write_call` từ chối `rel` mà bộ chặn và `read_git_state` (T38, đọc bằng `./<rel>`, `:(literal)<rel>`) cho qua: tên chứa `[ ] * ?` (vd `helpdesk/desk/src/[id].vue`), đường dẫn bắt đầu bằng `:` hoặc `-`. Đề xuất như vậy được duyệt rồi lỗi ở T19 lúc áp dụng (`ValueError` sau khi ghi; T45 phải trả lại file). Chọn một: (a) bộ chặn từ chối các tên này lúc đề xuất, hoặc (b) design 3.5 đổi argv ghi sang `:(literal)<rel>`. 4 repo lõi hiện không có tên file như vậy.
- Luật so tên `_run_wrapped` theo chữ: gán bí danh `w = _run_wrapped` sẽ lọt.
- Chặn `\r` trong subject và bỏ kiểm NUL của `repo_root` không do phát hiện nào yêu cầu; nhỏ, có test.
