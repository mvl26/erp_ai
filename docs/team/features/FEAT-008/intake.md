Feature: FEAT-008
Stage: intake
Author-agent: team-leader
Date: 2026-11-16
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Intake FEAT-008 — Cơ sở kiến thức để bot học và tự đề xuất cải tiến

- Yêu cầu gốc: "phát triển phần này, tôi muốn bot có 1 cơ sở kiến thức để học và tối ưu"
- Nguồn: hội thoại (2026-11-16); "phần này" = chia việc, phân loại phiếu, cơ sở kiến thức của bot.
- Loại việc: feature
- Playbook: new-feature
- Size: L
- Mode: decide
- Lý do chọn playbook/cỡ: hành vi mới cho hệ thống đang chạy; công cụ tìm và bài nháp của FEAT-007 giữ nguyên, việc "học" chưa có. Cỡ L: nhiều module (sự kiện phiếu, phân loại, lập luận, DocType mới, lịch, báo cáo) và NFR mới (nhóm loại trừ, bài học là dữ liệu, trần chi phí prompt). Bằng chứng (`develop` @ `28d35f8`):
  - Lần người sửa phân loại chỉ vào Log và báo cáo độ đúng (`erp_ai/handlers.py:127`, `erp_ai_accuracy.py:172-177`); lời gọi phân loại không nhận bài học (`erp_ai/agent/prompts.py:427-448`).
  - Tri thức chỉ là tìm theo từ khóa (`erp_ai/agent/knowledge.py:53`, `:89`; `tools/read.py:130`) và bài nháp khi phiếu đóng (`tools/kb_draft.py:49`).
  - Duyệt, từ chối, hoàn tác đề xuất (`changes/transitions.py:222-237`) và rà soát tháng (`monthly_review.py:63`) không để lại bài học.
- Skill tạm: không cần.
- Ngân sách: max_agents_per_feature = 10; feature_budget_usd = không giới hạn

## Quyết định của người (AskUserQuestion, 2026-11-16)

| # | Câu hỏi | Người chọn |
|---|---|---|
| N-1 | Bot học từ nguồn nào | Cả bốn: (1) người sửa đầu mục, nhóm, người nhận; (2) phiếu đã giải quyết (triệu chứng, nguyên nhân, cách xử lý); (3) người dạy trực tiếp trên form hoặc bằng comment; (4) đề xuất bị từ chối hoặc hoàn tác và phiếu bị chấm sai khi rà soát tháng |
| N-2 | Dùng ngay hay phải duyệt | "Tùy loại": bài do người có quyền tạo dùng ngay; bài bot tự rút từ nội dung phiếu phải duyệt trước |
| N-3 | "Tối ưu" tới mức nào | "Bot tự đề xuất cải tiến": định kỳ tổng kết lỗi lặp lại, đề xuất sửa kiến thức hoặc hướng dẫn phân loại, người duyệt mới áp dụng; kèm số liệu bài nào được dùng, độ đúng tăng hay giảm |

## Quyết định của team-leader (decide, 2026-11-16, sau kiến trúc; Q-A1..Q-A3 của `arch-impact.md`)

| # | Chọn | Vì | Phương án khác | Sai thì sửa |
|---|---|---|---|---|
| D-1 (Q-A1) | AC-14 không đòi mục "Căn cứ": bot nêu mã bài đã dùng trong "Nhận định" hoặc "Hướng xử lý"; căn cứ kiểm là vết dùng AC-17 | FEAT-007 đã bỏ "Căn cứ" và ghim test; AC-21 cấm sửa | Chỉ còn vết; dựng lại "Căn cứ" | Amend AC-14 |
| D-2 (Q-A2) | Giữ đề xuất loại (b) (N-3), đợt 2. FEAT-008 không tự nối runner với `prompt_override_*`: đó là AC-38 của FEAT-007, chưa có trên `develop` (không mã nào trong `erp_ai/agent/` đọc các ô này). AC-19 (b) ghi rõ phụ thuộc | Một hành vi một chủ; tránh hai feature cùng sửa một chỗ trong `runner.py` | FEAT-008 tự nối; bỏ (b) | FEAT-007 đóng mà thiếu: mở CHG riêng hoặc amend thêm AC |
| D-3 (Q-A3) | Việc không gắn phiếu (dạy trên form, tắt/bật bài): chỉ role `ERP AI Instructor`; không bao giờ `Administrator`, `Guest`, tài khoản bot. Dạy bằng comment giữ A-1 | Không có phiếu thì không kiểm được vế "được người khác giao phiếu" | Thêm System Manager | Đổi ở AC-8 và các AC tắt/bật |

## Ghi chú cho các vai sau

- Không làm lại gói 4 của FEAT-007 (AC-45..AC-48); phải đổi thì nêu thành điểm riêng.
- Tìm theo nghĩa (embedding) ngoài phạm vi: kéo theo dịch vụ ngoài, dữ liệu rời hệ thống.
- CHG-005, CHG-006, CHG-007 cùng đụng `runner.py`, `prompts.py`: plan xếp thứ tự theo `team.py sessions`.
