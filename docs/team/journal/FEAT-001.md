Feature: FEAT-001
Stage: any
Author-agent: team-leader
Date: 2026-11-11
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Journal FEAT-001

<!-- Mỗi lần bàn giao: 3–5 dòng, đúng định dạng dưới; trần journal.max_lines_per_entry. -->
- 2026-11-11 intake → team-leader | new-project, L, ask | intake.md | — | good | khung bench new-app rỗng (assessment.md:16) + guide mô tả hệ thống mới nhiều module (guide:605-643); ràng buộc: dùng superpowers không ghi đè, chưa commit
- 2026-11-11 intake (lần 2) → team-leader | mode ask → decide; helpdesk 15.1.0 đã cài trên miyano; người chọn tắt G1–G4 và commit local trên team/FEAT-001* | intake.md cập nhật | — | good — hook chặn team-leader sửa config, người phải tự đổi gates | in lệnh jq cho người
- 2026-11-11 lý do gọi analyst: intake READY, cần spec.md có DoD/NFR từ guide v2.2 trước research/architect
- 2026-11-11 analyze → analyst | spec.md: 20 AC, 9 NFR, 15 giả định, 6 câu kỹ thuật H-1..H-6 | SPECIFIED | 1 lượt | good — phạm vi dừng ở L0/L1 (A-1) vì guide chưa có schema tool L2/L3 (`:1462-1472`) | L2/L3 thành feature sau
- 2026-11-11 quyết định (decide): chấp nhận phạm vi L0/L1. Vì: guide tự nhận thiếu schema tool L2/L3. Khác: tự viết schema L2/L3. Hoàn tác: `/team:analyze FEAT-001 --amend`. Người đã tắt G0–G4 (team.py: gates G5)
- 2026-11-11 lý do gọi researcher: spec còn H-1..H-6 (SDK/header hạn mức, dedupe job, Helpdesk 15.1.0 field layout, rg, pyproject) cần docs đúng phiên bản
- 2026-11-11 research → researcher | research.md + 3 cache (anthropic 0.103.1, helpdesk fields 15.1.0, enqueue 15.126.1) | RESEARCHED | 1 lượt | good — phát hiện SDK dùng chung với workflowcore (ghim <1), dedupe lọt trong cùng transaction, job chạy dưới user lưu phiếu | không cần POC
- 2026-11-11 lý do gọi architect: size L, H-1 (vị trí module) còn mở, research có ADR nháp cần đánh số
- 2026-11-11 architect → architect | architecture.md, arch-impact.md, ADR-001..006 (proposed) | ARCHITECTED | 1 lượt | good — giữ module `ERP AI agent`, 4 tầng, gateway duy nhất, 1 writer/record | rủi ro lớn nhất: ERP AI Setting nhiều writer → cấm `.save()`
- 2026-11-11 lý do gọi designer: G2 tắt, cần design.md (DocType, schema tool, prompt, bảng breaker, test plan) trước plan
- 2026-11-11 design → designer | design.md 779 dòng (DocType, gateway, registry, luồng, quyền, migration, touchpoints, test plan) | DESIGNED | 1 lượt | good — skill fork trả về rỗng, phải đọc artifact để biết kết quả | kit: fork nên luôn trả dòng trạng thái
- 2026-11-11 quyết định (decide): dev chạy test trong worktree bằng `PYTHONPATH=<worktree>` + đường dẫn bench tuyệt đối (probe exit 0, erp_ai.__file__ trong worktree); base_branch = develop (repo không có main). Khác: build ngay trên checkout chính. Hoàn tác: đổi lại cmd.* trong profile. Người chạy script vì hook chặn sửa profile/config
- 2026-11-11 lý do gọi tech-lead (plan): design READY, cần plan.md + tasks.md, task 1 là walking skeleton
- 2026-11-11 plan → tech-lead | skill /team:plan (cỡ L) | 40 task, T1 walking skeleton; 65 touchpoint đều có task; task chạm migrate chạy tuần tự
- 2026-11-11 base → team-leader | commit local 34e4c8f trên team/FEAT-001 (onboard + artifact FEAT-001) để worktree của dev thấy profile/docs; .github/* mới để lại chờ người | — | — | good | —
- 2026-11-11 lý do gọi tech-lead (build): plan READY, G3 tắt; chạy vòng dev → reviewer cho 40 task, tuần tự với task [migrate]
- 2026-11-11 build T1 → dev (2 lượt) | c03d70f skeleton (5 test OK) + cfb160b guard DoesNotExistError trên nhánh team/FEAT-001-task-1-r2 (6 test OK) | DONE_WITH_CONCERNS | 2 lượt | slow — fork /team:build kết thúc ngay sau khi gọi agent nền nên team-leader phải nối tay | chạy tech-lead như Agent riêng để tự chờ dev/reviewer
- 2026-11-11 lý do gọi tech-lead (Agent): tiếp vòng build từ review T1 tới T40 trong một ngữ cảnh chờ được agent con
- 2026-11-11 build T1 → reviewer ×3 + dev ×2 | vòng 1 request-changes (STD-DESIGN-2), vòng 2 request-changes (STD-TEST-5), vòng 3 approve; merge vào team/FEAT-001 | test_handlers 6 OK, lint exit 0 | `cmd.test` (--app erp_ai) chạy 0 test do lỗi `_add_test` của Frappe với file test ở gốc gói; tech-lead không chạy được `bench` trực tiếp (hook role-policy) nên chạy qua dev | dừng ở T1, chờ team-leader quyết định cmd.test
- 2026-11-11 build → tech-lead (Agent) | T1 review-01 approve sau 3 vòng, merge 35cdcb4 | BLOCKED sau 1/40 | 1 lượt | wrong — cmd.test chạy 0 test (Frappe test_runner.py:304-307 import file test ở gốc package thành `erp_ai`); hook role-policy chặn cmd.* dạng `cd ../.. && …` | profile dùng lệnh một đoạn
- 2026-11-11 quyết định (decide): D2 chuyển mọi file test ở gốc `erp_ai/test_*.py` (trừ helper `test_utils.py`) vào `erp_ai/tests/` (+`__init__.py`); thêm task chuyển `test_handlers.py`, sửa đường dẫn test trong tasks.md. Vì: bug discovery của Frappe 15. Khác: cmd.test = danh sách --module. Hoàn tác: chuyển file về gốc. D3 cmd.* thành lệnh một đoạn (bench tự tìm thư mục bench) — người chạy script vì hook chặn sửa profile
- 2026-11-11 lý do gọi lại tech-lead: tiếp build T1b (chuyển test) → T2..T40 với D2/D3
