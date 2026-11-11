Feature: FEAT-001
Stage: intake
Author-agent: team-leader
Date: 2026-11-11
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Intake FEAT-001 — AI Agent `erp_ai` cho Helpdesk Miyano (theo guide v2.2)

- Yêu cầu gốc: "tiếp nhận yêu cầu docs/HuongDan_TrienKhai_erp-ai.md rồi triển khai app theo yêu cầu này, dùng superpowers (không ghi đè), chưa commit vội"
- Nguồn: hội thoại
- Loại việc: feature (dựng hệ thống mới từ khung app rỗng)
- Playbook: new-project
- Size: L
- Mode: decide
- Lý do chọn playbook/cỡ: Khớp tín hiệu "Empty repo, building a system from scratch" vì repo chỉ là khung `bench new-app` chưa có hành vi nào (`docs/team/assessment.md:16`, `erp_ai/hooks.py:1-6`, `erp_ai/erp_ai_agent/__init__.py` 0 byte), còn guide mô tả trọn một hệ thống mới gồm nhiều module: thẩm quyền, tool registry, vòng lặp agent, 3 DocType, scheduler, custom field Helpdesk, eval (`docs/HuongDan_TrienKhai_erp-ai.md:605-643`, `:186-216`); cỡ L vì nhiều module, có NFR mới (an toàn `:1171-1236`, chi phí `:1222`, quyền `:220-430`) và lộ trình 10 bước dài hơn 5 người-ngày (`:1271-1301`).
- Skill tạm: không cần cho bước analyze; ghi cho plan — cân nhắc một skill tạm "frappe-helpdesk" (tạo DocType/fixtures/custom field đúng chuẩn Frappe 15, viết `FrappeTestCase`, chạy `cmd.test_one`), vì kit không có profile `frappe` sẵn (`<kit>/profiles/`).
- Ngân sách: max_agents_per_feature = 10; feature_budget_usd = không giới hạn

## Đã cân nhắc và loại
- `integration` (dòng xếp sau `new-project` trong bảng): Claude API chỉ là một phần (`:682-955`); phạm vi còn gồm thẩm quyền, DocType, hook Helpdesk, scheduler.
- `new-feature`: không có hệ thống đang chạy nào để thêm hành vi — app chưa có tính năng nào (`assessment.md:42`).
- Bước 1 của playbook (`/team:onboard --new`) đã được thay bằng takeover + onboard (`docs/team/onboarding.md`).

## Ràng buộc của người yêu cầu
- Yêu cầu lần 2 (2026-11-11): "…, tôi cài helpdesk rồi, chạy auto đến khi hoàn thiện thì thôi, tôi cấp quyền cho bạn".
- **Dùng superpowers, không ghi đè**: được dùng skill `superpowers:*` song song với `/team:*`; không thêm `skillOverrides` ẩn superpowers vào `.claude/settings.json`.
- **Commit**: chỉ commit local trên nhánh `team/FEAT-001` và nhánh task `team/FEAT-001-task-N`; không đụng `develop`/`main`, không push (người chốt qua AskUserQuestion 2026-11-11).
- **Chạy tự động**: Mode `decide`; người chọn tắt G1–G4 trong `.team/config.json` (AskUserQuestion 2026-11-11). G0, G5 giữ bật. Không deploy lên `erp.miyano.com.vn` — guide mục 15 nói "cài trực tiếp production" nhưng việc đó là của người.
- **Môi trường**: `helpdesk` 15.1.0 đã cài trên site `miyano` (frappe 15.126.1) — `bench --site miyano list-apps`.

## Quyết định (decide mode)
- D1 — Tắt G1–G4. Vì: người chọn để chạy tới khi xong. Phương án khác: dừng ở mỗi cổng; chỉ giữ G1. Hoàn tác: đặt lại `true` trong `.team/config.json`, người đọc lại spec/architecture/plan/acceptance và điền `Approved-by:`.

## Điều analyst phải xử lý đầu tiên
- Guide coi bước 1 (bộ đánh giá offline 71 phiếu) là **cửa quyết định trước khi dựng app** (`:1287-1297`); `open-questions.md` câu 1 chưa trả lời → spec phải nói rõ walking skeleton bắt đầu từ `eval/` hay từ DocType.
- Bench dev không có app `helpdesk` (`open-questions.md` câu 2, `debt.md:14`) → mọi tiêu chí dựa trên HD Ticket chưa kiểm được ở local.
- Guide tự nhận "chưa hoàn thiện" — thiếu JSON schema tool, `run_eval.py`, hàm phụ, `hooks.py` đầy đủ (`:15`, `:1462-1472`).
- Lệch guide ↔ code: module `erp_ai/erp_ai/doctype/` (`:634`) vs `erp_ai/erp_ai_agent/` (`modules.txt:1`); `requirements.txt` (`:640`) vs `pyproject.toml`.
- Các việc COO chốt (`:1494-1502`) và điểm kiểm chứng tại production (`:1506-1519`) là câu hỏi cho người, không tự giả định.

## Đổi cỡ (nếu có)
- —
