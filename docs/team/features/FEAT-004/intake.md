Feature: FEAT-004
Stage: intake
Author-agent: team-leader
Date: 2026-11-12
Approved-by:
<!-- Cổng: người duyệt điền dòng trên `Approved-by: <tên> <YYYY-MM-DD>`. Không có cổng thì để trống. -->

# Intake FEAT-004 — Cho bot quyền sửa code và chạy lệnh bench, có người duyệt từng thay đổi

- Original request: "thế làm sao để bot có full quyền đối với code của hệ thống, tôi muốn bot này sửa được cả cài đặt hệ thống, bot hỗ trợ erp mà, tài khoản tôi cũng cho nó full quyền rồi nhưng nó chả làm được gì cả" (đã chốt: "Thêm quyền sửa code và chạy lệnh"; trước đó: "bảo tạo 1 user cũng không tạo được")
- Source: conversation
- Work type: feature (mở rộng bộ công cụ của agent)
- Playbook: new-feature
- Size: L
- Mode: decide
- Reason for playbook/size: hành vi mới cho hệ thống đang chạy (không khớp dòng nào khác của bảng); nhiều module (công cụ, registry, authority, prompt, policy, log) và đổi quyết định bảo mật ADR-003/ADR-005, nên cỡ L. Bằng chứng: bot chỉ có 4 công cụ ghi phiếu (`erp_ai/agent/tools/write_ticket.py:113,133,147,161`), `User` nằm trong `DENIED_DOCTYPES` (`erp_ai/agent/tools/read.py:9-22`), prompt cấm sửa `apps/` và chạm phân quyền (`erp_ai/agent/prompts.py`, mục GIỚI HẠN).
- Temp skill: not needed
- Budget: max_agents_per_feature = 10; feature_budget_usd = unlimited

## Điểm rủi ro phải giải trong spec/design (không bỏ qua)
- Nội dung phiếu là dữ liệu không tin cậy (STD-SEC-5): ai tạo được phiếu đều có thể nhúng lệnh để điều khiển bot. Công cụ sửa code/chạy lệnh phải có người duyệt từng thay đổi và không tự chạy theo chỉ dẫn trong phiếu.
- Quyền của tài khoản `ai.agent` không phải rào cản; rào cản là bộ công cụ, prompt và policy. Cần quyết định có nâng quyền tài khoản không.
- ADR-003/ADR-005 và `protected_paths` đang cấm bot sửa `apps/` và chạm phân quyền; spec phải nêu ADR nào đổi, đổi thế nào, và cách hoàn tác.
- Chạy lệnh: allowlist lệnh, thư mục làm việc, không đọc `.env*`/secret, ghi log từng lệnh vào ERP AI Log.

## Size changes (if any)
- Không có.

## Yêu cầu bổ sung 2026-11-12 (phiên team-leader thứ hai nhận FEAT-004)

- Lý do đổi người giữ: phiên team-leader đã lập FEAT-004 (intake → plan) đang build FEAT-006; FEAT-004 dừng ở `planned`, không phiên nào chạy. Người giao FEAT-004 cho phiên này.
- Câu gốc của người (nguyên văn):
  - "có cách nào để bot sửa được code không? kiểu can thiệp trực tiếp vào core ý"
  - "oke làm đi, gọi agent lên mà làm cho nhanh và đúng yêu cầu"
- Hiện trạng đối chiếu: spec A-3 (`spec.md:123`) đã cho System Manager chọn app được sửa, mặc định rỗng, `erp_ai` luôn bị cấm; spec A-4 (`spec.md:124`) và mục Ngoài phạm vi (`spec.md:27`, `spec.md:50`) loại commit/push/đổi nhánh, với hướng sửa đã ghi sẵn ở A-4: "thêm bước commit local vào bước áp dụng". App lõi trên bench: `frappe` và `helpdesk` theo nhánh chính thức `version-15`; `erpnext` ở nhánh `develop` (fork của công ty, `prompts.py:90`); `hrms` cũng là fork.
- Quyết định (decide, team-leader; người đã chọn "làm đi" sau khi được đưa ba hướng a/b/c và chưa chọn hướng nào):
  - Chọn: (c) = (a) + (b).
    - (a) Cho bot đề xuất sửa code của app lõi (`frappe`, `erpnext`, `helpdesk`, `hrms`) khi System Manager thêm app đó vào danh sách app được sửa; `erp_ai` vẫn bị cấm cứng; mọi thay đổi vẫn cần người duyệt từng cái.
    - (b) Mỗi thay đổi đã duyệt và áp dụng thành đúng một commit git local trong repo của app đó, chỉ gồm file được đổi; bot không push, không đổi nhánh đang checkout (site đang chạy nhánh đó). Đẩy lên fork, mở PR và deploy vẫn là việc của người.
  - Vì: không có commit thì thay đổi bot làm trên site dev không có đường lên prod (FEAT-004 không chạy trên production) và dễ mất khi `bench update`; commit giữ lịch sử, hoàn tác bằng git được, người đẩy lên fork để CI test.
  - Phương án khác: chỉ (a) (không đổi gì, thay đổi nằm ở working tree như A-4 cũ); chỉ (b); bot tự push/mở PR (cần token GitHub trên máy chủ, trái quy tắc không push).
  - Sai thì: bỏ phần (b) bằng `analyze --amend` trả A-4 về như cũ; tắt công tắc hoặc rút app khỏi danh sách thì bot quay về hành vi hiện tại.
- Phạm vi đợt này: chỉ tài liệu (spec → ADR → design → plan/tasks) trong `docs/team/features/FEAT-004/` và ADR của FEAT-004. Build sau khi FEAT-006 qua verify, nền là `team/FEAT-006` (cùng site `miyano`, cùng sửa `runner.py`, bảng công cụ, `erp_ai_setting.json`; journal FEAT-004 dòng 19 đã loại build song song).
- Không ghi `.team/current.json` trong đợt này (build FEAT-006 của phiên kia đang giữ), như quy ước phiên kia đã dùng khi FEAT-003 build.
