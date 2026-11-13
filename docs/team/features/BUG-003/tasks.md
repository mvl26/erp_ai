Feature: BUG-003
Stage: build
Author-agent: tech-lead
Date: 2026-11-13
Approved-by:

# Tasks BUG-003

Cỡ S, bug-fix. Nhánh `team/BUG-003` tách từ `team/FEAT-003` @ `d425faa`, worktree `.claude/worktrees/bug-003` (cây chính không bị checkout). Một task, 1 dev + 1 reviewer.

Preflight: chỉ một task nên không có cặp chung tệp/giao diện. Test của task (`erp_ai/tests/test_architecture.py`) nằm trong touchpoint; không mâu thuẫn tự thân; không yêu cầu nào bị Review checklist coi là lỗi.

- [x] T1 — Khung chỉ báo 3 chấm ẩn thật khi không có lần chạy: style inline `display` không còn đè thuộc tính `hidden` (lúc mới tạo trong `ensureElement`, sau `done`/hẹn giờ tự mất qua `render`, khi `reset`, cả khi nổi lẫn khi gắn trong khu vực "Trao đổi với bot"); khi có lần chạy khung vẫn hiện dạng flex như cũ — files: erp_ai/public/js/agent_status_indicator.js, erp_ai/tests/test_architecture.py — test: erp_ai/tests/test_architecture.py — depends: —

## Progress
baseline: `Ran 658 tests in 144.871s` `OK` trên `team/BUG-003` @ `d425faa` — red: (không có)
round 1: dev T1
round 2: review T1
round 3: rework T1 (vòng 1/3)
round 4: re-review T1 (scoped)
Progress T1: BASE=d425faa95f08194152d52bf8d982be908be7dac3 (team/BUG-003), nhánh task team/BUG-003-task-1 · dev call 1 DONE_WITH_CONCERNS @ 362b3bd (lo ngại: full suite deadlock 1213 do phiên khác chạy suite cùng site) · review vòng 1 request-changes (1 major STD-TEST-2) · rework 1 FIX_BASE=362b3bd → fae6172 DONE · re-review vòng 2 approve · merge 2354fe0 · `cmd.test` lần 1 `Ran 660 … FAILED (errors=39)` toàn `QueryDeadlockError 1213` trong `setUp` (trùng lúc phiên FEAT-004 chạy suite trên cùng site), lần 2 `Ran 660 tests in 117.672s` `OK` · ticked · review-01.md

## Tiêu chí (từ intake, FEAT-002 AC-10)
- C1: khi không có lần chạy nào, khung chỉ báo không hiển thị: không còn đường nào để style inline `display` khác `none` cùng tồn tại với trạng thái ẩn (lúc tạo, sau `done`, sau hẹn giờ, khi `reset`).
- C2: khi có ít nhất một lần chạy, khung hiện đúng bố cục cũ (flex, 3 chấm + tên + chữ), cả khi nổi và khi gắn trong khu vực trao đổi.
- C3: test tái hiện ĐỎ trước trên mã hiện tại vì đúng hành vi lỗi (không phải lỗi import/cú pháp), XANH sau khi sửa; test kiểu quy tắc tĩnh trên file script như các test `test_status_script_*` hiện có (profile chưa có slot test JavaScript).
- C4: không đổi gì khác của khu vực trao đổi; `cmd.test` trên `team/BUG-003` sau merge: không test đỏ nào (baseline rỗng).

Receives/Returns: không có hàm mới công khai; `ensureElement`/`render`/`reset`/`dockIndicator` giữ nguyên chữ ký và hợp đồng với phần còn lại của script.

One-file-one-owner: agent_status_indicator.js → T1; test_architecture.py → T1.
