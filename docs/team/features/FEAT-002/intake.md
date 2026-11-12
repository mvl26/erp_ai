Feature: FEAT-002
Stage: intake
Author-agent: team-leader
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Intake FEAT-002 — Bot "đang suy nghĩ" rồi trễ 3–5 giây mới trả lời, chỉnh được trong setting

- Yêu cầu gốc: "khi gọi ai không nên trả lời luôn mà viết là suy nghĩ rồi delay khoảng 3-5s rồi mới trả lời, có thể sửa trong setting"
- Nguồn: hội thoại
- Loại việc: feature (bổ sung hành vi cho agent đã có)
- Playbook: new-feature
- Size: L
- Mode: decide
- Lý do chọn playbook/cỡ: Thêm hành vi mới cho hệ thống đang chạy (FEAT-001 đã verified) chứ không sửa lỗi; chạm nhiều nơi — cấu hình `ERP AI Setting` (trường mới + validate, `erp_ai_setting.py`), luồng trả lời `erp_ai/agent/runner.py:239` (`_reason`) và việc đăng comment `erp_ai/agent/tools/write_ticket.py:73` (`post_comment`), cộng test và migrate trường. Cỡ ban đầu M, đổi lên L (xem mục Đổi cỡ).
- Skill tạm: không cần
- Ngân sách: max_agents_per_feature = 10; feature_budget_usd = không giới hạn

## Điểm analyst phải làm rõ (không tự giả định)
- "Gọi ai" = trigger comment có `@ai` (`TRIGGER_COMMENT_MENTION`, `erp_ai/handlers.py:100`); trigger tạo phiếu (`TRIGGER_TICKET_INSERT`, chỉ phân loại, không comment) có áp dụng không?
- "Viết là suy nghĩ" = đăng một comment tạm (ví dụ "Đang suy nghĩ…") rồi trả lời sau: comment tạm sau đó bị xóa/sửa thành câu trả lời, hay để lại? Ảnh hưởng ADR-004 (một người ghi duy nhất cho mỗi bản ghi), D8 (đọc comment từ `Comment` của core, tác giả = `owner`) và việc agent tự đọc lại comment của chính nó.
- Delay thực hiện thế nào khi job chạy trên queue `long` (`erp_ai/agent/queue.py:29`): `time.sleep` trong worker hay enqueue trễ; ảnh hưởng `JOB_TIMEOUT_S` và `deadline` trong runner, và quy tắc daily limit/dedup.
- Cấu hình: tên trường, đơn vị giây, mặc định 3–5 s (khoảng ngẫu nhiên min–max hay một giá trị?), giá trị 0 = tắt, giới hạn trên trong `INT_LIMITS`/validate (NFR-3); nội dung câu "đang suy nghĩ" có sửa được không.
- Thời điểm delay: trước hay sau lời gọi API (lời gọi API tự nó mất vài giây — delay có cần bù thời gian đã qua?).

## Ràng buộc của người yêu cầu
- Như FEAT-001/BUG-001: commit local trên `team/FEAT-002`, không push, không đụng `develop`/`main`; G1–G4 tắt, G5 bật; không ghi khóa API vào artifact/log/commit; không đổi giá trị `ERP AI Setting` trên `miyano` (việc của người, trừ phần người đã bảo cấu hình local).
- Nhánh nền: `team/FEAT-001` (mã FEAT-001 và BUG-001 chưa vào `develop`); `.team/config.json` base_branch vẫn `main` (không tồn tại).

## Đổi cỡ (nếu có)
- 2026-11-12: M → L — người chọn chỉ báo riêng tiếng Việt (Q1 = b): thêm lớp mã giao diện JavaScript đầu tiên của dự án, NFR mới (NFR-5/6, tự hết sau 600 s), cần research và có thể cần ADR. Đề xuất của analyst, team-leader ghi nhận.

## Quyết định của người (2026-11-12, ghi bởi analyst khi amend spec)
- Câu hỏi qua team-leader (AskUserQuestion 2026-11-12), sau khi design.md báo `DESIGN_CONFLICT` (comment tạm phải xóa, trái ADR-004). Nguyên văn câu trả lời: "Làm dạng như claude cạy đó, nếu nó đang làm hay đang suy nghĩ thì viết là ... đang suy nghĩ, đang làm để người dùng biết ai đang hoạt động, tăng UI/UX. tránh ai đang chạy mà ko hiển thị gì để user theo dõi".
- Nghĩa đội ghi nhận:
  - Bỏ comment tạm. Thay bằng chỉ báo trạng thái trực tiếp ("Đang suy nghĩ…", "Đang làm: <việc>…") trong suốt lần chạy, tự mất khi xong, kể cả khi lỗi hoặc hết thời gian.
  - Không sửa ADR-004. Giữ khoảng trễ 3–5 s chỉnh được trong cấu hình.
- Kết quả: spec.md mục `## Amendment 1 (2026-11-12)`. Q1 (cách hiện trên giao diện): người chọn b) chỉ báo riêng tiếng Việt, có mã giao diện trong app erp_ai (AskUserQuestion 2026-11-12), ghi trong `questions.md`.
