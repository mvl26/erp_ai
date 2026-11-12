## Feature
FEAT-006 — Bot chấm độ phức tạp và độ quan trọng; chọn mức ưu tiên, nhóm, người phụ trách; SLA và Task theo điểm. Nhánh `team/FEAT-006` (cắt từ `team/FEAT-003` @ `d425faa`), đầu `e5e1a16`. Verdict acceptance: `accepted`, 6/6 (`docs/team/features/FEAT-006/acceptance.md`). As-Built: `docs/team/features/FEAT-006/asbuilt.md`.

## Why
Bot chỉ ghi nhóm và ưu tiên theo bảng ánh xạ cố định theo đầu mục, không gán được người, và người mặc định cùng SLA chỉ là chữ trong prompt, nên phiếu vẫn chờ người chia tay (spec FEAT-006, "Why now").

## What changed
- Chấm hai điểm 1–3 (độ phức tạp, độ quan trọng) và lý do trong cùng lời gọi phân loại; ghi `ERP AI Log` ở mọi mức, lên phiếu từ `L1` (3 trường HD Ticket chỉ đọc, permlevel 8, role `Agent` đọc được). Điểm sai thì 0 và ưu tiên theo ánh xạ (AC-1, AC-2).
- Ưu tiên tính theo quy tắc R1–R5 trong một hàm (`erp_ai/agent/routing.py`); nhóm D/E theo bảng bộ phận; cấu hình `routing_rules` (JSON, kiểm khi lưu) và công tắc `auto_assign_enabled` (tắt sẵn) trên `ERP AI Setting` (AC-3..AC-5).
- Gán người qua cơ chế gán của Helpdesk và tạo một Task cho đầu mục C/D khi chính bot vừa gán; không giành phiếu đã có người, không gán tài khoản agent, nội dung phiếu không điều khiển được việc gán (AC-6..AC-9, AC-13). Bước định tuyến là mã tất định ngoài registry tool (`erp_ai/agent/tools/route_ticket.py`), ADR-019..ADR-021. Task có Custom Field `ai_ticket`; dòng quyền Task của app có thêm `share`.
- Báo không có SLA hoặc SLA chậm hơn mức mong đợi; SLA do Helpdesk tính theo `condition` trên `doc.ai_complexity` (AC-10..AC-12, AC-18). Truy vết đủ trong `actions` của `ERP AI Log` (AC-16). Eval offline thêm khớp ưu tiên, khớp nhóm, phân bố điểm, token và số lần bị cắt (AC-15).
- Sửa lỗi cắt phân loại: cổng model gửi `thinking: disabled` cho bước phân loại với model `claude-haiku-*` (`erp_ai/gateway/__init__.py:154-155`), trần token vẫn 600, khác chữ design D-8. Model phân loại khác Haiku vẫn có thể bị cắt. Mã nền FEAT-003 có cùng lỗi: cần backport nếu phát hành riêng.
- Tài liệu: `README.md`, `CHANGELOG.md` (mục `[Unreleased]`), `docs/HuongDan_QuanTri_DinhTuyen.md` (8 việc của người trước khi bật công tắc, mẫu `condition` SLA).
- Giới hạn đã biết (chi tiết ở As-Built mục 1.5, 1.6): thông báo "ma" khi lỗi sau `notify_assignment`; 2 khe hở bảo vệ tĩnh (tên bộ phận, `runner._route` không bị quét `.save()`).
- Không phải điều kiện merge: dữ liệu site `miyano` còn phải dọn (tài khoản agent còn 99 role, SLA rác, team trỏ rule đã mất, 0 HD Agent). Công tắc phải giữ tắt cho tới khi xong. Prod cần người duyệt (G5).

## How verified
Lệnh lấy từ `acceptance.md`, chạy trên `e5e1a16`:
- `cd /home/miyano/frappe-bench && bench --site miyano run-tests --app erp_ai --junit-xml-output <thư mục tạm>/app-r1.xml` → exit 0, `Ran 885 tests in 162.894s` / `OK`; junit 885 pass, 0 fail, 0 error, 0 skip.
- `pre-commit run --all-files` → exit 0 (12 hook).
- `bench build --app erp_ai` → exit 0; `bench --site miyano migrate` → exit 0, không có `error`/`traceback` trong log.
- Eval thật: `bench --site miyano execute erp_ai.eval.export_tickets.export --args '["<đường dẫn ngoài repo>"]'` rồi `bench --site miyano execute erp_ai.eval.run_eval.run --args '["<đường dẫn>"]'` → `Overall accuracy: 100.0% (2/2)`, `max_tokens hits: 0`, token đầu ra lớn nhất 285 (mẫu chỉ 2 phiếu cùng đầu mục B, không kết luận độ đúng chung).
- `grep -rnE "response_by|resolution_by" erp_ai/agent/` → không có phép gán trong mã không phải test (AC-10).
- Không thêm skip marker: `git diff d425faa e5e1a16 -U0 -- erp_ai | grep -nE "^\+.*(@unittest\.skip|skipIf|expectedFailure|\.skipTest\()"` → rỗng. Không chạm `protected_paths`.
- Đếm site trước → sau cả bộ test: Has Role agent 99 → 99; HD Ticket 8 → 8; Task 0 → 0; ToDo 49 → 49; HD Service Level Agreement 2 → 2; HD Team 4 → 4; Assignment Rule 3 → 3.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
