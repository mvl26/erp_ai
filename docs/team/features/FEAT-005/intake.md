Feature: FEAT-005
Stage: intake
Author-agent: team-leader
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Intake FEAT-005 — Bot tạo User và sửa cấu hình hệ thống qua DocType (allowlist)

- Original request: "con bot chả làm được cái gì vậy? bảo tạo 1 user cũng ko tạo được" và "tôi muốn bot này sửa được cả cài đặt hệ thống, bot hỗ trợ erp mà, tài khoản tôi cũng cho nó full quyền rồi nhưng nó chả làm được gì cả". Người đã chốt (2026-11-12): "Tách FEAT-005, làm song song" với FEAT-004; role được gán: "Role nghiệp vụ, cấm admin" — được gán role nghiệp vụ (ví dụ Sales User, Stock User, HD Agent), không bao giờ gán System Manager, Administrator hay ERP AI Instructor, để chặn tự nâng quyền.
- Source: conversation
- Work type: feature (thêm tool ghi DocType cho agent: tài khoản + cấu hình, tức nhóm tool `L2`/`L3` mà FEAT-004 spec A-1 để ngoài)
- Playbook: new-feature
- Size: L
- Mode: decide
- Reason for playbook/size: hành vi mới cho hệ thống đang chạy; nhiều module (tool, registry, authority/policy theo mức L2/L3, prompt, cấu hình, cảnh báo hằng ngày) và đổi quyết định bảo mật ADR-005/ADR-006, nên cỡ L. Bằng chứng: `User` nằm trong `DENIED_DOCTYPES` (`erp_ai/agent/tools/read.py:9-22`); chỉ có 4 tool ghi phiếu (`erp_ai/agent/tools/write_ticket.py:113,133,147,161`); prompt cấm chạm Has Role (`erp_ai/agent/prompts.py`, mục GIỚI HẠN) mà gán role cho User mới chính là tạo dòng Has Role; FEAT-004 spec A-1 (`docs/team/features/FEAT-004/spec.md:121`) chuyển phần này sang intake riêng.
- Temp skill: not needed
- Budget: max_agents_per_feature = 10; feature_budget_usd = unlimited

## Điểm phải giải trong spec/design
- Danh sách role được gán (allowlist) và danh sách cấm cứng: System Manager, Administrator, ERP AI Instructor, cùng mọi role mang quyền sửa phân quyền.
- Danh sách DocType cấu hình được ghi (Customize Form/Property Setter, Holiday List, Workflow, Notification, Assignment Rule…, theo bảng đầu mục B trong `erp_ai/agent/prompts.py`); việc không hoàn tác được thì chờ chữ "ok" (quy tắc 6 của CORE_PROMPT).
- Người dùng đã cấp thêm role cho `ai.agent@miyano.com.vn`, nhưng thừa role không mở thêm được việc gì: bot chỉ làm được những gì tool cho phép, và cảnh báo hằng ngày "Tài khoản agent có role ngoài danh sách cho phép" sẽ bắn (`erp_ai/tasks.py:74-81,133`). Spec phải chốt quyền nào tài khoản agent cần thật sự (ADR-006).
- Nội dung phiếu là dữ liệu không tin cậy (STD-SEC-5): người tạo phiếu không được tự yêu cầu bot cấp quyền cho chính mình; thẩm quyền ra lệnh theo `ERP AI Instructor` (`erp_ai/agent/authority.py`).
- Đụng chung với FEAT-004 (registry, prompt GIỚI HẠN, ADR-005); hai feature phải tránh sửa chồng.

## Size changes (if any)
- Không có.
