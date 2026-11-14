Feature: FEAT-007
Stage: intake
Author-agent: team-leader
Date: 2026-11-14
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Intake FEAT-007 — Đưa app `erp_ai` về đúng và đủ theo "Chiến lược AI Agent Helpdesk Miyano"

- Yêu cầu gốc: "kiẻm tra xem app hiện tại đẫ đáp ứng đúng yêu cầu docs/Chiến lược AI Agent Helpdesk Miyano.docx, điều chỉnh lại app nếu chưa đúng yêu cầu, làm feât 007  để hoàn thinẹ app như yêu cầu docs/Chiến lược AI Agent Helpdesk Miyano.docx"
- Nguồn: hội thoại (2026-11-14). Tài liệu yêu cầu: `docs/Chiến lược AI Agent Helpdesk Miyano.docx` (31/10/2026, COO Miyano); bản chữ để các vai đọc: `docs/team/features/FEAT-007/source-strategy.md`.
- Loại việc: feature
- Playbook: new-feature
- Size: L
- Mode: decide
- Lý do chọn playbook/cỡ: hành vi mới cho hệ thống đang chạy, người gọi tên một ID (FEAT-007) cho cả phần "điều chỉnh" lẫn "hoàn thiện". Cỡ L vì đụng nhiều module (lịch chạy, báo cáo, registry công cụ, chính sách mức tự chủ, prompt, ERP AI Setting), có yêu cầu phi chức năng mới (guardrail, giới hạn chi phí, dữ liệu nhạy cảm), ước tính hơn 5 ngày công. Bằng chứng lúc nhận việc (`develop` @ `7cc37bb`):
  - Lịch chạy chỉ có 3 việc (`reprobe_exhausted_keys`, `recompute_monthly_spend`, `check_privilege_escalation`): `erp_ai/hooks.py:159-161`. Tài liệu mục 3 và 5 đòi báo cáo 8h hằng ngày cho COO, KPI hằng tuần, tự đóng phiếu đầu mục F sau 3 ngày im lặng, nhắc hạn.
  - Chỉ có một báo cáo: `erp_ai/erp_ai_agent/report/erp_ai_accuracy/`. Tài liệu mục 5 đòi 6 KPI trên Trang tổng quan Helpdesk.
  - Tri thức: app chỉ có công cụ đọc (`erp_ai/agent/tools/read.py:24` cho đọc `HD Article`, `:103` tìm phiếu đã Resolved). Tài liệu mục 4 đòi bot soạn bài CSKT nháp sau mỗi phiếu đóng.
  - Công cụ ghi ERP: registry có nhóm `site_admin` và `site_unrestricted` (`erp_ai/agent/tools/registry.py:43-46`), tức công cụ bản ghi chung và ô "Toàn quyền". Tài liệu mục 4 và 6 đòi danh mục trắng, mặc định cấm, và một danh sách cấm tuyệt đối.
- Skill tạm: không cần cho bước phân tích.
- Ngân sách: max_agents_per_feature = 10; feature_budget_usd = không giới hạn

## File đầu vào cho các vai

| File | Là gì |
|---|---|
| `docs/team/features/FEAT-007/source-strategy.md` | Bản chữ nguyên văn của tài liệu chiến lược, gồm 7 bảng và 3 hình |
| `docs/team/features/FEAT-007/gap-audit.md` | Bảng đối chiếu tổng hợp app so với tài liệu: đã đúng, lệch có quyết định, trái (C1–C6), còn thiếu (G1–G13, H1–H14), điểm cần architect phán |
| `docs/team/features/FEAT-007/audit-A1.md` … `audit-A8.md` | Bằng chứng `file:line` cho từng dòng đối chiếu, theo 8 nhóm |
| `docs/HuongDan_TrienKhai_erp-ai.md:1474-1490` | 9 chỗ hướng dẫn 2.2 chủ ý làm khác tài liệu chiến lược |
| `docs/team/features/CHG-001/handoff-direct-session.md` | Mô tả code viết theo lệnh trực tiếp ngày 13/11 (công cụ bản ghi chung, ô "Toàn quyền", "làm luôn", đường dẫn duyệt) |

## Quyết định của người (AskUserQuestion, 2026-11-14)

