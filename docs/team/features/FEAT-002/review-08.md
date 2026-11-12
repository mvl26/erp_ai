Feature: FEAT-002
Stage: build
Author-agent: reviewer
Date: 2026-11-12
Approved-by:

# Review 08 — FEAT-002 T8

- Diff: `git diff e57751b..team/FEAT-002-task-8` (vòng 2: `git diff c7930e2..c89faf6`)
- Vòng: 2 (max_rework=3)
- Verdict: approve

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major (vòng 1, ADDRESSED) | STD-DESIGN-2 | erp_ai/public/js/agent_status_indicator.js:162-166 | rời trang chỉ `reset()`, `state.ticket` giữ tên cũ nên tín hiệu của phiếu đã rời vẫn hiện trên trang khác (ADR-008 Quyết định 6) | `afterEach` đặt `state.ticket = null` sau `reset()`; "connect" chỉ subscribe lại khi `if (state.ticket)` |
| major (vòng 1, ADDRESSED) | STD-TEST-8 | erp_ai/tests/test_architecture.py:211 | không có kiểm tĩnh cho cờ `state.socket` (setupForm chạy lại không đăng ký trùng) | thêm mẫu `if \(state\.socket !== socket\)`, `state\.ticket = null`, `if \(state\.ticket\)` vào bộ mẫu bắt buộc |

minor (ADDRESSED): bỏ `bound`, try/catch có comment lý do ở timer/connect/afterEach, kiểm `try \{` và `catch \(`.

## Review checklist (10)
1–10: đạt (vòng 2 giới hạn ở diff sửa; vòng 1 phủ 10/10).

## Bằng chứng dev
- ĐỎ vòng 1: 2 failures, `unexpectedly None : public/js/agent_status_indicator.js is missing`. Vòng 2: ĐỎ `missing in script: state\.ticket = null`; đột biến `if (true)` thay cờ socket đỏ `missing in script: if \(state\.socket !== socket\)`, đã hoàn lại.
- XANH: `test_architecture` Ran 44 OK; `pre-commit run --files` (ruff, prettier, eslint) đạt. Không chạy full suite (tránh deadlock với T4); full suite trên cây đã merge T4+T8 do dev T5 chạy làm nền.
- Phần hiển thị (AC-10, AC-11) là bước tay của người (J1, không có JS runner).

## deferred
- Thiết kế `design.md` 3.7 bước 4 (`reset()` không xóa ticket) chưa khớp ADR-008 Quyết định 6; code theo ADR. Cần designer/team-leader cập nhật chữ ở 3.7.
- Hẹn giờ có thể bắt đầu lại khi quay lại phiếu giữa lúc đang chạy (vì `reset()` xóa `runs`): kiểm ở bước tay AC-10 (i) / AC-11; thêm bước tay "rời sang danh sách phiếu khi `@ai` đang chạy trên phiếu A, không có chỉ báo nào hiện".
- Kiểm tĩnh chỉ chứng minh mẫu có mặt, không chứng minh vị trí (đánh đổi khi không có JS test runner).
- Có thể đăng ký `router.afterEach` thứ hai nếu socket đổi; vô hại.
