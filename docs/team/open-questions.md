Feature: takeover
Stage: takeover
Author-agent: team-leader
Date: 2026-11-10
Approved-by: Hieu 2026-11-11

<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Câu hỏi mở (≤ 10)

Trả lời ngay dưới từng câu. Xếp theo mức chặn onboard.

1. Bước 0 (backup + script kiểm chứng field, guide mục 6) và bước 1 (bộ đánh giá offline 71 phiếu, guide mục 15) đã làm chưa? Nếu bước 1 đã chạy: độ chính xác tổng và theo từng đầu mục là bao nhiêu? — vì sao cần: guide coi bước 1 là cửa quyết định *trước khi dựng app* (`docs/HuongDan_TrienKhai_erp-ai.md:1289`); app đã được tạo, nên intake đầu tiên là `eval/` hay là DocType phụ thuộc vào câu này.
   - Trả lời:
2. Đội dùng site dev nào để chạy test (local đang có `miyano`, chưa cài `erp_ai`, **không có app `helpdesk`**)? Có cài helpdesk vào bench local không, đúng phiên bản nào trên production? — vì sao cần: mọi lệnh `cmd.*` cần `<site>`; không có helpdesk thì không test được tính năng nào dựa trên HD Ticket.
   - Trả lời:
3. Tên module: giữ `ERP AI agent` (thư mục `erp_ai/erp_ai_agent/`, `modules.txt:1`) hay đổi thành `ERP AI` như guide (`erp_ai/erp_ai/doctype/`, `:634`)? — vì sao cần: phải chốt trước DocType đầu tiên; đổi sau thì phải migrate.
   - Trả lời:
4. `.gitignore:10` (`team/`, thay đổi chưa commit xuất hiện lúc 18:25:53 trong khi quét — ai/công cụ nào thêm?) đang làm git bỏ qua `docs/team/`. Có muốn version các artifact của đội (spec, design, plan, journal, 5 báo cáo này) không? — vì sao cần: nếu có, phải sửa dòng này; onboard sẽ ghi thêm vào `docs/team/`.
   - Trả lời:
5. CI đang chắc chắn đỏ vì chưa có test (`.github/workflows/ci.yml:45`). Chấp nhận đỏ tới khi có test đầu tiên, hay sửa CI trước? — vì sao cần: quyết định verdict `adjust-profile` hay `clean-first` trong `ai-readiness.md`.
   - Trả lời:
6. Phiên bản Frappe/Helpdesk trên production `erp.miyano.com.vn` là gì? Local đang là frappe 15.112.0 / erpnext 15.83.0. — vì sao cần: guide mục 19 cảnh báo tên field HD Ticket, `HD Ticket Template`, `deduplicate=` khác giữa các bản.
   - Trả lời:
7. Bản "Chiến lược AI Agent Helpdesk Miyano" (31/10/2026) nằm ở đâu? — vì sao cần: guide nói phần 6 đầu mục, routing, KPI, danh mục cấm vẫn theo bản đó (`:1492`), mà nó không có trong repo.
   - Trả lời:
8. `docs/HuongDan_TrienKhai_erp-ai.md` và `.claude/settings.json` có được commit vào `develop` không? — vì sao cần: hiện untracked; tài liệu là nguồn yêu cầu duy nhất của dự án.
   - Trả lời:
9. Có muốn đội làm QA giao diện (Playwright) cho phần custom field và nút trên trang ticket Helpdesk không (khe `ui`)? — vì sao cần: quyết định có bật QA trình duyệt.
   - Trả lời:
10. Quy ước tên nhánh và luồng PR (`develop` → `main`?) — vì sao cần: khe `naming.branch`; repo hiện chỉ có nhánh `develop`.

- Trả lời:

## Đã quét / Chưa quét / Độ tin cậy

| Tầng  | Đã quét                                              | Chưa quét                                                          | Độ tin cậy                                       |
| ------ | ------------------------------------------------------- | -------------------------------------------------------------------- | --------------------------------------------------- |
| T0–T2 | Như `assessment.md`                                  | Production `erp.miyano.com.vn` (ngoài phạm vi, không truy cập) | Câu hỏi dựa trên bằng chứng có `file:line` |
| T3     | Không chạy: không có mâu thuẫn chưa giải thích | —                                                                   | —                                                  |
