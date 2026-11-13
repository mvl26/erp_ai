# Review 44 — FEAT-001 T34 (Job hằng ngày: kiểm nâng quyền)

Verdict: approve (sau 1 vòng rework)
Vòng: 2 (vòng 1 request-changes; vòng 2 scoped re-review approve)
Diff: `git diff 881fa66..team/FEAT-001-task-34` (head 1280cd2; vòng 2: `git diff dd51bf4..team/FEAT-001-task-34`)

## Vòng 1 (review-raw-T34.md)
- major STD-ERR-1: `send_alarm` chung một try; lỗi email rollback xóa Error Log báo động, bỏ qua điều kiện sau.
- major STD-DESIGN-5: điều kiện role chỉ kiểm thừa, spec (AC-18, design.md:483) yêu cầu bằng đúng {ROLE_AGENT, Agent}.
- major STD-TEST-2: test "không giải mã khóa" không thể đỏ.
- Phán quyết: đăng ký hook daily `check_privilege_escalation` giao cho T35 (dòng T35 trong tasks.md đã cập nhật).

## Vòng 2
Cả ba ADDRESSED (`_raise_alarm` bọc từng lời gọi, lỗi email ghi TITLE_RUN_FAILED rồi tiếp tục, không rollback; so sánh bằng, thông điệp nêu role thừa/thiếu; test vá `get_decrypted_password` và `Document.get_password` ném AssertionError, là bảo vệ hồi quy vì mã không bao giờ giải mã). Minor 1, 2 ADDRESSED; hooks.py không bị chạm.

## Bằng chứng dev
Vòng 1: RED stub (7 failure + 3 error) -> GREEN 25 OK; 8 mutation đều đỏ. Vòng 2: RED 2 failure đúng lý do -> GREEN 28 OK; 3 mutation đỏ; pre-commit pass; đếm HD Team/HD Ticket/User/ERP AI Log/Error Log/Email Queue/Server Script/Webhook/Custom DocPerm 4/3/8/0/198/9/0/0/1360 trước = sau.

## Deferred (minor)
- `except Exception` trong `_raise_alarm` gắn nhãn "email error" cho mọi lỗi, kể cả lỗi ghi Error Log báo động; thông điệp thiếu `subject` nên ba email hỏng cho ba dòng giống nhau (STD-ERR-4).
- Subject "role ngoài danh sách cho phép" chưa mô tả ca thiếu role.
- Test thiếu role giả định AGENT_USER trên site test chỉ có hai role mong đợi.
