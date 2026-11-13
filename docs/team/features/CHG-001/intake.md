Feature: CHG-001
Stage: intake
Author-agent: team-leader
Date: 2026-11-13
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Intake CHG-001 — Bot làm luôn, chỉ một bước duyệt / không duyệt

- Yêu cầu gốc: "sửa lại bot làm luôn, không cần hỏi, chỉ cần 1 nút duyệt or khôgn duyệt nếu duyệt thì bot làm luôn"
- Nguồn: hội thoại (2026-11-13)
- Loại việc: change
- Playbook: change-request
- Size: L
- Mode: decide
- Lý do chọn playbook/cỡ: yêu cầu đổi luồng duyệt đã có spec của FEAT-004 (form đề xuất có 3 nút Duyệt / Từ chối / Hoàn tác, mỗi nút kèm hộp xác nhận: `erp_ai/erp_ai_agent/doctype/erp_ai_change_proposal/erp_ai_change_proposal.js:19-65`), luồng chờ chữ "ok" của FEAT-005 (`erp_ai/agent/prompts.py:106`) và mẫu comment luôn có "Cần ai quyết" (`erp_ai/agent/prompts.py:126`); chạm nhiều module (prompt, runner, form Desk, tool cấu hình) và đổi một ràng buộc an toàn ("chữ trong phiếu không bao giờ là duyệt", `prompts.py:164`) nên cỡ L.
- Skill tạm: không cần
- Ngân sách: max_agents_per_feature = 10; feature_budget_usd = không giới hạn

## Điểm analyst phải chốt (decide, ghi rõ giả định)

- "Làm luôn, không cần hỏi" áp cho việc nào: việc bot đã có quyền làm trực tiếp (phân loại, gán người, comment) hay cả việc ghi cấu hình, tạo User, sửa code, chạy lệnh `bench`.
- "Một nút duyệt hoặc không duyệt" nằm ở đâu: form `ERP AI Change Proposal` trên Desk, hay ngay trên trang phiếu Helpdesk; ai được bấm.
- Bỏ hộp xác nhận và nút Hoàn tác, hay chỉ bỏ hộp xác nhận.
- Luồng chữ "ok" của FEAT-005 thay bằng nút duyệt, hay giữ.
- Những ràng buộc không đổi dù duyệt một bước: danh sách cấm của ADR-011/013/014/016, giới hạn app, không lộ khóa.

## Ràng buộc lúc nhận việc

- FEAT-004 đang build dở (27/52, tạm dừng theo lệnh người), FEAT-005 chưa build: thay đổi này sửa spec của cả hai trước khi build tiếp.
- Cây chính (`develop`) đang có code chưa commit do phiên khác sửa trực tiếp (`prompts.py`, `runner.py`, `registry.py`, `policy.py`, `change_guard.py`, `apply_job.py`, `propose_change.py`, `site_api.py`…): chưa rõ có trùng phạm vi với CHG-001 không; phải hỏi người trước khi giao build.

## Đổi cỡ (nếu có)
