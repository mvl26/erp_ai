Feature: FEAT-006
Stage: build
Author-agent: tech-lead (tổng hợp từ reviewer)
Date: 2026-11-12
Approved-by:

# Review 19 — FEAT-006 T19 (runner nạp cấu hình, công tắc, `departments`, 4 cột nhật ký, `CLASSIFY_MAX_TOKENS` 600)

- Diff: `git diff a62944e..c4d821f -- erp_ai` (nhánh `team/FEAT-006-task-19-rework1`, một commit c4d821f gom từ 5fa6d4b, 0f6e89f và phần sửa; merge `13a67f1`)
- Vòng: 2 (1 vòng sửa; trước đó dev gặp DESIGN_CONFLICT hai lần, tech-lead mở rộng touchpoint, xem progress.md)
- Verdict: approve

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix | vòng 2 |
|---|---|---|---|---|---|
| major | STD-TEST-6 | test_runner_routing.py:183, test_agent_runner.py:241 | `RunnerTestBase.setUp` không đặt `routing_rules` nên 2 khẳng định (`predicted_assignee` rỗng, prompt không có `departments`) chỉ qua khi site chưa cấu hình định tuyến | thêm `routing_rules=make_routing_rules()` vào `setUp` | ADDRESSED |

minor | — | — | (1) STD-GIT-2: commit "wip" 5fa6d4b có 2 test đỏ (400 vs 600): đã gom thành một commit từ BASE nên không còn commit đỏ trên `team/FEAT-006`; (2) test L0 chỉ kiểm `ai_complexity`: dev thêm `ai_importance` và `ai_score_reason` (ADDRESSED).

## Điểm reviewer đã kiểm
- AC-1, AC-2, D-8, D-15, NFR-1 đạt như design 4.1: nạp `routing` một lần ở (b), `auto_assign` ở (e), `routing_config` trong `ToolContext`, `departments(routing)` vào prompt, 600 token, 4 cột (Int/Int/Small Text/Data) trong `section_prediction`, `read_only`, `description` đúng hành vi; `BAD_ROUTING_ERROR` ở cột `error`; `decide_route` dùng `site_facts`/`policy` thật; `_route` nhận `auto_assign`/`subject` nhưng chưa dùng (đúng phạm vi T19).
- Mười đột biến của dev (bỏ từng hành vi trong runner.py) đều làm đỏ test tương ứng (reviewer đọc mã xác nhận). Hai test 400 -> 600 là sửa kỳ vọng theo D-8, không nới.

## Mục "không kiểm được từ diff" và phán quyết của tech-lead
- Test ngoài `RunnerTestBase` (ví dụ `test_handlers.py`) gọi runner có phụ thuộc `routing_rules` thật của site không: đã đọc `test_handlers.py:231-243`, chỉ khẳng định số lần gọi model, `task`, `max_tokens`, `system` khác rỗng; không khẳng định `predicted_assignee` hay `departments`, nên không phụ thuộc.
- Chuỗi rỗng so với NULL của `routing_rules`: T9b chặn lưu rỗng, `after_migrate` gieo mặc định (review-09b); site miyano đã kiểm ở C2 (`routing_rules` là JSON mặc định).
- Báo cáo đỏ-trước của lần 1/2 nằm trong báo cáo dev (đột biến 10 hành vi, đỏ `3 failures + 3 errors` của `test_runner_routing` đúng lý do thiếu hành vi, ví dụ `(0, 0) != (2, 3)`, `None != 'không có điểm'`, `400 != 600`); lần 3 `AssertionError: 600 != 400` ở hai module.

## Deferred
- `description` của `auto_assign_enabled` (`erp_ai_setting.json:207`, deferred từ review-11/12) lệch design 4.2 ở hai điểm: (1) "chưa có ai được gán" xét SAU (u1), nên Assignment Rule của nhóm gán trong lần `doc.save()` đó thì bot không gán (AC-6 Amendment); (2) "tạo 1 Task cho đầu mục C/D" chỉ khi bot tự gán được người (`needs_task` cần `assignee` khác None và `assigned`), phiếu chưa có Task, và chia sẻ tài liệu không bị tắt. "Từ L1" và "Tắt thì không gán, không tạo Task" khớp. Sửa lời ở T21 hoặc T26 khi hành vi có mã (ngoài touchpoint T19).
- T20 phải đưa `decision.notes` vào `skipped_fields` (xem review-17), và kiểm không trùng lý do với `skipped` của `apply_route`.
- Minor ở trên đã xử lý hoặc chấp nhận.

## Bằng chứng chạy (dev)
- RED: `erp_ai.agent.test_runner_routing` 3 failures + 3 errors đúng lý do thiếu hành vi; `migrate` site miyano exit 0, `show columns` có 4 cột mới (`predicted_complexity` int, `predicted_importance` int, `predicted_score_reason` text, `predicted_assignee` varchar).
- GREEN: test_runner_routing 11 OK, test_erp_ai_log 7 OK, test_doctype_descriptions 10 OK, test_agent_runner 56 OK, test_handlers 31 OK.
- `cmd.test` toàn app (`bench --site miyano run-tests --app erp_ai`) trên đầu nhánh task c4d821f: `Ran 792 tests in 135.148s`, `OK`; lint pre-commit Passed.
- Sau merge: `git diff --stat c4d821f HEAD -- . ':!docs'` rỗng (cây mã sau merge 13a67f1 trùng cây đã chạy xanh).

## Review checklist (10)
1–10: đạt (reviewer approve vòng 2).