| # | Câu hỏi | Người chọn | Hệ quả cho spec |
|---|---|---|---|
| N-1 | Ở 5 điểm app đang làm trái tài liệu (C1–C5 trong `gap-audit.md`), FEAT-007 theo bên nào | "Mặc định theo chiến lược" | Đường chính làm đúng tài liệu: bot chỉ ghi vào danh mục trắng; việc ngoài danh mục phải được bấm Duyệt trên comment rồi mới làm. 5 quyền ngày 13/11 (Toàn quyền, công cụ bản ghi chung, "làm luôn", sửa code + bench, đường dẫn duyệt một lần bấm) vẫn giữ, nhưng là công tắc riêng, mặc định tắt, bật thì có cảnh báo và ghi log đủ. |
| N-2 | Bot có được trả lời người tạo phiếu và đổi trạng thái phiếu không | "Cho cả hai, có chốt" | Bot được gửi trả lời tới người tạo phiếu, và được đổi trạng thái trong đúng 2 trường hợp: phiếu đầu mục F im lặng 3 ngày; phiếu có mọi Task liên kết đã xong. Không bao giờ áp cho phiếu Chỉ đạo BGĐ và đầu mục E. Mỗi việc một công tắc, mặc định tắt. Quyết định này thay dòng "chỉ comment nội bộ" và "không đổi status" của hướng dẫn 2.2 trong phạm vi vừa nêu. |
| N-3 | Build FEAT-007 lúc nào so với phiên đang build FEAT-004/005 | "Build toàn bộ song song" | Build hết ngay ở worktree riêng, không chờ FEAT-004/005. Người chấp nhận xung đột khi merge và test chập chờn vì hai phiên dùng chung site `miyano`. |

## Quyết định của team-leader (decide mode)

| # | Chọn | Vì | Phương án khác | Sai thì hoàn tác |
|---|---|---|---|---|
| QĐ-1 | Một feature FEAT-007 cho cả phần "điều chỉnh" và "hoàn thiện"; spec chia tiêu chí thành các gói build và nghiệm thu riêng được | Người gọi tên một ID; chia gói để build song song và merge từng phần | Tách thành nhiều feature | Analyst đề xuất đổi cỡ/tách, team-leader mở intake mới |
| QĐ-2 | Giữ các điểm lệch có quyết định của hướng dẫn 2.2 mà N-1, N-2 không đụng tới: job nền thay dịch vụ riêng, L0 chỉ ghi log, đọc bản ghi theo danh sách cho phép, tool đọc mã nguồn, nhiều khóa API, đánh giá offline trước khi dựng | Hướng dẫn ghi "tài liệu này thắng" (`docs/HuongDan_TrienKhai_erp-ai.md:5`) và FEAT-001…006 dựng trên đó; đảo lại là viết lại app | Theo sát tài liệu chiến lược ở mọi điểm | Change-request cho từng điểm |
| QĐ-3 | Lỗ rò C6 (công cụ bản ghi chung đọc được phiếu của nhóm loại trừ) được vá trong FEAT-007 | Không lệnh nào yêu cầu nó; trái NFR-4 của FEAT-001 và `README.md:39` | Tách thành bug riêng | `git revert` commit vá |
| QĐ-4 | Việc trên site production (cài 6 Loại phiếu, SLA, Assignment Rule, gán tay phiếu cũ, cấp role) nằm ngoài phạm vi; app chỉ cung cấp thứ để người làm việc đó dễ và kiểm được | Triển khai production cần người duyệt (cổng G5); dữ liệu site không phải mã | App tự tạo cấu hình Helpdesk | Thêm tiêu chí ở change-request |
| QĐ-5 | Giá trị phụ thuộc site (tên trường "Nguồn phát sinh", "Hạn hoàn thành", người nhận báo cáo COO, danh mục trắng, kho HDSD) là cấu hình, mặc định rỗng; rỗng thì phần hành vi tương ứng không chạy và có ghi rõ | Site dev không có các trường đó (`docs/team/features/FEAT-006/research-site.md:116-133`); site production chưa kiểm được; STD-DESIGN-7 | Viết cứng tên trường của production | Sửa cấu hình |

## Ràng buộc lúc nhận việc

- Mốc đối chiếu: `develop` @ `7cc37bb` (đã gồm phần code "làm trực tiếp" được nhận vào FEAT-004 lúc 00:31–00:32 ngày 2026-11-14) và cấu hình đang lưu trên site dev `miyano`.
- Một phiên khác đang hoàn thiện FEAT-004/005 trên cùng repo, cùng site `miyano` (journal FEAT-004, dòng 2026-11-14; có `.team/active-build-FEAT-004`). FEAT-007 đụng cùng các file (`registry.py`, `policy.py`, `prompts.py`, `runner.py`, ERP AI Setting). Vì vậy: không ghi `.team/current.json`; mọi việc của FEAT-007 làm trên nhánh `team/FEAT-007` trong worktree riêng, không checkout ở cây chính; test chạy trên site dùng chung nên một lần đỏ phải được chạy lại trước khi kết luận.
- Triển khai lên `erp.miyano.com.vn` nằm ngoài phạm vi (cổng G5).

## Đổi cỡ (nếu có)
- Không có.
