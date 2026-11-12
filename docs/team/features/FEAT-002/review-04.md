Feature: FEAT-002
Stage: build
Author-agent: reviewer
Date: 2026-11-12
Approved-by:

# Review 04 — FEAT-002 T4

- Diff: `git diff e57751b..team/FEAT-002-task-4` (vòng 2: `git diff 7e5871c..abb07de`)
- Vòng: 2 (max_rework=3)
- Verdict: approve

## Phát hiện (chỉ blocker/major)
| severity | STD | file:line | description | fix |
|---|---|---|---|---|
| major (vòng 1, ADDRESSED) | STD-TEST-2 | erp_ai/agent/test_runner_status.py:165-185 | D-6 (chờ trước tool đầu của cả lượt) không có test; chuyển chờ sát khối `post_comment` vẫn xanh | thêm `test_whole_turn_waits_before_its_first_tool` (`set_classification` + `post_comment`, L1, trễ 4/4, chụp trường phân loại và số comment lúc ngủ) |

minor (ADDRESSED): mốc anchor được ghim (`load_mapping` đẩy đồng hồ giả 0.5 s, kỳ vọng 2.5); rollback subtest nằm trong `try/finally`.
minor (deferred): (a) `:81` dùng `assertNotEqual` thay vì so giá trị đúng; (b) anchor đặt trước `status.start()` vẫn chưa phân biệt được vì tín hiệu bắt đầu không đẩy đồng hồ giả. Ghi cho T6: `delay = None` phải đặt trước `try` trước khi `_end_status(status, delay, …)` vào `finally`.

## Review checklist (10)
1–10: đạt (vòng 2 giới hạn ở diff sửa; vòng 1 phủ 10/10).

## Bằng chứng dev
- ĐỎ: 3 failures + 1 error / 10 test: `[] != [3]`, `0 != 1` (2 subTest), IndexError vì chưa có chờ.
- Vòng 2, đột biến A (chờ sát `post_comment`) đỏ `[('AI','Cao','High')] != [('','','Medium')]`; đột biến B (anchor trước `_reason`) đỏ `[3.0] != [2.5]`; đã hoàn lại.
- XANH: `test_runner_status` Ran 11 OK, `test_agent_runner` Ran 56 OK, `tests.test_handlers` Ran 31 OK, `test_architecture` Ran 42 OK; lint đạt.
- Toàn bộ `--app erp_ai`: nền (sau T2+T3) Ran 523 failures=16 errors=3; cuối Ran 530 failures=16 errors=3; 0 Deadlock; không test đỏ ngoài danh sách đỏ nền.
- Đếm DB: lúc bắt đầu T4 đã là HD Team 4 / HD Ticket 5 / HD Form Script 0 / ERP AI Log 29 (trước đó 4/4/0/22). Dev truy vấn chỉ-đọc: HD Ticket 43067 và 43068 (13:18 và 10:54 ngày 2026-11-12) do người dùng thật tạo (tài khoản quản trị của người dùng), nhật ký bot cho 43068 bắt đầu ~5 s sau khi tạo phiếu (một lần chạy `ticket_insert` thật), skip cho 43067 sau 75 phút: là sử dụng thật của người dùng, không phải rò rỉ test (D-4).

## deferred
Hai minor ở trên; nhắc T5: mở rộng `test_answer_waits_from_start_signal` và `test_indicator_stays_thinking_while_waiting` với `working(viết trả lời)` khi `RunStatus.working` có mặt.
