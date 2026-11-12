Feature: FEAT-003
Stage: intake
Author-agent: team-leader
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Intake FEAT-003 — Chú thích và mô tả rõ ràng cho các field của DocType mới (ERP AI Setting, ERP AI Credential, ERP AI Log)

- Yêu cầu gốc: "viết thêm các chú thích và mô tả rõ ràng cho các feild của doctype mới tạo, vd ERP AI Setting"
- Nguồn: hội thoại
- Loại việc: feature (cải thiện giao diện cấu hình, không đổi hành vi)
- Playbook: new-feature
- Size: S
- Mode: decide
- Lý do chọn playbook/cỡ: Không có playbook khớp riêng — tài liệu trong form của người dùng cuối là thay đổi metadata DocType (thuộc tính `description` của field) chứ không phải tệp tài liệu riêng (`docs-only`/`client-docs` không áp dụng), nên dùng `new-feature` (dòng "mọi trường hợp khác"). Cỡ S: hiện chỉ 1 trong 22 field của `erp_ai_setting.json` có `description`, 0/18 ở `erp_ai_credential.json`, 0/31 ở `erp_ai_log.json` (đếm `grep -c '"description"'` trên `erp_ai/erp_ai_agent/doctype/*/*.json`); sửa ≤ 3 tệp JSON, không đổi cột/kiểu field, không đổi logic; thêm một test kiểm mỗi field hiển thị đều có mô tả.
- Skill tạm: không cần
- Ngân sách: max_agents_per_feature = 10; feature_budget_usd = không giới hạn

## Điểm analyst phải làm rõ (không tự giả định)
- Phạm vi "doctype mới tạo": 3 DocType của app (`ERP AI Setting`, `ERP AI Credential` là bảng con, `ERP AI Log`) và 3 field mới của FEAT-002 (`thinking_text`, `answer_delay_min_s`, `answer_delay_max_s`)? Report `ERP AI Accuracy`, label của Section Break/nút có nằm trong phạm vi không?
- "Chú thích và mô tả" = thuộc tính `description` hiển thị dưới field trên form (Frappe), kèm `label` tiếng Việt chuẩn; có cần thêm chú thích ở mức DocType/section (Section Break `description`) và gợi ý "ví dụ"/đơn vị/giá trị hợp lệ/hệ quả (vd `permission_level` L0–L3 làm gì, giá bằng USD/triệu token, `excluded_teams` mỗi dòng một tên nhóm) không.
- Ngôn ngữ: tiếng Việt (như label hiện có); có cần bản dịch `translations` không.
- Field chỉ-đọc/tự quản (`spent_this_month_usd`, trạng thái khóa…) và field của ERP AI Log: mô tả nói ai ghi, người có được sửa không.
- Không để lộ thông tin nhạy cảm (khóa, giá trị thật) trong mô tả.

## Ràng buộc của người yêu cầu
- Như FEAT-001/FEAT-002: commit local trên `team/FEAT-003`, không push, không đụng `develop`/`main`; G1–G4 tắt, G5 bật; không đổi giá trị `ERP AI Setting` trên `miyano`.
- **Phụ thuộc FEAT-002:** FEAT-002 đang build trên `team/FEAT-002` và cũng sửa `erp_ai_setting.json` (3 field mới). Để tránh xung đột, FEAT-003 chỉ bắt đầu `/team:build` sau khi FEAT-002 được verify, và nhánh nền là `team/FEAT-002` (không phải `team/FEAT-001`).
- `.team/current.json` đang do tech-lead của FEAT-002 giữ (stage build) nên intake này không ghi đè nó; ghi khi chạy `/team:analyze FEAT-003`.

## Đổi cỡ (nếu có)
- —
