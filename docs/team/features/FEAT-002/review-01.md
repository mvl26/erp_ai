Feature: FEAT-002
Stage: build
Author-agent: reviewer
Date: 2026-11-12
Approved-by:

# Review 01 — FEAT-002 T1

- Diff: `git diff bc4baf6..team/FEAT-002-task-1` (vòng 2: `git diff b60469e..09273cd`)
- Vòng: 2 (max_rework=3)
- Verdict: approve

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major (vòng 1, ADDRESSED vòng 2) | STD-TEST-2 | erp_ai/agent/test_runner_status.py:220-235 | `test_done_last_when_answered` không phủ nhánh có câu trả lời (chỉ `end_turn`, không `post_comment`) | turn 1 là `post_comment` thật, kiểm `_comment_count()` +1; đã sửa ở 09273cd |

minor | — | — | 3 điểm nhỏ: phòng viết cứng `doc:HD Ticket/<tên>` (đã làm), kiểm 7 khóa cả payload `done` (đã làm), `settings.get("thinking_text")` thay `settings.thinking_text` đến khi T2 thêm trường (giữ nguyên) | —

## Review checklist (10)
1–10: đạt (vòng 2 giới hạn ở diff sửa; vòng 1 xem toàn diff, 10/10 đã phủ).

## Bằng chứng dev
- ĐỎ vòng 1 (stub RunStatus): `Ran 3 tests … FAILED (failures=2)`, `AssertionError: [] is not true : no status signal was emitted`.
- ĐỎ vòng 2 (script cũ không `post_comment`): `AssertionError: 0 != 1`.
- XANH: `test_runner_status` Ran 3 OK; `test_agent_runner` Ran 56 OK; `tests.test_handlers` Ran 31 OK.
- Toàn bộ `--app erp_ai`: nền Ran 507 FAILED (failures=16, errors=3); sau Ran 510 FAILED (failures=16, errors=3); danh sách đỏ giống hệt (19 test sẵn đỏ do môi trường: `test_tasks.TestCheckPrivilegeEscalation`, `erp_ai_accuracy`). Đếm DB HD Team/HD Ticket/HD Form Script/ERP AI Log: 4/4/0/22 trước và sau.
- Merge `9db58cd` vào `team/FEAT-002`; cây `erp_ai/` của `team/FEAT-002` giống hệt `team/FEAT-002-task-1` (`git diff --stat … -- erp_ai` rỗng), nên kết quả toàn bộ của dev áp dụng cho cây sau merge. Hook role-policy chặn tech-lead chạy `bench run-tests --app erp_ai` (D3).

## deferred
Không có.
